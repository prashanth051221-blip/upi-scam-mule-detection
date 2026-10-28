"""
Transaction Anomaly Detection - Streamlit Batch Web Application
Batch analysis of transaction datasets powered by an existing Isolation Forest model.
"""

import os
import pickle
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# Feature engineering imports
from feature_engineering import (
    REQUIRED_COLUMNS,
    validate_raw_csv,
    compute_30_features,
)

# ==============================================================================
# 1. PAGE CONFIGURATION & THEME STYLING
# ==============================================================================
st.set_page_config(
    page_title="Transaction Anomaly Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
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
        margin: 0.4rem 0 0 0;
        color: #94a3b8;
        font-size: 0.95rem;
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e293b;
        margin-top: 1.75rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #e2e8f0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .badge-high {
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }
    .badge-med {
        background-color: #fef3c7;
        color: #92400e;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }
    .badge-low {
        background-color: #dcfce7;
        color: #166534;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. MODEL AND ARTIFACT CACHING
# ==============================================================================
@st.cache_resource(show_spinner="Loading trained ML artifacts...")
def load_ml_artifacts():
    """
    Loads existing trained Isolation Forest and configuration artifacts.
    Never fits or retrains models.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(base_dir, "models")
    
    # Fallback if run directly or inside workspace
    if not os.path.exists(model_dir):
        model_dir = os.path.join(base_dir, "..")

    paths = {
        "feature_config": os.path.join(model_dir, "feature_config.pkl"),
        "preprocessing_config": os.path.join(model_dir, "preprocessing_config.pkl"),
        "scaler": os.path.join(model_dir, "scaler.pkl"),
        "model": os.path.join(model_dir, "isolation_forest.pkl"),
    }

    loaded = {}
    for name, path in paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required artifact '{os.path.basename(path)}' not found at {path}")
        with open(path, "rb") as f:
            loaded[name] = pickle.load(f)

    # Validate exact 30 features
    fc = loaded["feature_config"]
    if len(fc) != 30:
        raise ValueError(f"Expected 30 features in feature_config, found {len(fc)}")

    return loaded["feature_config"], loaded["preprocessing_config"], loaded["scaler"], loaded["model"]


try:
    FEATURE_CONFIG, PREPROCESSING_CONFIG, SCALER, MODEL = load_ml_artifacts()
    LOG_FEATURES = set(PREPROCESSING_CONFIG.get("log_features", []))
except Exception as e:
    st.error(f"❌ Error loading ML model artifacts: {e}")
    st.stop()


# ==============================================================================
# 3. SIDEBAR CONTROLS & MODEL SUMMARY
# ==============================================================================
with st.sidebar:
    st.markdown("### 🛡️ System Engine")
    st.info(
        f"**Algorithm**: Isolation Forest\n\n"
        f"**Normalizer**: StandardScaler (`transform()` only)\n\n"
        f"**Total Features**: {len(FEATURE_CONFIG)} ML Features\n\n"
        f"**Log-Transformed**: {len(LOG_FEATURES)} Features (`np.log1p`)"
    )

    st.markdown("---")
    st.markdown("### 📊 Risk Scoring Legend")
    st.markdown(
        """
        - <span class="badge-high">High Risk</span>: Anomaly score < -0.05
        - <span class="badge-med">Medium Risk</span>: Anomaly score between -0.05 and 0.0
        - <span class="badge-low">Normal / Low Risk</span>: Anomaly score ≥ 0.0
        """,
        unsafe_allow_html=True,
    )
    st.caption("Risk levels represent model anomaly rankings; more negative scores reflect greater divergence from normal behavior.")


# ==============================================================================
# 4. MAIN HEADER
# ==============================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>Transaction Anomaly Detection</h1>
        <p>Enterprise batch anomaly scoring and fraud monitoring system powered by trained Isolation Forest.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# 5. SECTION 1 — UPLOAD
# ==============================================================================
st.markdown('<div class="section-header">📁 Section 1 — Upload Transaction Dataset</div>', unsafe_allow_html=True)

upload_col1, upload_col2 = st.columns([2, 1])

with upload_col1:
    uploaded_file = st.file_uploader(
        "Upload Batch Transaction CSV (e.g. 1 Month Transaction History)",
        type=["csv"],
        help="Upload CSV containing the 14 raw transaction columns.",
    )

with upload_col2:
    st.markdown("**Quick Demo Datasets**")
    st.caption("Select a pre-built showcase dataset to test the system:")
    demo_options = {
        "Dataset 1: Normal Retail / P2P Baseline (300 txns)": "dataset_1_normal_baseline.csv",
        "Dataset 2: High-Risk Scam & Takeover Attacks (400 txns)": "dataset_2_scam_attacks.csv",
        "Dataset 3: Money Mule & Multi-Hop Chains (350 txns)": "dataset_3_mule_layering_chains.csv",
        "Dataset 4: Original Mixed Simulation (500 txns)": "sample_transactions.csv",
    }
    selected_demo_label = st.selectbox("Choose Demo Dataset", options=list(demo_options.keys()), index=0)
    selected_demo_file = demo_options[selected_demo_label]
    
    demo_btn = st.button("📥 Load Selected Demo Dataset", use_container_width=True)

raw_df = None
file_name = ""

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file)
        file_name = uploaded_file.name
    except Exception as e:
        st.error(f"Error reading uploaded CSV: {e}")
        st.stop()
elif demo_btn or ("loaded_demo" in st.session_state and uploaded_file is None):
    if demo_btn:
        st.session_state["loaded_demo"] = selected_demo_file
        st.session_state["loaded_demo_label"] = selected_demo_label
    
    target_demo_file = st.session_state.get("loaded_demo", selected_demo_file)
    target_demo_label = st.session_state.get("loaded_demo_label", selected_demo_label)
    
    demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), target_demo_file)
    if not os.path.exists(demo_path):
        demo_path = target_demo_file
        
    if os.path.exists(demo_path):
        raw_df = pd.read_csv(demo_path)
        file_name = f"{target_demo_file} ({target_demo_label.split(':')[0]})"

if raw_df is None:
    st.info("👆 Please upload a transaction CSV file or select a **Demo Dataset** and click **'Load Selected Demo Dataset'**.")
    st.stop()

# --- Validation Step ---
is_valid, validation_errors, metadata = validate_raw_csv(raw_df)

v_c1, v_c2, v_c3, v_c4 = st.columns(4)
v_c1.metric("Uploaded File", file_name)
v_c2.metric("Total Transactions", f"{len(raw_df):,}")
v_c3.metric("Total Columns", len(raw_df.columns))
v_c4.metric("Validation Status", "✅ PASSED" if is_valid else "❌ FAILED")

if not is_valid:
    st.error("### ❌ CSV Validation Failed — Cannot Proceed")
    for err in validation_errors:
        st.markdown(f"• {err}")
    st.stop()

if metadata["duplicate_id_count"] > 0 or metadata["null_counts"]:
    with st.expander("⚠️ Data Quality Alerts", expanded=True):
        if metadata["duplicate_id_count"] > 0:
            st.warning(f"Found {metadata['duplicate_id_count']} duplicate transaction IDs.")
        if metadata["null_counts"]:
            st.warning(f"Columns with nulls: {metadata['null_counts']}")


# ==============================================================================
# 6. FEATURE ENGINEERING & BATCH SCORING
# ==============================================================================
with st.spinner("Processing batch feature engineering & running Isolation Forest inference..."):
    # 1. Create the exact 30 ML features without future leakage
    features_30_df, sorted_full_df = compute_30_features(raw_df, FEATURE_CONFIG)

    # 2. Apply log1p ONLY to the features in preprocessing_config.pkl
    features_proc_df = features_30_df.copy()
    for col in LOG_FEATURES:
        if col in features_proc_df.columns:
            features_proc_df[col] = np.log1p(features_proc_df[col].clip(lower=0.0))

    # 3. Apply saved scaler (transform only)
    X_scaled = SCALER.transform(features_proc_df)

    # 4. Model prediction & anomaly score
    raw_predictions = MODEL.predict(X_scaled)
    anomaly_scores = MODEL.decision_function(X_scaled)

    # 5. Create final enriched result dataframe preserving original columns
    scored_df = raw_df.copy()
    scored_df["anomaly_score"] = anomaly_scores
    scored_df["anomaly_prediction"] = raw_predictions
    
    # Risk levels ranking based on anomaly score
    scored_df["risk_level"] = np.where(
        anomaly_scores < -0.05,
        "High Risk",
        np.where(anomaly_scores < 0.0, "Medium Risk", "Normal / Low Risk")
    )


# ==============================================================================
# 7. SECTION 2 — DATASET OVERVIEW
# ==============================================================================
st.markdown('<div class="section-header">📈 Section 2 — Dataset Overview</div>', unsafe_allow_html=True)

total_txns = len(scored_df)
anomaly_txns = int((scored_df["anomaly_prediction"] == -1).sum())
normal_txns = int((scored_df["anomaly_prediction"] == 1).sum())
anomaly_pct = (anomaly_txns / total_txns * 100) if total_txns > 0 else 0.0

most_negative_score = float(scored_df["anomaly_score"].min())
highest_risk_idx = scored_df["anomaly_score"].idxmin()
highest_risk_txn_id = scored_df.loc[highest_risk_idx, "transaction_id"]

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Transactions", f"{total_txns:,}")
m2.metric("Normal Transactions", f"{normal_txns:,}", f"{(normal_txns/total_txns*100):.1f}%")
m3.metric("Anomalous Transactions", f"{anomaly_txns:,}", f"{anomaly_pct:.1f}%", delta_color="inverse")
m4.metric("Anomaly Rate", f"{anomaly_pct:.2f}%")
m5.metric("Highest-Risk ID", highest_risk_txn_id)
m6.metric("Min Anomaly Score", f"{most_negative_score:.4f}")


# ==============================================================================
# 8. SECTION 3 — SUSPICIOUS TRANSACTIONS
# ==============================================================================
st.markdown('<div class="section-header">🚨 Section 3 — Ranked Suspicious Transactions</div>', unsafe_allow_html=True)

f_c1, f_c2, f_c3, f_c4 = st.columns([1, 1, 1, 1])

with f_c1:
    risk_filter = st.selectbox(
        "Filter by Risk Level",
        options=["All Risk Levels", "High Risk", "Medium Risk", "Normal / Low Risk"],
        index=0,
    )
with f_c2:
    pred_filter = st.selectbox(
        "Filter by Prediction",
        options=["All Predictions", "Anomalies Only (-1)", "Normal Only (1)"],
        index=0,
    )
with f_c3:
    all_types = ["All Types"] + sorted(list(scored_df["transaction_type"].dropna().unique()))
    type_filter = st.selectbox("Filter by Transaction Type", options=all_types, index=0)

with f_c4:
    top_n_str = st.selectbox(
        "Display Limit",
        options=["Top 10", "Top 25", "Top 50", "Top 100", "Top 500", "All Transactions"],
        index=1,
    )

# Apply filters
filtered_df = scored_df.copy()

if risk_filter != "All Risk Levels":
    filtered_df = filtered_df[filtered_df["risk_level"] == risk_filter]

if pred_filter == "Anomalies Only (-1)":
    filtered_df = filtered_df[filtered_df["anomaly_prediction"] == -1]
elif pred_filter == "Normal Only (1)":
    filtered_df = filtered_df[filtered_df["anomaly_prediction"] == 1]

if type_filter != "All Types":
    filtered_df = filtered_df[filtered_df["transaction_type"] == type_filter]

# Sort by anomaly_score from most negative to highest
filtered_df = filtered_df.sort_values(by="anomaly_score", ascending=True)

# Limit
if top_n_str != "All Transactions":
    n_limit = int(top_n_str.replace("Top ", ""))
    display_df = filtered_df.head(n_limit)
else:
    display_df = filtered_df

display_cols = [
    "transaction_id",
    "sender_id",
    "receiver_id",
    "amount",
    "transaction_type",
    "transaction_step",
    "transaction_time",
    "anomaly_score",
    "anomaly_prediction",
    "risk_level",
]

# Ensure display columns exist
available_display_cols = [c for c in display_cols if c in display_df.columns]

st.dataframe(
    display_df[available_display_cols].style.format(
        {
            "amount": "${:,.2f}",
            "anomaly_score": "{:.5f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
st.caption(f"Showing {len(display_df):,} of {len(filtered_df):,} matching transactions (Sorted by anomaly score ascending).")


# ==============================================================================
# 9. SECTION 4 — ANOMALY ANALYSIS CHARTS
# ==============================================================================
st.markdown('<div class="section-header">📊 Section 4 — Anomaly Analysis & Visualizations</div>', unsafe_allow_html=True)

chart_tab1, chart_tab2, chart_tab3, chart_tab4 = st.tabs(
    [
        "Distribution & Breakdown",
        "Timeline & Steps",
        "Transaction Types",
        "Top Suspicious Rankings",
    ]
)

with chart_tab1:
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        st.markdown("**1. Normal vs. Anomalous Breakdown**")
        pred_counts = scored_df["anomaly_prediction"].map({1: "Normal (1)", -1: "Anomaly (-1)"}).value_counts()
        st.bar_chart(pred_counts)

    with c_col2:
        st.markdown("**2. Anomaly Score Distribution**")
        # Histogram of scores
        hist_values, bin_edges = np.histogram(scored_df["anomaly_score"], bins=30)
        hist_df = pd.DataFrame({
            "Score Bin": [f"{bin_edges[i]:.3f} to {bin_edges[i+1]:.3f}" for i in range(len(hist_values))],
            "Count": hist_values
        })
        st.bar_chart(hist_df.set_index("Score Bin"))

with chart_tab2:
    st.markdown("**3. Anomaly Distribution Across Transaction Steps**")
    if "transaction_step" in scored_df.columns:
        step_summary = scored_df.groupby(["transaction_step", "anomaly_prediction"]).size().unstack(fill_value=0)
        step_summary.columns = [f"Class {c}" for c in step_summary.columns]
        if "Class -1" in step_summary.columns:
            step_summary = step_summary.rename(columns={"Class -1": "Anomalies", "Class 1": "Normal"})
        st.line_chart(step_summary)

with chart_tab3:
    st.markdown("**4. Anomalies by Transaction Type**")
    if "transaction_type" in scored_df.columns:
        type_summary = scored_df.groupby(["transaction_type", "risk_level"]).size().unstack(fill_value=0)
        st.bar_chart(type_summary)

with chart_tab4:
    st.markdown("**5. Top 10 Most Extreme Anomaly Scores**")
    top10_extreme = scored_df.sort_values(by="anomaly_score", ascending=True).head(10)
    st.bar_chart(
        top10_extreme.set_index("transaction_id")["anomaly_score"]
    )


# ==============================================================================
# 10. SECTION 5 — TRANSACTION DETAILS & FEATURE INSPECTOR
# ==============================================================================
st.markdown('<div class="section-header">🔍 Section 5 — Individual Transaction Deep-Dive</div>', unsafe_allow_html=True)

# Select a transaction ID
all_txn_ids = list(scored_df["transaction_id"].values)
default_idx = int(scored_df["anomaly_score"].argmin())

selected_txn_id = st.selectbox(
    "Select Transaction ID to inspect:",
    options=all_txn_ids,
    index=default_idx,
    help="Select any transaction ID to view its complete attributes and 30 model features.",
)

if selected_txn_id:
    txn_row = scored_df[scored_df["transaction_id"] == selected_txn_id].iloc[0]
    txn_idx_orig = scored_df[scored_df["transaction_id"] == selected_txn_id].index[0]
    
    # Feature vector for this transaction
    txn_features = features_30_df.iloc[txn_idx_orig]
    txn_proc_features = features_proc_df.iloc[txn_idx_orig]

    d1, d2, d3 = st.columns([1.2, 1.2, 1])

    with d1:
        st.markdown(f"**Transaction ID**: `{txn_row['transaction_id']}`")
        st.markdown(f"**Sender ID**: `{txn_row.get('sender_id', 'N/A')}`")
        st.markdown(f"**Receiver ID**: `{txn_row.get('receiver_id', 'N/A')}`")
        st.markdown(f"**Amount**: `${txn_row.get('amount', 0.0):,.2f}`")
        st.markdown(f"**Transaction Type**: `{txn_row.get('transaction_type', 'N/A')}`")

    with d2:
        st.markdown(f"**Transaction Step**: `Step {txn_row.get('transaction_step', 'N/A')}`")
        st.markdown(f"**Transaction Time**: `{txn_row.get('transaction_time', 'N/A')}`")
        st.markdown(f"**Device ID**: `{txn_row.get('device_id', 'N/A')}`")
        st.markdown(f"**Device Flags**: `Changed: {txn_row.get('device_change_flag', 0)}` | `New: {txn_row.get('new_device_flag', 0)}`")

    with d3:
        p_val = txn_row["anomaly_prediction"]
        score_val = txn_row["anomaly_score"]
        r_lvl = txn_row["risk_level"]

        if p_val == -1:
            st.error(f"🚨 **PREDICTION**: ANOMALY (-1)\n\n**Risk Level**: {r_lvl}\n\n**Anomaly Score**: {score_val:.5f}")
        else:
            st.success(f"✅ **PREDICTION**: NORMAL (1)\n\n**Risk Level**: {r_lvl}\n\n**Anomaly Score**: {score_val:.5f}")

    st.info(
        "💡 **Model Evaluation Context**: "
        "These are the feature values associated with this transaction. "
        "The anomaly score indicates how unusual the transaction is relative to the patterns learned by the model."
    )

    with st.expander("📋 View All 30 Model Features for this Transaction", expanded=False):
        feat_inspect_rows = []
        for feat in FEATURE_CONFIG:
            raw_v = txn_features[feat]
            is_lg = feat in LOG_FEATURES
            trans_v = txn_proc_features[feat]
            feat_inspect_rows.append({
                "Model Feature Name": feat,
                "Calculated Feature Value": f"{raw_v:,.4f}" if isinstance(raw_v, (int, float)) else str(raw_v),
                "Log Transformed?": "Yes (np.log1p)" if is_lg else "No",
                "Preprocessed Value": f"{trans_v:,.4f}" if isinstance(trans_v, (int, float)) else str(trans_v),
            })
        st.dataframe(pd.DataFrame(feat_inspect_rows), use_container_width=True, hide_index=True)


# ==============================================================================
# 11. SECTION 6 — DOWNLOAD RESULTS
# ==============================================================================
st.markdown('<div class="section-header">💾 Section 6 — Export Scored Results</div>', unsafe_allow_html=True)

st.write("Download complete scored dataset with all original columns and anomaly rankings, or filter anomalies only:")

down_col1, down_col2 = st.columns(2)

with down_col1:
    csv_complete = scored_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Complete Scored Dataset (CSV)",
        data=csv_complete,
        file_name=f"scored_transactions_{file_name.replace('.csv', '')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption(f"Includes all {len(scored_df):,} original rows + `anomaly_score`, `anomaly_prediction`, `risk_level`.")

with down_col2:
    anomalies_only_df = scored_df[scored_df["anomaly_prediction"] == -1]
    csv_anomalies = anomalies_only_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"🚨 Download Anomalies Only ({len(anomalies_only_df):,} Rows)",
        data=csv_anomalies,
        file_name=f"anomalies_only_{file_name.replace('.csv', '')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption("Includes only transactions flagged as anomalies (`anomaly_prediction == -1`).")

st.markdown("---")
st.caption(
    "Transaction Anomaly Detection • Batch Processing Engine • Powered by scikit-learn Isolation Forest"
)
