"""Patient CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────

class ReceptorStatus(BaseModel):
    er: bool = True
    pr: bool = True
    her2: bool = False


class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    age: int = Field(..., ge=0, le=130)
    sex: str = Field(default="Female")
    stage: str = Field(default="II")
    tumor_size_cm: float = Field(default=0.0, ge=0)
    lymph_nodes_positive: int = Field(default=0, ge=0)
    receptors: ReceptorStatus = Field(default_factory=ReceptorStatus)
    ki67_percent: float = Field(default=0.0, ge=0, le=100)


class PatientResponse(BaseModel):
    id: str
    name: str
    age: int
    sex: str
    stage: str
    tumor_size_cm: float
    lymph_nodes_positive: int
    receptors: ReceptorStatus
    ki67_percent: float
    subtype: Optional[str] = None
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    created_at: str
    updated_at: str


class PatientListResponse(BaseModel):
    patients: list[PatientResponse]
    total: int
    page: int
    per_page: int


# ── In-memory store (replace with DB in production) ────────────────

_PATIENTS: dict[str, dict] = {}


def _seed() -> None:
    """Seed demo patients if store is empty."""
    if _PATIENTS:
        return
    demo = [
        dict(name="Jane Doe", age=58, sex="Female", stage="IIA", tumor_size_cm=2.3,
             lymph_nodes_positive=1, receptors=dict(er=True, pr=True, her2=False),
             ki67_percent=14, subtype="luminal_a", risk_score=0.23, confidence=0.96),
        dict(name="Mary Smith", age=47, sex="Female", stage="IIIA", tumor_size_cm=4.1,
             lymph_nodes_positive=4, receptors=dict(er=False, pr=False, her2=True),
             ki67_percent=42, subtype="her2_enriched", risk_score=0.71, confidence=0.89),
        dict(name="Alice Chen", age=62, sex="Female", stage="IIB", tumor_size_cm=3.5,
             lymph_nodes_positive=2, receptors=dict(er=True, pr=False, her2=False),
             ki67_percent=28, subtype="luminal_b", risk_score=0.54, confidence=0.91),
        dict(name="Rachel Adams", age=39, sex="Female", stage="IIIB", tumor_size_cm=5.2,
             lymph_nodes_positive=7, receptors=dict(er=False, pr=False, her2=False),
             ki67_percent=68, subtype="basal", risk_score=0.89, confidence=0.94),
        dict(name="Emma Wilson", age=55, sex="Female", stage="I", tumor_size_cm=1.1,
             lymph_nodes_positive=0, receptors=dict(er=True, pr=True, her2=False),
             ki67_percent=8, subtype="normal_like", risk_score=0.12, confidence=0.97),
    ]
    now = datetime.utcnow().isoformat()
    for d in demo:
        pid = f"P-{uuid.uuid4().hex[:6].upper()}"
        _PATIENTS[pid] = {**d, "id": pid, "created_at": now, "updated_at": now}


_seed()


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    risk: Optional[str] = Query(None),
    subtype: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List patients with pagination and optional filters."""
    result = list(_PATIENTS.values())

    if search:
        q = search.lower()
        result = [p for p in result if q in p["name"].lower() or q in p["id"].lower()]
    if risk:
        thresholds = {"low": (0, 0.33), "moderate": (0.33, 0.66), "high": (0.66, 1.01)}
        lo, hi = thresholds.get(risk, (0, 1.01))
        result = [p for p in result if lo <= (p.get("risk_score") or 0) < hi]
    if subtype:
        result = [p for p in result if p.get("subtype") == subtype]

    total = len(result)
    start = (page - 1) * per_page
    page_items = result[start : start + per_page]
    return PatientListResponse(patients=page_items, total=total, page=page, per_page=per_page)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str):
    """Get a single patient by ID."""
    if patient_id not in _PATIENTS:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _PATIENTS[patient_id]


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(body: PatientCreate):
    """Create a new patient record."""
    pid = f"P-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.utcnow().isoformat()
    record = {
        **body.model_dump(),
        "id": pid,
        "receptors": body.receptors.model_dump(),
        "subtype": None,
        "risk_score": None,
        "confidence": None,
        "created_at": now,
        "updated_at": now,
    }
    _PATIENTS[pid] = record
    return record


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, body: PatientCreate):
    """Update an existing patient."""
    if patient_id not in _PATIENTS:
        raise HTTPException(status_code=404, detail="Patient not found")
    existing = _PATIENTS[patient_id]
    now = datetime.utcnow().isoformat()
    updated = {
        **existing,
        **body.model_dump(),
        "receptors": body.receptors.model_dump(),
        "updated_at": now,
    }
    _PATIENTS[patient_id] = updated
    return updated


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(patient_id: str):
    """Delete a patient record."""
    if patient_id not in _PATIENTS:
        raise HTTPException(status_code=404, detail="Patient not found")
    del _PATIENTS[patient_id]
