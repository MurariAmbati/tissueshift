"""
TissueShift — Open Temporal Histopathology-to-Omics Model
for Subtype Emergence and Progression in Breast Cancer.

TissueShift models breast cancer as a changing tissue program observed
through H&E morphology, IHC-style marker signals, transcriptomics,
proteomics, and spatial context over time. Rather than treating subtype
as a fixed label, TissueShift learns how subtype identity emerges,
drifts, and hardens across disease progression.
"""

__version__ = "0.1.0"
__author__ = "TissueShift Team"

from tissueshift.config import TissueShiftConfig
from tissueshift.inference import InferencePipeline, TissueShiftPrediction
from tissueshift.tracking import ExperimentTracker
from tissueshift.interpretability import (
    AttentionVisualizer,
    GradientAttribution,
    LatentTraversal,
    AxisAttribution,
)

__all__ = [
    "TissueShiftConfig",
    "InferencePipeline",
    "TissueShiftPrediction",
    "ExperimentTracker",
    "AttentionVisualizer",
    "GradientAttribution",
    "LatentTraversal",
    "AxisAttribution",
]
