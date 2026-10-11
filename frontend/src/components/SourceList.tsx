import type { Source } from "../api/types"

const KIND_LABELS: Record<string, string> = {
  government: "Government",
  academic: "Academic",
  research: "Research org",
  news: "News",
}

function formatDate(value: string | null | undefined, withTime = false): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return withTime
    ? date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
    : date.toLocaleDateString(undefined, { dateStyle: "medium" })
}

function safeHref(url: string | null | undefined): string | null {
  if (!url) return null
  try {
    const parsed = new URL(url)
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null
  } catch {
    return null
  }
}

function domainOf(source: Source): string | null {
  if (source.domain) return source.domain
  const href = safeHref(source.url)
  return href ? new URL(href).hostname.replace(/^www\./, "") : null
}

/** Retrieved sources behind a research answer. Only ever renders what the backend
 * actually retrieved — never model-written links. */
export function SourceList({
  sources,
  title = "Sources",
  compact = false,
}: {
  sources: Source[] | undefined
  title?: string
  compact?: boolean
}) {
  if (!sources || sources.length === 0) return null
  return (
    <div className={compact ? "" : "mt-1"}>
      <div className="mb-2 text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
        {title} ({sources.length})
      </div>
      <ol className="flex flex-col gap-2">
        {sources.map((source, i) => {
          const href = safeHref(source.url)
          const domain = domainOf(source)
          const published = formatDate(source.source_date)
          const retrieved = formatDate(source.retrieved_at, true)
          const kind = source.source_kind ? KIND_LABELS[source.source_kind] : undefined
          return (
            <li
              key={`${source.url ?? source.title}-${i}`}
              className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-xs"
            >
              <div className="flex items-start gap-2">
                <span className="shrink-0 font-mono text-[var(--color-text-dim)]">
                  {source.id ?? `S${i + 1}`}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="break-words font-medium text-white">{source.title}</div>
                  <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[var(--color-text-dim)]">
                    {domain && <span className="break-all">{domain}</span>}
                    {kind && <span>{kind}</span>}
                    <span>Published: {published ?? "Not available"}</span>
                    {retrieved && <span>Retrieved: {retrieved}</span>}
                  </div>
                  {!compact && source.snippet && (
                    <p className="mt-1 break-words text-[var(--color-text-dim)]">{source.snippet}</p>
                  )}
                </div>
                {href && (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 rounded-md border border-white/10 px-2 py-1 text-[11px] text-white hover:bg-white/10"
                  >
                    Open ↗
                  </a>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

/** Banner shown above research results so evidence-backed research is never confused
 * with model-generated text, and failures are stated plainly. */
export function ResearchStatusBanner({
  status,
  note,
}: {
  status: string | undefined
  note: string | undefined
}) {
  if (status === "live") {
    return (
      <div className="mb-4 rounded-lg bg-emerald-500/10 px-4 py-2 text-xs text-emerald-300">
        ✓ Live research — findings below are backed by the retrieved sources. {note}
      </div>
    )
  }
  if (status === "unavailable") {
    return (
      <div className="mb-4 rounded-lg bg-amber-500/10 px-4 py-2 text-xs text-amber-300">
        ⚠ Live research is temporarily unavailable. Please try again later.
      </div>
    )
  }
  if (status === "no_results") {
    return (
      <div className="mb-4 rounded-lg bg-amber-500/10 px-4 py-2 text-xs text-amber-300">
        ⚠ Insufficient reliable evidence was retrieved for this research.
      </div>
    )
  }
  if (status === "background_only") {
    return (
      <div className="mb-4 rounded-lg bg-amber-500/10 px-4 py-2 text-xs text-amber-300">
        ⚠ Not live research — general background knowledge only. Do not treat as current market data.
      </div>
    )
  }
  return null
}
