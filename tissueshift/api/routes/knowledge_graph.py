"""Knowledge graph query endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # gene | pathway | drug | phenotype
    properties: dict = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0


class SubgraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathwayDetail(BaseModel):
    id: str
    name: str
    genes: list[str]
    description: str
    clinical_relevance: str


# ── Static knowledge graph ──────────────────────────────────────────

_NODES = [
    GraphNode(id="ERBB2", label="ERBB2 / HER2", type="gene",
              properties={"chromosome": "17q12", "druggable": True}),
    GraphNode(id="PIK3CA", label="PIK3CA", type="gene",
              properties={"chromosome": "3q26.32", "druggable": True}),
    GraphNode(id="AKT1", label="AKT1", type="gene",
              properties={"chromosome": "14q32.33", "druggable": True}),
    GraphNode(id="TP53", label="TP53", type="gene",
              properties={"chromosome": "17p13.1", "druggable": False}),
    GraphNode(id="MDM2", label="MDM2", type="gene",
              properties={"chromosome": "12q15", "druggable": True}),
    GraphNode(id="CDK4", label="CDK4", type="gene",
              properties={"chromosome": "12q14.1", "druggable": True}),
    GraphNode(id="mTOR", label="mTOR Pathway", type="pathway"),
    GraphNode(id="MAPK", label="MAPK/ERK Pathway", type="pathway"),
    GraphNode(id="MEK", label="MEK1/2", type="gene",
              properties={"chromosome": "15q22.31", "druggable": True}),
    GraphNode(id="trastuzumab", label="Trastuzumab", type="drug",
              properties={"target": "ERBB2", "class": "monoclonal antibody"}),
    GraphNode(id="alpelisib", label="Alpelisib", type="drug",
              properties={"target": "PIK3CA", "class": "PI3K inhibitor"}),
    GraphNode(id="palbociclib", label="Palbociclib", type="drug",
              properties={"target": "CDK4", "class": "CDK4/6 inhibitor"}),
    GraphNode(id="everolimus", label="Everolimus", type="drug",
              properties={"target": "mTOR", "class": "mTOR inhibitor"}),
    GraphNode(id="pembrolizumab", label="Pembrolizumab", type="drug",
              properties={"target": "PD-1", "class": "immune checkpoint inhibitor"}),
]

_EDGES = [
    GraphEdge(source="ERBB2", target="PIK3CA", relation="activates", weight=0.85),
    GraphEdge(source="PIK3CA", target="AKT1", relation="phosphorylates", weight=0.92),
    GraphEdge(source="AKT1", target="mTOR", relation="activates", weight=0.88),
    GraphEdge(source="ERBB2", target="MAPK", relation="activates", weight=0.78),
    GraphEdge(source="MAPK", target="MEK", relation="signals_through", weight=0.80),
    GraphEdge(source="TP53", target="MDM2", relation="regulated_by", weight=0.90),
    GraphEdge(source="MDM2", target="CDK4", relation="interacts_with", weight=0.65),
    GraphEdge(source="trastuzumab", target="ERBB2", relation="inhibits", weight=0.95),
    GraphEdge(source="alpelisib", target="PIK3CA", relation="inhibits", weight=0.88),
    GraphEdge(source="palbociclib", target="CDK4", relation="inhibits", weight=0.91),
    GraphEdge(source="everolimus", target="mTOR", relation="inhibits", weight=0.87),
]

_PATHWAYS = [
    PathwayDetail(id="pi3k-akt-mtor", name="PI3K/AKT/mTOR Signaling",
                  genes=["PIK3CA", "AKT1", "PTEN", "mTOR", "TSC1"],
                  description="Central signaling cascade driving cell growth, survival, and metabolism.",
                  clinical_relevance="Frequently mutated in luminal breast cancer. Targetable with alpelisib + fulvestrant."),
    PathwayDetail(id="mapk-erk", name="MAPK/ERK Pathway",
                  genes=["KRAS", "BRAF", "MEK1", "ERK1", "ERK2"],
                  description="Mitogen-activated protein kinase cascade controlling proliferation.",
                  clinical_relevance="Cross-talk with HER2 signaling. MEK inhibitors under investigation."),
    PathwayDetail(id="dna-damage", name="DNA Damage Repair",
                  genes=["TP53", "BRCA1", "BRCA2", "ATM", "CHEK2"],
                  description="Genome integrity maintenance through homologous recombination and checkpoint control.",
                  clinical_relevance="BRCA1/2 mutations predict PARP inhibitor sensitivity (olaparib)."),
    PathwayDetail(id="cell-cycle", name="Cell Cycle Regulation",
                  genes=["CDK4", "CDK6", "CCND1", "RB1", "CDKN2A"],
                  description="Controls cell division through cyclin-dependent kinase activity.",
                  clinical_relevance="CDK4/6 inhibitors (palbociclib, ribociclib) are standard of care in HR+ disease."),
]

_NODE_MAP = {n.id: n for n in _NODES}


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/nodes", response_model=list[GraphNode])
async def list_nodes(type: Optional[str] = Query(None)):
    """List all nodes, optionally filtered by type."""
    result = _NODES
    if type:
        result = [n for n in result if n.type == type]
    return result


@router.get("/nodes/{node_id}", response_model=GraphNode)
async def get_node(node_id: str):
    """Get details for a single node."""
    if node_id not in _NODE_MAP:
        raise HTTPException(status_code=404, detail="Node not found")
    return _NODE_MAP[node_id]


@router.get("/subgraph", response_model=SubgraphResponse)
async def get_subgraph(center: str = Query(...), depth: int = Query(1, ge=1, le=3)):
    """Get a subgraph centered around a node up to N hops."""
    if center not in _NODE_MAP:
        raise HTTPException(status_code=404, detail="Center node not found")

    visited = {center}
    frontier = {center}
    kept_edges = []

    for _ in range(depth):
        next_frontier = set()
        for edge in _EDGES:
            if edge.source in frontier:
                next_frontier.add(edge.target)
                kept_edges.append(edge)
            if edge.target in frontier:
                next_frontier.add(edge.source)
                kept_edges.append(edge)
        frontier = next_frontier - visited
        visited |= frontier

    nodes = [_NODE_MAP[nid] for nid in visited if nid in _NODE_MAP]
    return SubgraphResponse(nodes=nodes, edges=kept_edges)


@router.get("/pathways", response_model=list[PathwayDetail])
async def list_pathways():
    """List all known biological pathways."""
    return _PATHWAYS


@router.get("/pathways/{pathway_id}", response_model=PathwayDetail)
async def get_pathway(pathway_id: str):
    """Get details for a specific pathway."""
    for p in _PATHWAYS:
        if p.id == pathway_id:
            return p
    raise HTTPException(status_code=404, detail="Pathway not found")
