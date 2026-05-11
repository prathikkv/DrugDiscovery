"""LLM tool definitions for the reasoning engine -- 14 tools in Anthropic format.

Tools are defined in Anthropic input_schema format. The existing
anthropic_to_openai_tools() converter in llm_provider.py handles
conversion to OpenAI/Ollama format transparently.

Tool categories:
- Omics data (4): gene expression, enrichment, DE results, cell composition
- Evidence sources (6): OpenTargets, DGIdb, PubMed, ClinicalTrials, UniProt, ChEMBL
- Analysis (4): QC summary, cell type markers, pipeline summary, batch correction
"""

from __future__ import annotations

# ── 14 Tool Definitions in Anthropic format ─────────────────────────────────

TOOL_DEFINITIONS: list[dict] = [
    # ── Omics data tools (4) ────────────────────────────────────────────────
    {
        "name": "get_gene_expression",
        "description": (
            "Get expression data for a specific gene across all cell types in the "
            "loaded single-cell dataset. Returns mean expression level and percent "
            "of cells expressing the gene per cell type."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene": {
                    "type": "string",
                    "description": "Gene symbol to query (e.g., 'BRCA1', 'TP53').",
                },
            },
            "required": ["gene"],
        },
    },
    {
        "name": "get_enrichment",
        "description": (
            "Get fold enrichment values for a specific gene across cell types. "
            "Shows how enriched the gene is relative to expected background levels "
            "in each cell type."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene": {
                    "type": "string",
                    "description": "Gene symbol to query (e.g., 'BRCA1', 'TP53').",
                },
            },
            "required": ["gene"],
        },
    },
    {
        "name": "get_de_results",
        "description": (
            "Get top differentially expressed genes from the analysis. Can filter "
            "by cell type and direction (upregulated or downregulated). Returns "
            "gene names, log fold changes, and adjusted p-values."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_type": {
                    "type": "string",
                    "description": "Filter to a specific cell type (optional).",
                },
                "n_top": {
                    "type": "integer",
                    "description": "Number of top DE genes to return (default 10).",
                    "default": 10,
                },
                "direction": {
                    "type": "string",
                    "description": "Filter by expression direction.",
                    "enum": ["up", "down", "all"],
                    "default": "up",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_cell_composition",
        "description": (
            "Get the cell type composition of the loaded dataset. Returns counts "
            "and proportions for each cell type identified in the analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # ── Evidence source tools (6) ───────────────────────────────────────────
    {
        "name": "query_opentargets",
        "description": (
            "Query the Open Targets platform for genetic associations, target "
            "tractability assessments, and known drugs for a gene. Optionally "
            "filter by disease context to highlight relevant associations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol to query (e.g., 'EGFR', 'KRAS').",
                },
                "disease_context": {
                    "type": "string",
                    "description": "Optional disease/indication context to filter results.",
                },
            },
            "required": ["gene_symbol"],
        },
    },
    {
        "name": "query_dgidb",
        "description": (
            "Query the Drug-Gene Interaction Database (DGIdb) for known drug-gene "
            "interactions and druggability assessments. Returns interaction types, "
            "drug names, and gene categories."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol to query (e.g., 'EGFR', 'KRAS').",
                },
            },
            "required": ["gene_symbol"],
        },
    },
    {
        "name": "query_pubmed",
        "description": (
            "Search PubMed for recent publications about a gene, optionally in a "
            "specific disease context. Returns article titles, abstracts, authors, "
            "and publication dates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol to search for (e.g., 'EGFR', 'KRAS').",
                },
                "disease_context": {
                    "type": "string",
                    "description": "Optional disease/indication context to narrow search.",
                },
            },
            "required": ["gene_symbol"],
        },
    },
    {
        "name": "query_clinicaltrials",
        "description": (
            "Search ClinicalTrials.gov for active and completed clinical trials "
            "involving a gene target. Returns trial titles, phases, status, and "
            "intervention details."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol to search for (e.g., 'EGFR', 'KRAS').",
                },
                "disease_context": {
                    "type": "string",
                    "description": "Optional disease/indication context to filter trials.",
                },
            },
            "required": ["gene_symbol"],
        },
    },
    {
        "name": "query_uniprot",
        "description": (
            "Query UniProt for protein function, structural domains, subcellular "
            "location, and post-translational modifications for the protein "
            "encoded by a gene."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol to query (e.g., 'EGFR', 'KRAS').",
                },
            },
            "required": ["gene_symbol"],
        },
    },
    {
        "name": "query_chembl",
        "description": (
            "Query ChEMBL for bioactivity data, known compounds, and mechanism of "
            "action information for a gene target. Returns assay data, compound "
            "structures, and pharmacological classifications."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol to query (e.g., 'EGFR', 'KRAS').",
                },
            },
            "required": ["gene_symbol"],
        },
    },
    # ── Analysis tools (4) ──────────────────────────────────────────────────
    {
        "name": "get_qc_summary",
        "description": (
            "Get a summary of quality control filtering applied to the dataset. "
            "Returns cell/gene counts before and after filtering, QC thresholds "
            "used, and filtering statistics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_cell_type_markers",
        "description": (
            "Get top marker genes for a specific cell type or all cell types. "
            "Returns genes ranked by discriminative power with statistical scores."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_type": {
                    "type": "string",
                    "description": "Filter to a specific cell type (optional).",
                },
                "n_top": {
                    "type": "integer",
                    "description": "Number of top markers to return per cell type (default 5).",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_pipeline_summary",
        "description": (
            "Get an overview of the analysis pipeline: dataset information, "
            "processing parameters, number of cells and genes, normalization "
            "method, clustering resolution, and key findings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_batch_correction",
        "description": (
            "Get details about batch correction applied to the dataset. Returns "
            "the method used, batch variable, number of batches, and correction "
            "parameters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# ── Citation label to tool name mapping ─────────────────────────────────────
# Used by the hallucination checker to verify that claims citing a source
# correspond to actual tool calls made during reasoning.

CITATION_TO_TOOL: dict[str, str] = {
    "OpenTargets": "query_opentargets",
    "DGIdb": "query_dgidb",
    "PubMed": "query_pubmed",
    "ClinicalTrials": "query_clinicaltrials",
    "UniProt": "query_uniprot",
    "ChEMBL": "query_chembl",
    "Expression": "get_gene_expression",
    "Enrichment": "get_enrichment",
    "DE": "get_de_results",
    "QC": "get_qc_summary",
    "Markers": "get_cell_type_markers",
    "Pipeline": "get_pipeline_summary",
    "BatchCorrection": "get_batch_correction",
    "CellComposition": "get_cell_composition",
}
