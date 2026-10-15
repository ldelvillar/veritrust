"""Contrato compartido por los clientes de fuentes de evidencia biomédica."""

from collections.abc import Iterable

# Cota de cada sección de una ficha de medicamento: ninguna desplaza a las siguientes.
LABEL_SECTION_MAX_CHARS = 500


class EvidenceRetrievalError(Exception):
    """Excepción lanzada cuando falla la consulta a una fuente de evidencia."""


def join_label_sections(sections: Iterable[str]) -> str | None:
    """Une las secciones de una ficha recortando cada una, para que el juez las vea todas."""
    text = " ".join(
        section.strip()[:LABEL_SECTION_MAX_CHARS]
        for section in sections
        if section.strip()
    )
    return text or None
