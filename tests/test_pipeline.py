"""
Tests that check the system DETECTS fraud, not just that files load.

Run from the project folder:
    python tests/test_pipeline.py          (no extra packages needed)
    python -m pytest tests/                (if pytest is installed)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "fraud_detection_app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(ROOT))

from explain import ForestExplainer  # noqa: E402
from feature_engineering import (FEATURES, FeatureEngine, compute_features,  # noqa: E402
                                 row_to_txn, validate_raw_csv)
from mule_rings import detect_rings  # noqa: E402
from scoring import load_bundle, model_matrix, score_batch, score_one  # noqa: E402

D1 = APP / "dataset_1_normal_baseline.csv"
D2 = APP / "dataset_2_scam_attacks.csv"
D3 = APP / "dataset_3_mule_rings.csv"
_BUNDLE = None


def bundle():
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = load_bundle()
    return _BUNDLE


# --------------------------------------------------------------------------- features
def test_no_future_leakage():
    """Features for the first N rows must be identical whether or not later rows exist."""
    df = pd.read_csv(D2).sort_values("transaction_time").reset_index(drop=True)
    full, _ = compute_features(df)
    n = 3000
    part, _ = compute_features(df.iloc[:n])
    assert np.allclose(full.iloc[:n].values, part.values), "features depend on future payments"


def test_streaming_equals_batch():
    """Real-time path (one payment at a time) gives exactly the batch features."""
    df = pd.read_csv(D2).sort_values("transaction_time").reset_index(drop=True).head(1500)
    batch, _ = compute_features(df)
    eng = FeatureEngine()
    stream = np.vstack([eng.process(row_to_txn(r)) for r in df.to_dict("records")])
    assert np.allclose(batch.values, stream)


def test_no_dead_features():
    """Every feature must vary in real data (the old model had 9 features that never did)."""
    df = pd.read_csv(D2)
    X, meta = compute_features(df)
    X = X[~meta["warmup"]]
    dead = [c for c in FEATURES if X[c].nunique() <= 1]
    assert not dead, f"constant features: {dead}"


def test_validation_rejects_bad_files():
    df = pd.read_csv(D1).head(50)
    ok, _, _ = validate_raw_csv(df)
    assert ok
    bad = df.drop(columns=["device_id"])
    assert not validate_raw_csv(bad)[0]
    bad = df.copy()
    bad.loc[0, "amount"] = -5
    assert not validate_raw_csv(bad)[0]
    bad = df.copy()
    bad.loc[1, "transaction_id"] = bad.loc[0, "transaction_id"]
    assert not validate_raw_csv(bad)[0]
    bad = df.copy()
    bad["transaction_time"] = bad["transaction_time"].astype(object)
    bad.loc[2, "transaction_time"] = "not a date"
    assert not validate_raw_csv(bad)[0]


# --------------------------------------------------------------------------- model
def test_bundle_matches_features():
    b = bundle()
    assert b["features"] == FEATURES
    assert b["model_features"] == FEATURES + ["if_anomaly_score"]
    assert 0 < b["thresholds"]["alert"] <= b["thresholds"]["high"] <= 1


def test_normal_data_is_mostly_not_flagged():
    """The old model flagged 89% of normal payments. Now: under 3%."""
    scored, _ = score_batch(pd.read_csv(D1), bundle())
    live = ~scored["warmup"]
    rate = scored.loc[live, "alert"].mean()
    assert rate < 0.03, f"false-alert rate on normal data {rate:.1%}"


def test_scams_are_caught():
    for path in (D2, D3):
        scored, _ = score_batch(pd.read_csv(path), bundle())
        live = ~scored["warmup"]
        y = scored.loc[live, "is_fraud"] == 1
        recall = scored.loc[live & y, "alert"].mean()
        precision = scored.loc[live & scored["alert"], "is_fraud"].mean()
        assert recall > 0.85, f"{path.name}: recall {recall:.1%}"
        assert precision > 0.35, f"{path.name}: precision {precision:.1%}"


def test_fraud_scores_higher_than_normal():
    scored, _ = score_batch(pd.read_csv(D2), bundle())
    live = scored[~scored["warmup"]]
    assert live.loc[live.is_fraud == 1, "fraud_score"].median() > 10 * live.loc[live.is_fraud == 0, "fraud_score"].median() + 0.05


def test_real_time_score_equals_batch_score():
    b = bundle()
    df = pd.read_csv(D2).sort_values("transaction_time").reset_index(drop=True).head(800)
    scored, _ = score_batch(df, b)
    eng = FeatureEngine()
    live = [score_one(eng, b, row_to_txn(r))[0] for r in df.to_dict("records")]
    assert np.allclose(scored["fraud_score"].values, live)


# --------------------------------------------------------------------------- explanations & graph
def test_explanations_add_up():
    """Bias + contributions must equal the model's probability (exact attribution)."""
    b = bundle()
    df = pd.read_csv(D2)
    X, _ = compute_features(df)
    Xm = model_matrix(b, X).iloc[:300]
    ex = ForestExplainer(b["model"], b["model_features"])
    C = ex.contributions(Xm.values)
    p = b["model"].predict_proba(Xm.values)[:, 1]
    assert np.allclose(ex.bias + C.sum(1), p, atol=1e-6)


def test_rings_found_only_where_they_exist():
    b = bundle()
    s1, _ = score_batch(pd.read_csv(D1), b)
    s1["alert"] &= ~s1["warmup"]
    rings1, *_ = detect_rings(s1, "alert")
    assert len(rings1) == 0, "rings reported in normal-only data"
    s3, _ = score_batch(pd.read_csv(D3), b)
    s3["alert"] &= ~s3["warmup"]
    rings3, ring_of, *_ = detect_rings(s3, "alert")
    assert len(rings3) >= 1
    in_ring = ring_of >= 0
    assert s3.loc[in_ring, "is_fraud"].mean() > 0.6


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    sys.exit(1 if failed else 0)
