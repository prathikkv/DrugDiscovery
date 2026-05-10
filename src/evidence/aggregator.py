"""Evidence aggregator: parallel orchestrator for all evidence sources.

Implements two-phase fetch (REQ-204):
  Phase 1: Fetch OpenTargets, DGIdb, PubMed, UniProt, ChEMBL in parallel
  Phase 2: Fetch ClinicalTrials with drug names extracted from DGIdb results

Handles cache integration, gene resolution, and graceful degradation with
stale cache fallback (REQ-210 step 2).
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from src.evidence.cache import EvidenceCache
from src.evidence.gene_resolver import GeneResolver
from src.evidence.models import AggregatedEvidence, EvidenceResult, GeneIdentifiers
from src.evidence.sources import get_default_sources

logger = logging.getLogger(__name__)


class EvidenceAggregator:
    """Parallel evidence fetch orchestrator.

    Resolves gene symbols, checks cache, dispatches parallel fetches to all
    6 sources using a two-phase strategy (DGIdb first for drug names, then
    ClinicalTrials), and returns a unified AggregatedEvidence object.

    Args:
        sources: List of EvidenceSource instances. If None, instantiates all 6 defaults.
        cache: EvidenceCache instance. If None, creates default.
        gene_resolver: GeneResolver instance. If None, creates default.
        max_workers: Maximum threads for parallel fetch. Default 6.
        timeout: Maximum seconds to wait for all futures. Default 60.
    """

    def __init__(
        self,
        sources=None,
        cache: Optional[EvidenceCache] = None,
        gene_resolver: Optional[GeneResolver] = None,
        max_workers: int = 6,
        timeout: float = 60.0,
    ) -> None:
        self.sources = sources if sources is not None else get_default_sources()
        self.cache = cache if cache is not None else EvidenceCache()
        self.gene_resolver = gene_resolver if gene_resolver is not None else GeneResolver()
        self.max_workers = max_workers
        self.timeout = timeout

    def gather(
        self,
        gene_symbol: str,
        disease_context: Optional[str] = None,
    ) -> AggregatedEvidence:
        """Resolve gene, fetch all sources in parallel, return aggregated evidence.

        This is the primary orchestration method implementing REQ-204 two-phase fetch:
        1. Resolve gene symbol to canonical identifiers
        2. Check cache for each source
        3. Phase 1: Parallel fetch (OpenTargets, DGIdb, PubMed, UniProt, ChEMBL)
        4. Extract drug names from DGIdb results
        5. Phase 2: Fetch ClinicalTrials with drug names
        6. Build and return AggregatedEvidence

        Args:
            gene_symbol: User-provided gene symbol or alias (e.g., 'PD-L1', 'EGFR').
            disease_context: Optional disease/indication string for context.

        Returns:
            AggregatedEvidence with results from all sources.
        """
        # Step 1: Resolve gene
        gene_ids = self.gene_resolver.resolve(gene_symbol)

        # Step 2: Check cache for each source
        results: dict[str, EvidenceResult] = {}
        sources_to_fetch = []

        for source in self.sources:
            cached = self.cache.get(gene_ids.canonical_symbol, source.source_name)
            if cached is not None:
                results[source.source_name] = cached
            else:
                sources_to_fetch.append(source)

        # Step 3: Two-phase fetch (REQ-204)
        phase1_sources = [s for s in sources_to_fetch if s.source_name != "clinicaltrials"]
        phase2_sources = [s for s in sources_to_fetch if s.source_name == "clinicaltrials"]

        # Phase 1: Parallel fetch (OpenTargets, DGIdb, PubMed, UniProt, ChEMBL)
        if phase1_sources:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(source.fetch, gene_ids, disease_context): source
                    for source in phase1_sources
                }
                for future in as_completed(futures, timeout=self.timeout):
                    source = futures[future]
                    try:
                        result = future.result()
                        results[source.source_name] = result
                        if result.confidence > 0.0:
                            self.cache.put(
                                gene_ids.canonical_symbol, source.source_name, result
                            )
                        else:
                            # REQ-210 step 2: stale cache fallback on failure
                            stale = self.cache.get_stale(
                                gene_ids.canonical_symbol, source.source_name
                            )
                            if stale is not None:
                                stale.is_fallback = True
                                results[source.source_name] = stale
                    except Exception as exc:
                        stale = self.cache.get_stale(
                            gene_ids.canonical_symbol, source.source_name
                        )
                        if stale is not None:
                            stale.is_fallback = True
                            results[source.source_name] = stale
                        else:
                            results[source.source_name] = EvidenceResult(
                                source_name=source.source_name,
                                confidence=0.0,
                                data=None,
                                error=f"Executor error: {exc}",
                                is_fallback=True,
                                fetched_at=time.time(),
                            )

        # Step 4: Extract drug names from DGIdb results (REQ-204)
        drug_names: list[str] = []
        dgidb_result = results.get("dgidb")
        if dgidb_result and dgidb_result.confidence > 0.0 and dgidb_result.data:
            interactions = dgidb_result.data.get("interactions", [])
            drug_names = [
                i["drug_name"] for i in interactions if i.get("drug_name")
            ][:10]  # top 10 drugs

        # Step 5: Phase 2 -- ClinicalTrials fetch with drug names
        if phase2_sources:
            ct_source = phase2_sources[0]
            try:
                result = ct_source.fetch(gene_ids, disease_context, drug_names=drug_names)
                results[ct_source.source_name] = result
                if result.confidence > 0.0:
                    self.cache.put(
                        gene_ids.canonical_symbol, ct_source.source_name, result
                    )
                else:
                    stale = self.cache.get_stale(
                        gene_ids.canonical_symbol, ct_source.source_name
                    )
                    if stale is not None:
                        stale.is_fallback = True
                        results[ct_source.source_name] = stale
            except Exception as exc:
                stale = self.cache.get_stale(
                    gene_ids.canonical_symbol, ct_source.source_name
                )
                if stale is not None:
                    stale.is_fallback = True
                    results[ct_source.source_name] = stale
                else:
                    results[ct_source.source_name] = EvidenceResult(
                        source_name=ct_source.source_name,
                        confidence=0.0,
                        data=None,
                        error=f"Executor error: {exc}",
                        is_fallback=True,
                        fetched_at=time.time(),
                    )

        # Step 6: Build AggregatedEvidence
        sources_failed = sum(
            1 for r in results.values() if r.confidence == 0.0
        )
        sources_available = len(results) - sources_failed

        return AggregatedEvidence(
            gene=gene_ids,
            disease_context=disease_context,
            results=results,
            fetched_at=time.time(),
            sources_available=sources_available,
            sources_failed=sources_failed,
        )

    def invalidate_cache(
        self,
        gene_symbol: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> int:
        """Invalidate cached evidence entries.

        Args:
            gene_symbol: If provided, invalidate only entries for this gene.
            source_name: If provided, invalidate only entries from this source.
            If both None, invalidates ALL entries.

        Returns:
            Number of cache entries removed.
        """
        return self.cache.invalidate(gene_symbol=gene_symbol, source_name=source_name)
