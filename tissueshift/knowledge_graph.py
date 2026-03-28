"""Biological knowledge graph for mechanistic reasoning.

Integrates curated biological knowledge (gene-pathway-drug-phenotype
relationships) into the latent tissue-state model.  This bridges the
gap between black-box deep learning and interpretable biology:

1. **Knowledge Graph Construction** — builds a heterogeneous graph
   from KEGG, Reactome, DrugBank, Gene Ontology, and MSigDB.
2. **Graph Neural Reasoning** — message-passing on the KG to produce
   biology-aware embeddings for genes, pathways, and drugs.
3. **Knowledge-Guided Regularisation** — soft constraints that
   encourage the latent space to respect known biology.
4. **Drug-Target Interaction** — predicts drug sensitivity from
   tissue state + molecular profile using the KG structure.
5. **Pathway Activity Inference** — infers pathway activity scores
   from gene expression guided by KG topology.

References
----------
Kanehisa et al., "KEGG: new perspectives on genomes, pathways, diseases
    and drugs", NAR 2017.
Wishart et al., "DrugBank 5.0", NAR 2018.
Zitnik et al., "Modeling polypharmacy side effects with GCNs", Bioinformatics 2018.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class KnowledgeGraphConfig:
    """Parameters for the biological knowledge graph module."""

    # Node types in the heterogeneous graph
    node_types: Tuple[str, ...] = ("gene", "pathway", "drug", "phenotype", "go_term")

    # Edge types (relation types)
    edge_types: Tuple[str, ...] = (
        "gene_in_pathway",
        "gene_interacts_gene",
        "drug_targets_gene",
        "gene_associated_phenotype",
        "pathway_related_pathway",
        "go_annotates_gene",
        "drug_treats_phenotype",
    )

    # Embedding dimensions
    node_embed_dim: int = 128
    relation_embed_dim: int = 64

    # GNN parameters
    gnn_hidden_dim: int = 256
    gnn_num_layers: int = 3
    gnn_dropout: float = 0.1
    gnn_type: str = "rgcn"  # rgcn | rgat | compgcn

    # Knowledge-guided regularisation
    pathway_coherence_weight: float = 0.1
    gene_coexpression_weight: float = 0.05

    # Drug sensitivity prediction
    drug_sensitivity_hidden: int = 128

    # Curated gene sets
    num_hallmark_gene_sets: int = 50
    num_kegg_pathways: int = 186
    breast_cancer_genes: int = 500


# ===================================================================
# Heterogeneous Graph Store
# ===================================================================

class BiologicalKnowledgeGraph:
    """In-memory heterogeneous biological knowledge graph.

    Stores nodes of different types (genes, pathways, drugs, phenotypes)
    and typed edges.  Supports efficient lookup and subgraph extraction.
    """

    def __init__(self, cfg: KnowledgeGraphConfig):
        self.cfg = cfg
        self.nodes: Dict[str, Dict[str, int]] = {nt: {} for nt in cfg.node_types}
        self.node_features: Dict[str, Dict[int, np.ndarray]] = {nt: {} for nt in cfg.node_types}
        self.edges: Dict[str, List[Tuple[int, int]]] = {et: [] for et in cfg.edge_types}
        self.edge_attrs: Dict[str, List[Dict[str, Any]]] = {et: [] for et in cfg.edge_types}

    def add_node(
        self, node_type: str, name: str, features: Optional[np.ndarray] = None
    ) -> int:
        """Add a node to the graph. Returns the node index."""
        if name in self.nodes[node_type]:
            return self.nodes[node_type][name]
        idx = len(self.nodes[node_type])
        self.nodes[node_type][name] = idx
        if features is not None:
            self.node_features[node_type][idx] = features
        return idx

    def add_edge(
        self,
        edge_type: str,
        source_idx: int,
        target_idx: int,
        attrs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a typed edge."""
        self.edges[edge_type].append((source_idx, target_idx))
        self.edge_attrs[edge_type].append(attrs or {})

    def num_nodes(self, node_type: str) -> int:
        return len(self.nodes[node_type])

    def get_edge_index(self, edge_type: str) -> torch.LongTensor:
        """Return (2, E) edge index for the given edge type."""
        if not self.edges[edge_type]:
            return torch.zeros(2, 0, dtype=torch.long)
        src, dst = zip(*self.edges[edge_type])
        return torch.tensor([list(src), list(dst)], dtype=torch.long)

    def subgraph_around_genes(
        self, gene_names: List[str], hops: int = 2
    ) -> Dict[str, Any]:
        """Extract a local subgraph around given genes.

        Performs BFS up to *hops* distance, collecting all reachable
        nodes and edges across all relation types.
        """
        visited_genes: Set[int] = set()
        frontier: Set[int] = set()

        for g in gene_names:
            if g in self.nodes["gene"]:
                idx = self.nodes["gene"][g]
                visited_genes.add(idx)
                frontier.add(idx)

        # Simple BFS across gene-gene edges
        gene_edges = self.edges.get("gene_interacts_gene", [])
        for _ in range(hops):
            next_frontier: Set[int] = set()
            for src, dst in gene_edges:
                if src in frontier and dst not in visited_genes:
                    next_frontier.add(dst)
                    visited_genes.add(dst)
                if dst in frontier and src not in visited_genes:
                    next_frontier.add(src)
                    visited_genes.add(src)
            frontier = next_frontier

        # Collect connected pathways, drugs, phenotypes
        connected_pathways: Set[int] = set()
        for src, dst in self.edges.get("gene_in_pathway", []):
            if src in visited_genes:
                connected_pathways.add(dst)

        connected_drugs: Set[int] = set()
        for src, dst in self.edges.get("drug_targets_gene", []):
            if dst in visited_genes:
                connected_drugs.add(src)

        return {
            "gene_indices": sorted(visited_genes),
            "pathway_indices": sorted(connected_pathways),
            "drug_indices": sorted(connected_drugs),
            "n_genes": len(visited_genes),
            "n_pathways": len(connected_pathways),
            "n_drugs": len(connected_drugs),
        }

    def save(self, path: str) -> None:
        """Serialise graph to JSON."""
        data = {
            "nodes": {nt: list(nmap.keys()) for nt, nmap in self.nodes.items()},
            "edges": {et: edges for et, edges in self.edges.items()},
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_json(cls, path: str, cfg: Optional[KnowledgeGraphConfig] = None) -> "BiologicalKnowledgeGraph":
        """Load from JSON."""
        if cfg is None:
            cfg = KnowledgeGraphConfig()
        kg = cls(cfg)
        with open(path) as f:
            data = json.load(f)
        for nt, names in data.get("nodes", {}).items():
            if nt in kg.nodes:
                for name in names:
                    kg.add_node(nt, name)
        for et, edges in data.get("edges", {}).items():
            if et in kg.edges:
                for src, dst in edges:
                    kg.add_edge(et, src, dst)
        return kg


# ===================================================================
# Knowledge-Graph Builder from Curated Sources
# ===================================================================

class KnowledgeGraphBuilder:
    """Build the biological KG from standard bioinformatics resources.

    Constructs a unified heterogeneous graph from:
    * KEGG pathway membership
    * MSigDB Hallmark gene sets
    * STRING protein-protein interactions
    * DrugBank drug-target links
    * COSMIC cancer gene census
    """

    def __init__(self, cfg: KnowledgeGraphConfig):
        self.cfg = cfg
        self.kg = BiologicalKnowledgeGraph(cfg)

    def add_kegg_pathways(self, pathway_file: str) -> int:
        """Load KEGG pathway → gene membership.

        Expected format: TSV with columns [pathway_id, pathway_name, gene_symbol].
        """
        count = 0
        try:
            import pandas as pd
            df = pd.read_csv(pathway_file, sep="\t")
            for _, row in df.iterrows():
                pw_idx = self.kg.add_node("pathway", str(row.iloc[1]))
                g_idx = self.kg.add_node("gene", str(row.iloc[2]))
                self.kg.add_edge("gene_in_pathway", g_idx, pw_idx)
                count += 1
        except Exception as e:
            logger.warning("Failed to load KEGG pathways: %s", e)
        logger.info("Added %d gene-pathway edges from KEGG", count)
        return count

    def add_string_interactions(
        self, interactions_file: str, min_score: int = 700
    ) -> int:
        """Load STRING protein-protein interactions.

        Expected: TSV with [protein1, protein2, combined_score].
        """
        count = 0
        try:
            import pandas as pd
            df = pd.read_csv(interactions_file, sep="\t")
            for _, row in df.iterrows():
                if int(row.iloc[2]) >= min_score:
                    g1 = self.kg.add_node("gene", str(row.iloc[0]))
                    g2 = self.kg.add_node("gene", str(row.iloc[1]))
                    self.kg.add_edge("gene_interacts_gene", g1, g2)
                    self.kg.add_edge("gene_interacts_gene", g2, g1)
                    count += 1
        except Exception as e:
            logger.warning("Failed to load STRING: %s", e)
        logger.info("Added %d PPI edges from STRING", count)
        return count

    def add_drugbank_targets(self, drugbank_file: str) -> int:
        """Load DrugBank drug-target interactions.

        Expected: TSV with [drug_name, gene_symbol, action].
        """
        count = 0
        try:
            import pandas as pd
            df = pd.read_csv(drugbank_file, sep="\t")
            for _, row in df.iterrows():
                d_idx = self.kg.add_node("drug", str(row.iloc[0]))
                g_idx = self.kg.add_node("gene", str(row.iloc[1]))
                action = str(row.iloc[2]) if len(row) > 2 else "unknown"
                self.kg.add_edge("drug_targets_gene", d_idx, g_idx, {"action": action})
                count += 1
        except Exception as e:
            logger.warning("Failed to load DrugBank: %s", e)
        logger.info("Added %d drug-target edges from DrugBank", count)
        return count

    def add_breast_cancer_genes(self) -> None:
        """Add known breast cancer driver genes from literature."""
        drivers = [
            "TP53", "PIK3CA", "GATA3", "CDH1", "MAP3K1", "MLL3",
            "PTEN", "AKT1", "CBFB", "TBX3", "RUNX1", "FOXA1",
            "ERBB2", "ESR1", "PGR", "MKI67", "BRCA1", "BRCA2",
            "ATM", "CHEK2", "PALB2", "CDK4", "CDK6", "CCND1",
            "RB1", "FGFR1", "MYC", "NOTCH1", "NF1", "SF3B1",
        ]
        for gene in drivers:
            self.kg.add_node("gene", gene)
            self.kg.add_node("phenotype", "breast_cancer")
            g_idx = self.kg.nodes["gene"][gene]
            p_idx = self.kg.nodes["phenotype"]["breast_cancer"]
            self.kg.add_edge("gene_associated_phenotype", g_idx, p_idx)

    def add_breast_cancer_drugs(self) -> None:
        """Add standard-of-care breast cancer therapies."""
        drugs_targets = {
            "Tamoxifen": ["ESR1"],
            "Letrozole": ["CYP19A1"],
            "Trastuzumab": ["ERBB2"],
            "Pertuzumab": ["ERBB2"],
            "T-DM1": ["ERBB2"],
            "Palbociclib": ["CDK4", "CDK6"],
            "Ribociclib": ["CDK4", "CDK6"],
            "Abemaciclib": ["CDK4", "CDK6"],
            "Olaparib": ["PARP1", "PARP2"],
            "Talazoparib": ["PARP1", "PARP2"],
            "Pembrolizumab": ["PDCD1"],
            "Atezolizumab": ["CD274"],
            "Everolimus": ["MTOR"],
            "Alpelisib": ["PIK3CA"],
            "Sacituzumab_Govitecan": ["TACSTD2"],
            "Capecitabine": ["TYMS"],
            "Doxorubicin": ["TOP2A"],
            "Paclitaxel": ["TUBB"],
        }
        for drug, targets in drugs_targets.items():
            d_idx = self.kg.add_node("drug", drug)
            for gene in targets:
                g_idx = self.kg.add_node("gene", gene)
                self.kg.add_edge("drug_targets_gene", d_idx, g_idx, {"action": "inhibitor"})

    def build(self) -> BiologicalKnowledgeGraph:
        """Build default KG with curated breast cancer knowledge."""
        self.add_breast_cancer_genes()
        self.add_breast_cancer_drugs()
        logger.info(
            "Built KG: %d genes, %d pathways, %d drugs",
            self.kg.num_nodes("gene"),
            self.kg.num_nodes("pathway"),
            self.kg.num_nodes("drug"),
        )
        return self.kg


# ===================================================================
# Relational GCN on the Knowledge Graph
# ===================================================================

class RelationalGCNLayer(nn.Module):
    """Single layer of a Relational Graph Convolutional Network.

    Aggregates messages per relation type and combines them:

        h_v^{(l+1)} = σ( Σ_r  (1/|N_r(v)|) Σ_{u∈N_r(v)} W_r h_u^{(l)} + W_0 h_v^{(l)} )

    Uses basis decomposition to reduce parameters when the number
    of relations is large.
    """

    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        num_relations: int,
        num_bases: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.num_relations = num_relations

        # Basis decomposition: W_r = Σ_b a_{rb} V_b
        self.num_bases = min(num_bases, num_relations)
        self.bases = nn.Parameter(torch.randn(self.num_bases, in_dim, out_dim) * 0.01)
        self.coefficients = nn.Parameter(torch.randn(num_relations, self.num_bases) * 0.01)

        # Self-loop weight
        self.self_loop = nn.Linear(in_dim, out_dim)
        self.norm = nn.LayerNorm(out_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        edge_indices: Dict[int, torch.LongTensor],
    ) -> torch.Tensor:
        """Forward pass.

        Parameters
        ----------
        x : (N, in_dim) — node features (all types concatenated)
        edge_indices : relation_id → (2, E_r) edge index

        Returns
        -------
        h : (N, out_dim)
        """
        h = self.self_loop(x)  # (N, out)

        for r, edge_idx in edge_indices.items():
            if edge_idx.shape[1] == 0:
                continue
            # Compute W_r via basis decomposition
            coeff = self.coefficients[r]  # (num_bases,)
            W_r = (coeff.unsqueeze(-1).unsqueeze(-1) * self.bases).sum(dim=0)  # (in, out)

            src, dst = edge_idx
            msg = x[src] @ W_r  # (E, out)

            # Scatter-add with degree normalisation
            deg = torch.zeros(x.shape[0], device=x.device)
            deg.scatter_add_(0, dst, torch.ones_like(dst, dtype=torch.float))
            deg = deg.clamp(min=1)

            agg = torch.zeros_like(h)
            agg.scatter_add_(0, dst.unsqueeze(-1).expand_as(msg), msg)
            agg = agg / deg.unsqueeze(-1)

            h = h + agg

        h = self.norm(F.silu(h))
        return self.dropout(h)


class KnowledgeGraphEmbedder(nn.Module):
    """Multi-layer R-GCN to produce biology-aware node embeddings.

    Can be used to:
    1. Initialise gene embeddings for the MolecularEncoder
    2. Provide drug embeddings for treatment response prediction
    3. Regularise the latent space with pathway coherence
    """

    def __init__(self, cfg: KnowledgeGraphConfig, kg: BiologicalKnowledgeGraph):
        super().__init__()
        self.cfg = cfg
        self.kg = kg

        # Node type embeddings (type-specific initial projections)
        self.node_embeddings = nn.ModuleDict()
        for nt in cfg.node_types:
            n = max(kg.num_nodes(nt), 1)
            self.node_embeddings[nt] = nn.Embedding(n, cfg.node_embed_dim)

        # R-GCN layers
        num_rels = len(cfg.edge_types)
        self.layers = nn.ModuleList()
        in_d = cfg.node_embed_dim
        for i in range(cfg.gnn_num_layers):
            out_d = cfg.gnn_hidden_dim if i < cfg.gnn_num_layers - 1 else cfg.node_embed_dim
            self.layers.append(
                RelationalGCNLayer(in_d, out_d, num_rels, dropout=cfg.gnn_dropout)
            )
            in_d = out_d

        # Cache edge indices
        self._edge_cache: Optional[Dict[int, torch.LongTensor]] = None

    def _get_edge_dict(self, device: torch.device) -> Dict[int, torch.LongTensor]:
        """Build edge index dict, accounting for node offsets per type."""
        if self._edge_cache is not None:
            # Check device
            first_key = next(iter(self._edge_cache))
            if self._edge_cache[first_key].device == device:
                return self._edge_cache

        # Compute offsets for each node type
        offsets: Dict[str, int] = {}
        running = 0
        for nt in self.cfg.node_types:
            offsets[nt] = running
            running += max(self.kg.num_nodes(nt), 1)

        edge_dict: Dict[int, torch.LongTensor] = {}
        for r, et in enumerate(self.cfg.edge_types):
            raw = self.kg.get_edge_index(et)
            # Determine source and target node types from edge type name
            # Convention: "gene_in_pathway" → gene → pathway
            src_type, dst_type = self._infer_types(et)
            if raw.shape[1] > 0:
                raw[0] += offsets.get(src_type, 0)
                raw[1] += offsets.get(dst_type, 0)
            edge_dict[r] = raw.to(device)

        self._edge_cache = edge_dict
        return edge_dict

    def _infer_types(self, edge_type: str) -> Tuple[str, str]:
        """Infer src/dst node types from edge type name."""
        mapping = {
            "gene_in_pathway": ("gene", "pathway"),
            "gene_interacts_gene": ("gene", "gene"),
            "drug_targets_gene": ("drug", "gene"),
            "gene_associated_phenotype": ("gene", "phenotype"),
            "pathway_related_pathway": ("pathway", "pathway"),
            "go_annotates_gene": ("go_term", "gene"),
            "drug_treats_phenotype": ("drug", "phenotype"),
        }
        return mapping.get(edge_type, ("gene", "gene"))

    def forward(self) -> Dict[str, torch.Tensor]:
        """Compute embeddings for all node types.

        Returns
        -------
        Dict mapping node_type → (N_type, embed_dim)
        """
        # Concatenate all node embeddings
        all_embs = []
        for nt in self.cfg.node_types:
            n = max(self.kg.num_nodes(nt), 1)
            idx = torch.arange(n, device=self.node_embeddings[nt].weight.device)
            all_embs.append(self.node_embeddings[nt](idx))
        x = torch.cat(all_embs, dim=0)

        edge_dict = self._get_edge_dict(x.device)

        for layer in self.layers:
            x = layer(x, edge_dict)

        # Split back by node type
        result = {}
        offset = 0
        for nt in self.cfg.node_types:
            n = max(self.kg.num_nodes(nt), 1)
            result[nt] = x[offset: offset + n]
            offset += n

        return result


# ===================================================================
# Pathway Activity Inference (KG-guided)
# ===================================================================

class KGPathwayScorer(nn.Module):
    """Infer pathway activity scores using KG-derived gene-pathway edges.

    Unlike simple average-based gene set scoring, this uses learned
    attention weights over KG-connected genes to compute pathway
    activities, respecting the graph topology.
    """

    def __init__(
        self,
        gene_embed_dim: int,
        pathway_embed_dim: int,
        num_pathways: int,
        hidden_dim: int = 128,
    ):
        super().__init__()
        self.gene_proj = nn.Linear(gene_embed_dim, hidden_dim)
        self.pathway_proj = nn.Linear(pathway_embed_dim, hidden_dim)
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )
        self.output_proj = nn.Linear(hidden_dim, 1)
        self.num_pathways = num_pathways

    def forward(
        self,
        gene_expression: torch.Tensor,
        gene_embeddings: torch.Tensor,
        pathway_embeddings: torch.Tensor,
        gene_pathway_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Compute pathway activity scores.

        Parameters
        ----------
        gene_expression : (B, G) — expression values
        gene_embeddings : (G, gene_embed_dim) — KG gene embeddings
        pathway_embeddings : (P, pathway_embed_dim) — KG pathway embeddings
        gene_pathway_mask : (P, G) — binary membership

        Returns
        -------
        pathway_scores : (B, P)
        """
        B, G = gene_expression.shape
        P = pathway_embeddings.shape[0]

        g_proj = self.gene_proj(gene_embeddings)  # (G, H)
        p_proj = self.pathway_proj(pathway_embeddings)  # (P, H)

        # Expression-weighted gene features: (B, G, H)
        g_feat = g_proj.unsqueeze(0) * gene_expression.unsqueeze(-1)

        scores = []
        for p in range(P):
            mask = gene_pathway_mask[p]  # (G,)
            if mask.sum() == 0:
                scores.append(torch.zeros(B, 1, device=gene_expression.device))
                continue

            # Attend over genes in this pathway
            p_feat = p_proj[p].unsqueeze(0).expand(B, -1)  # (B, H)
            member_genes = g_feat[:, mask.bool()]  # (B, K, H)
            K = member_genes.shape[1]

            p_expand = p_feat.unsqueeze(1).expand(-1, K, -1)  # (B, K, H)
            attn_in = torch.cat([member_genes, p_expand], dim=-1)
            attn_w = self.attention(attn_in).softmax(dim=1)  # (B, K, 1)

            pooled = (member_genes * attn_w).sum(dim=1)  # (B, H)
            score = self.output_proj(pooled)  # (B, 1)
            scores.append(score)

        return torch.cat(scores, dim=-1)  # (B, P)


# ===================================================================
# Drug Sensitivity Predictor (KG-informed)
# ===================================================================

class DrugSensitivityPredictor(nn.Module):
    """Predict drug sensitivity from tissue state + KG drug embeddings.

    For each drug, combines:
    1. The patient's tissue state (from the latent manifold)
    2. The drug's KG embedding (incorporating target gene context)
    3. Patient molecular profile features

    Outputs IC50-like sensitivity scores and binary response prediction.
    """

    def __init__(
        self,
        tissue_dim: int = 128,
        drug_embed_dim: int = 128,
        molecular_dim: int = 512,
        hidden_dim: int = 128,
        num_drugs: int = 18,
    ):
        super().__init__()
        self.num_drugs = num_drugs
        input_dim = tissue_dim + drug_embed_dim + molecular_dim

        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.SiLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Dropout(0.1),
        )
        self.sensitivity_head = nn.Linear(hidden_dim, 1)  # continuous IC50
        self.response_head = nn.Linear(hidden_dim, 1)  # binary response

    def forward(
        self,
        tissue_state: torch.Tensor,
        drug_embeddings: torch.Tensor,
        molecular_embedding: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """Predict sensitivity for all drugs.

        Parameters
        ----------
        tissue_state : (B, tissue_dim)
        drug_embeddings : (D, drug_embed_dim) — all drug embeddings
        molecular_embedding : (B, molecular_dim)

        Returns
        -------
        Dict with:
            sensitivity : (B, D) — predicted IC50 (lower = more sensitive)
            response_prob : (B, D) — P(response) for each drug
            recommended_drugs : (B, top_k) — indices of most promising drugs
        """
        B = tissue_state.shape[0]
        D = drug_embeddings.shape[0]

        sensitivities = []
        response_probs = []

        for d in range(D):
            d_emb = drug_embeddings[d].unsqueeze(0).expand(B, -1)
            combined = torch.cat([tissue_state, d_emb, molecular_embedding], dim=-1)
            h = self.net(combined)
            sens = self.sensitivity_head(h).squeeze(-1)  # (B,)
            resp = torch.sigmoid(self.response_head(h)).squeeze(-1)  # (B,)
            sensitivities.append(sens)
            response_probs.append(resp)

        sens_all = torch.stack(sensitivities, dim=1)  # (B, D)
        resp_all = torch.stack(response_probs, dim=1)  # (B, D)

        # Top-3 recommended drugs (highest response probability)
        _, top_drugs = resp_all.topk(min(3, D), dim=1)

        return {
            "sensitivity": sens_all,
            "response_prob": resp_all,
            "recommended_drugs": top_drugs,
        }
