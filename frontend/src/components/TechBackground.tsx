import { motion } from "motion/react"

const NODES = [
  { x: 60, y: 80 }, { x: 180, y: 140 }, { x: 120, y: 260 }, { x: 260, y: 60 },
  { x: 320, y: 220 }, { x: 420, y: 100 }, { x: 480, y: 260 }, { x: 400, y: 340 },
  { x: 560, y: 180 }, { x: 620, y: 320 }, { x: 700, y: 90 }, { x: 740, y: 240 },
  { x: 220, y: 380 }, { x: 340, y: 440 }, { x: 500, y: 420 }, { x: 660, y: 420 },
  { x: 80, y: 460 }, { x: 780, y: 380 },
]

const EDGES: [number, number][] = [
  [0, 1], [1, 2], [1, 3], [3, 5], [4, 5], [4, 6], [5, 8], [6, 7], [6, 8],
  [8, 9], [8, 10], [9, 11], [10, 11], [2, 12], [12, 13], [7, 13], [13, 14],
  [14, 15], [9, 15], [11, 15], [2, 16], [12, 16], [14, 17], [15, 17],
]

export function TechBackground({ intensity = "full" }: { intensity?: "full" | "subtle" }) {
  const dim = intensity === "subtle"
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden bg-[var(--color-bg)]">
      <motion.svg
        viewBox="0 0 800 500"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 h-full w-full"
        style={{ opacity: dim ? 0.22 : 0.42 }}
        animate={{ x: [0, 12, 0], y: [0, -8, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      >
        <defs>
          <linearGradient id="edge-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#7c6cff" />
            <stop offset="1" stopColor="#4fd1c5" />
          </linearGradient>
        </defs>
        {EDGES.map(([a, b], i) => (
          <motion.line
            key={i}
            x1={NODES[a].x}
            y1={NODES[a].y}
            x2={NODES[b].x}
            y2={NODES[b].y}
            stroke="url(#edge-grad)"
            strokeWidth="1"
            initial={{ opacity: 0.15 }}
            animate={{ opacity: [0.1, 0.35, 0.1] }}
            transition={{ duration: 5 + (i % 5), repeat: Infinity, ease: "easeInOut", delay: i * 0.15 }}
          />
        ))}
        {NODES.map((n, i) => (
          <motion.circle
            key={i}
            cx={n.x}
            cy={n.y}
            r={i % 3 === 0 ? 3.5 : 2.5}
            fill={i % 2 === 0 ? "#7c6cff" : "#4fd1c5"}
            initial={{ opacity: 0.4 }}
            animate={{ opacity: [0.3, 0.9, 0.3], scale: [1, 1.3, 1] }}
            transition={{ duration: 4 + (i % 4), repeat: Infinity, ease: "easeInOut", delay: i * 0.2 }}
          />
        ))}
      </motion.svg>

      <motion.div
        className="absolute h-[30rem] w-[30rem] rounded-full blur-3xl"
        style={{ background: "var(--color-accent)", opacity: dim ? 0.12 : 0.26, top: "-12%", left: "-8%" }}
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute h-[24rem] w-[24rem] rounded-full blur-3xl"
        style={{ background: "var(--color-accent-2)", opacity: dim ? 0.1 : 0.2, bottom: "-10%", right: "-6%" }}
        animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />

      <div
        className="absolute inset-0"
        style={{
          background: dim
            ? "radial-gradient(1200px 800px at 50% 30%, transparent 0%, var(--color-bg) 88%)"
            : "radial-gradient(1000px 700px at 50% 40%, transparent 0%, var(--color-bg) 75%)",
        }}
      />
    </div>
  )
}
