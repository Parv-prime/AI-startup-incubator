from __future__ import annotations

from ml import predictor


def test_model_file_exists():
    assert predictor.is_available()


def test_prediction_in_range_and_shape():
    result = predictor.predict(
        {
            "market_demand": 80,
            "competition": 40,
            "problem_severity": 70,
            "customer_accessibility": 60,
            "business_model_strength": 65,
            "startup_cost": 75,
            "scalability": 70,
            "growth_potential": 80,
        }
    )
    assert 0 <= result["score"] <= 100
    assert result["classification"] in {"High Potential", "Moderate Potential", "Low Potential"}
    assert set(result["factors"]) == set(predictor.FEATURES)
    assert set(result["feature_importance"]) == set(predictor.FEATURES)
    assert result["model_version"]


def test_missing_features_default_to_midpoint():
    result = predictor.predict({"market_demand": 90})
    assert result["factors"]["competition"] == 50.0
    assert 0 <= result["score"] <= 100


def test_classification_thresholds():
    assert predictor.classify(85) == "High Potential"
    assert predictor.classify(65) == "Moderate Potential"
    assert predictor.classify(30) == "Low Potential"
