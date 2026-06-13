"""Este módulo contiene los prompts de sistema que utilizan los distintos agentes."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.core.config import get_settings


@dataclass
class PromptItem:
    """Define la estructura de cada prompt, incluyendo su versión y el texto del prompt."""

    version: str
    text: str


@dataclass
class Prompts:
    """Contiene los prompts para cada agente."""

    extractor: PromptItem
    translator: PromptItem
    judge: PromptItem
    health_expert: PromptItem


def load_prompts() -> Prompts:
    """Carga los prompts desde un archivo YAML y los devuelve como una instancia de Prompts."""
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
        health_expert=PromptItem(**data["health_expert"]),
    )
