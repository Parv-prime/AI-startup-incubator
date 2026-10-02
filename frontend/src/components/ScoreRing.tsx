import { motion, useMotionValue, useTransform, animate } from "motion/react"
import { useEffect, useState } from "react"

const CIRCUMFERENCE = 2 * Math.PI * 54

export function ScoreRing({ score, classification }: { score: number; classification: string }) {
  const progress = useMotionValue(0)
  const [display, setDisplay] = useState(0)
  const dashoffset = useTransform(progress, (v) => CIRCUMFERENCE * (1 - v / 100))

  useEffect(() => {
    const controls = animate(progress, score, {
      duration: 1.1,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(Math.round(v)),
    })
    return () => controls.stop()
  }, [score, progress])

  const color =
    classification === "High Potential"
      ? "#4fd1c5"
      : classification === "Moderate Potential"
        ? "#f6ad55"
        : "#fc8181"

  const tone =
    classification === "High Potential"
      ? "bg-emerald-500/15 text-emerald-300"
      : classification === "Moderate Potential"
        ? "bg-amber-500/15 text-amber-300"
        : "bg-red-500/15 text-red-300"

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative h-[140px] w-[140px]">
        <svg width="140" height="140" viewBox="0 0 120 120" className="-rotate-90">
          <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
          <motion.circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            style={{ strokeDashoffset: dashoffset }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-white">{display}</span>
          <span className="text-xs text-[var(--color-text-dim)]">/ 100</span>
        </div>
      </div>
      <span className={`rounded-full px-3 py-1 text-sm font-medium ${tone}`}>{classification}</span>
    </div>
  )
}
