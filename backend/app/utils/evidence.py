"""Contract shared by the biomedical evidence source clients."""

from collections.abc import Iterable

# Cap on each section of a drug label, so none crowds out the following ones.
LABEL_SECTION_MAX_CHARS = 500


class EvidenceRetrievalError(Exception):
    """Raised when a query to an evidence source fails."""


def failure_cause(exc: Exception) -> str:
    """Name a failed request by its exception type and HTTP status, leaving out the URL that carries the query and any api_key."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return type(exc).__name__ if status is None else f"{type(exc).__name__} {status}"


def join_label_sections(sections: Iterable[str]) -> str | None:
    """Join the sections of a label, trimming each so the judge sees them all."""
    text = " ".join(
        section.strip()[:LABEL_SECTION_MAX_CHARS]
        for section in sections
        if section.strip()
    )
    return text or None
