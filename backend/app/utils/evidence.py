"""Contract shared by the biomedical evidence source clients."""

from collections.abc import Iterable

# Cap on each section of a drug label, so none crowds out the following ones.
LABEL_SECTION_MAX_CHARS = 500


class EvidenceRetrievalError(Exception):
    """Raised when a query to an evidence source fails."""


def join_label_sections(sections: Iterable[str]) -> str | None:
    """Join the sections of a label, trimming each so the judge sees them all."""
    text = " ".join(
        section.strip()[:LABEL_SECTION_MAX_CHARS]
        for section in sections
        if section.strip()
    )
    return text or None
