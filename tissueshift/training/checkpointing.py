"""Advanced checkpoint utilities for TissueShift.

Provides:
- :class:`TopKCheckpointManager` — keeps only the K best checkpoints
- :class:`ExponentialMovingAverage` — Polyak-style weight averaging
- :func:`average_checkpoints` — uniform weight averaging across runs
"""

from __future__ import annotations

import copy
import heapq
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


# ===================================================================
# Top-K checkpoint manager
# ===================================================================

class TopKCheckpointManager:
    """Keep only the top-K model checkpoints by validation metric.

    Parameters
    ----------
    save_dir : str
        Directory for checkpoint files.
    top_k : int
        Maximum number of checkpoints to retain.
    mode : str
        ``"min"`` (lower is better, e.g. loss) or ``"max"`` (higher is better).
    """

    def __init__(
        self,
        save_dir: str,
        top_k: int = 3,
        mode: str = "min",
    ) -> None:
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.top_k = top_k
        self.mode = mode

        # Min-heap for "max" mode (negate scores), max-heap not natively
        # supported so we use negation trick:
        #   mode="min" → store (score, path)  pop largest score
        #   mode="max" → store (-score, path) pop smallest -score (= largest)
        self._heap: list[tuple[float, str]] = []

    def save(
        self,
        model: nn.Module,
        score: float,
        epoch: int,
        stage: int = 0,
        optimizer: Optional[torch.optim.Optimizer] = None,
        scaler: Optional[torch.amp.GradScaler] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Save a checkpoint if it qualifies for top-K.

        Returns
        -------
        str | None
            Path to saved checkpoint, or None if it didn't qualify.
        """
        heap_score = score if self.mode == "min" else -score

        # Check if qualified
        if len(self._heap) >= self.top_k:
            # For min mode: worst = largest score → heap[-1] style
            # We use negative trick for max-heap behavior
            worst_score = max(self._heap, key=lambda x: x[0])[0]
            if heap_score >= worst_score:
                return None  # This checkpoint is worse than all current top-K

        # Build checkpoint path
        filename = f"stage{stage}_epoch{epoch}_score{score:.4f}.pt"
        filepath = self.save_dir / filename

        # Save
        state = {
            "model_state_dict": model.state_dict(),
            "epoch": epoch,
            "stage": stage,
            "score": score,
        }
        if optimizer is not None:
            state["optimizer_state_dict"] = optimizer.state_dict()
        if scaler is not None:
            state["scaler_state_dict"] = scaler.state_dict()
        if extra:
            state.update(extra)

        torch.save(state, filepath)
        logger.info("Saved checkpoint: %s (score=%.4f)", filename, score)

        # Add to heap
        heapq.heappush(self._heap, (heap_score, str(filepath)))

        # Remove worst if over capacity
        if len(self._heap) > self.top_k:
            self._remove_worst()

        return str(filepath)

    def _remove_worst(self) -> None:
        """Remove the worst checkpoint (highest heap_score)."""
        if not self._heap:
            return
        # Find and remove worst
        worst_idx = max(range(len(self._heap)), key=lambda i: self._heap[i][0])
        _, worst_path = self._heap.pop(worst_idx)
        heapq.heapify(self._heap)

        path = Path(worst_path)
        if path.exists():
            path.unlink()
            logger.info("Removed worst checkpoint: %s", path.name)

    @property
    def best_path(self) -> Optional[str]:
        """Path to the best checkpoint."""
        if not self._heap:
            return None
        best = min(self._heap, key=lambda x: x[0])
        return best[1]

    @property
    def best_score(self) -> Optional[float]:
        """Best metric score."""
        if not self._heap:
            return None
        best = min(self._heap, key=lambda x: x[0])
        return best[0] if self.mode == "min" else -best[0]

    @property
    def all_checkpoints(self) -> List[Dict[str, Any]]:
        """List all tracked checkpoints with scores."""
        results = []
        for heap_score, path in self._heap:
            score = heap_score if self.mode == "min" else -heap_score
            results.append({"path": path, "score": score})
        results.sort(key=lambda x: x["score"], reverse=(self.mode == "max"))
        return results


# ===================================================================
# Exponential Moving Average (EMA)
# ===================================================================

class ExponentialMovingAverage:
    """Exponential moving average of model parameters (Polyak averaging).

    Maintains a shadow copy of model weights that is updated as:
        shadow = decay * shadow + (1 - decay) * current

    Parameters
    ----------
    model : nn.Module
        Model whose parameters to track.
    decay : float
        EMA decay rate (typically 0.999 or 0.9999).
    """

    def __init__(self, model: nn.Module, decay: float = 0.999) -> None:
        self.decay = decay
        self.shadow: Dict[str, torch.Tensor] = {}
        self.backup: Dict[str, torch.Tensor] = {}

        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self, model: nn.Module) -> None:
        """Update shadow weights with current model parameters."""
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.shadow:
                self.shadow[name].mul_(self.decay).add_(
                    param.data, alpha=1.0 - self.decay
                )

    def apply(self, model: nn.Module) -> None:
        """Replace model parameters with EMA shadow weights."""
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.shadow:
                self.backup[name] = param.data.clone()
                param.data.copy_(self.shadow[name])

    def restore(self, model: nn.Module) -> None:
        """Restore original model parameters (undo ``apply``)."""
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data.copy_(self.backup[name])
        self.backup = {}

    def state_dict(self) -> Dict[str, torch.Tensor]:
        return {"shadow": self.shadow, "decay": self.decay}

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        self.shadow = state["shadow"]
        self.decay = state.get("decay", self.decay)


# ===================================================================
# Checkpoint averaging (Stochastic Weight Averaging style)
# ===================================================================

def average_checkpoints(
    checkpoint_paths: List[str],
    model: nn.Module,
) -> nn.Module:
    """Average model weights from multiple checkpoints.

    Implements uniform weight averaging (SWA / checkpoint soup).

    Parameters
    ----------
    checkpoint_paths : list of str
        Paths to ``.pt`` files with ``model_state_dict``.
    model : nn.Module
        Model architecture (used to load state dicts).

    Returns
    -------
    nn.Module with averaged weights.
    """
    if not checkpoint_paths:
        raise ValueError("No checkpoint paths provided")

    avg_state: Dict[str, torch.Tensor] = {}
    n = len(checkpoint_paths)

    for i, path in enumerate(checkpoint_paths):
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        state = ckpt.get("model_state_dict", ckpt)

        for key, val in state.items():
            if key not in avg_state:
                avg_state[key] = val.float().clone()
            else:
                avg_state[key] += val.float()

    # Divide by count
    for key in avg_state:
        avg_state[key] /= n

    model.load_state_dict(avg_state)
    logger.info("Averaged %d checkpoints", n)
    return model


def find_best_checkpoint(
    checkpoint_dir: str,
    mode: str = "min",
) -> Optional[str]:
    """Scan a directory for the best checkpoint by score in filename.

    Expects filenames like ``stage*_epoch*_score*.pt``.

    Returns
    -------
    str | None
        Path to the best checkpoint.
    """
    ckpt_dir = Path(checkpoint_dir)
    if not ckpt_dir.exists():
        return None

    best_path = None
    best_score = float("inf") if mode == "min" else float("-inf")

    for pt_file in ckpt_dir.glob("*.pt"):
        # Extract score from filename
        name = pt_file.stem
        if "score" not in name:
            continue
        score_str = name.split("score")[-1]
        try:
            score = float(score_str)
        except ValueError:
            continue

        if (mode == "min" and score < best_score) or (mode == "max" and score > best_score):
            best_score = score
            best_path = str(pt_file)

    return best_path
