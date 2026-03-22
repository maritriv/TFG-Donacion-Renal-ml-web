"""Configuracion centralizada de la fase 03: model training."""

from pathlib import Path

# Rutas
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")
MODEL_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_training")

# Entradas
MID_CLEAN_FILENAME = "dataset_mid_clean.csv"
TRANSFER_CLEAN_FILENAME = "dataset_transfer_clean.csv"

# Columna target
TARGET_COLUMN = "DONANTE_VALIDO"

# Parametros de entrenamiento
RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_N_SPLITS = 5

# Modelos a entrenar
MODEL_NAMES = [
    "dummy",
    "logistic_regression",
    "random_forest",
    "svm",
    "xgboost",
    "voting",
]