"""Evidence source implementations registry.

All 6 evidence sources are registered here for use by the EvidenceAggregator.
The get_default_sources() factory instantiates all registered sources.
"""

from src.evidence.sources.opentargets import OpenTargetsSource
from src.evidence.sources.dgidb import DGIdbSource
from src.evidence.sources.pubmed import PubMedSource
from src.evidence.sources.clinicaltrials import ClinicalTrialsSource
from src.evidence.sources.uniprot import UniProtSource
from src.evidence.sources.chembl import ChEMBLSource

ALL_SOURCES = [
    OpenTargetsSource,
    DGIdbSource,
    PubMedSource,
    ClinicalTrialsSource,
    UniProtSource,
    ChEMBLSource,
]


def get_default_sources():
    """Instantiate all registered evidence sources."""
    return [cls() for cls in ALL_SOURCES]
