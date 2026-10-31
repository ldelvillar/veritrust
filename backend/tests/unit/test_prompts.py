"""Tests of the prompt loader the worker's startup consumes."""

from types import SimpleNamespace

import pytest

import app.prompts.agents as prompts_module
from app.agents.sanitize import USER_INPUT_END, USER_INPUT_START


def test_load_prompts_reads_packaged_yaml_with_all_agents():
    """The packaged YAML must bring the four prompts, without which the worker does not start."""
    prompts = prompts_module.load_prompts()

    for item in (
        prompts.extractor,
        prompts.translator,
        prompts.judge,
        prompts.health_expert,
    ):
        assert item.version.strip()
        assert item.text.strip()

    # The expert's user message also lives in the YAML, not inline in Python.
    expert = prompts.health_expert
    for template in (
        expert.user_message,
        expert.verdict_certain,
        expert.verdict_uncertain,
        expert.closing_certain,
        expert.closing_uncertain,
        expert.closing_mixed,
        expert.evidence_sources,
        expert.evidence_missing,
    ):
        assert template.strip()


def test_agents_reading_user_derived_text_are_told_it_is_delimited_data():
    """Text that comes from the user arrives between markers and the prompt must name them."""
    prompts = prompts_module.load_prompts()

    for item in (prompts.extractor, prompts.translator, prompts.judge):
        assert USER_INPUT_START in item.text
        assert USER_INPUT_END in item.text


def test_load_prompts_raises_value_error_on_invalid_yaml(tmp_path, monkeypatch):
    bad_yaml = tmp_path / "prompts.yaml"
    bad_yaml.write_text("extractor: [sin cerrar", encoding="utf-8")
    monkeypatch.setattr(
        prompts_module,
        "get_settings",
        lambda: SimpleNamespace(prompt_file_path=str(bad_yaml)),
    )

    with pytest.raises(ValueError, match="YAML inválido"):
        prompts_module.load_prompts()
