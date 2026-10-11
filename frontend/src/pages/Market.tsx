import { Card, SectionTitle, EmptyState } from "../components/Card"
import { CardSkeleton } from "../components/Skeleton"
import { ResearchStatusBanner, SourceList } from "../components/SourceList"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"
import type { ResearchFinding } from "../api/types"

export function Market() {
  const { analysis, projectId, loading } = useProjectWorkspace()
  const market = analysis?.market_research

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-6">
        <CardSkeleton />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    )
  }

  if (!projectId || !market) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          title="No market research yet"
          hint='Ask your AI Co-Founder something like "What is the market demand for my idea?"'
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-6">
      <SectionTitle subtitle={market.note}>Market Research</SectionTitle>
      <ResearchStatusBanner status={market.research_status} note={undefined} />

      {market.summary && (
        <Card className="mb-4">
          <div className="text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
            Research summary
          </div>
          <p className="mt-1 text-sm text-white">{market.summary}</p>
        </Card>
      )}

      {market.key_findings && market.key_findings.length > 0 && (
        <Card className="mb-4" delay={0.03}>
          <SectionTitle subtitle="Each finding is backed by a retrieved source.">Key findings</SectionTitle>
          <Findings items={market.key_findings} />
        </Card>
      )}

      <Card>
        <div className="text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
          Target market
        </div>
        <p className="mt-1 text-sm text-white">{market.target_market}</p>
        <div className="mt-4 text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
          Demand
        </div>
        <p className="mt-1 text-sm text-white">{market.demand_summary}</p>
      </Card>

      {market.analysis_basis && (
        <p className="mt-6 text-xs text-[var(--color-text-dim)]">
          <span className="font-medium text-white">AI analysis</span> — {market.analysis_basis}
        </p>
      )}
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        <Card delay={0.05}>
          <SectionTitle>Customer segments</SectionTitle>
          <Bullets items={market.customer_segments} />
        </Card>
        <Card delay={0.1}>
          <SectionTitle>Trends</SectionTitle>
          <Bullets items={market.trends} />
        </Card>
        <Card delay={0.15}>
          <SectionTitle>Opportunities</SectionTitle>
          <Bullets items={market.opportunities} tone="text-emerald-300" />
        </Card>
        <Card delay={0.2}>
          <SectionTitle>Risks</SectionTitle>
          <Bullets items={market.risks} tone="text-red-300" />
        </Card>
      </div>

      {market.limitations && market.limitations.length > 0 && (
        <Card className="mt-4" delay={0.25}>
          <SectionTitle>Limitations</SectionTitle>
          <Bullets items={market.limitations} tone="text-amber-300" />
        </Card>
      )}

      {market.sources.length > 0 && (
        <Card className="mt-4" delay={0.3}>
          <SourceList sources={market.sources} />
        </Card>
      )}

      {!market.data_available && !market.research_status && (
        <p className="mt-4 text-xs text-[var(--color-text-dim)]">
          ⚠ This is model-based qualitative analysis, not live/current market data.
        </p>
      )}
    </div>
  )
}

function Findings({ items }: { items: ResearchFinding[] }) {
  return (
    <ul className="flex flex-col gap-3 text-sm">
      {items.map((f, i) => (
        <li key={i} className="border-l-2 border-white/10 pl-3">
          <div className="text-white">
            {f.claim}{" "}
            <span className="font-mono text-xs text-[var(--color-text-dim)]">
              [{f.source_ids.join(", ")}]
            </span>
            {f.type === "derived" && (
              <span className="ml-2 rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase text-[var(--color-text-dim)]">
                Derived
              </span>
            )}
          </div>
          {f.evidence && (
            <div className="mt-1 text-xs italic text-[var(--color-text-dim)]">“{f.evidence}”</div>
          )}
          <div className="mt-0.5 text-xs text-[var(--color-text-dim)]">
            {f.source_title}
            {f.source_date ? ` · ${f.source_date}` : " · Date not available"}
          </div>
        </li>
      ))}
    </ul>
  )
}

function Bullets({ items, tone }: { items: string[]; tone?: string }) {
  if (!items.length) return <p className="text-sm text-[var(--color-text-dim)]">None identified.</p>
  return (
    <ul className="flex flex-col gap-1.5 text-sm">
      {items.map((item, i) => (
        <li key={i} className={`flex gap-2 ${tone ?? "text-[var(--color-text-dim)]"}`}>
          <span>•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}
