"""
Este módulo define una herramienta de detección de Fake
News utilizando un modelo de IA basado en BioBERT.
"""

import os
from typing import Type
import torch
import torch.nn.functional as F
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from transformers import BertTokenizer, BertForSequenceClassification


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
    args_schema: Type[BaseModel] = DetectorInput
    model_path: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../models/bert_classifier")
    )

    def _run(self, text: str) -> dict[str, str | float]:
        try:
            # Cargar modelo y tokenizador
            tokenizer = BertTokenizer.from_pretrained(self.model_path)
            model = BertForSequenceClassification.from_pretrained(self.model_path)

            # Procesar texto
            inputs = tokenizer(
                text, return_tensors="pt", truncation=True, padding=True, max_length=128
            )

            with torch.no_grad():
                logits = model(**inputs).logits
                probs = F.softmax(logits, dim=1)

            # 0=verdadera, 1=falsa
            real_prob = probs[0][0].item()
            fake_prob = probs[0][1].item()

            resultado = "falsa" if fake_prob > real_prob else "verdadera"
            confianza = max(fake_prob, real_prob)

            return {"resultado": resultado, "confianza": round(confianza, 4)}

        except (OSError, ValueError, RuntimeError) as e:
            print(f"Error al ejecutar el detector: {str(e)}")
            return {"resultado": "error", "confianza": 0.0000}


if __name__ == "__main__":
    tool = FakeNewsDetectorTool()
    print(tool.run("Bleach cures COVID instantly according to studies."))
