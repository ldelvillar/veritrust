"""
Este módulo contiene las funciones necesarias para entrenar
el modelo BERT para detectar noticias falsas en salud pública.
"""

import logging

import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    BatchEncoding,
    BertForSequenceClassification,
    BertTokenizer,
    EvalPrediction,
    Trainer,
    TrainingArguments,
)

from ml.utils.load_data import load_dataset
from ml.utils.preprocess import preprocess_data

logger = logging.getLogger(__name__)

# Configuración e hiperparámetros
MODEL_NAME = "dmis-lab/biobert-v1.1"
OUTPUT_DIR = "./models/bert_classifier"
MAX_LENGTH = 128
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 2e-5

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


def compute_metrics(pred: EvalPrediction) -> dict:
    """Calcula métricas de evaluación: Precisión, Recall, F1 y Accuracy."""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)  # type: ignore[union-attr]

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary"
    )
    acc = accuracy_score(labels, preds)

    return {"accuracy": acc, "f1": f1, "precision": precision, "recall": recall}


def run_training() -> None:
    """Función principal para ejecutar el entrenamiento del modelo BERT."""
    # Cargar y preprocesar los datos de entrenamiento y validación
    raw_train = load_dataset()
    train_df = preprocess_data(raw_train)

    raw_val = load_dataset("validation")
    val_df = preprocess_data(raw_val)

    logger.info("Datos de entrenamiento: %d", len(train_df))
    logger.info("Datos de validación: %d", len(val_df))

    # Extraer listas
    train_texts = train_df["text"].tolist()
    train_labels = train_df["label"].tolist()

    val_texts = val_df["text"].tolist()
    val_labels = val_df["label"].tolist()

    # Tokenización
    logger.info("Tokenizando con %s", MODEL_NAME)
    tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)

    train_encodings = tokenizer(
        train_texts, truncation=True, padding=True, max_length=MAX_LENGTH
    )
    val_encodings = tokenizer(
        val_texts, truncation=True, padding=True, max_length=MAX_LENGTH
    )

    # Crear datasets de PyTorch
    train_dataset = PubHealthDataset(train_encodings, train_labels)
    val_dataset = PubHealthDataset(val_encodings, val_labels)

    # Configuración del modelo
    logger.info("Inicializando modelo. Usando dispositivo: %s", DEVICE)

    model = BertForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    model.to(DEVICE)  # type: ignore[arg-type]

    # Argumentos de entrenamiento
    training_args = TrainingArguments(
        output_dir="./results",  # Directorio temporal para checkpoints
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        warmup_steps=500,  # Calentamiento del learning rate
        weight_decay=0.01,  # Regularización para evitar overfitting
        logging_dir="./logs",
        logging_steps=100,
        eval_strategy="epoch",  # Evaluar al final de cada época
        save_strategy="epoch",  # Guardar checkpoint al final de cada época
        load_best_model_at_end=True,  # Quedarse con el mejor modelo al final
        metric_for_best_model="f1",  # Optimizar para F1-Score
        save_total_limit=2,  # No llenar el disco duro, guardar solo los 2 últimos
    )

    # Entrenar el modelo
    logger.info("Entrenando el modelo...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # Evaular el modelo en el conjunto de validación
    logger.info("Evaluando en el conjunto de validación...")
    eval_results = trainer.evaluate()
    logger.info("Resultados finales: %s", eval_results)

    # Guardar el modelo final y el tokenizador para su uso posterior en los agentes
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    logger.info("Modelo guardado en %s", OUTPUT_DIR)

    logger.info("Entrenamiento finalizado con éxito")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        run_training()
    except Exception:
        logger.exception("Error en el entrenamiento")
