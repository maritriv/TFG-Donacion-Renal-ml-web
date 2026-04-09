"""Configuracion centralizada de la fase 03: model training."""

from pathlib import Path

# Rutas
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")
MODEL_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_training")

# Entradas
MID_CLEAN_FILENAME = "dataset_mid_clean.csv"
TRANSFER_CLEAN_FILENAME = "dataset_transfer_clean.csv"
MID_SYNTH_FILENAME = "dataset_mid_synthetic.csv"
TRANSFER_SYNTH_FILENAME = "dataset_transfer_synthetic.csv"

# Columna target
TARGET_COLUMN = "DONANTE_VALIDO"

# Parametros de entrenamiento
RANDOM_STATES = [1, 42, 123, 999]
TEST_SIZE = 0.20
CV_N_SPLITS = 10

# Experimentos
RUN_REAL_EXPERIMENT = True
RUN_REAL_PLUS_SYNTHETIC_EXPERIMENT = True

# Baseline sin tuning
BASELINE_MODEL_NAME = "dummy"

# Modelos con tuning
TUNED_MODEL_NAMES = [
    "logistic_regression",
    "random_forest",
    "svm",
    "xgboost",
]

# Metrica principal para GridSearch
PRIMARY_SCORING = "f1"

# Grids de hiperparametros
PARAM_GRIDS = {
    "logistic_regression": {
        "model__C": [0.01, 0.1, 1, 10],
    },
    "random_forest": {
        "n_estimators": [100, 300, 500],
        "max_depth": [None, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    },
    "svm": {
        "model__C": [0.1, 1, 10],
        "model__gamma": ["scale", 0.1, 0.01],
    },
    "xgboost": {
        "n_estimators": [100, 300],
        "max_depth": [3, 4, 6],
        "learning_rate": [0.01, 0.05, 0.1],
        "subsample": [0.8, 0.9],
        "colsample_bytree": [0.8, 0.9],
    },
}

# Ensemble
USE_VOTING_ENSEMBLE = True
VOTING_MODEL_NAME = "voting_tuned"

# Resumenes finales por dataset
BEST_MID_SUMMARY_FILENAME = "best_mid_summary.json"
BEST_TRANSFER_SUMMARY_FILENAME = "best_transfer_summary.json"

# Resumen agregado entre seeds
SEED_AGGREGATED_SUMMARY_FILENAME = "models_summary_by_seed.csv"