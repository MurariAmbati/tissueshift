"""End-to-end inference pipeline for TissueShift.

Orchestrates preprocessing → encoding → prediction for new samples with
support for partial modalities, batched inference, and uncertainty estimation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import torch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class TissueShiftPrediction:
    """Container for all model predictions on a single sample."""

    sample_id: str = ""

    # Tissue state
    tissue_state: Optional[np.ndarray] = None  # (latent_dim,)
    tissue_axes: Optional[Dict[str, float]] = None  # axis_name → score

    # Subtype
    subtype_pam50_probs: Optional[np.ndarray] = None  # (5,)
    subtype_ihc_probs: Optional[np.ndarray] = None  # (4,)
    subtype_lattice_probs: Optional[np.ndarray] = None  # (7,)
    subtype_confidence: Optional[float] = None

    # Progression
    progression_stage_probs: Optional[np.ndarray] = None  # (5,)
    progression_ordinal_score: Optional[float] = None

    # Drift (requires pair)
    drift_class_probs: Optional[np.ndarray] = None  # (3,)
    drift_magnitude: Optional[float] = None

    # Microenvironment
    microenv_overall: Optional[float] = None
    microenv_components: Optional[Dict[str, float]] = None

    # Survival
    survival_curve: Optional[np.ndarray] = None  # (num_intervals,)
    risk_score: Optional[float] = None

    # Molecular bridge
    predicted_expression: Optional[np.ndarray] = None
    predicted_pathways: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        out: Dict[str, Any] = {"sample_id": self.sample_id}
        for k, v in self.__dict__.items():
            if k == "sample_id":
                continue
            if v is None:
                continue
            if isinstance(v, np.ndarray):
                out[k] = v.tolist()
            elif isinstance(v, dict):
                out[k] = {dk: dv.tolist() if isinstance(dv, np.ndarray) else dv for dk, dv in v.items()}
            else:
                out[k] = v
        return out


# ---------------------------------------------------------------------------
# Inference pipeline
# ---------------------------------------------------------------------------

class InferencePipeline:
    """Orchestrates preprocessing, encoding, and prediction.

    Parameters
    ----------
    model : TissueShiftModel
        Loaded and eval-mode model.
    config : TissueShiftConfig
        Configuration object (used for preprocessing params).
    device : str | torch.device
        Compute device.
    """

    def __init__(
        self,
        model: Any,  # TissueShiftModel — avoid circular import
        config: Any,  # TissueShiftConfig
        device: str | torch.device = "cpu",
    ) -> None:
        self.model = model
        self.config = config
        self.device = torch.device(device)
        self.model = self.model.to(self.device)
        self.model.eval()

        # Lazy-loaded preprocessors
        self._tile_extractor = None
        self._stain_normalizer = None
        self._graph_builder = None

    # ---- Lazy loaders ------------------------------------------------

    @property
    def tile_extractor(self):
        if self._tile_extractor is None:
            from tissueshift.preprocess.tile_extraction import TileExtractor
            self._tile_extractor = TileExtractor(
                tile_size=self.config.data.tile_size,
                target_magnification=self.config.data.tile_magnification,
                max_tiles_per_slide=self.config.data.max_tiles_per_slide,
            )
        return self._tile_extractor

    @property
    def stain_normalizer(self):
        if self._stain_normalizer is None:
            from tissueshift.preprocess.stain_normalization import StainNormalizer
            self._stain_normalizer = StainNormalizer(method="macenko")
        return self._stain_normalizer

    @property
    def graph_builder(self):
        if self._graph_builder is None:
            from tissueshift.preprocess.graph_builder import CellGraphBuilder
            self._graph_builder = CellGraphBuilder(
                radius=self.config.spatial.neighborhood_radius,
            )
        return self._graph_builder

    # ---- Class methods -----------------------------------------------

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str,
        config_path: Optional[str] = None,
        device: str = "cpu",
    ) -> "InferencePipeline":
        """Load a pipeline from a saved checkpoint.

        Parameters
        ----------
        checkpoint_path : str
            Path to a ``.pt`` checkpoint file.
        config_path : str, optional
            Path to YAML config. If *None*, uses default config.
        device : str
            Target device.

        Returns
        -------
        InferencePipeline
        """
        from tissueshift.config import TissueShiftConfig
        from tissueshift.world_model.tissueshift_model import TissueShiftModel

        config = TissueShiftConfig.from_yaml(config_path) if config_path else TissueShiftConfig()
        model = TissueShiftModel(config)

        ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        state_dict = ckpt.get("model_state_dict", ckpt)
        model.load_state_dict(state_dict)
        logger.info("Loaded model from %s (%d params)", checkpoint_path, model.count_parameters())

        return cls(model, config, device)

    # ---- Preprocessing helpers ---------------------------------------

    def preprocess_slide(self, slide_path: str) -> Optional[torch.Tensor]:
        """Extract and normalize tiles from a WSI.

        Returns
        -------
        torch.Tensor | None
            Tile tensor of shape ``(N, C, H, W)`` or *None* on failure.
        """
        try:
            tiles = self.tile_extractor.extract_to_tensor(slide_path)
            return tiles
        except Exception as e:
            logger.warning("Failed to preprocess slide %s: %s", slide_path, e)
            return None

    def preprocess_rna(self, rna_path: str) -> Optional[torch.Tensor]:
        """Load RNA expression from a TSV file.

        Expects a two-column TSV (gene_id, expression) or a single-column
        expression vector indexed by gene symbols.
        """
        try:
            import pandas as pd
            df = pd.read_csv(rna_path, sep="\t", index_col=0)
            values = df.iloc[:, 0].values if df.shape[1] >= 1 else df.values.flatten()
            return torch.tensor(values, dtype=torch.float32)
        except Exception as e:
            logger.warning("Failed to load RNA from %s: %s", rna_path, e)
            return None

    def preprocess_graph(self, graph_path: str):
        """Load a pre-built cell graph from a .pt file."""
        try:
            return torch.load(graph_path, map_location="cpu", weights_only=False)
        except Exception as e:
            logger.warning("Failed to load graph from %s: %s", graph_path, e)
            return None

    # ---- Core inference ----------------------------------------------

    @torch.no_grad()
    def predict(
        self,
        *,
        slide_path: Optional[str] = None,
        tile_embeddings: Optional[torch.Tensor] = None,
        gene_expression: Optional[torch.Tensor] = None,
        pathway_scores: Optional[torch.Tensor] = None,
        cnv_profile: Optional[torch.Tensor] = None,
        marker_status: Optional[torch.Tensor] = None,
        cell_graph: Optional[Any] = None,
        sample_id: str = "",
        num_mc_samples: int = 1,
    ) -> TissueShiftPrediction:
        """Run full inference on a single sample.

        Accepts any subset of modalities. If ``slide_path`` is given,
        tiles are extracted automatically; alternatively, pass
        pre-computed ``tile_embeddings`` directly.

        Parameters
        ----------
        slide_path : str, optional
            WSI file path.
        tile_embeddings : Tensor, optional
            Pre-computed tile features ``(N, D)``.
        gene_expression : Tensor, optional
            Gene expression vector.
        pathway_scores : Tensor, optional
            Hallmark pathway activity vector.
        cnv_profile : Tensor, optional
            Copy-number variation segment vector.
        marker_status : Tensor, optional
            IHC marker state ``(4,)`` for ER/PR/HER2/Ki67.
        cell_graph : PyG Data, optional
            Cell-level graph.
        sample_id : str
            Identifier for the sample.
        num_mc_samples : int
            Number of Monte-Carlo forward passes for uncertainty (VAE sampling).

        Returns
        -------
        TissueShiftPrediction
        """
        # Build batch dictionary
        batch: Dict[str, Any] = {}

        # Pathology
        if slide_path and tile_embeddings is None:
            tile_embeddings = self.preprocess_slide(slide_path)
        if tile_embeddings is not None:
            batch["tile_embeddings"] = tile_embeddings.unsqueeze(0).to(self.device)

        # Molecular
        if gene_expression is not None:
            batch["gene_expression"] = gene_expression.unsqueeze(0).to(self.device)
        if pathway_scores is not None:
            batch["pathway_scores"] = pathway_scores.unsqueeze(0).to(self.device)
        if cnv_profile is not None:
            batch["cnv_profile"] = cnv_profile.unsqueeze(0).to(self.device)
        if marker_status is not None:
            batch["marker_status"] = marker_status.unsqueeze(0).to(self.device)

        # Spatial
        if cell_graph is not None:
            batch["cell_graph"] = cell_graph

        if not batch:
            logger.warning("No input modalities provided for sample %s", sample_id)
            return TissueShiftPrediction(sample_id=sample_id)

        # MC sampling for uncertainty
        all_outputs: List[Dict[str, Any]] = []
        for _ in range(num_mc_samples):
            outputs = self.model(batch)
            all_outputs.append(outputs)

        # Aggregate MC samples
        result = self._aggregate_outputs(all_outputs, sample_id)
        return result

    @torch.no_grad()
    def predict_batch(
        self,
        samples: Sequence[Dict[str, Any]],
        num_mc_samples: int = 1,
    ) -> List[TissueShiftPrediction]:
        """Run inference on multiple samples.

        Parameters
        ----------
        samples : list of dict
            Each dict has the same keys as ``predict()`` kwargs.
        num_mc_samples : int
            MC samples for uncertainty.

        Returns
        -------
        list of TissueShiftPrediction
        """
        results = []
        for sample_kwargs in samples:
            pred = self.predict(num_mc_samples=num_mc_samples, **sample_kwargs)
            results.append(pred)
        return results

    @torch.no_grad()
    def predict_progression(
        self,
        *,
        early_state: torch.Tensor,
        late_state: Optional[torch.Tensor] = None,
        time_delta_days: float = 365.0,
    ) -> Dict[str, Any]:
        """Predict subtype transition from tissue-state vectors.

        Parameters
        ----------
        early_state : Tensor
            Tissue-state vector ``(latent_dim,)`` at earlier time-point.
        late_state : Tensor, optional
            Tissue-state vector at later time-point. If *None*, the transition
            model predicts a future state at ``time_delta_days``.
        time_delta_days : float
            Time interval in days.

        Returns
        -------
        dict with drift, predicted subtype probabilities, stability score.
        """
        z_early = early_state.unsqueeze(0).to(self.device)
        t = torch.tensor([[time_delta_days]], dtype=torch.float32, device=self.device)

        transition = self.model.transition_model
        transition_out = transition(z_early, t)

        result = {
            "stability_score": transition.stability_score(z_early).item(),
            "drift_vector": transition.drift_vector(z_early).squeeze(0).cpu().numpy().tolist(),
        }

        if "next_state" in transition_out:
            result["predicted_next_state"] = transition_out["next_state"].squeeze(0).cpu().numpy().tolist()
        if "edge_logits" in transition_out:
            probs = torch.softmax(transition_out["edge_logits"], dim=-1)
            result["transition_probs"] = probs.squeeze(0).cpu().numpy().tolist()

        return result

    # ---- Helpers -----------------------------------------------------

    def _aggregate_outputs(
        self,
        all_outputs: List[Dict[str, Any]],
        sample_id: str,
    ) -> TissueShiftPrediction:
        """Aggregate multiple MC forward passes into a single prediction."""
        pred = TissueShiftPrediction(sample_id=sample_id)

        # Use mean of first output for deterministic keys
        out = all_outputs[0]

        # Tissue state
        if "tissue_state" in out:
            states = torch.stack([o["tissue_state"] for o in all_outputs])
            pred.tissue_state = states.mean(0).squeeze(0).cpu().numpy()

        # Axes
        if "tissue_axes" in out:
            axis_vals = {}
            for key in out["tissue_axes"]:
                vals = torch.stack([o["tissue_axes"][key] for o in all_outputs])
                axis_vals[key] = vals.mean(0).squeeze(0).item()
            pred.tissue_axes = axis_vals

        # Subtype
        if "subtype" in out:
            sub = out["subtype"]
            if "pam50_probs" in sub:
                probs = torch.stack([o["subtype"]["pam50_probs"] for o in all_outputs])
                pred.subtype_pam50_probs = probs.mean(0).squeeze(0).cpu().numpy()
            if "ihc_probs" in sub:
                probs = torch.stack([o["subtype"]["ihc_probs"] for o in all_outputs])
                pred.subtype_ihc_probs = probs.mean(0).squeeze(0).cpu().numpy()
            if "lattice_probs" in sub:
                probs = torch.stack([o["subtype"]["lattice_probs"] for o in all_outputs])
                pred.subtype_lattice_probs = probs.mean(0).squeeze(0).cpu().numpy()
            if "confidence" in sub:
                confs = torch.stack([o["subtype"]["confidence"] for o in all_outputs])
                pred.subtype_confidence = confs.mean().item()

        # Progression
        if "progression" in out:
            prog = out["progression"]
            if "stage_probs" in prog:
                probs = torch.stack([o["progression"]["stage_probs"] for o in all_outputs])
                pred.progression_stage_probs = probs.mean(0).squeeze(0).cpu().numpy()
            if "ordinal_score" in prog:
                scores = torch.stack([o["progression"]["ordinal_score"] for o in all_outputs])
                pred.progression_ordinal_score = scores.mean().item()

        # Drift
        if "drift" in out:
            d = out["drift"]
            if "class_probs" in d:
                probs = torch.stack([o["drift"]["class_probs"] for o in all_outputs])
                pred.drift_class_probs = probs.mean(0).squeeze(0).cpu().numpy()
            if "magnitude" in d:
                mags = torch.stack([o["drift"]["magnitude"] for o in all_outputs])
                pred.drift_magnitude = mags.mean().item()

        # Microenvironment
        if "microenvironment" in out:
            mic = out["microenvironment"]
            if "overall_score" in mic:
                scores = torch.stack([o["microenvironment"]["overall_score"] for o in all_outputs])
                pred.microenv_overall = scores.mean().item()
            if "components" in mic:
                comp_dict = {}
                for k in mic["components"]:
                    vals = torch.stack([o["microenvironment"]["components"][k] for o in all_outputs])
                    comp_dict[k] = vals.mean().item()
                pred.microenv_components = comp_dict

        # Survival
        if "survival" in out:
            surv = out["survival"]
            if "survival_curve" in surv:
                curves = torch.stack([o["survival"]["survival_curve"] for o in all_outputs])
                pred.survival_curve = curves.mean(0).squeeze(0).cpu().numpy()
            if "risk_score" in surv:
                risks = torch.stack([o["survival"]["risk_score"] for o in all_outputs])
                pred.risk_score = risks.mean().item()

        # Molecular bridge
        if "morphology_bridge" in out:
            bridge = out["morphology_bridge"]
            if "predicted_expression" in bridge:
                exprs = torch.stack([o["morphology_bridge"]["predicted_expression"] for o in all_outputs])
                pred.predicted_expression = exprs.mean(0).squeeze(0).cpu().numpy()
            if "predicted_pathways" in bridge:
                paths = torch.stack([o["morphology_bridge"]["predicted_pathways"] for o in all_outputs])
                pred.predicted_pathways = paths.mean(0).squeeze(0).cpu().numpy()

        return pred
