"""
Spatial encoder — cell-graph and neighbourhood tokeniser.

Encodes cell neighbourhoods, immune proximity structure,
duct-to-stroma boundaries, and region-level interaction patterns
using Graph Neural Networks (GATv2 / GraphSAGE / GIN).

Because HTAN and recent spatial atlases show strong correlations
between patient-specific spatial phenotypes and microenvironmental
features, this branch is first-class.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from tissueshift.config import SpatialEncoderConfig

logger = logging.getLogger(__name__)


# ======================================================================
# GNN layers (with fallback if PyG not installed)
# ======================================================================
class _FallbackGNNLayer(nn.Module):
    """Simple message-passing layer when PyG is not available."""

    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.1):
        super().__init__()
        self.linear = nn.Linear(in_dim * 2, out_dim)
        self.norm = nn.LayerNorm(out_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        x : (N, D_in)
        edge_index : (2, E)
        Returns : (N, D_out)
        """
        if edge_index.size(1) == 0:
            return self.dropout(self.norm(self.linear(
                torch.cat([x, torch.zeros_like(x)], dim=-1)
            )))

        src, dst = edge_index[0], edge_index[1]
        # Aggregate neighbour features (mean)
        agg = torch.zeros_like(x)
        count = torch.zeros(x.size(0), 1, device=x.device)
        agg.index_add_(0, dst, x[src])
        count.index_add_(0, dst, torch.ones(src.size(0), 1, device=x.device))
        count = count.clamp(min=1)
        agg = agg / count

        out = self.linear(torch.cat([x, agg], dim=-1))
        return self.dropout(self.norm(F.gelu(out)))


def _build_gnn_layers(
    gnn_type: str,
    node_dim: int,
    hidden_dim: int,
    output_dim: int,
    num_layers: int,
    dropout: float,
) -> nn.ModuleList:
    """Build GNN layer stack, preferring PyG if available."""
    layers = nn.ModuleList()

    try:
        if gnn_type == "gatv2":
            from torch_geometric.nn import GATv2Conv
            for i in range(num_layers):
                in_d = node_dim if i == 0 else hidden_dim
                out_d = output_dim if i == num_layers - 1 else hidden_dim
                layers.append(GATv2Conv(in_d, out_d, heads=1, dropout=dropout))
        elif gnn_type == "graphsage":
            from torch_geometric.nn import SAGEConv
            for i in range(num_layers):
                in_d = node_dim if i == 0 else hidden_dim
                out_d = output_dim if i == num_layers - 1 else hidden_dim
                layers.append(SAGEConv(in_d, out_d))
        elif gnn_type == "gin":
            from torch_geometric.nn import GINConv
            for i in range(num_layers):
                in_d = node_dim if i == 0 else hidden_dim
                out_d = output_dim if i == num_layers - 1 else hidden_dim
                mlp = nn.Sequential(
                    nn.Linear(in_d, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, out_d),
                )
                layers.append(GINConv(mlp))
        else:
            raise ValueError(f"Unknown GNN type: {gnn_type}")

        logger.info("Built %d %s layers via PyG", num_layers, gnn_type)
        return layers

    except ImportError:
        logger.warning("PyG not installed — using fallback GNN layers")
        for i in range(num_layers):
            in_d = node_dim if i == 0 else hidden_dim
            out_d = output_dim if i == num_layers - 1 else hidden_dim
            layers.append(_FallbackGNNLayer(in_d, out_d, dropout))
        return layers


# ======================================================================
# Graph attention pooling
# ======================================================================
class GraphAttentionPool(nn.Module):
    """Attention-based global graph pooling."""

    def __init__(self, in_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(
        self, x: torch.Tensor, batch: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x : (N, D)
        batch : (N,) — graph membership (for batched graphs)

        Returns
        -------
        pooled : (B, D)
        gate_weights : (N,)
        """
        gate_logits = self.gate(x).squeeze(-1)  # (N,)

        if batch is not None:
            # Softmax per graph
            try:
                from torch_geometric.utils import softmax
                gate = softmax(gate_logits, batch)
            except ImportError:
                gate = F.softmax(gate_logits, dim=0)

            # Weighted sum per graph
            num_graphs = batch.max().item() + 1
            pooled = torch.zeros(num_graphs, x.size(1), device=x.device)
            weighted = x * gate.unsqueeze(-1)
            pooled.index_add_(0, batch, weighted)
        else:
            gate = F.softmax(gate_logits, dim=0)
            pooled = (x * gate.unsqueeze(-1)).sum(0, keepdim=True)

        return pooled, gate


# ======================================================================
# Main encoder
# ======================================================================
class SpatialEncoder(nn.Module):
    """
    Full spatial encoder pipeline:

    1. GNN layers process cell-graph nodes.
    2. Attention pooling produces a region-level spatial embedding.
    3. Edge features (distance, interaction type) are optionally used.

    Outputs
    -------
    spatial_embedding : (B, output_dim)
    node_embeddings : (N, hidden_dim)
    attention_weights : (N,)
    """

    def __init__(self, cfg: SpatialEncoderConfig):
        super().__init__()
        self.cfg = cfg

        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(cfg.node_feature_dim, cfg.hidden_dim),
            nn.LayerNorm(cfg.hidden_dim),
            nn.GELU(),
        )

        # GNN layers
        self.gnn_layers = _build_gnn_layers(
            cfg.gnn_type,
            cfg.hidden_dim,
            cfg.hidden_dim,
            cfg.output_dim,
            cfg.num_gnn_layers,
            cfg.dropout,
        )
        self.norms = nn.ModuleList([
            nn.LayerNorm(cfg.hidden_dim if i < cfg.num_gnn_layers - 1 else cfg.output_dim)
            for i in range(cfg.num_gnn_layers)
        ])
        self.dropout = nn.Dropout(cfg.dropout)

        # Pooling
        self.pool = GraphAttentionPool(cfg.output_dim)

        # Final projection
        self.out_proj = nn.Sequential(
            nn.Linear(cfg.output_dim, cfg.output_dim),
            nn.LayerNorm(cfg.output_dim),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: Optional[torch.Tensor] = None,
        pos: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Parameters
        ----------
        x : (N, node_feature_dim) — node features
        edge_index : (2, E) — edge connectivity
        batch : (N,) — graph membership for batched input
        pos : (N, 2) — spatial coordinates (optional, for distance features)
        """
        h = self.input_proj(x)

        # GNN message passing
        for i, (layer, norm) in enumerate(zip(self.gnn_layers, self.norms)):
            h_new = layer(h, edge_index)
            if isinstance(h_new, tuple):
                h_new = h_new[0]
            h_new = norm(h_new)
            if i < len(self.gnn_layers) - 1:
                h_new = F.gelu(h_new)
                h_new = self.dropout(h_new)
                # Residual if dims match
                if h.shape == h_new.shape:
                    h_new = h_new + h
            h = h_new

        # Pool
        pooled, attn_weights = self.pool(h, batch)
        spatial_embedding = self.out_proj(pooled)

        return {
            "spatial_embedding": spatial_embedding,
            "node_embeddings": h,
            "attention_weights": attn_weights,
        }

    def forward_from_dict(self, graph_dict: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        """Convenience: forward from a graph dict (as produced by CellGraphBuilder)."""
        device = next(self.parameters()).device
        x = graph_dict["x"].to(device)
        edge_index = graph_dict.get("edge_index", torch.zeros(2, 0, dtype=torch.long)).to(device)
        batch = graph_dict.get("batch", None)
        pos = graph_dict.get("pos", None)
        if batch is not None:
            batch = batch.to(device)
        if pos is not None:
            pos = pos.to(device)
        return self.forward(x, edge_index, batch, pos)
