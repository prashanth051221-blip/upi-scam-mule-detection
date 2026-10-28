"""
Reason codes for every alert.

Method
------
For a random forest, each prediction can be split exactly into
    prediction = bias + sum(contribution of each feature)
by walking every tree from root to leaf and giving the change in
"fraud probability" at each split to the feature used in that split
(tree path attribution, Saabas method). It needs no extra library and is fast
enough to run inside the dashboard. In notebooks/train_and_evaluate.ipynb it is
checked against SHAP TreeExplainer: the top reasons agree for most alerts.

The top three positive contributions are then turned into plain-English
sentences using the raw transaction values, e.g.
    "Sends 100% of the sender's balance (₹48,000)"
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np
import pandas as pd
from scipy import sparse


def _tree_matrix(tree, n_features: int) -> sparse.csr_matrix:
    """(n_nodes x n_features) matrix: row = node, value = change in P(fraud) caused by
    reaching that node, placed in the column of the parent's split feature."""
    t = tree.tree_
    value = t.value[:, 0, :]
    prob = value[:, 1] / np.maximum(value.sum(axis=1), 1e-12)
    rows, cols, vals = [], [], []
    for parent in range(t.node_count):
        f = t.feature[parent]
        if f < 0:
            continue
        for child in (t.children_left[parent], t.children_right[parent]):
            rows.append(child)
            cols.append(f)
            vals.append(prob[child] - prob[parent])
    return sparse.csr_matrix((vals, (rows, cols)), shape=(t.node_count, n_features))


class ForestExplainer:
    """Exact additive contributions for a fitted RandomForestClassifier."""

    def __init__(self, forest, feature_names: Sequence[str]):
        self.forest = forest
        self.feature_names = list(feature_names)
        n = len(self.feature_names)
        self._mats = [_tree_matrix(est, n) for est in forest.estimators_]
        roots = []
        for est in forest.estimators_:
            v = est.tree_.value[0, 0, :]
            roots.append(v[1] / max(v.sum(), 1e-12))
        self.bias = float(np.mean(roots))

    def contributions(self, X) -> np.ndarray:
        Xa = np.asarray(X, dtype=np.float32)
        total = np.zeros((Xa.shape[0], len(self.feature_names)))
        for est, mat in zip(self.forest.estimators_, self._mats):
            path = est.decision_path(Xa)
            total += (path @ mat).toarray()
        return total / len(self._mats)


# ----------------------------------------------------------------------------
# Plain-English reason templates
# ----------------------------------------------------------------------------
def _fmt_rupees(x: float) -> str:
    x = float(x)
    if x >= 1e5:
        return f"₹{x/1e5:.2f} lakh"
    return f"₹{x:,.0f}"


def _hhmm(h: float) -> str:
    h = float(h) % 24
    return f"{int(h):02d}:{int(round((h - int(h)) * 60)) % 60:02d}"


def reason_text(feature: str, f: Dict[str, float], raw: Dict) -> str:
    """Human-readable sentence for one contributing feature."""
    amt = float(raw.get("amount", np.expm1(f.get("amount_log", 0))))
    e = np.expm1
    t = {
        "amount_log": f"Large amount: {_fmt_rupees(amt)}",
        "sender_balance_ratio": f"Sends {min(f['sender_balance_ratio'], 1.0):.0%} of the sender's balance",
        "sender_old_balance_log": f"Sender balance before payment: {_fmt_rupees(e(f['sender_old_balance_log']))}",
        "receiver_old_balance_log": f"Receiver balance before payment was only {_fmt_rupees(e(f['receiver_old_balance_log']))}",
        "transaction_hour": f"Made at {_hhmm(f['transaction_hour'])}",
        "is_night": f"Night-time payment ({_hhmm(f['transaction_hour'])})",
        "is_p2m": "Person-to-person transfer, not a merchant payment" if f["is_p2m"] < 0.5 else "Merchant payment",
        "is_collect": "Payer approved a collect request" if f["is_collect"] >= 0.5 else "Not a collect request",
        "sender_txn_count_before_log": f"Sender has only {e(f['sender_txn_count_before_log']):.0f} earlier payments",
        "txns_last_1h": f"{f['txns_last_1h']:.0f} payments by the sender in the previous hour",
        "txns_last_24h": f"{f['txns_last_24h']:.0f} payments by the sender in the previous 24h",
        "minutes_since_prev_txn_log": f"Only {e(f['minutes_since_prev_txn_log']):.0f} min after the sender's previous payment",
        "amount_zscore": f"Amount is {f['amount_zscore']:.1f} std-devs above the sender's usual",
        "amount_vs_max_log": "Largest payment this sender has ever made" if f["amount_vs_max_log"] > 0
                             else "Amount close to the sender's largest ever",
        "is_new_recipient": "First-ever payment to this receiver" if f["is_new_recipient"] >= 0.5
                            else "Repeat payment to a known receiver",
        "new_recipients_last_24h": f"Sender paid {f['new_recipients_last_24h']:.0f} new receivers in the last 24h",
        "sender_night_ratio": "Sender rarely pays at night" if f["sender_night_ratio"] < 0.15 else "Sender often pays at night",
        "hour_deviation": f"At {_hhmm(f['transaction_hour'])}, {f['hour_deviation']:.0f}h away from the sender's usual time",
        "device_change_flag": "Device differs from the sender's previous payment",
        "new_device_flag": "Sender has never used this device before",
        "hours_since_device_change_log": f"Device changed {e(f['hours_since_device_change_log']):.0f}h ago",
        "sent_since_device_change_log": f"{_fmt_rupees(e(f['sent_since_device_change_log']))} already sent since the device change",
        "receiver_unique_senders_24h": f"Receiver was paid by {f['receiver_unique_senders_24h']:.0f} different accounts in 24h",
        "receiver_inflow_24h_log": f"Receiver got {_fmt_rupees(e(f['receiver_inflow_24h_log']))} in the last 24h",
        "receiver_fanin_burst": f"{f['receiver_fanin_burst']:.0%} of the receiver's payers appeared only in the last 24h",
        "receiver_txn_count_before_log": f"Receiver account has little history ({e(f['receiver_txn_count_before_log']):.0f} earlier receipts)",
        "sender_inflow_60m_log": f"Sender itself received {_fmt_rupees(e(f['sender_inflow_60m_log']))} in the last hour",
        "forwarded_share": f"Passes on {f['forwarded_share']:.0%} of money received in the last hour",
        "minutes_since_sender_inflow_log": f"Sender received money only {e(f['minutes_since_sender_inflow_log']):.0f} min earlier",
        "hop_depth": f"Money has already made {f['hop_depth']:.0f} quick hop(s) before this payment",
        "sender_unique_payers_24h": f"Sender was paid by {f['sender_unique_payers_24h']:.0f} different accounts in 24h",
        "if_anomaly_score": "Overall pattern is unusual compared with normal UPI activity",
    }
    return t.get(feature, feature)


GENERIC = {"if_anomaly_score"}   # true but not actionable; used only if nothing concrete applies


def top_reasons(contrib_row: np.ndarray, names: Sequence[str], feats: Dict[str, float],
                raw: Dict, k: int = 3) -> List[str]:
    """Top-k positive contributions as sentences. Concrete signals come first;
    the generic 'unusual overall pattern' reason fills in only when needed."""
    order = [j for j in np.argsort(-contrib_row) if contrib_row[j] > 0.005]
    concrete = [j for j in order if names[j] not in GENERIC]
    generic = [j for j in order if names[j] in GENERIC]
    return [reason_text(names[j], feats, raw) for j in (concrete + generic)[:k]]


def explain_rows(explainer: ForestExplainer, X_model: pd.DataFrame, raw_df: pd.DataFrame,
                 k: int = 3) -> pd.DataFrame:
    """Return a DataFrame (same index as X_model) with `reasons` and per-feature contributions."""
    if len(X_model) == 0:
        return pd.DataFrame({"reasons": []})
    C = explainer.contributions(X_model.values)
    names = list(X_model.columns)
    reasons = []
    for i, idx in enumerate(X_model.index):
        feats = X_model.loc[idx].to_dict()
        raw = raw_df.loc[idx].to_dict() if idx in raw_df.index else {}
        reasons.append(" · ".join(top_reasons(C[i], names, feats, raw, k)))
    out = pd.DataFrame(C, columns=names, index=X_model.index)
    out.insert(0, "reasons", reasons)
    return out
