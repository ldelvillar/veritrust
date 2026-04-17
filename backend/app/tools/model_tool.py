"""
Este módulo define una herramienta de detección de Fake
News utilizando un modelo de IA basado en BioBERT.
"""

import logging
import os

from pathlib import Path
from typing import Any, Mapping, cast
import torch
import torch.nn.functional as F
from langchain.tools import BaseTool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field
from transformers import BertTokenizer, BertForSequenceClassification


logger = logging.getLogger(__name__)


class DetectorInput(BaseModel):
    """Esquema de entrada para la herramienta de detección de Fake News."""

    text: str = Field(
        description="El texto de la noticia médica o de salud a analizar."
    )


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
    _tokenizer: BertTokenizer | None = None
    _model: BertForSequenceClassification | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_path = self._resolve_model_path()

    def _ensure_model_loaded(self) -> None:
        """Carga el tokenizador y modelo una única vez por instancia."""
        if self._tokenizer is not None and self._model is not None:
            return

        tokenizer = BertTokenizer.from_pretrained(
            self.model_path, local_files_only=True
        )
        model = BertForSequenceClassification.from_pretrained(
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
    def _resolve_model_path() -> str:
        """Resuelve una ruta local valida para el modelo en distintos entornos."""
        env_path = os.getenv("FAKE_NEWS_MODEL_PATH")
        if env_path and Path(env_path).exists():
            return str(Path(env_path).resolve())

        current_file = Path(__file__).resolve()
        candidates = [
            current_file.parents[2] / "models" / "bert_classifier",
            current_file.parents[1] / "models" / "bert_classifier",
            Path.cwd() / "models" / "bert_classifier",
        ]

        for path in candidates:
            if path.exists():
                return str(path.resolve())

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

    def _run(self, *args: Any, **kwargs: Any) -> dict[str, str | float]:
        try:
            text = self._extract_text_arg(*args, **kwargs)
            self._ensure_model_loaded()
            if self._tokenizer is None or self._model is None:
                raise RuntimeError(
                    "El detector no pudo inicializar modelo y tokenizador"
                )

            # Procesar texto
            inputs = self._tokenizer(
                text, return_tensors="pt", truncation=True, padding=True, max_length=128
            )
            model_inputs = self._prepare_inputs_for_model(inputs)
            model_inputs_dict = cast(Mapping[str, Any], model_inputs)

            with torch.inference_mode():
                logits = self._model(**model_inputs_dict).logits
                probs = F.softmax(logits, dim=1)

            # 0=verdadera, 1=falsa
            real_prob = probs[0][0].item()
            fake_prob = probs[0][1].item()

            label = "falsa" if fake_prob > real_prob else "verdadera"
            confidence = max(fake_prob, real_prob)

            return {"label": label, "confidence": round(confidence, 4)}

        except (OSError, ValueError, RuntimeError) as e:
            logger.exception("Error al ejecutar el detector: %s", e)
            return {"label": "error", "confidence": 0.0000}
