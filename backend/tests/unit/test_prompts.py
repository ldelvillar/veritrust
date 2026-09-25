"""Tests del cargador de prompts que consume el startup del worker."""

from types import SimpleNamespace

import pytest

import app.prompts.agents as prompts_module
from app.agents.sanitize import USER_INPUT_END, USER_INPUT_START


def test_load_prompts_reads_packaged_yaml_with_all_agents():
    """El YAML del paquete debe traer los cuatro prompts; sin ellos el worker no arranca."""
    prompts = prompts_module.load_prompts()

    for item in (
        prompts.extractor,
        prompts.translator,
        prompts.judge,
        prompts.health_expert,
    ):
        assert item.version.strip()
        assert item.text.strip()

    # El mensaje de usuario del experto también vive en el YAML, no inline en Python.
    expert = prompts.health_expert
    for template in (
        expert.user_message,
        expert.verdict_certain,
        expert.verdict_uncertain,
        expert.closing_certain,
        expert.closing_uncertain,
        expert.evidence_sources,
        expert.evidence_missing,
    ):
        assert template.strip()


def test_agents_reading_user_derived_text_are_told_it_is_delimited_data():
    """El texto que viene del usuario llega entre marcadores y el prompt debe nombrarlos."""
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
