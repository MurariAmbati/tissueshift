"""Slide analysis endpoints — WSI upload and AI inference."""

from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class AttentionHotspot(BaseModel):
    x: int
    y: int
    w: int
    h: int
    weight: float
    label: str


class LatentComponent(BaseModel):
    name: str
    value: float
    description: str


class AnalysisResult(BaseModel):
    id: str
    patient_id: Optional[str]
    filename: str
    subtype: str
    risk_score: float
    confidence: float
    cells_counted: int
    mitotic_index: float
    tumor_purity: float
    til_score: float
    hotspots: list[AttentionHotspot]
    latent_components: list[LatentComponent]
    created_at: str


_ANALYSES: dict[str, dict] = {}

SUBTYPES = ["luminal_a", "luminal_b", "her2_enriched", "basal", "normal_like", "claudin_low"]


@router.post("", response_model=AnalysisResult, status_code=201)
async def analyze_slide(
    file: UploadFile = File(...),
    patient_id: Optional[str] = Query(None),
):
    """Run AI inference on an uploaded whole-slide image."""
    contents = await file.read()
    file_hash = hashlib.sha256(contents[:4096]).hexdigest()[:12]
    aid = f"A-{uuid.uuid4().hex[:6].upper()}"

    # Simulated inference results
    subtype = random.choice(SUBTYPES)
    risk = round(random.uniform(0.05, 0.95), 3)
    conf = round(random.uniform(0.80, 0.99), 3)

    hotspots = [
        AttentionHotspot(x=random.randint(100, 900), y=random.randint(100, 900),
                         w=64, h=64, weight=round(random.uniform(0.6, 1.0), 3),
                         label=f"Region {i+1}")
        for i in range(5)
    ]
    latent = [
        LatentComponent(name="Proliferative Index", value=round(random.uniform(0, 1), 3),
                        description="Measures cell division activity"),
        LatentComponent(name="Stromal Reactivity", value=round(random.uniform(0, 1), 3),
                        description="Captures tumor microenvironment response"),
        LatentComponent(name="Immune Infiltration", value=round(random.uniform(0, 1), 3),
                        description="Tumor-infiltrating lymphocyte density"),
        LatentComponent(name="Nuclear Pleomorphism", value=round(random.uniform(0, 1), 3),
                        description="Variation in nuclear size and shape"),
        LatentComponent(name="Glandular Architecture", value=round(random.uniform(0, 1), 3),
                        description="Preservation of normal gland structure"),
    ]

    result = AnalysisResult(
        id=aid,
        patient_id=patient_id,
        filename=file.filename or "unknown.svs",
        subtype=subtype,
        risk_score=risk,
        confidence=conf,
        cells_counted=random.randint(8000, 25000),
        mitotic_index=round(random.uniform(1, 30), 1),
        tumor_purity=round(random.uniform(0.5, 0.98), 2),
        til_score=round(random.uniform(0.05, 0.60), 2),
        hotspots=hotspots,
        latent_components=latent,
        created_at=datetime.utcnow().isoformat(),
    )
    _ANALYSES[aid] = result.model_dump()
    return result


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str):
    """Retrieve a previously completed analysis."""
    if analysis_id not in _ANALYSES:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _ANALYSES[analysis_id]


@router.get("", response_model=list[AnalysisResult])
async def list_analyses(patient_id: Optional[str] = Query(None)):
    """List all analyses, optionally filtered by patient."""
    results = list(_ANALYSES.values())
    if patient_id:
        results = [a for a in results if a.get("patient_id") == patient_id]
    return results
