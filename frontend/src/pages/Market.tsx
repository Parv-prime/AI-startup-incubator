import { Card, SectionTitle, EmptyState } from "../components/Card"
import { CardSkeleton } from "../components/Skeleton"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"

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

      <div className="mt-4 grid gap-4 md:grid-cols-2">
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

      {!market.data_available && (
        <p className="mt-4 text-xs text-[var(--color-text-dim)]">
          ⚠ This is model-based qualitative analysis, not live/current market data.
        </p>
      )}
    </div>
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
