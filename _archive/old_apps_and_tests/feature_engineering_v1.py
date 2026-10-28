"""
Feature engineering module for Batch Transaction Anomaly Detection.
Constructs the exact 30 ML features from raw transaction batches strictly before
the current transaction, preventing data leakage.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

# The 14 raw required CSV columns
REQUIRED_COLUMNS: List[str] = [
    "transaction_id",
    "sender_id",
    "receiver_id",
    "amount",
    "transaction_type",
    "transaction_step",
    "sender_old_balance",
    "sender_new_balance",
    "receiver_old_balance",
    "receiver_new_balance",
    "transaction_time",
    "device_id",
    "device_change_flag",
    "new_device_flag",
]

NUMERIC_COLUMNS: List[str] = [
    "amount",
    "transaction_step",
    "sender_old_balance",
    "sender_new_balance",
    "receiver_old_balance",
    "receiver_new_balance",
    "device_change_flag",
    "new_device_flag",
]


def validate_raw_csv(df: pd.DataFrame) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validates uploaded raw transaction CSV.
    Checks:
    - Presence of all 14 required columns
    - Data types and numeric parsing
    - Timestamp parsing
    - Missing values (nulls)
    - Duplicate transaction IDs
    - Invalid numeric ranges (negative values)
    """
    errors: List[str] = []
    metadata: Dict[str, Any] = {
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "missing_cols": [],
        "null_counts": {},
        "duplicate_id_count": 0,
        "invalid_numeric_count": 0,
        "time_parse_errors": 0,
    }

    # 1. Check required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        metadata["missing_cols"] = missing_cols
        errors.append(f"Missing required column(s): {', '.join(missing_cols)}")
        return False, errors, metadata

    # 2. Check for duplicate transaction IDs
    dup_mask = df["transaction_id"].duplicated(keep=False)
    dup_count = int(dup_mask.sum())
    metadata["duplicate_id_count"] = dup_count
    if dup_count > 0:
        dup_samples = df.loc[dup_mask, "transaction_id"].head(5).tolist()
        errors.append(
            f"Found {dup_count} duplicate transaction_id values (e.g. {dup_samples}). Transaction IDs must be unique."
        )

    # 3. Check for missing values (nulls)
    null_counts = df[REQUIRED_COLUMNS].isnull().sum()
    cols_with_nulls = null_counts[null_counts > 0].to_dict()
    metadata["null_counts"] = cols_with_nulls
    if cols_with_nulls:
        null_desc = ", ".join([f"{k} ({v} nulls)" for k, v in cols_with_nulls.items()])
        errors.append(f"Missing (null) values detected in columns: {null_desc}.")

    # 4. Check numeric conversions and negative values
    for col in NUMERIC_COLUMNS:
        non_numeric = pd.to_numeric(df[col], errors="coerce")
        nan_count = int(non_numeric.isnull().sum()) - int(df[col].isnull().sum())
        if nan_count > 0:
            errors.append(f"Column '{col}' contains {nan_count} non-numeric values.")
        
        # Check negative amounts or negative steps
        if col in ["amount", "transaction_step"]:
            neg_count = int((non_numeric < 0).sum())
            if neg_count > 0:
                metadata["invalid_numeric_count"] += neg_count
                errors.append(f"Column '{col}' contains {neg_count} negative values, which are invalid.")

    # 5. Check transaction_time parsing
    parsed_time = pd.to_datetime(df["transaction_time"], errors="coerce")
    time_nulls = int(parsed_time.isnull().sum()) - int(df["transaction_time"].isnull().sum())
    if time_nulls > 0:
        metadata["time_parse_errors"] = time_nulls
        errors.append(f"Column 'transaction_time' contains {time_nulls} unparseable datetime strings.")

    is_valid = len(errors) == 0
    return is_valid, errors, metadata


def compute_30_features(df_raw: pd.DataFrame, feature_order: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Computes exactly 30 ML features from raw transactions strictly before the current transaction.
    Returns:
    - features_df: DataFrame with exactly the 30 ML features in feature_order, mapped back to original input rows.
    - sorted_df: The internally processed DataFrame with all calculated helper columns.
    """
    # Create a copy and preserve original row index
    df = df_raw.copy()
    df["__orig_idx__"] = np.arange(len(df))

    # Parse datetime and numeric types
    df["parsed_time"] = pd.to_datetime(df["transaction_time"])
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Sort strictly chronologically by transaction_time and transaction_step, using orig index as tie-breaker
    df = df.sort_values(by=["parsed_time", "transaction_step", "__orig_idx__"]).reset_index(drop=True)

    # --- 1. Direct & Datetime Features ---
    df["transaction_hour"] = df["parsed_time"].dt.hour.astype(float)
    df["is_night"] = ((df["transaction_hour"] < 6) | (df["transaction_hour"] >= 22)).astype(float)
    df["sender_balance_ratio"] = df["amount"] / (df["sender_old_balance"].clip(lower=0.0) + 1.0)

    # --- 2. Sender and Receiver Historical Interaction Counts ---
    # sender_txn_count_before: prior transactions sent by this sender
    df["sender_txn_count_before"] = df.groupby("sender_id").cumcount().astype(float)

    # same_step_txn_count_before: prior transactions sent by this sender in the same step
    df["same_step_txn_count_before"] = df.groupby(["sender_id", "transaction_step"]).cumcount().astype(float)

    # sender_receiver_txn_count_before: prior transactions between this exact pair
    df["sender_receiver_txn_count_before"] = df.groupby(["sender_id", "receiver_id"]).cumcount().astype(float)

    # sender_unique_recipients_before: unique recipients seen by sender strictly before current txn
    df["__is_new_recipient__"] = (~df.duplicated(subset=["sender_id", "receiver_id"])).astype(int)
    df["sender_unique_recipients_before"] = (
        df.groupby("sender_id")["__is_new_recipient__"].cumsum() - df["__is_new_recipient__"]
    ).astype(float)

    # receiver_txn_count_before: prior transactions received by this receiver
    df["receiver_txn_count_before"] = df.groupby("receiver_id").cumcount().astype(float)

    # receiver_unique_senders_before: unique senders to this receiver strictly before current txn
    df["__is_new_sender__"] = (~df.duplicated(subset=["receiver_id", "sender_id"])).astype(int)
    df["receiver_unique_senders_before"] = (
        df.groupby("receiver_id")["__is_new_sender__"].cumsum() - df["__is_new_sender__"]
    ).astype(float)

    # --- 3. Time Since Previous Sender Transaction ---
    prev_time = df.groupby("sender_id")["parsed_time"].shift(1)
    time_diff_hours = (df["parsed_time"] - prev_time).dt.total_seconds() / 3600.0
    # If no previous transaction, encode as sentinel -1.0
    df["time_since_previous_sender_txn"] = time_diff_hours.fillna(-1.0).astype(float)

    # --- 4. Historical Sender Amount Statistics & Deviations ---
    # Cumulative sum and count of sender transfer amounts strictly before current txn
    cum_amt_before = df.groupby("sender_id")["amount"].cumsum() - df["amount"]
    count_before = df["sender_txn_count_before"].values

    df["sender_amount_mean_before"] = np.where(
        count_before > 0,
        cum_amt_before / np.maximum(1, count_before),
        0.0
    )

    # Expanding variance strictly before
    cum_sq_before = (
        df.groupby("sender_id")["amount"].transform(lambda s: (s ** 2).cumsum())
        - (df["amount"] ** 2)
    )
    # Sample variance: (cum_sq - (cum_amt^2)/N) / (N - 1)
    variance_before = np.where(
        count_before > 1,
        np.maximum(
            0.0,
            (cum_sq_before - (cum_amt_before ** 2) / np.maximum(1, count_before))
            / np.maximum(1, count_before - 1),
        ),
        0.0,
    )
    df["sender_amount_std_before"] = np.sqrt(variance_before)

    # Amount deviation & Z-score
    df["amount_deviation"] = np.where(
        count_before > 0,
        np.abs(df["amount"] - df["sender_amount_mean_before"]),
        0.0
    )
    df["amount_zscore"] = np.where(
        df["sender_amount_std_before"] > 1e-6,
        (df["amount"] - df["sender_amount_mean_before"]) / df["sender_amount_std_before"],
        0.0
    )

    # Transaction frequency baseline
    df["transaction_frequency"] = 1.0

    # --- 5. Rolling Window Transaction Velocities (1h, 6h, 24h) ---
    # High performance searchsorted per sender
    timestamps_sec = df["parsed_time"].astype("int64") // 10**9
    df["__timestamp_sec__"] = timestamps_sec

    txns_1h = np.zeros(len(df), dtype=float)
    txns_6h = np.zeros(len(df), dtype=float)
    txns_24h = np.zeros(len(df), dtype=float)

    # Compute rolling window per sender group strictly before (< t)
    for _, group_indices in df.groupby("sender_id").groups.items():
        indices = group_indices.values
        t_vals = timestamps_sec.iloc[indices].values
        n_items = len(t_vals)
        cur_pos = np.arange(n_items)

        # Left bounds: find first index >= (t - window)
        idx_1h = np.searchsorted(t_vals, t_vals - 3600, side="left")
        idx_6h = np.searchsorted(t_vals, t_vals - 21600, side="left")
        idx_24h = np.searchsorted(t_vals, t_vals - 86400, side="left")

        # Counts strictly before current transaction
        txns_1h[indices] = cur_pos - idx_1h
        txns_6h[indices] = cur_pos - idx_6h
        txns_24h[indices] = cur_pos - idx_24h

    df["txns_last_1h"] = txns_1h
    df["txns_last_6h"] = txns_6h
    df["txns_last_24h"] = txns_24h

    # Rapid transaction flag: burst within 6 minutes (0.1 hour) or same step
    df["rapid_transaction_flag"] = (
        ((df["time_since_previous_sender_txn"] >= 0.0) & (df["time_since_previous_sender_txn"] <= 0.1))
        | (df["same_step_txn_count_before"] > 0)
    ).astype(float)

    # --- 6. Chain Tracking (hop_number, chain_length, chain_duration_steps) ---
    # Track transfer flow where account B receives funds and subsequently sends funds
    hop_number = np.zeros(len(df), dtype=float)
    chain_length = np.zeros(len(df), dtype=float)
    chain_duration_steps = np.zeros(len(df), dtype=float)

    # Dictionary: account_id -> (chain_root_step, current_chain_length, last_seen_step)
    recent_chains: Dict[str, Tuple[int, int, int]] = {}

    senders = df["sender_id"].values
    receivers = df["receiver_id"].values
    steps = df["transaction_step"].values

    for i in range(len(df)):
        s_id = senders[i]
        r_id = receivers[i]
        s_step = int(steps[i])

        if s_id in recent_chains:
            root_step, prev_len, last_step = recent_chains[s_id]
            # If received within last 48 steps, consider it part of the ongoing money flow chain
            if 0 <= (s_step - last_step) <= 48:
                c_len = prev_len + 1
                c_dur = float(s_step - root_step)
                hop_number[i] = float(c_len)
                chain_length[i] = float(c_len)
                chain_duration_steps[i] = c_dur
                # Forward chain to receiver
                recent_chains[r_id] = (root_step, c_len, s_step)
            else:
                # Chain expired
                recent_chains[r_id] = (s_step, 1, s_step)
        else:
            # New chain origin
            recent_chains[r_id] = (s_step, 1, s_step)

    df["hop_number"] = hop_number
    df["chain_length"] = chain_length
    df["chain_duration_steps"] = chain_duration_steps

    # Re-align back to original input row ordering
    df_restored = df.sort_values(by="__orig_idx__").reset_index(drop=True)
    
    # Extract exactly the 30 features in feature_order
    features_30_df = df_restored[feature_order].astype(float)

    return features_30_df, df_restored
