"""Model answers with one required field per numbered input item, no more and no fewer."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model


class _Answers(BaseModel):
    """Base of the numbered schemas, where an extra field also invalidates the answer."""

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class NumberedAnswers:
    """Output schema with ``<field>_1`` … ``<field>_N``, one per item, and its reading in order."""

    name: str
    field: str
    # Type of each answer, e.g. a Literal of Stances or str.
    answer: Any
    # Description of each field, where ``{n}`` is the number of the item it answers.
    description: str

    def schema(self, size: int) -> type[BaseModel]:
        """Schema with one required field per item, so Ollama cannot generate more or fewer."""
        fields: dict[str, Any] = {
            self._key(n): (self.answer, Field(description=self.description.format(n=n)))
            for n in range(1, size + 1)
        }
        return create_model(self.name, __base__=_Answers, **fields)

    def in_order(self, result: object, size: int) -> tuple[Any, ...]:
        """Answers of an already validated output, in the order of the input items."""
        return tuple(getattr(result, self._key(n)) for n in range(1, size + 1))

    def _key(self, n: int) -> str:
        return f"{self.field}_{n}"
