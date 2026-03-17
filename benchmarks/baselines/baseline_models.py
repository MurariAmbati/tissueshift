"""Baseline models for all six benchmark tracks.

These serve as reference implementations and minimum benchmarks.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVR


class MeanPoolLinear:
    """Baseline: Mean-pool patch features + logistic regression.

    Track: SubtypeCall
    Expected Macro-F1: ~0.75-0.80
    """

    def __init__(self):
        self.model = LogisticRegression(
            max_iter=1000, multi_class="multinomial", C=1.0
        )

    def fit(self, features_list: list[np.ndarray], labels: np.ndarray):
        """Train on mean-pooled slide features.

        Args:
            features_list: List of (N_i, D) arrays per slide
            labels: (n_slides,) subtype labels
        """
        X = np.array([f.mean(axis=0) for f in features_list])
        self.model.fit(X, labels)

    def predict(self, features_list: list[np.ndarray]) -> np.ndarray:
        X = np.array([f.mean(axis=0) for f in features_list])
        return self.model.predict(X)

    def predict_proba(self, features_list: list[np.ndarray]) -> np.ndarray:
        X = np.array([f.mean(axis=0) for f in features_list])
        return self.model.predict_proba(X)


class RandomForestBaseline:
    """Baseline: Mean-pool + Random Forest.

    Track: SubtypeCall, ProgressionStage
    """

    def __init__(self, n_estimators: int = 200):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators, n_jobs=-1, random_state=42
        )

    def fit(self, features_list: list[np.ndarray], labels: np.ndarray):
        X = np.array([f.mean(axis=0) for f in features_list])
        self.model.fit(X, labels)

    def predict(self, features_list: list[np.ndarray]) -> np.ndarray:
        X = np.array([f.mean(axis=0) for f in features_list])
        return self.model.predict(X)


class ClinicalCoxBaseline:
    """Baseline: Clinical features only (Cox proportional hazards).

    Track: Survival
    Expected C-index: ~0.62-0.67
    """

    def __init__(self):
        self.model = None

    def fit(
        self,
        clinical_features: np.ndarray,
        event_times: np.ndarray,
        event_indicators: np.ndarray,
    ):
        """Fit Cox PH model on clinical features."""
        try:
            from sksurv.linear_model import CoxPHSurvivalAnalysis

            y = np.array(
                [(bool(e), t) for e, t in zip(event_indicators, event_times)],
                dtype=[("event", bool), ("time", float)],
            )
            self.model = CoxPHSurvivalAnalysis(alpha=0.1)
            self.model.fit(clinical_features, y)
        except ImportError:
            # Fallback: use risk = negative mean of features
            self.feature_weights = np.ones(clinical_features.shape[1])

    def predict_risk(self, clinical_features: np.ndarray) -> np.ndarray:
        if self.model is not None:
            return self.model.predict(clinical_features)
        return clinical_features @ self.feature_weights


class Morph2MolRegression:
    """Baseline: Mean-pool SVR for gene expression prediction.

    Track: Morph2Mol
    Expected mean R²: ~0.10-0.20
    """

    def __init__(self):
        self.models: list = []

    def fit(self, features_list: list[np.ndarray], expression: np.ndarray):
        """Fit per-gene SVR.

        Args:
            features_list: List of (N_i, D) arrays per slide
            expression: (n_slides, n_genes) expression matrix
        """
        X = np.array([f.mean(axis=0) for f in features_list])
        n_genes = expression.shape[1]

        self.models = []
        for g in range(n_genes):
            svr = SVR(kernel="rbf", C=1.0)
            svr.fit(X, expression[:, g])
            self.models.append(svr)

    def predict(self, features_list: list[np.ndarray]) -> np.ndarray:
        X = np.array([f.mean(axis=0) for f in features_list])
        preds = np.column_stack([m.predict(X) for m in self.models])
        return preds


# Registry of baselines per track
BASELINES = {
    "SubtypeCall": {
        "MeanPool+LR": MeanPoolLinear,
        "MeanPool+RF": RandomForestBaseline,
    },
    "ProgressionStage": {
        "MeanPool+RF": RandomForestBaseline,
    },
    "Survival": {
        "Clinical+Cox": ClinicalCoxBaseline,
    },
    "Morph2Mol": {
        "MeanPool+SVR": Morph2MolRegression,
    },
}
