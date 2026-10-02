from __future__ import annotations

from app.startup.finance import compute_financials


def test_break_even_and_profit():
    result = compute_financials(
        initial_cost=5000,
        monthly_operating_cost=2000,
        price_per_customer=50,
        variable_cost_per_customer=10,
        customers=100,
        cash_on_hand=10000,
    )
    assert result["monthly_revenue"] == 5000
    assert result["gross_profit"] == 4000
    assert result["monthly_profit_loss"] == 2000
    assert result["break_even_customers"] == 50.0
    assert result["break_even_revenue"] == 2500.0
    assert result["runway_months"] is None  # profitable, no burn


def test_runway_when_losing_money():
    result = compute_financials(
        initial_cost=1000,
        monthly_operating_cost=3000,
        price_per_customer=20,
        variable_cost_per_customer=5,
        customers=10,
        cash_on_hand=6000,
    )
    assert result["monthly_profit_loss"] == -2850.0
    assert result["runway_months"] == round(6000 / 2850, 1)


def test_no_customers_yet_omits_revenue():
    result = compute_financials(
        initial_cost=1000,
        monthly_operating_cost=500,
        price_per_customer=30,
        variable_cost_per_customer=5,
    )
    assert result["monthly_revenue"] is None
    assert result["break_even_customers"] == round(500 / 25, 1)
