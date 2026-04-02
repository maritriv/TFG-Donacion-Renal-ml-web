"""Configuracion de la fase 05: exportacion final."""

from pathlib import Path

MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_training")
MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_evaluation")
FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH = Path("outputs/final_model_export")
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")

BEST_MID_SUMMARY_FILENAME = "best_mid_summary.json"
BEST_TRANSFER_SUMMARY_FILENAME = "best_transfer_summary.json"
FINAL_COMPARISON_REPORT_FILENAME = "final_comparison_report.json"

FINAL_EXPERIMENT_NAME = "real"

MID_CLEAN_FILENAME = "dataset_mid_clean.csv"
TRANSFER_CLEAN_FILENAME = "dataset_transfer_clean.csv"
TARGET_COLUMN = "DONANTE_VALIDO"