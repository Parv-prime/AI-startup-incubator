export interface StartupProfile {
  startup_name: string | null
  industry: string | null
  problem: string | null
  solution: string | null
  target_customer: string | null
  geography: string | null
  business_model: string | null
  startup_stage: string | null
  budget: string | null
  goals: string | null
}

export interface ToolActivity {
  tool_name: string
  status: "started" | "completed" | "failed"
  message: string
  duration_ms: number | null
}

export interface Source {
  id?: string
  title: string
  url: string | null
  domain?: string | null
  snippet?: string | null
  source_type: string
  source_kind?: string | null
  source_date?: string | null
  retrieved_at: string | null
  provider?: string | null
}

export type ResearchStatus = "live" | "no_results" | "unavailable" | "background_only"

export interface ResearchFinding {
  claim: string
  type: "evidence" | "derived"
  evidence: string
  source_ids: string[]
  source_title: string | null
  source_url: string | null
  source_date: string | null
}

export interface Recommendation {
  title: string
  description: string
  priority: "High" | "Medium" | "Low"
  category: string
}

export interface ViabilityResponse {
  score: number
  classification: "High Potential" | "Moderate Potential" | "Low Potential"
  factors: Record<string, number>
  feature_importance: Record<string, number>
  model_version: string
}

export interface Competitor {
  name: string
  website?: string | null
  website_verified?: boolean
  product: string
  target_audience: string
  pricing: string | null
  pricing_verified?: boolean
  features?: string[]
  geography?: string | null
  business_model?: string | null
  strengths: string[]
  weaknesses: string[]
  positioning: string
  source_ids?: string[]
  source_urls?: string[]
  source?: string | null
}

export interface MarketResearch {
  data_available: boolean
  target_market: string
  demand_summary: string
  customer_segments: string[]
  trends: string[]
  opportunities: string[]
  risks: string[]
  sources: Source[]
  note: string
  research_status?: ResearchStatus
  basis?: "retrieved_evidence" | "background_knowledge" | "none"
  summary?: string
  key_findings?: ResearchFinding[]
  analysis_basis?: string
  limitations?: string[]
  retrieved_at?: string | null
}

export interface CompetitorResearch {
  data_available: boolean
  competitors: Competitor[]
  differentiation_opportunity: string
  sources: Source[]
  note: string
  research_status?: ResearchStatus
  analysis_basis?: string
  limitations?: string[]
  retrieved_at?: string | null
}

export interface CostComponent {
  name: string
  amount: number
}

export interface FinancialAnalysis {
  currency?: string
  cost_data_available?: boolean
  note?: string
  sources?: Source[]
  initial_cost: number
  initial_cost_components?: CostComponent[]
  monthly_operating_cost: number
  monthly_cost_components?: CostComponent[]
  monthly_revenue: number | null
  gross_profit: number | null
  gross_margin_pct: number | null
  monthly_profit_loss: number | null
  break_even_customers: number | null
  break_even_revenue: number | null
  runway_months: number | null
  unit_economics: {
    price_per_customer: number
    variable_cost_per_customer: number
    contribution_margin: number
    contribution_margin_pct: number | null
  }
}

export interface AnalysisResponse {
  market_research: MarketResearch | null
  competitor_research: CompetitorResearch | null
  financial_analysis: FinancialAnalysis | null
}

export interface ReportResponse {
  generated_at: string
  executive_summary: string
  profile: StartupProfile
  market_analysis: MarketResearch | null
  competitor_analysis: CompetitorResearch | null
  financial_analysis: FinancialAnalysis | null
  viability: ViabilityResponse | null
  risks: string[]
  opportunities: string[]
  recommendations: Recommendation[]
  next_steps: string[]
}

export interface HealthResponse {
  status: string
  version: string
  model_runtime: string
  model_name: string
  llm_status: string
  database_status: string
  ml_model_status: string
  research_status?: string
  research_providers?: string[]
}
