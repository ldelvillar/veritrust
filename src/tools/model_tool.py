"""
Este módulo define una herramienta de detección de Fake
News utilizando un modelo de IA basado en DistilBERT.
"""

import os
from typing import Type
import torch
import torch.nn.functional as F
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification


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

    def _run(self, text: str) -> str:
        try:
            # Cargar modelo y tokenizador
            tokenizer = DistilBertTokenizer.from_pretrained(self.model_path)
            model = DistilBertForSequenceClassification.from_pretrained(self.model_path)

            # Procesar texto
            inputs = tokenizer(
                text, return_tensors="pt", truncation=True, padding=True, max_length=128
            )

            with torch.no_grad():
                logits = model(**inputs).logits
                probs = F.softmax(logits, dim=1)

            # 0: Real, 1: Fake
            real_prob = probs[0][0].item()
            fake_prob = probs[0][1].item()

            resultado = "FALSA" if fake_prob > real_prob else "REAL"
            confianza = max(fake_prob, real_prob)

            return (
                f"El análisis de IA sugiere que la noticia es {resultado} "
                f"con una confianza del {confianza:.2%}."
            )

        except (OSError, ValueError, RuntimeError) as e:
            return f"Error al ejecutar el detector: {str(e)}"


# Prueba individual de la herramienta
if __name__ == "__main__":
    tool = FakeNewsDetectorTool()
    print(tool.run("La lejía cura el COVID de forma instantánea según estudios."))
