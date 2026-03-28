"""
TissueShift — Breast Cancer Tissue Evolution Atlas

Interactive Streamlit application that visualises:
  1. Whole-slide H&E pathology with region annotations
  2. The TissueShift manifold with patient trajectories
  3. Molecular evidence panels and pathway localisation
  4. Subtype River: temporal ribbon showing subtype drift
  5. Microenvironment remodelling scores
  6. Benchmark comparison dashboard

Design ethos: beauty reveals biology.  Clean ivory backgrounds,
stain-faithful pathology imagery, restrained accent colours tied
to biological axes, and flowing trajectories instead of chunky
dashboard blocks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Defer Streamlit import to allow module import without Streamlit installed
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


# ======================================================================
# Colour system — stain-faithful palette
# ======================================================================
TISSUE_SHIFT_PALETTE = {
    "luminal_A": "#4A90D9",       # Calm blue — stable luminal
    "luminal_B": "#7B68EE",       # Medium purple — proliferative luminal
    "luminal_B_her2pos": "#9370DB", # Muted violet
    "her2_enriched": "#E8596C",   # Warm rose — amplified
    "basal_like": "#D4442A",      # Deep red-orange — aggressive
    "normal_like": "#8FBC8F",     # Sage green — normal-adjacent
    "claudin_low": "#8B4513",     # Sienna — mesenchymal

    # UI colours
    "background": "#FFFFF5",      # Warm ivory
    "surface": "#FBF9F4",         # Light parchment
    "text": "#2D2926",            # Dark warm grey
    "text_secondary": "#6B6560",
    "accent": "#B88E6F",          # Warm taupe accent
    "border": "#E6E0D8",

    # Axis colours
    "lineage": "#4A90D9",
    "proliferative": "#E8596C",
    "her2_signal": "#FF7F50",
    "basal_emt": "#D4442A",
    "immune": "#3CB371",
    "stromal": "#DAA520",
    "instability": "#808080",
    "uncertainty": "#C0C0C0",
}

SUBTYPE_COLORS = {k: v for k, v in TISSUE_SHIFT_PALETTE.items()
                  if k in ["luminal_A", "luminal_B", "luminal_B_her2pos",
                           "her2_enriched", "basal_like", "normal_like", "claudin_low"]}


# ======================================================================
# Manifold visualisation
# ======================================================================
def compute_manifold_embedding(
    tissue_states: np.ndarray,
    method: str = "umap",
    n_components: int = 2,
) -> np.ndarray:
    """
    Reduce tissue-state latent vectors to 2D/3D for visualisation.
    """
    if method == "umap":
        try:
            import umap
            reducer = umap.UMAP(n_components=n_components, random_state=42, n_neighbors=15)
            return reducer.fit_transform(tissue_states)
        except ImportError:
            logger.warning("umap-learn not installed, falling back to PCA")
            method = "pca"

    if method == "phate":
        try:
            import phate
            reducer = phate.PHATE(n_components=n_components, random_state=42)
            return reducer.fit_transform(tissue_states)
        except ImportError:
            logger.warning("phate not installed, falling back to PCA")
            method = "pca"

    # Fallback: PCA
    from sklearn.decomposition import PCA
    return PCA(n_components=n_components, random_state=42).fit_transform(tissue_states)


def plot_manifold(
    coords_2d: np.ndarray,
    labels: np.ndarray,
    title: str = "TissueShift Manifold",
    trajectories: Optional[List[np.ndarray]] = None,
    confidence: Optional[np.ndarray] = None,
):
    """
    Plot the tissue-state manifold with Plotly.

    Points are coloured by subtype, sized by confidence.
    Trajectories are drawn as ribbons connecting timepoints.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        logger.warning("plotly not installed — cannot render manifold")
        return None

    fig = go.Figure()

    # Determine unique labels (limited to known subtypes for colouring)
    unique_labels = sorted(set(labels))

    for label in unique_labels:
        mask = labels == label
        colour = SUBTYPE_COLORS.get(label, "#888888")
        size = 8
        if confidence is not None:
            size = 4 + confidence[mask] * 12

        fig.add_trace(go.Scatter(
            x=coords_2d[mask, 0],
            y=coords_2d[mask, 1],
            mode="markers",
            name=str(label).replace("_", " ").title(),
            marker=dict(
                color=colour,
                size=size,
                opacity=0.75,
                line=dict(width=0.5, color="white"),
            ),
            hovertemplate=f"<b>{label}</b><br>x: %{{x:.2f}}<br>y: %{{y:.2f}}<extra></extra>",
        ))

    # Trajectories (Subtype River ribbons)
    if trajectories:
        for traj in trajectories:
            if len(traj) < 2:
                continue
            fig.add_trace(go.Scatter(
                x=traj[:, 0],
                y=traj[:, 1],
                mode="lines+markers",
                line=dict(width=2, color=TISSUE_SHIFT_PALETTE["accent"]),
                marker=dict(size=6, color=TISSUE_SHIFT_PALETTE["text"]),
                showlegend=False,
                hoverinfo="skip",
            ))
            # Arrow at end
            fig.add_annotation(
                x=traj[-1, 0], y=traj[-1, 1],
                ax=traj[-2, 0], ay=traj[-2, 1],
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.5,
                arrowcolor=TISSUE_SHIFT_PALETTE["text"],
            )

    fig.update_layout(
        title=dict(text=title, font=dict(size=20, family="Georgia, serif")),
        paper_bgcolor=TISSUE_SHIFT_PALETTE["background"],
        plot_bgcolor=TISSUE_SHIFT_PALETTE["surface"],
        font=dict(family="Georgia, serif", color=TISSUE_SHIFT_PALETTE["text"]),
        xaxis=dict(showgrid=False, zeroline=False, title="Manifold Dimension 1"),
        yaxis=dict(showgrid=False, zeroline=False, title="Manifold Dimension 2"),
        legend=dict(
            bgcolor="rgba(255,255,245,0.8)",
            bordercolor=TISSUE_SHIFT_PALETTE["border"],
            borderwidth=1,
        ),
        width=900,
        height=650,
    )
    return fig


# ======================================================================
# Subtype River — signature feature
# ======================================================================
def plot_subtype_river(
    timepoints: List[str],
    subtype_probs: np.ndarray,
    patient_id: str = "",
):
    """
    The Subtype River: a stacked-area ribbon showing how subtype
    probabilities change across timepoints for one patient.

    subtype_probs : (T, num_subtypes) — probabilities at each timepoint.
    timepoints : list of timepoint labels (e.g., "Biopsy 1", "Surgery", "Met").
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    subtype_names = list(SUBTYPE_COLORS.keys())
    T, S = subtype_probs.shape

    fig = go.Figure()
    for s_idx in range(min(S, len(subtype_names))):
        name = subtype_names[s_idx]
        fig.add_trace(go.Scatter(
            x=timepoints,
            y=subtype_probs[:, s_idx],
            mode="lines",
            name=name.replace("_", " ").title(),
            line=dict(width=0.5, color=SUBTYPE_COLORS.get(name, "#888")),
            fill="tonexty" if s_idx > 0 else "tozeroy",
            fillcolor=SUBTYPE_COLORS.get(name, "#888") + "60",  # semi-transparent
            stackgroup="one",
        ))

    title_text = f"Subtype River — {patient_id}" if patient_id else "Subtype River"
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=18, family="Georgia, serif")),
        paper_bgcolor=TISSUE_SHIFT_PALETTE["background"],
        plot_bgcolor=TISSUE_SHIFT_PALETTE["surface"],
        font=dict(family="Georgia, serif", color=TISSUE_SHIFT_PALETTE["text"]),
        xaxis=dict(title="Disease Timeline"),
        yaxis=dict(title="Subtype Probability", range=[0, 1]),
        legend=dict(
            bgcolor="rgba(255,255,245,0.8)",
            bordercolor=TISSUE_SHIFT_PALETTE["border"],
        ),
        width=900,
        height=400,
    )
    return fig


# ======================================================================
# Tissue axis radar chart
# ======================================================================
def plot_tissue_axes(axes: Dict[str, float], title: str = "Tissue State Axes"):
    """Radar chart of the 8 interpretable tissue-state axes."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    axis_names = list(axes.keys())
    values = [axes[n] for n in axis_names]
    values.append(values[0])  # close the polygon
    axis_names.append(axis_names[0])

    ax_colours = [
        TISSUE_SHIFT_PALETTE.get(n.split("_")[0], "#888") for n in axis_names
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=[n.replace("_", " ").title() for n in axis_names],
        fill="toself",
        fillcolor=TISSUE_SHIFT_PALETTE["accent"] + "30",
        line=dict(color=TISSUE_SHIFT_PALETTE["accent"], width=2),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, family="Georgia, serif")),
        polar=dict(
            bgcolor=TISSUE_SHIFT_PALETTE["surface"],
            radialaxis=dict(visible=True, range=[0, 1]),
        ),
        paper_bgcolor=TISSUE_SHIFT_PALETTE["background"],
        font=dict(family="Georgia, serif", color=TISSUE_SHIFT_PALETTE["text"]),
        showlegend=False,
        width=500,
        height=500,
    )
    return fig


# ======================================================================
# Streamlit main app
# ======================================================================
def run_app():
    """Launch the TissueShift interactive atlas."""
    if not HAS_STREAMLIT:
        print("Streamlit is required: pip install streamlit")
        return

    st.set_page_config(
        page_title="TissueShift — Breast Cancer Tissue Evolution Atlas",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for the TissueShift aesthetic
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {TISSUE_SHIFT_PALETTE["background"]};
        font-family: 'Georgia', serif;
    }}
    .stSidebar {{
        background-color: {TISSUE_SHIFT_PALETTE["surface"]};
    }}
    h1, h2, h3 {{
        color: {TISSUE_SHIFT_PALETTE["text"]};
        font-family: 'Georgia', serif;
    }}
    .metric-card {{
        background: {TISSUE_SHIFT_PALETTE["surface"]};
        border: 1px solid {TISSUE_SHIFT_PALETTE["border"]};
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ---- Sidebar ----
    with st.sidebar:
        st.markdown("# 🧬 TissueShift")
        st.markdown("*Breast Cancer Tissue Evolution Atlas*")
        st.divider()

        page = st.radio("Navigate", [
            "🏠 Overview",
            "🔬 Patient Explorer",
            "🌊 Subtype River",
            "🗺️ Tissue Manifold",
            "🧪 Molecular Bridge",
            "📊 Benchmarks",
            "📋 Data Sources",
        ])

    # ---- Pages ----
    if "Overview" in page:
        _page_overview()
    elif "Patient Explorer" in page:
        _page_patient_explorer()
    elif "Subtype River" in page:
        _page_subtype_river()
    elif "Tissue Manifold" in page:
        _page_manifold()
    elif "Molecular Bridge" in page:
        _page_molecular_bridge()
    elif "Benchmarks" in page:
        _page_benchmarks()
    elif "Data Sources" in page:
        _page_data_sources()


# ======================================================================
# Page implementations
# ======================================================================
def _page_overview():
    st.markdown("# TissueShift")
    st.markdown("### Open Temporal Histopathology-to-Omics Model for Subtype Emergence and Progression in Breast Cancer")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="metric-card">
        <h3>🔬 Current State Engine</h3>
        <p>Reads H&E morphology + molecular context to estimate
        the tumour's present tissue identity.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
        <h3>🌊 Drift Engine</h3>
        <p>Predicts whether the tissue will remain stable, drift
        within lineage, or shift toward a different subtype.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="metric-card">
        <h3>🧪 Molecule Bridge</h3>
        <p>Links tissue regions to pathway activity and shows
        which molecular programmes are being expressed.</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### How it works")
    st.markdown("""
    TissueShift fuses **histopathology**, **spatial microenvironment**,
    **transcriptomic** and **proteomic** signals, and **longitudinal clinical context**
    into a shared latent tissue manifold, then predicts:

    1. **Subtype state** — current and probability distribution
    2. **Subtype drift** — stability vs. movement toward a different neighbourhood
    3. **Progression stage** — pre-invasive to metastatic-adapted
    4. **Morphology-to-molecule translation** — what the tissue is expressing
    5. **Microenvironment remodelling** — invasion/immune-evasion readiness
    6. **Time-aware risk** — survival and relapse proxy
    """)


def _page_patient_explorer():
    st.markdown("# 🔬 Patient Explorer")
    st.markdown("*Select a patient to explore their tissue evolution.*")

    # Demo patient selector
    demo_patients = ["TCGA-A1-A0SK", "TCGA-A2-A04P", "TCGA-BH-A0B3", "CPTAC-BR-001"]
    patient = st.selectbox("Patient ID", demo_patients)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Whole-Slide Image")
        st.info("🔬 Slide viewer loads when real data is available. "
                "Connect TCGA/CPTAC slides via the data manifest.")

    with col2:
        st.markdown("### Tissue State Axes")
        # Demo axes
        demo_axes = {
            "lineage_identity": 0.85,
            "proliferative_pressure": 0.45,
            "her2_signaling": 0.2,
            "basal_mesenchymal": 0.1,
            "immune_activation": 0.55,
            "stromal_permissiveness": 0.35,
            "clonal_instability": 0.25,
            "uncertainty": 0.15,
        }
        fig = plot_tissue_axes(demo_axes, f"Tissue State — {patient}")
        if fig:
            st.plotly_chart(fig, use_container_width=True)


def _page_subtype_river():
    st.markdown("# 🌊 Subtype River")
    st.markdown("*Watch how subtype identity flows through time.*")

    # Demo data
    np.random.seed(42)
    timepoints = ["DCIS Biopsy", "Excision", "1-yr Follow-up", "Recurrence", "Metastatic"]
    T = len(timepoints)
    probs = np.random.dirichlet(np.ones(7) * 2, size=T)
    # Make it look like Luminal A drifting to Luminal B then Her2
    probs[0] = [0.65, 0.15, 0.05, 0.05, 0.03, 0.05, 0.02]
    probs[1] = [0.50, 0.25, 0.08, 0.07, 0.03, 0.05, 0.02]
    probs[2] = [0.35, 0.35, 0.12, 0.08, 0.03, 0.05, 0.02]
    probs[3] = [0.20, 0.30, 0.25, 0.12, 0.05, 0.05, 0.03]
    probs[4] = [0.10, 0.20, 0.35, 0.20, 0.05, 0.05, 0.05]

    fig = plot_subtype_river(timepoints, probs, "DEMO-001")
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    > The ribbon thickens or narrows with confidence. Each point sits
    > on the TissueShift manifold. Clicking a point opens the corresponding
    > H&E morphology, pathway activity, and microenvironment summary.
    """)


def _page_manifold():
    st.markdown("# 🗺️ Tissue Manifold")
    st.markdown("*Explore the shared latent tissue-state space.*")

    method = st.selectbox("Reduction method", ["UMAP", "PCA", "PHATE"])

    # Generate demo embedding
    np.random.seed(42)
    n = 500
    subtypes = np.random.choice(list(SUBTYPE_COLORS.keys()), n, p=[0.3, 0.25, 0.1, 0.15, 0.1, 0.05, 0.05])
    latent = np.random.randn(n, 8) * 0.5
    # Cluster by subtype
    for i, st_name in enumerate(SUBTYPE_COLORS.keys()):
        mask = subtypes == st_name
        latent[mask] += np.array([i * 0.8, (i % 3) * 0.6, 0, 0, 0, 0, 0, 0])

    coords = compute_manifold_embedding(latent, method.lower())

    # Demo trajectories
    traj1 = coords[subtypes == "luminal_A"][:5]
    trajectories = [traj1] if len(traj1) >= 2 else None

    fig = plot_manifold(coords, subtypes, "TissueShift Breast Cancer Manifold", trajectories)
    if fig:
        st.plotly_chart(fig, use_container_width=True)


def _page_molecular_bridge():
    st.markdown("# 🧪 Morphology-to-Molecule Bridge")
    st.markdown("*See what the tissue is expressing.*")

    st.markdown("""
    The Morphology-to-Molecule Bridge predicts which pathways, markers,
    and latent programmes are being expressed by what the pathologist sees,
    then shows exactly which tissue regions appear to correspond to those programmes.

    **Key pathways predicted:**
    - Hallmark Estrogen Response Early/Late
    - Hallmark E2F Targets (proliferation)
    - Hallmark EMT (epithelial–mesenchymal transition)
    - Hallmark Inflammatory Response
    - Hallmark Angiogenesis
    - HER2/ERBB2 signalling
    """)

    # Demo pathway bars
    pathways = ["ER Response", "E2F Targets", "EMT", "Inflammation", "Angiogenesis", "ERBB2"]
    scores = [0.82, 0.45, 0.15, 0.55, 0.30, 0.18]

    try:
        import plotly.graph_objects as go
        fig = go.Figure(go.Bar(
            x=scores,
            y=pathways,
            orientation="h",
            marker_color=[TISSUE_SHIFT_PALETTE["lineage"],
                         TISSUE_SHIFT_PALETTE["proliferative"],
                         TISSUE_SHIFT_PALETTE["basal_emt"],
                         TISSUE_SHIFT_PALETTE["immune"],
                         TISSUE_SHIFT_PALETTE["stromal"],
                         TISSUE_SHIFT_PALETTE["her2_signal"]],
        ))
        fig.update_layout(
            title="Predicted Pathway Activity",
            paper_bgcolor=TISSUE_SHIFT_PALETTE["background"],
            plot_bgcolor=TISSUE_SHIFT_PALETTE["surface"],
            font=dict(family="Georgia, serif"),
            xaxis=dict(title="Activity Score", range=[0, 1]),
            width=700,
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("Install plotly for interactive charts: pip install plotly")


def _page_benchmarks():
    st.markdown("# 📊 Benchmarks")
    st.markdown("*Four-layer evaluation protocol.*")

    st.markdown("""
    | Layer | Task | Cohorts | Key Metrics |
    |-------|------|---------|-------------|
    | 1 | Static Subtype | TCGA-BRCA, CPTAC-BRCA | Accuracy, Balanced Acc, Macro F1, AUC, ECE |
    | 2 | Progression Stage | GEO DCIS→invasive, Spatial DCIS atlas | Accuracy, Macro F1, Stage Confusion |
    | 3 | Metastatic Drift | Paired primary–met (AURORA potential) | Drift Acc, C-index, Time-dep AUC |
    | 4 | Spatial Phenotype | HTAN Metastatic Breast Atlas | Silhouette, NMI, Region F1 |
    """)


def _page_data_sources():
    st.markdown("# 📋 Data Sources")
    st.markdown("*Public-data-first. Honest about access tiers.*")

    sources = [
        ("TCGA-BRCA (IDC)", "1,098 subjects", "Open", "Clinical, genomic, histopathology, nuclei segmentations, TIL maps"),
        ("CPTAC-BRCA (IDC/TCIA)", "198 subjects", "Open", "Proteogenomics + pathology + imaging"),
        ("Human Protein Atlas", "Millions of images", "Open", "Cancer IHC images, mRNA expression, survival"),
        ("HTAN (Synapse/IDC)", "Varies by atlas", "Open (L3/L4) + CC BY 4.0 imaging", "Spatial, scRNA-seq, imaging"),
        ("HTAN Metastatic Breast", "67 biopsies / 60 patients", "Open processed", "H&E + sc/snRNA-seq + 4 spatial assays"),
        ("GEO DCIS Progression", "GSE214093/94", "Open", "DCIS→invasive expression"),
        ("AURORA US (GEO)", "Public molecular series", "Open/semi-open", "Paired primary–met molecular"),
        ("AURORA Manuscript", "617 samples / 371 patients", "Currently restricted", "Ideal for drift — architect for later"),
    ]

    for name, size, access, desc in sources:
        with st.expander(f"**{name}** — {size}"):
            st.markdown(f"**Access:** {access}")
            st.markdown(f"**Contents:** {desc}")


# ======================================================================
# Entry point
# ======================================================================
if __name__ == "__main__":
    run_app()
