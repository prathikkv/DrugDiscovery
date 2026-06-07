# Interview Prep Guide — Pharma AI Roles

## Target Roles
- AI/ML Scientist, Drug Discovery (Pfizer, AZ, Novartis, Roche, Merck)
- Computational Biology Engineer (Genentech, BMS, Sanofi)
- AI Platform Lead (Series B-C biotech)

---

## "Tell Me About a Project" — BioOrchestrator Script

> "I built BioOrchestrator — an end-to-end AI drug target intelligence platform. The problem it solves is that computational biologists currently spend 2–4 weeks manually triaging a target across 6 different databases before making a GO/NO-GO recommendation. I automated that into a 15-minute workflow.
>
> The architecture has three main layers: first, a parallel evidence aggregation engine that queries OpenTargets, DGIdb, PubMed, UniProt, ChEMBL, and ClinicalTrials simultaneously using a 2-phase fetch pattern. Second, an AI reasoning engine that runs 5 parallel LLM modes — hypothesis, synthesis, contradiction detection, gap analysis, and confidence assessment — using an agentic tool-calling loop up to 10 rounds deep, with hallucination checking and provenance tracking. Third, a 7-dimension scoring framework that produces a GO/CONDITIONAL/NO-GO verdict.
>
> I also built a 21 CFR Part 11 compliant audit trail with SHA-256 hash chain and electronic signatures, because anything used in a pharma regulatory submission needs to be fully auditable.
>
> The platform supports 6 pre-validated pharma targets including EGFR/NSCLC, GLP1R/Obesity, and CD274 for immunotherapy. I'm currently looking for biotech teams to pilot it."

---

## Domain Knowledge Q&A

### "What is GWAS and how is it relevant to target ID?"
> "GWAS — Genome-Wide Association Study — identifies genetic variants associated with disease. It's one of the strongest lines of genetic evidence for target validation. If a gene's variants show statistically significant association with a disease phenotype across large patient cohorts, that's meaningful evidence the gene is causally involved. OpenTargets integrates GWAS data to produce genetic evidence scores for gene-disease pairs, which is one of the 7 dimensions in my scoring framework."

### "What is GSEA and when would you use it?"
> "Gene Set Enrichment Analysis. Instead of looking at individual differentially expressed genes, GSEA asks whether a predefined set of genes — like a pathway from KEGG or Reactome — shows statistically coordinated enrichment at the top or bottom of a ranked gene list. It's less sensitive to arbitrary fold-change cutoffs. I use it in the omics pipeline enrichment stage after differential expression to map DE results onto biological pathways."

### "What's the difference between Seurat and Scanpy?"
> "Both are the standard scRNA-seq analysis toolkits — Seurat is R-based, Scanpy is Python-based. They share the same conceptual pipeline: QC → normalization → HVG selection → PCA → neighborhood graph → clustering → annotation → DE. I used Scanpy because it integrates well with AnnData (the standard h5ad format) and plays nicely with the Python LLM ecosystem. For DE specifically, Scanpy wraps Wilcoxon rank-sum and t-test by default, while Seurat uses several methods including pseudobulk."

### "What is 21 CFR Part 11?"
> "It's the FDA regulation governing electronic records and electronic signatures in pharmaceutical settings. In practice, it means: audit trails must be tamper-evident (I implemented this with a SHA-256 hash chain where each record includes the hash of the previous), electronic signatures must require re-authentication, records must be attributable to a specific individual with timestamps, and systems must have access controls. It applies to any software used in the context of regulated activities — clinical trials, manufacturing, regulatory submissions."

### "What are the main reasons drug targets fail?"
> "Three main categories: first, lack of efficacy — the target isn't actually driving the disease in humans the way it did in the animal model. Second, safety — the target has off-target effects that weren't predicted. Third, technical failure — the drug can't reach the target or isn't druggable. The root cause of most failures is insufficient target validation at the discovery stage — which is what BioOrchestrator is designed to address."

### "What is Leiden clustering vs. Louvain?"
> "Both are community detection algorithms used for clustering cells in single-cell analysis. Louvain can produce disconnected communities and is technically not guaranteed to converge. Leiden fixes this — it's provably well-connected and generally produces higher quality clusters. Scanpy uses Leiden by default for this reason."

---

## System Design Questions

### "How would you design a scalable version of BioOrchestrator?"

> "For a production pharma deployment, I'd make three main changes. First, replace SQLite with PostgreSQL for multi-user concurrent access and proper ACID guarantees — the current task state, project, and audit tables map cleanly to relational schema. Second, replace local file storage with object storage — S3 or GCS — for uploaded scRNA-seq files, since h5ad files can be 5GB+. Third, containerize the omics pipeline as a separate worker service rather than running it in the Streamlit thread — probably Celery or a managed queue like SQS, with the Streamlit app just submitting jobs and polling status. The LLM reasoning layer is already designed for horizontal scale with the multi-provider fallback chain."

### "How does the AI reasoning work?"

> "The ReasoningEngine uses a tool-calling loop pattern. It gets a system prompt from a versioned registry, calls the LLM with a gene symbol, disease context, and aggregated evidence. The LLM can call 14 tools — things like `query_opentargets`, `gene_expression`, `de_results`, `enrichment_summary` — and the tool results are appended to the message history as tool_result blocks. This repeats for up to 10 rounds until the model stops calling tools. Five modes run in parallel via a fallback chain: Claude primary, then Groq, then Ollama. A HallucinationChecker validates that cited genes and claims appear in the actual evidence."

---

## Competitive Landscape — Know These

| Company | What They Do | How BioOrchestrator Differs |
|---------|-------------|---------------------------|
| Recursion | Drug discovery company using AI internally | Not a platform sold to others |
| BenevolentAI | Knowledge graph + AI for target ID | No scRNA-seq, no GxP compliance |
| Schrödinger | Physics-based molecular simulation | Different layer (post-target, pre-clinical) |
| Partek Flow | Browser-based scRNA-seq analysis | No AI reasoning, no target triage |
| OpenTargets | Public DB, not a platform | Data source, not a workflow tool |

---

## Salary Negotiation Numbers (2025-2026)

| Level | Big Pharma Base | Biotech Base | Equity |
|-------|----------------|--------------|--------|
| Senior (IC3/IC4) | $180K–$240K | $200K–$280K | 0.05–0.2% |
| Staff (IC5) | $240K–$320K | $280K–$400K | 0.1–0.5% |
| Principal (IC6) | $300K–$420K | $350K–$500K+ | 0.2–1%+ |

**Anchor high.** Your GxP compliance expertise + working product puts you at IC4 minimum.
