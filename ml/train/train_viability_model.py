"""Reproducible training script for the startup viability RandomForestRegressor.

Run manually (not on API startup):

    python ml/train/train_viability_model.py

Loads ml/data/startup_viability.csv, trains, evaluates, and writes
ml/models/viability_model.joblib + ml/models/model_metadata.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42
ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "startup_viability.csv"
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
TARGET = "viability_score"


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    missing_columns = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    df = df.dropna(subset=FEATURES + [TARGET])

    x = df[FEATURES]
    y = df[TARGET]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=RANDOM_STATE
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        random_state=RANDOM_STATE,
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "model_version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "target": TARGET,
        "n_train": len(x_train),
        "n_test": len(x_test),
        "mae": round(float(mae), 3),
        "r2": round(float(r2), 3),
        "random_state": RANDOM_STATE,
        "note": (
            "Educational decision-support model trained on a small synthetic "
            "dataset. Not a real-world startup-success predictor."
        ),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print(f"Trained on {len(x_train)} rows, tested on {len(x_test)} rows.")
    print(f"MAE={mae:.2f}  R2={r2:.3f}")
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
