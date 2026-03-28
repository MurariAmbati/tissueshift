"""Clinical report generator — automated pathology reports from model outputs.

Produces structured, human-readable clinical reports that integrate:
* Histopathological grading and subtype classification
* Molecular biomarker predictions (ER, PR, HER2, Ki-67)
* Treatment response forecasts
* Uncertainty quantification & confidence levels
* Digital-twin longitudinal projections
* Actionable clinical recommendations

Output formats: structured dict, Markdown, HTML, and HL7 FHIR-compatible JSON.

Designed for integration into the clinical dashboard as a one-click
"Generate Report" action attached to a patient case.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ===================================================================
# Configuration
# ===================================================================

@dataclass
class ReportConfig:
    """Report generation settings."""

    institution_name: str = "TissueShift AI Pathology"
    report_version: str = "1.0"
    include_uncertainty: bool = True
    include_digital_twin: bool = True
    include_treatment_recs: bool = True
    include_biomarkers: bool = True
    include_molecular_profile: bool = True
    confidence_threshold: float = 0.85
    risk_levels: Dict[str, float] = field(default_factory=lambda: {
        "low": 0.3, "moderate": 0.6, "high": 1.0,
    })
    languages: List[str] = field(default_factory=lambda: ["en"])


# ===================================================================
# Structured Report Sections
# ===================================================================

@dataclass
class PatientInfo:
    """De-identified patient demographics for the report header."""
    patient_id: str = ""
    age: Optional[int] = None
    sex: Optional[str] = None
    referring_physician: str = ""
    specimen_id: str = ""
    specimen_type: str = "breast core biopsy"
    collection_date: Optional[str] = None
    report_date: str = field(default_factory=lambda: datetime.date.today().isoformat())


@dataclass
class HistopathologyFindings:
    """Structured histopathological grading."""
    tumour_type: str = ""
    histological_grade: int = 0  # 1-3 Nottingham
    tubule_formation: int = 0  # 1-3
    nuclear_pleomorphism: int = 0  # 1-3
    mitotic_count: int = 0  # 1-3
    tumour_size_mm: Optional[float] = None
    lymphovascular_invasion: Optional[bool] = None
    in_situ_component: Optional[str] = None
    margins: Optional[str] = None
    notes: str = ""


@dataclass
class MolecularProfile:
    """Predicted molecular biomarkers."""
    er_status: Optional[str] = None  # positive / negative
    er_percentage: Optional[float] = None
    pr_status: Optional[str] = None
    pr_percentage: Optional[float] = None
    her2_status: Optional[str] = None  # 0, 1+, 2+, 3+
    her2_score: Optional[float] = None
    ki67_percentage: Optional[float] = None
    molecular_subtype: str = ""  # Luminal A/B, HER2+, Basal, Normal-like
    confidence: float = 0.0


@dataclass
class RiskAssessment:
    """Clinical risk assessment derived from model outputs."""
    recurrence_risk: str = ""  # low / intermediate / high
    recurrence_score: float = 0.0
    five_year_survival_estimate: Optional[float] = None
    uncertainty_range: Optional[tuple] = None
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class TreatmentRecommendation:
    """Model-suggested treatment considerations."""
    primary_recommendation: str = ""
    alternative_options: List[str] = field(default_factory=list)
    predicted_response: Dict[str, float] = field(default_factory=dict)
    evidence_level: str = ""  # A / B / C
    clinical_trial_eligible: bool = False
    notes: str = ""


# ===================================================================
# Report Builder
# ===================================================================

class ClinicalReportBuilder:
    """Assembles structured report from model outputs.

    Takes raw model predictions and converts them into clinically
    meaningful, structured report sections.
    """

    def __init__(self, cfg: ReportConfig = ReportConfig()):
        self.cfg = cfg

    def build_report(
        self,
        patient: PatientInfo,
        model_outputs: Dict[str, Any],
        digital_twin_summary: Optional[Dict[str, Any]] = None,
        uncertainty_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build complete structured report.

        Parameters
        ----------
        patient : Patient demographics.
        model_outputs : Raw model predictions dict.
        digital_twin_summary : Optional digital twin projection.
        uncertainty_info : Optional uncertainty quantification.

        Returns
        -------
        Structured report dictionary.
        """
        report: Dict[str, Any] = {
            "metadata": self._build_metadata(patient),
            "patient": self._patient_section(patient),
            "histopathology": self._histopath_section(model_outputs),
        }

        if self.cfg.include_molecular_profile:
            report["molecular_profile"] = self._molecular_section(model_outputs)

        if self.cfg.include_biomarkers:
            report["biomarkers"] = self._biomarker_section(model_outputs)

        report["risk_assessment"] = self._risk_section(
            model_outputs, digital_twin_summary
        )

        if self.cfg.include_treatment_recs:
            report["treatment"] = self._treatment_section(model_outputs)

        if self.cfg.include_uncertainty and uncertainty_info:
            report["uncertainty"] = self._uncertainty_section(uncertainty_info)

        if self.cfg.include_digital_twin and digital_twin_summary:
            report["longitudinal_projection"] = self._twin_section(
                digital_twin_summary
            )

        report["conclusion"] = self._conclusion(report)
        report["disclaimer"] = self._disclaimer()

        return report

    # ---------------------------------------------------------------
    # Section builders
    # ---------------------------------------------------------------

    def _build_metadata(self, patient: PatientInfo) -> Dict[str, str]:
        return {
            "institution": self.cfg.institution_name,
            "report_version": self.cfg.report_version,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "specimen_id": patient.specimen_id,
            "report_type": "AI-Assisted Pathology Report",
        }

    def _patient_section(self, patient: PatientInfo) -> Dict[str, Any]:
        return {
            "patient_id": patient.patient_id,
            "age": patient.age,
            "sex": patient.sex,
            "referring_physician": patient.referring_physician,
            "specimen_type": patient.specimen_type,
            "collection_date": patient.collection_date,
        }

    def _histopath_section(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        subtype_probs = outputs.get("subtype_probs", {})
        grade_pred = outputs.get("grade", {})

        # Determine tumour type from predicted subtype
        if isinstance(subtype_probs, dict):
            top_subtype = max(subtype_probs, key=subtype_probs.get) if subtype_probs else "Unknown"
            top_conf = subtype_probs.get(top_subtype, 0.0)
        else:
            top_subtype = "Unknown"
            top_conf = 0.0

        subtype_map = {
            "luminal_a": "Invasive ductal carcinoma, Luminal A",
            "luminal_b": "Invasive ductal carcinoma, Luminal B",
            "her2_enriched": "Invasive ductal carcinoma, HER2-enriched",
            "basal": "Invasive ductal carcinoma, Basal-like",
            "normal_like": "Invasive ductal carcinoma, Normal-like",
            "claudin_low": "Invasive ductal carcinoma, Claudin-low",
            "dcis": "Ductal carcinoma in situ",
        }

        findings = {
            "tumour_type": subtype_map.get(top_subtype, top_subtype),
            "predicted_subtype": top_subtype,
            "subtype_confidence": round(top_conf, 3),
            "all_subtype_probabilities": subtype_probs,
        }

        if grade_pred:
            findings.update({
                "histological_grade": grade_pred.get("overall", 0),
                "tubule_formation_score": grade_pred.get("tubule", 0),
                "nuclear_pleomorphism_score": grade_pred.get("nuclear", 0),
                "mitotic_score": grade_pred.get("mitotic", 0),
            })

        return findings

    def _molecular_section(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        mol = outputs.get("molecular", {})
        er = mol.get("er_prob", None)
        pr = mol.get("pr_prob", None)
        her2 = mol.get("her2_prob", None)
        ki67 = mol.get("ki67_index", None)

        section = {}
        if er is not None:
            section["er_status"] = "Positive" if er > 0.5 else "Negative"
            section["er_probability"] = round(float(er), 3)
        if pr is not None:
            section["pr_status"] = "Positive" if pr > 0.5 else "Negative"
            section["pr_probability"] = round(float(pr), 3)
        if her2 is not None:
            score = 0 if her2 < 0.25 else (1 if her2 < 0.5 else (2 if her2 < 0.75 else 3))
            section["her2_ihc_score"] = f"{score}+"
            section["her2_probability"] = round(float(her2), 3)
        if ki67 is not None:
            section["ki67_index"] = round(float(ki67), 1)
            section["ki67_category"] = "High" if ki67 > 20 else "Low"

        section["molecular_subtype"] = self._infer_molecular_subtype(section)
        return section

    def _infer_molecular_subtype(self, mol: Dict[str, Any]) -> str:
        """Derive molecular subtype from receptor status."""
        er = mol.get("er_status", "")
        pr = mol.get("pr_status", "")
        her2 = mol.get("her2_ihc_score", "0+")
        ki67 = mol.get("ki67_category", "Low")
        her2_pos = her2 in ("2+", "3+")

        if er == "Positive" and not her2_pos:
            return "Luminal A" if ki67 == "Low" else "Luminal B (HER2-)"
        if er == "Positive" and her2_pos:
            return "Luminal B (HER2+)"
        if er == "Negative" and her2_pos:
            return "HER2-enriched"
        if er == "Negative" and pr == "Negative" and not her2_pos:
            return "Triple-negative / Basal-like"
        return "Unclassified"

    def _biomarker_section(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        biomarkers = outputs.get("biomarkers", {})
        gene_expr = outputs.get("gene_expression", {})

        section = {"predicted_biomarkers": biomarkers}
        if gene_expr:
            # Top differentially expressed genes
            sorted_genes = sorted(
                gene_expr.items(), key=lambda x: abs(x[1]), reverse=True
            )[:20]
            section["top_genes"] = {g: round(v, 4) for g, v in sorted_genes}

        return section

    def _risk_section(
        self,
        outputs: Dict[str, Any],
        twin: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        survival = outputs.get("survival", {})
        risk_score = survival.get("risk_score", 0.5)

        # Map to risk category
        thresholds = self.cfg.risk_levels
        if risk_score < thresholds.get("low", 0.3):
            category = "Low"
        elif risk_score < thresholds.get("moderate", 0.6):
            category = "Intermediate"
        else:
            category = "High"

        section: Dict[str, Any] = {
            "recurrence_risk_category": category,
            "recurrence_risk_score": round(float(risk_score), 3),
        }

        if "five_year_survival" in survival:
            section["five_year_os_estimate"] = round(
                float(survival["five_year_survival"]), 3
            )

        if twin and "risk_windows" in twin:
            section["projected_risk_windows"] = twin["risk_windows"]

        return section

    def _treatment_section(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        treatment = outputs.get("treatment", {})
        drug_scores = treatment.get("drug_sensitivity", {})

        # Sort by predicted response
        ranked = sorted(drug_scores.items(), key=lambda x: x[1], reverse=True)

        recommendations = []
        for drug, score in ranked[:5]:
            recommendations.append({
                "drug": drug,
                "predicted_response_score": round(float(score), 3),
                "category": "Likely responsive" if score > 0.6 else "Low response",
            })

        section: Dict[str, Any] = {
            "treatment_recommendations": recommendations,
        }

        if "recommended_regimen" in treatment:
            section["primary_regimen"] = treatment["recommended_regimen"]

        return section

    def _uncertainty_section(self, info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "model_confidence": info.get("confidence", 0.0),
            "predictive_entropy": info.get("entropy", 0.0),
            "epistemic_uncertainty": info.get("epistemic", 0.0),
            "aleatoric_uncertainty": info.get("aleatoric", 0.0),
            "conformal_set_size": info.get("set_size", None),
            "calibration_ece": info.get("ece", None),
            "interpretation": self._interpret_uncertainty(info),
        }

    def _interpret_uncertainty(self, info: Dict[str, Any]) -> str:
        conf = info.get("confidence", 0.0)
        if conf >= self.cfg.confidence_threshold:
            return "Model confidence is HIGH. Predictions are reliable."
        elif conf >= 0.6:
            return ("Model confidence is MODERATE. Results should be "
                    "interpreted with caution and correlated with clinical findings.")
        else:
            return ("Model confidence is LOW. Predictions may be unreliable. "
                    "Consider additional testing or expert review.")

    def _twin_section(self, twin: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "projection_horizon": twin.get("horizon", "5 years"),
            "current_state": twin.get("current_state", {}),
            "one_year_outlook": twin.get("one_year_outlook", {}),
            "risk_windows": twin.get("risk_windows", []),
            "recommended_monitoring": twin.get("monitoring", {}),
        }

    def _conclusion(self, report: Dict[str, Any]) -> str:
        """Generate natural-language conclusion paragraph."""
        parts = []

        histopath = report.get("histopathology", {})
        if histopath.get("tumour_type"):
            parts.append(f"Diagnosis: {histopath['tumour_type']}.")

        mol = report.get("molecular_profile", {})
        if mol.get("molecular_subtype"):
            parts.append(f"Molecular subtype: {mol['molecular_subtype']}.")

        risk = report.get("risk_assessment", {})
        if risk.get("recurrence_risk_category"):
            parts.append(
                f"Recurrence risk: {risk['recurrence_risk_category']} "
                f"(score {risk.get('recurrence_risk_score', 'N/A')})."
            )

        unc = report.get("uncertainty", {})
        if unc.get("interpretation"):
            parts.append(unc["interpretation"])

        return " ".join(parts) if parts else "Report generated successfully."

    def _disclaimer(self) -> str:
        return (
            "DISCLAIMER: This report was generated by an AI-assisted pathology "
            "system and is intended to support — not replace — clinical decision-making. "
            "All findings should be reviewed by a qualified pathologist and correlated "
            "with clinical and radiological data before any treatment decisions."
        )


# ===================================================================
# Report Formatters
# ===================================================================

class MarkdownFormatter:
    """Render a structured report as Markdown."""

    @staticmethod
    def render(report: Dict[str, Any]) -> str:
        lines: list[str] = []
        meta = report.get("metadata", {})

        lines.append(f"# {meta.get('institution', 'Pathology Report')}")
        lines.append(f"**Report Type:** {meta.get('report_type', 'AI Report')}")
        lines.append(f"**Generated:** {meta.get('generated_at', '')}")
        lines.append(f"**Specimen:** {meta.get('specimen_id', '')}")
        lines.append("")

        # Patient
        pt = report.get("patient", {})
        if pt:
            lines.append("## Patient Information")
            for k, v in pt.items():
                if v is not None:
                    lines.append(f"- **{_human_key(k)}:** {v}")
            lines.append("")

        # Histopathology
        hist = report.get("histopathology", {})
        if hist:
            lines.append("## Histopathology Findings")
            for k, v in hist.items():
                if k != "all_subtype_probabilities" and v:
                    lines.append(f"- **{_human_key(k)}:** {v}")
            probs = hist.get("all_subtype_probabilities", {})
            if probs and isinstance(probs, dict):
                lines.append("\n**Subtype Probabilities:**\n")
                lines.append("| Subtype | Probability |")
                lines.append("|---------|-------------|")
                for sub, p in sorted(probs.items(), key=lambda x: -x[1]):
                    lines.append(f"| {sub} | {p:.3f} |")
            lines.append("")

        # Molecular profile
        mol = report.get("molecular_profile", {})
        if mol:
            lines.append("## Molecular Profile")
            for k, v in mol.items():
                if v is not None:
                    lines.append(f"- **{_human_key(k)}:** {v}")
            lines.append("")

        # Risk assessment
        risk = report.get("risk_assessment", {})
        if risk:
            lines.append("## Risk Assessment")
            for k, v in risk.items():
                lines.append(f"- **{_human_key(k)}:** {v}")
            lines.append("")

        # Treatment
        tx = report.get("treatment", {})
        if tx:
            lines.append("## Treatment Considerations")
            recs = tx.get("treatment_recommendations", [])
            if recs:
                lines.append("\n| Drug | Response Score | Category |")
                lines.append("|------|---------------|----------|")
                for r in recs:
                    lines.append(
                        f"| {r['drug']} | {r['predicted_response_score']} | {r['category']} |"
                    )
            if tx.get("primary_regimen"):
                lines.append(f"\n**Primary Regimen:** {tx['primary_regimen']}")
            lines.append("")

        # Uncertainty
        unc = report.get("uncertainty", {})
        if unc:
            lines.append("## Model Confidence & Uncertainty")
            for k, v in unc.items():
                if v is not None:
                    lines.append(f"- **{_human_key(k)}:** {v}")
            lines.append("")

        # Digital twin
        proj = report.get("longitudinal_projection", {})
        if proj:
            lines.append("## Longitudinal Projection (Digital Twin)")
            for k, v in proj.items():
                lines.append(f"- **{_human_key(k)}:** {v}")
            lines.append("")

        # Conclusion
        if report.get("conclusion"):
            lines.append("## Conclusion")
            lines.append(report["conclusion"])
            lines.append("")

        # Disclaimer
        if report.get("disclaimer"):
            lines.append("---")
            lines.append(f"*{report['disclaimer']}*")

        return "\n".join(lines)


class HTMLFormatter:
    """Render a structured report as standalone HTML."""

    @staticmethod
    def render(report: Dict[str, Any]) -> str:
        md = MarkdownFormatter.render(report)
        # Minimal HTML wrapping — real deployment would use a template engine
        html_body = md.replace("\n", "<br>\n")
        # Convert markdown headers
        html_body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html_body, flags=re.MULTILINE)
        html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
        html_body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html_body)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Clinical Pathology Report</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
  h1 {{ color: #1a365d; border-bottom: 2px solid #2b6cb0; padding-bottom: 0.3rem; }}
  h2 {{ color: #2b6cb0; margin-top: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0; }}
  th, td {{ border: 1px solid #cbd5e0; padding: 0.4rem 0.8rem; text-align: left; }}
  th {{ background: #ebf4ff; }}
  em {{ color: #718096; font-size: 0.9rem; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""


class FHIRFormatter:
    """Generate HL7 FHIR DiagnosticReport-compatible JSON."""

    @staticmethod
    def render(report: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a FHIR R4 DiagnosticReport resource."""
        meta = report.get("metadata", {})
        pt = report.get("patient", {})
        hist = report.get("histopathology", {})
        mol = report.get("molecular_profile", {})

        observations = []

        # Subtype observation
        if hist.get("predicted_subtype"):
            observations.append({
                "resourceType": "Observation",
                "status": "final",
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "85337-4",
                        "display": "Breast cancer molecular subtype",
                    }]
                },
                "valueCodeableConcept": {
                    "text": hist["predicted_subtype"],
                },
                "reliability": hist.get("subtype_confidence", 0),
            })

        # ER/PR/HER2
        for marker, loinc, display in [
            ("er_status", "85310-1", "Estrogen receptor status"),
            ("pr_status", "85311-9", "Progesterone receptor status"),
            ("her2_ihc_score", "85319-2", "HER2 IHC score"),
        ]:
            if mol.get(marker):
                observations.append({
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": display}]},
                    "valueString": str(mol[marker]),
                })

        fhir = {
            "resourceType": "DiagnosticReport",
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "PAT",
                    "display": "Pathology",
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "60568-3",
                    "display": "Pathology Synoptic report",
                }]
            },
            "subject": {"reference": f"Patient/{pt.get('patient_id', 'unknown')}"},
            "effectiveDateTime": meta.get("generated_at", ""),
            "conclusion": report.get("conclusion", ""),
            "result": [{"reference": f"#obs-{i}"} for i in range(len(observations))],
            "contained": observations,
        }

        return fhir


# ===================================================================
# Convenience
# ===================================================================

def _human_key(key: str) -> str:
    """Convert snake_case to Title Case."""
    return key.replace("_", " ").title()


def generate_report(
    patient: PatientInfo,
    model_outputs: Dict[str, Any],
    digital_twin_summary: Optional[Dict[str, Any]] = None,
    uncertainty_info: Optional[Dict[str, Any]] = None,
    cfg: ReportConfig = ReportConfig(),
    fmt: str = "markdown",
) -> str:
    """One-call convenience to generate a formatted clinical report.

    Parameters
    ----------
    fmt : "markdown" | "html" | "fhir" | "json"
    """
    builder = ClinicalReportBuilder(cfg)
    report = builder.build_report(
        patient, model_outputs, digital_twin_summary, uncertainty_info
    )

    if fmt == "markdown":
        return MarkdownFormatter.render(report)
    elif fmt == "html":
        return HTMLFormatter.render(report)
    elif fmt == "fhir":
        return json.dumps(FHIRFormatter.render(report), indent=2)
    else:
        return json.dumps(report, indent=2, default=str)
