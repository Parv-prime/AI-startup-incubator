import { motion } from "motion/react"
import { Card, SectionTitle, EmptyState } from "../components/Card"
import { CardSkeleton } from "../components/Skeleton"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"

export function Financial() {
  const { analysis, projectId, loading } = useProjectWorkspace()
  const f = analysis?.financial_analysis

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-6">
        <div className="grid gap-4 md:grid-cols-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <div className="mt-4">
          <CardSkeleton />
        </div>
      </div>
    )
  }

  if (!projectId || !f) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState
          title="No financial analysis yet"
          hint='Ask your AI Co-Founder something like "What is my break-even point if I charge ₹500/month?"'
        />
      </div>
    )
  }

  const revenue = f.monthly_revenue ?? 0
  const cost = f.monthly_operating_cost
  const maxBar = Math.max(revenue, cost, 1)

  return (
    <div className="mx-auto max-w-4xl px-8 py-6">
      <SectionTitle>Financial Analysis</SectionTitle>
      {f.note && (
        <div
          className={`mb-4 rounded-lg px-3 py-2 text-xs ${
            f.cost_data_available
              ? "bg-emerald-500/10 text-emerald-300"
              : "bg-amber-500/10 text-amber-300"
          }`}
        >
          {f.cost_data_available ? "✓ " : "⚠ "}
          {f.note}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Metric label="Initial cost" value={money(f.initial_cost)} />
        <Metric label="Monthly cost" value={money(f.monthly_operating_cost)} />
        <Metric label="Monthly revenue" value={f.monthly_revenue != null ? money(f.monthly_revenue) : "—"} />
        <Metric
          label="Profit / Loss"
          value={f.monthly_profit_loss != null ? money(f.monthly_profit_loss) : "—"}
          tone={f.monthly_profit_loss != null ? (f.monthly_profit_loss >= 0 ? "text-emerald-300" : "text-red-300") : undefined}
        />
      </div>

      <Card className="mt-4">
        <SectionTitle>Revenue vs. Cost</SectionTitle>
        <div className="flex items-end gap-8 pt-2">
          <Bar label="Revenue" value={revenue} max={maxBar} color="#4fd1c5" />
          <Bar label="Cost" value={cost} max={maxBar} color="#fc8181" />
        </div>
      </Card>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Card delay={0.05}>
          <SectionTitle>Break-even</SectionTitle>
          <dl className="flex flex-col gap-2 text-sm">
            <Row label="Customers needed" value={f.break_even_customers != null ? f.break_even_customers.toFixed(1) : "—"} />
            <Row label="Revenue needed" value={f.break_even_revenue != null ? money(f.break_even_revenue) : "—"} />
            <Row label="Runway" value={f.runway_months != null ? `${f.runway_months} months` : "Profitable / N/A"} />
          </dl>
        </Card>
        <Card delay={0.1}>
          <SectionTitle>Unit economics</SectionTitle>
          <dl className="flex flex-col gap-2 text-sm">
            <Row label="Price / customer" value={money(f.unit_economics.price_per_customer)} />
            <Row label="Variable cost / customer" value={money(f.unit_economics.variable_cost_per_customer)} />
            <Row label="Contribution margin" value={money(f.unit_economics.contribution_margin)} />
            <Row
              label="Margin %"
              value={f.unit_economics.contribution_margin_pct != null ? `${f.unit_economics.contribution_margin_pct.toFixed(1)}%` : "—"}
            />
          </dl>
        </Card>
      </div>

      {((f.initial_cost_components?.length ?? 0) > 0 || (f.monthly_cost_components?.length ?? 0) > 0) && (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {(f.initial_cost_components?.length ?? 0) > 0 && (
            <Card delay={0.05}>
              <SectionTitle>Initial cost breakdown</SectionTitle>
              <dl className="flex flex-col gap-2 text-sm">
                {f.initial_cost_components!.map((c, i) => (
                  <Row key={i} label={c.name} value={money(c.amount)} />
                ))}
                <div className="mt-1 border-t border-white/10 pt-2">
                  <Row label="Total" value={money(f.initial_cost)} />
                </div>
              </dl>
            </Card>
          )}
          {(f.monthly_cost_components?.length ?? 0) > 0 && (
            <Card delay={0.1}>
              <SectionTitle>Monthly cost breakdown</SectionTitle>
              <dl className="flex flex-col gap-2 text-sm">
                {f.monthly_cost_components!.map((c, i) => (
                  <Row key={i} label={c.name} value={money(c.amount)} />
                ))}
                <div className="mt-1 border-t border-white/10 pt-2">
                  <Row label="Total" value={money(f.monthly_operating_cost)} />
                </div>
              </dl>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs text-[var(--color-text-dim)]">{label}</span>
      <span className={`text-xl font-semibold ${tone ?? "text-white"}`}>{value}</span>
    </Card>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-[var(--color-text-dim)]">{label}</dt>
      <dd className="text-white">{value}</dd>
    </div>
  )
}

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const heightPct = Math.max(4, (value / max) * 100)
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex h-40 w-16 items-end rounded-md bg-white/5">
        <motion.div
          initial={{ height: 0 }}
          animate={{ height: `${heightPct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="w-full rounded-md"
          style={{ backgroundColor: color }}
        />
      </div>
      <span className="text-xs text-[var(--color-text-dim)]">{label}</span>
      <span className="text-sm font-medium text-white">{money(value)}</span>
    </div>
  )
}

function money(value: number): string {
  return value.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })
}
