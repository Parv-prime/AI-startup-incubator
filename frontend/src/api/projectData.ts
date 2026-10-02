import { apiGet, apiPost } from "./client"
import type { ReportResponse, ViabilityResponse } from "./types"

interface MarketResearchRow {
  id: string
  project_id: string
  data: Record<string, unknown>
  created_at: string
}

interface CompetitorRow {
  id: string
  project_id: string
  name: string
  description: string | null
  product: string | null
  pricing: string | null
  strengths: string[]
  weaknesses: string[]
  target_market: string | null
  differentiation: string | null
  source: string | null
  created_at: string
  updated_at: string
}

interface FinancialAnalysisRow {
  id: string
  project_id: string
  data: Record<string, unknown>
  created_at: string
}

interface ViabilityRow {
  id: string
  project_id: string
  score: number
  classification: string
  factors: Record<string, number>
  feature_importance: Record<string, number>
  model_version: string
  created_at: string
}

interface ReportRow {
  id: string
  project_id: string
  content: Record<string, unknown>
  generated_at: string
}

export async function getLatestMarketResearch(projectId: string) {
  const rows = await apiGet<MarketResearchRow[]>(`/api/v1/projects/${projectId}/market-research`)
  return rows[0]?.data ?? null
}

export async function getCompetitorsForDisplay(projectId: string) {
  const rows = await apiGet<CompetitorRow[]>(`/api/v1/projects/${projectId}/competitors`)
  if (rows.length === 0) return null
  return {
    data_available: true,
    competitors: rows.map((c) => ({
      name: c.name,
      product: c.product ?? "",
      target_audience: c.target_market ?? "",
      pricing: c.pricing,
      strengths: c.strengths,
      weaknesses: c.weaknesses,
      positioning: c.differentiation ?? c.description ?? "",
    })),
    differentiation_opportunity:
      rows.find((c) => c.differentiation)?.differentiation ??
      "Not enough information to identify a clear differentiation angle.",
    sources: [],
    note: "Based on the model's general background knowledge, not a live competitor lookup.",
  }
}

export async function getLatestFinancialAnalysis(projectId: string) {
  const rows = await apiGet<FinancialAnalysisRow[]>(`/api/v1/projects/${projectId}/financial`)
  return rows[0]?.data ?? null
}

export async function getViability(projectId: string): Promise<ViabilityResponse | null> {
  const row = await apiGet<ViabilityRow | null>(`/api/v1/projects/${projectId}/viability`)
  if (!row) return null
  return {
    score: row.score,
    classification: row.classification as ViabilityResponse["classification"],
    factors: row.factors,
    feature_importance: row.feature_importance,
    model_version: row.model_version,
  }
}

export interface RoadmapItem {
  id: string
  project_id: string
  phase: string | null
  title: string
  description: string | null
  priority: string
  status: string
  target_date: string | null
  dependencies: string[]
  notes: string | null
}

export function getRoadmap(projectId: string): Promise<RoadmapItem[]> {
  return apiGet(`/api/v1/projects/${projectId}/roadmap`)
}

export interface RecommendationRow {
  id: string
  title: string
  description: string
  priority: "High" | "Medium" | "Low"
  category: string
}

export function getRecommendations(projectId: string): Promise<RecommendationRow[]> {
  return apiGet(`/api/v1/projects/${projectId}/recommendations`)
}

export async function generateReport(projectId: string): Promise<ReportResponse> {
  const row = await apiPost<ReportRow>(`/api/v1/projects/${projectId}/reports`)
  return { ...(row.content as object), generated_at: row.generated_at } as ReportResponse
}

export async function getLatestReport(projectId: string): Promise<ReportResponse | null> {
  const row = await apiGet<ReportRow | null>(`/api/v1/projects/${projectId}/reports/latest`)
  if (!row) return null
  return { ...(row.content as object), generated_at: row.generated_at } as ReportResponse
}
