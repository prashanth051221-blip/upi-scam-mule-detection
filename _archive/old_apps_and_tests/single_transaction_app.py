"""
Transaction Anomaly Detection - Streamlit Web Application
Powered by an existing trained Isolation Forest Model and StandardScaler.
"""

import datetime
import os
import pickle
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. PAGE CONFIGURATION & THEME STYLING
# ==============================================================================
st.set_page_config(
    page_title="Transaction Anomaly Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a clean, professional banking/fintech dashboard
st.markdown(
    """
    <style>
    /* Main container styling */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: #f8fafc;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .main-header p {
        margin: 0.35rem 0 0 0;
        color: #94a3b8;
        font-size: 0.95rem;
    }

    /* Card styling */
    .stCard {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* Result Badges */
    .result-banner-anomaly {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin: 1rem 0;
    }
    .result-banner-anomaly h2 {
        color: #b91c1c;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.05em;
    }

    .result-banner-normal {
        background-color: #f0fdf4;
        border: 2px solid #22c55e;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin: 1rem 0;
    }
    .result-banner-normal h2 {
        color: #15803d;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.05em;
    }

    .score-badge {
        font-size: 1.1rem;
        font-weight: 600;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        display: inline-block;
        margin-top: 0.5rem;
    }
    .score-badge-anomaly {
        background-color: #fee2e2;
        color: #991b1b;
    }
    .score-badge-normal {
        background-color: #dcfce7;
        color: #166534;
    }

    /* Section Subheaders */
    .section-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1e293b;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.4rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. MODEL AND CONFIGURATION ARTIFACT LOADERS
# ==============================================================================
@st.cache_resource(show_spinner="Loading trained models and configurations...")
def load_detection_artifacts():
    """
    Loads the 4 pre-existing pickle files without retraining or refitting:
    - feature_config.pkl
    - preprocessing_config.pkl
    - scaler.pkl
    - isolation_forest.pkl
    """
    artifacts_to_load = {
        "feature_config": "feature_config.pkl",
        "preprocessing_config": "preprocessing_config.pkl",
        "scaler": "scaler.pkl",
        "model": "isolation_forest.pkl",
    }

    loaded = {}
    for key, filename in artifacts_to_load.items():
        if not os.path.exists(filename):
            raise FileNotFoundError(
                f"Missing required artifact '{filename}'. Ensure it is located in the working directory."
            )
        with open(filename, "rb") as f:
            loaded[key] = pickle.load(f)

    # Validate that exactly 30 model features exist and orders align
    feature_list = loaded["feature_config"]
    ml_features = loaded["preprocessing_config"].get("ml_features", [])
    scaler_features = list(getattr(loaded["scaler"], "feature_names_in_", []))

    if len(feature_list) != 30:
        raise ValueError(f"Expected 30 model features, found {len(feature_list)}.")
    if feature_list != ml_features:
        raise ValueError("Mismatch between feature_config.pkl and preprocessing_config.pkl ml_features.")
    if scaler_features and feature_list != scaler_features:
        raise ValueError("Mismatch between feature_config.pkl and scaler feature_names_in_.")

    return loaded["feature_config"], loaded["preprocessing_config"], loaded["scaler"], loaded["model"]


try:
    FEATURE_CONFIG, PREPROCESSING_CONFIG, SCALER, MODEL = load_detection_artifacts()
    LOG_FEATURES = set(PREPROCESSING_CONFIG.get("log_features", []))
except Exception as e:
    st.error(f"Failed to load detection model artifacts: {e}")
    st.stop()


# ==============================================================================
# 3. FEATURE VECTOR CONSTRUCTION & PREPROCESSING
# ==============================================================================
def construct_feature_vector(
    amount: float,
    step: int,
    sender_old: float,
    sender_new: float,
    receiver_old: float,
    receiver_new: float,
    hour: int,
    is_night: int,
    device_change: int,
    new_device: int,
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Builds the exact 30-feature dataframe in the order specified by feature_config.pkl.
    Maps user inputs, computes derived variables, and assigns clearly documented prototype defaults
    for internal historical/behavioral features that cannot be captured from a single-transaction form.
    """
    # Derived balance ratio: amount transferred relative to available sender balance
    sender_balance_ratio = float(amount / (sender_old + 1.0)) if sender_old >= 0 else 0.0

    # 30-feature vector mapping
    features = {
        # --- Direct User Inputs ---
        "amount": float(amount),
        "transaction_step": int(step),
        "sender_old_balance": float(sender_old),
        "sender_new_balance": float(sender_new),
        "receiver_old_balance": float(receiver_old),
        "receiver_new_balance": float(receiver_new),
        # --- Calculated / Derived Features ---
        "transaction_hour": int(hour),
        "is_night": int(is_night),
        "device_change_flag": float(device_change),
        "new_device_flag": float(new_device),
        "sender_balance_ratio": float(sender_balance_ratio),
        # --- Prototype Defaults for Historical / Behavioral Features ---
        "transaction_frequency": 1.0,  # Single observation frequency baseline
        "same_step_txn_count_before": 0.0,  # No concurrent transactions in current step
        "sender_txn_count_before": 0.0,  # First observed transaction for sender
        "sender_receiver_txn_count_before": 0.0,  # No previous interaction between pair
        "sender_unique_recipients_before": 0.0,  # No previous recipients for sender
        "receiver_txn_count_before": 0.0,  # No previous transactions for receiver
        "receiver_unique_senders_before": 0.0,  # No previous unique senders for receiver
        "time_since_previous_sender_txn": -1.0,  # Sentinel -1 encodes no prior transaction
        "sender_amount_mean_before": 0.0,  # No historical amount mean available
        "sender_amount_std_before": 0.0,  # No historical amount std available
        "amount_deviation": 0.0,  # Deviation from historical sender average
        "amount_zscore": 0.0,  # Z-score of transaction amount
        "txns_last_1h": 0.0,  # Rolling 1-hour window transaction count
        "txns_last_6h": 0.0,  # Rolling 6-hour window transaction count
        "txns_last_24h": 0.0,  # Rolling 24-hour window transaction count
        "rapid_transaction_flag": 0.0,  # High frequency burst flag
        "hop_number": 0.0,  # Hop position in transaction money trail
        "chain_length": 0.0,  # Money flow chain path length
        "chain_duration_steps": 0.0,  # Multi-hop chain duration
    }

    # Tracking source category for transparency in UI
    source_categories = {
        "amount": "User Input",
        "transaction_step": "User Input",
        "sender_old_balance": "User Input",
        "sender_new_balance": "User Input",
        "receiver_old_balance": "User Input",
        "receiver_new_balance": "User Input",
        "transaction_hour": "Derived (from Date & Time)",
        "is_night": "Derived (from Date & Time)",
        "device_change_flag": "User Input (Device Option)",
        "new_device_flag": "User Input (Device Option)",
        "sender_balance_ratio": "Derived (Amount / [Old Balance + 1])",
        "transaction_frequency": "Prototype Default (Baseline = 1.0)",
        "same_step_txn_count_before": "Prototype Default (0.0)",
        "sender_txn_count_before": "Prototype Default (0.0)",
        "sender_receiver_txn_count_before": "Prototype Default (0.0)",
        "sender_unique_recipients_before": "Prototype Default (0.0)",
        "receiver_txn_count_before": "Prototype Default (0.0)",
        "receiver_unique_senders_before": "Prototype Default (0.0)",
        "time_since_previous_sender_txn": "Prototype Default (-1.0: No prior event)",
        "sender_amount_mean_before": "Prototype Default (0.0)",
        "sender_amount_std_before": "Prototype Default (0.0)",
        "amount_deviation": "Prototype Default (0.0)",
        "amount_zscore": "Prototype Default (0.0)",
        "txns_last_1h": "Prototype Default (0.0)",
        "txns_last_6h": "Prototype Default (0.0)",
        "txns_last_24h": "Prototype Default (0.0)",
        "rapid_transaction_flag": "Prototype Default (0.0)",
        "hop_number": "Prototype Default (0.0)",
        "chain_length": "Prototype Default (0.0)",
        "chain_duration_steps": "Prototype Default (0.0)",
    }

    # Ensure exact column ordering as trained
    df = pd.DataFrame([features])[FEATURE_CONFIG]
    return df, source_categories


def run_pipeline_inference(df_raw: pd.DataFrame) -> Tuple[int, float, pd.DataFrame]:
    """
    Applies exact preprocessing steps:
    1. Log transform (np.log1p) exclusively on designated log features from preprocessing_config.pkl.
    2. Scaler transform via scaler.pkl (NEVER fit or fit_transform).
    3. Model prediction and decision function using isolation_forest.pkl (NEVER retrain).
    """
    df_transformed = df_raw.copy()

    # 1. Apply log1p ONLY to the features in preprocessing_config.pkl
    for col in LOG_FEATURES:
        if col in df_transformed.columns:
            df_transformed[col] = np.log1p(df_transformed[col].clip(lower=0.0))

    # 2. Scale using existing fitted scaler
    scaled_array = SCALER.transform(df_transformed)

    # 3. Isolation Forest prediction & decision function
    prediction = int(MODEL.predict(scaled_array)[0])
    anomaly_score = float(MODEL.decision_function(scaled_array)[0])

    return prediction, anomaly_score, df_transformed


# ==============================================================================
# 4. SIDEBAR CONTROLS & PRESET SCENARIOS
# ==============================================================================
with st.sidebar:
    st.markdown("### 🛡️ System Control")
    st.info(
        "**Model**: Isolation Forest (Pre-trained)\n\n"
        "**Scaler**: StandardScaler (Pre-fitted)\n\n"
        "**Total Features**: 30 (11 log-transformed)"
    )

    st.markdown("---")
    st.markdown("### ⚡ Quick-Load Test Presets")
    st.caption("Load representative transaction scenarios to test the model response:")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Normal Txn", use_container_width=True):
            st.session_state["txn_id"] = "TXN-NORM-8821"
            st.session_state["amount"] = 15000.0
            st.session_state["step"] = 200
            st.session_state["sender_old"] = 25000.0
            st.session_state["sender_new"] = 10000.0
            st.session_state["receiver_old"] = 5000.0
            st.session_state["receiver_new"] = 20000.0
            st.session_state["txn_date"] = datetime.date.today()
            st.session_state["txn_time"] = datetime.time(14, 30)
            st.session_state["device_change"] = "No"
            st.session_state["new_device"] = "No"
            st.rerun()

    with col_btn2:
        if st.button("Suspicious Txn", use_container_width=True):
            st.session_state["txn_id"] = "TXN-ANOM-4092"
            st.session_state["amount"] = 850000.0
            st.session_state["step"] = 12
            st.session_state["sender_old"] = 850000.0
            st.session_state["sender_new"] = 0.0
            st.session_state["receiver_old"] = 0.0
            st.session_state["receiver_new"] = 850000.0
            st.session_state["txn_date"] = datetime.date.today()
            st.session_state["txn_time"] = datetime.time(3, 15)
            st.session_state["device_change"] = "Yes"
            st.session_state["new_device"] = "Yes"
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚠️ Prototype Disclaimer")
    st.caption(
        "This application is an **evaluation prototype**. "
        "A single transaction form cannot capture multi-transaction historical aggregations "
        "(such as historical transaction counts, rolling z-scores, graph chains). "
        "Clearly documented prototype defaults are applied for these internal behavioral features."
    )


# ==============================================================================
# 5. MAIN HEADER
# ==============================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>Transaction Anomaly Detection</h1>
        <p>Enterprise fraud & anomaly monitoring system powered by trained Isolation Forest modeling.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State defaults if not set
if "txn_id" not in st.session_state:
    st.session_state["txn_id"] = "TXN-90412"
if "amount" not in st.session_state:
    st.session_state["amount"] = 12500.0
if "step" not in st.session_state:
    st.session_state["step"] = 180
if "sender_old" not in st.session_state:
    st.session_state["sender_old"] = 30000.0
if "sender_new" not in st.session_state:
    st.session_state["sender_new"] = 17500.0
if "receiver_old" not in st.session_state:
    st.session_state["receiver_old"] = 10000.0
if "receiver_new" not in st.session_state:
    st.session_state["receiver_new"] = 22500.0
if "txn_date" not in st.session_state:
    st.session_state["txn_date"] = datetime.date.today()
if "txn_time" not in st.session_state:
    st.session_state["txn_time"] = datetime.time(15, 0)
if "device_change" not in st.session_state:
    st.session_state["device_change"] = "No"
if "new_device" not in st.session_state:
    st.session_state["new_device"] = "No"


# ==============================================================================
# 6. TRANSACTION INPUT FORM
# ==============================================================================
with st.form("transaction_form", clear_on_submit=False):
    # --- Section 1: Transaction Details ---
    st.markdown('<div class="section-title">📄 1. Transaction Details</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1.2])

    with c1:
        txn_id = st.text_input(
            "Transaction ID *",
            value=st.session_state["txn_id"],
            placeholder="e.g. TXN-100234",
            help="Unique reference identifier for the transaction record.",
        )
    with c2:
        amount = st.number_input(
            "Amount ($) *",
            min_value=0.0,
            value=float(st.session_state["amount"]),
            step=100.0,
            format="%.2f",
            help="Total financial transfer amount.",
        )
    with c3:
        transaction_step = st.number_input(
            "Transaction Step *",
            min_value=1,
            value=int(st.session_state["step"]),
            step=1,
            help="Simulation step or hourly timeline sequence index (must be >= 1).",
        )
    with c4:
        # Date & Time selection to calculate transaction_hour and is_night
        col_d, col_t = st.columns(2)
        with col_d:
            txn_date = st.date_input("Date *", value=st.session_state["txn_date"])
        with col_t:
            txn_time = st.time_input("Time *", value=st.session_state["txn_time"])

    # Computed datetime features preview
    calc_hour = txn_time.hour
    calc_is_night = 1 if (calc_hour < 6 or calc_hour >= 22) else 0

    st.caption(
        f"🕒 Calculated from Date & Time: **Transaction Hour**: `{calc_hour}:00` | "
        f"**Is Night Flag**: `{'1 (Yes - Night Hours)' if calc_is_night == 1 else '0 (No - Daytime)'}` (Night defined as 22:00 – 06:00)"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Section 2: Account & Balance Information ---
    st.markdown('<div class="section-title">💳 2. Account & Balance Information</div>', unsafe_allow_html=True)
    b_col1, b_col2 = st.columns(2)

    with b_col1:
        st.markdown("**Sender Account**")
        sender_old_balance = st.number_input(
            "Sender Old Balance ($) *",
            min_value=0.0,
            value=float(st.session_state["sender_old"]),
            step=100.0,
            format="%.2f",
            help="Account balance of the sender before the transaction occurred.",
        )
        sender_new_balance = st.number_input(
            "Sender New Balance ($) *",
            min_value=0.0,
            value=float(st.session_state["sender_new"]),
            step=100.0,
            format="%.2f",
            help="Account balance of the sender after the transaction occurred.",
        )

    with b_col2:
        st.markdown("**Receiver Account**")
        receiver_old_balance = st.number_input(
            "Receiver Old Balance ($) *",
            min_value=0.0,
            value=float(st.session_state["receiver_old"]),
            step=100.0,
            format="%.2f",
            help="Account balance of the recipient before the transaction occurred.",
        )
        receiver_new_balance = st.number_input(
            "Receiver New Balance ($) *",
            min_value=0.0,
            value=float(st.session_state["receiver_new"]),
            step=100.0,
            format="%.2f",
            help="Account balance of the recipient after the transaction occurred.",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Section 3: Device Information ---
    st.markdown('<div class="section-title">📱 3. Device Information</div>', unsafe_allow_html=True)
    d_col1, d_col2 = st.columns(2)

    with d_col1:
        device_change = st.radio(
            "Device Changed? *",
            options=["No", "Yes"],
            index=0 if st.session_state["device_change"] == "No" else 1,
            horizontal=True,
            help="Did the sender switch from their primary registered device for this transfer?",
        )
    with d_col2:
        new_device = st.radio(
            "New Device? *",
            options=["No", "Yes"],
            index=0 if st.session_state["new_device"] == "No" else 1,
            horizontal=True,
            help="Was this transaction executed from an entirely newly registered or unrecognized device?",
        )

    device_change_val = 1 if device_change == "Yes" else 0
    new_device_val = 1 if new_device == "Yes" else 0

    st.markdown("<br>", unsafe_allow_html=True)
    submit_btn = st.form_submit_button("🔍 Run Anomaly Detection", use_container_width=True, type="primary")


# ==============================================================================
# 7. VALIDATION AND PREDICTION EXECUTION
# ==============================================================================
if submit_btn:
    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------
    validation_errors = []

    if not txn_id or not txn_id.strip():
        validation_errors.append("• **Transaction ID** is required and cannot be empty.")

    if amount <= 0.0:
        validation_errors.append("• **Amount** must be strictly greater than zero.")

    if transaction_step < 1:
        validation_errors.append("• **Transaction Step** must be a positive integer (>= 1).")

    if sender_old_balance < 0.0 or sender_new_balance < 0.0:
        validation_errors.append("• **Sender Balances** cannot be negative.")

    if receiver_old_balance < 0.0 or receiver_new_balance < 0.0:
        validation_errors.append("• **Receiver Balances** cannot be negative.")

    if validation_errors:
        st.error("### ❌ Transaction Validation Errors Found:")
        for err in validation_errors:
            st.markdown(err)
        st.stop()

    # Informative business logic sanity check (non-blocking warning)
    if sender_old_balance > 0 and amount > sender_old_balance:
        st.warning(
            f"⚠️ **Note**: Transfer amount (${amount:,.2f}) exceeds sender's available balance (${sender_old_balance:,.2f}). "
            "This behavior is heavily flagged by fraud models."
        )

    # -------------------------------------------------------------------------
    # Pipeline Execution
    # -------------------------------------------------------------------------
    feature_df, feature_sources = construct_feature_vector(
        amount=amount,
        step=transaction_step,
        sender_old=sender_old_balance,
        sender_new=sender_new_balance,
        receiver_old=receiver_old_balance,
        receiver_new=receiver_new_balance,
        hour=calc_hour,
        is_night=calc_is_night,
        device_change=device_change_val,
        new_device=new_device_val,
    )

    pred, anomaly_score, processed_df = run_pipeline_inference(feature_df)

    # ==============================================================================
    # 8. SECTION 4: PREDICTION RESULT
    # ==============================================================================
    st.markdown('<div class="section-title">📊 4. Prediction Result</div>', unsafe_allow_html=True)

    res_col1, res_col2 = st.columns([1.5, 1])

    with res_col1:
        if pred == -1:
            st.markdown(
                f"""
                <div class="result-banner-anomaly">
                    <h2>🚨 ANOMALY DETECTED</h2>
                    <p style="color: #991b1b; margin-top: 0.5rem; font-size: 1.05rem;">
                        Transaction <b>{txn_id}</b> deviates significantly from normal behavioral distributions.
                    </p>
                    <div class="score-badge score-badge-anomaly">
                        Anomaly Score: {anomaly_score:.5f} (Below Decision Threshold 0.0)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="result-banner-normal">
                    <h2>✅ NORMAL TRANSACTION</h2>
                    <p style="color: #166534; margin-top: 0.5rem; font-size: 1.05rem;">
                        Transaction <b>{txn_id}</b> conforms to expected behavioral baseline distributions.
                    </p>
                    <div class="score-badge score-badge-normal">
                        Anomaly Score: {anomaly_score:.5f} (Above Decision Threshold 0.0)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.info(
            "💡 **Model Insight**: Anomaly detection identifies transactions that differ significantly "
            "from the patterns learned from normal transactions."
        )

    with res_col2:
        st.markdown("#### Key Transaction Overview")
        st.markdown(
            f"""
            - **Transaction ID**: `{txn_id}`
            - **Transfer Amount**: `${amount:,.2f}`
            - **Timeline Step**: `Step {transaction_step}`
            - **Time / Period**: `{calc_hour:02d}:00` ({'Night' if calc_is_night == 1 else 'Day'})
            - **Device Flags**: `Changed: {device_change}` | `New: {new_device}`
            - **Sender Balance**: `${sender_old_balance:,.2f}` ➔ `${sender_new_balance:,.2f}`
            - **Receiver Balance**: `${receiver_old_balance:,.2f}` ➔ `${receiver_new_balance:,.2f}`
            """
        )

    # ==============================================================================
    # 9. FEATURE VECTOR & PREPROCESSING BREAKDOWN (ALL 30 FEATURES)
    # ==============================================================================
    with st.expander("🔍 Detailed Model Features & Transformation Breakdown (All 30 Features)", expanded=False):
        st.caption(
            "Below is the exact 30-feature vector fed to the Isolation Forest model after log-transformation "
            "and StandardScaler normalization."
        )

        breakdown_rows = []
        for i, col in enumerate(FEATURE_CONFIG):
            raw_val = feature_df[col].iloc[0]
            is_log = col in LOG_FEATURES
            trans_val = processed_df[col].iloc[0]
            src = feature_sources.get(col, "Internal")
            breakdown_rows.append(
                {
                    "Feature Name": col,
                    "Raw Input Value": f"{raw_val:,.4f}" if isinstance(raw_val, (int, float)) else str(raw_val),
                    "Log Transformed?": "Yes (np.log1p)" if is_log else "No",
                    "Transformed Value": f"{trans_val:,.4f}" if isinstance(trans_val, (int, float)) else str(trans_val),
                    "Feature Source / Category": src,
                }
            )

        breakdown_table = pd.DataFrame(breakdown_rows)
        st.dataframe(breakdown_table, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.caption(
    "Transaction Anomaly Detection System • Powered by scikit-learn Isolation Forest • "
    "Prototype Mode: Using documented defaults for historical window features."
)
