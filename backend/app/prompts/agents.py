"""Este módulo contiene los prompts de sistema que utilizan los distintos agentes."""

from pathlib import Path
from dataclasses import dataclass
import yaml


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
    health_expert: PromptItem


def load_prompts() -> Prompts:
    """Carga los prompts desde un archivo YAML y los devuelve como una instancia de Prompts."""
    yaml_path = Path(__file__).parent / "prompts.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Prompts(
        extractor=PromptItem(**data["extractor"]),
        translator=PromptItem(**data["translator"]),
        health_expert=PromptItem(**data["health_expert"]),
    )
