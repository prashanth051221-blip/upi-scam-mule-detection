"""Page views. All heavy lifting lives in services.py."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import services

PAGE_SIZE = 25


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _cfg(request) -> dict:
    return {**services.DEFAULT_SETTINGS, **request.session.get("settings", {})}


def _analysis(request):
    key = request.session.get("dataset")
    if not key:
        return None
    return services.analyse(key, _cfg(request))


def _need_data(view):
    def wrapped(request, *args, **kwargs):
        a = _analysis(request)
        if a is None:
            request.session.pop("dataset", None)
            return redirect("start")
        return view(request, a, *args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def _reasons(text: str) -> list[str]:
    return [r.strip() for r in (text or "").split(" · ") if r.strip()]


def _row(a, idx) -> dict:
    r = a.scored.loc[idx]
    out = {
        "idx": idx,
        "id": r["transaction_id"],
        "time": pd.Timestamp(r["transaction_time"]),
        "sender": r["sender_id"],
        "receiver": r["receiver_id"],
        "amount": float(r["amount"]),
        "type": str(r["transaction_type"]),
        "score": float(r["fraud_score"]) * 100,
        "level": r["risk_level"],
        "ring": int(r["ring"]) if int(r["ring"]) >= 0 else None,
        "escalated": bool(r["escalated"]),
        "reasons": _reasons(a.reasons.get(idx, "")),
    }
    if a.has_labels:
        out["truth"] = str(r["fraud_type"]).replace("_", " ") if int(r["is_fraud"]) == 1 else "normal"
        out["is_fraud"] = int(r["is_fraud"]) == 1
    return out


# ----------------------------------------------------------------------------
# start / dataset / settings
# ----------------------------------------------------------------------------
def start(request):
    if request.method == "POST":
        f = request.FILES.get("csv")
        if not f:
            messages.error(request, "Choose a CSV file to upload.")
            return redirect("start")
        key, errors = services.save_upload(f)
        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("start")
        request.session["dataset"] = key
        request.session["upload_name"] = f.name
        return redirect("overview")
    demos = [{"slug": k, **v} for k, v in services.DEMOS.items()]
    return render(request, "dashboard/start.html", {"demos": demos})


def load_demo(request, slug):
    if slug not in services.DEMOS:
        raise Http404("Unknown demo dataset")
    request.session["dataset"] = f"demo:{slug}"
    request.session.pop("upload_name", None)
    return redirect("overview")


@require_POST
def update_settings(request):
    cfg = _cfg(request)
    mode = request.POST.get("mode", cfg["mode"])
    cfg["mode"] = mode if mode in ("cost", "capacity") else "cost"
    try:
        rc = int(request.POST.get("review_cost", cfg["review_cost"]))
        cfg["review_cost"] = rc if rc in services.COST_CHOICES else 200
    except ValueError:
        pass
    try:
        cap = float(request.POST.get("capacity", cfg["capacity"]))
        cfg["capacity"] = min(max(cap, 0.5), 10.0)
    except ValueError:
        pass
    cfg["rings"] = request.POST.get("rings") == "on"
    request.session["settings"] = cfg
    nxt = request.POST.get("next") or reverse("overview")
    return redirect(nxt if nxt.startswith("/") else reverse("overview"))


# ----------------------------------------------------------------------------
# overview
# ----------------------------------------------------------------------------
@_need_data
def overview(request, a):
    s = a.scored
    top = s[s["flagged"]].sort_values("fraud_score", ascending=False).head(8)
    ctx = {
        "a": a,
        "k": a.kpis(),
        "charts_json": a.charts(),
        "type_rows": a.type_breakdown(),
        "top_alerts": [_row(a, i) for i in top.index],
        "rings": a.rings[:5],
    }
    return render(request, "dashboard/overview.html", ctx)


# ----------------------------------------------------------------------------
# alert queue
# ----------------------------------------------------------------------------
@_need_data
def alerts(request, a):
    s = a.scored
    view = request.GET.get("view", "alerts")
    level = request.GET.get("level", "")
    ptype = request.GET.get("type", "")
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "score")
    truth = request.GET.get("truth", "")

    m = pd.Series(True, index=s.index)
    if view == "alerts":
        m &= s["flagged"]
    elif view == "scored":
        m &= ~s["warmup"]
    if level == "High":
        m &= s["risk_level"] == "High"
    elif level == "Medium":
        m &= s["risk_level"] == "Medium"
    elif level == "ring":
        m &= s["ring"] >= 0
    if ptype:
        m &= s["transaction_type"].astype(str) == ptype
    if q:
        ql = q.lower()
        m &= (s["transaction_id"].astype(str).str.lower().str.contains(ql, regex=False)
              | s["sender_id"].astype(str).str.lower().str.contains(ql, regex=False)
              | s["receiver_id"].astype(str).str.lower().str.contains(ql, regex=False))
    if a.has_labels and truth in ("fraud", "normal"):
        m &= s["is_fraud"] == (1 if truth == "fraud" else 0)

    sub = s[m]
    key = {"score": ("fraud_score", False), "amount": ("amount", False),
           "time": ("transaction_time", True), "time_desc": ("transaction_time", False)}.get(sort, ("fraud_score", False))
    sub = sub.sort_values(key[0], ascending=key[1], kind="stable")
    total = len(sub)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    try:
        page = min(max(int(request.GET.get("page", 1)), 1), pages)
    except ValueError:
        page = 1
    rows = [_row(a, i) for i in sub.index[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]]

    params = request.GET.copy()
    params.pop("page", None)
    ctx = {
        "a": a, "rows": rows, "total": total, "page": page, "pages": pages,
        "first": (page - 1) * PAGE_SIZE + 1 if total else 0, "last": min(page * PAGE_SIZE, total),
        "f": {"view": view, "level": level, "type": ptype, "q": q, "sort": sort, "truth": truth},
        "types": sorted(s["transaction_type"].astype(str).unique()),
        "qs": params.urlencode(),
        "amount_total": float(sub["amount"].sum()),
    }
    return render(request, "dashboard/alerts.html", ctx)


# ----------------------------------------------------------------------------
# single payment
# ----------------------------------------------------------------------------
@_need_data
def payment(request, a, txn_id):
    s = a.scored
    hit = s.index[s["transaction_id"].astype(str) == txn_id]
    if len(hit) == 0:
        raise Http404("Payment not found in the loaded file")
    idx = hit[0]
    row = _row(a, idx)
    r = s.loc[idx]
    if not row["reasons"]:
        row["reasons"] = [t["text"] for t in services.explain_one(a, idx)["top"] if t["points"] > 0.5][:3]
    ex = services.explain_one(a, idx)
    t = pd.to_datetime(s["transaction_time"])
    same_sender = s[(s["sender_id"] == r["sender_id"]) & (s.index != idx)]
    order = (t[same_sender.index] - t[idx]).abs().sort_values().index[:8]
    sender_rows = sorted([_row(a, i) for i in order], key=lambda x: x["time"])
    into_receiver = s[(s["receiver_id"] == r["receiver_id"]) & (s.index != idx)]
    order_r = (t[into_receiver.index] - t[idx]).abs().sort_values().index[:8]
    receiver_rows = sorted([_row(a, i) for i in order_r], key=lambda x: x["time"])
    contrib = {
        "labels": [x["text"] for x in ex["top"]],
        "points": [round(x["points"], 2) for x in ex["top"]],
    }
    ctx = {
        "a": a, "p": row, "raw": r, "ex": ex, "contrib_json": contrib,
        "sender_rows": sender_rows, "receiver_rows": receiver_rows,
        "n_sender": len(same_sender), "n_receiver": len(into_receiver),
        "device_flags": {"changed": int(r["device_change_flag"]), "new": int(r["new_device_flag"])},
        "warmup": bool(r["warmup"]),
    }
    return render(request, "dashboard/payment.html", ctx)


# ----------------------------------------------------------------------------
# mule rings
# ----------------------------------------------------------------------------
@_need_data
def rings(request, a, ring=None):
    if not a.rings:
        return render(request, "dashboard/rings.html", {"a": a, "rings": [], "sel": None})
    if ring is None:
        ring = 0
    if ring < 0 or ring >= len(a.rings):
        raise Http404("Ring not found")
    sel = a.rings[ring]
    s = a.scored
    pay = s[s["ring"] == ring].sort_values("transaction_time")
    rows = [_row(a, i) for i in pay.index]
    fraud_share = float(pay["is_fraud"].mean()) if a.has_labels and len(pay) else None
    ctx = {
        "a": a, "rings": a.rings, "sel": sel, "rows": rows,
        "graph_json": services.ring_graph_json(a, sel),
        "fraud_share": fraud_share,
        "span_hours": (pd.Timestamp(sel["last_seen"]) - pd.Timestamp(sel["first_seen"])).total_seconds() / 3600,
    }
    return render(request, "dashboard/rings.html", ctx)


# ----------------------------------------------------------------------------
# model evidence
# ----------------------------------------------------------------------------
def evidence(request):
    p = settings.PROJECT_ROOT / "results" / "metrics.json"
    if not p.exists():
        return render(request, "dashboard/evidence.html", {"missing": True})
    M = json.loads(p.read_text())
    comp = sorted(M["comparison"], key=lambda r: r["model"])
    ab = M["ablation"]
    ab_rows = []
    for feat in dict.fromkeys(r["features"] for r in ab):
        i = next(r for r in ab if r["features"] == feat and r["model"] == "Isolation Forest")
        f = next(r for r in ab if r["features"] == feat and r["model"] == "Random Forest")
        ab_rows.append({"features": feat, "n": f["n_features"], "if_pr": i["pr_auc"], "rf_pr": f["pr_auc"],
                        "rf_recall": f["budget_recall"], "mule": f["mule_recall_budget"]})
    types = ["qr_scam", "fake_refund_call", "screen_share", "sim_swap", "fake_merchant_collect", "mule_layering"]
    ctx = {
        "missing": False,
        "comp": comp,
        "ab_rows": ab_rows,
        "unseen": M["unseen_scams"],
        "rbt": M["recall_by_type"],
        "types": types,
        "type_labels": [t.replace("_", " ") for t in types],
        "rings": M["graph_rings"],
        "cost": M["cost_sensitivity"],
        "data": M["data"],
        "latency": M.get("latency"),
        "expl": M["explanations"],
        "th": M["thresholds"],
    }
    return render(request, "dashboard/evidence.html", ctx)


# ----------------------------------------------------------------------------
# export
# ----------------------------------------------------------------------------
@_need_data
def export(request, a, kind):
    s = a.scored.copy()
    s["reasons"] = [a.reasons.get(i, "") for i in s.index]
    if kind == "alerts":
        s = s[s["flagged"]]
    elif kind != "all":
        raise Http404()
    resp = HttpResponse(s.to_csv(index=False), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{kind}_scored_payments.csv"'
    return resp
