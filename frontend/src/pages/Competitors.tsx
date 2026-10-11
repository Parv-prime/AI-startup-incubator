import { Card, SectionTitle, EmptyState } from "../components/Card"
import { CardSkeleton } from "../components/Skeleton"
import { ResearchStatusBanner, SourceList } from "../components/SourceList"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"

const NOT_VERIFIED = "Not verified from available sources"

export function Competitors() {
  const { analysis, projectId, loading } = useProjectWorkspace()
  const data = analysis?.competitor_research

  if (loading) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4 px-8 py-6">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  if (!projectId || !data) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          title="No competitor research yet"
          hint='Ask your AI Co-Founder something like "Who are my competitors?"'
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-6">
      <SectionTitle subtitle={data.note}>Competitors</SectionTitle>
      <ResearchStatusBanner status={data.research_status} note={undefined} />

      {data.competitors.length === 0 ? (
        <Card>
          <p className="text-sm text-[var(--color-text-dim)]">
            No competitors could be verified from the retrieved sources.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {data.competitors.map((c, i) => (
            <Card key={c.name} delay={i * 0.05}>
              <div className="flex items-start justify-between">
                <div className="min-w-0">
                  <div className="text-base font-semibold text-white">{c.name}</div>
                  <div className="text-sm text-[var(--color-text-dim)]">{c.product}</div>
                  {c.website && (
                    <a
                      href={c.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-0.5 inline-block break-all text-xs text-[var(--color-accent-2)] hover:underline"
                    >
                      {c.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                      {c.website_verified ? " ✓ official site checked" : ""}
                    </a>
                  )}
                </div>
                {c.pricing && (
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${
                      c.pricing === NOT_VERIFIED
                        ? "bg-amber-500/10 text-amber-300"
                        : "bg-white/10 text-white"
                    }`}
                    title={c.pricing_verified ? "Price found in a retrieved source" : undefined}
                  >
                    {c.pricing === NOT_VERIFIED ? "Pricing: not verified" : c.pricing}
                  </span>
                )}
              </div>
              <p className="mt-3 text-sm text-white">{c.positioning}</p>
              <p className="mt-1 text-xs text-[var(--color-text-dim)]">
                Target: {c.target_audience}
              </p>
              {(c.geography || c.business_model) && (
                <p className="mt-1 text-xs text-[var(--color-text-dim)]">
                  {c.geography && <>Availability: {c.geography}</>}
                  {c.geography && c.business_model && " · "}
                  {c.business_model && <>Model: {c.business_model}</>}
                </p>
              )}
              {c.features && c.features.length > 0 && (
                <div className="mt-3">
                  <div className="mb-1 text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
                    Features (from sources)
                  </div>
                  <Bullets items={c.features} />
                </div>
              )}
              {c.source_ids && c.source_ids.length > 0 && (
                <p className="mt-2 font-mono text-[11px] text-[var(--color-text-dim)]">
                  Sources: {c.source_ids.join(", ")}
                </p>
              )}
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="mb-1 text-xs uppercase tracking-wide text-emerald-300">
                    Strengths (AI view)
                  </div>
                  <Bullets items={c.strengths} />
                </div>
                <div>
                  <div className="mb-1 text-xs uppercase tracking-wide text-red-300">
                    Weaknesses (AI view)
                  </div>
                  <Bullets items={c.weaknesses} />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Card className="mt-4" delay={0.2}>
        <SectionTitle subtitle="AI interpretation of the evidence above.">
          Differentiation opportunity
        </SectionTitle>
        <p className="text-sm text-white">{data.differentiation_opportunity}</p>
      </Card>

      {data.limitations && data.limitations.length > 0 && (
        <Card className="mt-4" delay={0.25}>
          <SectionTitle>Limitations</SectionTitle>
          <Bullets items={data.limitations} />
        </Card>
      )}

      {data.sources.length > 0 && (
        <Card className="mt-4" delay={0.3}>
          <SourceList sources={data.sources} />
        </Card>
      )}
    </div>
  )
}

function Bullets({ items }: { items: string[] }) {
  if (!items.length) return <p className="text-xs text-[var(--color-text-dim)]">—</p>
  return (
    <ul className="flex flex-col gap-1 text-xs text-[var(--color-text-dim)]">
      {items.map((item, i) => (
        <li key={i}>• {item}</li>
      ))}
    </ul>
  )
}
