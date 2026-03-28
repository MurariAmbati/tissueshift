"""Interpretability and attention visualization tools for TissueShift.

Provides attention heatmap overlay on WSIs, latent-space traversal,
tissue-axis attribution, and gradient-based saliency computation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Attention heatmap on WSI tiles
# ===================================================================

class AttentionVisualizer:
    """Visualize MIL attention weights overlaid on tile locations.

    Given attention weights from the pathology encoder's gated attention
    pooling and tile coordinate metadata, produces heatmaps at the WSI
    level.
    """

    @staticmethod
    def extract_attention_weights(
        model: Any,
        tile_embeddings: torch.Tensor,
    ) -> np.ndarray:
        """Extract attention weights from the pathology encoder.

        Parameters
        ----------
        model : TissueShiftModel
            The full model.
        tile_embeddings : Tensor of shape (1, N_tiles, D)
            Pre-computed tile features.

        Returns
        -------
        np.ndarray of shape (N_tiles,)
            Normalized attention weights.
        """
        model.eval()
        with torch.no_grad():
            encoder = model.pathology_encoder
            V = encoder.attention_V(tile_embeddings)
            U = encoder.attention_U(tile_embeddings)
            logits = encoder.attention_w(V * torch.tanh(U))  # (1, N, 1)
            weights = F.softmax(logits.squeeze(-1), dim=-1)  # (1, N)
        return weights.squeeze(0).cpu().numpy()

    @staticmethod
    def create_tile_heatmap(
        attention_weights: np.ndarray,
        tile_coords: np.ndarray,
        wsi_dimensions: Tuple[int, int],
        tile_size: int = 256,
        thumbnail_size: Tuple[int, int] = (1024, 1024),
    ) -> np.ndarray:
        """Create an attention heatmap image from tile coordinates and weights.

        Parameters
        ----------
        attention_weights : array of shape (N_tiles,)
        tile_coords : array of shape (N_tiles, 2) — (x, y) in WSI coordinates
        wsi_dimensions : (width, height) of the original WSI
        tile_size : size of each tile in WSI coordinates
        thumbnail_size : output heatmap image size

        Returns
        -------
        np.ndarray of shape (H, W, 3) — RGB heatmap image
        """
        w_wsi, h_wsi = wsi_dimensions
        h_thumb, w_thumb = thumbnail_size

        # Scale factors
        scale_x = w_thumb / w_wsi
        scale_y = h_thumb / h_wsi
        tile_w = max(1, int(tile_size * scale_x))
        tile_h = max(1, int(tile_size * scale_y))

        # Accumulate attention in thumbnail space
        heatmap = np.zeros((h_thumb, w_thumb), dtype=np.float32)
        counts = np.zeros_like(heatmap)

        for idx, (x, y) in enumerate(tile_coords):
            tx = int(x * scale_x)
            ty = int(y * scale_y)
            y1, y2 = max(0, ty), min(h_thumb, ty + tile_h)
            x1, x2 = max(0, tx), min(w_thumb, tx + tile_w)
            heatmap[y1:y2, x1:x2] += attention_weights[idx]
            counts[y1:y2, x1:x2] += 1.0

        # Average overlapping tiles
        mask = counts > 0
        heatmap[mask] /= counts[mask]

        # Normalize to [0, 1]
        if heatmap.max() > heatmap.min():
            heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min())

        # Apply colormap (jet-like)
        rgb = AttentionVisualizer._apply_jet_colormap(heatmap)
        return rgb

    @staticmethod
    def overlay_heatmap(
        thumbnail: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = 0.5,
    ) -> np.ndarray:
        """Overlay a heatmap on a tissue thumbnail.

        Parameters
        ----------
        thumbnail : array (H, W, 3), uint8
        heatmap : array (H, W, 3), uint8
        alpha : blending factor

        Returns
        -------
        np.ndarray (H, W, 3), uint8
        """
        from PIL import Image
        thumb_resized = np.array(
            Image.fromarray(thumbnail).resize(
                (heatmap.shape[1], heatmap.shape[0])
            )
        )
        blended = (alpha * heatmap.astype(np.float32) +
                    (1 - alpha) * thumb_resized.astype(np.float32))
        return np.clip(blended, 0, 255).astype(np.uint8)

    @staticmethod
    def _apply_jet_colormap(heatmap: np.ndarray) -> np.ndarray:
        """Simple jet colormap without matplotlib dependency."""
        h = heatmap
        r = np.clip(1.5 - np.abs(4 * h - 3), 0, 1)
        g = np.clip(1.5 - np.abs(4 * h - 2), 0, 1)
        b = np.clip(1.5 - np.abs(4 * h - 1), 0, 1)
        rgb = np.stack([r, g, b], axis=-1)
        return (rgb * 255).astype(np.uint8)


# ===================================================================
# Gradient-based saliency / attribution
# ===================================================================

class GradientAttribution:
    """Gradient-based attribution methods for TissueShift predictions.

    Supports vanilla saliency, input × gradient, and integrated gradients.
    """

    def __init__(self, model: Any) -> None:
        self.model = model

    def vanilla_saliency(
        self,
        batch: Dict[str, torch.Tensor],
        target_key: str = "subtype",
        target_class: int = 0,
    ) -> Dict[str, np.ndarray]:
        """Compute vanilla gradient saliency for each input modality.

        Parameters
        ----------
        batch : dict
            Model input batch (each value requires grad enabled).
        target_key : str
            Which output head to attribute to.
        target_class : int
            Class index for classification targets.

        Returns
        -------
        dict mapping input keys to gradient magnitude arrays.
        """
        self.model.eval()
        for v in batch.values():
            if isinstance(v, torch.Tensor) and v.is_floating_point():
                v.requires_grad_(True)

        outputs = self.model(batch)

        # Extract target logit
        target_tensor = self._extract_target(outputs, target_key, target_class)
        target_tensor.backward()

        saliency = {}
        for key, v in batch.items():
            if isinstance(v, torch.Tensor) and v.grad is not None:
                grad = v.grad.abs()
                saliency[key] = grad.cpu().numpy()

        return saliency

    def input_x_gradient(
        self,
        batch: Dict[str, torch.Tensor],
        target_key: str = "subtype",
        target_class: int = 0,
    ) -> Dict[str, np.ndarray]:
        """Input × Gradient attribution."""
        self.model.eval()
        for v in batch.values():
            if isinstance(v, torch.Tensor) and v.is_floating_point():
                v.requires_grad_(True)

        outputs = self.model(batch)
        target_tensor = self._extract_target(outputs, target_key, target_class)
        target_tensor.backward()

        attributions = {}
        for key, v in batch.items():
            if isinstance(v, torch.Tensor) and v.grad is not None:
                attr = (v * v.grad).abs()
                attributions[key] = attr.cpu().numpy()

        return attributions

    def integrated_gradients(
        self,
        batch: Dict[str, torch.Tensor],
        target_key: str = "subtype",
        target_class: int = 0,
        n_steps: int = 50,
    ) -> Dict[str, np.ndarray]:
        """Integrated Gradients attribution (Sundararajan et al., 2017).

        Uses a zero baseline and linearly interpolates in ``n_steps``.
        """
        self.model.eval()

        # Accumulate gradients over interpolation steps
        accumulated = {k: torch.zeros_like(v)
                       for k, v in batch.items()
                       if isinstance(v, torch.Tensor) and v.is_floating_point()}

        for step in range(1, n_steps + 1):
            alpha = step / n_steps
            interp_batch = {}
            for k, v in batch.items():
                if isinstance(v, torch.Tensor) and v.is_floating_point():
                    interp = (alpha * v).detach().requires_grad_(True)
                    interp_batch[k] = interp
                else:
                    interp_batch[k] = v

            outputs = self.model(interp_batch)
            target_tensor = self._extract_target(outputs, target_key, target_class)
            target_tensor.backward()

            for k, v in interp_batch.items():
                if isinstance(v, torch.Tensor) and v.grad is not None:
                    accumulated[k] += v.grad.detach()

            self.model.zero_grad()

        attributions = {}
        for k in accumulated:
            avg_grad = accumulated[k] / n_steps
            ig = (batch[k].detach() * avg_grad).abs()
            attributions[k] = ig.cpu().numpy()

        return attributions

    def _extract_target(
        self, outputs: Dict[str, Any], target_key: str, target_class: int,
    ) -> torch.Tensor:
        """Navigate the output dict to find the target scalar."""
        out = outputs.get(target_key, outputs)
        if isinstance(out, dict):
            # Try common sub-keys
            for sub_key in ("lattice_logits", "pam50_logits", "logits", "class_logits"):
                if sub_key in out:
                    return out[sub_key][0, target_class]
            # Use first tensor found
            for v in out.values():
                if isinstance(v, torch.Tensor) and v.dim() >= 2:
                    return v[0, target_class]
        if isinstance(out, torch.Tensor):
            if out.dim() >= 2:
                return out[0, target_class]
            return out.sum()
        raise ValueError(f"Cannot extract target from output key '{target_key}'")


# ===================================================================
# Latent-space traversal
# ===================================================================

class LatentTraversal:
    """Traverse the tissue-state latent space along interpretable axes.

    Useful for understanding what each axis encodes by observing how
    predictions change as a single axis is varied.
    """

    def __init__(self, model: Any) -> None:
        self.model = model

    @torch.no_grad()
    def traverse_axis(
        self,
        base_state: torch.Tensor,
        axis_idx: int,
        n_steps: int = 11,
        range_sigma: float = 3.0,
    ) -> List[Dict[str, Any]]:
        """Sweep a single latent axis and record predictions.

        Parameters
        ----------
        base_state : Tensor of shape (latent_dim,)
            Starting tissue-state vector.
        axis_idx : int
            Which latent dimension to vary.
        n_steps : int
            Number of interpolation points.
        range_sigma : float
            Range in standard deviations from the mean.

        Returns
        -------
        list of dicts with 'axis_value' and prediction outputs.
        """
        self.model.eval()
        device = next(self.model.parameters()).device
        base = base_state.clone().to(device)

        values = torch.linspace(-range_sigma, range_sigma, n_steps)
        results = []

        for val in values:
            z = base.clone().unsqueeze(0)
            z[0, axis_idx] = val.item()
            outputs = self._predict_from_latent(z)
            outputs["axis_value"] = val.item()
            results.append(outputs)

        return results

    @torch.no_grad()
    def interpolate(
        self,
        state_a: torch.Tensor,
        state_b: torch.Tensor,
        n_steps: int = 10,
    ) -> List[Dict[str, Any]]:
        """Linear interpolation between two tissue states.

        Returns predictions at each interpolation point.
        """
        self.model.eval()
        device = next(self.model.parameters()).device
        a = state_a.to(device).unsqueeze(0)
        b = state_b.to(device).unsqueeze(0)

        results = []
        for alpha in torch.linspace(0, 1, n_steps):
            z = (1 - alpha) * a + alpha * b
            outputs = self._predict_from_latent(z)
            outputs["alpha"] = alpha.item()
            results.append(outputs)

        return results

    def _predict_from_latent(self, z: torch.Tensor) -> Dict[str, Any]:
        """Run prediction heads from a latent vector."""
        outputs = {}

        # Subtype
        if hasattr(self.model, "subtype_head"):
            sub = self.model.subtype_head(z)
            if isinstance(sub, dict) and "lattice_probs" in sub:
                outputs["subtype_probs"] = sub["lattice_probs"].squeeze(0).cpu().numpy().tolist()

        # Progression
        if hasattr(self.model, "progression_head"):
            prog = self.model.progression_head(z)
            if isinstance(prog, dict) and "ordinal_score" in prog:
                outputs["progression_score"] = prog["ordinal_score"].item()

        # Microenvironment
        if hasattr(self.model, "microenvironment_head"):
            mic = self.model.microenvironment_head(z)
            if isinstance(mic, dict) and "overall_score" in mic:
                outputs["microenv_score"] = mic["overall_score"].item()

        return outputs


# ===================================================================
# Tissue-axis attribution / importance ranking
# ===================================================================

class AxisAttribution:
    """Rank the importance of each tissue axis for a given prediction.

    Uses leave-one-out perturbation: zero each axis in turn and measure
    the change in the target prediction.
    """

    def __init__(self, model: Any) -> None:
        self.model = model

    @torch.no_grad()
    def rank_axes(
        self,
        tissue_state: torch.Tensor,
        target_key: str = "subtype",
        axis_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Rank tissue axes by prediction impact.

        Parameters
        ----------
        tissue_state : Tensor (latent_dim,)
        target_key : str
            Output to monitor.
        axis_names : list of str, optional
            Human-readable names for each axis.

        Returns
        -------
        list of dicts sorted by descending importance.
        """
        self.model.eval()
        device = next(self.model.parameters()).device
        z = tissue_state.to(device).unsqueeze(0)

        # Baseline prediction
        base_out = self._get_prediction_vector(z, target_key)

        n_axes = z.shape[1]
        importances = []

        for i in range(n_axes):
            z_perturbed = z.clone()
            z_perturbed[0, i] = 0.0
            perturbed_out = self._get_prediction_vector(z_perturbed, target_key)
            diff = np.abs(base_out - perturbed_out).sum()
            name = axis_names[i] if axis_names and i < len(axis_names) else f"axis_{i}"
            importances.append({
                "axis": name,
                "axis_idx": i,
                "importance": float(diff),
                "base_value": float(z[0, i].cpu()),
            })

        importances.sort(key=lambda x: x["importance"], reverse=True)
        return importances

    def _get_prediction_vector(self, z: torch.Tensor, target_key: str) -> np.ndarray:
        """Get a prediction vector from a latent state."""
        if hasattr(self.model, "subtype_head") and target_key == "subtype":
            out = self.model.subtype_head(z)
            if isinstance(out, dict) and "lattice_probs" in out:
                return out["lattice_probs"].squeeze(0).cpu().numpy()
        if hasattr(self.model, "progression_head") and target_key == "progression":
            out = self.model.progression_head(z)
            if isinstance(out, dict) and "stage_probs" in out:
                return out["stage_probs"].squeeze(0).cpu().numpy()
        # Fallback: return latent itself
        return z.squeeze(0).cpu().numpy()
