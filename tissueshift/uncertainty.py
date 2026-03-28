"""Uncertainty quantification for clinical-grade predictions.

Provides multiple complementary uncertainty estimation strategies:

1. **Conformal Prediction** — distribution-free prediction sets with
   guaranteed coverage.  Given a calibration set, produces prediction
   *sets* (not just point estimates) whose coverage is statistically
   valid regardless of the true distribution.

2. **Evidential Deep Learning** — Dirichlet prior over class
   probabilities.  A single forward pass yields both the predicted
   distribution *and* epistemic uncertainty (how much the model
   "doesn't know").

3. **Temperature Scaling** — post-hoc calibration of softmax outputs
   so that confidence == accuracy.

4. **Ensemble Disagreement** — measures spread across multiple model
   checkpoints or MC-dropout samples.

5. **Selective Prediction** — abstention mechanism that defers to a
   pathologist when model uncertainty exceeds a clinically-set
   threshold.

References
----------
Shafer & Vovk, "A Tutorial on Conformal Prediction", JMLR 2008.
Sensoy et al., "Evidential Deep Learning", NeurIPS 2018.
Guo et al., "On Calibration of Modern Neural Networks", ICML 2017.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class UncertaintyConfig:
    """Configuration for the uncertainty module."""

    # Conformal prediction
    conformal_alpha: float = 0.10  # 1 - desired coverage (90% default)
    conformal_method: str = "aps"  # aps | lac | raps
    raps_k_reg: int = 3  # RAPS regularisation parameter
    raps_lambda: float = 0.01

    # Evidential
    evidential_annealing_epochs: int = 10
    evidential_kl_weight: float = 0.01

    # Temperature scaling
    temperature_max_iter: int = 100

    # Selective prediction
    abstention_threshold: float = 0.70  # confidence below this → defer
    abstention_entropy_threshold: float = 1.5

    # Ensemble
    ensemble_size: int = 5
    mc_dropout_samples: int = 30


# ===================================================================
# 1. Conformal Prediction
# ===================================================================

class ConformalPredictor:
    """Distribution-free prediction sets with finite-sample coverage.

    Supports three non-conformity score functions:
    * **LAC** (Least Ambiguous set-valued Classifier) — thresholds on
      1 - softmax_prob of ground truth.
    * **APS** (Adaptive Prediction Sets) — cumulative sorted
      probabilities until coverage.
    * **RAPS** (Regularised APS) — APS + penalty for large sets.
    """

    def __init__(self, cfg: UncertaintyConfig):
        self.alpha = cfg.conformal_alpha
        self.method = cfg.conformal_method
        self.k_reg = cfg.raps_k_reg
        self.lam = cfg.raps_lambda
        self._qhat: Optional[float] = None

    def calibrate(
        self,
        cal_probs: np.ndarray,
        cal_labels: np.ndarray,
    ) -> float:
        """Compute the conformal quantile from a calibration set.

        Parameters
        ----------
        cal_probs : (N_cal, C) — softmax probabilities on calibration data
        cal_labels : (N_cal,) — true class indices

        Returns
        -------
        qhat : float — the estimated quantile threshold
        """
        n = len(cal_labels)
        scores = self._nonconformity_scores(cal_probs, cal_labels)
        # Finite-sample correction
        level = np.ceil((1 - self.alpha) * (n + 1)) / n
        level = min(level, 1.0)
        self._qhat = float(np.quantile(scores, level))
        logger.info(
            "Conformal calibration: method=%s, n_cal=%d, qhat=%.4f",
            self.method,
            n,
            self._qhat,
        )
        return self._qhat

    def predict_sets(
        self, probs: np.ndarray
    ) -> List[List[int]]:
        """Produce prediction sets for new samples.

        Parameters
        ----------
        probs : (N, C) — softmax probabilities

        Returns
        -------
        sets : list of lists of class indices in the prediction set
        """
        if self._qhat is None:
            raise RuntimeError("Must call calibrate() before predict_sets().")

        sets: list[list[int]] = []
        for i in range(len(probs)):
            if self.method == "lac":
                s = self._lac_set(probs[i])
            elif self.method == "aps":
                s = self._aps_set(probs[i])
            elif self.method == "raps":
                s = self._raps_set(probs[i])
            else:
                s = self._aps_set(probs[i])
            sets.append(s)
        return sets

    def coverage_and_size(
        self,
        sets: List[List[int]],
        true_labels: np.ndarray,
    ) -> Dict[str, float]:
        """Compute empirical coverage and average set size."""
        covered = sum(
            1 for s, y in zip(sets, true_labels) if int(y) in s
        )
        avg_size = np.mean([len(s) for s in sets])
        return {
            "coverage": covered / len(true_labels),
            "avg_set_size": avg_size,
        }

    # Non-conformity scores ------------------------------------------

    def _nonconformity_scores(
        self, probs: np.ndarray, labels: np.ndarray
    ) -> np.ndarray:
        if self.method == "lac":
            return 1.0 - probs[np.arange(len(labels)), labels.astype(int)]
        elif self.method in ("aps", "raps"):
            return self._aps_scores(probs, labels)
        return self._aps_scores(probs, labels)

    def _aps_scores(
        self, probs: np.ndarray, labels: np.ndarray
    ) -> np.ndarray:
        n, C = probs.shape
        sorted_idx = np.argsort(-probs, axis=1)
        sorted_probs = np.take_along_axis(probs, sorted_idx, axis=1)
        cumsum = np.cumsum(sorted_probs, axis=1)

        # Where does the true label sit in the sorted order?
        scores = np.zeros(n)
        for i in range(n):
            rank = np.where(sorted_idx[i] == int(labels[i]))[0][0]
            scores[i] = cumsum[i, rank]
            if self.method == "raps":
                penalty = self.lam * max(0, rank + 1 - self.k_reg)
                scores[i] += penalty
        return scores

    # Set construction -----------------------------------------------

    def _lac_set(self, probs: np.ndarray) -> List[int]:
        return [int(c) for c in range(len(probs)) if 1.0 - probs[c] <= self._qhat]

    def _aps_set(self, probs: np.ndarray) -> List[int]:
        order = np.argsort(-probs)
        cumsum = 0.0
        result: list[int] = []
        for c in order:
            result.append(int(c))
            cumsum += probs[c]
            if cumsum >= self._qhat:
                break
        return result

    def _raps_set(self, probs: np.ndarray) -> List[int]:
        order = np.argsort(-probs)
        cumsum = 0.0
        result: list[int] = []
        for rank, c in enumerate(order):
            penalty = self.lam * max(0, rank + 1 - self.k_reg)
            result.append(int(c))
            cumsum += probs[c]
            if cumsum + penalty >= self._qhat:
                break
        return result


# ===================================================================
# 2. Evidential Deep Learning
# ===================================================================

class EvidentialHead(nn.Module):
    """Dirichlet-based evidential classification head.

    Instead of a softmax, outputs parameters (α₁, …, αₖ) of a Dirichlet
    distribution Dir(α) over class probabilities.  The *total evidence*
    S = Σαₖ quantifies how much data support the prediction, while the
    *vacuity* u = K/S measures epistemic uncertainty.
    """

    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256):
        super().__init__()
        self.num_classes = num_classes
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.SiLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Compute Dirichlet parameters & derived quantities.

        Returns
        -------
        alpha : (B, C) — Dirichlet concentration parameters
        evidence : (B, C) — α − 1
        expected_prob : (B, C) — E[p] = α / S
        vacuity : (B,) — K / S  (epistemic uncertainty)
        dissonance : (B,) — inter-class conflict
        aleatoric : (B,) — expected entropy of the Dirichlet
        """
        # Ensure positive evidence via softplus
        evidence = F.softplus(self.net(x))
        alpha = evidence + 1.0
        S = alpha.sum(dim=-1, keepdim=True)  # (B, 1)
        K = float(self.num_classes)

        expected_prob = alpha / S
        vacuity = K / S.squeeze(-1)

        # Dissonance (Deng et al.): how much evidence conflicts
        belief = evidence / S
        bal = torch.zeros(x.shape[0], device=x.device)
        for i in range(self.num_classes):
            for j in range(i + 1, self.num_classes):
                bi, bj = belief[:, i], belief[:, j]
                bal += (1 - torch.abs(bi - bj) / (bi + bj + 1e-8)) * bi * bj
        dissonance = bal

        # Aleatoric uncertainty: expected entropy under Dirichlet
        digamma_S = torch.digamma(S.squeeze(-1))
        aleatoric = -(
            (alpha / S * (torch.digamma(alpha) - digamma_S.unsqueeze(-1)))
            .sum(dim=-1)
        )

        return {
            "alpha": alpha,
            "evidence": evidence,
            "expected_prob": expected_prob,
            "vacuity": vacuity,
            "dissonance": dissonance,
            "aleatoric": aleatoric,
        }


class EvidentialLoss(nn.Module):
    """Type-II maximum likelihood loss for Dirichlet classification.

    Computes:
      L = Σᵢ [log(S) − log(αᵧ)]  + λ·KL[Dir(α̃) || Dir(1)]

    where α̃ removes non-target evidence to penalise "evidence for
    wrong classes".
    """

    def __init__(self, num_classes: int, kl_weight: float = 0.01):
        super().__init__()
        self.num_classes = num_classes
        self.kl_weight = kl_weight

    def forward(
        self,
        alpha: torch.Tensor,
        targets: torch.Tensor,
        epoch: int = 0,
        annealing_epochs: int = 10,
    ) -> torch.Tensor:
        """Compute evidential loss.

        Parameters
        ----------
        alpha : (B, C) — Dirichlet params from EvidentialHead
        targets : (B,) — class indices
        epoch : current training epoch (for KL annealing)
        """
        S = alpha.sum(dim=-1, keepdim=True)
        y_one_hot = F.one_hot(targets.long(), self.num_classes).float()

        # Type-II ML
        ml_loss = (
            y_one_hot * (torch.digamma(S) - torch.digamma(alpha))
        ).sum(dim=-1).mean()

        # KL regularisation (with annealing)
        anneal = min(1.0, epoch / max(annealing_epochs, 1))
        alpha_tilde = y_one_hot + (1 - y_one_hot) * (alpha - 1) + 1
        kl = self._kl_dirichlet(alpha_tilde)

        return ml_loss + self.kl_weight * anneal * kl

    def _kl_dirichlet(self, alpha: torch.Tensor) -> torch.Tensor:
        """KL[Dir(α) || Dir(1)]."""
        K = alpha.shape[-1]
        ones = torch.ones_like(alpha)
        S_alpha = alpha.sum(dim=-1)
        S_ones = ones.sum(dim=-1)

        kl = (
            torch.lgamma(S_alpha)
            - torch.lgamma(S_ones)
            - (torch.lgamma(alpha) - torch.lgamma(ones)).sum(dim=-1)
            + ((alpha - ones) * (torch.digamma(alpha) - torch.digamma(S_alpha.unsqueeze(-1)))).sum(dim=-1)
        )
        return kl.mean()


# ===================================================================
# 3. Temperature Scaling
# ===================================================================

class TemperatureScaler(nn.Module):
    """Post-hoc temperature scaling for model calibration.

    Learns a single scalar T > 0 such that softmax(logits / T) is
    well-calibrated on a held-out validation set.  This does *not*
    change the rank-order of predictions.
    """

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """Scale logits by temperature."""
        return logits / self.temperature.clamp(min=0.01)

    def calibrate(
        self,
        logits: torch.Tensor,
        labels: torch.Tensor,
        max_iter: int = 100,
        lr: float = 0.01,
    ) -> float:
        """Optimise temperature on calibration data.

        Parameters
        ----------
        logits : (N, C)
        labels : (N,) — class indices

        Returns
        -------
        Optimal temperature value.
        """
        self.train()
        opt = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)
        ce = nn.CrossEntropyLoss()

        def closure():
            opt.zero_grad()
            loss = ce(self.forward(logits), labels)
            loss.backward()
            return loss

        opt.step(closure)
        self.eval()
        logger.info("Temperature scaling: T=%.4f", self.temperature.item())
        return self.temperature.item()

    def expected_calibration_error(
        self,
        probs: np.ndarray,
        labels: np.ndarray,
        n_bins: int = 15,
    ) -> float:
        """Compute ECE after calibration."""
        confidences = probs.max(axis=1)
        predictions = probs.argmax(axis=1)
        correct = (predictions == labels).astype(float)

        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        for b in range(n_bins):
            lo, hi = bin_boundaries[b], bin_boundaries[b + 1]
            mask = (confidences > lo) & (confidences <= hi)
            if mask.sum() == 0:
                continue
            bin_acc = correct[mask].mean()
            bin_conf = confidences[mask].mean()
            ece += mask.sum() / len(labels) * abs(bin_acc - bin_conf)
        return float(ece)


# ===================================================================
# 4. Ensemble Disagreement
# ===================================================================

class EnsembleUncertainty:
    """Measure uncertainty from an ensemble of forward passes.

    Works with:
    * Multiple model checkpoints (deep ensemble)
    * MC-dropout samples from a single model
    * Stochastic weight averaging Gaussian (SWAG) samples
    """

    @staticmethod
    def predictive_entropy(probs_ensemble: np.ndarray) -> np.ndarray:
        """Total uncertainty: H[E[p]].

        Parameters
        ----------
        probs_ensemble : (M, N, C) — M forward passes, N samples, C classes

        Returns
        -------
        entropy : (N,)
        """
        mean_probs = probs_ensemble.mean(axis=0)  # (N, C)
        eps = 1e-10
        return -(mean_probs * np.log(mean_probs + eps)).sum(axis=-1)

    @staticmethod
    def mutual_information(probs_ensemble: np.ndarray) -> np.ndarray:
        """Epistemic uncertainty via BALD: I[y ; θ | x].

        MI = H[E[p]] − E[H[p]]
        """
        total_entropy = EnsembleUncertainty.predictive_entropy(probs_ensemble)
        eps = 1e-10
        per_model_entropy = -(probs_ensemble * np.log(probs_ensemble + eps)).sum(axis=-1)
        expected_entropy = per_model_entropy.mean(axis=0)
        return total_entropy - expected_entropy

    @staticmethod
    def variation_ratio(probs_ensemble: np.ndarray) -> np.ndarray:
        """Fraction of models that disagree with the ensemble prediction.

        Returns
        -------
        vr : (N,) in [0, 1)
        """
        predictions = probs_ensemble.argmax(axis=-1)  # (M, N)
        modes = np.apply_along_axis(
            lambda x: np.bincount(x, minlength=probs_ensemble.shape[-1]).argmax(),
            axis=0,
            arr=predictions,
        )
        agree = (predictions == modes[np.newaxis, :]).sum(axis=0)
        return 1.0 - agree / probs_ensemble.shape[0]

    @staticmethod
    def prediction_interval(
        values_ensemble: np.ndarray, confidence: float = 0.90
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute mean and prediction interval for regression.

        Parameters
        ----------
        values_ensemble : (M, N) or (M, N, D)

        Returns
        -------
        mean, lower, upper
        """
        alpha = (1 - confidence) / 2
        mean = values_ensemble.mean(axis=0)
        lower = np.quantile(values_ensemble, alpha, axis=0)
        upper = np.quantile(values_ensemble, 1 - alpha, axis=0)
        return mean, lower, upper

    @staticmethod
    def mc_dropout_forward(
        model: nn.Module,
        inputs: Dict[str, torch.Tensor],
        n_samples: int = 30,
        output_key: str = "pam50_probs",
    ) -> np.ndarray:
        """Collect MC-dropout forward passes.

        Enables dropout at test time and collects *n_samples* stochastic
        forward passes.

        Returns
        -------
        probs_ensemble : (n_samples, B, C)
        """
        model.train()  # Enable dropout
        results = []
        with torch.no_grad():
            for _ in range(n_samples):
                out = model(**inputs)
                results.append(out[output_key].cpu().numpy())
        model.eval()
        return np.stack(results, axis=0)


# ===================================================================
# 5. Selective Prediction (Abstention)
# ===================================================================

class SelectivePredictor:
    """Clinical abstention mechanism.

    Decides whether a prediction is reliable enough for clinical use
    or should be deferred to a human pathologist.  Combines multiple
    uncertainty signals with clinically-motivated thresholds.
    """

    def __init__(self, cfg: UncertaintyConfig):
        self.confidence_threshold = cfg.abstention_threshold
        self.entropy_threshold = cfg.abstention_entropy_threshold

    def should_abstain(
        self,
        probs: np.ndarray,
        vacuity: Optional[np.ndarray] = None,
        prediction_set_size: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Determine which samples to defer.

        Parameters
        ----------
        probs : (N, C) — class probabilities
        vacuity : (N,) — evidential vacuity (optional)
        prediction_set_size : (N,) — conformal set size (optional)

        Returns
        -------
        abstain_mask : (N,) bool — True = defer to pathologist
        """
        N = probs.shape[0]
        abstain = np.zeros(N, dtype=bool)

        # Rule 1: low confidence
        max_conf = probs.max(axis=1)
        abstain |= max_conf < self.confidence_threshold

        # Rule 2: high entropy
        eps = 1e-10
        entropy = -(probs * np.log(probs + eps)).sum(axis=1)
        abstain |= entropy > self.entropy_threshold

        # Rule 3: high vacuity (if available)
        if vacuity is not None:
            abstain |= vacuity > 0.5

        # Rule 4: large conformal set (if available)
        if prediction_set_size is not None:
            abstain |= prediction_set_size > max(2, probs.shape[1] // 2)

        return abstain

    def selective_accuracy(
        self,
        probs: np.ndarray,
        labels: np.ndarray,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """Compute accuracy on accepted vs deferred samples.

        Returns
        -------
        Dict with coverage, accuracy_all, accuracy_accepted,
            n_accepted, n_deferred
        """
        abstain = self.should_abstain(probs, **kwargs)
        preds = probs.argmax(axis=1)
        correct = preds == labels

        n_total = len(labels)
        n_deferred = int(abstain.sum())
        n_accepted = n_total - n_deferred

        acc_all = float(correct.mean())
        acc_accepted = float(correct[~abstain].mean()) if n_accepted > 0 else 0.0

        return {
            "coverage": n_accepted / n_total,
            "accuracy_all": acc_all,
            "accuracy_accepted": acc_accepted,
            "n_accepted": n_accepted,
            "n_deferred": n_deferred,
        }

    def risk_coverage_curve(
        self,
        probs: np.ndarray,
        labels: np.ndarray,
        n_thresholds: int = 100,
    ) -> Dict[str, np.ndarray]:
        """Compute the selective risk-coverage trade-off curve.

        Sweeps confidence thresholds and computes (coverage, risk)
        pairs.  Useful for choosing the operating point.

        Returns
        -------
        Dict with: thresholds, coverages, risks, accuracies
        """
        max_confs = probs.max(axis=1)
        preds = probs.argmax(axis=1)
        correct = (preds == labels).astype(float)

        thresholds = np.linspace(0, 1, n_thresholds)
        coverages, risks, accuracies = [], [], []

        for th in thresholds:
            accept = max_confs >= th
            n_accept = accept.sum()
            cov = n_accept / len(labels)
            coverages.append(cov)
            if n_accept > 0:
                acc = correct[accept].mean()
                accuracies.append(acc)
                risks.append(1 - acc)
            else:
                accuracies.append(1.0)
                risks.append(0.0)

        return {
            "thresholds": thresholds,
            "coverages": np.array(coverages),
            "risks": np.array(risks),
            "accuracies": np.array(accuracies),
        }


# ===================================================================
# 6. Reliability Diagram
# ===================================================================

def reliability_diagram_data(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 15,
) -> Dict[str, np.ndarray]:
    """Compute data for a reliability (calibration) diagram.

    Returns
    -------
    Dict with: bin_midpoints, accuracies, confidences, counts, ece
    """
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    correct = (predictions == labels).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_mids = (bin_boundaries[:-1] + bin_boundaries[1:]) / 2
    bin_accs = np.zeros(n_bins)
    bin_confs = np.zeros(n_bins)
    bin_counts = np.zeros(n_bins, dtype=int)

    ece = 0.0
    for b in range(n_bins):
        mask = (confidences > bin_boundaries[b]) & (confidences <= bin_boundaries[b + 1])
        count = mask.sum()
        bin_counts[b] = count
        if count == 0:
            continue
        bin_accs[b] = correct[mask].mean()
        bin_confs[b] = confidences[mask].mean()
        ece += count / len(labels) * abs(bin_accs[b] - bin_confs[b])

    return {
        "bin_midpoints": bin_mids,
        "accuracies": bin_accs,
        "confidences": bin_confs,
        "counts": bin_counts,
        "ece": ece,
    }
