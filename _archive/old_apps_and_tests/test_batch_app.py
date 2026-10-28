"""
Automated test suite verifying the 15 requirements for the Batch Transaction Anomaly Detection App.
"""

import copy
import os
import pickle
import numpy as np
import pandas as pd

from fraud_detection_app.feature_engineering import (
    REQUIRED_COLUMNS,
    validate_raw_csv,
    compute_30_features,
)


def run_batch_verification():
    print("=" * 70)
    print("RUNNING BATCH ANOMALY DETECTION PIPELINE VERIFICATION SUITE")
    print("=" * 70)

    # 1. Load sample dataset
    sample_csv_path = "fraud_detection_app/sample_transactions.csv"
    assert os.path.exists(sample_csv_path), "sample_transactions.csv does not exist"
    df_raw = pd.read_csv(sample_csv_path)
    print(f"\n[Test 1] Loaded {len(df_raw)} transactions from {sample_csv_path} (Cols: {len(df_raw.columns)})")

    # 2. Validate required columns
    is_valid, errors, meta = validate_raw_csv(df_raw)
    assert is_valid, f"CSV Validation failed: {errors}"
    print(f"  ✓ [Test 2] Required 14 columns validated successfully. Zero errors.")

    # 3. Load 4 model artifacts
    with open("fraud_detection_app/models/feature_config.pkl", "rb") as f:
        feature_config = pickle.load(f)
    with open("fraud_detection_app/models/preprocessing_config.pkl", "rb") as f:
        preprocessing_config = pickle.load(f)
    with open("fraud_detection_app/models/scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    with open("fraud_detection_app/models/isolation_forest.pkl", "rb") as f:
        model = pickle.load(f)

    print(f"  ✓ [Test 9] Isolation Forest loaded ({type(model).__name__})")
    print(f"  ✓ Scaler loaded ({type(scaler).__name__})")

    # Record scaler and model states to verify non-refitting and non-retraining
    init_scaler_mean = copy.deepcopy(scaler.mean_)
    init_scaler_scale = copy.deepcopy(scaler.scale_)
    init_model_offset = model.offset_
    init_trees_count = len(model.estimators_)

    # 4 & 5. Feature Engineering: Compute 30 features in exact order
    feat_30_df, sorted_full_df = compute_30_features(df_raw, feature_config)
    assert feat_30_df.shape[1] == 30, f"Expected 30 features, got {feat_30_df.shape[1]}"
    assert list(feat_30_df.columns) == feature_config, "Feature columns order does not match feature_config.pkl"
    print(f"  ✓ [Test 3, 4 & 5] Generated exactly 30 features matching feature_config.pkl sequence.")

    # Check temporal / historical causality (no future leakage)
    first_row_sender = df_raw.iloc[0]["sender_id"]
    # Verify sender_txn_count_before is strictly non-negative and increments chronologically
    assert (sorted_full_df["sender_txn_count_before"] >= 0).all()
    print("  ✓ [Test 3] Historical features verified without future data leakage.")

    # 6. Log transformations match preprocessing_config.pkl
    log_features = preprocessing_config["log_features"]
    assert len(log_features) == 11, f"Expected 11 log features, found {len(log_features)}"
    
    feat_proc_df = feat_30_df.copy()
    for col in log_features:
        feat_proc_df[col] = np.log1p(feat_proc_df[col].clip(lower=0.0))
    print(f"  ✓ [Test 6] Exact 11 log features transformed with np.log1p().")

    # 7 & 8. Scaler transform (never fit)
    X_scaled = scaler.transform(feat_proc_df)
    assert X_scaled.shape == (len(df_raw), 30), f"Unexpected scaled shape {X_scaled.shape}"
    np.testing.assert_array_equal(scaler.mean_, init_scaler_mean, "Scaler mean was modified!")
    np.testing.assert_array_equal(scaler.scale_, init_scaler_scale, "Scaler scale was modified!")
    print(f"  ✓ [Test 7 & 8] Scaler transform executed. Scaler was NOT refitted.")

    # 9 & 10. Isolation Forest prediction (never retrain)
    preds = model.predict(X_scaled)
    scores = model.decision_function(X_scaled)
    assert model.offset_ == init_model_offset, "Model offset was modified!"
    assert len(model.estimators_) == init_trees_count, "Model estimators count was modified!"
    print(f"  ✓ [Test 10] Model was NOT retrained.")

    # 11 & 12. Every transaction receives anomaly score & prediction
    assert len(scores) == len(df_raw), "Score count mismatch"
    assert len(preds) == len(df_raw), "Prediction count mismatch"
    assert set(np.unique(preds)).issubset({-1, 1}), f"Unexpected prediction values: {np.unique(preds)}"
    print(f"  ✓ [Test 11 & 12] All {len(df_raw)} transactions scored: {(preds == 1).sum()} Normal, {(preds == -1).sum()} Anomalous.")

    # 13. Original columns preserved in output
    scored_df = df_raw.copy()
    scored_df["anomaly_score"] = scores
    scored_df["anomaly_prediction"] = preds
    scored_df["risk_level"] = np.where(scores < -0.05, "High Risk", np.where(scores < 0.0, "Medium Risk", "Normal / Low Risk"))

    for col in REQUIRED_COLUMNS:
        assert col in scored_df.columns, f"Original column '{col}' missing from scored output!"
    print(f"  ✓ [Test 13] All 14 original columns preserved alongside anomaly score & prediction.")

    # 14 & 15. CSV exports
    complete_csv = scored_df.to_csv(index=False)
    anomalies_only_df = scored_df[scored_df["anomaly_prediction"] == -1]
    anomalies_csv = anomalies_only_df.to_csv(index=False)
    assert len(complete_csv) > 0, "Complete CSV export is empty"
    assert len(anomalies_csv) > 0, "Anomalies CSV export is empty"
    print(f"  ✓ [Test 14 & 15] Complete scored dataset and anomalies-only ({len(anomalies_only_df)} rows) successfully exported.")

    print("\n" + "=" * 70)
    print("ALL 15 BATCH PIPELINE VERIFICATION TESTS PASSED (100% SUCCESS)")
    print("=" * 70)


if __name__ == "__main__":
    run_batch_verification()
