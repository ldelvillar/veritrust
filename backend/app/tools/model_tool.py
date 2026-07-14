"""
Este módulo define una herramienta de detección de Fake
News utilizando un modelo de IA basado en BioBERT.
"""

import logging
from pathlib import Path
from typing import Any, Mapping, TypedDict, cast

import torch
import torch.nn.functional as F
from langchain.tools import BaseTool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.agents.errors import BertInferenceError
from app.core.config import get_settings
from ml.utils.text import CLASS_LABELS, MAX_SEQUENCE_LENGTH, clean_text

logger = logging.getLogger(__name__)

# Diferencia mínima entre p(falsa) y p(verdadera) para emitir un veredicto firme.
FAKE_MARGIN = 0.25
REAL_MARGIN = 0.10


class DetectorInput(BaseModel):
    """Esquema de entrada para la herramienta de detección de Fake News."""

    text: str = Field(
        description="El texto de la noticia médica o de salud a analizar."
    )


class DetectorResult(TypedDict):
    """Resultado de una clasificación: etiqueta, confianza y probabilidades por clase."""

    label: str
    confidence: float
    probs: dict[str, float]


def _decide_label(probs_by_label: dict[str, float]) -> str:
    """Decide la etiqueta exigiendo un margen entre falsa y verdadera; si no, abstiene."""
    best = max(probs_by_label, key=lambda label: probs_by_label[label])
    if best == "incierta":
        return "incierta"
    diff = probs_by_label.get("falsa", 0.0) - probs_by_label.get("verdadera", 0.0)
    if diff > FAKE_MARGIN:
        return "falsa"
    if -diff > REAL_MARGIN:
        return "verdadera"
    return "incierta"


class FakeNewsDetectorTool(BaseTool):
    """Herramienta de detección de Fake News utilizando un modelo de IA."""

    name: str = "fake_news_bert_detector"
    description: str = (
        "Útil para obtener una evaluación técnica inicial de una noticia. "
        "Analiza el texto y determina si es probable que sea REAL o FAKE"
        "basándose en patrones lingüísticos."
    )
    args_schema: ArgsSchema | None = DetectorInput
    model_path: str = ""
    _tokenizer: Any | None = None
    _model: Any | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_path = self._resolve_model_path()

    def _ensure_model_loaded(self) -> None:
        """Carga el tokenizador y modelo una única vez por instancia."""
        if self._tokenizer is not None and self._model is not None:
            return

        tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, local_files_only=True
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            self.model_path, local_files_only=True
        )
        if hasattr(model, "eval"):
            model.eval()

        self._tokenizer = tokenizer
        self._model = model

    @staticmethod
    def _prepare_inputs_for_model(inputs: object) -> object:
        """Compatibiliza entradas tokenizadas para llamada al modelo."""
        if isinstance(inputs, dict):
            return inputs

        if hasattr(inputs, "to"):
            return inputs

        raise ValueError("El tokenizador devolvió un tipo de entrada no compatible")

    @staticmethod
    def _latest_version_dir(container: Path) -> Path | None:
        """Devuelve el subdirectorio de versión con modelo más reciente, si existe."""
        if not container.is_dir():
            return None
        versions = sorted(
            (
                child
                for child in container.iterdir()
                if (child / "config.json").exists()
            ),
            reverse=True,
        )
        return versions[0] if versions else None

    @classmethod
    def _resolve_model_path(cls) -> str:
        """Resuelve una ruta local valida para el modelo en distintos entornos."""
        configured_path = get_settings().fake_news_model_path
        if configured_path and Path(configured_path).exists():
            base = Path(configured_path)
            resolved = cls._latest_version_dir(base) or base
            return str(resolved.resolve())

        current_file = Path(__file__).resolve()
        candidates = [
            current_file.parents[2] / "models" / "bert_classifier",
            current_file.parents[1] / "models" / "bert_classifier",
            Path.cwd() / "models" / "bert_classifier",
        ]

        for path in candidates:
            if path.exists():
                resolved = cls._latest_version_dir(path) or path
                return str(resolved.resolve())

        raise FileNotFoundError(
            "No se encontro el modelo en una ruta local valida. "
            "Configura FAKE_NEWS_MODEL_PATH o verifica models/bert_classifier."
        )

    @staticmethod
    def _extract_text_arg(*args: Any, **kwargs: Any) -> str:
        """Obtiene el texto desde kwargs o desde el primer argumento posicional."""
        candidate = kwargs.get("text")
        if candidate is None and args:
            candidate = args[0]

        if not isinstance(candidate, str):
            raise ValueError("La herramienta requiere un argumento 'text' de tipo str")

        return candidate

    def predict_batch(self, texts: list[str]) -> list[DetectorResult]:
        """Clasifica varias afirmaciones en una sola pasada por el modelo."""
        if not texts:
            return []

        try:
            self._ensure_model_loaded()
            if self._tokenizer is None or self._model is None:
                raise RuntimeError(
                    "El detector no pudo inicializar modelo y tokenizador"
                )

            cleaned = [clean_text(t) for t in texts]

            inputs = self._tokenizer(
                cleaned,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=MAX_SEQUENCE_LENGTH,
            )
            model_inputs = self._prepare_inputs_for_model(inputs)
            model_inputs_dict = cast(Mapping[str, Any], model_inputs)

            with torch.inference_mode():
                logits = self._model(**model_inputs_dict).logits
                probs = F.softmax(logits, dim=1)

            # Las probabilidades se mapean por índice: 0=verdadera, 1=falsa, 2=incierta.
            results: list[DetectorResult] = []
            for row in probs:
                scores = [round(value.item(), 4) for value in row]
                probs_by_label = dict(zip(CLASS_LABELS, scores))
                results.append(
                    {
                        "label": _decide_label(probs_by_label),
                        "confidence": max(scores),
                        "probs": probs_by_label,
                    }
                )

            return results

        except (OSError, ValueError, RuntimeError) as e:
            # Un fallo de carga/inferencia se propaga como error tipado
            logger.exception("Error al ejecutar el detector: %s", e)
            raise BertInferenceError(
                "El detector BERT no pudo clasificar el texto"
            ) from e

    def _run(self, *args: Any, **kwargs: Any) -> DetectorResult:
        text = self._extract_text_arg(*args, **kwargs)
        return self.predict_batch([text])[0]
