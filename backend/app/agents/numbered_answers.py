"""Respuestas del modelo con un campo obligatorio por elemento numerado de la entrada, ni más ni menos."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model


class _Answers(BaseModel):
    """Base de los esquemas numerados: un campo que sobre también invalida la respuesta."""

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class NumberedAnswers:
    """Esquema de salida con ``<field>_1`` … ``<field>_N``, uno por elemento, y su lectura en orden."""

    name: str
    field: str
    # Tipo de cada respuesta, p. ej. un Literal de posturas o str.
    answer: Any
    # Descripción de cada campo; ``{n}`` es el número del elemento al que responde.
    description: str

    def schema(self, size: int) -> type[BaseModel]:
        """Esquema con un campo obligatorio por elemento; con él, Ollama no puede generar más ni menos."""
        fields: dict[str, Any] = {
            self._key(n): (self.answer, Field(description=self.description.format(n=n)))
            for n in range(1, size + 1)
        }
        return create_model(self.name, __base__=_Answers, **fields)

    def in_order(self, result: object, size: int) -> tuple[Any, ...]:
        """Respuestas de una salida ya validada, en el orden de los elementos de la entrada."""
        return tuple(getattr(result, self._key(n)) for n in range(1, size + 1))

    def _key(self, n: int) -> str:
        return f"{self.field}_{n}"
