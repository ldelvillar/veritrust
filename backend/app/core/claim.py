"""Afirmaciones de un análisis: el registro que el pipeline construye una vez y lleva hasta el veredicto."""

from collections.abc import Sequence
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Claim:
    """Una afirmación médica del contenido con lo necesario para buscar su evidencia."""

    # Posición en el análisis: la clave con la que fuentes y veredicto enlazan la afirmación.
    index: int
    # Tal como se extrajo, en el idioma del contenido.
    text: str
    # Traducción al inglés clínico; vacía si el traductor la omitió.
    text_en: str = ""
    # Consulta booleana del extractor; vacía si no la dio.
    query: str = ""
    # Fármaco que nombra, o vacío si no trata de uno concreto.
    drug_term: str = ""

    @property
    def search_query(self) -> str:
        """Consulta de búsqueda: la del extractor si sirve, si no la traducción, o vacía si no hay ninguna."""
        if _usable(self.query):
            return self.query
        return self.text_en if self.text_en.strip() else ""


def extract_claims(
    statements: Sequence[str], queries: Sequence[str], drug_terms: Sequence[str]
) -> list[Claim]:
    """Construye las afirmaciones del extractor, alineando con cada una su consulta y su fármaco."""
    size = len(statements)
    return [
        Claim(index=index, text=text, query=query, drug_term=drug_term.strip())
        for index, (text, query, drug_term) in enumerate(
            zip(statements, _aligned(queries, size), _aligned(drug_terms, size))
        )
    ]


def translate_claims(
    claims: Sequence[Claim], translations: Sequence[str]
) -> list[Claim]:
    """Asigna a cada afirmación su traducción; las que el modelo omita quedan vacías."""
    return [
        replace(claim, text_en=text_en)
        for claim, text_en in zip(claims, _aligned(translations, len(claims)))
    ]


def _aligned(values: Sequence[str], size: int) -> list[str]:
    """Recorta o rellena con cadenas vacías una lista del modelo hasta ``size`` elementos."""
    return list(values[:size]) + [""] * (size - len(values))


def _usable(query: str) -> bool:
    """Una consulta sin caracteres alfanuméricos no recupera nada."""
    return any(char.isalnum() for char in query)
