import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import * as projectsApi from "../api/projects"
import { useAuth } from "./AuthContext"

interface ProjectsState {
  projects: projectsApi.Project[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  createProject: (input: projectsApi.ProjectInput) => Promise<projectsApi.Project>
  updateProject: (
    id: string,
    input: Partial<projectsApi.ProjectInput> & { status?: string; archived?: boolean },
  ) => Promise<projectsApi.Project>
  deleteProject: (id: string) => Promise<void>
}

const ProjectsContext = createContext<ProjectsState | null>(null)

export function ProjectsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [projects, setProjects] = useState<projectsApi.Project[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!user) {
      setProjects([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      setProjects(await projectsApi.listProjects())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects.")
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const createProject = useCallback(async (input: projectsApi.ProjectInput) => {
    const project = await projectsApi.createProject(input)
    setProjects((prev) => [project, ...prev])
    return project
  }, [])

  const updateProject = useCallback(
    async (id: string, input: Partial<projectsApi.ProjectInput> & { status?: string; archived?: boolean }) => {
      const updated = await projectsApi.updateProject(id, input)
      setProjects((prev) => prev.map((p) => (p.id === id ? updated : p)))
      return updated
    },
    [],
  )

  const deleteProject = useCallback(async (id: string) => {
    await projectsApi.deleteProject(id)
    setProjects((prev) => prev.filter((p) => p.id !== id))
  }, [])

  const value = useMemo(
    () => ({ projects, loading, error, refresh, createProject, updateProject, deleteProject }),
    [projects, loading, error, refresh, createProject, updateProject, deleteProject],
  )

  return <ProjectsContext.Provider value={value}>{children}</ProjectsContext.Provider>
}

export function useProjects(): ProjectsState {
  const ctx = useContext(ProjectsContext)
  if (!ctx) throw new Error("useProjects must be used within ProjectsProvider")
  return ctx
}
