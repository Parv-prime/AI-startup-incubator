"""Deterministic financial calculations. No LLM involvement — Section 37."""

from __future__ import annotations


def compute_financials(
    *,
    initial_cost: float,
    monthly_operating_cost: float,
    price_per_customer: float,
    variable_cost_per_customer: float = 0.0,
    customers: float | None = None,
    cash_on_hand: float | None = None,
    initial_cost_components: list[dict] | None = None,
    monthly_cost_components: list[dict] | None = None,
) -> dict:
    if initial_cost_components:
        initial_cost = round(sum(c["amount"] for c in initial_cost_components), 2)
    if monthly_cost_components:
        monthly_operating_cost = round(sum(c["amount"] for c in monthly_cost_components), 2)

    contribution_margin = price_per_customer - variable_cost_per_customer
    contribution_margin_pct = (
        (contribution_margin / price_per_customer) * 100 if price_per_customer > 0 else None
    )

    monthly_revenue = price_per_customer * customers if customers is not None else None
    gross_profit = (
        contribution_margin * customers if customers is not None else None
    )
    monthly_profit_loss = (
        gross_profit - monthly_operating_cost if gross_profit is not None else None
    )

    break_even_customers = (
        monthly_operating_cost / contribution_margin if contribution_margin > 0 else None
    )
    break_even_revenue = (
        break_even_customers * price_per_customer if break_even_customers is not None else None
    )

    runway_months = None
    if cash_on_hand is not None and monthly_profit_loss is not None:
        if monthly_profit_loss < 0:
            runway_months = round(cash_on_hand / abs(monthly_profit_loss), 1)
        else:
            runway_months = None  # profitable: no burn-based runway limit

    return {
        "currency": "INR",
        "initial_cost": initial_cost,
        "initial_cost_components": initial_cost_components or [],
        "monthly_operating_cost": monthly_operating_cost,
        "monthly_cost_components": monthly_cost_components or [],
        "monthly_revenue": _round_or_none(monthly_revenue),
        "gross_profit": _round_or_none(gross_profit),
        "gross_margin_pct": _round_or_none(contribution_margin_pct),
        "monthly_profit_loss": _round_or_none(monthly_profit_loss),
        "break_even_customers": (
            round(break_even_customers, 1) if break_even_customers is not None else None
        ),
        "break_even_revenue": _round_or_none(break_even_revenue),
        "runway_months": runway_months,
        "unit_economics": {
            "price_per_customer": price_per_customer,
            "variable_cost_per_customer": variable_cost_per_customer,
            "contribution_margin": round(contribution_margin, 2),
            "contribution_margin_pct": _round_or_none(contribution_margin_pct),
        },
    }


def _round_or_none(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None
