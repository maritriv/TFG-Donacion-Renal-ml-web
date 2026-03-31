"""Configuracion centralizada de la fase 01.

Define rutas, nombres de ficheros de entrada/salida, umbrales
de limpieza y listas de columnas utilizadas por ambos pipelines.
"""

from pathlib import Path

# Rutas base
EXCEL_RELATIVE_PATH = Path("data/raw/dataset_medicos.xlsx")
SHEET_NAME = "Donante"
PROCESSED_DIR_RELATIVE_PATH = Path("data/processed")

# Salidas limpieza
MID_OUTPUT_FILENAME = "dataset_mid_clean.csv"
TRANSFER_OUTPUT_FILENAME = "dataset_transfer_clean.csv"
CLEANING_REPORT_FILENAME = "cleaning_report.json"

# Alias explicitos para lectura en fase sintetica
MID_CLEAN_FILENAME = MID_OUTPUT_FILENAME
TRANSFER_CLEAN_FILENAME = TRANSFER_OUTPUT_FILENAME

# Salidas sintetico
MID_SYNTH_FILENAME = "dataset_mid_synthetic.csv"
TRANSFER_SYNTH_FILENAME = "dataset_transfer_synthetic.csv"
SYNTH_REPORT_FILENAME = "synthetic_report.json"

# Parametros generales
RANDOM_STATE = 1
NULL_THRESHOLD = 0.40
TEMPORAL_MAX_NULL_RATIO = 0.20
TARGET_COLUMN = "DONANTE_VALIDO"
UNKNOWN_CATEGORY_LABEL = "DESCONOCIDO"

# Tamaño de sintetico para dataset pequeño
N_SYNTHETIC_MID = 30
N_SYNTHETIC_TRANSFER = 30

# Columnas protegidas para no romper la creacion del target
PROTECTED_COLUMNS_FOR_TARGET = [
    "RINON_DCHO_VALIDO",
    "RINON_IZDO_VALIDO",
]

# Columnas manualmente descartables
MANUAL_DROP_COLUMNS = [
    "CODIGO_DONANTE_CORE",
    "CODIGO_DONANTE",
    "ID_DONANTE",
    "NOMBRE",
    "APELLIDOS",
    "NOMBRE_COMPLETO",
    "OBSERVACIONES",
    "COMENTARIOS",
    "MOTIVO_DESCARTE",
    "DECISION_CLINICA_FINAL",
    "RESULTADO_FINAL",
    "ADMINISTRATIVO_ESTADO",
    "USUARIO_REGISTRO",
    "FECHA_REGISTRO",
    "HORA_REGISTRO",
    "RECEPTOR_ID",
    "RINON_IMPLANTADO",
]

# Variables candidatas para modelado
COMMON_CANDIDATE_COLUMNS = [
    "EDAD",
    "SEXO",
    "IMC",
    "GRUPO_SANGUINEO",
    "CAUSA_FALLECIMIENTO_DANC",
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "ADRENALINA_N",
    "COLESTEROL",
    TARGET_COLUMN,
]

MID_SPECIFIC_COLUMNS = [
    "CAPNOMETRIA_MEDIO",
]

TRANSFER_SPECIFIC_COLUMNS = [
    "CAPNOMETRIA_TRANSFERENCIA",
]

# Columnas temporales opcionales
TEMPORAL_OPTIONAL_COLUMNS = []

# Columnas binarias/codificadas como 0-1
BINARY_CANDIDATE_COLUMNS = [
    "SEXO",
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "COLESTEROL",
    "RINON_DCHO_VALIDO",
    "RINON_IZDO_VALIDO",
]

# Variables clinicas en las que el missing puede ser informativo
MISSING_INDICATOR_SOURCE_COLUMNS = [
    "CAPNOMETRIA_TRANSFERENCIA",
    "CAPNOMETRIA_MEDIO",
    "ADRENALINA_N",
]

# Reglas simples para constraints clinicos en sintetico
SYNTHETIC_NUMERIC_LIMITS = {
    "EDAD": {"min": 0, "max": 100},
    "IMC": {"min": 0.01, "max": 80},
    "CAPNOMETRIA_MEDIO": {"min": 0, "max": 100},
    "CAPNOMETRIA_TRANSFERENCIA": {"min": 0, "max": 100},
    "ADRENALINA_N": {"min": 0, "max": 50},
}

SYNTHETIC_BINARY_COLUMNS = [
    "SEXO",
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "COLESTEROL",
    "DONANTE_VALIDO",
    "CAPNOMETRIA_MEDIO_MISSING",
    "CAPNOMETRIA_TRANSFERENCIA_MISSING",
    "ADRENALINA_N_MISSING",
]