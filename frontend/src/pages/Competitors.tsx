import { Card, SectionTitle, EmptyState } from "../components/Card"
import { CardSkeleton } from "../components/Skeleton"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"

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

      {data.competitors.length === 0 ? (
        <Card>
          <p className="text-sm text-[var(--color-text-dim)]">
            No confidently-known competitors were identified for this idea.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {data.competitors.map((c, i) => (
            <Card key={c.name} delay={i * 0.05}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-base font-semibold text-white">{c.name}</div>
                  <div className="text-sm text-[var(--color-text-dim)]">{c.product}</div>
                </div>
                {c.pricing && (
                  <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs text-white">
                    {c.pricing}
                  </span>
                )}
              </div>
              <p className="mt-3 text-sm text-white">{c.positioning}</p>
              <p className="mt-1 text-xs text-[var(--color-text-dim)]">
                Target: {c.target_audience}
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="mb-1 text-xs uppercase tracking-wide text-emerald-300">
                    Strengths
                  </div>
                  <Bullets items={c.strengths} />
                </div>
                <div>
                  <div className="mb-1 text-xs uppercase tracking-wide text-red-300">
                    Weaknesses
                  </div>
                  <Bullets items={c.weaknesses} />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Card className="mt-4" delay={0.2}>
        <SectionTitle>Differentiation opportunity</SectionTitle>
        <p className="text-sm text-white">{data.differentiation_opportunity}</p>
      </Card>
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
