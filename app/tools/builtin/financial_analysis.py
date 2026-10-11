from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.base import ModelProvider
from app.models.structured import generate_json
from app.startup.finance import compute_financials
from app.tools.base import BaseTool, ToolContext
from app.research.base import ResearchProvider
from app.research.evidence import UNAVAILABLE_NOTE, gather_evidence
from app.tools.permissions import PermissionLevel

_COST_SYNTHESIS_PROMPT = """You are a startup financial analyst. Using the numbered live web
sources below (real current Indian market rates), produce a realistic itemized cost breakdown in
INR for launching and running this specific startup in India.

Do not invent sources or URLs. If the sources don't clearly cover a needed cost category, you may
fill it in from your own general knowledge but you MUST prefix that component's name with
"Estimated: " so it's clear it wasn't taken from a source. Keep each list to the 3-6 most material cost components — do not pad with trivial items.

Respond with ONLY a JSON object with exactly this shape:
{
  "initial_cost_components": [{"name": string, "amount": number}],
  "monthly_cost_components": [{"name": string, "amount": number}]
}
All amounts are numbers only (INR, no currency symbols or commas)."""


class CostComponent(BaseModel):
    name: str = Field(
        description="What the cost is for, e.g. 'Cloud hosting (AWS/GCP)', 'Founder/staff salaries', "
        "'Domain + SSL', 'Marketing', 'Office/coworking rent'."
    )
    amount: float = Field(ge=0, description="Cost of this single component, in INR.")


class FinancialAnalysisInput(BaseModel):
    industry: str | None = Field(
        default=None,
        description="The startup's industry/category (e.g. 'SaaS note-taking app', 'B2B food "
        "safety compliance platform'). When set and initial_cost_components / "
        "monthly_cost_components are not both provided, this tool automatically searches the "
        "live web for real Indian market rates and builds an itemized breakdown for you — do "
        "not guess a lump-sum cost yourself when you can pass industry instead.",
    )
    initial_cost_components: list[CostComponent] = Field(
        default_factory=list,
        description="Itemized one-time setup costs in INR (e.g. domain registration, initial "
        "dev tools/licenses, incorporation fees, first equipment). When provided, initial_cost "
        "is computed as their sum instead of using the initial_cost field or auto-research.",
    )
    monthly_cost_components: list[CostComponent] = Field(
        default_factory=list,
        description="Itemized recurring monthly costs in INR (e.g. cloud hosting, SaaS "
        "subscriptions, salaries, rent, marketing spend). When provided, monthly_operating_cost "
        "is computed as their sum instead of using the monthly_operating_cost field or auto-research.",
    )
    initial_cost: float = Field(
        default=0, ge=0, description="One-time startup/setup cost in INR. Only used when "
        "initial_cost_components is empty AND industry is not set (or auto-research finds nothing)."
    )
    monthly_operating_cost: float = Field(
        default=0, ge=0, description="Recurring monthly operating cost in INR. Only used when "
        "monthly_cost_components is empty AND industry is not set (or auto-research finds nothing)."
    )
    price_per_customer: float = Field(gt=0, description="Revenue per paying customer per month, in INR.")
    variable_cost_per_customer: float = Field(
        default=0, ge=0, description="Variable cost incurred per paying customer per month, in INR."
    )
    customers: float | None = Field(
        default=None, ge=0, description="Current or projected number of paying customers."
    )
    cash_on_hand: float | None = Field(
        default=None, ge=0, description="Available cash in INR, used to estimate runway."
    )


class FinancialAnalysisOutput(BaseModel):
    currency: str
    initial_cost: float
    initial_cost_components: list[CostComponent]
    monthly_operating_cost: float
    monthly_cost_components: list[CostComponent]
    monthly_revenue: float | None
    gross_profit: float | None
    gross_margin_pct: float | None
    monthly_profit_loss: float | None
    break_even_customers: float | None
    break_even_revenue: float | None
    runway_months: float | None
    unit_economics: dict
    cost_data_available: bool
    note: str
    sources: list[dict] = Field(default_factory=list)


class FinancialAnalysisTool(BaseTool):
    name = "financial_analysis"
    description = (
        "Calculate startup financial metrics: revenue, gross margin, profit/loss, break-even "
        "point, and runway. Use for any cost/revenue/break-even/runway question. Never estimate "
        "these by hand. All monetary values are in INR. Pass 'industry' and leave the cost "
        "component lists empty to have this tool automatically research real current Indian "
        "market rates and build an itemized cost breakdown for you — only pass "
        "initial_cost_components / monthly_cost_components yourself if the founder already gave "
        "you their own real numbers."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = FinancialAnalysisInput
    output_model = FinancialAnalysisOutput

    def __init__(self, model: ModelProvider | None = None, research: ResearchProvider | None = None):
        self.model = model
        self.research = research

    async def execute(self, payload: FinancialAnalysisInput, context: ToolContext) -> dict[str, Any]:
        initial_components = [c.model_dump() for c in payload.initial_cost_components]
        monthly_components = [c.model_dump() for c in payload.monthly_cost_components]
        cost_data_available = bool(initial_components or monthly_components)
        note = "Cost components provided by the conversation." if cost_data_available else ""
        sources: list[dict] = []

        if (
            not initial_components
            and not monthly_components
            and payload.industry
            and self.model
            and self.research
        ):
            researched, note, cost_data_available, sources = await self._auto_research_costs(payload.industry)
            initial_components = researched["initial_cost_components"]
            monthly_components = researched["monthly_cost_components"]

        result = compute_financials(
            initial_cost=payload.initial_cost,
            monthly_operating_cost=payload.monthly_operating_cost,
            price_per_customer=payload.price_per_customer,
            variable_cost_per_customer=payload.variable_cost_per_customer,
            customers=payload.customers,
            cash_on_hand=payload.cash_on_hand,
            initial_cost_components=initial_components,
            monthly_cost_components=monthly_components,
        )
        result["cost_data_available"] = cost_data_available
        result["note"] = note or (
            "No industry given and no cost components provided — using the flat initial_cost / "
            "monthly_operating_cost figures as-is."
        )
        result["sources"] = sources
        return result

    async def _auto_research_costs(
        self, industry: str
    ) -> tuple[dict[str, list[dict]], str, bool, list[dict]]:
        empty = {"initial_cost_components": [], "monthly_cost_components": []}
        evidence = await gather_evidence(
            self.research,
            [
                f"{industry} startup one-time setup cost India domain incorporation tools",
                f"{industry} startup monthly operating cost India hosting salary rent",
            ],
            max_results=4,
            max_sources=6,
        )
        if evidence.status != "live":
            reason = UNAVAILABLE_NOTE if evidence.status == "unavailable" else "No cost sources were found."
            return (
                empty,
                f"{reason} No cost breakdown could be generated. Ask the founder for their real "
                "numbers, or provide initial_cost / monthly_operating_cost directly.",
                False,
                [],
            )

        parsed = await generate_json(
            self.model,
            system_prompt=_COST_SYNTHESIS_PROMPT,
            user_prompt=f"Industry: {industry}\n\nSOURCES:\n{evidence.prompt_block(max_chars_per_source=600)}\n",
        )
        sources = evidence.to_dicts()
        if parsed is None:
            return empty, "Web search succeeded but the cost breakdown could not be parsed.", False, sources

        initial = _as_components(parsed.get("initial_cost_components"))
        monthly = _as_components(parsed.get("monthly_cost_components"))
        if not initial and not monthly:
            return empty, "Web search succeeded but no cost components could be extracted.", False, sources

        return (
            {"initial_cost_components": initial, "monthly_cost_components": monthly},
            "Cost breakdown informed by live web sources for current Indian market rates; items "
            "prefixed 'Estimated:' are model estimates, not taken from a source.",
            True,
            sources,
        )


def _as_components(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        try:
            amount = float(item.get("amount", 0))
        except (TypeError, ValueError):
            continue
        if amount < 0:
            continue
        out.append({"name": str(item["name"]), "amount": amount})
    return out
