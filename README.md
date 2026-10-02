# AI Startup Incubator — AI Co-Founder

An AI-powered startup incubator. Describe an idea, and an agent — not a scripted
chatbot — decides which tools to run (market research, competitor research,
financial calculations, an ML viability model), gathers structured evidence,
remembers your startup's profile across turns, and can assemble everything into
a report.

Built on top of a reusable local-first agent platform: FastAPI + a real
tool-calling agent loop + Ollama (`qwen2.5:3b`) + SQLite, with a React/Vite
frontend.

## Architecture

```text
React (Vite + TS + Tailwind + Motion)
        ↓  HTTP (VITE_API_BASE_URL)
FastAPI  →  StartupOrchestrator
              ├── profile extraction (LLM, separate prompt)
              ├── AgentEngine (tool-calling loop, max 6 iterations)
              │     ├── Qwen2.5 3B via Ollama (ModelProvider abstraction)
              │     └── ToolRegistry
              │           ├── calculator
              │           ├── financial_analysis   (deterministic Python)
              │           ├── market_research      (LLM synthesis, marked non-live)
              │           ├── competitor_research  (LLM synthesis, marked non-live)
              │           ├── startup_viability_predictor  (RandomForest, ml/)
              │           ├── report_generator
              │           └── memory_write / memory_search / knowledge_search
              └── SQLite (startups, conversation_messages, analyses, memories)
                    ↓
              Structured AgentRunResponse → React
```

The agent decides which tools to call per request — a simple calculation
triggers only the calculator; "who are my competitors?" triggers only
`competitor_research`; a full evaluation may chain several tools. Nothing is
hardcoded into a fixed pipeline.

## Setup

### 1. Ollama + model

```powershell
ollama pull qwen2.5:3b
```

### 2. Backend

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Train the viability model once (writes `ml/models/viability_model.joblib`):

```powershell
python ml/data/generate_dataset.py   # optional: regenerate the synthetic dataset
python ml/train/train_viability_model.py
```

Run the test suite:

```powershell
pytest
```

Serve the API:

```powershell
python main.py serve
```

```powershell
curl http://127.0.0.1:8080/api/v1/health
```

Or run one request from the CLI:

```powershell
python main.py agent "I want to build an AI tutoring platform for engineering students in India."
```

### 3. Frontend

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://localhost:5173. Make sure `CORS_ORIGINS` in the backend `.env`
includes `http://localhost:5173` (it does by default).

## ML: startup viability model

`ml/data/startup_viability.csv` is a small synthetic dataset (300 rows) of
8 factors (`market_demand`, `competition`, `problem_severity`,
`customer_accessibility`, `business_model_strength`, `startup_cost`
[an affordability score, not raw currency], `scalability`,
`growth_potential`, each 0-100) mapped to a `viability_score`.
`ml/train/train_viability_model.py` trains a `RandomForestRegressor`
(`random_state=42`, 80/20 split), reports MAE/R², and saves
`ml/models/viability_model.joblib` + `model_metadata.json`. The API loads the
model once at runtime — it is never retrained on request. This is an
educational decision-support estimate, not a real-world success predictor.

## Testing

```powershell
pytest                       # backend: 24 tests — agent loop, tools, ML, schemas, financial math
cd frontend; npm run build   # frontend: type-check + production build
```

## Environment variables

See `.env.example` (backend) and `frontend/.env.example` (frontend,
`VITE_API_BASE_URL`).

## Demo prompt

> "I want to build an AI tutoring platform for engineering students in India."

Then, in the same conversation:

> "Who are my competitors?"
> "Calculate break-even if I charge $20/month with $3000 monthly cost."
> "Evaluate my startup's viability."
> "Generate a report."

Each message flows through the same loop: agent decides tools → tools execute
→ results are persisted per-startup → a structured response reaches the UI,
which shows live tool activity, updates the Dashboard/Market/Competitors/
Financial/Viability pages, and can assemble a full report at any time from
`GET /api/v1/startups/{id}/report`.

Note: this runs a 3B model on CPU locally — a full evaluation with several
chained tool calls can take 1-3 minutes. `AGENT_TIMEOUT_SECONDS` in `.env`
is set generously (240s) to accommodate this; lower it if you switch to a
faster runtime or GPU inference.

## Layout

- `app/models` — model interface + Ollama runtime (replaceable)
- `app/agent` — bounded tool-calling agent loop (iterations, timeout, tool limits)
- `app/tools` — registry, permission levels, calculator, startup tools, files/text
- `app/startup` — StartupProfile, StartupStore (SQLite), financial engine,
  LLM-backed profile extraction, response builder, report assembly
- `app/memory` / `app/knowledge` — SQLite long-term memory / documents, isolated by `application_id`
- `app/api` — FastAPI: health, agent run, startups/analysis/report, tools, memory, knowledge
- `app/security` — API key gate (`REQUIRE_API_KEY`)
- `ml/` — dataset, training script, runtime predictor (RandomForest viability model)
- `frontend/` — React + Vite + TypeScript + Tailwind v4 + Motion

Not built (intentionally, MVP scope): PostgreSQL, live web search/RAG,
authentication, multi-agent orchestration, fine-tuning.
