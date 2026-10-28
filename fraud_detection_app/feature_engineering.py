"""
Feature engineering for UPI scam & mule detection.

Design rules
------------
1. ONE code path. Batch scoring and real-time scoring both run through
   `FeatureEngine.process()`, one transaction at a time, in time order.
   Batch = "replay the file as a stream". So training features and
   live features can never drift apart.
2. No leakage. Every feature for a transaction is computed from the
   engine's state BEFORE that transaction is applied. Nothing from the
   future is ever used (tested in tests/test_pipeline.py).
3. Every feature has variance in the training data. Dead or duplicate
   features from the first version (transaction_frequency = 1.0 always,
   chain_length == hop_number, absolute transaction_step) were removed.

Feature groups (used for the ablation study)
--------------------------------------------
- amount_context     : what this single transaction looks like
- behaviour_velocity : how it compares with the sender's own history
- device             : device-binding signals (SIM swap / new registration)
- graph_flow         : temporal money-flow graph signals (fan-in, pass-through,
                       hop depth) - the per-transaction part of the graph layer.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Input schema
# ----------------------------------------------------------------------------
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

# Optional ground-truth columns. Never used for scoring; only for evaluation.
LABEL_COLUMNS: List[str] = ["is_fraud", "fraud_type"]

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

P2M_TYPES = {"P2M", "P2M_COLLECT"}
COLLECT_TYPES = {"P2M_COLLECT", "P2P_COLLECT"}

# ----------------------------------------------------------------------------
# Feature definitions
# ----------------------------------------------------------------------------
FEATURE_GROUPS: Dict[str, List[str]] = {
    "amount_context": [
        "amount_log",
        "sender_balance_ratio",
        "sender_old_balance_log",
        "receiver_old_balance_log",
        "transaction_hour",
        "is_night",
        "is_p2m",
        "is_collect",
    ],
    "behaviour_velocity": [
        "sender_txn_count_before_log",
        "txns_last_1h",
        "txns_last_24h",
        "minutes_since_prev_txn_log",
        "amount_zscore",
        "amount_vs_max_log",
        "is_new_recipient",
        "new_recipients_last_24h",
        "sender_night_ratio",
        "hour_deviation",
    ],
    "device": [
        "device_change_flag",
        "new_device_flag",
        "hours_since_device_change_log",
        "sent_since_device_change_log",
    ],
    "graph_flow": [
        "receiver_unique_senders_24h",
        "receiver_inflow_24h_log",
        "receiver_fanin_burst",
        "receiver_txn_count_before_log",
        "sender_inflow_60m_log",
        "forwarded_share",
        "minutes_since_sender_inflow_log",
        "hop_depth",
        "sender_unique_payers_24h",
    ],
}
FEATURES: List[str] = [f for group in FEATURE_GROUPS.values() for f in group]

# Plain-English descriptions, used by the dashboard and README.
FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "amount_log": "log(1 + amount in ₹)",
    "sender_balance_ratio": "amount ÷ sender balance before the payment (1.0 = whole balance)",
    "sender_old_balance_log": "log(1 + sender balance before)",
    "receiver_old_balance_log": "log(1 + receiver balance before)",
    "transaction_hour": "hour of day (0-23, fractional)",
    "is_night": "1 if between 22:00 and 06:00",
    "is_p2m": "1 if paid to a merchant (P2M / merchant collect)",
    "is_collect": "1 if it was an approved collect request",
    "sender_txn_count_before_log": "log(1 + number of earlier payments by the sender)",
    "txns_last_1h": "sender's payments in the previous 60 minutes",
    "txns_last_24h": "sender's payments in the previous 24 hours",
    "minutes_since_prev_txn_log": "log(1 + minutes since the sender's previous payment)",
    "amount_zscore": "how many std-devs this amount is above the sender's usual (log scale)",
    "amount_vs_max_log": "log-ratio of this amount to the sender's largest earlier payment",
    "is_new_recipient": "1 if the sender has never paid this receiver before",
    "new_recipients_last_24h": "new receivers the sender paid in the previous 24 hours",
    "sender_night_ratio": "share of the sender's earlier payments made at night",
    "hour_deviation": "hours between this payment and the sender's usual time of day",
    "device_change_flag": "1 if the device differs from the sender's previous payment",
    "new_device_flag": "1 if the sender has never used this device before",
    "hours_since_device_change_log": "log(1 + hours since the sender's last device change)",
    "sent_since_device_change_log": "log(1 + ₹ sent in the 24h after a device change)",
    "receiver_unique_senders_24h": "distinct accounts that paid the receiver in the last 24h (fan-in)",
    "receiver_inflow_24h_log": "log(1 + ₹ received by the receiver in the last 24h)",
    "receiver_fanin_burst": "share of the receiver's all-time payers that appeared in the last 24h",
    "receiver_txn_count_before_log": "log(1 + payments the receiver has received before)",
    "sender_inflow_60m_log": "log(1 + ₹ the sender itself received in the last 60 minutes)",
    "forwarded_share": "share of the sender's last-60-min inflow being passed on now",
    "minutes_since_sender_inflow_log": "log(1 + minutes since the sender last received money)",
    "hop_depth": "how many quick hops this money has already made (A→B→C…)",
    "sender_unique_payers_24h": "distinct accounts that paid the sender in the last 24h",
}

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
H1 = 3600
H24 = 24 * 3600
M60 = 60 * 60
NO_HISTORY_MIN = 30 * 24 * 60  # "never" encoded as 30 days, in minutes
NO_DEVICE_CHANGE_H = 30 * 24   # "never" encoded as 30 days, in hours
WARMUP_HOURS = 48              # rows in the first 48h of a file lack history
CHAIN_WINDOW = 60 * 60         # money counts as "passed on" if forwarded within 60 min


def _is_night(hour: float) -> bool:
    return hour < 6.0 or hour >= 22.0


class _Account:
    """Running state for one account (as sender and as receiver)."""

    __slots__ = (
        # sender side
        "n_sent", "mean_log", "m2_log", "max_amt", "n_night", "sin_sum", "cos_sum",
        "last_time", "sent_times", "recipients", "new_recip_times",
        "device_change_time", "sent_since_change",
        # receiver side
        "n_recv", "payers_all", "recv_window", "recv_window_counts", "recv_window_sum",
        "inflow_60", "inflow_60_sum", "last_inflow_time", "chain_depth", "chain_time",
    )

    def __init__(self) -> None:
        self.n_sent = 0
        self.mean_log = 0.0
        self.m2_log = 0.0
        self.max_amt = 0.0
        self.n_night = 0
        self.sin_sum = 0.0
        self.cos_sum = 0.0
        self.last_time = None
        self.sent_times: deque = deque()
        self.recipients: set = set()
        self.new_recip_times: deque = deque()
        self.device_change_time = None
        self.sent_since_change = 0.0
        self.n_recv = 0
        self.payers_all: set = set()
        self.recv_window: deque = deque()          # (t, payer, amount)
        self.recv_window_counts: Dict[str, int] = {}
        self.recv_window_sum = 0.0
        self.inflow_60: deque = deque()            # (t, amount)
        self.inflow_60_sum = 0.0
        self.last_inflow_time = None
        self.chain_depth = 0
        self.chain_time = None


class FeatureEngine:
    """
    Stateful, leak-free feature engine.

    Usage (streaming):
        engine = FeatureEngine()
        x = engine.process(txn_dict)   # returns np.ndarray in FEATURES order

    Usage (batch):
        feats, meta = compute_features(df)
    """

    def __init__(self) -> None:
        self.accounts: Dict[str, _Account] = {}
        self.first_time = None

    def _acct(self, key: str) -> _Account:
        a = self.accounts.get(key)
        if a is None:
            a = _Account()
            self.accounts[key] = a
        return a

    # ------------------------------------------------------------------
    def process(self, txn: Dict[str, Any]) -> np.ndarray:
        """Compute features for `txn` from past state, then update state."""
        t = float(txn["ts"])  # unix seconds
        if self.first_time is None:
            self.first_time = t
        s_id = str(txn["sender_id"])
        r_id = str(txn["receiver_id"])
        amount = float(txn["amount"])
        ttype = str(txn["transaction_type"]).upper()
        hour = float(txn["hour"])
        s_old = max(0.0, float(txn["sender_old_balance"]))
        r_old = max(0.0, float(txn["receiver_old_balance"]))
        dev_change = 1.0 if float(txn["device_change_flag"]) >= 0.5 else 0.0
        new_dev = 1.0 if float(txn["new_device_flag"]) >= 0.5 else 0.0

        s = self._acct(s_id)
        r = self._acct(r_id)
        log_amt = math.log1p(amount)
        night = _is_night(hour)

        # ---- expire windows (state up to, but not including, this txn) ----
        while s.sent_times and t - s.sent_times[0] > H24:
            s.sent_times.popleft()
        while s.new_recip_times and t - s.new_recip_times[0] > H24:
            s.new_recip_times.popleft()
        self._expire_recv(s, t)
        self._expire_recv(r, t)
        self._expire_inflow(s, t)

        # ---- amount_context ----
        balance_ratio = min(amount / (s_old + 1.0), 1.5)
        f_amount = [
            log_amt,
            balance_ratio,
            math.log1p(s_old),
            math.log1p(r_old),
            hour,
            1.0 if night else 0.0,
            1.0 if ttype in P2M_TYPES else 0.0,
            1.0 if ttype in COLLECT_TYPES else 0.0,
        ]

        # ---- behaviour_velocity ----
        n = s.n_sent
        txns_1h = 0
        for ts in reversed(s.sent_times):
            if t - ts <= H1:
                txns_1h += 1
            else:
                break
        if s.last_time is None:
            mins_prev = NO_HISTORY_MIN
        else:
            mins_prev = min((t - s.last_time) / 60.0, NO_HISTORY_MIN)
        if n >= 3:
            std = max(math.sqrt(s.m2_log / (n - 1)), 0.25)
            zscore = max(min((log_amt - s.mean_log) / std, 20.0), -10.0)
        else:
            zscore = 0.0
        amt_vs_max = (log_amt - math.log1p(s.max_amt)) if n >= 1 else 0.0
        is_new_recip = 0.0 if r_id in s.recipients else 1.0
        night_ratio = (s.n_night + 0.1) / (n + 2.0)
        if n >= 1:
            mean_angle = math.atan2(s.sin_sum, s.cos_sum)
            angle = 2 * math.pi * hour / 24.0
            diff = abs(math.atan2(math.sin(angle - mean_angle), math.cos(angle - mean_angle)))
            hour_dev = diff * 24.0 / (2 * math.pi)
        else:
            hour_dev = 0.0
        f_behaviour = [
            math.log1p(n),
            float(txns_1h),
            float(len(s.sent_times)),
            math.log1p(mins_prev),
            zscore,
            amt_vs_max,
            is_new_recip,
            float(len(s.new_recip_times)),
            night_ratio,
            hour_dev,
        ]

        # ---- device ----
        # A change on THIS payment counts as "0 hours since change".
        change_now = dev_change >= 0.5 or new_dev >= 0.5
        if change_now:
            hrs_since_change = 0.0
            sent_since_change = 0.0
        elif s.device_change_time is None:
            hrs_since_change = NO_DEVICE_CHANGE_H
            sent_since_change = 0.0
        else:
            hrs_since_change = min((t - s.device_change_time) / 3600.0, NO_DEVICE_CHANGE_H)
            sent_since_change = s.sent_since_change if hrs_since_change <= 24.0 else 0.0
        f_device = [
            dev_change,
            new_dev,
            math.log1p(hrs_since_change),
            math.log1p(sent_since_change),
        ]

        # ---- graph_flow ----
        r_uniq_24 = len(r.recv_window_counts)
        r_burst = r_uniq_24 / (len(r.payers_all) + 1.0)
        inflow_60 = s.inflow_60_sum
        forwarded = min(amount, inflow_60) / (inflow_60 + 1.0) if inflow_60 > 0 else 0.0
        if s.last_inflow_time is None:
            mins_inflow = NO_HISTORY_MIN
        else:
            mins_inflow = min((t - s.last_inflow_time) / 60.0, NO_HISTORY_MIN)
        if s.chain_time is not None and t - s.chain_time <= CHAIN_WINDOW:
            hop = float(s.chain_depth)
        else:
            hop = 0.0
        f_graph = [
            float(r_uniq_24),
            math.log1p(r.recv_window_sum),
            r_burst,
            math.log1p(r.n_recv),
            math.log1p(inflow_60),
            forwarded,
            math.log1p(mins_inflow),
            hop,
            float(len(s.recv_window_counts)),
        ]

        features = np.array(f_amount + f_behaviour + f_device + f_graph, dtype=float)

        # ================= update state with this transaction =================
        # sender
        s.n_sent = n + 1
        delta = log_amt - s.mean_log
        s.mean_log += delta / s.n_sent
        s.m2_log += delta * (log_amt - s.mean_log)
        s.max_amt = max(s.max_amt, amount)
        if night:
            s.n_night += 1
        angle = 2 * math.pi * hour / 24.0
        s.sin_sum += math.sin(angle)
        s.cos_sum += math.cos(angle)
        s.last_time = t
        s.sent_times.append(t)
        if is_new_recip:
            s.recipients.add(r_id)
            s.new_recip_times.append(t)
        if change_now:
            s.device_change_time = t
            s.sent_since_change = amount
        elif s.device_change_time is not None and t - s.device_change_time <= H24:
            s.sent_since_change += amount

        # receiver
        r.n_recv += 1
        r.payers_all.add(s_id)
        r.recv_window.append((t, s_id, amount))
        r.recv_window_counts[s_id] = r.recv_window_counts.get(s_id, 0) + 1
        r.recv_window_sum += amount
        r.inflow_60.append((t, amount))
        r.inflow_60_sum += amount
        r.last_inflow_time = t
        # money-flow chain: receiver's money is now `hop + 1` hops from its source
        r.chain_depth = int(hop) + 1
        r.chain_time = t

        return features

    # ------------------------------------------------------------------
    @staticmethod
    def _expire_recv(a: _Account, t: float) -> None:
        while a.recv_window and t - a.recv_window[0][0] > H24:
            _, payer, amt = a.recv_window.popleft()
            a.recv_window_sum -= amt
            c = a.recv_window_counts[payer] - 1
            if c <= 0:
                del a.recv_window_counts[payer]
            else:
                a.recv_window_counts[payer] = c
        if not a.recv_window:
            a.recv_window_sum = 0.0

    @staticmethod
    def _expire_inflow(a: _Account, t: float) -> None:
        while a.inflow_60 and t - a.inflow_60[0][0] > M60:
            _, amt = a.inflow_60.popleft()
            a.inflow_60_sum -= amt
        if not a.inflow_60:
            a.inflow_60_sum = 0.0


# ----------------------------------------------------------------------------
# Batch helpers
# ----------------------------------------------------------------------------
def prepare_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Parse types and add `ts` (unix seconds) and `hour` columns."""
    out = df.copy()
    parsed = pd.to_datetime(out["transaction_time"])
    # unit-safe conversion to unix seconds (pandas may use s/ms/us/ns internally)
    out["__ts__"] = (parsed - pd.Timestamp("1970-01-01")).dt.total_seconds()
    out["__hour__"] = parsed.dt.hour + parsed.dt.minute / 60.0
    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    return out


def compute_features(df: pd.DataFrame, engine: FeatureEngine | None = None
                     ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Replay a batch through the streaming engine in time order.

    Returns
    -------
    features : DataFrame (rows in the ORIGINAL order of `df`, columns = FEATURES)
    meta     : DataFrame with `warmup` (bool) and `hours_from_start` per row
    """
    engine = engine or FeatureEngine()
    prep = prepare_transactions(df)
    order = np.lexsort((np.arange(len(prep)), prep["__ts__"].to_numpy()))

    ts = prep["__ts__"].to_numpy(dtype=float)
    hours = prep["__hour__"].to_numpy(dtype=float)
    cols = {c: prep[c].to_numpy() for c in [
        "sender_id", "receiver_id", "amount", "transaction_type",
        "sender_old_balance", "receiver_old_balance",
        "device_change_flag", "new_device_flag"]}

    out = np.zeros((len(prep), len(FEATURES)), dtype=float)
    for i in order:
        out[i] = engine.process({
            "ts": ts[i],
            "hour": hours[i],
            "sender_id": cols["sender_id"][i],
            "receiver_id": cols["receiver_id"][i],
            "amount": cols["amount"][i],
            "transaction_type": cols["transaction_type"][i],
            "sender_old_balance": cols["sender_old_balance"][i],
            "receiver_old_balance": cols["receiver_old_balance"][i],
            "device_change_flag": cols["device_change_flag"][i],
            "new_device_flag": cols["new_device_flag"][i],
        })

    features = pd.DataFrame(out, columns=FEATURES, index=df.index)
    start = ts.min() if len(ts) else 0.0
    meta = pd.DataFrame({
        "hours_from_start": (ts - start) / 3600.0,
    }, index=df.index)
    meta["warmup"] = meta["hours_from_start"] < WARMUP_HOURS
    return features, meta


def row_to_txn(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one raw CSV-style record into the dict `FeatureEngine.process` expects."""
    ts = pd.Timestamp(row["transaction_time"])
    return {
        "ts": (ts - pd.Timestamp("1970-01-01")).total_seconds(),
        "hour": ts.hour + ts.minute / 60.0,
        "sender_id": row["sender_id"],
        "receiver_id": row["receiver_id"],
        "amount": row["amount"],
        "transaction_type": row["transaction_type"],
        "sender_old_balance": row["sender_old_balance"],
        "receiver_old_balance": row["receiver_old_balance"],
        "device_change_flag": row["device_change_flag"],
        "new_device_flag": row["new_device_flag"],
    }


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------
def validate_raw_csv(df: pd.DataFrame) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Check columns, nulls, duplicate IDs, numeric values and timestamps."""
    errors: List[str] = []
    metadata: Dict[str, Any] = {
        "total_rows": len(df),
        "total_cols": len(df.columns),
        "missing_cols": [],
        "null_counts": {},
        "duplicate_id_count": 0,
        "invalid_numeric_count": 0,
        "time_parse_errors": 0,
        "has_labels": "is_fraud" in df.columns,
    }

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        metadata["missing_cols"] = missing
        errors.append(f"Missing required column(s): {', '.join(missing)}")
        return False, errors, metadata

    if len(df) == 0:
        errors.append("The file has no rows.")
        return False, errors, metadata

    dup = df["transaction_id"].duplicated(keep=False)
    metadata["duplicate_id_count"] = int(dup.sum())
    if dup.any():
        sample = df.loc[dup, "transaction_id"].head(5).tolist()
        errors.append(f"Found {int(dup.sum())} duplicate transaction_id values (e.g. {sample}).")

    nulls = df[REQUIRED_COLUMNS].isnull().sum()
    nulls = {k: int(v) for k, v in nulls.items() if v > 0}
    metadata["null_counts"] = nulls
    if nulls:
        errors.append("Missing (null) values in: " + ", ".join(f"{k} ({v})" for k, v in nulls.items()))

    for col in NUMERIC_COLUMNS:
        num = pd.to_numeric(df[col], errors="coerce")
        bad = int(num.isnull().sum()) - int(df[col].isnull().sum())
        if bad > 0:
            errors.append(f"Column '{col}' has {bad} non-numeric values.")
        if col in ("amount",):
            nonpos = int((num <= 0).sum())
            if nonpos:
                metadata["invalid_numeric_count"] += nonpos
                errors.append(f"Column 'amount' has {nonpos} values ≤ 0.")
        elif col in ("transaction_step", "sender_old_balance", "sender_new_balance",
                     "receiver_old_balance", "receiver_new_balance"):
            neg = int((num < 0).sum())
            if neg:
                metadata["invalid_numeric_count"] += neg
                errors.append(f"Column '{col}' has {neg} negative values.")

    parsed = pd.to_datetime(df["transaction_time"], errors="coerce")
    bad_t = int(parsed.isnull().sum()) - int(df["transaction_time"].isnull().sum())
    if bad_t > 0:
        metadata["time_parse_errors"] = bad_t
        errors.append(f"Column 'transaction_time' has {bad_t} unparseable timestamps.")

    return len(errors) == 0, errors, metadata
