"""Version-aware access to official CMS ICD-10 materials.

The package separates release acquisition from parsing and keeps CM and PCS materials
independently lazy.
"""

from .exceptions import (
    AmbiguousReleaseError,
    DownloadError,
    ICDKnowledgeBaseError,
    MaterialUnavailableError,
    ParseError,
    ReleaseUnavailableError,
)
from .knowledge_base import (
    ICD10CMKnowledgeBase,
    ICD10KnowledgeBase,
    ICD10PCSKnowledgeBase,
)
from .models import Code, Guideline, InstructionalNote, Release, Term

__all__ = [
    "AmbiguousReleaseError",
    "Code",
    "DownloadError",
    "Guideline",
    "ICD10CMKnowledgeBase",
    "ICD10KnowledgeBase",
    "ICD10PCSKnowledgeBase",
    "ICDKnowledgeBaseError",
    "InstructionalNote",
    "MaterialUnavailableError",
    "ParseError",
    "Release",
    "ReleaseUnavailableError",
    "Term",
]
