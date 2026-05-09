"""Gene set enrichment via gseapy ORA per cell type (REQ-106).

Runs over-representation analysis (ORA) on significant differentially
expressed genes from each cell type using gseapy. Requires DE results
in adata.uns["de_results"] from the differential expression stage.

All gene set selections come from PipelineConfig.enrichment_gene_sets --
nothing is hardcoded to any specific biology or disease.
"""

import logging
import time
from pathlib import Path
from typing import Optional

import anndata as ad

from src.pipeline.checkpointing import (
    load_checkpoint,
    save_checkpoint,
    save_stage_report,
)
from src.pipeline.config import PipelineConfig
from src.pipeline.progress import StageProgressTracker

logger = logging.getLogger(__name__)

# Thresholds for extracting significant genes from DE results
PVAL_ADJ_THRESHOLD = 0.05
LOG_FC_THRESHOLD = 0.5
MIN_SIG_GENES = 5


def run_enrichment(
    adata: ad.AnnData,
    config: PipelineConfig,
    project_dir: Path,
    progress_tracker: Optional[StageProgressTracker] = None,
) -> tuple[ad.AnnData, dict]:
    """Run gene set enrichment (ORA) on DE results per cell type.

    For each cell type in adata.uns["de_results"], extracts significant
    upregulated genes (pvals_adj < 0.05, logfoldchanges > 0.5) and runs
    gseapy.enrich() for over-representation analysis.

    Integrates with checkpointing (loads existing, saves on completion)
    and progress tracking (reports stage completion).

    Args:
        adata: AnnData object with DE results in adata.uns["de_results"].
        config: PipelineConfig with enrichment_gene_sets list.
        project_dir: Project directory for checkpoints and reports.
        progress_tracker: Optional StageProgressTracker for progress
            reporting. None silently skips progress updates.

    Returns:
        Tuple of (adata_with_enrichment, enrichment_report_dict).
    """
    # -- Check for existing checkpoint --
    existing = load_checkpoint(project_dir, "enrichment")
    if existing is not None:
        logger.info("Enrichment checkpoint found -- loading cached result")
        from src.pipeline.checkpointing import load_stage_report

        report = load_stage_report(project_dir, "enrichment") or {
            "stage": "enrichment",
            "cached": True,
        }
        if progress_tracker:
            progress_tracker.update("enrichment")
        return existing, report

    t0 = time.time()

    # -- Check for DE results --
    de_results = adata.uns.get("de_results")
    if de_results is None:
        logger.warning("No DE results found in adata.uns -- skipping enrichment")
        report = {
            "stage": "enrichment",
            "status": "skipped",
            "reason": "No DE results found. Run differential expression first.",
        }
        save_stage_report(report, project_dir, "enrichment")
        if progress_tracker:
            progress_tracker.update("enrichment")
        return adata, report

    gene_sets = config.enrichment_gene_sets
    logger.info(
        "Starting enrichment: %d cell types, gene sets=%s",
        len(de_results),
        gene_sets,
    )

    if progress_tracker:
        progress_tracker.update_substage("enrichment", 0.1)

    # -- Run ORA per cell type --
    enrichment_results: dict = {}
    n_analyzed = 0
    n_skipped = 0
    cell_types = list(de_results.keys())

    for i, cell_type in enumerate(cell_types):
        gene_dicts = de_results[cell_type]

        # Extract significant upregulated genes
        sig_genes = [
            g["names"]
            for g in gene_dicts
            if (
                g.get("pvals_adj", 1.0) < PVAL_ADJ_THRESHOLD
                and g.get("logfoldchanges", 0.0) > LOG_FC_THRESHOLD
            )
        ]

        if len(sig_genes) < MIN_SIG_GENES:
            enrichment_results[cell_type] = {
                "status": "too_few_genes",
                "n_sig_genes": len(sig_genes),
                "reason": (
                    f"Only {len(sig_genes)} significant genes found "
                    f"(minimum {MIN_SIG_GENES} required)"
                ),
            }
            n_skipped += 1
            logger.info(
                "Skipping enrichment for '%s': %d significant genes (<%d)",
                cell_type,
                len(sig_genes),
                MIN_SIG_GENES,
            )
            continue

        # Run gseapy ORA
        try:
            import gseapy as gp  # noqa: PLC0415

            enr = gp.enrich(
                gene_list=sig_genes,
                gene_sets=gene_sets,
                organism="human",
                outdir=None,
                cutoff=0.05,
            )

            results_records = enr.results.to_dict(orient="records")
            enrichment_results[cell_type] = {
                "status": "completed",
                "n_sig_genes": len(sig_genes),
                "n_significant_terms": len(results_records),
                "results": results_records,
            }
            n_analyzed += 1
            logger.info(
                "Enrichment for '%s': %d sig genes -> %d enriched terms",
                cell_type,
                len(sig_genes),
                len(results_records),
            )

        except ConnectionError as exc:
            logger.warning(
                "Network error during enrichment for '%s': %s",
                cell_type,
                exc,
            )
            enrichment_results[cell_type] = {
                "status": "error",
                "error": f"Network error: {exc}",
                "n_sig_genes": len(sig_genes),
            }
            n_skipped += 1

        except Exception as exc:
            logger.warning(
                "Enrichment failed for '%s': %s",
                cell_type,
                exc,
            )
            enrichment_results[cell_type] = {
                "status": "error",
                "error": str(exc),
                "n_sig_genes": len(sig_genes),
            }
            n_skipped += 1

        # Update substage progress
        if progress_tracker:
            frac = 0.1 + 0.8 * ((i + 1) / len(cell_types))
            progress_tracker.update_substage("enrichment", frac)

    # -- Store results in adata --
    adata.uns["enrichment_results"] = enrichment_results

    # -- Save checkpoint --
    checkpoint_path = save_checkpoint(adata, project_dir, "enrichment")

    elapsed = time.time() - t0
    logger.info(
        "Enrichment complete: %d analyzed, %d skipped in %.1fs",
        n_analyzed,
        n_skipped,
        elapsed,
    )

    # -- Build report --
    results_summary = {}
    for ct, res in enrichment_results.items():
        if res.get("status") == "completed":
            results_summary[ct] = {
                "n_significant_terms": res.get("n_significant_terms", 0),
                "n_sig_genes": res.get("n_sig_genes", 0),
            }
        else:
            results_summary[ct] = {
                "status": res.get("status", "unknown"),
                "reason": res.get("reason", res.get("error", "")),
            }

    report = {
        "stage": "enrichment",
        "status": "completed",
        "gene_sets_used": gene_sets,
        "n_cell_types_analyzed": n_analyzed,
        "n_cell_types_skipped": n_skipped,
        "results_summary": results_summary,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 1),
    }

    save_stage_report(report, project_dir, "enrichment")

    # -- Report progress --
    if progress_tracker:
        progress_tracker.update("enrichment", str(checkpoint_path))

    return adata, report
