"""
Central configuration for TissueShift.

Defines all hyper-parameters, paths, model dimensions, and training
settings used throughout the project.  Every module imports from here
so there is one source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _env_or(key: str, default: str) -> str:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# Data configuration
# ---------------------------------------------------------------------------
@dataclass
class DataConfig:
    """Paths and parameters for public data sources."""

    data_root: Path = Path(_env_or("TISSUESHIFT_DATA", str(_PROJECT_ROOT / "data")))

    # TCGA-BRCA  (IDC manifest)
    tcga_brca_manifest: Path = data_root / "manifests" / "tcga_brca_idc.csv"
    tcga_brca_slides_dir: Path = data_root / "tcga_brca" / "slides"
    tcga_brca_clinical: Path = data_root / "tcga_brca" / "clinical.tsv"
    tcga_brca_rna: Path = data_root / "tcga_brca" / "rnaseq.tsv"
    tcga_brca_cnv: Path = data_root / "tcga_brca" / "cnv.tsv"

    # CPTAC-BRCA  (IDC / TCIA)
    cptac_brca_slides_dir: Path = data_root / "cptac_brca" / "slides"
    cptac_brca_clinical: Path = data_root / "cptac_brca" / "clinical.tsv"
    cptac_brca_proteomics: Path = data_root / "cptac_brca" / "proteomics.tsv"
    cptac_brca_rna: Path = data_root / "cptac_brca" / "rnaseq.tsv"

    # Human Protein Atlas
    hpa_images_dir: Path = data_root / "hpa" / "images"
    hpa_cancer_expression: Path = data_root / "hpa" / "pathology.tsv"
    hpa_survival: Path = data_root / "hpa" / "survival.tsv"

    # HTAN  (Synapse open processed + IDC imaging)
    htan_processed_dir: Path = data_root / "htan" / "processed"
    htan_imaging_dir: Path = data_root / "htan" / "imaging"
    htan_spatial_dir: Path = data_root / "htan" / "spatial"
    htan_metastatic_dir: Path = data_root / "htan" / "metastatic_breast"

    # GEO progression cohorts
    geo_dcis_progression: Path = data_root / "geo" / "GSE214093"
    geo_aurora_public: Path = data_root / "geo" / "aurora_us"

    # Slide processing
    tile_size: int = 256
    tile_magnification: float = 20.0  # 20× objective
    tile_overlap: int = 0
    max_tiles_per_slide: int = 4096
    stain_norm_method: str = "macenko"  # macenko | vahadane | reinhard

    def __post_init__(self) -> None:
        if self.tile_size < 64 or self.tile_size > 1024:
            raise ValueError(f"tile_size must be 64–1024, got {self.tile_size}")
        if self.tile_magnification not in (5.0, 10.0, 20.0, 40.0):
            raise ValueError(f"tile_magnification must be 5/10/20/40, got {self.tile_magnification}")
        if self.max_tiles_per_slide < 1:
            raise ValueError("max_tiles_per_slide must be ≥ 1")
        if self.stain_norm_method not in ("macenko", "vahadane", "reinhard"):
            raise ValueError(f"Unknown stain_norm_method: {self.stain_norm_method}")

    # Region annotation vocabulary
    region_labels: Tuple[str, ...] = (
        "tumor_epithelium",
        "stroma",
        "necrosis",
        "immune_rich",
        "ductal_structure",
        "invasive_front",
        "lymphovascular",
        "adipose",
        "normal_epithelium",
        "background",
    )


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
@dataclass
class PathologyEncoderConfig:
    """Pathology vision backbone."""

    backbone: str = "uni"  # uni | ctranspath | resnet50_imagenet
    pretrained: bool = True
    patch_embed_dim: int = 1024
    region_embed_dim: int = 512
    num_region_classes: int = 10
    pool_strategy: str = "attention"  # attention | mean | max
    dropout: float = 0.1

    def __post_init__(self) -> None:
        if self.backbone not in ("uni", "ctranspath", "resnet50_imagenet"):
            raise ValueError(f"Unknown backbone: {self.backbone}")
        if self.pool_strategy not in ("attention", "mean", "max"):
            raise ValueError(f"Unknown pool_strategy: {self.pool_strategy}")
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError(f"dropout must be 0–1, got {self.dropout}")


@dataclass
class MolecularEncoderConfig:
    """RNA / protein / CNV tokenizer."""

    gene_vocab_size: int = 20_000
    gene_embed_dim: int = 256
    pathway_embed_dim: int = 256
    protein_embed_dim: int = 256
    cnv_embed_dim: int = 128
    fused_dim: int = 512
    num_pathways: int = 50  # Hallmark + curated
    dropout: float = 0.1
    num_attention_heads: int = 8
    num_transformer_layers: int = 4

    def __post_init__(self) -> None:
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError(f"dropout must be 0–1, got {self.dropout}")
        if self.num_attention_heads < 1:
            raise ValueError("num_attention_heads must be ≥ 1")
        if self.fused_dim % self.num_attention_heads != 0:
            raise ValueError("fused_dim must be divisible by num_attention_heads")


@dataclass
class SpatialEncoderConfig:
    """Cell-graph / neighborhood tokenizer."""

    node_feature_dim: int = 64
    edge_feature_dim: int = 32
    hidden_dim: int = 256
    output_dim: int = 256
    num_gnn_layers: int = 4
    gnn_type: str = "gatv2"  # gatv2 | graphsage | gin
    pool_strategy: str = "attention"
    dropout: float = 0.1
    max_cells_per_region: int = 2000
    neighborhood_radius_um: float = 50.0

    def __post_init__(self) -> None:
        if self.gnn_type not in ("gatv2", "graphsage", "gin"):
            raise ValueError(f"Unknown gnn_type: {self.gnn_type}")
        if self.pool_strategy not in ("attention", "mean", "max"):
            raise ValueError(f"Unknown pool_strategy: {self.pool_strategy}")
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError(f"dropout must be 0–1, got {self.dropout}")
        if self.neighborhood_radius_um <= 0:
            raise ValueError("neighborhood_radius_um must be > 0")


@dataclass
class TissueStateConfig:
    """Shared latent tissue-state manifold (world model)."""

    latent_dim: int = 128
    num_latent_axes: int = 8  # interpretable axes
    # Axes: lineage_identity, proliferative_pressure, her2_signaling,
    #        basal_mesenchymal, immune_activation, stromal_permissiveness,
    #        clonal_instability, uncertainty
    axis_names: Tuple[str, ...] = (
        "lineage_identity",
        "proliferative_pressure",
        "her2_signaling",
        "basal_mesenchymal",
        "immune_activation",
        "stromal_permissiveness",
        "clonal_instability",
        "uncertainty",
    )
    fusion_hidden_dim: int = 512
    fusion_num_layers: int = 3
    use_variational: bool = True  # VAE-style for uncertainty
    kl_weight: float = 0.001
    dropout: float = 0.1

    def __post_init__(self) -> None:
        if self.latent_dim < 8:
            raise ValueError(f"latent_dim must be ≥ 8, got {self.latent_dim}")
        if self.num_latent_axes > self.latent_dim:
            raise ValueError("num_latent_axes cannot exceed latent_dim")
        if len(self.axis_names) != self.num_latent_axes:
            raise ValueError(
                f"Expected {self.num_latent_axes} axis_names, got {len(self.axis_names)}"
            )
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError(f"dropout must be 0–1, got {self.dropout}")


@dataclass
class TransitionModelConfig:
    """Subtype lattice transition model."""

    # Subtype lattice nodes
    subtype_nodes: Tuple[str, ...] = (
        "luminal_A",
        "luminal_B",
        "luminal_B_her2pos",
        "her2_enriched",
        "basal_like",
        "normal_like",
        "claudin_low",
    )
    # Allowed edges (adjacency) — biologically motivated
    allowed_transitions: Tuple[Tuple[str, str], ...] = (
        ("luminal_A", "luminal_B"),
        ("luminal_B", "luminal_B_her2pos"),
        ("luminal_B", "her2_enriched"),
        ("luminal_B", "basal_like"),
        ("her2_enriched", "basal_like"),
        ("luminal_A", "normal_like"),
        ("basal_like", "claudin_low"),
    )
    transition_hidden_dim: int = 256
    num_transition_layers: int = 2
    use_time_encoding: bool = True
    max_time_horizon_days: int = 3650  # 10 years


@dataclass
class HeadConfig:
    """Prediction head dimensions."""

    subtype_classes: int = 7
    progression_stages: int = 5  # pre-invasive, invasive, locally_advanced, metastatic_adapted, ambiguous
    stage_names: Tuple[str, ...] = (
        "pre_invasive",
        "invasive",
        "locally_advanced",
        "metastatic_adapted",
        "ambiguous_intermediate",
    )
    mol_reconstruction_dim: int = 512
    microenv_score_dim: int = 64
    survival_num_intervals: int = 20
    hidden_dim: int = 256
    dropout: float = 0.1

    def __post_init__(self) -> None:
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError(f"dropout must be 0–1, got {self.dropout}")
        if self.subtype_classes < 2:
            raise ValueError("subtype_classes must be ≥ 2")
        if self.progression_stages < 2:
            raise ValueError("progression_stages must be ≥ 2")
        if len(self.stage_names) != self.progression_stages:
            raise ValueError(
                f"Expected {self.progression_stages} stage_names, got {len(self.stage_names)}"
            )
        if self.survival_num_intervals < 1:
            raise ValueError("survival_num_intervals must be ≥ 1")


# ---------------------------------------------------------------------------
# Training configuration
# ---------------------------------------------------------------------------
@dataclass
class TrainingConfig:
    """Training hyper-parameters per stage."""

    # Stage 1: histology encoder pretraining
    stage1_epochs: int = 50
    stage1_lr: float = 1e-4
    stage1_batch_size: int = 32

    # Stage 2: molecular encoder
    stage2_epochs: int = 40
    stage2_lr: float = 5e-4
    stage2_batch_size: int = 64

    # Stage 3: spatial encoder
    stage3_epochs: int = 30
    stage3_lr: float = 3e-4
    stage3_batch_size: int = 16

    # Stage 4: progression bridge (joint)
    stage4_epochs: int = 60
    stage4_lr: float = 1e-4
    stage4_batch_size: int = 16

    # Stage 5: transition model + drift heads
    stage5_epochs: int = 40
    stage5_lr: float = 5e-5
    stage5_batch_size: int = 16

    # Stage 6: calibration & robustness
    stage6_epochs: int = 20
    stage6_lr: float = 1e-5
    stage6_batch_size: int = 32

    # General
    optimizer: str = "adamw"
    weight_decay: float = 1e-2
    scheduler: str = "cosine"  # cosine | plateau | one_cycle
    warmup_epochs: int = 5
    grad_clip: float = 1.0
    mixed_precision: bool = True
    num_workers: int = 4
    seed: int = 42

    # Loss weights
    loss_subtype_w: float = 1.0
    loss_drift_w: float = 0.5
    loss_stage_w: float = 0.8
    loss_mol_recon_w: float = 0.3
    loss_microenv_w: float = 0.4
    loss_survival_w: float = 0.6
    loss_kl_w: float = 0.001

    # Checkpointing
    checkpoint_dir: Path = _PROJECT_ROOT / "checkpoints"
    log_dir: Path = _PROJECT_ROOT / "logs"
    save_top_k: int = 3
    early_stop_patience: int = 10

    def __post_init__(self) -> None:
        if self.optimizer not in ("adamw", "adam", "sgd"):
            raise ValueError(f"Unknown optimizer: {self.optimizer}")
        if self.scheduler not in ("cosine", "plateau", "one_cycle"):
            raise ValueError(f"Unknown scheduler: {self.scheduler}")
        if self.grad_clip < 0:
            raise ValueError("grad_clip must be ≥ 0")
        for stage_idx in range(1, 7):
            epochs = getattr(self, f"stage{stage_idx}_epochs")
            lr = getattr(self, f"stage{stage_idx}_lr")
            if epochs < 1:
                raise ValueError(f"stage{stage_idx}_epochs must be ≥ 1")
            if lr <= 0:
                raise ValueError(f"stage{stage_idx}_lr must be > 0")


# ---------------------------------------------------------------------------
# Evaluation configuration
# ---------------------------------------------------------------------------
@dataclass
class EvalConfig:
    """Evaluation and benchmark settings."""

    # Layer 1: Static subtype on TCGA/CPTAC
    static_metrics: Tuple[str, ...] = (
        "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1",
        "cohen_kappa", "auc_ovr", "calibration_ece",
    )
    # Layer 2: Progression stage (DCIS→invasive)
    progression_metrics: Tuple[str, ...] = (
        "accuracy", "macro_f1", "auc_ovr", "stage_confusion",
    )
    # Layer 3: Metastatic drift (paired primary–met)
    drift_metrics: Tuple[str, ...] = (
        "drift_accuracy", "concordance_primary_met",
        "c_index", "time_dependent_auc",
    )
    # Layer 4: Spatial phenotype consistency (HTAN)
    spatial_metrics: Tuple[str, ...] = (
        "silhouette_latent", "manifold_alignment",
        "spatial_cluster_nmi", "region_prediction_f1",
    )
    bootstrap_n: int = 1000
    confidence_level: float = 0.95
    stratify_by: Tuple[str, ...] = ("subtype", "stage", "race", "age_group")


# ---------------------------------------------------------------------------
# App / visualization configuration
# ---------------------------------------------------------------------------
@dataclass
class AppConfig:
    """Interactive atlas / demo settings."""

    host: str = "0.0.0.0"
    port: int = 8501
    title: str = "TissueShift — Breast Cancer Tissue Evolution Atlas"
    manifold_method: str = "umap"  # umap | tsne | phate
    manifold_n_components: int = 2
    river_smoothing: float = 0.3
    color_palette: str = "tissueshift"  # custom palette
    max_slides_in_memory: int = 10
    thumbnail_size: Tuple[int, int] = (512, 512)


# ---------------------------------------------------------------------------
# Master configuration
# ---------------------------------------------------------------------------
@dataclass
class TissueShiftConfig:
    """Root configuration object — one import, full access."""

    data: DataConfig = field(default_factory=DataConfig)
    pathology_encoder: PathologyEncoderConfig = field(default_factory=PathologyEncoderConfig)
    molecular_encoder: MolecularEncoderConfig = field(default_factory=MolecularEncoderConfig)
    spatial_encoder: SpatialEncoderConfig = field(default_factory=SpatialEncoderConfig)
    tissue_state: TissueStateConfig = field(default_factory=TissueStateConfig)
    transition: TransitionModelConfig = field(default_factory=TransitionModelConfig)
    heads: HeadConfig = field(default_factory=HeadConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)
    app: AppConfig = field(default_factory=AppConfig)

    def save(self, path: Path) -> None:
        """Persist config as YAML."""
        import yaml
        with open(path, "w") as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)

    @classmethod
    def from_yaml(cls, path: Path) -> "TissueShiftConfig":
        """Load config from YAML file."""
        import yaml
        with open(path) as f:
            raw = yaml.safe_load(f)
        cfg = cls()
        for section_name, section_dict in raw.items():
            if hasattr(cfg, section_name) and isinstance(section_dict, dict):
                section_obj = getattr(cfg, section_name)
                for k, v in section_dict.items():
                    if hasattr(section_obj, k):
                        setattr(section_obj, k, v)
        return cfg
