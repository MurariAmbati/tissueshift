"""Distributed training utilities for TissueShift.

Wraps the :class:`TissueShiftTrainer` with PyTorch ``DistributedDataParallel``
(DDP) support, gradient accumulation, and multi-node launch helpers.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler

logger = logging.getLogger(__name__)


# ===================================================================
# DDP setup / teardown
# ===================================================================

def setup_distributed(
    backend: str = "nccl",
    init_method: Optional[str] = None,
) -> int:
    """Initialize the default process group.

    Reads ``RANK``, ``WORLD_SIZE``, ``LOCAL_RANK`` from environment
    (set by ``torchrun`` / ``torch.distributed.launch``).

    Returns the local rank.
    """
    rank = int(os.environ.get("RANK", 0))
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    local_rank = int(os.environ.get("LOCAL_RANK", 0))

    if world_size <= 1:
        logger.info("Single-GPU mode — skipping distributed init")
        return local_rank

    if init_method is None:
        init_method = "env://"

    dist.init_process_group(
        backend=backend,
        init_method=init_method,
        rank=rank,
        world_size=world_size,
    )
    torch.cuda.set_device(local_rank)
    logger.info(
        "Distributed: rank=%d, local_rank=%d, world_size=%d, backend=%s",
        rank, local_rank, world_size, backend,
    )
    return local_rank


def teardown_distributed() -> None:
    """Destroy the default process group."""
    if dist.is_initialized():
        dist.destroy_process_group()


def is_main_process() -> bool:
    """True on rank-0 or when not running distributed."""
    if not dist.is_initialized():
        return True
    return dist.get_rank() == 0


def get_world_size() -> int:
    if not dist.is_initialized():
        return 1
    return dist.get_world_size()


# ===================================================================
# Distributed data loader wrapper
# ===================================================================

def make_distributed_loader(
    dataset: Any,
    batch_size: int,
    num_workers: int = 4,
    shuffle: bool = True,
    seed: int = 42,
    drop_last: bool = True,
    **kwargs,
) -> DataLoader:
    """Create a DataLoader with DistributedSampler.

    Parameters
    ----------
    dataset : Dataset
        PyTorch dataset.
    batch_size : int
        **Per-GPU** batch size.
    num_workers : int
        DataLoader workers.
    shuffle : bool
        Shuffle via the distributed sampler.
    seed : int
        Seed for reproducible shuffling.
    drop_last : bool
        Drop incomplete last batch.

    Returns
    -------
    DataLoader
    """
    sampler = None
    if dist.is_initialized() and get_world_size() > 1:
        sampler = DistributedSampler(
            dataset, shuffle=shuffle, seed=seed, drop_last=drop_last,
        )
        shuffle = False  # sampler handles shuffling

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle if sampler is None else False,
        sampler=sampler,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=drop_last,
        **kwargs,
    )


# ===================================================================
# Gradient accumulation wrapper
# ===================================================================

class GradientAccumulator:
    """Context manager for gradient accumulation across micro-batches.

    Parameters
    ----------
    model : nn.Module
        The model (may be DDP-wrapped).
    accumulation_steps : int
        Number of micro-batches to accumulate before stepping.
    """

    def __init__(self, model: nn.Module, accumulation_steps: int = 1) -> None:
        self.model = model
        self.accumulation_steps = max(1, accumulation_steps)
        self._step_count = 0

    def should_step(self) -> bool:
        """Check if the optimizer should step after this micro-batch."""
        self._step_count += 1
        return self._step_count % self.accumulation_steps == 0

    def scale_loss(self, loss: torch.Tensor) -> torch.Tensor:
        """Scale loss by accumulation steps to maintain consistent effective LR."""
        return loss / self.accumulation_steps

    @property
    def sync_context(self):
        """Context manager to skip gradient sync on non-step micro-batches.

        For DDP, uses ``model.no_sync()`` to defer AllReduce until the
        final accumulation step.
        """
        if (
            isinstance(self.model, DDP)
            and self._step_count % self.accumulation_steps != 0
        ):
            return self.model.no_sync()

        # No-op context manager
        import contextlib
        return contextlib.nullcontext()

    def reset(self) -> None:
        self._step_count = 0


# ===================================================================
# Distributed trainer wrapper
# ===================================================================

class DistributedTrainer:
    """Wraps :class:`TissueShiftTrainer` for multi-GPU training.

    Parameters
    ----------
    model : TissueShiftModel
        Unwrapped model.
    config : TissueShiftConfig
        Configuration.
    local_rank : int
        GPU index for this process.
    accumulation_steps : int
        Gradient accumulation factor.
    sync_bn : bool
        Convert BatchNorm to SyncBatchNorm.
    find_unused : bool
        DDP ``find_unused_parameters`` flag.
    """

    def __init__(
        self,
        model: nn.Module,
        config: Any,
        local_rank: int = 0,
        accumulation_steps: int = 1,
        sync_bn: bool = True,
        find_unused: bool = True,
    ) -> None:
        self.config = config
        self.local_rank = local_rank
        self.accumulation_steps = accumulation_steps
        self.device = torch.device(f"cuda:{local_rank}")

        # Sync BatchNorm
        if sync_bn and get_world_size() > 1:
            model = nn.SyncBatchNorm.convert_sync_batchnorm(model)
            logger.info("Converted BatchNorm → SyncBatchNorm")

        self.model = model.to(self.device)

        # Wrap with DDP
        if dist.is_initialized() and get_world_size() > 1:
            self.ddp_model = DDP(
                self.model,
                device_ids=[local_rank],
                output_device=local_rank,
                find_unused_parameters=find_unused,
            )
        else:
            self.ddp_model = self.model

        self.accumulator = GradientAccumulator(self.ddp_model, accumulation_steps)

        # Import base trainer for training loop
        from tissueshift.training.trainer import TissueShiftTrainer
        self._base_trainer = TissueShiftTrainer.__new__(TissueShiftTrainer)
        self._base_trainer.model = self.ddp_model
        self._base_trainer.config = config
        self._base_trainer.device = self.device

    def train_epoch(
        self,
        train_loader: DataLoader,
        optimizer: torch.optim.Optimizer,
        loss_fn: Any,
        scaler: Optional[torch.amp.GradScaler] = None,
    ) -> float:
        """Train one epoch with gradient accumulation and DDP sync.

        Parameters
        ----------
        train_loader : DataLoader
            Training data (should use DistributedSampler).
        optimizer : Optimizer
        loss_fn : callable
        scaler : GradScaler, optional
            For mixed-precision training.

        Returns
        -------
        float — average loss for the epoch.
        """
        self.ddp_model.train()
        total_loss = 0.0
        n_batches = 0
        self.accumulator.reset()

        # Set epoch on sampler for proper shuffling
        if hasattr(train_loader, "sampler") and isinstance(
            train_loader.sampler, DistributedSampler
        ):
            train_loader.sampler.set_epoch(n_batches)

        for batch in train_loader:
            # Move batch to device
            batch = self._to_device(batch)

            with self.accumulator.sync_context:
                if scaler is not None:
                    with torch.amp.autocast("cuda"):
                        outputs = self.ddp_model(batch)
                        loss = loss_fn(outputs, batch)
                    loss = self.accumulator.scale_loss(loss)
                    scaler.scale(loss).backward()
                else:
                    outputs = self.ddp_model(batch)
                    loss = loss_fn(outputs, batch)
                    loss = self.accumulator.scale_loss(loss)
                    loss.backward()

            if self.accumulator.should_step():
                if scaler is not None:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                optimizer.zero_grad()

            total_loss += loss.item() * self.accumulation_steps
            n_batches += 1

        return total_loss / max(n_batches, 1)

    def save_checkpoint(self, path: str, epoch: int, **extras) -> None:
        """Save checkpoint (only on rank 0)."""
        if not is_main_process():
            return
        unwrapped = self.ddp_model.module if isinstance(self.ddp_model, DDP) else self.ddp_model
        torch.save({
            "model_state_dict": unwrapped.state_dict(),
            "epoch": epoch,
            **extras,
        }, path)
        logger.info("Checkpoint saved: %s", path)

    def _to_device(self, batch: Any) -> Any:
        """Recursively move batch to device."""
        if isinstance(batch, torch.Tensor):
            return batch.to(self.device, non_blocking=True)
        if isinstance(batch, dict):
            return {k: self._to_device(v) for k, v in batch.items()}
        if isinstance(batch, (list, tuple)):
            return type(batch)(self._to_device(v) for v in batch)
        return batch
