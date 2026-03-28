"""
Baseline models for comparison.

Includes RNA-only, pathology-only, and flat-classifier baselines
to benchmark TissueShift's multimodal + temporal approach.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class SubtypeBaselines:
    """
    Collection of baseline models.

    1. PAM50-from-RNA: standard centroid-based PAM50 caller
    2. Random Forest on RNA features
    3. ResNet-50 tile classifier (pathology-only)
    4. Majority class baseline
    """

    def __init__(self):
        self.models: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Majority class
    # ------------------------------------------------------------------
    def fit_majority(self, y_train: np.ndarray) -> None:
        """Fit majority-class baseline."""
        from collections import Counter
        majority = Counter(y_train).most_common(1)[0][0]
        self.models["majority"] = {"class": majority}
        logger.info("Majority baseline fitted: class=%s", majority)

    def predict_majority(self, n_samples: int) -> np.ndarray:
        return np.full(n_samples, self.models["majority"]["class"])

    # ------------------------------------------------------------------
    # Random Forest on RNA
    # ------------------------------------------------------------------
    def fit_rf_rna(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int = 200,
    ) -> None:
        """Fit Random Forest on RNA expression."""
        from sklearn.ensemble import RandomForestClassifier
        rf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=20,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )
        rf.fit(X_train, y_train)
        self.models["rf_rna"] = rf
        logger.info("RF-RNA fitted: %d features, %d samples", X_train.shape[1], X_train.shape[0])

    def predict_rf_rna(self, X: np.ndarray) -> np.ndarray:
        return self.models["rf_rna"].predict(X)

    def predict_proba_rf_rna(self, X: np.ndarray) -> np.ndarray:
        return self.models["rf_rna"].predict_proba(X)

    # ------------------------------------------------------------------
    # PAM50 centroid caller
    # ------------------------------------------------------------------
    @staticmethod
    def pam50_centroid_classify(
        expression_matrix: np.ndarray,
        gene_names: list,
        pam50_centroids: Optional[Dict[str, np.ndarray]] = None,
    ) -> np.ndarray:
        """
        Nearest-centroid PAM50 classification.

        If pam50_centroids is None, uses a placeholder centroid set.
        In production, use the Parker et al. 2009 centroids.
        """
        subtypes = ["LumA", "LumB", "Her2", "Basal", "Normal"]

        if pam50_centroids is None:
            logger.warning("Using random placeholder PAM50 centroids — replace with real centroids")
            rng = np.random.RandomState(0)
            pam50_centroids = {s: rng.randn(expression_matrix.shape[1]) for s in subtypes}

        predictions = []
        for sample in expression_matrix:
            dists = {s: np.linalg.norm(sample - c) for s, c in pam50_centroids.items()}
            predictions.append(min(dists, key=dists.get))

        return np.array(predictions)

    # ------------------------------------------------------------------
    # Logistic regression on clinical features
    # ------------------------------------------------------------------
    def fit_logistic_clinical(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
    ) -> None:
        """Logistic regression on ER/PR/HER2/age features."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        scaler = StandardScaler().fit(X_train)
        X_scaled = scaler.transform(X_train)
        lr = LogisticRegression(
            max_iter=1000, random_state=42, class_weight="balanced",
        )
        lr.fit(X_scaled, y_train)
        self.models["logistic_clinical"] = {"model": lr, "scaler": scaler}

    def predict_logistic_clinical(self, X: np.ndarray) -> np.ndarray:
        m = self.models["logistic_clinical"]
        return m["model"].predict(m["scaler"].transform(X))
