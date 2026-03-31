"""Configuracion de la fase 05: exportacion final."""

from pathlib import Path

MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_training")
MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_evaluation")
FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH = Path("outputs/final_model_export")

BEST_MODEL_SUMMARY_FILENAME = "best_model_summary.json"
FINAL_EVALUATION_REPORT_FILENAME = "final_evaluation_report.json"

FINAL_EXPERIMENT_NAME = "real"