"""
Test suite to verify that:
1. All four pickle files load successfully.
2. Exactly 30 model features are supplied to the scaler/model.
3. Feature order matches the saved configuration.
4. The scaler is NOT refitted.
5. The Isolation Forest is NOT retrained.
6. A sample transaction successfully produces a prediction.
"""

import pickle
import numpy as np
import pandas as pd
import copy


def run_tests():
    print("=" * 60)
    print("RUNNING ISOLATION FOREST FRAUD DETECTION PIPELINE TESTS")
    print("=" * 60)

    # ---------------------------------------------------------
    # TEST 1: Load all four pickle files
    # ---------------------------------------------------------
    print("\n[Test 1] Loading all 4 pickle files...")
    with open("feature_config.pkl", "rb") as f:
        feature_config = pickle.load(f)
    print(f"  ✓ feature_config.pkl loaded ({len(feature_config)} features)")

    with open("preprocessing_config.pkl", "rb") as f:
        preprocessing_config = pickle.load(f)
    print(f"  ✓ preprocessing_config.pkl loaded (ml_features: {len(preprocessing_config.get('ml_features', []))}, log_features: {len(preprocessing_config.get('log_features', []))})")

    with open("scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    print(f"  ✓ scaler.pkl loaded ({type(scaler).__name__}, n_features_in_: {scaler.n_features_in_})")

    with open("isolation_forest.pkl", "rb") as f:
        model = pickle.load(f)
    print(f"  ✓ isolation_forest.pkl loaded ({type(model).__name__}, n_features_in_: {model.n_features_in_})")

    # ---------------------------------------------------------
    # TEST 2 & 3: Exactly 30 features and matching order
    # ---------------------------------------------------------
    print("\n[Test 2 & 3] Verifying feature count and exact order matching...")
    expected_30_features = [
        "amount",
        "transaction_step",
        "sender_old_balance",
        "sender_new_balance",
        "receiver_old_balance",
        "receiver_new_balance",
        "transaction_hour",
        "is_night",
        "transaction_frequency",
        "same_step_txn_count_before",
        "sender_txn_count_before",
        "sender_receiver_txn_count_before",
        "sender_unique_recipients_before",
        "receiver_txn_count_before",
        "receiver_unique_senders_before",
        "time_since_previous_sender_txn",
        "sender_balance_ratio",
        "sender_amount_mean_before",
        "sender_amount_std_before",
        "amount_deviation",
        "amount_zscore",
        "txns_last_1h",
        "txns_last_6h",
        "txns_last_24h",
        "rapid_transaction_flag",
        "device_change_flag",
        "new_device_flag",
        "hop_number",
        "chain_length",
        "chain_duration_steps"
    ]
    assert len(expected_30_features) == 30, "Expected feature count should be 30"
    assert len(feature_config) == 30, f"feature_config has {len(feature_config)} features, expected 30"
    assert feature_config == expected_30_features, "feature_config order does not match expected 30 features"
    assert preprocessing_config["ml_features"] == expected_30_features, "preprocessing_config['ml_features'] order mismatch"
    assert list(scaler.feature_names_in_) == expected_30_features, "scaler.feature_names_in_ order mismatch"
    print("  ✓ Exactly 30 features verified across all configurations in matching order.")

    # ---------------------------------------------------------
    # TEST 4 & 5: Ensure scaler is NOT refitted and model NOT retrained
    # ---------------------------------------------------------
    print("\n[Test 4 & 5] Recording initial scaler and model parameters to check immutability...")
    initial_scaler_mean = copy.deepcopy(scaler.mean_)
    initial_scaler_scale = copy.deepcopy(scaler.scale_)
    initial_scaler_var = copy.deepcopy(scaler.var_)
    initial_model_offset = model.offset_
    initial_tree_count = len(model.estimators_)

    # ---------------------------------------------------------
    # TEST 6: Sample transactions produce predictions
    # ---------------------------------------------------------
    print("\n[Test 6] Running sample transactions through the preprocessing and prediction pipeline...")
    log_features = preprocessing_config["log_features"]

    def build_test_feature_vector(
        amount: float,
        step: int,
        sender_old: float,
        sender_new: float,
        receiver_old: float,
        receiver_new: float,
        hour: int,
        is_night: int,
        device_change: int,
        new_device: int
    ) -> pd.DataFrame:
        ratio = amount / (sender_old + 1.0) if sender_old >= 0 else 0.0
        data = {
            "amount": float(amount),
            "transaction_step": int(step),
            "sender_old_balance": float(sender_old),
            "sender_new_balance": float(sender_new),
            "receiver_old_balance": float(receiver_old),
            "receiver_new_balance": float(receiver_new),
            "transaction_hour": int(hour),
            "is_night": int(is_night),
            "transaction_frequency": 1.0,
            "same_step_txn_count_before": 0.0,
            "sender_txn_count_before": 0.0,
            "sender_receiver_txn_count_before": 0.0,
            "sender_unique_recipients_before": 0.0,
            "receiver_txn_count_before": 0.0,
            "receiver_unique_senders_before": 0.0,
            "time_since_previous_sender_txn": -1.0,
            "sender_balance_ratio": float(ratio),
            "sender_amount_mean_before": 0.0,
            "sender_amount_std_before": 0.0,
            "amount_deviation": 0.0,
            "amount_zscore": 0.0,
            "txns_last_1h": 0.0,
            "txns_last_6h": 0.0,
            "txns_last_24h": 0.0,
            "rapid_transaction_flag": 0.0,
            "device_change_flag": float(device_change),
            "new_device_flag": float(new_device),
            "hop_number": 0.0,
            "chain_length": 0.0,
            "chain_duration_steps": 0.0,
        }
        df = pd.DataFrame([data])[expected_30_features]
        return df

    def predict(df_input: pd.DataFrame):
        df_proc = df_input.copy()
        for col in log_features:
            df_proc[col] = np.log1p(df_proc[col].clip(lower=0.0))
        # Use ONLY scaler.transform()
        scaled = scaler.transform(df_proc)
        pred = model.predict(scaled)[0]
        score = model.decision_function(scaled)[0]
        return pred, score

    # Sample 1: Normal transaction
    normal_df = build_test_feature_vector(
        amount=15000.0,
        step=200,
        sender_old=25000.0,
        sender_new=10000.0,
        receiver_old=5000.0,
        receiver_new=20000.0,
        hour=14,
        is_night=0,
        device_change=0,
        new_device=0
    )
    norm_pred, norm_score = predict(normal_df)
    print(f"  Sample 1 (Typical transaction) -> Prediction: {norm_pred} ({'NORMAL TRANSACTION' if norm_pred == 1 else 'ANOMALY DETECTED'}), Anomaly Score: {norm_score:.4f}")
    assert norm_pred == 1, f"Expected normal transaction (1), got {norm_pred}"

    # Sample 2: Anomalous transaction (device change, new device, 3 AM night)
    anomaly_df = build_test_feature_vector(
        amount=15000.0,
        step=200,
        sender_old=25000.0,
        sender_new=10000.0,
        receiver_old=5000.0,
        receiver_new=20000.0,
        hour=3,
        is_night=1,
        device_change=1,
        new_device=1
    )
    anom_pred, anom_score = predict(anomaly_df)
    print(f"  Sample 2 (Suspicious transaction) -> Prediction: {anom_pred} ({'NORMAL TRANSACTION' if anom_pred == 1 else 'ANOMALY DETECTED'}), Anomaly Score: {anom_score:.4f}")
    assert anom_pred == -1, f"Expected anomaly transaction (-1), got {anom_pred}"

    # Sample 3: Extreme balance wipeout anomaly
    extreme_df = build_test_feature_vector(
        amount=9999999.0,
        step=1,
        sender_old=9999999.0,
        sender_new=0.0,
        receiver_old=0.0,
        receiver_new=0.0,
        hour=2,
        is_night=1,
        device_change=1,
        new_device=1
    )
    ext_pred, ext_score = predict(extreme_df)
    print(f"  Sample 3 (Extreme balance wipeout) -> Prediction: {ext_pred} ({'NORMAL TRANSACTION' if ext_pred == 1 else 'ANOMALY DETECTED'}), Anomaly Score: {ext_score:.4f}")
    assert ext_pred == -1, f"Expected anomaly transaction (-1), got {ext_pred}"

    # Verify scaler and model were NOT modified
    np.testing.assert_array_equal(scaler.mean_, initial_scaler_mean, "Scaler mean_ was modified!")
    np.testing.assert_array_equal(scaler.scale_, initial_scaler_scale, "Scaler scale_ was modified!")
    np.testing.assert_array_equal(scaler.var_, initial_scaler_var, "Scaler var_ was modified!")
    assert model.offset_ == initial_model_offset, "Model offset_ was modified!"
    assert len(model.estimators_) == initial_tree_count, "Model estimators count was modified!"
    print("  ✓ Scaler was NOT refitted (parameters are 100% identical).")
    print("  ✓ Model was NOT retrained (estimators & offset are 100% identical).")

    print("\n" + "=" * 60)
    print("ALL 6 TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
