"""
Este módulo contiene las funciones necesarias para entrenar
el modelo BERT para detectar noticias falsas en salud pública.
"""

import argparse
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BatchEncoding,
    EarlyStoppingCallback,
    EvalPrediction,
    Trainer,
    TrainingArguments,
    set_seed,
)

from ml.utils.load_data import load_dataset
from ml.utils.preprocess import preprocess_data
from ml.utils.text import CLASS_LABELS, MAX_SEQUENCE_LENGTH

logger = logging.getLogger(__name__)

# Configuración e hiperparámetros
MODEL_NAME = "dmis-lab/biobert-v1.1"
OUTPUT_DIR = "./models/bert_classifier"
MAX_LENGTH = MAX_SEQUENCE_LENGTH
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-5
LABEL_SMOOTHING = 0.1  # Reduce veredictos erróneos con confianza extrema
EVAL_STEPS = 200  # Evaluación frecuente para capturar el pico antes del sobreajuste
EARLY_STOPPING_PATIENCE = 3  # Detiene tras 3 evaluaciones sin mejorar el macro-F1
SEED = 42  # Semilla fija para entrenamientos reproducibles

# Detectar si hay una GPU disponible y usarla, sino usar CPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class PubHealthDataset(torch.utils.data.Dataset):
    """Clase personalizada para manejar el dataset en formato PyTorch."""

    def __init__(self, encodings: BatchEncoding, labels: list[int]) -> None:
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        # Convertir a tensores de PyTorch para el modelo
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item

    def __len__(self) -> int:
        return len(self.labels)


def _git_sha() -> str:
    """Devuelve el SHA corto de git del repo, o 'unknown' si no está disponible."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def compute_metrics(pred: EvalPrediction) -> dict:
    """Calcula métricas de evaluación: Precisión, Recall, F1 y Accuracy."""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)  # type: ignore[union-attr]

    # Promedio macro: seleccionar por la clase 'falsa' premiaría el sesgo hacia ella.
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="macro", zero_division=0
    )
    acc = accuracy_score(labels, preds)

    return {"accuracy": acc, "f1": f1, "precision": precision, "recall": recall}


def compute_class_weights(labels: list[int]) -> torch.Tensor:
    """Calcula pesos por frecuencia inversa para compensar el desbalance de clases."""
    counts = torch.bincount(torch.tensor(labels), minlength=len(CLASS_LABELS)).clamp(
        min=1
    )
    return counts.sum().float() / (len(CLASS_LABELS) * counts.float())


class WeightedTrainer(Trainer):
    """Trainer con pérdida ponderada por clase y suavizado de etiquetas."""

    def __init__(self, class_weights: torch.Tensor, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loss_fn = torch.nn.CrossEntropyLoss(
            weight=class_weights.to(DEVICE), label_smoothing=LABEL_SMOOTHING
        )

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss = self._loss_fn(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


def run_training(model_name: str = MODEL_NAME) -> None:
    """Función principal para ejecutar el entrenamiento del modelo BERT."""
    # Fijar semillas (Python, NumPy, PyTorch) para reproducibilidad
    set_seed(SEED)

    # Cargar y preprocesar los datos de entrenamiento y validación
    raw_train = load_dataset()
    train_df = preprocess_data(raw_train)

    raw_val = load_dataset("validation")
    val_df = preprocess_data(raw_val)

    # El conjunto de test se reserva para la métrica final, ajeno a la selección.
    raw_test = load_dataset("test")
    test_df = preprocess_data(raw_test)

    logger.info("Datos de entrenamiento: %d", len(train_df))
    logger.info("Datos de validación: %d", len(val_df))
    logger.info("Datos de test: %d", len(test_df))

    # Extraer listas
    train_texts = train_df["text"].tolist()
    train_labels = train_df["label"].tolist()

    val_texts = val_df["text"].tolist()
    val_labels = val_df["label"].tolist()

    test_texts = test_df["text"].tolist()
    test_labels = test_df["label"].tolist()

    # Tokenización
    logger.info("Tokenizando con %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    train_encodings = tokenizer(
        train_texts, truncation=True, padding=True, max_length=MAX_LENGTH
    )
    val_encodings = tokenizer(
        val_texts, truncation=True, padding=True, max_length=MAX_LENGTH
    )
    test_encodings = tokenizer(
        test_texts, truncation=True, padding=True, max_length=MAX_LENGTH
    )

    # Crear datasets de PyTorch
    train_dataset = PubHealthDataset(train_encodings, train_labels)
    val_dataset = PubHealthDataset(val_encodings, val_labels)
    test_dataset = PubHealthDataset(test_encodings, test_labels)

    # Configuración del modelo
    logger.info("Inicializando modelo. Usando dispositivo: %s", DEVICE)

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(CLASS_LABELS),
        id2label=dict(enumerate(CLASS_LABELS)),
        label2id={label: i for i, label in enumerate(CLASS_LABELS)},
        dtype=torch.float32,  # Algunos checkpoints (deberta-v3) se publican en fp16
    )
    model.to(DEVICE)

    # Argumentos de entrenamiento
    training_args = TrainingArguments(
        output_dir="./results",  # Directorio temporal para checkpoints
        num_train_epochs=EPOCHS,
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        warmup_steps=500,  # Calentamiento del learning rate
        weight_decay=0.01,  # Regularización para evitar overfitting
        logging_dir="./logs",
        logging_steps=100,
        eval_strategy="steps",  # Evaluar cada EVAL_STEPS para una selección más fina
        eval_steps=EVAL_STEPS,
        save_strategy="steps",  # Guardar al mismo ritmo que se evalúa
        save_steps=EVAL_STEPS,
        load_best_model_at_end=True,  # Quedarse con el mejor modelo al final
        metric_for_best_model="f1",  # Optimizar para F1-Score (macro)
        save_total_limit=2,  # No llenar el disco duro, guardar solo los 2 últimos
        seed=SEED,  # Semilla del Trainer (init de pesos, optimizador)
        data_seed=SEED,  # Semilla del muestreo/shuffle de datos
    )

    # Entrenar el modelo
    logger.info("Entrenando el modelo...")
    class_weights = compute_class_weights(train_labels)
    logger.info("Pesos por clase: %s", class_weights.tolist())
    trainer = WeightedTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(EARLY_STOPPING_PATIENCE)],
    )

    trainer.train()

    # Métrica final sobre el conjunto de test, ajeno a la selección del modelo
    logger.info("Evaluando en el conjunto de test...")
    test_results = trainer.evaluate(test_dataset)
    logger.info("Resultados finales (test): %s", test_results)

    # Directorio versionado (timestamp + SHA) para no sobrescribir modelos previos
    git_sha = _git_sha()
    version = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{git_sha}"
    version_dir = Path(OUTPUT_DIR) / version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Guardar el modelo final y el tokenizador para su uso posterior en los agentes
    model.save_pretrained(version_dir)
    tokenizer.save_pretrained(version_dir)

    # Registrar procedencia (datos/código/métricas) junto a los pesos del modelo
    metadata: dict[str, Any] = {
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "base_model": model_name,
        "label_names": list(CLASS_LABELS),
        "partition_sizes": {
            "train": len(train_df),
            "validation": len(val_df),
            "test": len(test_df),
        },
        "test_metrics": test_results,
        "hyperparameters": {
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "label_smoothing": LABEL_SMOOTHING,
            "eval_steps": EVAL_STEPS,
            "early_stopping_patience": EARLY_STOPPING_PATIENCE,
            "max_length": MAX_LENGTH,
            "seed": SEED,
        },
    }
    (version_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    logger.info("Modelo guardado en %s", version_dir)

    logger.info("Entrenamiento finalizado con éxito")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", default=MODEL_NAME, help="Modelo base de Hugging Face a ajustar."
    )
    cli_args = parser.parse_args()
    try:
        run_training(cli_args.model)
    except Exception:
        logger.exception("Error en el entrenamiento")
