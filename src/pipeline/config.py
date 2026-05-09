"""Pipeline configuration with tissue-specific defaults (REQ-101, REQ-104).

Provides PipelineConfig, QCConfig, and ProcessingConfig dataclasses
with a TISSUE_DEFAULTS registry mapping 10+ tissue types to
tissue-appropriate QC thresholds and CellTypist model selections.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Optional


# ── Tissue-specific defaults ─────────────────────────────────────────
# Maps tissue type to {max_pct_mt, celltypist_model}.
# The tissue_type key is a generic biological category -- no drug,
# target, or disease-specific references belong here.

TISSUE_DEFAULTS: dict[str, dict] = {
    "brain": {"max_pct_mt": 5.0, "celltypist_model": "Developing_Human_Brain.pkl"},
    "tumor": {"max_pct_mt": 25.0, "celltypist_model": "Immune_All_Low.pkl"},
    "lung": {"max_pct_mt": 10.0, "celltypist_model": "Human_Lung_Atlas.pkl"},
    "immune": {"max_pct_mt": 10.0, "celltypist_model": "Immune_All_Low.pkl"},
    "heart": {"max_pct_mt": 10.0, "celltypist_model": "Healthy_Adult_Heart.pkl"},
    "adipose": {"max_pct_mt": 20.0, "celltypist_model": "Immune_All_Low.pkl"},
    "kidney": {"max_pct_mt": 10.0, "celltypist_model": "Human_Kidney.pkl"},
    "liver": {"max_pct_mt": 10.0, "celltypist_model": "Human_Liver.pkl"},
    "intestine": {"max_pct_mt": 15.0, "celltypist_model": "Human_Intestine.pkl"},
    "eye": {"max_pct_mt": 10.0, "celltypist_model": "Immune_All_Low.pkl"},
    "pancreas": {"max_pct_mt": 10.0, "celltypist_model": "Immune_All_Low.pkl"},
    # Fallback for unrecognized tissue types
    "default": {"max_pct_mt": 15.0, "celltypist_model": "Immune_All_Low.pkl"},
}


@dataclass
class QCConfig:
    """Quality-control thresholds for cell and gene filtering."""

    min_genes: int = 200
    max_genes: int = 8000
    max_pct_mt: float = 15.0
    doublet_threshold: float = 0.25
    min_cells_per_gene: int = 3
    female_marker: str = "XIST"
    male_markers: list[str] = field(
        default_factory=lambda: ["RPS4Y1", "DDX3Y", "KDM5D"]
    )
    sex_expr_threshold: float = 0.5


@dataclass
class ProcessingConfig:
    """Parameters for normalization, HVG selection, PCA, and clustering."""

    normalize_total_target: float = 1e4
    n_top_hvgs: int = 3000
    batch_key: str = "donor_id"
    n_pcs: int = 50
    n_pcs_neighbors: int = 30
    n_neighbors: int = 15
    leiden_resolution: float = 0.5
    n_jobs: int = 2


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration with tissue-specific defaults.

    Use PipelineConfig.for_tissue("brain") to create a config pre-loaded
    with tissue-appropriate QC thresholds and CellTypist model.
    """

    tissue_type: str = "default"
    qc: QCConfig = field(default_factory=QCConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    celltypist_model: Optional[str] = None  # Auto-selected from tissue if None
    de_method: str = "wilcoxon"
    de_corr_method: str = "benjamini-hochberg"
    skip_ambient_rna: bool = False
    ambient_rna_method: str = "soupx"
    enrichment_gene_sets: list[str] = field(
        default_factory=lambda: ["GO_Biological_Process_2023", "KEGG_2021_Human"]
    )

    @classmethod
    def for_tissue(cls, tissue: str, **overrides) -> "PipelineConfig":
        """Create a config with tissue-specific defaults.

        Looks up the tissue in TISSUE_DEFAULTS to set max_pct_mt and
        celltypist_model. Falls back to "default" if tissue is unknown.

        Args:
            tissue: Tissue type key (e.g., "brain", "lung", "tumor").
            **overrides: Additional keyword arguments to override config
                fields (applied after tissue defaults).

        Returns:
            A PipelineConfig with tissue-appropriate defaults.
        """
        defaults = TISSUE_DEFAULTS.get(tissue, TISSUE_DEFAULTS["default"])
        qc = QCConfig(max_pct_mt=defaults["max_pct_mt"])
        cfg = cls(
            tissue_type=tissue,
            qc=qc,
            celltypist_model=defaults["celltypist_model"],
        )
        # Apply any user overrides
        for key, val in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, val)
        return cfg

    def to_json(self) -> str:
        """Serialize config to deterministic JSON string."""
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str) -> "PipelineConfig":
        """Deserialize config from JSON string.

        Reconstructs nested QCConfig and ProcessingConfig dataclasses.
        """
        data = json.loads(json_str)
        qc = QCConfig(**data.pop("qc", {}))
        proc = ProcessingConfig(**data.pop("processing", {}))
        return cls(qc=qc, processing=proc, **data)
