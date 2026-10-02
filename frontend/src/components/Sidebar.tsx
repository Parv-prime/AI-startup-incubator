import { useState } from "react"
import { Link, NavLink, useLocation, useNavigate, useParams } from "react-router-dom"
import { motion } from "motion/react"
import { useAuth } from "../state/AuthContext"
import { useProjects } from "../state/ProjectsContext"
import { LogoBadge } from "./Logo"

const NAV_ITEMS = [
  { to: "chat", label: "AI Co-Founder", icon: "✦" },
  { to: "dashboard", label: "Dashboard", icon: "▦" },
  { to: "market", label: "Market Research", icon: "◎" },
  { to: "competitors", label: "Competitors", icon: "◈" },
  { to: "financial", label: "Financial", icon: "$" },
  { to: "viability", label: "Viability", icon: "◑" },
  { to: "roadmap", label: "Roadmap", icon: "➜" },
  { to: "report", label: "Startup Report", icon: "▤" },
]

export function Sidebar() {
  const { projectId } = useParams()
  const { projects } = useProjects()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [selectorOpen, setSelectorOpen] = useState(false)

  const currentProject = projects.find((p) => p.id === projectId)

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-white/5 bg-black/20 px-3 py-5">
      <Link to="/projects" className="mb-4 flex items-center gap-2 px-2">
        <LogoBadge size={32} />
        <div>
          <div className="text-sm font-semibold leading-tight">AI Startup Incubator</div>
          <div className="text-[11px] text-[var(--color-text-dim)] leading-tight">AI Co-Founder</div>
        </div>
      </Link>

      <div className="relative mb-4">
        <button
          onClick={() => setSelectorOpen((v) => !v)}
          className="flex w-full items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-left text-sm text-white"
        >
          <span className="truncate">{currentProject?.name ?? "Select project"}</span>
          <span className="text-[var(--color-text-dim)]">▾</span>
        </button>
        {selectorOpen && (
          <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-64 overflow-y-auto rounded-lg border border-white/10 bg-[var(--color-surface-2)] p-1 shadow-xl">
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setSelectorOpen(false)
                  navigate(`/projects/${p.id}/chat`)
                }}
                className={`block w-full truncate rounded-md px-2 py-1.5 text-left text-sm ${
                  p.id === projectId ? "bg-white/10 text-white" : "text-[var(--color-text-dim)] hover:bg-white/5"
                }`}
              >
                {p.name}
              </button>
            ))}
            <Link
              to="/projects/new"
              onClick={() => setSelectorOpen(false)}
              className="mt-1 block rounded-md px-2 py-1.5 text-sm text-[var(--color-accent-2)] hover:bg-white/5"
            >
              + New Project
            </Link>
            <Link
              to="/projects"
              onClick={() => setSelectorOpen(false)}
              className="block rounded-md px-2 py-1.5 text-sm text-[var(--color-text-dim)] hover:bg-white/5"
            >
              All projects
            </Link>
          </div>
        )}
      </div>

      {projectId && (
        <nav className="flex flex-col gap-1">
          <div className="mb-1 px-2 text-[11px] uppercase tracking-wide text-[var(--color-text-dim)]">
            Current project
          </div>
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === `/projects/${projectId}/${item.to}`
            return (
              <NavLink
                key={item.to}
                to={`/projects/${projectId}/${item.to}`}
                className={`relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "text-white"
                    : "text-[var(--color-text-dim)] hover:bg-white/5 hover:text-white"
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="nav-active-pill"
                    transition={{ type: "spring", bounce: 0.2, visualDuration: 0.35 }}
                    className="absolute inset-0 rounded-lg bg-white/10"
                  />
                )}
                <span className="relative w-4 text-center text-[var(--color-accent-2)]">
                  {item.icon}
                </span>
                <span className="relative">{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      )}

      <div className="mt-auto flex flex-col gap-1">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
              isActive ? "bg-white/10 text-white" : "text-[var(--color-text-dim)] hover:bg-white/5 hover:text-white"
            }`
          }
        >
          <span className="w-4 text-center text-[var(--color-accent-2)]">⚙</span>
          Settings
        </NavLink>
        {user && (
          <div className="flex items-center justify-between rounded-lg px-3 py-2 text-xs text-[var(--color-text-dim)]">
            <span className="truncate">{user.name}</span>
            <button onClick={logout} className="shrink-0 text-white hover:underline">
              Logout
            </button>
          </div>
        )}
        <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 text-[11px] text-[var(--color-text-dim)]">
          Local model: <span className="text-white">qwen2.5:3b</span> via Ollama
        </div>
      </div>
    </aside>
  )
}
