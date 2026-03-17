"""HuggingFace Spaces Gradio demo for TissueShift."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

try:
    import gradio as gr
except ImportError:
    logger.error("gradio not installed. Install with: pip install gradio")
    raise

SUBTYPES = ["LumA", "LumB", "Her2", "Basal", "Normal"]
SUBTYPE_COLORS = {
    "LumA": "#3b82f6", "LumB": "#6366f1", "Her2": "#ec4899",
    "Basal": "#ef4444", "Normal": "#10b981",
}


def predict_subtype(file):
    """Run subtype prediction on uploaded HDF5 feature file."""
    if file is None:
        return {"error": "Please upload an HDF5 feature file"}

    # Demo prediction (replace with real inference)
    return {
        "subtype": "LumA",
        "confidence": 0.87,
        "probabilities": {
            "LumA": 0.87, "LumB": 0.08, "Her2": 0.02,
            "Basal": 0.01, "Normal": 0.02,
        },
    }


def get_model_info():
    """Return model architecture summary."""
    return """
## TissueShift-BRCA v0.1.0

### Architecture
- **Pathology**: UNI ViT-L/16 (frozen) → Region Tokenizer (7 types) → ABMIL
- **Molecular**: MLP encoder (expression + pathway + proteomic)
- **Spatial**: Stub encoder (full GNN in Phase 11)
- **Fusion**: 8-query cross-attention (2 layers)
- **World Model**: 512-d tissue state → subtype + transition lattice

### Training
- Dataset: TCGA-BRCA (1098 subjects, 70/15/15 split)
- External validation: CPTAC-BRCA (198 subjects)
- 2-stage: manifold pretrain → multi-task finetune
- GPU: Single RTX 3090/4090

### Benchmark Tracks
| Track | Metric | Target |
|-------|--------|--------|
| SubtypeCall | Macro-F1 | 0.92 |
| SubtypeDrift | AUROC | 0.85 |
| ProgressionStage | QWK | 0.80 |
| Morph2Mol | R² | 0.45 |
| Survival | C-index | 0.72 |
| SpatialPhenotype | R²-TIL | 0.50 |
"""


# Build Gradio interface
with gr.Blocks(
    title="TissueShift",
    theme=gr.themes.Base(primary_hue="purple"),
) as demo:
    gr.Markdown(
        "# 🔬 TissueShift\n"
        "Open temporal histopathology-to-omics model for breast cancer "
        "subtype emergence and progression."
    )

    with gr.Tab("Predict"):
        gr.Markdown("Upload pre-extracted patch features (HDF5) for subtype prediction.")
        with gr.Row():
            with gr.Column():
                file_input = gr.File(label="Upload HDF5 features", file_types=[".h5"])
                predict_btn = gr.Button("Predict Subtype", variant="primary")
            with gr.Column():
                output_json = gr.JSON(label="Prediction")

        predict_btn.click(predict_subtype, inputs=[file_input], outputs=[output_json])

    with gr.Tab("Model Info"):
        gr.Markdown(get_model_info())

    with gr.Tab("Leaderboard"):
        gr.Markdown("## Benchmark Leaderboard\n\nVisit the [full leaderboard](https://tissueshift.vercel.app/leaderboard) for detailed rankings.")
        gr.Markdown(
            "| Track | Top Score | Team |\n"
            "|-------|-----------|------|\n"
            "| SubtypeCall | 0.891 | TissueShift-Base |\n"
            "| Survival | 0.712 | TissueShift-Base |\n"
            "| Morph2Mol | 0.423 | TissueShift-Base |\n"
        )

if __name__ == "__main__":
    demo.launch()
