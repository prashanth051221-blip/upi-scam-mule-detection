"""
Scoring shared by the dashboard, the real-time demo, the tests and the
training script, so all of them use exactly the same logic.
"""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from feature_engineering import FeatureEngine, compute_features

# Models are fitted on named DataFrames but scored on plain arrays for speed; the
# column order is fixed by bundle["model_features"], so this warning is noise.
warnings.filterwarnings("ignore", message="X does not have valid feature names")

BUNDLE_PATH = Path(__file__).resolve().parent / "models" / "model_bundle.pkl"


def load_bundle(path: Path | str = BUNDLE_PATH) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)


def model_matrix(bundle: dict, X: pd.DataFrame) -> pd.DataFrame:
    """Add the Isolation Forest anomaly score and order columns for the hybrid model."""
    Z = X[bundle["features"]].copy()
    Xi = bundle["if_scaler"].transform(Z[bundle["if_features"]])
    Z["if_anomaly_score"] = -bundle["if_model"].decision_function(Xi)
    return Z[bundle["model_features"]]


def risk_level(score: np.ndarray, thresholds: Dict[str, float]) -> np.ndarray:
    return np.where(score >= thresholds["high"], "High",
                    np.where(score >= thresholds["alert"], "Medium", "Low"))


def score_batch(df: pd.DataFrame, bundle: dict, thresholds: Dict[str, float] | None = None
                ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Score a whole file. Returns (scored_df, model_matrix).

    scored_df = original columns + fraud_score (0-1), alert, risk_level, warmup
    """
    th = thresholds or bundle["thresholds"]
    X, meta = compute_features(df)
    Xm = model_matrix(bundle, X)
    score = bundle["model"].predict_proba(Xm.values)[:, 1]
    out = df.copy()
    out["fraud_score"] = score
    out["alert"] = score >= th["alert"]
    out["risk_level"] = risk_level(score, th)
    out["warmup"] = meta["warmup"].to_numpy()
    return out, Xm


def score_one(engine: FeatureEngine, bundle: dict, txn: dict) -> Tuple[float, np.ndarray]:
    """Real-time path: update the engine with one payment and score it (~1 ms).

    Uses fast_models.FastScorer, which gives exactly the same numbers as the
    scikit-learn models (see tests) but avoids their per-call overhead."""
    from fast_models import FastScorer
    fast = bundle.get("_fast")
    if fast is None:
        fast = bundle["_fast"] = FastScorer(bundle)
    x = engine.process(txn)
    return fast.score(x)
