"""Exceptions raised by :mod:`cms_icd`."""

from __future__ import annotations


class ICDKnowledgeBaseError(RuntimeError):
    """Base exception for expected CMS ICD knowledge-base failures."""


class ReleaseUnavailableError(ICDKnowledgeBaseError):
    """Raised when the requested CMS release cannot be resolved."""


class AmbiguousReleaseError(ICDKnowledgeBaseError):
    """Raised when multiple CMS artifacts match one material selection."""


class MaterialUnavailableError(ICDKnowledgeBaseError):
    """Raised when a release does not provide a requested material."""


class DownloadError(ICDKnowledgeBaseError):
    """Raised when an official CMS artifact cannot be downloaded or validated."""


class ParseError(ICDKnowledgeBaseError):
    """Raised when a CMS material does not match the expected structure."""
