"""Tool call dispatch to pipeline and evidence subsystems (REQ-303).

Routes LLM tool calls to the correct backend functions: omics data handlers
(require project_dir with pipeline results), evidence source handlers (use
individual evidence sources via GeneResolver), and analysis handlers (require
project_dir with pipeline report).

All handlers return compact result dicts. Errors are caught and returned as
{"error": "..."} dicts rather than raising exceptions, ensuring the tool-calling
loop always receives a parseable result.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.reasoning.token_manager import TokenManager

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Routes tool calls to the correct pipeline and evidence backend functions.

    All 14 tool names from src/reasoning/tools.py are dispatched to handler
    methods. Missing data returns error dicts instead of raising exceptions.

    Args:
        project_dir: Path to the project directory containing pipeline results.
        evidence_aggregator: EvidenceAggregator instance for evidence queries.
        token_manager: TokenManager for result truncation. Creates default if None.
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        evidence_aggregator: Optional[Any] = None,
        token_manager: Optional[TokenManager] = None,
    ) -> None:
        self.project_dir = project_dir
        self._evidence_aggregator = evidence_aggregator
        self.token_manager = token_manager or TokenManager()

        # Lazy-loaded data caches
        self._adata = None
        self._pipeline_report: Optional[dict] = None

        # Dispatch table: tool_name -> handler method
        self._dispatch: dict[str, Any] = {
            # Omics data tools (4)
            "get_gene_expression": self._handle_get_gene_expression,
            "get_enrichment": self._handle_get_enrichment,
            "get_de_results": self._handle_get_de_results,
            "get_cell_composition": self._handle_get_cell_composition,
            # Evidence source tools (6)
            "query_opentargets": self._handle_query_opentargets,
            "query_dgidb": self._handle_query_dgidb,
            "query_pubmed": self._handle_query_pubmed,
            "query_clinicaltrials": self._handle_query_clinicaltrials,
            "query_uniprot": self._handle_query_uniprot,
            "query_chembl": self._handle_query_chembl,
            # Analysis tools (4)
            "get_qc_summary": self._handle_get_qc_summary,
            "get_cell_type_markers": self._handle_get_cell_type_markers,
            "get_pipeline_summary": self._handle_get_pipeline_summary,
            "get_batch_correction": self._handle_get_batch_correction,
        }

    def execute(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool call by dispatching to the appropriate handler.

        Args:
            tool_name: Name of the tool to execute (must match dispatch table).
            arguments: Arguments dict from the LLM tool call.

        Returns:
            Result dict from the handler. On error, returns {"error": "..."}.
        """
        handler = self._dispatch.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = handler(arguments)

            # Truncate result if it exceeds 500 tokens
            result_json = json.dumps(result, default=str)
            truncated = self.token_manager.truncate_tool_result(result_json, max_tokens=500)
            if truncated != result_json:
                # Parse back to dict if truncated, or return as string
                try:
                    return json.loads(truncated)
                except json.JSONDecodeError:
                    return {"result": truncated, "truncated": True}

            return result

        except Exception as e:
            logger.warning("ToolExecutor: Error executing %s: %s", tool_name, e)
            return {"error": str(e)}

    # ── Lazy loaders ──────────────────────────────────────────────────────

    def _load_adata(self):
        """Lazy-load AnnData from project results directory."""
        if self._adata is not None:
            return self._adata

        if self.project_dir is None:
            return None

        h5ad_path = self.project_dir / "results" / "final.h5ad"
        if not h5ad_path.exists():
            return None

        try:
            import anndata

            self._adata = anndata.read_h5ad(h5ad_path)
            return self._adata
        except Exception as e:
            logger.warning("Failed to load AnnData: %s", e)
            return None

    def _load_pipeline_report(self) -> Optional[dict]:
        """Lazy-load pipeline_report.json from project results directory."""
        if self._pipeline_report is not None:
            return self._pipeline_report

        if self.project_dir is None:
            return None

        report_path = self.project_dir / "results" / "pipeline_report.json"
        if not report_path.exists():
            return None

        try:
            with open(report_path) as f:
                self._pipeline_report = json.load(f)
            return self._pipeline_report
        except Exception as e:
            logger.warning("Failed to load pipeline report: %s", e)
            return None

    def _get_gene_resolver(self):
        """Lazy import and create GeneResolver."""
        from src.evidence.gene_resolver import GeneResolver

        if not hasattr(self, "_gene_resolver"):
            self._gene_resolver = GeneResolver()
        return self._gene_resolver

    # ── Omics tool handlers (4) ───────────────────────────────────────────

    def _handle_get_gene_expression(self, args: dict) -> dict:
        """Get expression data for a gene across cell types."""
        adata = self._load_adata()
        if adata is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        gene = args.get("gene", "")
        if gene not in adata.var_names:
            return {"error": f"Gene '{gene}' not found in dataset"}

        try:
            import numpy as np

            cell_types = []
            cell_type_col = "cell_type" if "cell_type" in adata.obs.columns else None
            if cell_type_col is None:
                # Try common alternatives
                for col in ["celltype", "CellType", "cell_type_fine", "leiden"]:
                    if col in adata.obs.columns:
                        cell_type_col = col
                        break

            if cell_type_col is None:
                return {"error": "No cell type annotation found in dataset"}

            for ct in adata.obs[cell_type_col].unique():
                mask = adata.obs[cell_type_col] == ct
                subset = adata[mask, gene]
                expr = subset.X
                if hasattr(expr, "toarray"):
                    expr = expr.toarray()
                expr = expr.flatten()

                cell_types.append({
                    "name": str(ct),
                    "mean_expression": float(np.mean(expr)),
                    "pct_expressing": float(np.sum(expr > 0) / len(expr) * 100),
                })

            return {"gene": gene, "cell_types": cell_types}

        except Exception as e:
            return {"error": f"Expression analysis failed: {e}"}

    def _handle_get_enrichment(self, args: dict) -> dict:
        """Get fold enrichment for a gene across cell types."""
        adata = self._load_adata()
        if adata is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        gene = args.get("gene", "")
        if gene not in adata.var_names:
            return {"error": f"Gene '{gene}' not found in dataset"}

        try:
            import numpy as np

            # Compute fold enrichment vs overall mean
            all_expr = adata[:, gene].X
            if hasattr(all_expr, "toarray"):
                all_expr = all_expr.toarray()
            overall_mean = float(np.mean(all_expr))

            if overall_mean == 0:
                return {"gene": gene, "enrichment": [], "note": "No expression detected"}

            cell_type_col = "cell_type" if "cell_type" in adata.obs.columns else None
            if cell_type_col is None:
                for col in ["celltype", "CellType", "cell_type_fine", "leiden"]:
                    if col in adata.obs.columns:
                        cell_type_col = col
                        break

            if cell_type_col is None:
                return {"error": "No cell type annotation found in dataset"}

            enrichment = []
            for ct in adata.obs[cell_type_col].unique():
                mask = adata.obs[cell_type_col] == ct
                subset = adata[mask, gene].X
                if hasattr(subset, "toarray"):
                    subset = subset.toarray()
                ct_mean = float(np.mean(subset))
                enrichment.append({
                    "cell_type": str(ct),
                    "fold_change": round(ct_mean / overall_mean, 3) if overall_mean > 0 else 0,
                })

            return {"gene": gene, "enrichment": enrichment}

        except Exception as e:
            return {"error": f"Enrichment analysis failed: {e}"}

    def _handle_get_de_results(self, args: dict) -> dict:
        """Get top differentially expressed genes from the pipeline report."""
        report = self._load_pipeline_report()
        if report is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        cell_type = args.get("cell_type")
        n_top = args.get("n_top", 10)
        direction = args.get("direction", "up")

        try:
            de_data = report.get("differential_expression", {})
            if not de_data:
                return {"error": "No differential expression results in pipeline report"}

            results = {}
            for ct, genes in de_data.items():
                if cell_type and ct != cell_type:
                    continue

                gene_list = genes if isinstance(genes, list) else []
                # Filter by direction
                if direction == "up":
                    gene_list = [g for g in gene_list if g.get("log2fc", 0) > 0]
                elif direction == "down":
                    gene_list = [g for g in gene_list if g.get("log2fc", 0) < 0]

                # Sort by absolute fold change and take top N
                gene_list = sorted(gene_list, key=lambda x: abs(x.get("log2fc", 0)), reverse=True)[:n_top]
                results[ct] = [
                    {
                        "gene": g.get("gene", ""),
                        "log2fc": g.get("log2fc", 0),
                        "pval_adj": g.get("pval_adj", 1.0),
                    }
                    for g in gene_list
                ]

            if cell_type:
                return {"cell_type": cell_type, "top_genes": results.get(cell_type, [])}

            return {"results": results}

        except Exception as e:
            return {"error": f"DE analysis failed: {e}"}

    def _handle_get_cell_composition(self, args: dict) -> dict:
        """Get cell type composition of the dataset."""
        adata = self._load_adata()
        if adata is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        try:
            cell_type_col = "cell_type" if "cell_type" in adata.obs.columns else None
            if cell_type_col is None:
                for col in ["celltype", "CellType", "cell_type_fine", "leiden"]:
                    if col in adata.obs.columns:
                        cell_type_col = col
                        break

            if cell_type_col is None:
                return {"error": "No cell type annotation found in dataset"}

            counts = adata.obs[cell_type_col].value_counts()
            total = int(counts.sum())

            cell_types = []
            for ct, count in counts.items():
                cell_types.append({
                    "name": str(ct),
                    "count": int(count),
                    "proportion": round(int(count) / total, 4),
                })

            return {"cell_types": cell_types}

        except Exception as e:
            return {"error": f"Cell composition analysis failed: {e}"}

    # ── Evidence source tool handlers (6) ─────────────────────────────────

    def _handle_query_opentargets(self, args: dict) -> dict:
        """Query OpenTargets for a gene."""
        gene_symbol = args.get("gene_symbol", "")
        disease_context = args.get("disease_context")

        try:
            gene_ids = self._get_gene_resolver().resolve(gene_symbol)

            from src.evidence.sources.opentargets import OpenTargetsSource

            source = OpenTargetsSource()
            result = source.fetch(gene_ids, disease_context)

            if result.confidence == 0.0:
                return {"error": result.error or "No data from OpenTargets"}

            data = result.data or {}
            associations = data.get("associations", [])
            top_5 = associations[:5]

            return {
                "gene": gene_symbol,
                "association_count": len(associations),
                "top_associations": [
                    {
                        "disease": a.get("disease_name", ""),
                        "score": a.get("overall_score", 0),
                    }
                    for a in top_5
                ],
                "known_drug_count": len(data.get("known_drugs", [])),
                "tractability": data.get("tractability", []),
            }

        except Exception as e:
            return {"error": f"OpenTargets query failed: {e}"}

    def _handle_query_dgidb(self, args: dict) -> dict:
        """Query DGIdb for drug-gene interactions."""
        gene_symbol = args.get("gene_symbol", "")

        try:
            gene_ids = self._get_gene_resolver().resolve(gene_symbol)

            from src.evidence.sources.dgidb import DGIdbSource

            source = DGIdbSource()
            result = source.fetch(gene_ids)

            if result.confidence == 0.0:
                return {"error": result.error or "No data from DGIdb"}

            data = result.data or {}
            interactions = data.get("interactions", [])
            top_3 = interactions[:3]

            return {
                "gene": gene_symbol,
                "drug_count": data.get("interaction_count", 0),
                "gene_categories": data.get("gene_categories", []),
                "top_drugs": [
                    {
                        "drug_name": d.get("drug_name", ""),
                        "interaction_types": [
                            t.get("type", "") for t in d.get("interaction_types", [])
                        ],
                        "approved": d.get("approved", False),
                    }
                    for d in top_3
                ],
            }

        except Exception as e:
            return {"error": f"DGIdb query failed: {e}"}

    def _handle_query_pubmed(self, args: dict) -> dict:
        """Query PubMed for recent publications."""
        gene_symbol = args.get("gene_symbol", "")
        disease_context = args.get("disease_context")

        try:
            gene_ids = self._get_gene_resolver().resolve(gene_symbol)

            from src.evidence.sources.pubmed import PubMedSource

            source = PubMedSource()
            result = source.fetch(gene_ids, disease_context)

            if result.confidence == 0.0:
                return {"error": result.error or "No data from PubMed"}

            data = result.data or {}
            papers = data.get("papers", [])
            top_3 = papers[:3]

            return {
                "gene": gene_symbol,
                "paper_count": data.get("total_count", 0),
                "top_papers": [
                    {
                        "title": p.get("title", ""),
                        "year": p.get("year", ""),
                        "journal": p.get("journal", ""),
                    }
                    for p in top_3
                ],
                "ai_summary": data.get("ai_summary"),
            }

        except Exception as e:
            return {"error": f"PubMed query failed: {e}"}

    def _handle_query_clinicaltrials(self, args: dict) -> dict:
        """Query ClinicalTrials.gov for active trials."""
        gene_symbol = args.get("gene_symbol", "")
        disease_context = args.get("disease_context")

        try:
            gene_ids = self._get_gene_resolver().resolve(gene_symbol)

            from src.evidence.sources.clinicaltrials import ClinicalTrialsSource

            source = ClinicalTrialsSource()
            result = source.fetch(gene_ids, disease_context)

            if result.confidence == 0.0:
                return {"error": result.error or "No data from ClinicalTrials"}

            data = result.data or {}
            trials = data.get("trials", [])
            top_3 = trials[:3]

            return {
                "gene": gene_symbol,
                "trial_count": data.get("total_count", 0),
                "top_trials": [
                    {
                        "title": t.get("briefTitle", ""),
                        "phases": t.get("phases", []),
                        "status": t.get("overallStatus", ""),
                    }
                    for t in top_3
                ],
            }

        except Exception as e:
            return {"error": f"ClinicalTrials query failed: {e}"}

    def _handle_query_uniprot(self, args: dict) -> dict:
        """Query UniProt for protein function data."""
        gene_symbol = args.get("gene_symbol", "")

        try:
            gene_ids = self._get_gene_resolver().resolve(gene_symbol)

            from src.evidence.sources.uniprot import UniProtSource

            source = UniProtSource()
            result = source.fetch(gene_ids)

            if result.confidence == 0.0:
                return {"error": result.error or "No data from UniProt"}

            data = result.data or {}

            return {
                "gene": gene_symbol,
                "protein_name": data.get("protein_name", ""),
                "function_summary": data.get("function", [])[:2],
                "subcellular_location": data.get("subcellular_location", []),
                "domains": data.get("domains", []),
                "has_structure": data.get("has_alphafold_structure", False),
                "sequence_length": data.get("sequence_length", 0),
            }

        except Exception as e:
            return {"error": f"UniProt query failed: {e}"}

    def _handle_query_chembl(self, args: dict) -> dict:
        """Query ChEMBL for bioactivity and mechanism data."""
        gene_symbol = args.get("gene_symbol", "")

        try:
            gene_ids = self._get_gene_resolver().resolve(gene_symbol)

            from src.evidence.sources.chembl import ChEMBLSource

            source = ChEMBLSource()
            result = source.fetch(gene_ids)

            if result.confidence == 0.0:
                return {"error": result.error or "No data from ChEMBL"}

            data = result.data or {}
            mechanisms = data.get("mechanisms", [])

            return {
                "gene": gene_symbol,
                "compound_count": data.get("activity_count", 0),
                "mean_pchembl": data.get("mean_pchembl"),
                "max_pchembl": data.get("max_pchembl"),
                "top_mechanisms": [
                    {
                        "mechanism": m.get("mechanism_of_action", ""),
                        "action_type": m.get("action_type", ""),
                    }
                    for m in mechanisms[:3]
                ],
            }

        except Exception as e:
            return {"error": f"ChEMBL query failed: {e}"}

    # ── Analysis tool handlers (4) ────────────────────────────────────────

    def _handle_get_qc_summary(self, args: dict) -> dict:
        """Get QC filtering summary from pipeline report."""
        report = self._load_pipeline_report()
        if report is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        try:
            qc_data = report.get("quality_control", report.get("qc", {}))
            if not qc_data:
                return {"error": "No QC data in pipeline report"}

            return {
                "cells_before": qc_data.get("cells_before_filter", 0),
                "cells_after": qc_data.get("cells_after_filter", 0),
                "genes_before": qc_data.get("genes_before_filter", 0),
                "genes_after": qc_data.get("genes_after_filter", 0),
                "thresholds": qc_data.get("thresholds", {}),
                "doublet_removal": qc_data.get("doublet_removal", {}),
            }

        except Exception as e:
            return {"error": f"QC summary failed: {e}"}

    def _handle_get_cell_type_markers(self, args: dict) -> dict:
        """Get top marker genes for cell types from DE results."""
        report = self._load_pipeline_report()
        if report is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        cell_type = args.get("cell_type")
        n_top = args.get("n_top", 5)

        try:
            de_data = report.get("differential_expression", {})
            if not de_data:
                return {"error": "No DE results in pipeline report"}

            if cell_type:
                genes = de_data.get(cell_type, [])
                if not isinstance(genes, list):
                    return {"error": f"No markers for cell type '{cell_type}'"}
                # Top markers sorted by fold change
                markers = sorted(genes, key=lambda x: abs(x.get("log2fc", 0)), reverse=True)[:n_top]
                return {
                    "cell_type": cell_type,
                    "markers": [
                        {"gene": g.get("gene", ""), "log2fc": g.get("log2fc", 0)}
                        for g in markers
                    ],
                }

            # All cell types
            result = {}
            for ct, genes in de_data.items():
                if not isinstance(genes, list):
                    continue
                markers = sorted(genes, key=lambda x: abs(x.get("log2fc", 0)), reverse=True)[:n_top]
                result[ct] = [
                    {"gene": g.get("gene", ""), "log2fc": g.get("log2fc", 0)}
                    for g in markers
                ]

            return {"markers_by_cell_type": result}

        except Exception as e:
            return {"error": f"Cell type markers failed: {e}"}

    def _handle_get_pipeline_summary(self, args: dict) -> dict:
        """Get pipeline overview from pipeline report."""
        report = self._load_pipeline_report()
        if report is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        try:
            return {
                "dataset": report.get("dataset", {}),
                "cell_count": report.get("cell_count", report.get("n_cells", 0)),
                "gene_count": report.get("gene_count", report.get("n_genes", 0)),
                "normalization": report.get("normalization", {}),
                "clustering": report.get("clustering", {}),
                "cell_types_found": report.get("cell_types_found", []),
                "processing_params": report.get("processing_params", {}),
            }

        except Exception as e:
            return {"error": f"Pipeline summary failed: {e}"}

    def _handle_get_batch_correction(self, args: dict) -> dict:
        """Get batch correction details from pipeline report."""
        report = self._load_pipeline_report()
        if report is None:
            return {"error": "Pipeline results not available. Run the omics pipeline first."}

        try:
            batch_data = report.get("batch_correction", {})
            if not batch_data:
                return {"applied": False, "note": "No batch correction recorded in pipeline report"}

            return {
                "applied": True,
                "method": batch_data.get("method", ""),
                "batch_variable": batch_data.get("batch_variable", ""),
                "n_batches": batch_data.get("n_batches", 0),
                "parameters": batch_data.get("parameters", {}),
            }

        except Exception as e:
            return {"error": f"Batch correction query failed: {e}"}
