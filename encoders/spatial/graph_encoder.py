"""Spatial encoder stub (full implementation in Phase 11 with HTAN integration)."""

from __future__ import annotations

import torch
import torch.nn as nn


class SpatialEncoderStub(nn.Module):
    """Stub spatial encoder that returns a learnable default embedding.

    Full implementation (Phase 11) will use PyTorch Geometric to build:
    - Cell graph encoder (GIN/GAT) from spatial coordinates
    - Neighborhood composition encoder
    - Integration with HTAN spatial transcriptomics data
    """

    def __init__(self, output_dim: int = 128):
        super().__init__()
        self.output_dim = output_dim
        self.default_embedding = nn.Parameter(torch.randn(output_dim) * 0.02)

    def forward(self, batch_size: int = 1, **kwargs) -> torch.Tensor:
        """Return learnable default spatial embedding.

        Args:
            batch_size: Number of samples in batch

        Returns:
            z_spat: (B, output_dim) spatial embedding (same learned vector for all)
        """
        return self.default_embedding.unsqueeze(0).expand(batch_size, -1)


class GraphSpatialEncoder(nn.Module):
    """Full graph-based spatial encoder (Phase 11 implementation).

    Uses PyTorch Geometric to encode cell neighborhoods and
    spatial interaction patterns.

    Architecture:
    - Nodes = cells or patches
    - Edges = k-nearest spatial neighbors
    - 3-layer GIN (Graph Isomorphism Network) or GAT
    - Global attention pooling for graph-level embedding
    """

    def __init__(
        self,
        node_dim: int = 64,
        hidden_dim: int = 128,
        output_dim: int = 128,
        n_layers: int = 3,
        k_neighbors: int = 8,
    ):
        super().__init__()
        self.output_dim = output_dim
        self.k_neighbors = k_neighbors

        # Placeholder — will be implemented with torch_geometric
        self.stub = SpatialEncoderStub(output_dim)

        # TODO (Phase 11): Replace with actual GIN/GAT implementation
        # from torch_geometric.nn import GINConv, global_add_pool
        # self.convs = nn.ModuleList([...])
        # self.pool = global_add_pool

    def forward(self, batch_size: int = 1, **kwargs) -> torch.Tensor:
        """Encode spatial graph structure.

        Phase 11 will accept:
        - node_features: (total_nodes, node_dim) cell/patch features
        - edge_index: (2, n_edges) graph connectivity
        - batch: (total_nodes,) batch assignment

        Returns:
            z_spat: (B, output_dim) spatial embedding
        """
        return self.stub(batch_size)


def build_spatial_encoder(method: str = "stub", **kwargs) -> nn.Module:
    """Factory for spatial encoders."""
    if method == "stub":
        return SpatialEncoderStub(**kwargs)
    elif method == "graph":
        return GraphSpatialEncoder(**kwargs)
    else:
        raise ValueError(f"Unknown spatial encoder: {method}")
