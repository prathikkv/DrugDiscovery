# Phase 3: Evidence Integration - Research

**Researched:** 2026-05-10
**Domain:** External API integration, data aggregation, caching, gene alias resolution
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 implements the evidence integration layer: a system that fetches, caches, and aggregates structured evidence from six external bioinformatics APIs (OpenTargets, DGIdb, PubMed, ClinicalTrials.gov, UniProt, ChEMBL) for any gene target, returning a unified evidence profile. The architecture follows a well-established pattern: abstract source interface, parallel fetch via ThreadPoolExecutor (already proven in the codebase), SQLite cache with TTL, and gene alias resolution as a preprocessing step.

The key technical challenge is not individual API calls (each is straightforward REST/GraphQL) but rather the orchestration: handling partial failures gracefully (one source failing must not block others), managing rate limits per-source, caching intelligently with manual invalidation, and resolving gene aliases before dispatch.

**Primary recommendation:** Build each evidence source as an independent module implementing a common Python Protocol class. Use `tenacity` for retry/backoff logic on each source independently. Use a shared ThreadPoolExecutor (max_workers=6) for parallel fetch. Store cached responses in a dedicated SQLite database (`data/db/evidence_cache.db`) using the established WAL-mode pattern from `src/db.py`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | >=2.31 | HTTP client for all REST APIs | Universal Python HTTP library, synchronous (fits ThreadPoolExecutor model) |
| tenacity | >=8.2 | Retry with exponential backoff | De facto standard for Python retry logic; decorator-based, composable |
| biopython | >=1.83 | PubMed/Entrez access via Bio.Entrez | Official NCBI-recommended Python interface |
| mygene | >=3.2 | Gene alias resolution via MyGene.info | Official Python client from BioThings team |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| chembl_webresource_client | >=0.10 | ChEMBL API access | For ChEMBL bioactivity queries -- handles pagination/caching internally |
| dgipy | >=0.3 | DGIdb Python client | Optional -- can use raw GraphQL via requests if dgipy is too limited |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| requests (sync) | httpx (async) | Async is faster but contradicts the ThreadPoolExecutor decision; more complex error handling |
| tenacity | urllib3 Retry | urllib3 Retry is transport-level only; tenacity works at application level with custom logic |
| chembl_webresource_client | raw requests to ChEMBL REST | Client handles pagination and local caching automatically; raw requests give more control |
| mygene Python package | raw requests to mygene.info | Package handles batch queries and retries; minimal overhead |
| dgipy | raw GraphQL queries | dgipy may be limited; raw GraphQL gives full control over query structure |

**Installation:**
```bash
pip install requests tenacity biopython mygene chembl-webresource-client
# Optional: pip install dgipy
```

## Architecture Patterns

### Recommended Project Structure
```
src/evidence/
├── __init__.py              # Public API: EvidenceAggregator, gather_evidence()
├── models.py                # EvidenceResult, EvidenceRecord, SourceStatus dataclasses
├── interface.py             # Abstract EvidenceSource Protocol
├── aggregator.py            # Parallel fetch orchestrator using ThreadPoolExecutor
├── cache.py                 # SQLite evidence cache with TTL + manual invalidation
├── gene_resolver.py         # MyGene.info + local alias fallback
├── sources/
│   ├── __init__.py          # Registry of all sources
│   ├── opentargets.py       # OpenTargets GraphQL (genetic assoc, tractability, drugs)
│   ├── dgidb.py             # DGIdb GraphQL (druggability, interactions)
│   ├── pubmed.py            # PubMed via Bio.Entrez (papers, abstracts)
│   ├── clinicaltrials.py    # ClinicalTrials.gov REST v2 (active trials)
│   ├── uniprot.py           # UniProt REST (protein function, location, domains)
│   └── chembl.py            # ChEMBL REST (bioactivity, compounds, MoA)
tests/
└── test_evidence/
    ├── conftest.py          # Fixtures: mock responses, test gene symbols
    ├── test_aggregator.py
    ├── test_cache.py
    ├── test_gene_resolver.py
    └── test_sources/
        ├── test_opentargets.py
        ├── test_dgidb.py
        ├── test_pubmed.py
        ├── test_clinicaltrials.py
        ├── test_uniprot.py
        └── test_chembl.py
```

### Pattern 1: Abstract Evidence Source Protocol
**What:** Each source implements a common interface with `source_name`, `source_version`, `fetch()`, and `is_available()`.
**When to use:** Always -- this is REQ-211.
**Example:**
```python
# src/evidence/interface.py
from typing import Protocol, runtime_checkable
from src.evidence.models import EvidenceResult

@runtime_checkable
class EvidenceSource(Protocol):
    """Abstract interface all evidence sources must implement (REQ-211)."""

    @property
    def source_name(self) -> str:
        """Unique identifier, e.g. 'opentargets', 'chembl'."""
        ...

    @property
    def source_version(self) -> str:
        """API version or data release, e.g. '24.09', 'v2'."""
        ...

    def fetch(self, gene_symbol: str, disease_context: str | None = None) -> EvidenceResult:
        """Fetch evidence for a canonical gene symbol.

        Args:
            gene_symbol: Canonical gene symbol (already resolved).
            disease_context: Optional disease name/EFO ID for filtering.

        Returns:
            EvidenceResult with structured data and metadata.

        Raises:
            Should NOT raise -- catch errors internally, return
            EvidenceResult with confidence=0.0 and error flag.
        """
        ...

    def is_available(self) -> bool:
        """Quick health check (lightweight ping, cached for 5 min)."""
        ...
```

### Pattern 2: Parallel Aggregation with Graceful Degradation
**What:** Fetch from all sources in parallel. If one fails, others still succeed. Failed sources return confidence=0.0.
**When to use:** For every evidence query (REQ-208, REQ-210).
**Example:**
```python
# src/evidence/aggregator.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.evidence.interface import EvidenceSource
from src.evidence.cache import EvidenceCache
from src.evidence.gene_resolver import GeneResolver
from src.evidence.models import EvidenceResult, AggregatedEvidence

class EvidenceAggregator:
    def __init__(
        self,
        sources: list[EvidenceSource],
        cache: EvidenceCache,
        gene_resolver: GeneResolver,
        max_workers: int = 6,
        timeout: float = 60.0,
    ):
        self.sources = sources
        self.cache = cache
        self.gene_resolver = gene_resolver
        self.max_workers = max_workers
        self.timeout = timeout

    def gather(
        self, gene_symbol: str, disease_context: str | None = None
    ) -> AggregatedEvidence:
        """Fetch evidence from all sources (REQ-201 through REQ-206).

        1. Resolve gene alias to canonical symbol (REQ-209)
        2. Check cache for each source (REQ-207)
        3. Fetch uncached sources in parallel (REQ-208)
        4. Handle failures gracefully (REQ-210)
        """
        # Step 1: Gene resolution
        canonical = self.gene_resolver.resolve(gene_symbol)

        # Step 2: Check cache, identify what needs fetching
        results: dict[str, EvidenceResult] = {}
        sources_to_fetch: list[EvidenceSource] = []

        for source in self.sources:
            cached = self.cache.get(canonical, source.source_name)
            if cached is not None:
                results[source.source_name] = cached
            else:
                sources_to_fetch.append(source)

        # Step 3: Parallel fetch
        if sources_to_fetch:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(source.fetch, canonical, disease_context): source
                    for source in sources_to_fetch
                }
                for future in as_completed(futures, timeout=self.timeout):
                    source = futures[future]
                    try:
                        result = future.result()
                        results[source.source_name] = result
                        self.cache.put(canonical, source.source_name, result)
                    except Exception as exc:
                        # REQ-210: graceful degradation
                        results[source.source_name] = EvidenceResult(
                            source_name=source.source_name,
                            confidence=0.0,
                            data=None,
                            error=str(exc),
                            is_fallback=True,
                        )

        return AggregatedEvidence(
            gene_symbol=canonical,
            query_symbol=gene_symbol,
            disease_context=disease_context,
            results=results,
        )
```

### Pattern 3: SQLite Cache with TTL and Manual Invalidation
**What:** Cache API responses in SQLite with configurable TTL (default 24h). Support manual invalidation per gene or per source.
**When to use:** Every API response gets cached (REQ-207).
**Example:**
```python
# src/evidence/cache.py
import json
import time
from pathlib import Path
from src.db import get_connection
from src import config

CACHE_SCHEMA = """\
CREATE TABLE IF NOT EXISTS evidence_cache (
    gene_symbol     TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    fetched_at      REAL NOT NULL,  -- Unix timestamp
    expires_at      REAL NOT NULL,  -- Unix timestamp
    data_json       TEXT NOT NULL,
    PRIMARY KEY (gene_symbol, source_name)
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON evidence_cache(expires_at);
"""

class EvidenceCache:
    def __init__(self, db_path: Path = None, ttl_seconds: int = 86400):
        self.db_path = db_path or config.DB_DIR / "evidence_cache.db"
        self.ttl_seconds = ttl_seconds
        conn = get_connection(self.db_path)
        try:
            conn.executescript(CACHE_SCHEMA)
        finally:
            conn.close()

    def get(self, gene_symbol: str, source_name: str) -> EvidenceResult | None:
        """Return cached result if not expired, else None."""
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT data_json, expires_at FROM evidence_cache "
                "WHERE gene_symbol = ? AND source_name = ?",
                (gene_symbol, source_name),
            ).fetchone()
            if row is None:
                return None
            if time.time() > row["expires_at"]:
                return None  # Expired
            return EvidenceResult.from_json(row["data_json"])
        finally:
            conn.close()

    def put(self, gene_symbol: str, source_name: str, result: EvidenceResult) -> None:
        """Store result with TTL."""
        now = time.time()
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO evidence_cache "
                "(gene_symbol, source_name, fetched_at, expires_at, data_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (gene_symbol, source_name, now, now + self.ttl_seconds,
                 result.to_json()),
            )
            conn.commit()
        finally:
            conn.close()

    def invalidate(self, gene_symbol: str = None, source_name: str = None) -> int:
        """Manual cache invalidation. Returns number of entries removed."""
        conditions = []
        params = []
        if gene_symbol:
            conditions.append("gene_symbol = ?")
            params.append(gene_symbol)
        if source_name:
            conditions.append("source_name = ?")
            params.append(source_name)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                f"DELETE FROM evidence_cache {where}", params
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
```

### Pattern 4: Per-Source Retry with Tenacity
**What:** Each source wraps its HTTP calls with tenacity retry decorators. 3 retries, exponential backoff, retry only on transient errors.
**When to use:** Every external API call (REQ-210).
**Example:**
```python
# Inside any source, e.g. src/evidence/sources/opentargets.py
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

class OpenTargetsSource:
    BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    )
    def _query(self, graphql_query: str, variables: dict) -> dict:
        """Execute GraphQL query with retry."""
        resp = requests.post(
            self.BASE_URL,
            json={"query": graphql_query, "variables": variables},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
```

### Pattern 5: Gene Alias Resolution
**What:** Before fetching evidence, resolve gene aliases to canonical symbols (e.g., PD-L1 -> CD274, HER2 -> ERBB2) using MyGene.info with a local fallback dictionary.
**When to use:** Every query before dispatching to sources (REQ-209).
**Example:**
```python
# src/evidence/gene_resolver.py
import mygene

# Local fallback for common aliases that scientists use
LOCAL_ALIASES = {
    "PD-L1": "CD274",
    "PD-1": "PDCD1",
    "HER2": "ERBB2",
    "HER3": "ERBB3",
    "p53": "TP53",
    "VEGF": "VEGFA",
    "TNF-alpha": "TNF",
    "IL-6R": "IL6R",
    "CTLA-4": "CTLA4",
    "GIPR": "GIPR",  # Already canonical
    "GLP1R": "GLP1R",  # Already canonical
}

class GeneResolver:
    def __init__(self):
        self.mg = mygene.MyGeneInfo()
        self._cache: dict[str, str] = {}

    def resolve(self, symbol: str) -> str:
        """Resolve gene alias to canonical HGNC symbol.

        1. Check local cache
        2. Check LOCAL_ALIASES dict
        3. Query MyGene.info
        4. Fall back to input symbol if unresolvable
        """
        normalized = symbol.strip().upper()

        # Local cache hit
        if normalized in self._cache:
            return self._cache[normalized]

        # Local aliases
        if normalized in LOCAL_ALIASES:
            canonical = LOCAL_ALIASES[normalized]
            self._cache[normalized] = canonical
            return canonical

        # MyGene.info lookup
        try:
            result = self.mg.query(
                symbol, scopes="symbol,alias", species="human",
                fields="symbol", size=1
            )
            if result.get("hits"):
                canonical = result["hits"][0].get("symbol", symbol)
                self._cache[normalized] = canonical
                return canonical
        except Exception:
            pass  # Fall through to returning input

        # Unresolvable -- use as-is
        self._cache[normalized] = symbol
        return symbol
```

### Anti-Patterns to Avoid
- **Serial API calls:** Never fetch sources sequentially. 6 sources x 5s each = 30s serial vs ~5s parallel.
- **Global retry on aggregator:** Retry must happen per-source, not on the aggregator. One source having transient issues must not re-fetch all sources.
- **Storing raw JSON blobs without schema:** Always parse API responses into typed dataclasses. Raw JSON makes downstream code fragile.
- **Raising exceptions from source.fetch():** Sources should catch all exceptions internally and return EvidenceResult with confidence=0.0. Only the aggregator timeout should cause an exception.
- **Shared mutable state in sources:** Each source fetch runs in its own thread. No shared state. Each creates its own HTTP session or uses thread-local storage.
- **Caching errors indefinitely:** Only cache successful results. Errors with confidence=0.0 should NOT be cached (next query should retry).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom while-loop with sleep | `tenacity` decorators | Handles edge cases: jitter, conditional retry, logging, timeout |
| Gene alias resolution | Custom web scraper + manual mapping | `mygene` Python package + local dict | MyGene.info aggregates NCBI, Ensembl, UniProt aliases |
| ChEMBL pagination | Manual offset tracking | `chembl_webresource_client` | Client handles lazy pagination, local caching, rate limiting |
| PubMed search | Raw HTTP to NCBI | `Bio.Entrez` (Biopython) | Handles API key, rate limits, auto-retry, XML parsing |
| HTTP session management | Custom connection pooling | `requests.Session()` | Keep-alive, connection reuse, cookie persistence |
| SQLite thread safety | Manual lock management | Existing `src/db.get_connection()` | Already configured: WAL mode, busy_timeout, check_same_thread=False |

**Key insight:** Every external API in this phase has either an official Python client or a well-tested community package. The value is in orchestration and normalization, not in raw HTTP handling.

## Common Pitfalls

### Pitfall 1: OpenTargets Rate Limiting / Query Too Large
**What goes wrong:** Fetching all associations for a gene (50K+ rows) causes timeout or IP throttling. OpenTargets discourages repeated single-entity queries.
**Why it happens:** Default GraphQL queries without pagination or score filters return enormous result sets.
**How to avoid:** Filter by `score > 0.1` in GraphQL query, limit to top 25 diseases by score, cache aggressively. For the MVP, single-gene queries are acceptable at our scale (not thousands of genes).
**Warning signs:** Queries taking >10s, 429 status codes, empty responses.

### Pitfall 2: PubMed IP Ban Without API Key
**What goes wrong:** NCBI rate-limits to 3 requests/second without API key. During parallel fetches for multiple genes, this is easy to exceed.
**Why it happens:** Bio.Entrez defaults to 3 req/s without `Entrez.api_key` set.
**How to avoid:** Register for free NCBI API key (raises limit to 10 req/s). Always set `Entrez.email` and `Entrez.api_key`. Batch abstract fetches (efetch with multiple IDs) rather than individual requests.
**Warning signs:** HTTP 429 errors from NCBI, `urllib.error.HTTPError: 429`.

### Pitfall 3: ChEMBL Gene Name Lookup Failure
**What goes wrong:** ChEMBL does not support gene symbol lookup directly. Querying by gene name returns nothing.
**Why it happens:** ChEMBL uses its own target IDs (CHEMBL_TARGET_ID). Must first resolve gene -> UniProt accession -> ChEMBL target ID.
**How to avoid:** Resolution chain: gene_symbol -> UniProt (via UniProt API or gene_resolver) -> UniProt accession -> ChEMBL target search by `target_components.accession`. Cache the gene-to-ChEMBL-ID mapping.
**Warning signs:** Empty bioactivity results for known drug targets (e.g., EGFR should have thousands of compounds).

### Pitfall 4: ClinicalTrials.gov v1 API Code (Deprecated June 2024)
**What goes wrong:** Old code examples and libraries use the deprecated v1 API at `clinicaltrials.gov/api/query/`. These will fail.
**Why it happens:** Most tutorials and StackOverflow answers reference v1. The classic API was retired in June 2024.
**How to avoid:** Use only v2 endpoint: `https://clinicaltrials.gov/api/v2/studies`. Use `query.cond` and `query.intr` parameters (not the old field syntax). Rate limit: ~50 req/min.
**Warning signs:** 404 errors, redirect to modernized site, "pytrials" library using old endpoints.

### Pitfall 5: Cache Stampede on Expiration
**What goes wrong:** When cache expires for a popular gene, multiple concurrent requests all trigger fresh API fetches simultaneously.
**Why it happens:** TTL-based expiration without coordination leads to thundering herd.
**How to avoid:** Use "stale-while-revalidate" pattern: serve stale cache while one thread refreshes. Or use a simple lock per (gene, source) key. At our scale (single-user Streamlit app), this is LOW risk but worth noting for future scaling.
**Warning signs:** Burst of identical API calls in logs after exactly 24h.

### Pitfall 6: UniProt Old vs New API Endpoint
**What goes wrong:** Using old `https://www.uniprot.org/uniprot` endpoint which is deprecated. New API is at `https://rest.uniprot.org/uniprotkb/search`.
**Why it happens:** Many tutorials still reference the old endpoint.
**How to avoid:** Use `https://rest.uniprot.org/uniprotkb/search` with `query`, `fields`, and `format=json` parameters. The `fields` parameter is critical to reduce response size by 90%.
**Warning signs:** Redirects, unexpected HTML responses, missing fields in response.

### Pitfall 7: Thread Safety of Bio.Entrez Module
**What goes wrong:** Bio.Entrez uses module-level globals (`Entrez.email`, `Entrez.api_key`). If multiple threads modify these, race conditions occur.
**Why it happens:** Bio.Entrez was not designed for multi-threaded use.
**How to avoid:** Set `Entrez.email` and `Entrez.api_key` once at module import (they are read-only after that). The actual HTTP calls are thread-safe since each creates its own connection. Just do not modify module globals in threads.
**Warning signs:** Intermittent authentication failures in multi-threaded scenarios.

## Code Examples

### OpenTargets: Target-Disease Associations + Tractability
```python
# Source: https://platform-docs.opentargets.org/data-access/graphql-api
import requests

OPENTARGETS_URL = "https://api.platform.opentargets.org/api/v4/graphql"

QUERY_TARGET = """
query TargetInfo($ensemblId: String!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    approvedName
    biotype
    tractability {
      label
      modality
      value
    }
    knownDrugs {
      uniqueDrugs
      rows {
        drug { name mechanismsOfAction { rows { mechanismOfAction } } }
        disease { name }
        phase
        status
      }
    }
  }
}
"""

QUERY_ASSOCIATIONS = """
query DiseaseAssociations($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    associatedDiseases(page: {size: $size, index: 0}) {
      count
      rows {
        score
        disease { id name }
        datatypeScores {
          id
          score
        }
      }
    }
  }
}
"""

def fetch_opentargets(ensembl_id: str) -> dict:
    """Fetch target info and top disease associations."""
    # Target info (tractability, known drugs)
    resp = requests.post(OPENTARGETS_URL, json={
        "query": QUERY_TARGET,
        "variables": {"ensemblId": ensembl_id}
    }, timeout=30)
    resp.raise_for_status()
    target_data = resp.json()["data"]["target"]

    # Top 25 disease associations
    resp = requests.post(OPENTARGETS_URL, json={
        "query": QUERY_ASSOCIATIONS,
        "variables": {"ensemblId": ensembl_id, "size": 25}
    }, timeout=30)
    resp.raise_for_status()
    assoc_data = resp.json()["data"]["target"]["associatedDiseases"]

    return {"target": target_data, "associations": assoc_data}
```

### DGIdb: Drug-Gene Interactions
```python
# Source: https://dgidb.org/api
import requests

DGIDB_URL = "https://dgidb.org/api/graphql"

QUERY_INTERACTIONS = """
query GeneInteractions($geneName: String!) {
  genes(names: [$geneName]) {
    nodes {
      name
      longName
      geneCategories {
        name
      }
      interactions {
        drug {
          name
          conceptId
          approved
        }
        interactionScore
        interactionTypes {
          type
          directionality
        }
        publications {
          pmid
        }
        sources {
          sourceDbName
        }
      }
    }
  }
}
"""

def fetch_dgidb(gene_symbol: str) -> dict:
    resp = requests.post(DGIDB_URL, json={
        "query": QUERY_INTERACTIONS,
        "variables": {"geneName": gene_symbol}
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]["genes"]["nodes"]
```

### PubMed: Recent Papers with Abstracts
```python
# Source: Biopython Bio.Entrez documentation
from Bio import Entrez

Entrez.email = "user@example.com"  # Required
Entrez.api_key = "YOUR_NCBI_API_KEY"  # 10 req/s vs 3 req/s

def fetch_pubmed(gene_symbol: str, disease: str = None, max_results: int = 10) -> list:
    """Fetch recent papers for a gene, optionally filtered by disease."""
    query = f"{gene_symbol}[Title/Abstract]"
    if disease:
        query += f" AND {disease}[Title/Abstract]"
    query += " AND (\"last 5 years\"[PDat])"

    # Search for PMIDs
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, sort="relevance")
    search_results = Entrez.read(handle)
    handle.close()
    pmids = search_results["IdList"]

    if not pmids:
        return []

    # Fetch abstracts in batch
    handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml")
    records = Entrez.read(handle)
    handle.close()

    papers = []
    for article in records.get("PubmedArticle", []):
        medline = article["MedlineCitation"]
        art = medline["Article"]
        papers.append({
            "pmid": str(medline["PMID"]),
            "title": art.get("ArticleTitle", ""),
            "abstract": art.get("Abstract", {}).get("AbstractText", [""])[0] if art.get("Abstract") else "",
            "year": medline.get("DateCompleted", {}).get("Year", ""),
            "journal": art.get("Journal", {}).get("Title", ""),
        })

    return papers
```

### ClinicalTrials.gov v2: Active Trials
```python
# Source: ClinicalTrials.gov API v2 documentation
import requests

CT_BASE = "https://clinicaltrials.gov/api/v2/studies"

def fetch_clinical_trials(
    condition: str, intervention: str = None, max_results: int = 50
) -> list:
    """Fetch active clinical trials for a condition."""
    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,NOT_YET_RECRUITING",
        "pageSize": min(max_results, 100),
        "format": "json",
    }
    if intervention:
        params["query.intr"] = intervention

    all_studies = []
    while len(all_studies) < max_results:
        resp = requests.get(CT_BASE, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        studies = data.get("studies", [])
        all_studies.extend(studies)

        next_token = data.get("nextPageToken")
        if not next_token or len(studies) == 0:
            break
        params["pageToken"] = next_token

    return [
        {
            "nct_id": s["protocolSection"]["identificationModule"]["nctId"],
            "title": s["protocolSection"]["identificationModule"]["briefTitle"],
            "status": s["protocolSection"]["statusModule"]["overallStatus"],
            "phase": s["protocolSection"].get("designModule", {}).get("phases", []),
            "sponsor": s["protocolSection"].get("sponsorCollaboratorsModule", {})
                        .get("leadSponsor", {}).get("name", ""),
            "conditions": s["protocolSection"].get("conditionsModule", {})
                          .get("conditions", []),
            "interventions": [
                i.get("name", "") for i in
                s["protocolSection"].get("armsInterventionsModule", {})
                .get("interventions", [])
            ],
        }
        for s in all_studies
    ]
```

### UniProt: Protein Function and Location
```python
# Source: https://rest.uniprot.org documentation
import requests

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb/search"

def fetch_uniprot(gene_symbol: str) -> dict:
    """Fetch protein function, subcellular location, domains from UniProt."""
    params = {
        "query": f"(gene_exact:{gene_symbol}) AND (organism_id:9606) AND (reviewed:true)",
        "fields": "accession,gene_names,protein_name,cc_function,cc_subcellular_location,"
                  "ft_domain,ft_binding,structure_3d,length",
        "format": "json",
        "size": 1,
    }
    resp = requests.get(UNIPROT_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    if not results:
        return {}

    entry = results[0]
    return {
        "accession": entry.get("primaryAccession"),
        "protein_name": entry.get("proteinDescription", {})
                        .get("recommendedName", {}).get("fullName", {}).get("value", ""),
        "function": [c.get("texts", [{}])[0].get("value", "")
                     for c in entry.get("comments", [])
                     if c.get("commentType") == "FUNCTION"],
        "subcellular_location": [
            loc.get("location", {}).get("value", "")
            for c in entry.get("comments", [])
            if c.get("commentType") == "SUBCELLULAR LOCATION"
            for loc in c.get("subcellularLocations", [])
        ],
        "domains": [f.get("description", "")
                    for f in entry.get("features", [])
                    if f.get("type") == "Domain"],
        "has_structure": entry.get("structure3D", False),
        "length": entry.get("sequence", {}).get("length"),
    }
```

### ChEMBL: Bioactivity Data
```python
# Source: https://github.com/chembl/chembl_webresource_client
from chembl_webresource_client.new_client import new_client

def fetch_chembl(gene_symbol: str, uniprot_accession: str = None) -> dict:
    """Fetch bioactivity and compound data from ChEMBL.

    Note: ChEMBL requires UniProt accession to find target.
    If not provided, must resolve via UniProt first.
    """
    target_api = new_client.target
    activity_api = new_client.activity
    molecule_api = new_client.molecule

    # Step 1: Find ChEMBL target by UniProt accession
    if uniprot_accession:
        targets = target_api.filter(
            target_components__accession=uniprot_accession
        )
    else:
        targets = target_api.search(gene_symbol)

    if not targets:
        return {"compounds": [], "activities": []}

    target_chembl_id = targets[0]["target_chembl_id"]
    target_type = targets[0]["target_type"]

    # Step 2: Fetch bioactivities with pChEMBL values
    activities = activity_api.filter(
        target_chembl_id=target_chembl_id,
        pchembl_value__isnull=False,
    ).only(
        "molecule_chembl_id", "pchembl_value", "standard_type",
        "standard_value", "standard_units", "canonical_smiles",
    )[:50]  # Limit to top 50

    # Step 3: Get mechanism of action
    mechanisms = new_client.mechanism.filter(target_chembl_id=target_chembl_id)

    return {
        "target_chembl_id": target_chembl_id,
        "target_type": target_type,
        "activities": list(activities),
        "mechanisms": list(mechanisms),
        "activity_count": len(list(activities)),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ClinicalTrials.gov v1 API | v2 REST API (OpenAPI 3.0) | June 2024 (v1 retired) | New URL, new parameter names, JSON-first |
| UniProt old endpoint (`/uniprot`) | REST at `rest.uniprot.org` | 2022-2023 | New endpoint, `fields` parameter, better JSON |
| Open Targets Genetics (separate) | Merged into Platform API | 2024 | Single endpoint for both genetics + platform data |
| DGIdb REST API | DGIdb v5 GraphQL API | 2023 | GraphQL replaces REST, richer query capability |
| ChEMBL Python client (old) | `chembl_webresource_client` (maintained) | Ongoing | Still actively maintained, handles pagination |
| NCBI Entrez (no API key) | API key required for production use | 2018+ | 10 req/s vs 3 req/s; key is free to register |

**Deprecated/outdated:**
- ClinicalTrials.gov v1 API: Retired June 2024. Any code using `/api/query/` will fail.
- UniProt old search endpoint: `https://www.uniprot.org/uniprot` redirects to new API.
- `pytrials` library: May still use v1 endpoints. Verify before using.

## Open Questions

1. **OpenTargets Ensembl ID resolution**
   - What we know: OpenTargets requires Ensembl gene IDs (ENSG...), not gene symbols.
   - What's unclear: Best approach to map gene symbol -> Ensembl ID. MyGene.info can do this, or OpenTargets search endpoint.
   - Recommendation: Add Ensembl ID lookup to GeneResolver (MyGene.info returns `ensembl.gene` field). Cache the mapping.

2. **NCBI API Key management**
   - What we know: Free API key raises rate limit from 3 to 10 req/s. Required for production.
   - What's unclear: How to manage the key (env variable vs config file).
   - Recommendation: Use environment variable `NCBI_API_KEY` with fallback to `src/config.py` constant. Document registration in setup guide.

3. **DGIdb interaction score threshold**
   - What we know: PITFALLS.md recommends filtering `interactionScore > 0.5` with 2+ publications.
   - What's unclear: What the score range actually is and whether 0.5 is appropriate.
   - Recommendation: Start with no filter, analyze distribution for EGFR, then set threshold empirically. Make threshold configurable.

4. **ChEMBL activity volume for popular targets**
   - What we know: EGFR has 50,000+ bioactivity records in ChEMBL.
   - What's unclear: Whether limiting to top 50 by pChEMBL is sufficient for scoring.
   - Recommendation: Fetch top 50 by pChEMBL value (descending). Provide count of total activities as metadata. Scoring only needs summary statistics (mean, max pChEMBL).

5. **Gene symbol to UniProt accession mapping for ChEMBL**
   - What we know: ChEMBL requires UniProt accession or ChEMBL target ID (not gene symbol).
   - What's unclear: Whether to use UniProt API or MyGene.info for this mapping.
   - Recommendation: GeneResolver should return both canonical symbol AND UniProt accession. MyGene.info's `querymany` with `fields="symbol,uniprot"` returns both.

## Sources

### Primary (HIGH confidence)
- Open Targets Platform GraphQL API docs: https://platform-docs.opentargets.org/data-access/graphql-api
- ClinicalTrials.gov API v2 documentation: https://clinicaltrials.gov/data-api/api
- Biopython Bio.Entrez docs (v1.86): https://biopython.org/docs/latest/api/Bio.Entrez.html
- ChEMBL web resource client GitHub: https://github.com/chembl/chembl_webresource_client
- MyGene.info documentation: https://docs.mygene.info/en/latest/doc/query_service.html
- UniProt REST API docs: https://www.uniprot.org/help/programmatic_access
- Tenacity documentation: https://tenacity.readthedocs.io/en/stable/
- Existing codebase patterns: `src/db.py`, `src/execution/task_manager.py`, `src/config.py`

### Secondary (MEDIUM confidence)
- DGIdb v5 API documentation (JS-rendered, limited static content): https://dgidb.org/api
- DGIdb 5.0 paper (Nucleic Acids Research 2024): https://academic.oup.com/nar/article/52/D1/D1227/7416371
- NLM Technical Bulletin on ClinicalTrials.gov API v2: https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_clinicaltrials_api.html
- UniProt API 2025 paper: https://academic.oup.com/nar/article/53/W1/W547/8126256

### Tertiary (LOW confidence)
- DGIdb GraphQL query examples (reconstructed from search results, not directly verified in live playground)
- ClinicalTrials.gov rate limit (~50 req/min) -- from community-maintained reference, not official docs
- UniProt `gene_exact` field name -- inferred from query field documentation, not directly tested

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- requests, tenacity, biopython, mygene are well-established; versions verified via PyPI
- Architecture: HIGH -- follows patterns already proven in this codebase (ThreadPoolExecutor, SQLite WAL, Protocol classes)
- API endpoints: MEDIUM-HIGH -- OpenTargets, ChEMBL, PubMed endpoints verified via official docs; ClinicalTrials.gov v2 confirmed; UniProt and DGIdb needed JavaScript-rendered pages (verified via multiple sources)
- Pitfalls: MEDIUM -- integration gotchas from PITFALLS.md (HIGH confidence) + API-specific issues from web research (MEDIUM)
- Code examples: MEDIUM -- constructed from documented APIs and official examples; not tested against live endpoints

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (30 days -- APIs are stable; check for version bumps on OpenTargets which releases quarterly)
