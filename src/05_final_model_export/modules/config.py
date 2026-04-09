"""Configuracion centralizada de la fase 05: exportacion final del modelo."""

from pathlib import Path

# Rutas
MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_training")
MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/model_evaluation")
FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH = Path("outputs/final_model_export")
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")

# Entradas
MID_CLEAN_FILENAME = "dataset_mid_clean.csv"
TRANSFER_CLEAN_FILENAME = "dataset_transfer_clean.csv"
MID_SYNTH_FILENAME = "dataset_mid_synthetic.csv"
TRANSFER_SYNTH_FILENAME = "dataset_transfer_synthetic.csv"

# Columna target
TARGET_COLUMN = "DONANTE_VALIDO"

# Artefacto de evaluacion final
FINAL_COMPARISON_REPORT_FILENAME = "final_comparison_report.json"