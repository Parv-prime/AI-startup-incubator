import { AnimatePresence, motion } from "motion/react"
import type { ToolActivity } from "../api/types"

export function ToolActivityList({ items }: { items: ToolActivity[] }) {
  if (!items.length) return null
  const isMultiStep = items.length >= 3

  if (isMultiStep) {
    return (
      <div className="flex flex-col gap-2.5">
        {items.map((item, i) => (
          <div key={`${item.tool_name}-${i}`} className="flex items-center gap-2.5">
            <div className="relative flex h-4 w-4 shrink-0 items-center justify-center">
              {item.status === "completed" ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", bounce: 0.35, visualDuration: 0.3 }}
                  className="flex h-4 w-4 items-center justify-center rounded-full"
                  style={{ background: "var(--gradient-accent, var(--color-accent-2))" }}
                >
                  <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M1.5 5.2L4 7.7L8.5 2.5"
                      stroke="#08090d"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </motion.div>
              ) : item.status === "failed" ? (
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "#fc8181" }} />
              ) : (
                <motion.span
                  className="h-2.5 w-2.5 rounded-full border-2"
                  style={{ borderColor: "var(--color-accent-2)" }}
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.1, repeat: Infinity }}
                />
              )}
            </div>
            <span className="text-xs text-[var(--color-text-dim)]">{item.message}</span>
            {item.duration_ms != null && (
              <span className="text-[var(--color-text-dim)]/60 text-xs">
                {(item.duration_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      <AnimatePresence initial={false}>
        {items.map((item, i) => (
          <motion.div
            key={`${item.tool_name}-${i}`}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.18, delay: i * 0.04 }}
            className="flex items-center gap-2 text-xs text-[var(--color-text-dim)]"
          >
            <StatusDot status={item.status} />
            <span>{item.message}</span>
            {item.duration_ms != null && (
              <span className="text-[var(--color-text-dim)]/60">
                {(item.duration_ms / 1000).toFixed(1)}s
              </span>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

function StatusDot({ status }: { status: ToolActivity["status"] }) {
  const color =
    status === "completed" ? "#4fd1c5" : status === "failed" ? "#fc8181" : "#f6ad55"
  return (
    <span
      className="h-1.5 w-1.5 shrink-0 rounded-full"
      style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }}
    />
  )
}
