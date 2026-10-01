"""Tests del esquema numerado: un campo obligatorio por elemento de la entrada."""

from typing import Literal

import pytest
from pydantic import ValidationError

from app.agents.numbered_answers import NumberedAnswers

_ANSWERS = NumberedAnswers(
    name="Answers", field="item", answer=Literal["a", "b"], description="Item {n}"
)


def test_schema_requires_one_field_per_item_and_no_other():
    # Es lo que recibe Ollama para restringir su salida.
    schema = _ANSWERS.schema(3).model_json_schema()

    assert schema["required"] == ["item_1", "item_2", "item_3"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["item_2"]["enum"] == ["a", "b"]
    assert schema["properties"]["item_2"]["description"] == "Item 2"


@pytest.mark.parametrize(
    "raw",
    [
        {"item_1": "a"},
        {"item_1": "a", "item_2": "b", "item_3": "a"},
        {"item_1": "a", "item_2": "c"},
    ],
    ids=["missing", "extra", "wrong-type"],
)
def test_schema_rejects_an_answer_that_does_not_cover_each_item_once(raw):
    with pytest.raises(ValidationError):
        _ANSWERS.schema(2).model_validate(raw)


def test_in_order_reads_the_answers_in_the_order_of_the_items():
    answer = _ANSWERS.schema(3).model_validate(
        {"item_3": "a", "item_1": "b", "item_2": "a"}
    )

    assert _ANSWERS.in_order(answer, 3) == ("b", "a", "a")
