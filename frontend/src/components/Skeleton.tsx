import { motion } from "motion/react"

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <motion.div
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      className={`rounded-lg bg-white/10 ${className}`}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  )
}
