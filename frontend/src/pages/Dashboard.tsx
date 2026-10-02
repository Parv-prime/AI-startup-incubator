import { Link } from "react-router-dom"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"
import { Card, SectionTitle, EmptyState, Badge, priorityTone } from "../components/Card"
import { ScoreRing } from "../components/ScoreRing"

export function Dashboard() {
  const { profile, analysis, viability, recommendations, projectId } = useProjectWorkspace()

  if (!projectId) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          title="No startup yet"
          hint="Talk to your AI Co-Founder about your idea to populate the command center."
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-6">
      <SectionTitle subtitle="A live snapshot of everything your AI co-founder has learned.">
        {profile?.startup_name || "Startup Command Center"}
      </SectionTitle>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-1" delay={0}>
          <div className="text-xs uppercase tracking-wide text-[var(--color-text-dim)]">Profile</div>
          <dl className="mt-3 flex flex-col gap-2 text-sm">
            <Field label="Industry" value={profile?.industry} />
            <Field label="Stage" value={profile?.startup_stage} />
            <Field label="Target customer" value={profile?.target_customer} />
            <Field label="Geography" value={profile?.geography} />
            <Field label="Business model" value={profile?.business_model} />
          </dl>
        </Card>

        <Card className="flex flex-col items-center justify-center md:col-span-1" delay={0.05}>
          <div className="mb-2 text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
            Viability
          </div>
          {viability ? (
            <ScoreRing score={viability.score} classification={viability.classification} />
          ) : (
            <p className="text-center text-sm text-[var(--color-text-dim)]">
              Ask your co-founder to evaluate the startup to see a score.
            </p>
          )}
        </Card>

        <Card className="md:col-span-1" delay={0.1}>
          <div className="text-xs uppercase tracking-wide text-[var(--color-text-dim)]">
            Status
          </div>
          <ul className="mt-3 flex flex-col gap-2 text-sm">
            <StatusRow label="Market research" done={!!analysis?.market_research} to={`/projects/${projectId}/market`} />
            <StatusRow label="Competitor research" done={!!analysis?.competitor_research} to={`/projects/${projectId}/competitors`} />
            <StatusRow label="Financial analysis" done={!!analysis?.financial_analysis} to={`/projects/${projectId}/financial`} />
            <StatusRow label="Viability score" done={!!viability} to={`/projects/${projectId}/viability`} />
          </ul>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card delay={0.15}>
          <SectionTitle>Opportunities</SectionTitle>
          <List items={analysis?.market_research?.opportunities} empty="No market research yet." />
        </Card>
        <Card delay={0.2}>
          <SectionTitle>Risks</SectionTitle>
          <List items={analysis?.market_research?.risks} empty="No market research yet." />
        </Card>
      </div>

      <Card className="mt-4" delay={0.25}>
        <SectionTitle>Recent AI recommendations</SectionTitle>
        {recommendations.length === 0 ? (
          <p className="text-sm text-[var(--color-text-dim)]">
            Ask your co-founder to evaluate the startup for recommendations.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-3">
                <Badge tone={priorityTone(rec.priority)}>{rec.priority}</Badge>
                <div>
                  <div className="text-sm font-medium text-white">{rec.title}</div>
                  <div className="text-sm text-[var(--color-text-dim)]">{rec.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-[var(--color-text-dim)]">{label}</dt>
      <dd className="text-right text-white">{value || "—"}</dd>
    </div>
  )
}

function StatusRow({ label, done, to }: { label: string; done: boolean; to: string }) {
  return (
    <li>
      <Link to={to} className="flex items-center justify-between rounded-lg px-1 py-1 hover:bg-white/5">
        <span className="text-[var(--color-text-dim)]">{label}</span>
        <span className={done ? "text-emerald-300" : "text-[var(--color-text-dim)]"}>
          {done ? "Done" : "Pending"}
        </span>
      </Link>
    </li>
  )
}

function List({ items, empty }: { items?: string[]; empty: string }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-[var(--color-text-dim)]">{empty}</p>
  }
  return (
    <ul className="flex flex-col gap-2 text-sm text-[var(--color-text-dim)]">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2">
          <span className="text-[var(--color-accent-2)]">•</span>
          {item}
        </li>
      ))}
    </ul>
  )
}
