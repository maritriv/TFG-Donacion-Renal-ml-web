"""Configuracion de la fase 04: evaluacion final."""

from pathlib import Path

MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_training")
MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_evaluation")
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")

MID_CLEAN_FILENAME = "dataset_mid_clean.csv"
TRANSFER_CLEAN_FILENAME = "dataset_transfer_clean.csv"

BEST_MID_SUMMARY_FILENAME = "best_mid_summary.json"
BEST_TRANSFER_SUMMARY_FILENAME = "best_transfer_summary.json"

# Experimento de referencia para evaluacion final
FINAL_EXPERIMENT_NAME = "real"

TEST_SIZE = 0.20
TARGET_COLUMN = "DONANTE_VALIDO"