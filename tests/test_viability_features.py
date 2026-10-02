from __future__ import annotations

from app.startup.profile import ProfileUpdate
from app.startup.viability_features import derive_features


def test_no_data_returns_midpoint_defaults():
    features = derive_features(profile=ProfileUpdate(), market=None, competitor=None, financial=None)
    assert all(v == 50.0 for v in features.values())


def test_market_research_shifts_demand_and_growth():
    market = {
        "opportunities": ["a", "b"],
        "trends": ["x", "y"],
        "risks": [],
    }
    features = derive_features(profile=ProfileUpdate(), market=market, competitor=None, financial=None)
    assert features["market_demand"] > 50.0
    assert features["growth_potential"] > 50.0


def test_no_named_competitors_lowers_competition_score():
    competitor = {"competitors": []}
    features = derive_features(profile=ProfileUpdate(), market=None, competitor=competitor, financial=None)
    assert features["competition"] < 50.0


def test_many_competitors_raises_competition_score():
    competitor = {"competitors": [{"name": f"c{i}"} for i in range(5)]}
    features = derive_features(profile=ProfileUpdate(), market=None, competitor=competitor, financial=None)
    assert features["competition"] > 50.0


def test_financial_margin_drives_business_model_strength():
    financial = {"gross_margin_pct": 80.0, "monthly_operating_cost": 500}
    features = derive_features(profile=ProfileUpdate(), market=None, competitor=None, financial=financial)
    assert features["business_model_strength"] > 50.0
    assert features["startup_cost"] == 85.0


def test_profile_specificity_raises_customer_accessibility():
    profile = ProfileUpdate(target_customer="Engineering students", geography="India")
    features = derive_features(profile=profile, market=None, competitor=None, financial=None)
    assert features["customer_accessibility"] == 70.0
