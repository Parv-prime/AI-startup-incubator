import { useEffect, useState } from "react"
import { motion } from "motion/react"
import { Card, SectionTitle, EmptyState, Badge, priorityTone } from "../components/Card"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"
import { generateReport, getLatestReport } from "../api/projectData"
import type { ReportResponse } from "../api/types"

export function Report() {
  const { projectId } = useProjectWorkspace()
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getLatestReport(projectId)
      .then((result) => {
        if (!cancelled) setReport(result)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [projectId])

  const generate = async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const result = await generateReport(projectId)
      setReport(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report.")
    } finally {
      setLoading(false)
    }
  }

  if (!projectId) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <EmptyState title="No startup yet" hint="Talk to your AI Co-Founder first to build a profile." />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-6">
      <div className="mb-4 flex items-center justify-between">
        <SectionTitle subtitle="Assembled from everything the agent has gathered for this startup.">
          Startup Report
        </SectionTitle>
        <motion.button
          onClick={generate}
          disabled={loading}
          whileHover={{ scale: loading ? 1 : 1.03 }}
          whileTap={{ scale: loading ? 1 : 0.97 }}
          className="btn-primary h-fit rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Generating…" : report ? "Regenerate" : "Generate report"}
        </motion.button>
      </div>

      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

      {!report ? (
        <EmptyState title="No report yet" hint='Click "Generate report" to assemble the latest findings.' />
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4"
        >
          <Card>
            <SectionTitle>Executive Summary</SectionTitle>
            <p className="text-sm text-white">{report.executive_summary}</p>
          </Card>

          {report.viability && (
            <Card>
              <SectionTitle>Viability</SectionTitle>
              <p className="text-sm text-white">
                {report.viability.score}/100 — {report.viability.classification}
              </p>
            </Card>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <SectionTitle>Risks</SectionTitle>
              <BulletList items={report.risks} tone="text-red-300" />
            </Card>
            <Card>
              <SectionTitle>Opportunities</SectionTitle>
              <BulletList items={report.opportunities} tone="text-emerald-300" />
            </Card>
          </div>

          <Card>
            <SectionTitle>Recommendations</SectionTitle>
            {report.recommendations.length === 0 ? (
              <p className="text-sm text-[var(--color-text-dim)]">None yet.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {report.recommendations.map((rec, i) => (
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

          <Card>
            <SectionTitle>Next Steps</SectionTitle>
            <BulletList items={report.next_steps} />
          </Card>

          <p className="text-center text-xs text-[var(--color-text-dim)]">
            Generated {new Date(report.generated_at).toLocaleString()}
          </p>
        </motion.div>
      )}
    </div>
  )
}

function BulletList({ items, tone }: { items: string[]; tone?: string }) {
  if (!items.length) return <p className="text-sm text-[var(--color-text-dim)]">None.</p>
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
