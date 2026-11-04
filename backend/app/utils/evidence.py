"""Contract shared by the biomedical evidence source clients."""

from collections.abc import Iterable
from typing import NoReturn

# Cap on each section of a drug label, so none crowds out the following ones.
LABEL_SECTION_MAX_CHARS = 500


class EvidenceRetrievalError(Exception):
    """Raised when a query to an evidence source fails."""


def raise_retrieval_error(source: str, exc: Exception) -> NoReturn:
    """Raise the EvidenceRetrievalError of a failed request to ``source``, naming its cause without the request URL."""
    # Not chained, since the request error carries the URL with the query and any api_key, which a traceback would print.
    raise EvidenceRetrievalError(
        f"Error al consultar {source}: {_failure_cause(exc)}"
    ) from None


def _failure_cause(exc: Exception) -> str:
    """Name a failed request by its exception type and HTTP status."""
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
