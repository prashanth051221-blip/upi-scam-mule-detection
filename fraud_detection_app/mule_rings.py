"""
Graph layer, part 2: mule-ring detection with NetworkX.

Part 1 of the graph layer lives in feature_engineering.py: per-transaction
money-flow features (fan-in, pass-through share, hop depth) that the model
scores in real time.

This module works on a whole batch after scoring, the way an investigator
would. It:
  1. builds a directed money-flow graph (accounts = nodes, payments = edges);
  2. finds "fast pass-through" links: B receives money and sends at least half
     of it on within 60 minutes (A→B→C);
  3. grows rings from alerted payments: alerted edges, plus pass-through edges
     touching an account already involved in an alert;
  4. keeps groups of 3+ accounts with at least 3 alerted payments, of which at
     least 5 alerted payments are fast pass-throughs (money really moving), and
     reports each as a candidate mule ring, with
     victims, collectors, cash-out accounts, total ₹ and time span;
  5. optionally escalates payments inside a ring that the model alone missed.

Because it looks at the whole batch (including payments that happen later),
ring detection is an investigation tool, not a real-time score.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd

PASS_WINDOW_MIN = 60
PASS_MIN_SHARE = 0.5


def pass_through_edges(df: pd.DataFrame) -> pd.Series:
    """Boolean per row: is this payment B→C a fast pass-through of money B just received?

    The incoming leg A→B is marked too, so a full A→B→C chain is captured."""
    t = pd.to_datetime(df["transaction_time"])
    ts = ((t - pd.Timestamp("1970-01-01")).dt.total_seconds()).to_numpy()
    snd = df["sender_id"].astype(str).to_numpy()
    rcv = df["receiver_id"].astype(str).to_numpy()
    amt = df["amount"].astype(float).to_numpy()
    flag = np.zeros(len(df), dtype=bool)
    window = PASS_WINDOW_MIN * 60

    inflows: Dict[str, List[int]] = defaultdict(list)
    outflows: Dict[str, List[int]] = defaultdict(list)
    for i in np.argsort(ts, kind="stable"):
        inflows[rcv[i]].append(i)
        outflows[snd[i]].append(i)

    for acct, ins in inflows.items():
        outs = outflows.get(acct)
        if not outs:
            continue
        out_idx = np.array(outs)
        out_t = ts[out_idx]
        out_amt = amt[out_idx]
        csum = np.concatenate([[0.0], np.cumsum(out_amt)])
        for j in ins:       # j = incoming payment A→B
            lo = np.searchsorted(out_t, ts[j], side="right")
            hi = np.searchsorted(out_t, ts[j] + window, side="right")
            if hi > lo and csum[hi] - csum[lo] >= PASS_MIN_SHARE * amt[j]:
                flag[j] = True
                flag[out_idx[lo:hi]] = True
    return pd.Series(flag, index=df.index)


def detect_rings(scored: pd.DataFrame, alert_col: str = "alert", min_accounts: int = 3,
                 min_alerted: int = 3, min_alerted_pass_through: int = 5
                 ) -> Tuple[List[dict], pd.Series, nx.DiGraph, pd.Series]:
    """
    Returns
    -------
    rings      : list of dicts (one per candidate ring), largest ₹ first
    ring_of    : Series (index = scored.index) with ring number or -1
    graph      : the suspicious sub-graph (for drawing)
    pass_thru  : Series of bool, fast pass-through payments (A→B→C within 60 min)
    """
    df = scored
    pt = pass_through_edges(df)
    alerted = df[alert_col].astype(bool)
    alert_accounts = set(df.loc[alerted, "sender_id"].astype(str)) | set(df.loc[alerted, "receiver_id"].astype(str))
    touches = df["sender_id"].astype(str).isin(alert_accounts) | df["receiver_id"].astype(str).isin(alert_accounts)
    # merchants are hubs for everyone; never let a merchant payment glue rings together
    is_p2m = df["transaction_type"].astype(str).str.upper().isin(["P2M"])
    keep = (alerted | (pt & touches)) & ~is_p2m

    G = nx.DiGraph()
    for idx, r in df.loc[keep].iterrows():
        u, v = str(r["sender_id"]), str(r["receiver_id"])
        if G.has_edge(u, v):
            e = G[u][v]
            e["amount"] += float(r["amount"])
            e["count"] += 1
            e["rows"].append(idx)
            e["alerted"] = e["alerted"] or bool(r[alert_col])
        else:
            G.add_edge(u, v, amount=float(r["amount"]), count=1, rows=[idx], alerted=bool(r[alert_col]))

    ring_of = pd.Series(-1, index=df.index)
    rings = []
    comps = [c for c in nx.weakly_connected_components(G) if len(c) >= min_accounts]
    comps.sort(key=lambda c: -sum(d["amount"] for _, _, d in G.subgraph(c).edges(data=True)))
    for k, comp in enumerate(comps):
        sub = G.subgraph(comp)
        n_alerted = sum(1 for _, _, d in sub.edges(data=True) if d["alerted"])
        if n_alerted < min_alerted:  # need several independent alerts to call it a ring
            continue
        rows = [i for _, _, d in sub.edges(data=True) for i in d["rows"]]
        # real rings move money: several alerted payments must also be fast pass-throughs.
        # (False groups formed by a few unrelated false alerts almost never meet this.)
        if int((df.loc[rows, alert_col].astype(bool) & pt.loc[rows]).sum()) < min_alerted_pass_through:
            continue
        times = pd.to_datetime(df.loc[rows, "transaction_time"])
        sources = [n for n in sub if sub.in_degree(n) == 0]
        sinks = [n for n in sub if sub.out_degree(n) == 0]
        collectors = sorted(sub.nodes, key=lambda n: -sub.in_degree(n))[:3]
        try:
            longest = nx.dag_longest_path_length(sub) if nx.is_directed_acyclic_graph(sub) else None
        except Exception:
            longest = None
        ring_id = len(rings)
        ring_of.loc[rows] = ring_id
        pr = nx.pagerank(sub, weight="amount") if sub.number_of_edges() else {}
        rings.append({
            "ring": ring_id,
            "accounts": len(comp),
            "payments": len(rows),
            "alerted_payments": int(df.loc[rows, alert_col].sum()),
            "total_amount": float(df.loc[rows, "amount"].sum()),
            "victims_or_sources": len(sources),
            "cash_out_accounts": len(sinks),
            "longest_chain_hops": longest,
            "first_seen": str(times.min()),
            "last_seen": str(times.max()),
            "key_accounts": ", ".join(sorted(pr, key=pr.get, reverse=True)[:3]),
            "collectors": ", ".join(collectors),
            "nodes": list(comp),
        })
    return rings, ring_of, G, pt


def escalate(scored: pd.DataFrame, ring_of: pd.Series, pass_thru: pd.Series,
             score_col: str = "fraud_score", alert_col: str = "alert", min_score: float = 0.05) -> pd.Series:
    """Payments the model did NOT alert on, but which sit inside a detected ring,
    are a fast pass-through, and have at least a small model score.
    Tuned on the training/validation weeks; see RESULTS.md section 6."""
    return ((ring_of >= 0) & pass_thru & (scored[score_col] >= min_score) & ~scored[alert_col].astype(bool))


def ring_dot(G: nx.DiGraph, nodes: List[str], max_edges: int = 80) -> str:
    """Graphviz DOT text for one ring (rendered by st.graphviz_chart)."""
    sub = G.subgraph(nodes)
    lines = ["digraph ring {", 'rankdir=LR;', 'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];']
    for n in sub.nodes:
        if sub.in_degree(n) == 0:
            color = "#dbeafe"   # source / victim
        elif sub.out_degree(n) == 0:
            color = "#fee2e2"   # cash-out
        else:
            color = "#fef3c7"   # mule in the middle
        lines.append(f'"{n}" [fillcolor="{color}"];')
    edges = sorted(sub.edges(data=True), key=lambda e: -e[2]["amount"])[:max_edges]
    for u, v, d in edges:
        style = "bold" if d["alerted"] else "dashed"
        lines.append(f'"{u}" -> "{v}" [label="₹{d["amount"]:,.0f}", style={style}, fontsize=9];')
    lines.append("}")
    return "\n".join(lines)
