"""
Glue between the website and the ML code in fraud_detection_app/.

Nothing here re-implements the model: scoring, reasons and ring detection come
from scoring.py, explain.py and mule_rings.py, exactly as used in training,
tests and the real-time demo.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from django.conf import settings

from explain import ForestExplainer, explain_rows, reason_text
from feature_engineering import FEATURE_DESCRIPTIONS, REQUIRED_COLUMNS, validate_raw_csv
from mule_rings import detect_rings, escalate
from scoring import load_bundle, risk_level, score_batch

APP_DIR: Path = settings.APP_CODE_DIR

DEMOS = {
    "normal": {
        "file": "dataset_1_normal_baseline.csv",
        "title": "Normal activity only",
        "text": "7 days of everyday payments with no fraud. A good model should stay quiet here.",
    },
    "scams": {
        "file": "dataset_2_scam_attacks.csv",
        "title": "Scams and mule accounts",
        "text": "QR scams, fake refund calls, screen-share drains, SIM swaps and fake-merchant collect requests.",
    },
    "rings": {
        "file": "dataset_3_mule_rings.csv",
        "title": "Deep mule rings",
        "text": "Stolen money passed through 3–4 layers of mule accounts within minutes.",
    },
}

COST_CHOICES = [50, 200, 1000, 5000]
DEFAULT_SETTINGS = {"mode": "cost", "review_cost": 200, "capacity": 2.0, "rings": True}


@lru_cache(maxsize=1)
def model():
    bundle = load_bundle()
    return bundle, ForestExplainer(bundle["model"], bundle["model_features"])


# ----------------------------------------------------------------------------
# Datasets
# ----------------------------------------------------------------------------
def dataset_path(key: str) -> Optional[Path]:
    if key.startswith("demo:"):
        d = DEMOS.get(key[5:])
        return APP_DIR / d["file"] if d else None
    if key.startswith("upload:"):
        p = settings.UPLOAD_DIR / f"{key[7:]}.csv"
        return p if p.exists() else None
    return None


def dataset_label(key: str, upload_name: str = "") -> str:
    if key.startswith("demo:") and key[5:] in DEMOS:
        return DEMOS[key[5:]]["title"]
    return upload_name or "Uploaded file"


def save_upload(uploaded) -> tuple[str, list[str]]:
    """Validate and store an uploaded CSV. Returns (dataset key, errors)."""
    try:
        df = pd.read_csv(uploaded)
    except Exception as e:  # noqa: BLE001
        return "", [f"Could not read the file as CSV: {e}"]
    ok, errors, _ = validate_raw_csv(df)
    if not ok:
        return "", errors
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:12]
    df.to_csv(settings.UPLOAD_DIR / f"{uid}.csv", index=False)
    return f"upload:{uid}", []


# ----------------------------------------------------------------------------
# Analysis (cached per dataset + settings)
# ----------------------------------------------------------------------------
@dataclass
class Analysis:
    key: str
    settings: dict
    scored: pd.DataFrame
    Xm: pd.DataFrame
    rings: List[dict]
    graph: object
    alert_threshold: float
    high_threshold: float
    has_labels: bool
    reasons: Dict[int, str] = field(default_factory=dict)

    # ---- summaries ---------------------------------------------------------
    @property
    def live(self) -> pd.Series:
        return ~self.scored["warmup"]

    def kpis(self) -> dict:
        s, live = self.scored, self.live
        flag = s["flagged"]
        n_live = int(live.sum())
        out = {
            "payments": len(s),
            "scored": n_live,
            "warmup": int((~live).sum()),
            "alerts": int(flag.sum()),
            "alert_rate": flag.sum() / max(n_live, 1),
            "high": int((s["risk_level"] == "High").sum()),
            "medium": int(s["risk_level"].isin(["Medium", "Medium (ring)"]).sum()),
            "escalated": int(s["escalated"].sum()),
            "amount_in_alerts": float(s.loc[flag, "amount"].sum()),
            "rings": len(self.rings),
            "threshold": self.alert_threshold * 100,
            "high_threshold": self.high_threshold * 100,
        }
        if self.has_labels:
            y = s["is_fraud"].astype(int)
            yl, fl = y[live], flag[live]
            tp = int((fl & (yl == 1)).sum())
            fp = int((fl & (yl == 0)).sum())
            fn = int((~fl & (yl == 1)).sum())
            out.update({
                "frauds": int(yl.sum()),
                "caught": tp,
                "recall": tp / max(tp + fn, 1) if yl.sum() else None,
                "precision": tp / max(tp + fp, 1) if (tp + fp) else None,
                "false_alert_rate": fp / max(int((yl == 0).sum()), 1),
                "false_alerts": fp,
                "missed_amount": float(s.loc[live & (y == 1) & ~flag, "amount"].sum()),
            })
        return out

    def charts(self) -> dict:
        s, live, flag = self.scored, self.live, self.scored["flagged"]
        t = pd.to_datetime(s["transaction_time"])
        start = t.min().floor("D")
        block = ((t - start).dt.total_seconds() // (6 * 3600)).astype(int)   # 6-hour blocks
        n_blocks = int(block.max()) + 1 if len(block) else 0
        labels = [(start + pd.Timedelta(hours=6 * b)).strftime("%d %b %H:00") for b in range(n_blocks)]
        lvl = s["risk_level"]
        def per_block(mask):
            return s[mask].groupby(block[mask]).size().reindex(range(n_blocks), fill_value=0).astype(int).tolist()
        warm_blocks = s[~live].groupby(block[~live]).size().reindex(range(n_blocks), fill_value=0)
        by_type = s[flag].groupby("transaction_type").size().sort_values(ascending=False)
        n_live = int(live.sum())
        risk = []
        for name, mask, key in [("High risk", lvl == "High", "high"),
                                ("Medium risk", lvl.isin(["Medium", "Medium (ring)"]), "med"),
                                ("Low risk", lvl == "Low", "low"),
                                ("Warm-up (not scored)", lvl == "Warm-up", "warm")]:
            c = int(mask.sum())
            risk.append({"label": name, "count": c, "key": key,
                         "share": c / max(n_live, 1) if key != "warm" else c / max(len(s), 1)})
        return {
            "labels": labels,
            "high": per_block(lvl == "High"),
            "medium": per_block(lvl.isin(["Medium", "Medium (ring)"])),
            "payments": per_block(pd.Series(True, index=s.index)),
            "warm_until": int((warm_blocks > 0).sum()),
            "type_labels": by_type.index.astype(str).tolist(),
            "type_counts": by_type.astype(int).tolist(),
            "risk": risk,
        }

    def type_breakdown(self) -> List[dict]:
        """Recall per fraud type (labelled files only)."""
        if not self.has_labels:
            return []
        s = self.scored[self.live & (self.scored["is_fraud"] == 1)]
        rows = []
        for ft, g in s.groupby("fraud_type"):
            rows.append({"type": str(ft).replace("_", " "), "count": len(g),
                         "caught": int(g["flagged"].sum()), "recall": g["flagged"].mean()})
        return sorted(rows, key=lambda r: -r["count"])


_CACHE: "OrderedDict[tuple, Analysis]" = OrderedDict()
_BASE: "OrderedDict[str, tuple]" = OrderedDict()
_LOCK = threading.Lock()


def _base_scores(key: str):
    with _LOCK:
        if key in _BASE:
            _BASE.move_to_end(key)
            return _BASE[key]
    path = dataset_path(key)
    if path is None:
        return None
    bundle, _ = model()
    raw = pd.read_csv(path)
    scored, Xm = score_batch(raw, bundle)
    with _LOCK:
        _BASE[key] = (scored, Xm)
        while len(_BASE) > 3:
            _BASE.popitem(last=False)
    return scored, Xm


def analyse(key: str, cfg: dict) -> Optional[Analysis]:
    cfg = {**DEFAULT_SETTINGS, **(cfg or {})}
    cache_key = (key, cfg["mode"], cfg["review_cost"], cfg["capacity"], cfg["rings"])
    with _LOCK:
        if cache_key in _CACHE:
            _CACHE.move_to_end(cache_key)
            return _CACHE[cache_key]
    base = _base_scores(key)
    if base is None:
        return None
    bundle, explainer = model()
    scored, Xm = base[0].copy(), base[1]
    live = ~scored["warmup"]

    # threshold
    if cfg["mode"] == "capacity":
        share = float(cfg["capacity"]) / 100
        th = float(np.quantile(scored.loc[live, "fraud_score"], 1 - share)) if live.any() else 1.0
    else:
        options = {o["review_cost_rupees"]: o["threshold"] for o in bundle.get("threshold_options", [])}
        th = options.get(int(cfg["review_cost"]), bundle["thresholds"]["alert"])
    high = max(bundle["thresholds"]["high"], th)

    scored["alert"] = (scored["fraud_score"] >= th) & live
    scored["risk_level"] = np.where(scored["warmup"], "Warm-up",
                                    risk_level(scored["fraud_score"].to_numpy(), {"alert": th, "high": high}))
    # rings are built only from scored payments: warm-up rows have no history and no score
    rings, ring_of, G, pass_thru = detect_rings(scored.loc[live], "alert")
    ring_of = ring_of.reindex(scored.index, fill_value=-1)
    pass_thru = pass_thru.reindex(scored.index, fill_value=False)
    scored["ring"] = ring_of.astype(int)
    scored["escalated"] = False
    if cfg["rings"]:
        esc = escalate(scored, ring_of, pass_thru, min_score=bundle.get("escalation_min_score", 0.05)) & live
        scored["escalated"] = esc
        scored.loc[esc, "risk_level"] = "Medium (ring)"
    scored["flagged"] = scored["alert"] | scored["escalated"]

    # reasons for every flagged payment
    idx = scored.index[scored["flagged"]].tolist()[:3000]
    reasons = {}
    if idx:
        ex = explain_rows(explainer, Xm.loc[idx], scored.loc[idx])
        reasons = ex["reasons"].to_dict()
    for i in scored.index[scored["escalated"]]:
        reasons[i] = "Inside a mule ring and passes money on within 60 min · " + reasons.get(i, "")

    a = Analysis(key=key, settings=cfg, scored=scored, Xm=Xm, rings=rings, graph=G,
                 alert_threshold=th, high_threshold=high,
                 has_labels="is_fraud" in scored.columns, reasons=reasons)
    with _LOCK:
        _CACHE[cache_key] = a
        while len(_CACHE) > 6:
            _CACHE.popitem(last=False)
    return a


# ----------------------------------------------------------------------------
# Detail helpers
# ----------------------------------------------------------------------------
def explain_one(a: Analysis, row_idx) -> dict:
    bundle, explainer = model()
    names = bundle["model_features"]
    contrib = explainer.contributions(a.Xm.loc[[row_idx]].values)[0]
    feats = a.Xm.loc[row_idx].to_dict()
    raw = a.scored.loc[row_idx].to_dict()
    order = np.argsort(-np.abs(contrib))
    top = [{"text": reason_text(names[j], feats, raw), "points": float(contrib[j] * 100)} for j in order[:10]]
    table = [{"name": n, "value": feats[n], "points": float(contrib[j] * 100),
              "meaning": FEATURE_DESCRIPTIONS.get(n, "Isolation Forest anomaly score (higher = more unusual)")}
             for j, n in enumerate(names)]
    table.sort(key=lambda r: -abs(r["points"]))
    return {"top": top, "table": table, "baseline": explainer.bias * 100}


def ring_graph_json(a: Analysis, ring: dict, max_edges: int = 150) -> dict:
    import networkx as nx
    G = a.graph.subgraph(ring["nodes"])
    # column for the left-to-right layout: how many hops from where money enters
    sources = [n for n in G.nodes if G.in_degree(n) == 0] or list(G.nodes)[:1]
    depth = {}
    for src in sources:
        for n, d in nx.single_source_shortest_path_length(G, src).items():
            depth[n] = max(depth.get(n, 0), d)
    nodes = []
    for n in G.nodes:
        if G.in_degree(n) == 0:
            role = "source"
        elif G.out_degree(n) == 0:
            role = "cashout"
        else:
            role = "mule"
        nodes.append({"id": n, "label": n, "role": role, "level": int(depth.get(n, 1)),
                      "inflow": float(sum(d["amount"] for _, _, d in G.in_edges(n, data=True))),
                      "outflow": float(sum(d["amount"] for _, _, d in G.out_edges(n, data=True)))})
    edges = sorted(G.edges(data=True), key=lambda e: -e[2]["amount"])[:max_edges]
    return {
        "nodes": nodes,
        "edges": [{"from": u, "to": v, "amount": float(d["amount"]), "count": int(d["count"]),
                   "alerted": bool(d["alerted"])} for u, v, d in edges],
    }
