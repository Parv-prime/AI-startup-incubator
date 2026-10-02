import { motion } from "motion/react"
import { Card, SectionTitle, EmptyState } from "../components/Card"
import { ScoreRing } from "../components/ScoreRing"
import { CardSkeleton } from "../components/Skeleton"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"

const FACTOR_LABELS: Record<string, string> = {
  market_demand: "Market Demand",
  competition: "Competition",
  problem_severity: "Problem Severity",
  customer_accessibility: "Customer Accessibility",
  business_model_strength: "Business Model",
  startup_cost: "Startup Cost (affordability)",
  scalability: "Scalability",
  growth_potential: "Growth Potential",
}

export function Viability() {
  const { viability, projectId, loading } = useProjectWorkspace()

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-6">
        <CardSkeleton />
        <div className="mt-4">
          <CardSkeleton />
        </div>
      </div>
    )
  }

  if (!projectId || !viability) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          title="No viability score yet"
          hint='Ask your AI Co-Founder to "evaluate my startup" to generate a score.'
        />
      </div>
    )
  }

  const sortedFactors = Object.entries(viability.factors).sort((a, b) => b[1] - a[1])

  return (
    <div className="mx-auto max-w-3xl px-8 py-6">
      <SectionTitle subtitle="An educational decision-support estimate — not a prediction of real-world success.">
        Startup Viability
      </SectionTitle>

      <Card className="flex flex-col items-center py-8">
        <ScoreRing score={viability.score} classification={viability.classification} />
        <p className="mt-4 max-w-md text-center text-sm text-[var(--color-text-dim)]">
          Model {viability.model_version} weighed the factors below to estimate this score.
        </p>
      </Card>

      <Card className="mt-4">
        <SectionTitle>Factor breakdown</SectionTitle>
        <div className="flex flex-col gap-3">
          {sortedFactors.map(([key, value], i) => (
            <div key={key}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-white">{FACTOR_LABELS[key] ?? key}</span>
                <span className="text-[var(--color-text-dim)]">{value.toFixed(0)}/100</span>
              </div>
              <div className="h-2 w-full rounded-full bg-white/5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${value}%` }}
                  transition={{ duration: 0.6, delay: i * 0.05, ease: "easeOut" }}
                  className="h-2 rounded-full bg-gradient-to-r from-[var(--color-accent)] to-[var(--color-accent-2)]"
                />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
