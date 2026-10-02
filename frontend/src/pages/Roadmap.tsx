import { motion } from "motion/react"
import { Card, SectionTitle } from "../components/Card"
import { useProjectWorkspace } from "../state/ProjectWorkspaceContext"

const STAGES = ["Idea", "Validation", "MVP", "Launch", "Traction", "Growth"]

function currentStageIndex(stage: string | null | undefined): number {
  if (!stage) return 0
  const normalized = stage.toLowerCase()
  const idx = STAGES.findIndex((s) => normalized.includes(s.toLowerCase()))
  return idx === -1 ? 0 : idx
}

export function Roadmap() {
  const { profile } = useProjectWorkspace()
  const activeIndex = currentStageIndex(profile?.startup_stage)

  return (
    <div className="mx-auto max-w-3xl px-8 py-6">
      <SectionTitle subtitle="Where this startup sits in its lifecycle. Stages are not executed automatically.">
        Roadmap
      </SectionTitle>

      <Card>
        <div className="flex flex-col gap-1">
          {STAGES.map((stage, i) => (
            <motion.div
              key={stage}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: i * 0.06 }}
              className="flex items-center gap-4 py-3"
            >
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold ${
                    i < activeIndex
                      ? "border-[var(--color-accent-2)] bg-[var(--color-accent-2)]/20 text-[var(--color-accent-2)]"
                      : i === activeIndex
                        ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                        : "border-white/10 text-[var(--color-text-dim)]"
                  }`}
                >
                  {i + 1}
                </div>
                {i < STAGES.length - 1 && (
                  <div
                    className={`h-8 w-px ${i < activeIndex ? "bg-[var(--color-accent-2)]" : "bg-white/10"}`}
                  />
                )}
              </div>
              <div>
                <div
                  className={`text-sm font-medium ${
                    i === activeIndex ? "text-white" : "text-[var(--color-text-dim)]"
                  }`}
                >
                  {stage}
                </div>
                {i === activeIndex && (
                  <div className="text-xs text-[var(--color-accent-2)]">Current stage</div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </Card>
    </div>
  )
}
