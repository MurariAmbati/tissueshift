"""Active learning engine — pathologist-in-the-loop sample selection.

Provides acquisition functions and query strategies for selecting the
most informative unlabelled samples to present to a human expert,
maximising annotation efficiency.

Key Components
--------------
* **Acquisition Functions** — BALD, variation-ratio, predictive entropy,
  expected gradient length, coreset greedy-k, badge (batch-mode).
* **AcquisitionPool** — manages labelled/unlabelled splits.
* **ActiveLearningLoop** — full query → label → retrain loop.
* **DiversitySampler** — ensures selected batches cover the latent space.

References
----------
Gal, Islam, Ghahramani. "Deep Bayesian Active Learning with Image Data", ICML 2017.
Ash et al., "Deep Batch Active Learning by Diverse, Uncertain Gradient …" (BADGE), ICLR 2020.
Sener & Savarese, "Active Learning for CNNs: A Core-Set Approach", ICLR 2018.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class ActiveLearningConfig:
    """Parameters for active learning."""

    strategy: str = "bald"  # bald | var_ratio | entropy | badge | coreset | random
    query_size: int = 32
    mc_samples: int = 20  # MC-dropout forward passes
    initial_pool_fraction: float = 0.05  # fraction labelled at start
    diversity_weight: float = 0.3  # blend diversity into score
    coreset_metric: str = "euclidean"
    badge_embedding_dim: int = 128
    max_rounds: int = 50


# ===================================================================
# Acquisition Functions
# ===================================================================

class AcquisitionFunctions:
    """Static methods computing per-sample acquisition scores.

    All functions take MC-dropout prediction tensors of shape
    ``(mc_samples, N, C)`` where *C* is the number of classes.
    """

    @staticmethod
    def predictive_entropy(mc_probs: torch.Tensor) -> torch.Tensor:
        """H[y | x, D] — total uncertainty.  Shape (N,)."""
        mean_probs = mc_probs.mean(dim=0)  # (N, C)
        return -(mean_probs * (mean_probs + 1e-10).log()).sum(dim=-1)

    @staticmethod
    def bald(mc_probs: torch.Tensor) -> torch.Tensor:
        """Bayesian Active Learning by Disagreement.

        I[y; θ | x, D]  =  H[y | x, D] - E_θ[H[y | x, θ]]
        """
        total_h = AcquisitionFunctions.predictive_entropy(mc_probs)
        per_sample_h = -(mc_probs * (mc_probs + 1e-10).log()).sum(dim=-1)  # (T, N)
        cond_h = per_sample_h.mean(dim=0)
        return total_h - cond_h

    @staticmethod
    def variation_ratio(mc_probs: torch.Tensor) -> torch.Tensor:
        """Fraction of MC samples that disagree with the mode."""
        preds = mc_probs.argmax(dim=-1)  # (T, N)
        modes = preds.mode(dim=0).values  # (N,)
        agreement = (preds == modes.unsqueeze(0)).float().mean(dim=0)
        return 1.0 - agreement

    @staticmethod
    def mean_std(mc_probs: torch.Tensor) -> torch.Tensor:
        """Mean standard‐deviation across classes."""
        return mc_probs.std(dim=0).mean(dim=-1)

    @staticmethod
    def max_entropy_margin(mc_probs: torch.Tensor) -> torch.Tensor:
        """1 - (p_top1 - p_top2)  from the mean posterior."""
        mean_p = mc_probs.mean(dim=0)  # (N, C)
        top2 = mean_p.topk(2, dim=-1).values  # (N, 2)
        margin = top2[:, 0] - top2[:, 1]
        return 1.0 - margin


# ===================================================================
# BADGE Gradient Embeddings
# ===================================================================

class BADGEEmbedder:
    """Computes gradient embeddings for batch-mode active learning (BADGE).

    For each sample, the "hypothetical gradient" w.r.t. the last-layer
    parameters under the most likely label is used as a representation.
    k-means++ seeding in this gradient-embedding space yields a diverse
    and uncertain batch.
    """

    @staticmethod
    @torch.no_grad()
    def gradient_embeddings(
        model: nn.Module,
        dataloader: Any,
        device: str = "cpu",
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute per-sample gradient embeddings.

        Returns (embeddings: (N, D*C), indices: (N,))
        """
        model.eval()
        all_emb: list[torch.Tensor] = []
        all_idx: list[torch.Tensor] = []

        for batch in dataloader:
            x = batch["inputs"] if isinstance(batch, dict) else batch
            if isinstance(x, dict):
                x = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in x.items()}
                out = model(**x)
            else:
                out = model(x.to(device))

            logits = out["logits"] if isinstance(out, dict) else out
            probs = F.softmax(logits, dim=-1)
            pseudo_labels = probs.argmax(dim=-1)

            # Gradient of CE w.r.t. logits = probs - one_hot(label)
            one_hot = F.one_hot(pseudo_labels, probs.shape[-1]).float()
            grad_embed = probs - one_hot  # (B, C) — the "gradient embedding"

            all_emb.append(grad_embed.cpu())
            idx = batch.get("index", torch.arange(len(logits)))
            all_idx.append(idx if isinstance(idx, torch.Tensor) else torch.tensor(idx))

        return torch.cat(all_emb), torch.cat(all_idx)

    @staticmethod
    def kmeanspp_select(
        embeddings: torch.Tensor, k: int
    ) -> List[int]:
        """k-means++ initialisation to pick *k* diverse centres."""
        N = len(embeddings)
        if k >= N:
            return list(range(N))

        # First centre uniform at random
        selected = [int(np.random.randint(N))]
        min_dists = torch.full((N,), float("inf"))

        for _ in range(k - 1):
            last_center = embeddings[selected[-1]].unsqueeze(0)
            dists = ((embeddings - last_center) ** 2).sum(dim=-1)
            min_dists = torch.minimum(min_dists, dists)

            probs = min_dists / (min_dists.sum() + 1e-10)
            idx = int(torch.multinomial(probs, 1).item())
            selected.append(idx)

        return selected


# ===================================================================
# Coreset Greedy-k
# ===================================================================

class CoresetSelector:
    """Greedy k-centre coreset selection in the model's latent space."""

    @staticmethod
    @torch.no_grad()
    def extract_features(
        model: nn.Module, dataloader: Any, device: str = "cpu"
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Extract penultimate features.  Returns (features, indices)."""
        model.eval()
        feats: list[torch.Tensor] = []
        idxs: list[torch.Tensor] = []

        for batch in dataloader:
            x = batch["inputs"] if isinstance(batch, dict) else batch
            if isinstance(x, dict):
                x = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in x.items()}
                out = model(**x)
            else:
                out = model(x.to(device))

            feat = out.get("features", out.get("z", None)) if isinstance(out, dict) else out
            if feat is None:
                continue
            feats.append(feat.cpu())
            idx = batch.get("index", torch.arange(len(feat)))
            idxs.append(idx if isinstance(idx, torch.Tensor) else torch.tensor(idx))

        return torch.cat(feats), torch.cat(idxs)

    @staticmethod
    def greedy_k_centre(
        labelled_features: torch.Tensor,
        unlabelled_features: torch.Tensor,
        k: int,
    ) -> List[int]:
        """Select *k* points that minimise max distance to nearest centre."""
        # Initial distances from unlabelled to nearest labelled
        if len(labelled_features) > 0:
            dists = torch.cdist(unlabelled_features, labelled_features)
            min_dists = dists.min(dim=1).values  # (Nu,)
        else:
            min_dists = torch.full((len(unlabelled_features),), float("inf"))

        selected: list[int] = []
        for _ in range(min(k, len(unlabelled_features))):
            # Pick point with maximum distance to nearest centre
            idx = int(min_dists.argmax().item())
            selected.append(idx)

            # Update distances
            new_dists = ((unlabelled_features - unlabelled_features[idx].unsqueeze(0)) ** 2).sum(dim=-1).sqrt()
            min_dists = torch.minimum(min_dists, new_dists)

        return selected


# ===================================================================
# Diversity-Weighted Scoring
# ===================================================================

class DiversitySampler:
    """Blends acquisition score with latent-space diversity.

    Uses Determinantal Point Process (DPP) quality-diversity decomposition
    approximated via greedy MAP.
    """

    @staticmethod
    def diverse_topk(
        scores: torch.Tensor,
        features: torch.Tensor,
        k: int,
        diversity_weight: float = 0.3,
    ) -> List[int]:
        """Select top-k balancing score and diversity.

        Uses iterative greedy: at each step pick the sample maximising
            (1 - λ) * score + λ * min_dist_to_selected
        """
        N = len(scores)
        if k >= N:
            return list(range(N))

        # Normalise scores to [0, 1]
        s = scores.float()
        s = (s - s.min()) / (s.max() - s.min() + 1e-10)

        selected: list[int] = []
        min_dists = torch.full((N,), float("inf"))

        for _ in range(k):
            if not selected:
                combined = s
            else:
                d = min_dists / (min_dists.max() + 1e-10)
                combined = (1 - diversity_weight) * s + diversity_weight * d

            # Mask already selected
            for idx in selected:
                combined[idx] = -1.0

            best = int(combined.argmax().item())
            selected.append(best)

            # Update min distances
            new_dists = ((features - features[best].unsqueeze(0)) ** 2).sum(dim=-1).sqrt()
            min_dists = torch.minimum(min_dists, new_dists)

        return selected


# ===================================================================
# Acquisition Pool
# ===================================================================

class AcquisitionPool:
    """Manages labelled / unlabelled splits for active learning."""

    def __init__(
        self,
        total_size: int,
        initial_labelled: Optional[Sequence[int]] = None,
        initial_fraction: float = 0.05,
        seed: int = 42,
    ):
        rng = np.random.RandomState(seed)
        if initial_labelled is not None:
            self.labelled = set(initial_labelled)
        else:
            n_init = max(1, int(total_size * initial_fraction))
            self.labelled = set(rng.choice(total_size, n_init, replace=False).tolist())

        self.total_size = total_size
        self.query_history: list[list[int]] = []

    @property
    def unlabelled(self) -> List[int]:
        return sorted(set(range(self.total_size)) - self.labelled)

    @property
    def labelled_list(self) -> List[int]:
        return sorted(self.labelled)

    def label(self, indices: Sequence[int]) -> None:
        """Move indices from unlabelled to labelled."""
        self.labelled.update(indices)
        self.query_history.append(list(indices))
        logger.info(
            "Labelled %d samples (total labelled: %d / %d)",
            len(indices), len(self.labelled), self.total_size,
        )

    def label_fraction(self) -> float:
        return len(self.labelled) / max(self.total_size, 1)

    def summary(self) -> Dict[str, Any]:
        return {
            "total": self.total_size,
            "labelled": len(self.labelled),
            "unlabelled": len(self.unlabelled),
            "fraction_labelled": self.label_fraction(),
            "n_rounds": len(self.query_history),
        }


# ===================================================================
# MC-Dropout Inference
# ===================================================================

def mc_dropout_predict(
    model: nn.Module,
    dataloader: Any,
    mc_samples: int = 20,
    device: str = "cpu",
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Run MC-dropout forward passes.

    Returns
    -------
    mc_probs : (T, N, C)
    indices  : (N,)
    """
    model.train()  # keep dropout active
    all_probs: list[list[torch.Tensor]] = []
    all_idx: list[torch.Tensor] = []

    for _ in range(mc_samples):
        round_probs: list[torch.Tensor] = []
        round_idx: list[torch.Tensor] = []
        for batch in dataloader:
            x = batch["inputs"] if isinstance(batch, dict) else batch
            if isinstance(x, dict):
                x = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in x.items()}
                with torch.no_grad():
                    out = model(**x)
            else:
                with torch.no_grad():
                    out = model(x.to(device))

            logits = out["logits"] if isinstance(out, dict) else out
            round_probs.append(F.softmax(logits, dim=-1).cpu())
            if not all_idx:
                idx = batch.get("index", torch.arange(len(logits)))
                round_idx.append(idx if isinstance(idx, torch.Tensor) else torch.tensor(idx))

        all_probs.append(torch.cat(round_probs))
        if not all_idx:
            all_idx = round_idx

    return torch.stack(all_probs), torch.cat(all_idx)


# ===================================================================
# Active Learning Loop
# ===================================================================

class ActiveLearningLoop:
    """Full active learning loop: query → label → retrain.

    This orchestrates the entire active learning process, selecting
    the most informative samples after each training round.
    """

    def __init__(
        self,
        model: nn.Module,
        pool: AcquisitionPool,
        train_fn: Callable[[nn.Module, List[int]], Dict[str, float]],
        eval_fn: Callable[[nn.Module], Dict[str, float]],
        unlabelled_loader_fn: Callable[[List[int]], Any],
        cfg: ActiveLearningConfig = ActiveLearningConfig(),
        device: str = "cpu",
    ):
        """
        Parameters
        ----------
        model : The model to train.
        pool : Acquisition pool managing labelled/unlabelled splits.
        train_fn : Callable(model, labelled_indices) → metrics dict.
            Responsible for building a dataloader from indices and training.
        eval_fn : Callable(model) → metrics dict.
            Evaluates the model on a held-out test set.
        unlabelled_loader_fn : Callable(unlabelled_indices) → DataLoader.
            Builds a dataloader for the unlabelled set (for acquisition).
        """
        self.model = model
        self.pool = pool
        self.train_fn = train_fn
        self.eval_fn = eval_fn
        self.unlabelled_loader_fn = unlabelled_loader_fn
        self.cfg = cfg
        self.device = device
        self.history: list[Dict[str, Any]] = []

    def run(self, max_rounds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute the active learning loop."""
        rounds = max_rounds or self.cfg.max_rounds

        for r in range(rounds):
            logger.info(
                "=== AL Round %d/%d  (labelled=%d) ===",
                r + 1, rounds, len(self.pool.labelled),
            )

            # 1. Train on current labelled set
            train_metrics = self.train_fn(self.model, self.pool.labelled_list)

            # 2. Evaluate
            eval_metrics = self.eval_fn(self.model)

            # 3. Acquire new samples
            unlabelled = self.pool.unlabelled
            if len(unlabelled) == 0:
                logger.info("No unlabelled samples remaining.")
                break

            selected = self._acquire(unlabelled)

            # 4. Label (simulated or human-in-the-loop)
            self.pool.label(selected)

            round_info = {
                "round": r,
                "train_metrics": train_metrics,
                "eval_metrics": eval_metrics,
                "n_queried": len(selected),
                **self.pool.summary(),
            }
            self.history.append(round_info)

        return self.history

    def _acquire(self, unlabelled: List[int]) -> List[int]:
        """Select samples to query."""
        k = min(self.cfg.query_size, len(unlabelled))

        if self.cfg.strategy == "random":
            chosen = np.random.choice(len(unlabelled), k, replace=False)
            return [unlabelled[i] for i in chosen]

        loader = self.unlabelled_loader_fn(unlabelled)

        if self.cfg.strategy == "badge":
            return self._badge_acquire(loader, unlabelled, k)

        if self.cfg.strategy == "coreset":
            return self._coreset_acquire(loader, unlabelled, k)

        # Score-based strategies
        mc_probs, _ = mc_dropout_predict(
            self.model, loader, self.cfg.mc_samples, self.device
        )

        if self.cfg.strategy == "bald":
            scores = AcquisitionFunctions.bald(mc_probs)
        elif self.cfg.strategy == "var_ratio":
            scores = AcquisitionFunctions.variation_ratio(mc_probs)
        elif self.cfg.strategy == "entropy":
            scores = AcquisitionFunctions.predictive_entropy(mc_probs)
        elif self.cfg.strategy == "mean_std":
            scores = AcquisitionFunctions.mean_std(mc_probs)
        else:
            scores = AcquisitionFunctions.bald(mc_probs)

        # Optional diversity blending
        if self.cfg.diversity_weight > 0:
            feats, _ = CoresetSelector.extract_features(
                self.model, loader, self.device
            )
            if feats is not None and len(feats) == len(scores):
                sel = DiversitySampler.diverse_topk(
                    scores, feats, k, self.cfg.diversity_weight
                )
                return [unlabelled[i] for i in sel]

        topk = scores.topk(k).indices.tolist()
        return [unlabelled[i] for i in topk]

    def _badge_acquire(
        self, loader: Any, unlabelled: List[int], k: int
    ) -> List[int]:
        """BADGE: gradient embedding + k-means++ selection."""
        embeddings, _ = BADGEEmbedder.gradient_embeddings(
            self.model, loader, self.device
        )
        sel = BADGEEmbedder.kmeanspp_select(embeddings, k)
        return [unlabelled[i] for i in sel]

    def _coreset_acquire(
        self, loader: Any, unlabelled: List[int], k: int
    ) -> List[int]:
        """Coreset: greedy k-centre in feature space."""
        un_feats, _ = CoresetSelector.extract_features(
            self.model, loader, self.device
        )
        # Get labelled features too
        lab_loader = self.unlabelled_loader_fn(self.pool.labelled_list)
        lab_feats, _ = CoresetSelector.extract_features(
            self.model, lab_loader, self.device
        )
        sel = CoresetSelector.greedy_k_centre(lab_feats, un_feats, k)
        return [unlabelled[i] for i in sel]
