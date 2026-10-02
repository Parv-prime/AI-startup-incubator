import { Link, useNavigate } from "react-router-dom"
import { Card, SectionTitle, EmptyState } from "../components/Card"
import { TechBackground } from "../components/TechBackground"
import { useProjects } from "../state/ProjectsContext"
import { useAuth } from "../state/AuthContext"

export function Projects() {
  const { projects, loading, error, deleteProject } = useProjects()
  const { logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="relative mx-auto min-h-full max-w-4xl px-8 py-6">
      <TechBackground intensity="subtle" />
      <div className="mb-4 flex items-center justify-between">
        <SectionTitle subtitle="Each project is an isolated workspace with its own AI co-founder, memory, and data.">
          My Projects
        </SectionTitle>
        <div className="flex gap-2">
          <Link
            to="/projects/new"
            className="btn-primary h-fit rounded-lg px-4 py-2 text-sm font-medium text-white"
          >
            + New Project
          </Link>
          <button
            onClick={logout}
            className="h-fit rounded-lg border border-white/10 px-4 py-2 text-sm text-white hover:bg-white/5"
          >
            Logout
          </button>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

      {loading ? (
        <p className="text-sm text-[var(--color-text-dim)]">Loading…</p>
      ) : projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          hint='Click "+ New Project" to start your first startup workspace.'
        />
      ) : (
        <div className="flex flex-col gap-3">
          {projects.map((project, i) => (
            <Card key={project.id} delay={i * 0.04}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-base font-semibold text-white">{project.name}</div>
                  <div className="text-sm text-[var(--color-text-dim)]">
                    {[project.industry, project.business_model].filter(Boolean).join(" / ") || "No profile yet"}
                  </div>
                  <div className="mt-1 text-xs text-[var(--color-text-dim)]">
                    {project.status} · Last updated {new Date(project.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    onClick={() => navigate(`/projects/${project.id}/chat`)}
                    className="rounded-lg bg-white/10 px-3 py-1.5 text-sm text-white hover:bg-white/20"
                  >
                    Open
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete "${project.name}"? This cannot be undone.`)) {
                        void deleteProject(project.id)
                      }
                    }}
                    className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-[var(--color-text-dim)] hover:bg-white/5 hover:text-red-300"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
