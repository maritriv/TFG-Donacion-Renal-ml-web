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

# Alias explicitos para lectura en fase sintetica.
MID_CLEAN_FILENAME = MID_OUTPUT_FILENAME
TRANSFER_CLEAN_FILENAME = TRANSFER_OUTPUT_FILENAME

# Salidas sintetico
MID_SYNTH_FILENAME = "dataset_mid_synthetic.csv"
TRANSFER_SYNTH_FILENAME = "dataset_transfer_synthetic.csv"
SYNTH_REPORT_FILENAME = "synthetic_report.json"

# Parametros generales
NULL_THRESHOLD = 0.40
TEMPORAL_MAX_NULL_RATIO = 0.20
TARGET_COLUMN = "DONANTE_VALIDO"
N_SYNTHETIC_MID = 2000
N_SYNTHETIC_TRANSFER = 2000

# Columnas protegidas para no romper la creacion del target.
PROTECTED_COLUMNS_FOR_TARGET = [
    "RINON_DCHO_VALIDO",
    "RINON_IZDO_VALIDO",
]

# Columnas manualmente descartables (irrelevantes o posible fuga).
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

# Variables candidatas para modelado.
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

MID_SPECIFIC_COLUMNS = ["CAPNOMETRIA_MEDIO"]
TRANSFER_SPECIFIC_COLUMNS = ["CAPNOMETRIA_TRANSFERENCIA"]

TEMPORAL_OPTIONAL_COLUMNS = [
    "HORA_AVISO_061",
    "HORA_LLEGADA_061",
    "HORA_LLEGADA_HOSPITAL",
    "INICIO_MANIOBRAS_RCP",
    "FIN_MANIOBRAS_RCP",
]

BINARY_CANDIDATE_COLUMNS = [
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "RINON_DCHO_VALIDO",
    "RINON_IZDO_VALIDO",
]
