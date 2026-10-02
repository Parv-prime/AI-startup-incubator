import type { ReactNode } from "react"
import { motion } from "motion/react"

export function Card({
  children,
  className = "",
  delay = 0,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay, ease: "easeOut" }}
      className={`card card-interactive p-5 ${className}`}
    >
      {children}
    </motion.div>
  )
}

export function SectionTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div className="mb-4 flex gap-3">
      <span
        className="mt-1.5 h-4 w-1 shrink-0 rounded-full"
        style={{ background: "var(--gradient-accent)" }}
      />
      <div>
        <h2 className="text-lg font-semibold text-white">{children}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-[var(--color-text-dim)]">{subtitle}</p>}
      </div>
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="card flex flex-col items-center justify-center gap-2 p-10 text-center">
      <div className="text-2xl">✦</div>
      <div className="font-medium text-white">{title}</div>
      <div className="max-w-sm text-sm text-[var(--color-text-dim)]">{hint}</div>
    </div>
  )
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "high" | "medium" | "low" }) {
  const tones: Record<string, string> = {
    default: "bg-white/10 text-white",
    high: "bg-red-500/15 text-red-300",
    medium: "bg-amber-500/15 text-amber-300",
    low: "bg-emerald-500/15 text-emerald-300",
  }
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}

export function priorityTone(priority: string): "high" | "medium" | "low" {
  if (priority === "High") return "high"
  if (priority === "Medium") return "medium"
  return "low"
}
