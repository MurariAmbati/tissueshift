"""
Staged training pipeline for TissueShift.

Stage 1: Pretrain histology encoder (TCGA + CPTAC + HPA)
Stage 2: Train molecular encoder (TCGA + CPTAC)
Stage 3: Train spatial encoder (HTAN)
Stage 4: Build progression bridge (joint, all sources)
Stage 5: Train transition model + drift heads
Stage 6: Calibration, uncertainty, subgroup robustness
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from tissueshift.config import TissueShiftConfig
from tissueshift.training.losses import TissueShiftLoss
from tissueshift.world_model.tissueshift_model import TissueShiftModel

logger = logging.getLogger(__name__)


class TissueShiftTrainer:
    """
    Multi-stage trainer for TissueShift.

    Each stage freezes/unfreezes appropriate components and
    uses stage-specific learning rates, epochs, and loss weights.
    """

    def __init__(
        self,
        cfg: TissueShiftConfig,
        model: TissueShiftModel,
        device: Optional[torch.device] = None,
    ):
        self.cfg = cfg
        self.model = model
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        self.loss_fn = TissueShiftLoss(cfg.training)
        self.current_stage = 0
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Parameter groups per stage
    # ------------------------------------------------------------------
    def _get_param_groups(self, stage: int) -> list:
        """Get parameter groups with per-component learning rates."""
        tcfg = self.cfg.training

        if stage == 1:
            # Only pathology encoder
            return [{"params": self.model.pathology_encoder.parameters(), "lr": tcfg.stage1_lr}]
        elif stage == 2:
            # Only molecular encoder
            return [{"params": self.model.molecular_encoder.parameters(), "lr": tcfg.stage2_lr}]
        elif stage == 3:
            # Only spatial encoder
            return [{"params": self.model.spatial_encoder.parameters(), "lr": tcfg.stage3_lr}]
        elif stage == 4:
            # Joint: all encoders + tissue state + heads (lower LR for encoders)
            return [
                {"params": self.model.pathology_encoder.parameters(), "lr": tcfg.stage4_lr * 0.1},
                {"params": self.model.molecular_encoder.parameters(), "lr": tcfg.stage4_lr * 0.1},
                {"params": self.model.spatial_encoder.parameters(), "lr": tcfg.stage4_lr * 0.1},
                {"params": self.model.tissue_state_model.parameters(), "lr": tcfg.stage4_lr},
                {"params": self.model.subtype_head.parameters(), "lr": tcfg.stage4_lr},
                {"params": self.model.progression_head.parameters(), "lr": tcfg.stage4_lr},
                {"params": self.model.morphology_bridge.parameters(), "lr": tcfg.stage4_lr},
                {"params": self.model.microenv_head.parameters(), "lr": tcfg.stage4_lr},
                {"params": self.model.survival_head.parameters(), "lr": tcfg.stage4_lr},
            ]
        elif stage == 5:
            # Transition model + drift head + fine-tune tissue state
            return [
                {"params": self.model.transition_model.parameters(), "lr": tcfg.stage5_lr},
                {"params": self.model.drift_head.parameters(), "lr": tcfg.stage5_lr},
                {"params": self.model.tissue_state_model.parameters(), "lr": tcfg.stage5_lr * 0.1},
            ]
        else:  # stage 6
            # Full model at very low LR for calibration
            return [{"params": self.model.parameters(), "lr": tcfg.stage6_lr}]

    def _freeze_except(self, stage: int) -> None:
        """Freeze all parameters except those active in the current stage."""
        # First freeze everything
        for param in self.model.parameters():
            param.requires_grad = False

        # Then unfreeze stage-specific components
        if stage == 1:
            for p in self.model.pathology_encoder.parameters():
                p.requires_grad = True
        elif stage == 2:
            for p in self.model.molecular_encoder.parameters():
                p.requires_grad = True
        elif stage == 3:
            for p in self.model.spatial_encoder.parameters():
                p.requires_grad = True
        elif stage == 4:
            for p in self.model.parameters():
                p.requires_grad = True
        elif stage == 5:
            for p in self.model.transition_model.parameters():
                p.requires_grad = True
            for p in self.model.drift_head.parameters():
                p.requires_grad = True
            for p in self.model.tissue_state_model.parameters():
                p.requires_grad = True
        else:
            for p in self.model.parameters():
                p.requires_grad = True

    def _build_optimizer(self, stage: int) -> torch.optim.Optimizer:
        param_groups = self._get_param_groups(stage)
        return torch.optim.AdamW(
            param_groups,
            weight_decay=self.cfg.training.weight_decay,
        )

    def _build_scheduler(self, optimizer: torch.optim.Optimizer, num_epochs: int):
        tcfg = self.cfg.training
        if tcfg.scheduler == "cosine":
            return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
        elif tcfg.scheduler == "plateau":
            return torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        else:
            return torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=[g["lr"] for g in optimizer.param_groups],
                epochs=num_epochs,
                steps_per_epoch=100,  # placeholder
            )

    # ------------------------------------------------------------------
    # Training loop
    # ------------------------------------------------------------------
    def train_stage(
        self,
        stage: int,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
    ) -> Dict[str, Any]:
        """Train a single stage."""
        self.current_stage = stage
        tcfg = self.cfg.training
        epochs_map = {
            1: tcfg.stage1_epochs, 2: tcfg.stage2_epochs, 3: tcfg.stage3_epochs,
            4: tcfg.stage4_epochs, 5: tcfg.stage5_epochs, 6: tcfg.stage6_epochs,
        }
        num_epochs = epochs_map[stage]

        logger.info("=" * 60)
        logger.info("STAGE %d — %d epochs", stage, num_epochs)
        logger.info("=" * 60)

        self._freeze_except(stage)
        optimizer = self._build_optimizer(stage)
        scheduler = self._build_scheduler(optimizer, num_epochs)

        scaler = torch.amp.GradScaler("cuda") if tcfg.mixed_precision and self.device.type == "cuda" else None

        best_val_loss = float("inf")
        patience_counter = 0
        stage_history: List[Dict[str, float]] = []

        for epoch in range(num_epochs):
            # ---- Train ----
            self.model.train()
            epoch_losses: Dict[str, float] = {}
            n_batches = 0
            t0 = time.time()

            for batch in train_loader:
                optimizer.zero_grad()

                # Build model inputs from batch
                model_kwargs = self._batch_to_model_inputs(batch)
                targets = self._batch_to_targets(batch)

                if tcfg.mixed_precision and scaler is not None:
                    with torch.amp.autocast("cuda"):
                        outputs = self.model(**model_kwargs)
                        losses = self.loss_fn(outputs, targets, stage)
                    scaler.scale(losses["total"]).backward()
                    scaler.unscale_(optimizer)
                    nn.utils.clip_grad_norm_(self.model.parameters(), tcfg.grad_clip)
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    outputs = self.model(**model_kwargs)
                    losses = self.loss_fn(outputs, targets, stage)
                    losses["total"].backward()
                    nn.utils.clip_grad_norm_(self.model.parameters(), tcfg.grad_clip)
                    optimizer.step()

                for k, v in losses.items():
                    epoch_losses[k] = epoch_losses.get(k, 0.0) + v.item()
                n_batches += 1

            # Average losses
            for k in epoch_losses:
                epoch_losses[k] /= max(n_batches, 1)

            # ---- Validate ----
            val_loss = None
            if val_loader is not None:
                val_loss = self._validate(val_loader, stage)
                epoch_losses["val_total"] = val_loss

            # Scheduler step
            if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau) and val_loss is not None:
                scheduler.step(val_loss)
            elif not isinstance(scheduler, torch.optim.lr_scheduler.OneCycleLR):
                scheduler.step()

            elapsed = time.time() - t0
            logger.info(
                "Stage %d | Epoch %d/%d | train_loss=%.4f | val_loss=%s | %.1fs",
                stage, epoch + 1, num_epochs,
                epoch_losses.get("total", 0),
                f"{val_loss:.4f}" if val_loss is not None else "N/A",
                elapsed,
            )
            stage_history.append(epoch_losses)

            # Early stopping
            if val_loss is not None:
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    self._save_checkpoint(stage, epoch, is_best=True)
                else:
                    patience_counter += 1
                    if patience_counter >= tcfg.early_stop_patience:
                        logger.info("Early stopping at epoch %d", epoch + 1)
                        break

        result = {
            "stage": stage,
            "epochs_trained": len(stage_history),
            "best_val_loss": best_val_loss,
            "history": stage_history,
        }
        self.history.append(result)
        return result

    def train_all_stages(
        self,
        stage_loaders: Dict[int, Dict[str, DataLoader]],
    ) -> List[Dict[str, Any]]:
        """
        Train all six stages sequentially.

        stage_loaders: {stage_num: {"train": loader, "val": loader}}
        """
        results = []
        for stage in range(1, 7):
            if stage in stage_loaders:
                loaders = stage_loaders[stage]
                result = self.train_stage(
                    stage,
                    loaders["train"],
                    loaders.get("val"),
                )
                results.append(result)
            else:
                logger.warning("No loader for stage %d — skipping", stage)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _batch_to_model_inputs(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a batch dict to model forward kwargs."""
        kwargs: Dict[str, Any] = {}

        if "tiles" in batch:
            kwargs["tiles"] = batch["tiles"].to(self.device)
        if "rna" in batch:
            kwargs["rna"] = batch["rna"].to(self.device)
        if "proteomics" in batch:
            kwargs["proteomics"] = batch["proteomics"].to(self.device)
        if "cnv" in batch:
            kwargs["cnv"] = batch["cnv"].to(self.device)
        if "cell_graph" in batch:
            kwargs["cell_graph"] = batch["cell_graph"]

        return kwargs

    def _batch_to_targets(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        """Extract target labels from batch."""
        targets: Dict[str, Any] = {}

        if "pam50_idx" in batch:
            targets["pam50_idx"] = batch["pam50_idx"]
        if "progression_idx" in batch:
            targets["stage_idx"] = batch["progression_idx"]
        if "expression" in batch:
            targets["expression_target"] = batch["expression"]

        return targets

    @torch.no_grad()
    def _validate(self, val_loader: DataLoader, stage: int) -> float:
        """Run validation and return average total loss."""
        self.model.eval()
        total_loss = 0.0
        n = 0
        for batch in val_loader:
            kwargs = self._batch_to_model_inputs(batch)
            targets = self._batch_to_targets(batch)
            outputs = self.model(**kwargs)
            losses = self.loss_fn(outputs, targets, stage)
            total_loss += losses["total"].item()
            n += 1
        return total_loss / max(n, 1)

    def _save_checkpoint(self, stage: int, epoch: int, is_best: bool = False) -> None:
        """Save model checkpoint."""
        ckpt_dir = self.cfg.training.checkpoint_dir
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        name = f"stage{stage}_epoch{epoch}" + ("_best" if is_best else "")
        path = ckpt_dir / f"{name}.pt"
        torch.save({
            "stage": stage,
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
        }, path)
        logger.info("Checkpoint saved: %s", path)

    def load_checkpoint(self, path: Path) -> Dict[str, Any]:
        """Load a checkpoint and return metadata."""
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        logger.info("Loaded checkpoint: stage=%d, epoch=%d", ckpt["stage"], ckpt["epoch"])
        return ckpt
