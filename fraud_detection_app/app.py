"""
UPI Scam & Mule Detection - investigation dashboard (Streamlit).

Run from the project folder:
    streamlit run fraud_detection_app/app.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))

from explain import ForestExplainer, explain_rows, reason_text  # noqa: E402
from feature_engineering import FEATURE_DESCRIPTIONS, validate_raw_csv  # noqa: E402
from mule_rings import detect_rings, escalate, ring_dot  # noqa: E402
from scoring import load_bundle, risk_level, score_batch  # noqa: E402

st.set_page_config(page_title="UPI Scam & Mule Detection", page_icon="🛡️", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
    .main-header {background: #0f172a; padding: 1.3rem 1.8rem; border-radius: 12px; margin-bottom: 1.2rem;}
    .main-header h1 {margin: 0; font-size: 1.8rem; color: #ffffff;}
    .main-header p {margin: 0.35rem 0 0 0; color: #cbd5e1; font-size: 0.95rem;}
    .section-header {font-size: 1.2rem; font-weight: 700; margin-top: 1.6rem; margin-bottom: 0.6rem;
                     padding-bottom: 0.35rem; border-bottom: 2px solid #e2e8f0;}
    </style>
    """,
    unsafe_allow_html=True,
)

DEMOS = {
    "Dataset 1 — normal activity only (7 days)": "dataset_1_normal_baseline.csv",
    "Dataset 2 — scams + mule accounts (7 days)": "dataset_2_scam_attacks.csv",
    "Dataset 3 — deep mule-layering rings (7 days)": "dataset_3_mule_rings.csv",
}


# ----------------------------------------------------------------------------
# Loading and cached computation
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading model...")
def get_model():
    bundle = load_bundle()
    explainer = ForestExplainer(bundle["model"], bundle["model_features"])
    return bundle, explainer


@st.cache_data(show_spinner="Computing features and scoring every payment...")
def run_scoring(csv_bytes: bytes):
    bundle, _ = get_model()
    df = pd.read_csv(io.BytesIO(csv_bytes))
    ok, errors, meta = validate_raw_csv(df)
    if not ok:
        return df, None, None, errors, meta
    scored, Xm = score_batch(df, bundle)
    return df, scored, Xm, errors, meta


@st.cache_data(show_spinner="Writing reasons for each alert...")
def run_explanations(csv_bytes: bytes, row_ids: tuple):
    _, explainer = get_model()
    df, scored, Xm, _, _ = run_scoring(csv_bytes)
    idx = list(row_ids)
    if not idx:
        return pd.DataFrame({"reasons": []})
    return explain_rows(explainer, Xm.loc[idx], df.loc[idx])


@st.cache_data(show_spinner=False)
def load_metrics():
    p = ROOT / "results" / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else None


try:
    BUNDLE, EXPLAINER = get_model()
except Exception as e:  # pragma: no cover
    st.error(f"Could not load fraud_detection_app/models/model_bundle.pkl: {e}. "
             "Run `python train_and_evaluate.py` from the project folder first.")
    st.stop()

TH = BUNDLE["thresholds"]

# ----------------------------------------------------------------------------
# Sidebar: how alerts are decided
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🛡️ Model")
    tm = BUNDLE.get("test_metrics", {})
    st.caption(
        f"Random Forest on {len(BUNDLE['features'])} features (incl. graph money-flow) "
        f"+ Isolation Forest anomaly score. Trained {BUNDLE['created']}. "
        f"Test-week PR-AUC **{tm.get('pr_auc', float('nan')):.3f}** on simulated UPI data."
    )
    st.markdown("### ⚙️ When to raise an alert")
    mode = st.radio("Threshold method", ["Cost-based (chosen on validation data)", "Analyst capacity"],
                    help="Cost-based: minimise ₹ of fraud missed + cost of reviewing each alert. "
                         "Analyst capacity: alert on the top X% of payments in this file.")
    options = {o["review_cost_rupees"]: o["threshold"] for o in BUNDLE.get("threshold_options", [])}
    if mode.startswith("Cost"):
        if options:
            costs = sorted(options)
            default = costs.index(BUNDLE.get("review_cost", 200)) if BUNDLE.get("review_cost", 200) in costs else 0
            rc = st.selectbox("Cost of reviewing one alert (₹)", costs, index=default,
                              format_func=lambda c: f"₹{c:,}")
            alert_th = options[rc]
        else:
            alert_th = TH["alert"]
        budget_share = None
    else:
        budget_share = st.slider("Analysts can review this % of payments", 0.5, 5.0, 2.0, 0.5) / 100
        alert_th = None
    use_rings = st.toggle("Escalate fast pass-through payments inside mule rings", value=True,
                          help="Adds payments the model scored low, but which sit inside a detected ring "
                               "and pass money on within 60 minutes.")
    st.markdown("### 🚦 Risk levels")
    st.markdown(f"- **High**: fraud score ≥ {TH['high']*100:.0f} (≥ 90% precision on validation)\n"
                f"- **Medium**: above the alert threshold\n- **Low**: below it\n"
                f"- **Warm-up**: first 48h of a file — not enough history to score fairly")

# ----------------------------------------------------------------------------
# Header + Section 1: upload
# ----------------------------------------------------------------------------
st.markdown(
    """<div class="main-header"><h1>UPI Scam & Mule Detection</h1>
    <p>Scores every payment, explains every alert, and maps the mule accounts that move stolen money.</p></div>""",
    unsafe_allow_html=True,
)

st.markdown('<div class="section-header">📁 1 — Load payments</div>', unsafe_allow_html=True)
c1, c2 = st.columns([2, 1])
with c1:
    up = st.file_uploader("Upload a UPI transaction CSV (14 required columns)", type=["csv"])
with c2:
    demo_label = st.selectbox("…or pick a labelled demo dataset", list(DEMOS))
    if st.button("Load demo dataset", width="stretch"):
        st.session_state["demo"] = DEMOS[demo_label]

if up is not None:
    csv_bytes, file_name = up.getvalue(), up.name
elif "demo" in st.session_state:
    file_name = st.session_state["demo"]
    csv_bytes = (APP_DIR / file_name).read_bytes()
else:
    st.info("Upload a CSV or load a demo dataset to start.")
    with st.expander("Required columns"):
        st.write(", ".join(["transaction_id", "sender_id", "receiver_id", "amount", "transaction_type",
                            "transaction_step", "sender_old_balance", "sender_new_balance",
                            "receiver_old_balance", "receiver_new_balance", "transaction_time",
                            "device_id", "device_change_flag", "new_device_flag"]))
        st.caption("Optional: `is_fraud` and `fraud_type`. If present they are used ONLY to measure accuracy, never to score.")
    st.stop()

raw, scored, Xm, errors, meta = run_scoring(csv_bytes)
v1, v2, v3 = st.columns(3)
v1.metric("File", file_name)
v2.metric("Payments", f"{len(raw):,}")
v3.metric("Validation", "✅ passed" if scored is not None else "❌ failed")
if scored is None:
    for e in errors:
        st.error(e)
    st.stop()
has_labels = bool(meta.get("has_labels"))

# ----------------------------------------------------------------------------
# Decide alerts for this run
# ----------------------------------------------------------------------------
live = ~scored["warmup"]
if alert_th is None:
    alert_th = float(np.quantile(scored.loc[live, "fraud_score"], 1 - budget_share)) if live.any() else 1.0
scored["alert"] = (scored["fraud_score"] >= alert_th) & live
scored["risk_level"] = np.where(scored["warmup"], "Warm-up",
                                risk_level(scored["fraud_score"].to_numpy(), {"alert": alert_th, "high": max(TH["high"], alert_th)}))
rings, ring_of, G, pass_thru = detect_rings(scored, "alert")
scored["ring"] = ring_of
scored["escalated"] = False
if use_rings:
    esc = escalate(scored, ring_of, pass_thru, min_score=BUNDLE.get("escalation_min_score", 0.05)) & live
    scored["escalated"] = esc
    scored.loc[esc, "risk_level"] = "Medium (ring)"
scored["flagged"] = scored["alert"] | scored["escalated"]

# ----------------------------------------------------------------------------
# Section 2: overview
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">📈 2 — Overview</div>', unsafe_allow_html=True)
n_live = int(live.sum())
flag = scored["flagged"]
m = st.columns(6)
m[0].metric("Payments scored", f"{n_live:,}", f"{int((~live).sum()):,} warm-up", delta_color="off")
m[1].metric("Alerts", f"{int(flag.sum()):,}", f"{flag.sum() / max(n_live, 1):.1%} of payments", delta_color="off")
m[2].metric("High risk", f"{int((scored['risk_level'] == 'High').sum()):,}")
m[3].metric("₹ in alerts", f"₹{scored.loc[flag, 'amount'].sum():,.0f}")
m[4].metric("Mule rings", f"{len(rings)}")
m[5].metric("Alert threshold", f"{alert_th * 100:.0f} / 100")

if has_labels:
    y = scored["is_fraud"].astype(int)
    yl, fl = y[live], flag[live]
    tp, fp = int((fl & (yl == 1)).sum()), int((fl & (yl == 0)).sum())
    fn = int((~fl & (yl == 1)).sum())
    st.markdown("**Accuracy on this file** (labels present; warm-up rows excluded)")
    e = st.columns(5)
    e[0].metric("Frauds in file", f"{int(yl.sum()):,}")
    e[1].metric("Caught (recall)", f"{tp / max(tp + fn, 1):.1%}" if yl.sum() else "–")
    e[2].metric("Alerts that are fraud (precision)", f"{tp / max(tp + fp, 1):.1%}" if (tp + fp) else "–")
    e[3].metric("False-alert rate", f"{fp / max(int((yl == 0).sum()), 1):.2%}")
    missed = scored.loc[live & (y == 1) & ~flag, "amount"].sum()
    e[4].metric("₹ of fraud missed", f"₹{missed:,.0f}")

# ----------------------------------------------------------------------------
# Section 3: alert queue with reasons
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">🚨 3 — Alert queue (highest score first)</div>', unsafe_allow_html=True)
flag_ids = tuple(scored.index[scored["flagged"]].tolist()[:2000])
reasons = run_explanations(csv_bytes, flag_ids)
scored["reasons"] = ""
if len(reasons):
    scored.loc[reasons.index, "reasons"] = reasons["reasons"]
scored.loc[scored["escalated"], "reasons"] = "Inside a mule ring; passes money on within 60 min · " + scored.loc[scored["escalated"], "reasons"]

f1, f2, f3, f4 = st.columns(4)
show = f1.selectbox("Show", ["Alerts only", "All scored payments", "Everything incl. warm-up"])
lvl = f2.multiselect("Risk level", ["High", "Medium", "Medium (ring)", "Low", "Warm-up"], default=[])
types = f3.multiselect("Payment type", sorted(scored["transaction_type"].astype(str).unique()), default=[])
limit = f4.selectbox("Rows", [25, 50, 100, 500, "All"], index=1)

view = scored
if show == "Alerts only":
    view = view[view["flagged"]]
elif show == "All scored payments":
    view = view[live]
if lvl:
    view = view[view["risk_level"].isin(lvl)]
if types:
    view = view[view["transaction_type"].astype(str).isin(types)]
view = view.sort_values("fraud_score", ascending=False)
if limit != "All":
    view = view.head(int(limit))

cols = ["transaction_id", "transaction_time", "sender_id", "receiver_id", "amount", "transaction_type",
        "fraud_score", "risk_level", "ring", "reasons"] + (["fraud_type"] if has_labels else [])
table = view[cols].copy()
table["fraud_score"] = (table["fraud_score"] * 100).round(0)
table["ring"] = table["ring"].where(table["ring"] >= 0, None)
st.dataframe(
    table, hide_index=True, width="stretch",
    column_config={
        "fraud_score": st.column_config.ProgressColumn("Fraud score", min_value=0, max_value=100, format="%d"),
        "amount": st.column_config.NumberColumn("Amount (₹)", format="%.0f"),
        "ring": st.column_config.NumberColumn("Ring #", format="%d"),
        "reasons": st.column_config.TextColumn("Top reasons", width="large"),
        "fraud_type": st.column_config.TextColumn("Truth (label)"),
    },
)
st.caption(f"Showing {len(table):,} rows.")

# ----------------------------------------------------------------------------
# Section 4: mule rings
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">🕸️ 4 — Mule rings (NetworkX money-flow graph)</div>', unsafe_allow_html=True)
if not rings:
    st.info("No mule rings found: no group of 3+ accounts linked by several alerted payments or fast pass-through transfers.")
else:
    rt = pd.DataFrame([{k: v for k, v in r.items() if k != "nodes"} for r in rings])
    if has_labels:
        rt["fraud_share (label)"] = [scored.loc[scored["ring"] == r["ring"], "is_fraud"].mean() for r in rings]
    st.dataframe(rt, hide_index=True, width="stretch",
                 column_config={"total_amount": st.column_config.NumberColumn("Total ₹", format="%.0f")})
    pick = st.selectbox("Draw ring", [r["ring"] for r in rings],
                        format_func=lambda k: f"Ring {k} — {rings[k]['accounts']} accounts, ₹{rings[k]['total_amount']:,.0f}")
    st.caption("Blue = money enters (victims / sources) · Yellow = mule passing money on · Red = cash-out end. "
               "Bold arrows = payments the model alerted on; dashed = linked by fast pass-through.")
    st.graphviz_chart(ring_dot(G, rings[pick]["nodes"]))
    with st.expander("Payments in this ring"):
        st.dataframe(scored.loc[scored["ring"] == pick, cols].sort_values("transaction_time"), hide_index=True, width="stretch")

# ----------------------------------------------------------------------------
# Section 5: single payment deep dive
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">🔍 5 — Why was this payment flagged?</div>', unsafe_allow_html=True)
ordered = scored.sort_values("fraud_score", ascending=False)
txn_id = st.selectbox("Payment", ordered["transaction_id"].tolist(), index=0)
row_idx = scored.index[scored["transaction_id"] == txn_id][0]
row = scored.loc[row_idx]
contrib = EXPLAINER.contributions(Xm.loc[[row_idx]].values)[0]
names = BUNDLE["model_features"]
d1, d2 = st.columns([1, 1.4])
with d1:
    st.markdown(f"**{row['transaction_id']}** · {row['transaction_time']}")
    st.markdown(f"`{row['sender_id']}` → `{row['receiver_id']}`")
    st.markdown(f"**₹{row['amount']:,.2f}** · {row['transaction_type']} · device `{row['device_id']}`")
    st.metric("Fraud score", f"{row['fraud_score'] * 100:.0f} / 100", row["risk_level"], delta_color="off")
    if has_labels:
        st.caption(f"Ground truth: **{row['fraud_type'] if int(row['is_fraud']) == 1 else 'normal'}**")
    st.caption(f"Model baseline (average payment): {EXPLAINER.bias * 100:.0f} / 100. "
               "Each bar on the right shows how much one signal pushed this payment's score up or down.")
with d2:
    feats = Xm.loc[row_idx].to_dict()
    top = np.argsort(-np.abs(contrib))[:10]
    chart = pd.DataFrame({
        "signal": [reason_text(names[j], feats, row.to_dict()) for j in top],
        "effect on score": [contrib[j] * 100 for j in top],
    })
    st.bar_chart(chart, x="signal", y="effect on score", horizontal=True)
with st.expander("All model inputs for this payment"):
    st.dataframe(pd.DataFrame({
        "feature": names,
        "value": [feats[n] for n in names],
        "effect on score (points)": np.round(contrib * 100, 2),
        "meaning": [FEATURE_DESCRIPTIONS.get(n, "Isolation Forest anomaly score (higher = more unusual)") for n in names],
    }), hide_index=True, width="stretch")

# ----------------------------------------------------------------------------
# Section 6: patterns
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">📊 6 — Patterns in this file</div>', unsafe_allow_html=True)
t1, t2, t3 = st.tabs(["Alerts per day", "Score distribution", "By payment type"])
with t1:
    day = pd.to_datetime(scored["transaction_time"]).dt.date
    per_day = pd.DataFrame({"payments": scored.groupby(day).size(), "alerts": scored[flag].groupby(day[flag]).size()}).fillna(0)
    st.bar_chart(per_day["alerts"])
with t2:
    hist, edges = np.histogram(scored.loc[live, "fraud_score"] * 100, bins=20, range=(0, 100))
    st.bar_chart(pd.DataFrame({"payments": hist}, index=[f"{int(edges[i])}–{int(edges[i+1])}" for i in range(20)]))
    st.caption("Most payments score near 0; alerts sit in the long tail on the right.")
with t3:
    st.bar_chart(scored[flag].groupby("transaction_type").size())

# ----------------------------------------------------------------------------
# Section 7: evidence
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">🧪 7 — How well does the model work? (offline evaluation)</div>', unsafe_allow_html=True)
metrics = load_metrics()
if metrics is None:
    st.info("Run `python train_and_evaluate.py` to produce results/metrics.json.")
else:
    a, b, c = st.tabs(["Model comparison", "Ablation", "Unseen scam types"])
    with a:
        comp = pd.DataFrame(metrics["comparison"])[["model", "pr_auc", "budget_precision", "budget_recall", "cost_alerts_per_day"]]
        st.dataframe(comp, hide_index=True, width="stretch", column_config={
            "pr_auc": st.column_config.NumberColumn("PR-AUC", format="%.3f"),
            "budget_precision": st.column_config.NumberColumn("Precision @2% budget", format="%.2f"),
            "budget_recall": st.column_config.NumberColumn("Recall @2% budget", format="%.2f"),
            "cost_alerts_per_day": st.column_config.NumberColumn("Alerts/day @cost threshold", format="%.0f")})
        img = ROOT / "results" / "pr_curves.png"
        if img.exists():
            st.image(str(img))
    with b:
        st.dataframe(pd.DataFrame(metrics["ablation"]), hide_index=True, width="stretch")
        img = ROOT / "results" / "ablation.png"
        if img.exists():
            st.image(str(img))
    with c:
        st.dataframe(pd.DataFrame(metrics["unseen_scams"]), hide_index=True, width="stretch")
        st.caption("Recall when a scam type was never in training (same 2% alert budget for every model).")
    st.caption("Full write-up with assumptions and limitations: RESULTS.md")

# ----------------------------------------------------------------------------
# Section 8: export
# ----------------------------------------------------------------------------
st.markdown('<div class="section-header">💾 8 — Export</div>', unsafe_allow_html=True)
out_cols = [c for c in scored.columns if c not in ("__ts__", "__hour__")]
x1, x2 = st.columns(2)
x1.download_button("Download all scored payments (CSV)", scored[out_cols].to_csv(index=False).encode("utf-8"),
                   file_name=f"scored_{file_name}", mime="text/csv", width="stretch")
x2.download_button(f"Download alerts only ({int(flag.sum()):,})", scored.loc[flag, out_cols].to_csv(index=False).encode("utf-8"),
                   file_name=f"alerts_{file_name}", mime="text/csv", width="stretch")
st.caption("Prototype for PBL-III. Trained and evaluated on simulated UPI data; see RESULTS.md for limitations.")
