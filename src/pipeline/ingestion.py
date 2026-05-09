"""Multi-format scRNA-seq data ingestion (REQ-102).

Supports .h5ad, CellRanger .h5, and 10x MTX directory formats.
Auto-detects format from the input path and returns a unified
AnnData object with original counts stored as a layer.
"""

import logging
import re
from pathlib import Path

import anndata as ad
import scanpy as sc

logger = logging.getLogger(__name__)

# Pattern matching Ensembl gene IDs (e.g., ENSG00000141510)
_ENSEMBL_PATTERN = re.compile(r"^ENSG\d{11}$")


def _check_ensembl_ids(adata: ad.AnnData) -> None:
    """Detect Ensembl IDs in var_names and swap to gene symbols if available.

    If >50% of var_names match the ENSG pattern, checks for a
    "gene_symbols" or "gene_ids" column in .var that could provide
    human-readable gene names. Swaps var_names if a mapping is found;
    logs a warning otherwise.
    """
    n_ensembl = sum(
        1 for name in adata.var_names if _ENSEMBL_PATTERN.match(name)
    )
    if n_ensembl <= len(adata.var_names) * 0.5:
        return  # Not predominantly Ensembl IDs

    logger.info(
        "Detected Ensembl IDs in %d/%d var_names",
        n_ensembl,
        len(adata.var_names),
    )

    # Check for a gene symbols column to swap in
    for col in ("gene_symbols", "gene_symbol", "gene_name"):
        if col in adata.var.columns:
            adata.var["ensembl_id"] = adata.var_names.copy()
            adata.var_names = adata.var[col].astype(str).values
            adata.var_names_make_unique()
            logger.info("Swapped var_names to '%s' column", col)
            return

    # Check if "gene_ids" column has non-Ensembl names (reverse mapping)
    if "gene_ids" in adata.var.columns:
        sample = adata.var["gene_ids"].iloc[:10].tolist()
        if not any(_ENSEMBL_PATTERN.match(str(s)) for s in sample):
            adata.var["ensembl_id"] = adata.var_names.copy()
            adata.var_names = adata.var["gene_ids"].astype(str).values
            adata.var_names_make_unique()
            logger.info("Swapped var_names to 'gene_ids' column")
            return

    logger.warning(
        "var_names are Ensembl IDs but no gene symbol column found in .var "
        "(checked: gene_symbols, gene_symbol, gene_name, gene_ids). "
        "Downstream annotation may be affected."
    )


def ingest_data(input_path: Path) -> ad.AnnData:
    """Load scRNA-seq data from any supported format.

    Auto-detects the format based on file extension or directory
    structure and returns a unified AnnData object.

    Supported formats:
        - .h5ad: Native AnnData HDF5 format
        - .h5: CellRanger HDF5 format (gene expression only)
        - Directory: 10x MTX folder (matrix.mtx.gz + barcodes + features)

    After loading:
        - Ensures unique var_names
        - Detects and handles Ensembl gene IDs
        - Stores original counts in adata.layers["raw_counts"]

    Args:
        input_path: Path to the data file or directory.

    Returns:
        AnnData object with raw_counts layer.

    Raises:
        ValueError: If the format is not supported.
        FileNotFoundError: If the path does not exist.
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if input_path.suffix == ".h5ad":
        logger.info("Reading h5ad file: %s", input_path)
        adata = sc.read_h5ad(str(input_path))

    elif input_path.suffix == ".h5":
        logger.info("Reading 10x HDF5 file: %s", input_path)
        adata = sc.read_10x_h5(str(input_path), gex_only=True)

    elif input_path.is_dir():
        logger.info("Reading 10x MTX directory: %s", input_path)
        adata = sc.read_10x_mtx(
            str(input_path),
            var_names="gene_symbols",
            make_unique=True,
            gex_only=True,
        )

    else:
        raise ValueError(
            f"Unsupported format: '{input_path.suffix}'. "
            "Expected .h5ad, .h5, or a directory containing 10x MTX files "
            "(matrix.mtx.gz, barcodes.tsv.gz, features.tsv.gz)."
        )

    # Ensure unique gene names
    adata.var_names_make_unique()

    # Handle Ensembl ID detection and swap
    _check_ensembl_ids(adata)

    # Store original counts as a layer for downstream use
    adata.layers["raw_counts"] = adata.X.copy()

    logger.info(
        "Ingested %d cells x %d genes from %s",
        adata.n_obs,
        adata.n_vars,
        input_path,
    )

    return adata
