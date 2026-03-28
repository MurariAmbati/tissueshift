"""Experiment tracking integrations for TissueShift.

Provides a unified :class:`ExperimentTracker` interface with backends for
Weights & Biases, TensorBoard, and a lightweight JSON-file logger.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

logger = logging.getLogger(__name__)


# ===================================================================
# Abstract interface
# ===================================================================

class TrackerBackend(ABC):
    """Abstract base for experiment tracking backends."""

    @abstractmethod
    def log_metrics(self, metrics: Dict[str, float], step: int) -> None: ...

    @abstractmethod
    def log_config(self, config: Dict[str, Any]) -> None: ...

    @abstractmethod
    def log_artifact(self, path: str, name: str, artifact_type: str = "model") -> None: ...

    @abstractmethod
    def log_text(self, key: str, text: str, step: int) -> None: ...

    def log_image(self, key: str, image: Any, step: int) -> None:
        pass

    def finish(self) -> None:
        pass


# ===================================================================
# Weights & Biases backend
# ===================================================================

class WandBTracker(TrackerBackend):
    """Weights & Biases experiment tracker.

    Parameters
    ----------
    project : str
        W&B project name.
    run_name : str, optional
        Run display name.
    tags : list of str, optional
        Tags for the run.
    entity : str, optional
        W&B team / entity.
    config : dict, optional
        Initial config to log.
    """

    def __init__(
        self,
        project: str = "tissueshift",
        run_name: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        entity: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            import wandb
            self._wandb = wandb
        except ImportError:
            raise ImportError("wandb is required: pip install wandb")

        self.run = wandb.init(
            project=project,
            name=run_name,
            tags=list(tags) if tags else None,
            entity=entity,
            config=config or {},
        )
        logger.info("W&B run initialized: %s", self.run.url)

    def log_metrics(self, metrics: Dict[str, float], step: int) -> None:
        self._wandb.log(metrics, step=step)

    def log_config(self, config: Dict[str, Any]) -> None:
        self._wandb.config.update(config, allow_val_change=True)

    def log_artifact(self, path: str, name: str, artifact_type: str = "model") -> None:
        artifact = self._wandb.Artifact(name, type=artifact_type)
        artifact.add_file(path)
        self.run.log_artifact(artifact)

    def log_text(self, key: str, text: str, step: int) -> None:
        self._wandb.log({key: self._wandb.Html(f"<pre>{text}</pre>")}, step=step)

    def log_image(self, key: str, image: Any, step: int) -> None:
        self._wandb.log({key: self._wandb.Image(image)}, step=step)

    def finish(self) -> None:
        self._wandb.finish()


# ===================================================================
# TensorBoard backend
# ===================================================================

class TensorBoardTracker(TrackerBackend):
    """TensorBoard experiment tracker.

    Parameters
    ----------
    log_dir : str
        TensorBoard log directory.
    """

    def __init__(self, log_dir: str = "runs/tissueshift") -> None:
        try:
            from torch.utils.tensorboard import SummaryWriter
        except ImportError:
            raise ImportError("tensorboard is required: pip install tensorboard")
        self.writer = SummaryWriter(log_dir=log_dir)
        self.log_dir = log_dir
        logger.info("TensorBoard logging to: %s", log_dir)

    def log_metrics(self, metrics: Dict[str, float], step: int) -> None:
        for key, val in metrics.items():
            self.writer.add_scalar(key, val, global_step=step)
        self.writer.flush()

    def log_config(self, config: Dict[str, Any]) -> None:
        # Write config as text
        config_str = json.dumps(config, indent=2, default=str)
        self.writer.add_text("config", f"```json\n{config_str}\n```", global_step=0)

    def log_artifact(self, path: str, name: str, artifact_type: str = "model") -> None:
        logger.info("TensorBoard: artifact saved at %s (name=%s)", path, name)

    def log_text(self, key: str, text: str, step: int) -> None:
        self.writer.add_text(key, text, global_step=step)

    def log_image(self, key: str, image: Any, step: int) -> None:
        import numpy as np
        if hasattr(image, "numpy"):
            img_np = image.numpy()
        elif isinstance(image, np.ndarray):
            img_np = image
        else:
            return
        if img_np.ndim == 3 and img_np.shape[2] in (3, 4):
            img_np = img_np.transpose(2, 0, 1)  # HWC → CHW
        self.writer.add_image(key, img_np, global_step=step)

    def finish(self) -> None:
        self.writer.close()


# ===================================================================
# JSON file-based logger (no external deps)
# ===================================================================

class JSONTracker(TrackerBackend):
    """Lightweight JSON-file tracker for environments without W&B/TB.

    Writes metrics to a JSONL (JSON Lines) file and config to a separate
    JSON file.

    Parameters
    ----------
    output_dir : str
        Directory for log files.
    run_name : str
        Name of this run.
    """

    def __init__(self, output_dir: str = "logs", run_name: str = "run") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_path = self.output_dir / f"{run_name}_metrics.jsonl"
        self.config_path = self.output_dir / f"{run_name}_config.json"
        self.text_path = self.output_dir / f"{run_name}_text.jsonl"
        logger.info("JSON tracker logging to: %s", self.output_dir)

    def log_metrics(self, metrics: Dict[str, float], step: int) -> None:
        record = {"step": step, "timestamp": time.time(), **metrics}
        with open(self.metrics_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def log_config(self, config: Dict[str, Any]) -> None:
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2, default=str)

    def log_artifact(self, path: str, name: str, artifact_type: str = "model") -> None:
        record = {"artifact": name, "path": path, "type": artifact_type, "timestamp": time.time()}
        with open(self.output_dir / "artifacts.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")

    def log_text(self, key: str, text: str, step: int) -> None:
        record = {"step": step, "key": key, "text": text}
        with open(self.text_path, "a") as f:
            f.write(json.dumps(record) + "\n")


# ===================================================================
# Unified tracker
# ===================================================================

class ExperimentTracker:
    """Unified experiment tracker that fans out to multiple backends.

    Parameters
    ----------
    backends : list of str
        Which backends to enable: ``"wandb"``, ``"tensorboard"``, ``"json"``.
        Default: ``["json"]``.
    project : str
        Project/experiment group name.
    run_name : str, optional
        Display name for this run.
    tags : list of str, optional
        Tags (W&B only).
    log_dir : str
        Base directory for TensorBoard / JSON logs.
    wandb_entity : str, optional
        W&B team name.
    config : dict, optional
        Config to log at initialisation.
    """

    def __init__(
        self,
        backends: Sequence[str] = ("json",),
        project: str = "tissueshift",
        run_name: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        log_dir: str = "logs",
        wandb_entity: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._backends: list[TrackerBackend] = []
        run_name = run_name or f"run_{int(time.time())}"

        for backend_name in backends:
            if backend_name == "wandb":
                self._backends.append(WandBTracker(
                    project=project, run_name=run_name,
                    tags=tags, entity=wandb_entity, config=config,
                ))
            elif backend_name == "tensorboard":
                self._backends.append(TensorBoardTracker(
                    log_dir=str(Path(log_dir) / "tensorboard" / run_name),
                ))
            elif backend_name == "json":
                self._backends.append(JSONTracker(
                    output_dir=str(Path(log_dir) / "json"),
                    run_name=run_name,
                ))
            else:
                logger.warning("Unknown tracker backend: %s", backend_name)

        if config:
            self.log_config(config)

        self._step = 0

    @property
    def step(self) -> int:
        return self._step

    @step.setter
    def step(self, value: int) -> None:
        self._step = value

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        s = step if step is not None else self._step
        for b in self._backends:
            b.log_metrics(metrics, s)

    def log_config(self, config: Dict[str, Any]) -> None:
        for b in self._backends:
            b.log_config(config)

    def log_artifact(self, path: str, name: str, artifact_type: str = "model") -> None:
        for b in self._backends:
            b.log_artifact(path, name, artifact_type)

    def log_text(self, key: str, text: str, step: Optional[int] = None) -> None:
        s = step if step is not None else self._step
        for b in self._backends:
            b.log_text(key, text, s)

    def log_image(self, key: str, image: Any, step: Optional[int] = None) -> None:
        s = step if step is not None else self._step
        for b in self._backends:
            b.log_image(key, image, s)

    def log_stage(self, stage_idx: int, stage_name: str) -> None:
        """Log the start of a training stage."""
        self.log_text("training/stage", f"Stage {stage_idx}: {stage_name}", self._step)
        self.log_metrics({"training/current_stage": stage_idx}, self._step)

    def log_epoch(
        self,
        stage: int,
        epoch: int,
        train_loss: float,
        val_loss: Optional[float] = None,
        lr: Optional[float] = None,
        extra: Optional[Dict[str, float]] = None,
    ) -> None:
        """Convenience: log a full epoch of training metrics."""
        metrics = {
            f"stage_{stage}/train_loss": train_loss,
            f"stage_{stage}/epoch": epoch,
        }
        if val_loss is not None:
            metrics[f"stage_{stage}/val_loss"] = val_loss
        if lr is not None:
            metrics[f"stage_{stage}/learning_rate"] = lr
        if extra:
            for k, v in extra.items():
                metrics[f"stage_{stage}/{k}"] = v
        self.log_metrics(metrics, self._step)
        self._step += 1

    def finish(self) -> None:
        for b in self._backends:
            b.finish()
        logger.info("Experiment tracking finished.")
