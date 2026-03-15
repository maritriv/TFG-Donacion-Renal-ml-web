"""Configuracion centralizada de la fase 02: exploratory analysis."""

from pathlib import Path

# Rutas base
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")
EDA_OUTPUT_DIR_RELATIVE_PATH = Path("outputs/exploratory_analysis")

# Entradas
MID_CLEAN_FILENAME = "dataset_mid_clean.csv"
TRANSFER_CLEAN_FILENAME = "dataset_transfer_clean.csv"

# Salidas
EDA_REPORT_FILENAME = "eda_report.json"

# Target
TARGET_COLUMN = "DONANTE_VALIDO"

# Variables numericas esperadas
NUMERIC_CANDIDATE_COLUMNS = [
    "EDAD",
    "IMC",
    "ADRENALINA_N",
    "CAPNOMETRIA_MEDIO",
    "CAPNOMETRIA_TRANSFERENCIA",
    
]

# Variables categoricas/binarias esperadas
CATEGORICAL_CANDIDATE_COLUMNS = [
    "SEXO",
    "GRUPO_SANGUINEO",
    "CAUSA_FALLECIMIENTO_DANC",
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "COLESTEROL",
    "CAPNOMETRIA_MEDIO_MISSING",
    "CAPNOMETRIA_TRANSFERENCIA_MISSING",
    "ADRENALINA_N_MISSING",
]