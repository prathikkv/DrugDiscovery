"""PubMed/Entrez evidence source.

Fetches recent publications from PubMed using NCBI Entrez utilities,
retrieves abstracts, and generates AI summaries of literature evidence.
"""

from __future__ import annotations

import logging
import os
import urllib.error

from Bio import Entrez
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.evidence.models import EvidenceResult, GeneIdentifiers

logger = logging.getLogger(__name__)

# Module-level Entrez configuration (thread-safe per Bio.Entrez docs)
Entrez.email = os.environ.get("NCBI_EMAIL", "bioorchestrator@example.com")
Entrez.api_key = os.environ.get("NCBI_API_KEY", None)


class PubMedSource:
    """Evidence source searching PubMed via NCBI Entrez utilities.

    Fetches recent publications (last 5 years) for a gene, retrieves
    abstracts, and generates an AI summary of the literature.
    """

    def __init__(self, max_results: int = 10) -> None:
        """Initialize PubMed source.

        Args:
            max_results: Maximum number of papers to retrieve (default 10).
        """
        self.max_results = max_results

    @property
    def source_name(self) -> str:
        """Unique identifier for this evidence source."""
        return "pubmed"

    @property
    def source_version(self) -> str:
        """Version string for this source's API/data."""
        return "entrez"

    def fetch(
        self,
        gene: GeneIdentifiers,
        disease_context: str | None = None,
    ) -> EvidenceResult:
        """Fetch recent PubMed literature for a gene.

        Args:
            gene: Resolved gene identifiers (uses canonical_symbol).
            disease_context: Optional disease name to narrow search.

        Returns:
            EvidenceResult with papers list, count, query, and AI summary.
        """
        try:
            # Build search query
            query = f'"{gene.canonical_symbol}"[Title/Abstract]'
            if disease_context:
                query += f' AND "{disease_context}"[Title/Abstract]'
            query += ' AND ("last 5 years"[PDat])'

            # Search for PMIDs
            pmids = self._search(query, self.max_results)

            if not pmids:
                # No literature found -- valid result, low confidence
                return EvidenceResult(
                    source_name=self.source_name,
                    confidence=0.3,
                    data={
                        "papers": [],
                        "total_count": 0,
                        "query_used": query,
                        "ai_summary": None,
                    },
                )

            # Fetch paper details with abstracts
            papers = self._fetch_abstracts(pmids)

            # Generate AI summary (best-effort, non-fatal)
            summary = self._summarize_abstracts(
                papers, gene.canonical_symbol, disease_context
            )

            # Build result data
            data = {
                "papers": papers,
                "total_count": len(papers),
                "query_used": query,
                "ai_summary": summary,
            }

            return EvidenceResult(
                source_name=self.source_name,
                confidence=1.0,
                data=data,
            )

        except Exception as e:
            return EvidenceResult(
                source_name=self.source_name,
                confidence=0.0,
                error=str(e),
                is_fallback=True,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((urllib.error.HTTPError, IOError)),
    )
    def _search(self, query: str, max_results: int) -> list[str]:
        """Search PubMed for matching PMIDs.

        Args:
            query: PubMed search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of PMID strings.

        Raises:
            urllib.error.HTTPError: On HTTP failure (retried).
            IOError: On network failure (retried).
        """
        handle = Entrez.esearch(
            db="pubmed", term=query, retmax=max_results, sort="relevance"
        )
        record = Entrez.read(handle)
        handle.close()
        return record.get("IdList", [])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((urllib.error.HTTPError, IOError)),
    )
    def _fetch_abstracts(self, pmids: list[str]) -> list[dict]:
        """Fetch paper details for a list of PMIDs.

        Args:
            pmids: List of PubMed ID strings.

        Returns:
            List of paper dicts with pmid, title, abstract, year, journal, authors.

        Raises:
            urllib.error.HTTPError: On HTTP failure (retried).
            IOError: On network failure (retried).
        """
        handle = Entrez.efetch(
            db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml"
        )
        records = Entrez.read(handle)
        handle.close()

        papers = []
        articles = records.get("PubmedArticle", [])

        for article in articles:
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})

            # Extract PMID
            pmid = str(medline.get("PMID", ""))

            # Extract title
            title = str(article_data.get("ArticleTitle", ""))

            # Extract abstract text
            abstract_parts = article_data.get("Abstract", {}).get(
                "AbstractText", []
            )
            if abstract_parts:
                abstract = " ".join(str(part) for part in abstract_parts)
            else:
                abstract = ""

            # Extract year
            pub_date = (
                article_data.get("Journal", {})
                .get("JournalIssue", {})
                .get("PubDate", {})
            )
            year = pub_date.get("Year", "")

            # Extract journal name
            journal = article_data.get("Journal", {}).get("Title", "")

            # Extract first 3 authors
            author_list = article_data.get("AuthorList", [])
            authors = []
            for author in author_list[:3]:
                last = author.get("LastName", "")
                fore = author.get("ForeName", "")
                if last:
                    authors.append(f"{last} {fore}".strip())

            papers.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "year": year,
                    "journal": journal,
                    "authors": authors,
                }
            )

        return papers

    def _summarize_abstracts(
        self,
        papers: list[dict],
        gene_symbol: str,
        disease_context: str | None,
    ) -> str | None:
        """Generate an AI summary of paper abstracts.

        Uses the LLM provider from src.execution.llm (when available).
        This is best-effort -- failure returns None without breaking the pipeline.

        Args:
            papers: List of paper dicts with abstracts.
            gene_symbol: Gene symbol for context in the prompt.
            disease_context: Optional disease context for the summary.

        Returns:
            Summary string, or None if generation fails.
        """
        try:
            # Lazy import to avoid hard dependency on Phase 4 module
            from src.execution.llm import get_llm_client  # noqa: F401

            # Build prompt
            context_str = (
                f" in the context of {disease_context}" if disease_context else ""
            )
            prompt = (
                f"Summarize the following {len(papers)} PubMed abstracts about "
                f"{gene_symbol}{context_str}. Focus on: key findings, therapeutic "
                f"implications, and emerging research directions. Be concise (3-5 sentences)."
            )

            # Concatenate abstracts (truncate to fit context window)
            abstract_texts = []
            total_chars = 0
            for paper in papers:
                text = f"Title: {paper['title']}\nAbstract: {paper['abstract']}\n\n"
                if total_chars + len(text) > 8000:
                    break
                abstract_texts.append(text)
                total_chars += len(text)

            content = "".join(abstract_texts)

            # Get LLM client and generate summary
            model = os.environ.get("LLM_SUMMARY_MODEL", "gpt-4o-mini")
            client = get_llm_client()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
                max_tokens=300,
                temperature=0.3,
            )
            return response.choices[0].message.content

        except ImportError:
            logger.debug(
                "LLM module not available (Phase 4); skipping abstract summary"
            )
            return None
        except Exception as e:
            logger.warning(f"Abstract summarization failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if PubMed/Entrez API is reachable.

        Returns:
            True if Entrez einfo responds successfully.
        """
        try:
            handle = Entrez.einfo(db="pubmed")
            Entrez.read(handle)
            handle.close()
            return True
        except Exception:
            return False
