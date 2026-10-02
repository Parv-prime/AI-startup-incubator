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
  title: string
  url: string | null
  source_type: string
  retrieved_at: string | null
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
  product: string
  target_audience: string
  pricing: string | null
  strengths: string[]
  weaknesses: string[]
  positioning: string
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
}

export interface CompetitorResearch {
  data_available: boolean
  competitors: Competitor[]
  differentiation_opportunity: string
  sources: Source[]
  note: string
}

export interface CostComponent {
  name: string
  amount: number
}

export interface FinancialAnalysis {
  currency?: string
  cost_data_available?: boolean
  note?: string
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
}
