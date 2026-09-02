"""Tests del cargador de prompts que consume el startup del worker."""

from types import SimpleNamespace

import pytest

import app.prompts.agents as prompts_module


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
