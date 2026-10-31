"""System prompts used by the agents."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.core.config import get_settings


@dataclass
class PromptItem:
    """Structure of each prompt, with its version and text."""

    version: str
    text: str


@dataclass
class HealthExpertPrompt(PromptItem):
    """Health expert prompt, the system one and the user-message templates."""

    user_message: str
    verdict_certain: str
    verdict_uncertain: str
    closing_certain: str
    closing_uncertain: str
    closing_mixed: str
    evidence_sources: str
    evidence_missing: str


@dataclass
class Prompts:
    """Prompts for each agent."""

    extractor: PromptItem
    translator: PromptItem
    judge: PromptItem
    health_expert: HealthExpertPrompt


def load_prompts() -> Prompts:
    """Load the prompts from a YAML file and return them as a Prompts instance."""
    default_path = Path(__file__).parent / "prompts.yaml"
    configured_path = get_settings().prompt_file_path
    yaml_path = Path(configured_path) if configured_path else default_path
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"El archivo de prompts '{yaml_path}' contiene YAML inválido: {exc}"
        ) from exc
    return Prompts(
        extractor=PromptItem(**data["extractor"]),
        translator=PromptItem(**data["translator"]),
        judge=PromptItem(**data["judge"]),
        health_expert=HealthExpertPrompt(**data["health_expert"]),
    )
