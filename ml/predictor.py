"""Runtime prediction pipeline for the startup viability model.

Loads the trained RandomForest once (module-level cache) and exposes a small,
typed interface the `startup_viability_predictor` tool calls into. The model
is never retrained here.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "viability_model.joblib"
METADATA_PATH = ROOT / "models" / "model_metadata.json"

FEATURES = [
    "market_demand",
    "competition",
    "problem_severity",
    "customer_accessibility",
    "business_model_strength",
    "startup_cost",
    "scalability",
    "growth_potential",
]

HIGH_THRESHOLD = 80
MODERATE_THRESHOLD = 60

_model = None
_metadata: dict | None = None


class ModelNotAvailableError(RuntimeError):
    pass


def _load():
    global _model, _metadata
    if _model is None:
        if not MODEL_PATH.exists():
            raise ModelNotAvailableError(
                "Viability model not found. Run `python ml/train/train_viability_model.py` first."
            )
        _model = joblib.load(MODEL_PATH)
        _metadata = json.loads(METADATA_PATH.read_text()) if METADATA_PATH.exists() else {}
    return _model, _metadata


def is_available() -> bool:
    return MODEL_PATH.exists()


def classify(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "High Potential"
    if score >= MODERATE_THRESHOLD:
        return "Moderate Potential"
    return "Low Potential"


def predict(features: dict[str, float]) -> dict:
    model, metadata = _load()

    ordered = [float(features.get(name, 50.0)) for name in FEATURES]
    ordered = [max(0.0, min(100.0, value)) for value in ordered]

    frame = pd.DataFrame([ordered], columns=FEATURES)
    score = float(model.predict(frame)[0])
    score = max(0.0, min(100.0, score))

    importances = getattr(model, "feature_importances_", None)
    feature_importance = (
        {name: round(float(value), 4) for name, value in zip(FEATURES, importances)}
        if importances is not None
        else {}
    )

    return {
        "score": round(score, 1),
        "classification": classify(score),
        "factors": {name: value for name, value in zip(FEATURES, ordered)},
        "feature_importance": feature_importance,
        "model_version": (metadata or {}).get("model_version", "unknown"),
    }
