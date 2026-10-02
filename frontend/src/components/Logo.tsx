export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <path
        d="M12 2C12 7.523 7.523 12 2 12C7.523 12 12 16.477 12 22C12 16.477 16.477 12 22 12C16.477 12 12 7.523 12 2Z"
        fill="currentColor"
      />
    </svg>
  )
}

export function LogoBadge({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-lg text-[#08090d] ${className}`}
      style={{ width: size, height: size, background: "var(--gradient-accent)" }}
    >
      <LogoMark className="h-[55%] w-[55%]" />
    </div>
  )
}
