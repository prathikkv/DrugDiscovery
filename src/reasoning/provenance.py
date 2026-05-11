"""Evidence hashing and provenance recording (REQ-305).

Provides SHA256 hashing of evidence data for reproducible provenance,
builds ProvenanceRecord instances from reasoning session metadata, records
provenance to the audit trail, and saves full tool-calling traces to disk.

Per research recommendation: full traces are stored in files, not in
audit trail details_json which should stay lean.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.reasoning.models import ProvenanceRecord, ToolTrace

logger = logging.getLogger(__name__)


class ProvenanceTracker:
    """Evidence hashing and provenance recording for the reasoning engine.

    Computes SHA256 hashes of input evidence for reproducibility, builds
    ProvenanceRecord instances with full session metadata, records to the
    audit trail, and saves reasoning traces to disk.

    Args:
        audit_trail: Optional AuditTrail instance for recording provenance events.
    """

    def __init__(self, audit_trail: Optional[Any] = None) -> None:
        self.audit_trail = audit_trail

    def hash_evidence(self, evidence_data: dict | str) -> str:
        """Compute SHA256 hash of evidence data.

        Args:
            evidence_data: Evidence data as dict or JSON string.

        Returns:
            64-character hexadecimal SHA256 digest string.
        """
        if isinstance(evidence_data, dict):
            serialized = json.dumps(
                evidence_data,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
        else:
            serialized = evidence_data

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def hash_aggregated_evidence(self, aggregated: Any) -> dict[str, str]:
        """Hash each source result in an AggregatedEvidence object.

        Args:
            aggregated: AggregatedEvidence instance with results dict mapping
                       source_name -> EvidenceResult.

        Returns:
            Dict mapping source_name -> SHA256 hash of that source's data.
        """
        hashes: dict[str, str] = {}
        for source_name, result in aggregated.results.items():
            # EvidenceResult.to_json() returns a deterministic JSON string
            hashes[source_name] = self.hash_evidence(result.to_json())
        return hashes

    def build_provenance(
        self,
        model_name: str,
        provider_name: str,
        prompt_version: str,
        input_evidence_hashes: dict[str, str],
        tool_trace: ToolTrace,
        fallback_events: Optional[list[dict]] = None,
    ) -> ProvenanceRecord:
        """Build a ProvenanceRecord from reasoning session metadata.

        Args:
            model_name: Name of the LLM model used (e.g., "qwen3:8b").
            provider_name: Name of the provider (e.g., "Ollama").
            prompt_version: SHA256 hash of the system prompt used.
            input_evidence_hashes: Dict mapping source_name -> SHA256 hash.
            tool_trace: ToolTrace from the tool-calling loop.
            fallback_events: Optional list of fallback event dicts.

        Returns:
            Fully populated ProvenanceRecord.
        """
        return ProvenanceRecord(
            model_name=model_name,
            provider_name=provider_name,
            prompt_version=prompt_version,
            input_evidence_hashes=input_evidence_hashes,
            tools_used=tool_trace.tools_used(),
            tool_rounds=tool_trace.total_rounds,
            fallback_events=fallback_events or [],
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def record_to_audit(
        self,
        provenance: ProvenanceRecord,
        gene_symbol: str,
        mode: str,
        user_id: str = "system",
    ) -> Optional[str]:
        """Record provenance to the audit trail.

        Args:
            provenance: ProvenanceRecord to record.
            gene_symbol: Gene symbol that was analyzed.
            mode: Reasoning mode used (e.g., "hypothesis").
            user_id: User ID for audit record (default "system").

        Returns:
            Audit record hash string, or None if no audit trail is configured.
        """
        if self.audit_trail is None:
            return None

        try:
            record_hash = self.audit_trail.append_record(
                user_id=user_id,
                action="ai_reasoning",
                resource_type="ai_reasoning",
                resource_id=f"{gene_symbol}:{mode}",
                details=provenance.to_audit_details(),
            )
            return record_hash
        except Exception as e:
            logger.warning("Failed to record provenance to audit trail: %s", e)
            return None

    def save_trace(
        self,
        trace_id: str,
        tool_trace: ToolTrace,
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Save a full tool-calling trace to disk as JSON.

        Per research recommendation: store full traces in files, not in the
        audit trail details_json (which should stay lean).

        Args:
            trace_id: UUID identifying this trace (from ProvenanceRecord.trace_id).
            tool_trace: ToolTrace to save.
            output_dir: Directory for trace files. Default: data/reasoning_traces.

        Returns:
            Path to the saved trace file, or None on failure.
        """
        if output_dir is None:
            output_dir = Path("data/reasoning_traces")

        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            trace_path = output_dir / f"{trace_id}.json"
            trace_data = tool_trace.model_dump()

            with open(trace_path, "w") as f:
                json.dump(trace_data, f, default=str, indent=2)

            logger.info("Saved reasoning trace to %s", trace_path)
            return trace_path

        except Exception as e:
            logger.warning("Failed to save trace %s: %s", trace_id, e)
            return None
