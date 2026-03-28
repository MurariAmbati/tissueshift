"""Dashboard shared helpers — theme, session state, caching, chart utils."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

# ===================================================================
# Theme / CSS
# ===================================================================

CLINICAL_CSS = """
<style>
    /* Global font */
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #ebf4ff 0%, #fff 100%);
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #2b6cb0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        margin-bottom: 0.8rem;
    }
    .metric-card h4 { color: #2b6cb0; margin: 0 0 0.3rem 0; font-size: 0.85rem; }
    .metric-card .value { font-size: 1.8rem; font-weight: 700; color: #1a365d; }
    .metric-card .delta { font-size: 0.8rem; color: #718096; }

    /* Risk badges */
    .risk-low { background: #c6f6d5; color: #22543d; padding: 2px 10px; border-radius: 12px; font-weight: 600; }
    .risk-moderate { background: #fefcbf; color: #744210; padding: 2px 10px; border-radius: 12px; font-weight: 600; }
    .risk-high { background: #fed7d7; color: #822727; padding: 2px 10px; border-radius: 12px; font-weight: 600; }

    /* Status dots */
    .status-active { color: #38a169; }
    .status-inactive { color: #a0aec0; }

    /* Section header */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #2d3748;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.3rem;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }

    /* Confidence bar */
    .conf-bar { height: 8px; border-radius: 4px; background: #e2e8f0; }
    .conf-fill { height: 100%; border-radius: 4px; }
    .conf-high { background: #38a169; }
    .conf-mid  { background: #d69e2e; }
    .conf-low  { background: #e53e3e; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""


def inject_css() -> None:
    """Inject clinical dashboard CSS."""
    st.markdown(CLINICAL_CSS, unsafe_allow_html=True)


# ===================================================================
# Session State Defaults
# ===================================================================

def init_session_state() -> None:
    """Initialise session state with defaults."""
    defaults = {
        "patients": {},          # patient_id → PatientProfile dict
        "current_patient": None, # active patient_id
        "slides": {},            # slide_id → slide data
        "model_loaded": False,
        "model_path": "",
        "results_cache": {},     # patient_id → last results
        "cohort_data": None,
        "settings": {
            "institution": "TissueShift AI Pathology",
            "confidence_threshold": 0.85,
            "mc_samples": 20,
            "device": "cpu",
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ===================================================================
# Component Helpers
# ===================================================================

def metric_card(label: str, value: str, delta: str = "") -> str:
    """Return HTML for a styled metric card."""
    delta_html = f'<div class="delta">{delta}</div>' if delta else ""
    return (
        f'<div class="metric-card">'
        f'<h4>{label}</h4>'
        f'<div class="value">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def risk_badge(level: str) -> str:
    """Return HTML badge for risk level."""
    cls = {
        "low": "risk-low",
        "moderate": "risk-moderate",
        "high": "risk-high",
    }.get(level.lower(), "risk-moderate")
    return f'<span class="{cls}">{level.title()}</span>'


def confidence_bar(value: float) -> str:
    """Confidence bar HTML (0–1)."""
    pct = round(value * 100)
    cls = "conf-high" if value >= 0.85 else ("conf-mid" if value >= 0.6 else "conf-low")
    return (
        f'<div class="conf-bar">'
        f'<div class="conf-fill {cls}" style="width: {pct}%"></div>'
        f'</div>'
        f'<small>{pct}% confidence</small>'
    )


def section_header(text: str) -> None:
    """Render a styled section header."""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ===================================================================
# Demo / Mock Data Generators
# ===================================================================

def demo_patient(patient_id: str = "PT-001") -> Dict[str, Any]:
    """Generate a demo patient profile."""
    return {
        "patient_id": patient_id,
        "age": 54,
        "sex": "Female",
        "diagnosis": "Invasive Ductal Carcinoma",
        "diagnosis_date": "2024-01-15",
        "er_status": "Positive",
        "pr_status": "Positive",
        "her2_status": "Negative",
        "ki67": 18.5,
        "grade": 2,
        "stage": "IIA",
        "molecular_subtype": "Luminal A",
        "brca_status": "Wild-type",
        "treatments": [
            {"name": "Tamoxifen", "start": "2024-02-01", "status": "active"},
            {"name": "AC-T Chemotherapy", "start": "2024-01-20", "end": "2024-04-15", "status": "completed"},
        ],
        "observations": [
            {"date": "2024-01-15", "type": "biopsy", "notes": "Initial core biopsy"},
            {"date": "2024-03-15", "type": "imaging", "notes": "Partial response on MRI"},
            {"date": "2024-06-01", "type": "blood", "notes": "Tumour markers trending down"},
        ],
    }


def demo_model_outputs() -> Dict[str, Any]:
    """Generate demo model prediction outputs."""
    import random
    random.seed(42)
    return {
        "subtype_probs": {
            "luminal_a": 0.72,
            "luminal_b": 0.15,
            "her2_enriched": 0.05,
            "basal": 0.04,
            "normal_like": 0.02,
            "claudin_low": 0.02,
        },
        "grade": {"overall": 2, "tubule": 2, "nuclear": 2, "mitotic": 1},
        "molecular": {
            "er_prob": 0.92,
            "pr_prob": 0.78,
            "her2_prob": 0.12,
            "ki67_index": 18.5,
        },
        "survival": {
            "risk_score": 0.35,
            "five_year_survival": 0.89,
        },
        "treatment": {
            "drug_sensitivity": {
                "Tamoxifen": 0.82,
                "Letrozole": 0.79,
                "Anastrozole": 0.76,
                "Paclitaxel": 0.45,
                "Doxorubicin": 0.38,
                "Trastuzumab": 0.15,
            },
            "recommended_regimen": "Endocrine therapy (Tamoxifen / Aromatase Inhibitor)",
        },
        "biomarkers": {
            "ESR1": 2.8,
            "PGR": 1.9,
            "ERBB2": -0.5,
            "MKI67": 0.6,
            "TP53": -0.2,
        },
        "gene_expression": {g: random.gauss(0, 1) for g in [
            "ESR1", "PGR", "ERBB2", "MKI67", "TP53", "PIK3CA", "GATA3",
            "FOXA1", "CDH1", "MAP3K1", "PTEN", "CCND1", "FGFR1", "MYC",
            "BRCA1", "BRCA2", "PALB2", "CHEK2", "ATM", "RAD51",
        ]},
    }


def demo_uncertainty() -> Dict[str, Any]:
    return {
        "confidence": 0.88,
        "entropy": 0.34,
        "epistemic": 0.12,
        "aleatoric": 0.22,
        "set_size": 2,
        "ece": 0.03,
    }


def demo_digital_twin_summary() -> Dict[str, Any]:
    return {
        "horizon": "5 years",
        "current_state": {"subtype": "Luminal A", "stability": "Stable"},
        "one_year_outlook": {
            "subtype_shift_prob": 0.08,
            "expected_subtype": "Luminal A",
            "confidence": 0.91,
        },
        "risk_windows": [
            {"period": "12-18 months", "risk_type": "Subtype shift", "probability": 0.12},
            {"period": "24-36 months", "risk_type": "Recurrence", "probability": 0.18},
        ],
        "monitoring": {
            "next_imaging": "6 months",
            "next_blood_work": "3 months",
            "reassessment": "12 months",
        },
    }
