"""
Molecular encoder — RNA, protein, CNV, and pathway tokeniser.

Encodes subtype-relevant gene signatures, pathway activity scores,
protein abundance, phospho-signalling summaries, copy-number burden,
and marker-state tokens into a unified molecular embedding.

Architecture: Transformer over gene/pathway tokens with cross-attention
between modality streams.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from tissueshift.config import MolecularEncoderConfig

logger = logging.getLogger(__name__)


# ======================================================================
# Positional encoding for gene tokens
# ======================================================================
class SinusoidalPositionEncoding(nn.Module):
    """Standard sinusoidal positional encoding."""

    def __init__(self, d_model: int, max_len: int = 21000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, D)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


# ======================================================================
# Single-modality gene/protein stream
# ======================================================================
class GeneExpressionStream(nn.Module):
    """Encodes a gene-expression or protein-abundance vector into tokens."""

    def __init__(self, vocab_size: int, embed_dim: int, dropout: float = 0.1):
        super().__init__()
        # Gene-level projection: each gene value → embed
        self.gene_proj = nn.Linear(1, embed_dim)
        self.pos_enc = SinusoidalPositionEncoding(embed_dim, max_len=vocab_size + 100)
        self.norm = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x : (B, G) — gene expression vector, G genes.

        Returns
        -------
        tokens : (B, G, D) — per-gene token embeddings.
        """
        B, G = x.shape
        tokens = self.gene_proj(x.unsqueeze(-1))  # (B, G, D)
        tokens = self.pos_enc(tokens)
        tokens = self.norm(tokens)
        return self.dropout(tokens)


class PathwayStream(nn.Module):
    """Encodes pathway activity scores into tokens."""

    def __init__(self, num_pathways: int, embed_dim: int, dropout: float = 0.1):
        super().__init__()
        self.pathway_embed = nn.Linear(1, embed_dim)
        self.pathway_type_embed = nn.Embedding(num_pathways, embed_dim)
        self.norm = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, pathway_scores: torch.Tensor) -> torch.Tensor:
        """
        pathway_scores : (B, P) — activity scores for P pathways.
        Returns : (B, P, D) tokens.
        """
        B, P = pathway_scores.shape
        val_embed = self.pathway_embed(pathway_scores.unsqueeze(-1))  # (B, P, D)
        type_idx = torch.arange(P, device=pathway_scores.device).unsqueeze(0).expand(B, -1)
        type_embed = self.pathway_type_embed(type_idx)
        tokens = self.norm(val_embed + type_embed)
        return self.dropout(tokens)


class CNVStream(nn.Module):
    """Encodes copy-number variation / burden."""

    def __init__(self, input_dim: int, embed_dim: int, dropout: float = 0.1):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(input_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, cnv: torch.Tensor) -> torch.Tensor:
        """
        cnv : (B, G_cnv) — per-gene CNV values.
        Returns : (B, 1, D) — single CNV summary token.
        """
        return self.proj(cnv).unsqueeze(1)


# ======================================================================
# Cross-modality Transformer
# ======================================================================
class MolecularTransformer(nn.Module):
    """
    Transformer encoder that attends over concatenated gene, pathway,
    protein, and CNV tokens to produce a fused molecular embedding.
    """

    def __init__(
        self,
        d_model: int,
        nhead: int = 8,
        num_layers: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        """
        tokens : (B, T, D) — concatenated multi-modal tokens.
        Returns : (B, D) — [CLS] output.
        """
        B = tokens.size(0)
        cls = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls, tokens], dim=1)  # (B, T+1, D)
        x = self.encoder(x)
        return x[:, 0]  # [CLS] token


# ======================================================================
# Main encoder
# ======================================================================
class MolecularEncoder(nn.Module):
    """
    Full molecular encoder.

    Streams:
      - Gene expression (RNA) → gene tokens
      - Protein abundance → protein tokens (reuses GeneExpressionStream)
      - Pathway activity → pathway tokens
      - CNV burden → CNV summary token
      - Marker-state tokens (ER, PR, HER2, Ki-67) → discrete tokens

    Fusion via Transformer → fused molecular embedding.

    Outputs
    -------
    molecular_embedding : (B, fused_dim)
    gene_tokens : (B, G, gene_embed_dim)
    pathway_tokens : (B, P, pathway_embed_dim)
    """

    # Known markers encoded as discrete tokens
    MARKER_NAMES = ("ER", "PR", "HER2", "Ki67")
    MARKER_STATES = ("negative", "positive", "equivocal", "unknown")

    def __init__(self, cfg: MolecularEncoderConfig):
        super().__init__()
        self.cfg = cfg

        # Streams
        self.rna_stream = GeneExpressionStream(cfg.gene_vocab_size, cfg.gene_embed_dim, cfg.dropout)
        self.protein_stream = GeneExpressionStream(cfg.gene_vocab_size, cfg.protein_embed_dim, cfg.dropout)
        self.pathway_stream = PathwayStream(cfg.num_pathways, cfg.pathway_embed_dim, cfg.dropout)
        self.cnv_stream = CNVStream(cfg.gene_vocab_size, cfg.cnv_embed_dim, cfg.dropout)

        # Marker-state embedding
        self.marker_embed = nn.Embedding(
            len(self.MARKER_NAMES) * len(self.MARKER_STATES),
            cfg.gene_embed_dim,
        )

        # Project all streams to a common dim before Transformer
        self.stream_dim = cfg.gene_embed_dim  # common token dim
        self.rna_proj = nn.Linear(cfg.gene_embed_dim, self.stream_dim) if cfg.gene_embed_dim != self.stream_dim else nn.Identity()
        self.protein_proj = nn.Linear(cfg.protein_embed_dim, self.stream_dim) if cfg.protein_embed_dim != self.stream_dim else nn.Identity()
        self.pathway_proj = nn.Linear(cfg.pathway_embed_dim, self.stream_dim) if cfg.pathway_embed_dim != self.stream_dim else nn.Identity()
        self.cnv_proj = nn.Linear(cfg.cnv_embed_dim, self.stream_dim) if cfg.cnv_embed_dim != self.stream_dim else nn.Identity()

        # Cross-modal Transformer
        self.transformer = MolecularTransformer(
            d_model=self.stream_dim,
            nhead=cfg.num_attention_heads,
            num_layers=cfg.num_transformer_layers,
            dropout=cfg.dropout,
        )

        # Final projection
        self.out_proj = nn.Sequential(
            nn.Linear(self.stream_dim, cfg.fused_dim),
            nn.LayerNorm(cfg.fused_dim),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
        )

    def _encode_markers(self, marker_states: Dict[str, str]) -> torch.Tensor:
        """
        Encode IHC marker states as embedding tokens.

        Parameters
        ----------
        marker_states : dict  e.g. {"ER": "positive", "PR": "positive", ...}

        Returns
        -------
        tokens : (1, num_markers, stream_dim)
        """
        indices = []
        for i, name in enumerate(self.MARKER_NAMES):
            state = marker_states.get(name, "unknown").lower()
            j = self.MARKER_STATES.index(state) if state in self.MARKER_STATES else 3
            indices.append(i * len(self.MARKER_STATES) + j)
        idx_tensor = torch.tensor(indices, dtype=torch.long, device=next(self.parameters()).device)
        return self.marker_embed(idx_tensor).unsqueeze(0)  # (1, M, D)

    def forward(
        self,
        rna: Optional[torch.Tensor] = None,
        proteomics: Optional[torch.Tensor] = None,
        pathway_scores: Optional[torch.Tensor] = None,
        cnv: Optional[torch.Tensor] = None,
        marker_states: Optional[Dict[str, str]] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass — any subset of modalities may be provided.

        Returns dict with molecular_embedding, gene_tokens, pathway_tokens.
        """
        device = next(self.parameters()).device
        token_lists = []

        # RNA tokens (subsample to top-K genes if needed for speed)
        gene_tokens = None
        if rna is not None:
            rna = rna.to(device)
            if rna.dim() == 1:
                rna = rna.unsqueeze(0)
            # Subsample to manageable size for transformer
            G = min(rna.shape[1], 2000)
            rna_top = rna[:, :G]
            gene_tokens = self.rna_stream(rna_top)
            token_lists.append(self.rna_proj(gene_tokens))

        # Protein tokens
        if proteomics is not None:
            proteomics = proteomics.to(device)
            if proteomics.dim() == 1:
                proteomics = proteomics.unsqueeze(0)
            G = min(proteomics.shape[1], 2000)
            prot_tokens = self.protein_stream(proteomics[:, :G])
            token_lists.append(self.protein_proj(prot_tokens))

        # Pathway tokens
        pathway_tokens = None
        if pathway_scores is not None:
            pathway_scores = pathway_scores.to(device)
            if pathway_scores.dim() == 1:
                pathway_scores = pathway_scores.unsqueeze(0)
            pathway_tokens = self.pathway_stream(pathway_scores)
            token_lists.append(self.pathway_proj(pathway_tokens))

        # CNV token
        if cnv is not None:
            cnv = cnv.to(device)
            if cnv.dim() == 1:
                cnv = cnv.unsqueeze(0)
            cnv_tok = self.cnv_stream(cnv)
            token_lists.append(self.cnv_proj(cnv_tok))

        # Marker tokens
        if marker_states is not None:
            marker_tok = self._encode_markers(marker_states)
            token_lists.append(marker_tok.expand(token_lists[0].size(0) if token_lists else 1, -1, -1))

        # Handle empty input
        if not token_lists:
            B = 1
            dummy = torch.zeros(B, 1, self.stream_dim, device=device)
            token_lists.append(dummy)

        # Concatenate all tokens
        all_tokens = torch.cat(token_lists, dim=1)  # (B, T_total, D)

        # Transformer fusion
        fused = self.transformer(all_tokens)  # (B, D)
        molecular_embedding = self.out_proj(fused)  # (B, fused_dim)

        output = {"molecular_embedding": molecular_embedding}
        if gene_tokens is not None:
            output["gene_tokens"] = gene_tokens
        if pathway_tokens is not None:
            output["pathway_tokens"] = pathway_tokens

        return output
