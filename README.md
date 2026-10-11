# AI Startup Incubator — AI Co-Founder

An AI-powered startup incubator. Describe an idea, and an agent — not a scripted
chatbot — decides which tools to run (live market research, live competitor
research, financial calculations, an ML viability model), gathers structured
evidence with sources, remembers your startup's profile across turns, and can
assemble everything into a report.

FastAPI + a real tool-calling agent loop + a swappable LLM provider (local
Ollama `qwen2.5:3b`, or any OpenAI-compatible cloud endpoint) + live web
research (Exa → Tavily → DuckDuckGo) + SQLite/PostgreSQL, with a React/Vite
frontend.

## Architecture

```text
Local development                         Production (e.g. Render)
React (Vite)                              React static site
   ↓ VITE_API_BASE_URL                       ↓ VITE_API_BASE_URL
FastAPI                                   FastAPI (0.0.0.0:$PORT)
   ↓                                         ↓
ProjectOrchestrator → AgentEngine         ProjectOrchestrator → AgentEngine
   ↓                                         ↓
ModelProvider  (LLM_PROVIDER=ollama)      ModelProvider  (LLM_PROVIDER=cloud)
   ↓                                         ↓
OllamaProvider → Qwen2.5:3B (local)       CloudLLMProvider → configured cloud model
```

The provider is chosen **only** by the deployment's environment variables —
never by who is logged in. Even the project owner using the public URL uses
the cloud provider. `AgentEngine` and `ToolRegistry` only know the
`ModelProvider` interface (`app/models/base.py`); provider selection lives in
`app/models/factory.py`.

```text
AgentEngine (tool-calling loop, max 6 iterations)
   └── ToolRegistry
         ├── web_search            ─┐
         ├── market_research        ├─→ ResearchProvider (app/research/)
         ├── competitor_research    │     cache → fallback chain:
         ├── financial_analysis    ─┘     Exa → Tavily → DuckDuckGo  (+ Jina Reader for pages)
         ├── startup_viability_predictor  (RandomForest, ml/)
         ├── calculator, text_processor, file_reader
         └── memory_write / memory_search / knowledge_search
```

### Live, evidence-based research

Research tools never ask the LLM to "tell me about the market". Every run is:

```text
Research tool → ResearchProvider → live search → retrieved sources [S1], [S2], …
             → evidence prompt (strict no-fabrication rules) → LLM analysis
             → deterministic checks → findings + sources (title, URL, date, retrieval time)
```

- **Retrieved evidence**: key findings must cite a retrieved source id; findings
  citing nothing, or citing a source that doesn't exist, are discarded.
- **Number check**: any figure in a source-backed claim must literally appear in
  the cited source text, otherwise the claim is discarded and the omission is
  listed under *Limitations*. Interpretation bullets carrying figures found in
  no source are removed too.
- **Competitors** must be named in a retrieved source. Official websites are
  fetched (Jina Reader → direct HTTP) and marked verified only if the live page
  mentions the company. Pricing not found in a source becomes
  **"Not verified from available sources"**.
- **Derived / interpretation** content (trends, risks, strengths, positioning,
  differentiation) is labelled as AI interpretation in the API and UI.
- **No evidence → no fake research**: if all providers fail the result says
  *"Live research is currently unavailable…"*; if nothing relevant is found it
  says *"Insufficient reliable evidence was retrieved…"*. The LLM is not called
  to fill the gap (unless the user explicitly asked for general background, in
  which case the result is labelled `background_only`, not research).
- Sources are ranked government → academic → research orgs → news → other web.
- Results are cached in memory for `RESEARCH_CACHE_TTL_SECONDS` (default 1h).
  Cached sources keep their original `retrieved_at`, and the UI shows e.g.
  "Retrieved approximately 42 minutes ago".
- Normal conversation does not trigger web search; only research/finance-type
  requests reach the tool-calling path (`app/agent/router.py`).

## Local development (Ollama + Qwen2.5:3B)

### 1. Install dependencies

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt     # runtime deps + pytest
cd frontend; npm install; cd ..
```

### 2. Start Ollama and the model

```powershell
ollama serve                 # terminal 1 (skip if the Ollama app is already running)
ollama pull qwen2.5:3b       # once
ollama run qwen2.5:3b        # terminal 2 (optional: pre-loads the model)
```

### 3. Configure `.env`

```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

Keep `LLM_PROVIDER=ollama`. For live research add a free `EXA_API_KEY`
and/or `TAVILY_API_KEY` (see *Research providers* below). With no keys, research
falls back to DuckDuckGo, which usually works from a home connection.

Older `.env` files using `MODEL_RUNTIME` / `MODEL_NAME` still work (they are
aliases of `LLM_PROVIDER` / `OLLAMA_MODEL`).

### 4. Start FastAPI

```powershell
python main.py serve         # http://127.0.0.1:8080
curl http://127.0.0.1:8080/health          # {"status":"ok"}
curl http://127.0.0.1:8080/api/v1/health   # shows provider "ollama", model "qwen2.5:3b"
```

### 5. Start React and open it

```powershell
cd frontend
npm run dev                  # http://localhost:5175
```

`CORS_ORIGINS` must include the frontend origin (the default `.env.example`
includes `http://localhost:5175`). The Settings page shows which LLM and research
providers are active.

Train the viability model (only needed if `ml/models/viability_model.joblib` is missing):

```powershell
python ml/train/train_viability_model.py
```

## Production deployment (Render free tier)

The deployed app needs no Ollama, Python, virtualenv or GPU on the user's
device: the browser talks only to FastAPI, and FastAPI talks to the cloud LLM
and research APIs. **Ollama is never installed or run on the server, and no
model weights are downloaded.**

> Status: the code is ready for deployment, but **no cloud LLM provider has
> been selected yet**. Until `CLOUD_LLM_*` is set, a `LLM_PROVIDER=cloud`
> server refuses to start with a clear message naming the missing variables.

`render.yaml` in the repo root is a Render Blueprint describing both services.

1. **Push to GitHub** (make sure `.env` is not committed — it is git-ignored).
2. **Backend — Render Web Service** (or *New → Blueprint* to use `render.yaml`):
   - Runtime: Python · Root directory: repo root
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
3. **Backend environment variables** (Render dashboard → Environment; never in Git):

   | Variable | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.11.9` |
   | `APP_ENV` | `production` |
   | `LLM_PROVIDER` | `cloud` |
   | `GROQ_API_KEYS` | secret, comma-separated Groq keys (tried first, in order) |
   | `GEMINI_API_KEYS` | secret, comma-separated Gemini keys (backup after Groq) |
   | `GROQ_MODEL` / `GEMINI_MODEL` | `llama-3.3-70b-versatile` / `gemini-2.5-flash` |
   | `EXA_API_KEY`, `TAVILY_API_KEY` | secrets (Exa recommended, Tavily optional backup) |
   | `JINA_API_KEY` | optional |
   | `RESEARCH_PROVIDER` / `RESEARCH_FALLBACK_PROVIDERS` | `exa` / `tavily,duckduckgo` |
   | `JWT_SECRET_KEY` | long random value (required; the server won't start with the placeholder) |
   | `CORS_ORIGINS` | your frontend URL, e.g. `https://myai-web.onrender.com` |
   | `DATABASE_URL` | `sqlite:///./data/agent.db` (ephemeral) or a `postgresql://` URL |
   | `CHAT_RATE_LIMIT_PER_MINUTE` | e.g. `10` |

4. **Frontend — Render Static Site**:
   - Root directory: `frontend`
   - Build command: `npm ci && npm run build`
   - Publish directory: `dist`
   - Environment: `VITE_API_BASE_URL=https://<your-backend>.onrender.com`
   - Redirects/Rewrites: `/*` → `/index.html` (Rewrite), for client-side routes
5. **Configure the cloud LLM**: set `GROQ_API_KEYS` and/or `GEMINI_API_KEYS`.
   Keys are tried in order (Groq first, then Gemini); a rate-limited or rejected
   key is skipped until its cooldown expires. Alternatively, any endpoint that
   implements OpenAI-style `POST {CLOUD_LLM_BASE_URL}/chat/completions` works via
   `CLOUD_LLM_*` (tried before Groq). For tool-calling quality, pick a model that supports
   function calling. Set `CLOUD_LLM_REASONING_EFFORT` only if the model accepts it.
6. **Configure research**: add `EXA_API_KEY` (and optionally `TAVILY_API_KEY`).
7. **Deploy**, then verify:
   - `GET https://<backend>/health` → `{"status":"ok"}`
   - `GET https://<backend>/api/v1/health` → `model_runtime: "cloud"`, `llm_status: "reachable"`, `research_providers: ["exa", ...]`
   - Sign up / log in in the deployed frontend
   - Chat ("hi") → normal answer, no sources
   - "What is the market size for …?" → Market page shows key findings with `[S#]` citations and a Sources list
   - "Who are my competitors?" → Competitors page shows sources, verified sites, unverified pricing marked as such
   - Click several source links and check they support the claims
   - Financial / viability / report / roadmap still work
   - Open the frontend on a phone

## Research providers (free tiers, as of October 2026)

| Provider | Role | Free allowance | Key |
|---|---|---|---|
| Exa | primary search (+ page contents) | monthly credit resetting on the 1st, no card | `EXA_API_KEY` |
| Tavily | fallback search (+ page extract) | 1,000 credits/month (basic search = 1 credit), no card | `TAVILY_API_KEY` |
| DuckDuckGo | last-resort search | unofficial HTML page, no key; often rate-limited/blocked from cloud servers | — |
| Jina Reader | reading a known URL | ~20 req/min without key, more with a free key | `JINA_API_KEY` (optional) |

One market or competitor research request uses about 3 search queries plus up
to `RESEARCH_MAX_FETCHED_PAGES` page reads. When Exa's credit runs out, Tavily
takes over (its free tier covers roughly 250–300 research requests per month);
the cache reduces repeats. Providers without a key are skipped.

## Environment variables

All backend variables are documented in `.env.example`; the frontend has one
(`VITE_API_BASE_URL`, `frontend/.env.example`). Only `VITE_*` values reach the
browser, so **never** create `VITE_*` variables for API keys. `CLOUD_LLM_API_KEY`,
`TAVILY_API_KEY`, `EXA_API_KEY` and `JINA_API_KEY` exist only on the backend;
they are never returned by any endpoint or written to logs.

Safety limits: `MODEL_MAX_TOKENS`, `FAST_PATH_MAX_TOKENS`, `CHAT_HISTORY_LIMIT`,
`CLOUD_LLM_TIMEOUT_SECONDS`, `AGENT_TIMEOUT_SECONDS`, `MAX_TOOL_CALLS_PER_RUN`,
`CHAT_RATE_LIMIT_PER_MINUTE`, `RESEARCH_MAX_RESULTS`, `RESEARCH_MAX_FETCHED_PAGES`,
`RESEARCH_TIMEOUT_SECONDS`, `RESEARCH_FETCH_TIMEOUT_SECONDS`,
`RESEARCH_MAX_CHARS_PER_SOURCE`.

## Error handling

Users see safe messages only — never stack traces, keys or provider bodies:
LLM failures → *"AI service is temporarily unavailable. Please try again."*
(rate limits and timeouts get their own short messages); research failures →
*"Live research is currently unavailable."* Each research provider failure
(timeout, auth, rate limit, server error, malformed or empty response) is
logged with the provider name and failure kind, then the next provider is tried.
If the LLM fails after sources were retrieved, the sources are still returned.

## Known limitations of the free deployment

- **Render Free spins down after ~15 minutes idle**; the first request after
  that takes up to a minute while it starts.
- **Render's filesystem is ephemeral.** With the default SQLite `DATABASE_URL`,
  users, projects and chats are **wiped on every deploy, restart or spin-down**.
  The app starts cleanly from an empty database, but for persistence set
  `DATABASE_URL` to a PostgreSQL URL (the database layer already supports it).
- The research cache and per-user rate limiter are in-memory, per instance.
- Free research quotas are limited (see table above); DuckDuckGo is unreliable from cloud IPs.
- Live research quality depends on what the search APIs return; the
  number-check guard can discard correct claims written in different units
  (e.g. "1.2 billion" vs "1,200 million").
- Cloud LLM output quality/rate limits depend on the provider chosen.

## Testing

```powershell
pytest                       # backend: agent loop, tools, providers, research, API
cd frontend; npm run build   # frontend: type-check + production build
```

Tests mock all external HTTP, so they need no API keys or internet. They cover
the cloud adapter (auth/rate-limit/timeout/malformed errors, no key leakage),
provider selection, Exa → Tavily → DuckDuckGo fallback, caching/expiry, and
that market/competitor research discard uncited claims, invented figures,
invented competitors and unverified pricing.

## ML: startup viability model

`ml/data/startup_viability.csv` is a small synthetic dataset (300 rows) of
8 factors mapped to a `viability_score`. `ml/train/train_viability_model.py`
trains a `RandomForestRegressor` and saves `ml/models/viability_model.joblib`
(committed; production loads it, so `scikit-learn` is pinned to the training
version). This is an educational decision-support estimate, not a real-world
success predictor.

## Layout

- `app/models` — `ModelProvider` interface, factory, `OllamaProvider`, `CloudLLMProvider`
- `app/research` — `ResearchProvider` interface, Tavily/Exa/DuckDuckGo providers, Jina/direct page readers, fallback chain, cache, evidence + citation guards
- `app/agent` — bounded tool-calling agent loop and fast/agent path router
- `app/tools` — registry, permission levels, research/finance/viability/utility tools
- `app/projects` — orchestrator, per-project stores
- `app/startup` — profile extraction, financial engine, response builder, report assembly
- `app/memory` / `app/knowledge` — per-project memory and documents
- `app/api` — FastAPI routers (auth, projects, conversations, project data, health, …)
- `app/security` — JWT auth, per-user chat throttle
- `ml/` — dataset, training script, runtime predictor
- `frontend/` — React + Vite + TypeScript + Tailwind v4 + Motion
- `render.yaml` — Render Blueprint (backend web service + static frontend)
