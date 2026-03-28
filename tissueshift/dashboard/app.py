"""TissueShift Clinical Dashboard — Main Streamlit Entry-Point.

Launch with:
    streamlit run tissueshift/dashboard/app.py
"""

from __future__ import annotations

import streamlit as st

# ── Page config (must be first Streamlit call) ──────────────────────
st.set_page_config(
    page_title="TissueShift — Clinical AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Navigation ──────────────────────────────────────────────────────
from tissueshift.dashboard.pages import (
    page_home,
    page_patient_intake,
    page_slide_analysis,
    page_patient_timeline,
    page_digital_twin,
    page_treatment_comparison,
    page_uncertainty,
    page_cohort_analytics,
    page_biomarker_explorer,
    page_knowledge_graph,
    page_federated_status,
    page_report_generator,
    page_settings,
)

PAGES = {
    "🏠 Home": page_home.render,
    "📋 Patient Intake": page_patient_intake.render,
    "🔬 Slide Analysis": page_slide_analysis.render,
    "📅 Patient Timeline": page_patient_timeline.render,
    "🧬 Digital Twin": page_digital_twin.render,
    "💊 Treatment Comparison": page_treatment_comparison.render,
    "📊 Uncertainty & Confidence": page_uncertainty.render,
    "👥 Cohort Analytics": page_cohort_analytics.render,
    "🧪 Biomarker Explorer": page_biomarker_explorer.render,
    "🕸️ Knowledge Graph": page_knowledge_graph.render,
    "🌐 Federated Status": page_federated_status.render,
    "📄 Report Generator": page_report_generator.render,
    "⚙️ Settings": page_settings.render,
}


def main() -> None:
    # ── Sidebar ─────────────────────────────────────────────────────
    with st.sidebar:
        st.image(
            "https://via.placeholder.com/200x60?text=TissueShift",
            use_container_width=True,
        )
        st.markdown("### Navigation")
        selection = st.radio(
            "Go to", list(PAGES.keys()), label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown(
            "<small>TissueShift v2.0 — AI-Assisted Pathology<br>"
            "For research & clinical decision support</small>",
            unsafe_allow_html=True,
        )

    # ── Render selected page ────────────────────────────────────────
    PAGES[selection]()


if __name__ == "__main__":
    main()
