"""
Fast single-payment scoring.

scikit-learn is built for scoring many rows at once; for ONE row its per-tree
overhead dominates (~30 ms for a 200-tree forest + 200-tree Isolation Forest).
Here all trees are stacked into 2-D arrays and walked level by level with
NumPy, so one payment is scored in about a millisecond.

The results are identical to scikit-learn's (checked in tests/test_pipeline.py).
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble._iforest import _average_path_length


class _StackedTrees:
    def __init__(self, trees):
        n = len(trees)
        m = max(t.tree_.node_count for t in trees)
        self.left = np.full((n, m), -1, dtype=np.int64)
        self.right = np.full((n, m), -1, dtype=np.int64)
        self.feature = np.zeros((n, m), dtype=np.int64)
        self.threshold = np.zeros((n, m), dtype=np.float64)
        for i, t in enumerate(trees):
            tr = t.tree_
            k = tr.node_count
            self.left[i, :k] = tr.children_left
            self.right[i, :k] = tr.children_right
            self.feature[i, :k] = np.maximum(tr.feature, 0)
            self.threshold[i, :k] = tr.threshold
        self.rows = np.arange(n)
        self.max_depth = max(t.tree_.max_depth for t in trees)

    def leaves(self, x32: np.ndarray) -> np.ndarray:
        """Leaf index reached in every tree for one sample (float32 like sklearn)."""
        nodes = np.zeros(len(self.rows), dtype=np.int64)
        for _ in range(self.max_depth):
            l = self.left[self.rows, nodes]
            internal = l != -1
            if not internal.any():
                break
            go_left = x32[self.feature[self.rows, nodes]] <= self.threshold[self.rows, nodes]
            nxt = np.where(go_left, l, self.right[self.rows, nodes])
            nodes = np.where(internal, nxt, nodes)
        return nodes


class FastForest:
    """P(fraud) of a fitted RandomForestClassifier for a single sample."""

    def __init__(self, forest, positive_class: int = 1):
        trees = forest.estimators_
        self.stack = _StackedTrees(trees)
        m = self.stack.left.shape[1]
        self.prob = np.zeros((len(trees), m))
        for i, t in enumerate(trees):
            v = t.tree_.value[:, 0, :]
            self.prob[i, : t.tree_.node_count] = v[:, positive_class] / np.maximum(v.sum(axis=1), 1e-300)

    def predict_one(self, x: np.ndarray) -> float:
        leaves = self.stack.leaves(np.asarray(x, dtype=np.float32))
        return float(self.prob[self.stack.rows, leaves].mean())


class FastIsolationForest:
    """decision_function of a fitted IsolationForest for a single sample."""

    def __init__(self, iso, n_features: int):
        if getattr(iso, "_max_features", n_features) != n_features:
            raise ValueError("feature sub-sampling not supported by the fast path")
        trees = iso.estimators_
        self.stack = _StackedTrees(trees)
        m = self.stack.left.shape[1]
        self.path = np.zeros((len(trees), m))
        for i, t in enumerate(trees):
            tr = t.tree_
            depth = np.zeros(tr.node_count)
            for node in range(tr.node_count):          # parents always have smaller ids
                for c in (tr.children_left[node], tr.children_right[node]):
                    if c != -1:
                        depth[c] = depth[node] + 1
            # same quantity sklearn uses: depth (= nodes on path - 1) + c(n_samples in leaf)
            self.path[i, : tr.node_count] = depth + _average_path_length(tr.n_node_samples)
        self.denominator = len(trees) * _average_path_length([iso._max_samples])[0]
        self.offset = iso.offset_

    def decision_one(self, x: np.ndarray) -> float:
        leaves = self.stack.leaves(np.asarray(x, dtype=np.float32))
        depths = self.path[self.stack.rows, leaves].sum()
        score_samples = -(2.0 ** (-depths / self.denominator))
        return float(score_samples - self.offset)


class FastScorer:
    """Scaler + Isolation Forest + hybrid forest, for one feature vector."""

    def __init__(self, bundle: dict):
        feats = bundle["features"]
        self.if_idx = np.array([feats.index(c) for c in bundle["if_features"]])
        sc = bundle["if_scaler"]
        self.mean = sc.mean_
        self.scale = sc.scale_
        self.iso = FastIsolationForest(bundle["if_model"], len(self.if_idx))
        self.forest = FastForest(bundle["model"])

    def score(self, x: np.ndarray):
        z = (x[self.if_idx] - self.mean) / self.scale
        anomaly = -self.iso.decision_one(z)
        row = np.append(x, anomaly)
        return self.forest.predict_one(row), row
