"""Dataset package — public data loaders for TissueShift."""

from tissueshift.datasets.tcga_brca import TCGABRCADataset
from tissueshift.datasets.cptac_brca import CPTACBRCADataset
from tissueshift.datasets.hpa import HPADataset
from tissueshift.datasets.htan import HTANDataset, HTANMetastaticDataset
from tissueshift.datasets.geo_progression import GEOProgressionDataset
from tissueshift.datasets.multimodal import MultimodalTissueDataset
from tissueshift.datasets.progression_pairs import ProgressionPairsDataset

__all__ = [
    "TCGABRCADataset",
    "CPTACBRCADataset",
    "HPADataset",
    "HTANDataset",
    "HTANMetastaticDataset",
    "GEOProgressionDataset",
    "MultimodalTissueDataset",
    "ProgressionPairsDataset",
]
