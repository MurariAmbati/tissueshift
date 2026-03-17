"""Training loop for TissueShift."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    """Training configuration."""

    # Data
    data_dir: str = "data"
    cohort: str = "tcga_brca"
    feature_extractor: str = "uni"

    # Model
    aggregator: str = "abmil"       # abmil or transmil
    state_dim: int = 512
    path_dim: int = 512
    mol_dim: int = 256
    spat_dim: int = 128
    n_subtypes: int = 5

    # Training
    epochs: int = 50
    batch_size: int = 32
    lr: float = 1e-4
    weight_decay: float = 1e-5
    warmup_epochs: int = 5
    grad_clip: float = 1.0

    # Loss weights
    w_subtype: float = 1.0
    w_vicreg: float = 0.1
    w_contrastive: float = 0.5
    w_survival: float = 0.5
    w_progression: float = 0.3
    w_morph2mol: float = 0.3
    w_microenv: float = 0.2
    w_transition: float = 0.3

    # Checkpointing
    checkpoint_dir: str = "checkpoints"
    save_every: int = 5
    eval_every: int = 1

    # Stage (which heads are active)
    stage: str = "full"  # pretrain, finetune, full

    # Hardware
    device: str = "cuda"
    mixed_precision: bool = True
    num_workers: int = 4

    # Logging
    wandb_project: str = "tissueshift"
    wandb_entity: str | None = None
    log_every: int = 10

    @classmethod
    def from_yaml(cls, path: str) -> TrainConfig:
        """Load config from YAML file."""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TissueShiftDataset(Dataset):
    """Dataset that loads pre-extracted features and labels for training."""

    def __init__(self, data_dir: str, split: str = "train", cohort: str = "tcga_brca"):
        self.data_dir = Path(data_dir)
        self.split = split
        self.cohort = cohort

        # Load split manifest
        split_file = self.data_dir / cohort / "splits.json"
        if split_file.exists():
            with open(split_file) as f:
                splits = json.load(f)
            self.sample_ids = splits.get(split, [])
        else:
            # Discover samples from feature directory
            feat_dir = self.data_dir / cohort / "features"
            if feat_dir.exists():
                self.sample_ids = [p.stem for p in feat_dir.glob("*.h5")]
            else:
                self.sample_ids = []
                logger.warning(f"No data found at {feat_dir}")

        # Load labels
        label_file = self.data_dir / cohort / "labels.json"
        if label_file.exists():
            with open(label_file) as f:
                self.labels = json.load(f)
        else:
            self.labels = {}

        logger.info(f"Dataset {cohort}/{split}: {len(self.sample_ids)} samples")

    def __len__(self) -> int:
        return len(self.sample_ids)

    def __getitem__(self, idx: int) -> dict:
        import h5py

        sample_id = self.sample_ids[idx]
        item = {"sample_id": sample_id}

        # Load patch features
        feat_path = self.data_dir / self.cohort / "features" / f"{sample_id}.h5"
        if feat_path.exists():
            with h5py.File(feat_path, "r") as f:
                item["patch_features"] = torch.from_numpy(f["features"][:]).float()
                item["patch_coords"] = torch.from_numpy(f["coords"][:]).float()
                if "region_labels" in f:
                    item["region_labels"] = torch.from_numpy(f["region_labels"][:]).long()

        # Load molecular features
        mol_path = self.data_dir / self.cohort / "molecular" / f"{sample_id}.pt"
        if mol_path.exists():
            mol_data = torch.load(mol_path, weights_only=True)
            item.update(mol_data)

        # Load labels
        if sample_id in self.labels:
            sample_labels = self.labels[sample_id]
            if "subtype" in sample_labels:
                item["subtype"] = torch.tensor(sample_labels["subtype"]).long()
            if "event_time_bin" in sample_labels:
                item["event_time_bin"] = torch.tensor(sample_labels["event_time_bin"]).long()
                item["event_indicator"] = torch.tensor(sample_labels["event_indicator"]).float()
            if "progression_stage" in sample_labels:
                item["progression_stage"] = torch.tensor(sample_labels["progression_stage"]).long()

        return item

    @staticmethod
    def collate_fn(batch: list[dict]) -> dict:
        """Custom collation handling variable-length patch sequences."""
        collated = {}
        keys = batch[0].keys()

        for key in keys:
            if key == "sample_id":
                collated[key] = [b[key] for b in batch]
                continue

            values = [b[key] for b in batch if key in b]
            if not values:
                continue

            if key in ("patch_features", "patch_coords", "region_labels"):
                # Pad variable-length sequences
                max_len = max(v.shape[0] for v in values)
                padded = []
                mask = []
                for v in values:
                    pad_size = max_len - v.shape[0]
                    if pad_size > 0:
                        if v.dim() == 2:
                            padded.append(F.pad(v, (0, 0, 0, pad_size)))
                        else:
                            padded.append(F.pad(v, (0, pad_size)))
                    else:
                        padded.append(v)
                    m = torch.zeros(max_len, dtype=torch.bool)
                    m[: v.shape[0]] = True
                    mask.append(m)
                collated[key] = torch.stack(padded)
                collated[f"{key}_mask"] = torch.stack(mask)
            else:
                collated[key] = torch.stack(values)

        return collated


def build_model(config: TrainConfig) -> nn.Module:
    """Build the full TissueShift model from config."""
    from encoders.pathology.uni_encoder import UNIEncoder
    from encoders.pathology.region_tokenizer import RegionTokenizer
    from encoders.pathology.slide_aggregator import build_slide_aggregator
    from encoders.molecular.expression_encoder import MolecularEncoder
    from encoders.spatial.graph_encoder import build_spatial_encoder
    from world_model.tissue_state import TissueStateWorldModel
    from heads.predictions import TissueShiftHeads

    class TissueShiftModel(nn.Module):
        def __init__(self, cfg: TrainConfig):
            super().__init__()
            self.uni_encoder = UNIEncoder(feature_dim=1024, adapter_dim=64)
            self.region_tokenizer = RegionTokenizer(feature_dim=1024, n_region_types=7)
            self.slide_aggregator = build_slide_aggregator(
                method=cfg.aggregator, input_dim=1024, output_dim=cfg.path_dim
            )
            self.molecular_encoder = MolecularEncoder(output_dim=cfg.mol_dim)
            self.spatial_encoder = build_spatial_encoder("stub", output_dim=cfg.spat_dim)
            self.world_model = TissueStateWorldModel(
                path_dim=cfg.path_dim,
                mol_dim=cfg.mol_dim,
                spat_dim=cfg.spat_dim,
                state_dim=cfg.state_dim,
                n_subtypes=cfg.n_subtypes,
            )
            self.heads = TissueShiftHeads(state_dim=cfg.state_dim)

        def forward(self, batch: dict) -> dict:
            # Pathology branch
            patch_feat = batch["patch_features"]
            patch_feat = self.uni_encoder(patch_feat)
            patch_coords = batch["patch_coords"]
            region_labels = batch.get("region_labels")

            if region_labels is not None:
                region_tokens, region_mask = self.region_tokenizer(
                    patch_feat, patch_coords, region_labels
                )
                z_path, attn = self.slide_aggregator(region_tokens, region_mask)
            else:
                mask = batch.get("patch_features_mask")
                z_path, attn = self.slide_aggregator(patch_feat, mask)

            # Molecular branch
            z_mol = self.molecular_encoder(
                expression=batch.get("expression"),
                pathway_scores=batch.get("pathway_scores"),
                protein=batch.get("protein"),
                protein_available=batch.get("protein_available"),
            )

            # Spatial branch (stub)
            z_spat = self.spatial_encoder(batch_size=z_path.shape[0])

            # World model
            world_out = self.world_model(z_path, z_mol, z_spat)

            # Prediction heads
            state = world_out.state
            outputs = {
                "state": state,
                "manifold_proj": world_out.manifold_proj,
                "subtype_logits": world_out.subtype_logits,
                "subtype_probs": world_out.subtype_probs,
                "transition_logits": world_out.transition_logits,
                "transition_probs": world_out.transition_probs,
                "attention_weights": attn,
            }

            # Subtype head
            outputs["subtype_head_logits"] = self.heads.subtype(state)

            # Survival
            surv = self.heads.survival(state)
            outputs.update({f"survival_{k}": v for k, v in surv.items()})
            outputs["hazard_logits"] = surv["hazard_logits"]

            # Progression
            prog = self.heads.progression(state)
            outputs.update({f"progression_{k}": v for k, v in prog.items()})
            outputs["cumulative_logits"] = prog["cumulative_logits"]

            # Morph2Mol
            m2m = self.heads.morph2mol(state)
            outputs.update(m2m)

            # Microenvironment
            micro = self.heads.microenv(state)
            outputs.update(micro)

            return outputs

    return TissueShiftModel(config)


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    scaler: torch.amp.GradScaler | None,
    config: TrainConfig,
    epoch: int,
) -> dict[str, float]:
    """Train for one epoch."""
    model.train()
    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    epoch_losses = {}
    n_batches = 0

    for batch_idx, batch in enumerate(dataloader):
        # Move to device
        batch = {
            k: v.to(device) if isinstance(v, torch.Tensor) else v
            for k, v in batch.items()
        }

        optimizer.zero_grad()

        if scaler is not None and config.mixed_precision:
            with torch.amp.autocast("cuda"):
                outputs = model(batch)
                losses = criterion(
                    outputs,
                    batch,
                    manifold_proj=outputs.get("manifold_proj"),
                )
            scaler.scale(losses["total"]).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(batch)
            losses = criterion(
                outputs,
                batch,
                manifold_proj=outputs.get("manifold_proj"),
            )
            losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
            optimizer.step()

        # Accumulate losses
        for k, v in losses.items():
            if isinstance(v, torch.Tensor):
                epoch_losses[k] = epoch_losses.get(k, 0.0) + v.item()
        n_batches += 1

        if batch_idx % config.log_every == 0:
            logger.info(
                f"Epoch {epoch} [{batch_idx}/{len(dataloader)}] "
                f"loss={losses['total'].item():.4f}"
            )

    return {k: v / max(n_batches, 1) for k, v in epoch_losses.items()}


@torch.no_grad()
def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    config: TrainConfig,
) -> dict[str, float]:
    """Evaluate on validation set."""
    model.eval()
    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    epoch_losses = {}
    all_preds = []
    all_labels = []
    n_batches = 0

    for batch in dataloader:
        batch = {
            k: v.to(device) if isinstance(v, torch.Tensor) else v
            for k, v in batch.items()
        }

        outputs = model(batch)
        losses = criterion(outputs, batch, manifold_proj=outputs.get("manifold_proj"))

        for k, v in losses.items():
            if isinstance(v, torch.Tensor):
                epoch_losses[k] = epoch_losses.get(k, 0.0) + v.item()
        n_batches += 1

        if "subtype_logits" in outputs and "subtype" in batch:
            all_preds.append(outputs["subtype_logits"].argmax(dim=-1).cpu())
            all_labels.append(batch["subtype"].cpu())

    metrics = {k: v / max(n_batches, 1) for k, v in epoch_losses.items()}

    # Compute accuracy
    if all_preds:
        preds = torch.cat(all_preds)
        labels = torch.cat(all_labels)
        metrics["accuracy"] = (preds == labels).float().mean().item()

    return metrics


def train(config: TrainConfig):
    """Main training entry point."""
    # Setup
    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    checkpoint_dir = Path(config.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Training on {device}")

    # Data
    train_dataset = TissueShiftDataset(config.data_dir, "train", config.cohort)
    val_dataset = TissueShiftDataset(config.data_dir, "val", config.cohort)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        collate_fn=TissueShiftDataset.collate_fn,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        collate_fn=TissueShiftDataset.collate_fn,
        pin_memory=True,
    )

    # Model
    model = build_model(config).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model parameters: {n_params:,}")

    # Optimizer
    from training.losses import TissueShiftLoss

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )
    criterion = TissueShiftLoss(
        w_subtype=config.w_subtype,
        w_vicreg=config.w_vicreg,
        w_contrastive=config.w_contrastive,
        w_survival=config.w_survival,
        w_progression=config.w_progression,
        w_morph2mol=config.w_morph2mol,
        w_microenv=config.w_microenv,
        w_transition=config.w_transition,
    )

    # LR scheduler: cosine with warmup
    def lr_lambda(epoch):
        if epoch < config.warmup_epochs:
            return epoch / max(config.warmup_epochs, 1)
        progress = (epoch - config.warmup_epochs) / max(
            config.epochs - config.warmup_epochs, 1
        )
        return 0.5 * (1 + torch.cos(torch.tensor(progress * 3.14159)).item())

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    # Mixed precision
    scaler = torch.amp.GradScaler("cuda") if config.mixed_precision and device.type == "cuda" else None

    # Optional wandb
    try:
        import wandb

        wandb.init(
            project=config.wandb_project,
            entity=config.wandb_entity,
            config=vars(config),
        )
    except ImportError:
        logger.info("wandb not available, skipping logging")

    # Training loop
    best_val_loss = float("inf")

    for epoch in range(config.epochs):
        t0 = time.time()

        train_metrics = train_one_epoch(
            model, train_loader, optimizer, criterion, scaler, config, epoch
        )
        scheduler.step()

        # Validation
        if epoch % config.eval_every == 0:
            val_metrics = evaluate(model, val_loader, criterion, config)
            logger.info(
                f"Epoch {epoch}: train_loss={train_metrics.get('total', 0):.4f} "
                f"val_loss={val_metrics.get('total', 0):.4f} "
                f"val_acc={val_metrics.get('accuracy', 0):.4f} "
                f"lr={scheduler.get_last_lr()[0]:.6f} "
                f"time={time.time() - t0:.1f}s"
            )

            try:
                import wandb
                wandb.log({
                    **{f"train/{k}": v for k, v in train_metrics.items()},
                    **{f"val/{k}": v for k, v in val_metrics.items()},
                    "epoch": epoch,
                    "lr": scheduler.get_last_lr()[0],
                })
            except Exception:
                pass

            # Save best
            if val_metrics.get("total", float("inf")) < best_val_loss:
                best_val_loss = val_metrics["total"]
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "val_loss": best_val_loss,
                        "config": vars(config),
                    },
                    checkpoint_dir / "best_model.pt",
                )
                logger.info(f"Saved best model (val_loss={best_val_loss:.4f})")

        # Periodic checkpoint
        if epoch % config.save_every == 0:
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "config": vars(config),
                },
                checkpoint_dir / f"checkpoint_epoch_{epoch}.pt",
            )

    logger.info("Training complete!")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Train TissueShift")
    parser.add_argument("--config", type=str, help="YAML config file")
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--device", type=str, default="cuda")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.config:
        config = TrainConfig.from_yaml(args.config)
    else:
        config = TrainConfig(
            data_dir=args.data_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            device=args.device,
        )

    train(config)
