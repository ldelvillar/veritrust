"""
Este módulo contiene las funciones necesarias para entrenar
el modelo BERT para detectar noticias falsas en salud pública.
"""

import sys
import os
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    BatchEncoding,
    EvalPrediction,
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments,
)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.load_data import load_dataset
from src.utils.preprocess import preprocess_data


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
    preds = pred.predictions.argmax(-1)

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

    print(f"Datos de entrenamiento: {len(train_df)}")
    print(f"Datos de validación: {len(val_df)}")

    # Extraer listas
    train_texts = train_df["text"].tolist()
    train_labels = train_df["label"].tolist()

    val_texts = val_df["text"].tolist()
    val_labels = val_df["label"].tolist()

    # Tokenización
    print(f"Tokenizando con {MODEL_NAME}")
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
    print(f"Inicializando modelo. Usando dispositivo: {DEVICE}")

    model = BertForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    model.to(DEVICE)

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
    print("Entrenando el modelo...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # Evaular el modelo en el conjunto de validación
    print("Evaluando en el conjunto de validación...")
    eval_results = trainer.evaluate()
    print(f"Resultados finales: {eval_results}")

    # Guardar el modelo final y el tokenizador para su uso posterior en los agentes
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Modelo guardado en {OUTPUT_DIR}")

    print("Entrenamiento finalizado con éxito")


if __name__ == "__main__":
    try:
        run_training()
    except Exception as e:
        print(f"Error en el entrenamiento: {e}")
