"""
Real-time scoring demo.

UPI is real-time, so the system must score each payment the moment it happens,
not only in monthly batches. This script replays a demo file one payment at a
time through the SAME feature engine and model the dashboard uses:

    payment arrives -> update account state -> 31 features -> score -> alert?

It prints alerts with their reasons as they happen and reports latency.

Run:
    python realtime_demo.py                                   # replay dataset 2
    python realtime_demo.py fraud_detection_app/dataset_3_mule_rings.csv
    python realtime_demo.py --all                             # print Medium alerts too
    python realtime_demo.py --benchmark                       # latency only
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "fraud_detection_app"))

from explain import ForestExplainer, top_reasons  # noqa: E402
from feature_engineering import WARMUP_HOURS, FeatureEngine, row_to_txn  # noqa: E402
from scoring import load_bundle, risk_level, score_one  # noqa: E402

DEFAULT_FILE = ROOT / "fraud_detection_app" / "dataset_2_scam_attacks.csv"


def replay(path: Path = DEFAULT_FILE, max_alerts: int = 25, quiet: bool = False, limit: int | None = None,
           show_medium: bool = False) -> dict:
    bundle = load_bundle()
    th = bundle["thresholds"]
    explainer = ForestExplainer(bundle["model"], bundle["model_features"])
    df = pd.read_csv(path).sort_values("transaction_time").reset_index(drop=True)
    if limit:
        df = df.head(limit)
    engine = FeatureEngine()
    t_start = pd.Timestamp(df["transaction_time"].iloc[0])
    lat, alerts, shown, tp = [], 0, 0, 0
    tiers = {"High": [0, 0], "Medium": [0, 0]}   # [alerts, true fraud]
    if not quiet:
        print(f"Replaying {path.name} one payment at a time "
              f"(first {WARMUP_HOURS}h build account history and are not scored)\n")
    names = bundle["model_features"]
    for _, row in df.iterrows():
        rec = row.to_dict()
        txn = row_to_txn(rec)
        t0 = time.perf_counter()
        score, x = score_one(engine, bundle, txn)
        lat.append((time.perf_counter() - t0) * 1000)
        warm = (pd.Timestamp(rec["transaction_time"]) - t_start).total_seconds() < WARMUP_HOURS * 3600
        if warm or score < th["alert"]:
            continue
        alerts += 1
        is_fraud = int(rec.get("is_fraud", 0) == 1)
        tp += is_fraud
        level = risk_level(np.array([score]), th)[0]
        tiers[level][0] += 1
        tiers[level][1] += is_fraud
        if level == "Medium" and not show_medium:
            continue
        if not quiet and shown < max_alerts:
            shown += 1
            contrib = explainer.contributions(x[np.newaxis, :])[0]
            reasons = top_reasons(contrib, names, dict(zip(names, x)), rec)
            truth = ""
            if "is_fraud" in rec:
                truth = f"  [truth: {rec['fraud_type'] if rec['is_fraud'] == 1 else 'normal'}]"
            print(f"{rec['transaction_time']}  ₹{rec['amount']:>10,.0f}  {rec['sender_id']:>24s} → "
                  f"{rec['receiver_id']:<24s} score {score:.2f} ({level}){truth}")
            for r in reasons:
                print(f"      • {r}")
    lat = np.array(lat)
    stats = {"n": int(len(lat)), "p50_ms": float(np.percentile(lat, 50)),
             "p95_ms": float(np.percentile(lat, 95)), "p99_ms": float(np.percentile(lat, 99)),
             "alerts": alerts, "alerts_true_fraud": tp}
    if not quiet:
        print(f"\nReplayed {stats['n']:,} payments. Alerts: {alerts} ({tp} true fraud).")
        for lvl, (n_a, n_tp) in tiers.items():
            if n_a:
                print(f"  {lvl:6s}: {n_a} alerts, {n_tp} true fraud ({n_tp / n_a:.0%})")
        if not show_medium:
            print("  (only High alerts printed; run with --all to print Medium too)")
        print(f"Latency per payment (features + model): median {stats['p50_ms']:.1f} ms, "
              f"p95 {stats['p95_ms']:.1f} ms, p99 {stats['p99_ms']:.1f} ms")
    return stats


def benchmark(n: int = 2000, quiet: bool = True) -> dict:
    return replay(DEFAULT_FILE, quiet=quiet, limit=n)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--benchmark" in sys.argv:
        print(benchmark(quiet=True))
    else:
        replay(Path(args[0]) if args else DEFAULT_FILE, show_medium="--all" in sys.argv)
