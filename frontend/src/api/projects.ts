import { apiDelete, apiGet, apiPost, apiPut } from "./client"

export interface Project {
  id: string
  user_id: string
  name: string
  description: string | null
  industry: string | null
  stage: string | null
  target_customer: string | null
  geography: string | null
  business_model: string | null
  problem: string | null
  solution: string | null
  budget: string | null
  goals: string | null
  status: string
  archived: boolean
  created_at: string
  updated_at: string
  last_active_at: string
}

export interface ProjectInput {
  name: string
  description?: string
  industry?: string
  stage?: string
  target_customer?: string
  geography?: string
  business_model?: string
  problem?: string
  solution?: string
  budget?: string
  goals?: string
}

export function listProjects(): Promise<Project[]> {
  return apiGet("/api/v1/projects")
}

export function createProject(input: ProjectInput): Promise<Project> {
  return apiPost("/api/v1/projects", input)
}

export function getProject(id: string): Promise<Project> {
  return apiGet(`/api/v1/projects/${id}`)
}

export function updateProject(
  id: string,
  input: Partial<ProjectInput> & { status?: string; archived?: boolean },
): Promise<Project> {
  return apiPut(`/api/v1/projects/${id}`, input)
}

export function deleteProject(id: string): Promise<void> {
  return apiDelete(`/api/v1/projects/${id}`)
}
