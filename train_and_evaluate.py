"""
Train and evaluate the UPI scam & mule detection models.

Everything the project claims is produced here, from data to numbers:

  1. load (or generate) the labelled UPI simulation             -> data/
  2. compute features with the SAME engine the dashboard uses
  3. time-based split: warm-up | train | validation | test
  4. compare approaches: rules, Isolation Forest, Random Forest, hybrid
  5. ablation: what each feature group adds
  6. unseen-scam test: hold one scam type out of training completely
  7. thresholds chosen like a bank would (validation set only):
       - cost-based  : minimise missed ₹ + review cost per alert
       - alert budget: analysts can review a fixed share of daily volume
  8. graph layer: does NetworkX ring detection add recall on top of the model?
  9. save the model bundle used by the dashboard   -> fraud_detection_app/models/
 10. build and evaluate the three labelled demo datasets
 11. write RESULTS.md and charts                    -> results/

Run:  python train_and_evaluate.py            (about 10 minutes on a laptop)
The notebook notebooks/train_and_evaluate.ipynb runs the same steps cell by cell.
"""

from __future__ import annotations

import json
import pickle
import platform
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "fraud_detection_app"
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(ROOT))

import upi_simulator as sim  # noqa: E402
from explain import ForestExplainer, explain_rows  # noqa: E402
from feature_engineering import FEATURE_GROUPS, FEATURES, compute_features  # noqa: E402
from mule_rings import detect_rings  # noqa: E402

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
MODEL_DIR = APP_DIR / "models"
TRAIN_DATA = DATA_DIR / "upi_sim_train.csv.gz"

# ----------------------------------------------------------------------------
# Settings (all assumptions in one place)
# ----------------------------------------------------------------------------
SIM_SETTINGS = dict(n_customers=4000, n_merchants=250, days=30, seed=7)
WARMUP_DAYS, TRAIN_END, VAL_END = 2, 18, 23          # test = day 23 onwards
REVIEW_COST = 200          # ₹ cost of one analyst review (time + customer friction). Assumption.
ALERT_BUDGET_SHARE = 0.02  # analysts can review 2% of daily payments. Assumption.
HIGH_RISK_PRECISION = 0.90 # "High risk" tier = threshold where validation precision ≥ 90%
SEED = 42

TABULAR = FEATURE_GROUPS["amount_context"] + FEATURE_GROUPS["behaviour_velocity"] + FEATURE_GROUPS["device"]
ALL = FEATURES
RF_PARAMS = dict(n_estimators=200, min_samples_leaf=2, max_depth=16, max_features="sqrt",
                 class_weight="balanced_subsample", n_jobs=-1, random_state=SEED)
IF_PARAMS = dict(n_estimators=200, max_samples=512, random_state=SEED, n_jobs=-1)

# Chart colours (fixed categorical order, validated palette)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
def load_data(regenerate: bool = False) -> pd.DataFrame:
    DATA_DIR.mkdir(exist_ok=True)
    if regenerate or not TRAIN_DATA.exists():
        log("Simulating training data ...")
        df = sim.simulate(**SIM_SETTINGS)
        df.to_csv(TRAIN_DATA, index=False)
    else:
        df = pd.read_csv(TRAIN_DATA)
    df["fraud_type"] = df["fraud_type"].fillna("")
    return df


def build_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    X, meta = compute_features(df)
    meta["day"] = meta["hours_from_start"] / 24.0
    return X, meta


def split_masks(meta: pd.DataFrame) -> Dict[str, np.ndarray]:
    d = meta["day"].to_numpy()
    return {
        "train": (d >= WARMUP_DAYS) & (d < TRAIN_END),
        "val": (d >= TRAIN_END) & (d < VAL_END),
        "test": d >= VAL_END,
    }


# ----------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------
def rules_score(X: pd.DataFrame) -> np.ndarray:
    """A typical hand-written rule set (no learning). Score = number of rules fired."""
    amount = np.expm1(X["amount_log"])
    r = np.zeros(len(X))
    r += ((amount >= 20_000) & (X["is_new_recipient"] >= 0.5)).to_numpy()          # big payment to new payee
    r += (X["sender_balance_ratio"] >= 0.7).to_numpy()                               # balance wipe-out
    r += ((X["is_night"] >= 0.5) & ((X["device_change_flag"] + X["new_device_flag"]) >= 1)).to_numpy()  # night + new device
    r += (X["txns_last_1h"] >= 3).to_numpy()                                         # burst
    r += (X["amount_zscore"] >= 3).to_numpy()                                        # unusually large for this sender
    return r + X["amount_log"].to_numpy() / 100.0      # tiny tie-break so a PR curve exists


def fit_if(X: pd.DataFrame, cols: List[str]):
    scaler = StandardScaler().fit(X[cols])
    iso = IsolationForest(**IF_PARAMS).fit(scaler.transform(X[cols]))
    return scaler, iso, list(cols)


def score_if(model, X: pd.DataFrame) -> np.ndarray:
    scaler, iso, cols = model
    return -iso.decision_function(scaler.transform(X[cols]))   # higher = more anomalous


def fit_rf(X: pd.DataFrame, y: np.ndarray, cols: List[str]) -> RandomForestClassifier:
    return RandomForestClassifier(**RF_PARAMS).fit(X[cols], y)


def with_if(X: pd.DataFrame, if_model) -> pd.DataFrame:
    Z = X.copy()
    Z["if_anomaly_score"] = score_if(if_model, X)
    return Z


HYBRID_COLS = ALL + ["if_anomaly_score"]


# ----------------------------------------------------------------------------
# Thresholds and metrics
# ----------------------------------------------------------------------------
def cost_threshold(y: np.ndarray, s: np.ndarray, amount: np.ndarray, review_cost: float = REVIEW_COST) -> float:
    """Threshold minimising (₹ of fraud missed) + review_cost × (number of alerts)."""
    order = np.argsort(-s)
    s_sorted, y_sorted, a_sorted = s[order], y[order], amount[order]
    fraud_total = float((amount * y).sum())
    caught = np.cumsum(a_sorted * y_sorted)
    n_alerts = np.arange(1, len(s) + 1)
    cost = (fraud_total - caught) + review_cost * n_alerts
    # only cut between distinct scores
    valid = np.r_[s_sorted[:-1] > s_sorted[1:], True]
    cost = np.where(valid, cost, np.inf)
    k = int(np.argmin(cost))
    if fraud_total <= cost[k]:      # alerting nothing is cheaper
        return float(s_sorted[0] + 1e-9)
    return float(s_sorted[k])


def budget_threshold(s: np.ndarray, share: float = ALERT_BUDGET_SHARE) -> float:
    """Threshold that alerts on the top `share` of payments."""
    return float(np.quantile(s, 1 - share))


def precision_threshold(y: np.ndarray, s: np.ndarray, target: float = HIGH_RISK_PRECISION) -> float:
    p, r, t = precision_recall_curve(y, s)
    ok = np.where(p[:-1] >= target)[0]
    return float(t[ok[0]]) if len(ok) else float(s.max())


def at_threshold(y, s, amount, th, days) -> Dict[str, float]:
    alert = s >= th
    tp = int((alert & (y == 1)).sum())
    fp = int((alert & (y == 0)).sum())
    fn = int((~alert & (y == 1)).sum())
    tn = int((~alert & (y == 0)).sum())
    fraud_amt = float((amount * y).sum())
    missed = float((amount * ((~alert) & (y == 1))).sum())
    return {
        "precision": tp / max(tp + fp, 1),
        "recall": tp / max(tp + fn, 1),
        "false_positive_rate": fp / max(fp + tn, 1),
        "alerts_per_day": (tp + fp) / max(days, 1e-9),
        "amount_recall": 1 - missed / max(fraud_amt, 1e-9),
        "cost_rupees": missed + REVIEW_COST * (tp + fp),
        "tp": tp, "fp": fp, "fn": fn,
    }


def evaluate_scores(name, y_val, s_val, a_val, y_te, s_te, a_te, days_te) -> Dict[str, float]:
    th_cost = cost_threshold(y_val, s_val, a_val)
    th_budget = budget_threshold(s_val)
    c = at_threshold(y_te, s_te, a_te, th_cost, days_te)
    b = at_threshold(y_te, s_te, a_te, th_budget, days_te)
    no_model_cost = float((a_te * y_te).sum())
    return {
        "model": name,
        "pr_auc": average_precision_score(y_te, s_te),
        "roc_auc": roc_auc_score(y_te, s_te),
        "budget_precision": b["precision"], "budget_recall": b["recall"],
        "budget_amount_recall": b["amount_recall"],
        "cost_precision": c["precision"], "cost_recall": c["recall"],
        "cost_fpr": c["false_positive_rate"], "cost_alerts_per_day": c["alerts_per_day"],
        "cost_amount_recall": c["amount_recall"],
        "cost_rupees": c["cost_rupees"], "saving_vs_no_model": no_model_cost - c["cost_rupees"],
        "threshold_cost": th_cost, "threshold_budget": th_budget,
    }


# ----------------------------------------------------------------------------
# Experiments
# ----------------------------------------------------------------------------
class Experiment:
    def __init__(self, regenerate: bool = False):
        self.df = load_data(regenerate)
        log(f"{len(self.df):,} transactions, fraud rate {self.df.is_fraud.mean():.2%}")
        t = time.time()
        self.X, self.meta = build_features(self.df)
        log(f"features computed in {time.time() - t:.1f}s ({(time.time() - t) / len(self.df) * 1e6:.0f} µs per payment)")
        self.m = split_masks(self.meta)
        self.y = self.df["is_fraud"].to_numpy().astype(int)
        self.amount = self.df["amount"].to_numpy().astype(float)
        self.ftype = self.df["fraud_type"].to_numpy()
        self.days_test = (self.meta["day"][self.m["test"]].max() - VAL_END)
        self.results: Dict[str, object] = {}
        self.scores: Dict[str, Dict[str, np.ndarray]] = {}

    # -- helpers -------------------------------------------------------------
    def part(self, name):
        mk = self.m[name]
        return self.X[mk], self.y[mk], self.amount[mk]

    def data_summary(self) -> dict:
        out = {}
        for name, mk in self.m.items():
            out[name] = {
                "rows": int(mk.sum()),
                "fraud_rows": int(self.y[mk].sum()),
                "fraud_rate": float(self.y[mk].mean()),
                "days": [float(self.meta["day"][mk].min()), float(self.meta["day"][mk].max())],
            }
        out["fraud_type_counts"] = self.df.loc[self.df.is_fraud == 1, "fraud_type"].value_counts().to_dict()
        out["total_rows"] = int(len(self.df))
        self.results["data"] = out
        return out

    # -- 1. comparison -------------------------------------------------------
    def compare(self) -> pd.DataFrame:
        Xtr, ytr, _ = self.part("train")
        Xva, yva, ava = self.part("val")
        Xte, yte, ate = self.part("test")
        rows, scores = [], {}

        def add(name, s_val, s_te):
            scores[name] = {"val": s_val, "test": s_te}
            rows.append(evaluate_scores(name, yva, s_val, ava, yte, s_te, ate, self.days_test))
            log(f"  {name:36s} PR-AUC {rows[-1]['pr_auc']:.3f}")

        add("1. Rules (hand-written)", rules_score(Xva), rules_score(Xte))
        self.if_tab = fit_if(Xtr, TABULAR)
        add("2a. Isolation Forest (no graph)", score_if(self.if_tab, Xva), score_if(self.if_tab, Xte))
        self.if_all = fit_if(Xtr, ALL)
        add("2b. Isolation Forest (+ graph)", score_if(self.if_all, Xva), score_if(self.if_all, Xte))
        self.rf_tab = fit_rf(Xtr, ytr, TABULAR)
        add("3a. Random Forest (no graph)", self.rf_tab.predict_proba(Xva[TABULAR])[:, 1],
            self.rf_tab.predict_proba(Xte[TABULAR])[:, 1])
        self.rf_all = fit_rf(Xtr, ytr, ALL)
        add("3b. Random Forest (+ graph)", self.rf_all.predict_proba(Xva[ALL])[:, 1],
            self.rf_all.predict_proba(Xte[ALL])[:, 1])
        Htr, Hva, Hte = with_if(Xtr, self.if_all), with_if(Xva, self.if_all), with_if(Xte, self.if_all)
        self.hybrid = fit_rf(Htr, ytr, HYBRID_COLS)
        add("4. Hybrid (RF + graph + IF score)", self.hybrid.predict_proba(Hva[HYBRID_COLS])[:, 1],
            self.hybrid.predict_proba(Hte[HYBRID_COLS])[:, 1])

        orig = self.original_model_scores()
        if orig is not None:
            add("0. Original model (Oct 2026, PaySim IF)", orig["val"], orig["test"])

        table = pd.DataFrame(rows).sort_values("model").reset_index(drop=True)
        self.scores["compare"] = scores
        self.results["comparison"] = table.to_dict(orient="records")
        return table

    def original_model_scores(self):
        """Score val/test with the ORIGINAL pickles + original 30-feature pipeline, if archived."""
        old = ROOT / "_archive" / "original_model"
        if not (old / "isolation_forest.pkl").exists():
            log("  (original model not found in _archive/original_model - skipped)")
            return None
        sys.path.insert(0, str(old))
        try:
            import importlib
            ofe = importlib.import_module("original_feature_engineering")
            load = lambda n: pickle.load(open(old / n, "rb"))  # noqa: E731
            fc, pc, sc, iso = load("feature_config.pkl"), load("preprocessing_config.pkl"), load("scaler.pkl"), load("isolation_forest.pkl")
            raw = self.df.copy()
            raw["transaction_type"] = raw["transaction_type"].astype(str)
            feats, _ = ofe.compute_30_features(raw[[c for c in raw.columns if c in ofe.REQUIRED_COLUMNS]], fc)
            for c in pc["log_features"]:
                feats[c] = np.log1p(feats[c].clip(lower=0))
            s = -iso.decision_function(sc.transform(feats[fc].values))
            return {"val": s[self.m["val"]], "test": s[self.m["test"]]}
        except Exception as e:  # pragma: no cover
            log(f"  original model failed: {e}")
            return None
        finally:
            sys.path.remove(str(old))

    # -- 2. ablation ---------------------------------------------------------
    def ablation(self) -> pd.DataFrame:
        Xtr, ytr, _ = self.part("train")
        Xva, yva, ava = self.part("val")
        Xte, yte, ate = self.part("test")
        groups = list(FEATURE_GROUPS)
        labels = {"amount_context": "Amount & context only", "behaviour_velocity": "+ behaviour & velocity",
                  "device": "+ device", "graph_flow": "+ graph money-flow"}
        rows = []
        for k in range(1, len(groups) + 1):
            cols = sum((FEATURE_GROUPS[g] for g in groups[:k]), [])
            ifm = fit_if(Xtr, cols)
            rf = fit_rf(Xtr, ytr, cols)
            for mname, sv, st in [
                ("Isolation Forest", score_if(ifm, Xva), score_if(ifm, Xte)),
                ("Random Forest", rf.predict_proba(Xva[cols])[:, 1], rf.predict_proba(Xte[cols])[:, 1]),
            ]:
                r = evaluate_scores(mname, yva, sv, ava, yte, st, ate, self.days_test)
                rows.append({"features": labels[groups[k - 1]], "n_features": len(cols), "model": mname,
                             "pr_auc": r["pr_auc"], "budget_recall": r["budget_recall"],
                             "cost_recall": r["cost_recall"], "cost_precision": r["cost_precision"]})
                # recall on mule_layering specifically, at the budget threshold
                mk = self.ftype[self.m["test"]] == "mule_layering"
                rows[-1]["mule_recall_budget"] = float((st[mk] >= r["threshold_budget"]).mean())
            log(f"  ablation {labels[groups[k-1]]:28s} RF PR-AUC {rows[-1]['pr_auc']:.3f}")
        table = pd.DataFrame(rows)
        self.results["ablation"] = table.to_dict(orient="records")
        return table

    # -- 3. per-type recall --------------------------------------------------
    def recall_by_type(self) -> pd.DataFrame:
        sc = self.scores["compare"]
        comp = {r["model"]: r for r in self.results["comparison"]}
        te_type = self.ftype[self.m["test"]]
        rows = []
        for model in ["1. Rules (hand-written)", "2b. Isolation Forest (+ graph)",
                      "3a. Random Forest (no graph)", "4. Hybrid (RF + graph + IF score)"]:
            th = comp[model]["threshold_budget"]
            s = sc[model]["test"]
            row = {"model": model}
            for ft in sim.FRAUD_TYPES:
                mk = te_type == ft
                row[ft] = float((s[mk] >= th).mean()) if mk.any() else np.nan
            rows.append(row)
        table = pd.DataFrame(rows)
        self.results["recall_by_type"] = table.to_dict(orient="records")
        return table

    # -- 4. unseen scam types ------------------------------------------------
    def unseen_scams(self) -> pd.DataFrame:
        rows = []
        for held in sim.SCAM_TYPES:
            keep_tr = self.m["train"] & (self.ftype != held)
            keep_va = self.m["val"] & (self.ftype != held)
            Xtr, ytr = self.X[keep_tr], self.y[keep_tr]
            Xva, yva, ava = self.X[keep_va], self.y[keep_va], self.amount[keep_va]
            te_mk = self.m["test"] & (self.ftype == held)
            Xh = self.X[te_mk]
            ifm = fit_if(Xtr, ALL)
            rf = fit_rf(Xtr, ytr, ALL)
            hyb = fit_rf(with_if(Xtr, ifm), ytr, HYBRID_COLS)
            res = {"held_out_scam": held, "test_rows": int(te_mk.sum())}
            for name, sv, sh in [
                ("Rules", rules_score(Xva), rules_score(Xh)),
                ("Isolation Forest", score_if(ifm, Xva), score_if(ifm, Xh)),
                ("Random Forest", rf.predict_proba(Xva[ALL])[:, 1], rf.predict_proba(Xh[ALL])[:, 1]),
                ("Hybrid", hyb.predict_proba(with_if(Xva, ifm)[HYBRID_COLS])[:, 1],
                 hyb.predict_proba(with_if(Xh, ifm)[HYBRID_COLS])[:, 1]),
            ]:
                th = budget_threshold(sv)          # same alert volume for every model
                res[name] = float((sh >= th).mean())
            # same type, but seen in training (from the full hybrid)
            comp = {r["model"]: r for r in self.results["comparison"]}
            th_full = comp["4. Hybrid (RF + graph + IF score)"]["threshold_budget"]
            s_full = self.hybrid.predict_proba(with_if(Xh, self.if_all)[HYBRID_COLS])[:, 1]
            res["Hybrid (type seen in training)"] = float((s_full >= th_full).mean())
            rows.append(res)
            log(f"  unseen {held:22s} RF {res['Random Forest']:.2f}  Hybrid {res['Hybrid']:.2f}  IF {res['Isolation Forest']:.2f}")
        table = pd.DataFrame(rows)
        self.results["unseen_scams"] = table.to_dict(orient="records")
        return table

    # -- 5. graph ring escalation -------------------------------------------
    def ring_escalation(self) -> pd.DataFrame:
        from mule_rings import escalate
        comp = {r["model"]: r for r in self.results["comparison"]}
        name = "4. Hybrid (RF + graph + IF score)"
        th = comp[name]["threshold_cost"]
        # choose the escalation cut-off on the VALIDATION week (by total cost)
        va = self.df[self.m["val"]].copy()
        va["fraud_score"] = self.scores["compare"][name]["val"]
        va["alert"] = va["fraud_score"] >= th
        _, ring_va, _, pt_va = detect_rings(va, "alert")
        yv, av = va["is_fraud"].to_numpy(), va["amount"].to_numpy()
        best, best_cost = None, np.inf
        for ms in [0.01, 0.02, 0.05, 0.1, 0.15]:
            a = (va["alert"] | escalate(va, ring_va, pt_va, min_score=ms)).to_numpy()
            cost = float(av[(~a) & (yv == 1)].sum()) + REVIEW_COST * a.sum()
            if cost < best_cost:
                best, best_cost = ms, cost
        self.escalation_min_score = best

        te = self.df[self.m["test"]].copy()
        te["fraud_score"] = self.scores["compare"][name]["test"]
        te["alert"] = te["fraud_score"] >= th
        rings, ring_of, _, pt = detect_rings(te, "alert")
        te["in_ring"] = ring_of >= 0
        te["naive"] = te["alert"] | te["in_ring"]
        te["refined"] = te["alert"] | escalate(te, ring_of, pt, min_score=best)
        y = te["is_fraud"].to_numpy()
        amt = te["amount"].to_numpy()
        mule = te["fraud_type"].to_numpy() == "mule_layering"
        rows = []
        for col, label in [("alert", "Model alerts only"),
                           ("naive", "+ every payment inside a detected ring"),
                           ("refined", f"+ ring payments that are fast pass-throughs (score ≥ {best})")]:
            a = te[col].to_numpy()
            tp, fp = int((a & (y == 1)).sum()), int((a & (y == 0)).sum())
            missed = float(amt[(~a) & (y == 1)].sum())
            rows.append({"setting": label, "alerts": tp + fp, "true_frauds": tp, "false_alerts": fp,
                         "precision": tp / max(tp + fp, 1), "recall": tp / max(int(y.sum()), 1),
                         "mule_layering_recall": float(a[mule].mean()),
                         "cost_rupees": missed + REVIEW_COST * (tp + fp)})
        ring_rows = te[te["in_ring"]]
        per_ring = ring_rows.groupby(ring_of[te["in_ring"]])["is_fraud"].mean()
        summary = {
            "rings_found": len(rings),
            "rings_majority_fraud": int((per_ring >= 0.5).sum()),
            "ring_payment_purity": float(ring_rows["is_fraud"].mean()) if len(ring_rows) else float("nan"),
            "true_rings_active_in_test": int(te.loc[te.is_fraud == 1, "fraud_ring"].nunique()),
            "escalation_min_score": best,
        }
        self.results["graph_rings"] = {"table": rows, **summary}
        log(f"  rings found {len(rings)} ({summary['rings_majority_fraud']} mostly fraud), purity {summary['ring_payment_purity']:.2f}")
        return pd.DataFrame(rows)

    # -- 6. cost sensitivity -------------------------------------------------
    def cost_sensitivity(self) -> pd.DataFrame:
        name = "4. Hybrid (RF + graph + IF score)"
        sv, st = self.scores["compare"][name]["val"], self.scores["compare"][name]["test"]
        _, yva, ava = self.part("val")
        _, yte, ate = self.part("test")
        rows = []
        for rc in [50, 200, 1000, 5000]:
            th = cost_threshold(yva, sv, ava, rc)
            r = at_threshold(yte, st, ate, th, self.days_test)
            rows.append({"review_cost_rupees": rc, "threshold": th, "alerts_per_day": r["alerts_per_day"],
                         "precision": r["precision"], "recall": r["recall"], "amount_recall": r["amount_recall"]})
        table = pd.DataFrame(rows)
        self.results["cost_sensitivity"] = table.to_dict(orient="records")
        return table

    # -- 7. final bundle -----------------------------------------------------
    def save_bundle(self) -> dict:
        comp = {r["model"]: r for r in self.results["comparison"]}
        name = "4. Hybrid (RF + graph + IF score)"
        sv = self.scores["compare"][name]["val"]
        _, yva, _ = self.part("val")
        th_alert = comp[name]["threshold_cost"]
        th_high = max(precision_threshold(yva, sv), th_alert)
        model = self.hybrid
        model.set_params(n_jobs=1)   # single-payment scoring is faster without process pools
        scaler, iso, if_cols = self.if_all
        iso.set_params(n_jobs=1)
        bundle = {
            "version": "2.0",
            "created": time.strftime("%Y-%m-%d %H:%M"),
            "sklearn_version": sklearn.__version__,
            "python_version": platform.python_version(),
            "features": ALL,
            "feature_groups": FEATURE_GROUPS,
            "if_scaler": scaler, "if_model": iso, "if_features": if_cols,
            "model": model, "model_features": HYBRID_COLS,
            "thresholds": {"alert": th_alert, "high": th_high},
            "review_cost": REVIEW_COST,
            "escalation_min_score": getattr(self, "escalation_min_score", 0.05),
            "alert_budget_share": ALERT_BUDGET_SHARE,
            "threshold_options": [{"review_cost_rupees": r["review_cost_rupees"], "threshold": r["threshold"]}
                                  for r in self.results.get("cost_sensitivity", [])],
            "training_data": {"settings": SIM_SETTINGS, "train_days": [WARMUP_DAYS, TRAIN_END],
                              "validation_days": [TRAIN_END, VAL_END], "test_days": [VAL_END, SIM_SETTINGS["days"]]},
            "test_metrics": comp[name],
        }
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_DIR / "model_bundle.pkl", "wb") as f:
            pickle.dump(bundle, f)
        self.bundle = bundle
        self.results["thresholds"] = {"alert": th_alert, "high": th_high}
        log(f"  saved model bundle (alert ≥ {th_alert:.3f}, high ≥ {th_high:.3f})")
        return bundle

    # -- 8. explanations: own method vs SHAP --------------------------------
    def explanation_check(self, n: int = 150) -> dict:
        name = "4. Hybrid (RF + graph + IF score)"
        Xte = with_if(self.X[self.m["test"]], self.if_all)[HYBRID_COLS]
        s = self.scores["compare"][name]["test"]
        top = np.argsort(-s)[:n]
        Xa = Xte.iloc[top]
        expl = ForestExplainer(self.hybrid, HYBRID_COLS)
        Cown = expl.contributions(Xa.values)
        out = {"n_alerts_checked": n,
               "additivity_max_error": float(np.abs(expl.bias + Cown.sum(1) - self.hybrid.predict_proba(Xa)[:, 1]).max())}
        try:
            import shap
            sv = shap.TreeExplainer(self.hybrid).shap_values(Xa.values, check_additivity=False)
            sv = sv[1] if isinstance(sv, list) else (sv[..., 1] if sv.ndim == 3 else sv)
            agree_top1 = np.mean([np.argmax(Cown[i]) == np.argmax(sv[i]) for i in range(len(Xa))])
            overlap3 = np.mean([len(set(np.argsort(-Cown[i])[:3]) & set(np.argsort(-sv[i])[:3])) / 3 for i in range(len(Xa))])
            out.update({"shap_available": True, "top1_agreement": float(agree_top1), "top3_overlap": float(overlap3)})
        except Exception as e:  # shap is optional
            out.update({"shap_available": False, "note": str(e)[:200]})
        # global importance = mean |contribution| over alerts
        imp = pd.Series(np.abs(Cown).mean(0), index=HYBRID_COLS).sort_values(ascending=False)
        out["global_importance_top10"] = imp.head(10).round(4).to_dict()
        self.results["explanations"] = out
        log(f"  explanations: {out.get('top1_agreement', 'n/a')} top-1 agreement with SHAP")
        return out

    # -- 9. demo datasets ----------------------------------------------------
    def make_demo_datasets(self) -> Dict[str, Path]:
        specs = {
            "dataset_1_normal_baseline.csv": dict(n_customers=2000, n_merchants=150, n_high_value_merchants=6,
                                                  days=7, seed=101, fraud_enabled=False),
            "dataset_2_scam_attacks.csv": dict(n_customers=2000, n_merchants=150, n_high_value_merchants=6,
                                               days=7, seed=202, scam_events_per_day=8.0, n_rings=3),
            "dataset_3_mule_rings.csv": dict(n_customers=2000, n_merchants=150, n_high_value_merchants=6,
                                             days=7, seed=303, scam_events_per_day=8.0, n_rings=2,
                                             min_layers=2, max_layers=3, late_ring_share=0.0,
                                             scam_mix={"qr_scam": 0.3, "fake_merchant_collect": 0.4,
                                                       "fake_refund_call": 0.3}),
        }
        paths = {}
        cols = sim.REQUIRED_OUT + ["is_fraud", "fraud_type"]
        for fname, kw in specs.items():
            d = sim.simulate(**kw)[cols]
            p = APP_DIR / fname
            d.to_csv(p, index=False)
            paths[fname] = p
            log(f"  {fname}: {len(d):,} rows, {int(d.is_fraud.sum())} fraud")
        return paths

    def evaluate_demo(self, paths: Dict[str, Path]) -> pd.DataFrame:
        from scoring import score_batch  # dashboard scoring function
        rows = []
        for fname, p in paths.items():
            d = pd.read_csv(p)
            scored, _ = score_batch(d, self.bundle)
            live = ~scored["warmup"]
            y = d["is_fraud"].to_numpy()[live]
            a = scored["alert"].to_numpy()[live]
            tp, fp = int((a & (y == 1)).sum()), int((a & (y == 0)).sum())
            rows.append({"dataset": fname, "rows_scored": int(live.sum()), "warmup_rows": int((~live).sum()),
                         "fraud_rows": int(y.sum()), "alerts": tp + fp,
                         "false_alert_rate": fp / max(int((y == 0).sum()), 1),
                         "precision": tp / max(tp + fp, 1) if (tp + fp) else float("nan"),
                         "recall": tp / max(int(y.sum()), 1) if y.sum() else float("nan")})
        table = pd.DataFrame(rows)
        self.results["demo_datasets"] = table.to_dict(orient="records")
        return table


# ----------------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------------
def _style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, fontsize=12, loc="left", pad=10)
    ax.set_xlabel(xlabel, color=INK2)
    ax.set_ylabel(ylabel, color=INK2)
    ax.tick_params(colors=INK2)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]:
        ax.spines[sp].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def make_charts(exp: Experiment) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    RESULTS_DIR.mkdir(exist_ok=True)
    yte = exp.y[exp.m["test"]]

    # PR curves
    fig, ax = plt.subplots(figsize=(7.5, 5))
    order = ["1. Rules (hand-written)", "2b. Isolation Forest (+ graph)", "3a. Random Forest (no graph)",
             "3b. Random Forest (+ graph)", "4. Hybrid (RF + graph + IF score)", "0. Original model (Oct 2026, PaySim IF)"]
    for i, name in enumerate([n for n in order if n in exp.scores["compare"]]):
        p, r, _ = precision_recall_curve(yte, exp.scores["compare"][name]["test"])
        ax.plot(r, p, color=C[i], lw=2, label=name)
    _style(ax, "Precision vs recall on the unseen test week", "Recall (share of fraud caught)", "Precision (share of alerts that are fraud)")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    fig.tight_layout(); fig.savefig(RESULTS_DIR / "pr_curves.png", dpi=150); plt.close(fig)

    # Ablation
    ab = pd.DataFrame(exp.results["ablation"])
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    labels = ab["features"].unique()
    x = np.arange(len(labels))
    for i, m in enumerate(["Isolation Forest", "Random Forest"]):
        v = ab[ab.model == m].set_index("features").loc[labels, "pr_auc"].to_numpy()
        bars = ax.bar(x + (i - 0.5) * 0.36, v, width=0.34, color=C[i], label=m, edgecolor=SURFACE, linewidth=2)
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.015, f"{val:.2f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(x, labels, fontsize=9)
    _style(ax, "Ablation: PR-AUC as feature groups are added", "", "PR-AUC (test)")
    ax.set_ylim(0, 1.08); ax.legend(frameon=False, labelcolor=INK)
    fig.tight_layout(); fig.savefig(RESULTS_DIR / "ablation.png", dpi=150); plt.close(fig)

    # Unseen scams
    un = pd.DataFrame(exp.results["unseen_scams"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    models = ["Rules", "Isolation Forest", "Random Forest", "Hybrid", "Hybrid (type seen in training)"]
    x = np.arange(len(un))
    w = 0.16
    for i, m in enumerate(models):
        ax.bar(x + (i - 2) * w, un[m], width=w - 0.02, color=C[i], label=m, edgecolor=SURFACE, linewidth=1)
    ax.set_xticks(x, [s.replace("_", " ") for s in un["held_out_scam"]], fontsize=9)
    _style(ax, "Recall on a scam type the model never saw in training", "", "Recall (test)")
    ax.set_ylim(0, 1.05); ax.legend(frameon=False, fontsize=8, labelcolor=INK, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout(); fig.savefig(RESULTS_DIR / "unseen_scams.png", dpi=150); plt.close(fig)

    # Cost curve for the hybrid
    name = "4. Hybrid (RF + graph + IF score)"
    s, a = exp.scores["compare"][name]["test"], exp.amount[exp.m["test"]]
    ths = np.unique(np.quantile(s, np.linspace(0.5, 0.9995, 300)))
    costs = [at_threshold(yte, s, a, t, exp.days_test)["cost_rupees"] / 1e5 for t in ths]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(ths, costs, color=C[0], lw=2)
    th = exp.results["thresholds"]["alert"]
    ax.axvline(th, color=INK2, lw=1, ls="--")
    ax.text(th, max(costs) * 0.95, f"  chosen on validation: {th:.2f}", color=INK2, fontsize=9)
    _style(ax, f"Total cost on the test week (missed fraud ₹ + ₹{REVIEW_COST} per alert)", "Alert threshold (fraud score)", "Cost (₹ lakh)")
    fig.tight_layout(); fig.savefig(RESULTS_DIR / "cost_curve.png", dpi=150); plt.close(fig)

    # Importance
    imp = pd.Series(exp.results["explanations"]["global_importance_top10"]).sort_values()
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.barh(imp.index, imp.values, color=C[0], edgecolor=SURFACE, linewidth=2)
    _style(ax, "What drives alerts (mean contribution, top alerts)", "Mean |contribution| to fraud probability", "")
    fig.tight_layout(); fig.savefig(RESULTS_DIR / "feature_importance.png", dpi=150); plt.close(fig)


# ----------------------------------------------------------------------------
# RESULTS.md
# ----------------------------------------------------------------------------
def _pct(x):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.1f}%"


def write_results_md(exp: Experiment) -> None:
    R = exp.results
    d = R["data"]
    comp = pd.DataFrame(R["comparison"])
    lines = []
    A = lines.append
    A("# Results: UPI scam & mule detection\n")
    A(f"_Generated automatically by `train_and_evaluate.py` on {time.strftime('%Y-%m-%d %H:%M')}. "
      "Every number below comes from the code in this repository; re-running the script reproduces it._\n")
    A("## 1. Data\n")
    A(f"- Simulated UPI payments: **{d['total_rows']:,}** over {SIM_SETTINGS['days']} days, "
      f"{SIM_SETTINGS['n_customers']:,} customers, {SIM_SETTINGS['n_merchants']} merchants (`upi_simulator.py`, seed {SIM_SETTINGS['seed']}).")
    A("- Time-based split (no shuffling, so the model is always tested on the future):")
    A("\n| Part | Days | Payments | Fraud payments | Fraud rate |\n|---|---|---|---|---|")
    A(f"| Warm-up (history only, not scored) | 0–{WARMUP_DAYS} | – | – | – |")
    for k, lab in [("train", "Train"), ("val", "Validation (thresholds chosen here)"), ("test", "Test (reported below)")]:
        v = d[k]
        A(f"| {lab} | {v['days'][0]:.0f}–{v['days'][1]:.0f} | {v['rows']:,} | {v['fraud_rows']:,} | {_pct(v['fraud_rate'])} |")
    A("\nFraud payments by type (whole dataset): " + ", ".join(f"{k} {v}" for k, v in d["fraud_type_counts"].items()) + ".")
    A("\n> Fraud is over-represented on purpose (about 1–2% of payments) so models see enough examples. "
      "Real UPI fraud rates are far lower, so real-world precision would be lower than shown here. "
      "All results are on simulated data; they show the method works and how the parts compare, not how it would perform at a real bank.\n")

    A("## 2. Model comparison (test week)\n")
    A(f"Thresholds are chosen on the validation days only. **Cost threshold** minimises missed fraud ₹ + ₹{REVIEW_COST} per alert. "
      f"**Budget** = analysts review the top {ALERT_BUDGET_SHARE:.0%} of payments.\n")
    A("| Model | PR-AUC | Precision @budget | Recall @budget | Precision @cost | Recall @cost | ₹ recall @cost | Alerts/day @cost | Saving vs no model |")
    A("|---|---|---|---|---|---|---|---|---|")
    for _, r in comp.iterrows():
        A(f"| {r['model']} | {r['pr_auc']:.3f} | {_pct(r['budget_precision'])} | {_pct(r['budget_recall'])} | "
          f"{_pct(r['cost_precision'])} | {_pct(r['cost_recall'])} | {_pct(r['cost_amount_recall'])} | "
          f"{r['cost_alerts_per_day']:.0f} | ₹{r['saving_vs_no_model']/1e5:.1f} lakh |")
    A("\n**How to read this:** PR-AUC and the *@budget* columns compare models fairly (same number of alerts). "
      "The *@cost* columns show each model at its own cost-optimal threshold; for weak models that threshold "
      "means alerting on hundreds or thousands of payments a day, which no fraud team could review.\n")
    A("\n![PR curves](results/pr_curves.png)\n")

    A("## 3. Ablation: what each feature group adds\n")
    ab = pd.DataFrame(R["ablation"])
    A("| Features | # | IF PR-AUC | RF PR-AUC | RF recall @budget | RF mule-layering recall @budget |\n|---|---|---|---|---|---|")
    for f in ab["features"].unique():
        a_if = ab[(ab.features == f) & (ab.model == "Isolation Forest")].iloc[0]
        a_rf = ab[(ab.features == f) & (ab.model == "Random Forest")].iloc[0]
        A(f"| {f} | {a_rf['n_features']} | {a_if['pr_auc']:.3f} | {a_rf['pr_auc']:.3f} | {_pct(a_rf['budget_recall'])} | {_pct(a_rf['mule_recall_budget'])} |")
    A("\n![Ablation](results/ablation.png)\n")

    A(f"## 4. Recall by fraud type (same alert budget for every model: top {ALERT_BUDGET_SHARE:.0%}, test week)\n")
    rt = pd.DataFrame(R["recall_by_type"])
    A("| Model | " + " | ".join(sim.FRAUD_TYPES) + " |\n|---|" + "---|" * len(sim.FRAUD_TYPES))
    for _, r in rt.iterrows():
        A(f"| {r['model']} | " + " | ".join(_pct(r[t]) for t in sim.FRAUD_TYPES) + " |")

    A("\n## 5. Unseen scam types (zero-day test)\n")
    A("Each scam type is removed from training **and** validation, then the models are tested on that type only. "
      "This is the situation the unsupervised part is meant for. "
      f"All models get the same alert budget (top {ALERT_BUDGET_SHARE:.0%} of payments), so recall is compared fairly.\n")
    un = pd.DataFrame(R["unseen_scams"])
    A("| Held-out scam | Test payments | Rules | Isolation Forest | Random Forest | Hybrid | Hybrid (seen in training) |\n|---|---|---|---|---|---|---|")
    for _, r in un.iterrows():
        A(f"| {r['held_out_scam']} | {r['test_rows']} | {_pct(r['Rules'])} | {_pct(r['Isolation Forest'])} | "
          f"{_pct(r['Random Forest'])} | {_pct(r['Hybrid'])} | {_pct(r['Hybrid (type seen in training)'])} |")
    A("\n![Unseen scams](results/unseen_scams.png)\n")

    A("## 6. Graph layer: NetworkX ring escalation\n")
    g = R["graph_rings"]
    A(f"Candidate rings found in the test week: **{g['rings_found']}**, of which **{g['rings_majority_fraud']}** are mostly fraud "
      f"(true rings active in the test week: {g['true_rings_active_in_test']}). "
      f"Share of payments inside detected rings that are truly fraud: **{_pct(g['ring_payment_purity'])}**.\n")
    A(f"| Setting | Alerts | True frauds | False alerts | Precision | Recall | Mule-layering recall | Total cost (₹ lakh) |\n|---|---|---|---|---|---|---|---|")
    for r in g["table"]:
        A(f"| {r['setting']} | {r['alerts']:,} | {r['true_frauds']} | {r['false_alerts']} | {_pct(r['precision'])} | "
          f"{_pct(r['recall'])} | {_pct(r['mule_layering_recall'])} | {r['cost_rupees']/1e5:.2f} |")
    t0, t2 = g["table"][0], g["table"][2]
    A(f"\nThe escalation cut-off was chosen on the validation week. On the test week it catches "
      f"**{t2['true_frauds'] - t0['true_frauds']} more frauds** for **{t2['false_alerts'] - t0['false_alerts']} more false alerts**, "
      f"and lowers total cost from ₹{t0['cost_rupees']/1e5:.2f} lakh to ₹{t2['cost_rupees']/1e5:.2f} lakh, because a missed scam "
      f"costs far more than a ₹{REVIEW_COST} review. Most of the graph's value is already inside the model through the graph "
      "money-flow features (section 3); ring detection adds the rest and gives investigators the whole ring to act on.")

    A("\n## 7. Choosing the threshold like a bank\n")
    A(f"Chosen operating point (validation): alert if fraud score ≥ **{R['thresholds']['alert']:.3f}**; "
      f"'High risk' if ≥ **{R['thresholds']['high']:.3f}** (≥ {HIGH_RISK_PRECISION:.0%} precision on validation).\n")
    A("Sensitivity to the assumed review cost (hybrid model, test week):\n")
    A("| Review cost per alert | Threshold | Alerts/day | Precision | Recall | ₹ recall |\n|---|---|---|---|---|---|")
    for r in R["cost_sensitivity"]:
        A(f"| ₹{r['review_cost_rupees']:,} | {r['threshold']:.3f} | {r['alerts_per_day']:.0f} | {_pct(r['precision'])} | {_pct(r['recall'])} | {_pct(r['amount_recall'])} |")
    A("\n![Cost curve](results/cost_curve.png)\n")

    A("## 8. Explanations\n")
    e = R["explanations"]
    A(f"- Reason codes use exact tree-path contributions (max additivity error {e['additivity_max_error']:.1e}).")
    if e.get("shap_available"):
        A(f"- Checked against SHAP TreeExplainer on the top {e['n_alerts_checked']} test alerts: "
          f"top reason identical in **{_pct(e['top1_agreement'])}**, top-3 overlap **{_pct(e['top3_overlap'])}**.")
    A("\n![Feature importance](results/feature_importance.png)\n")

    if "demo_datasets" in R:
        A("## 9. Demo datasets (new simulations, different seeds, smaller bank)\n")
        A("| Dataset | Payments scored | Warm-up rows | Fraud | Alerts | False-alert rate | Precision | Recall |\n|---|---|---|---|---|---|---|---|")
        for r in R["demo_datasets"]:
            A(f"| {r['dataset']} | {r['rows_scored']:,} | {r['warmup_rows']:,} | {r['fraud_rows']} | {r['alerts']} | "
              f"{_pct(r['false_alert_rate'])} | {_pct(r['precision'])} | {_pct(r['recall'])} |")
    if "latency" in R:
        L = R["latency"]
        A("\n## 10. Real-time scoring\n")
        A(f"`realtime_demo.py` replays payments one at a time through the same feature engine and model. "
          f"Per-payment latency (features + model, single CPU core): median **{L['p50_ms']:.1f} ms**, "
          f"95th percentile **{L['p95_ms']:.1f} ms**, 99th **{L['p99_ms']:.1f} ms** over {L['n']:,} payments.")

    A("\n## 11. Limitations (state these in the report and viva)\n")
    A("- Data is simulated. The scam patterns follow public descriptions of UPI fraud, but the exact numbers depend on simulator assumptions.")
    A("- Fraud is over-represented; precision at a real bank's base rate would be lower.")
    A("- The first 48 hours of any uploaded file lack history; those rows are shown as 'warm-up' and not scored for metrics. A real deployment would keep history in a feature store.")
    A("- The supervised model only learns scams it has seen; section 5 shows how much it drops on a new scam type.")
    A("- Ring detection looks at the whole batch (including later payments), so it is an investigation tool, not a real-time decision.")
    (ROOT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def save_results(exp: Experiment) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, np.integer):
            return int(o)
        return o
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(clean(exp.results), indent=2), encoding="utf-8")
    for key in ["comparison", "ablation", "recall_by_type", "unseen_scams", "cost_sensitivity", "demo_datasets"]:
        if key in exp.results:
            pd.DataFrame(exp.results[key]).to_csv(RESULTS_DIR / f"{key}.csv", index=False)


def main(regenerate: bool = False) -> Experiment:
    exp = Experiment(regenerate)
    exp.data_summary()
    log("1/8 model comparison"); exp.compare()
    log("2/8 ablation"); exp.ablation()
    log("3/8 recall by fraud type"); exp.recall_by_type()
    log("4/8 unseen scam types"); exp.unseen_scams()
    log("5/8 graph ring escalation"); exp.ring_escalation()
    log("6/8 cost sensitivity"); exp.cost_sensitivity()
    log("7/8 save model + explanations"); exp.save_bundle(); exp.explanation_check()
    log("8/8 demo datasets"); exp.evaluate_demo(exp.make_demo_datasets())
    try:
        import realtime_demo
        exp.results["latency"] = realtime_demo.benchmark(n=2000, quiet=True)
    except Exception as e:  # pragma: no cover
        log(f"latency benchmark skipped: {e}")
    make_charts(exp)
    save_results(exp)
    write_results_md(exp)
    log("done -> RESULTS.md, results/, fraud_detection_app/models/model_bundle.pkl")
    return exp


if __name__ == "__main__":
    main(regenerate="--regenerate" in sys.argv)
