"""One-off generator for the synthetic startup-viability training dataset.

Not part of the runtime app. Re-run only if the dataset needs to be regenerated;
the checked-in CSV at ml/data/startup_viability.csv is what training actually uses.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

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

# Weights express a plausible (not authoritative) relationship between each
# 0-100 factor and overall viability. "competition" is inverted at use-time
# below (higher competition intensity hurts viability).
WEIGHTS = {
    "market_demand": 0.20,
    "competition": -0.10,
    "problem_severity": 0.15,
    "customer_accessibility": 0.12,
    "business_model_strength": 0.18,
    "startup_cost": 0.08,  # already an affordability score: higher = more feasible
    "scalability": 0.12,
    "growth_potential": 0.15,
}


def make_row(rng: np.random.Generator) -> dict[str, float]:
    values = {name: float(rng.integers(5, 96)) for name in FEATURES}
    score = sum(values[name] * weight for name, weight in WEIGHTS.items())
    score = score + rng.normal(0, 5)  # measurement noise
    score = max(0.0, min(100.0, score))
    values["viability_score"] = round(score, 2)
    return values


def main() -> None:
    rng = np.random.default_rng(42)
    rows = [make_row(rng) for _ in range(300)]
    out_path = Path(__file__).parent / "startup_viability.csv"
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FEATURES + ["viability_score"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
