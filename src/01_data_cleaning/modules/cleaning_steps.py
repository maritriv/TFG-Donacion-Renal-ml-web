"""Funciones de negocio de limpieza de datos.

Incluye carga de la hoja Donante, normalizacion de columnas,
validaciones de calidad, creacion del target y generacion de
datasets limpios MID/TRANSFER para el modelado posterior.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .config import TARGET_COLUMN

logger = logging.getLogger("cleaning_steps")


def load_donor_sheet(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    """Carga la hoja Donante desde Excel."""
    if not excel_path.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {excel_path}")
    return pd.read_excel(excel_path, sheet_name=sheet_name)


def _strip_accents(text: str) -> str:
    """Quita acentos para tener nombres de columnas estables en cualquier entorno."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_column_name(column_name: object) -> str:
    """Normaliza nombres de columnas: trim, ASCII, underscores y uppercase."""
    text = str(column_name).strip()
    text = _strip_accents(text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text.upper()


def normalize_column_names(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Renombra columnas a formato consistente y devuelve el mapping aplicado."""
    rename_map: Dict[str, str] = {}
    for col in df.columns:
        normalized = _normalize_column_name(col)
        if str(col) != normalized:
            rename_map[str(col)] = normalized
    return df.rename(columns=rename_map), rename_map


def find_first_existing_column(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    """Devuelve la primera columna existente de una lista de candidatos."""
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def remove_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Elimina duplicados exactos y reporta duplicados por identificador si existe."""
    exact_duplicates = int(df.duplicated().sum())
    id_column = find_first_existing_column(df, ["CODIGO_DONANTE_CORE", "CODIGO_DONANTE", "ID_DONANTE"])
    id_duplicates = int(df.duplicated(subset=[id_column]).sum()) if id_column else 0

    cleaned = df.drop_duplicates().copy()
    return cleaned, {
        "exact_duplicates_found": exact_duplicates,
        "id_duplicates_found": id_duplicates,
        "rows_after_exact_dedup": int(cleaned.shape[0]),
    }


def drop_high_null_columns(
    df: pd.DataFrame,
    threshold: float,
    protected_columns: Optional[Sequence[str]] = None,
) -> Tuple[pd.DataFrame, List[str], Dict[str, float], List[str]]:
    """Elimina columnas por exceso de nulos excepto columnas protegidas."""
    null_ratio = df.isna().mean().sort_values(ascending=False)
    protected = set(protected_columns or [])
    dropped = [col for col, ratio in null_ratio.items() if ratio > threshold and col not in protected]
    protected_over_threshold = [
        col for col, ratio in null_ratio.items() if ratio > threshold and col in protected
    ]
    cleaned = df.drop(columns=dropped, errors="ignore").copy()
    return (
        cleaned,
        dropped,
        {str(col): float(ratio) for col, ratio in null_ratio.items()},
        protected_over_threshold,
    )


def drop_manual_columns(
    df: pd.DataFrame, manual_columns: Sequence[str]
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Elimina columnas irrelevantes/fuga sin romper si faltan."""
    existing = [col for col in manual_columns if col in df.columns]
    missing = [col for col in manual_columns if col not in df.columns]
    cleaned = df.drop(columns=existing, errors="ignore").copy()
    return cleaned, existing, missing


def map_binary_value(value: object) -> Optional[int]:
    """Mapea representaciones binarias comunes hacia 0/1."""
    if pd.isna(value):
        return np.nan

    if isinstance(value, (int, float, np.integer, np.floating)):
        if value == 1:
            return 1
        if value == 0:
            return 0
        return np.nan

    text = str(value).strip().upper()
    positives = {"1", "SI", "S", "YES", "Y", "TRUE", "T"}
    negatives = {"0", "NO", "N", "FALSE", "F"}
    if text in positives:
        return 1
    if text in negatives:
        return 0
    return np.nan


def clean_binary_columns(
    df: pd.DataFrame, candidate_columns: Sequence[str]
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Convierte columnas binarias detectadas a 0/1 y cuenta valores no mapeables."""
    output = df.copy()
    issue_count: Dict[str, int] = {}

    for col in candidate_columns:
        if col not in output.columns:
            continue
        before = output[col].copy()
        output[col] = output[col].map(map_binary_value)
        issue_count[col] = int(before.notna().sum() - output[col].notna().sum())
    return output, issue_count


def clean_numeric_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Valida columnas numericas y transforma valores imposibles a NaN."""
    output = df.copy()
    anomaly_counts: Dict[str, int] = {}

    rules = {
        "EDAD": lambda s: s < 0,
        "CAPNOMETRIA_MEDIO": lambda s: s < 0,
        "CAPNOMETRIA_TRANSFERENCIA": lambda s: s < 0,
        "IMC": lambda s: (s <= 0) | (s > 80),
        "ADRENALINA_N": lambda s: s < 0,
    }

    for col, invalid_rule in rules.items():
        if col not in output.columns:
            continue
        output[col] = pd.to_numeric(output[col], errors="coerce")
        invalid_mask = invalid_rule(output[col]) & output[col].notna()
        anomaly_counts[col] = int(invalid_mask.sum())
        output.loc[invalid_mask, col] = np.nan

    return output, anomaly_counts


def create_target(df: pd.DataFrame, drop_undefined_rows: bool = True) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Crea DONANTE_VALIDO a partir de RINON_DCHO_VALIDO y RINON_IZDO_VALIDO."""
    right_col = find_first_existing_column(df, ["RINON_DCHO_VALIDO"])
    left_col = find_first_existing_column(df, ["RINON_IZDO_VALIDO"])
    if not right_col or not left_col:
        raise KeyError(
            "No se encontraron columnas para crear target: "
            "RINON_DCHO_VALIDO y RINON_IZDO_VALIDO"
        )

    right = df[right_col].map(map_binary_value)
    left = df[left_col].map(map_binary_value)

    target = pd.Series(np.nan, index=df.index, dtype="float")
    target[(right == 1) | (left == 1)] = 1
    target[(right == 0) & (left == 0)] = 0

    output = df.copy()
    output[TARGET_COLUMN] = target

    undefined_rows = int(output[TARGET_COLUMN].isna().sum())
    removed_rows = 0
    if drop_undefined_rows:
        before = output.shape[0]
        output = output.dropna(subset=[TARGET_COLUMN]).copy()
        output[TARGET_COLUMN] = output[TARGET_COLUMN].astype(int)
        removed_rows = int(before - output.shape[0])

    distribution = output[TARGET_COLUMN].value_counts(dropna=False).to_dict()
    stats = {
        "target_valid_1": int((output[TARGET_COLUMN] == 1).sum()),
        "target_invalid_0": int((output[TARGET_COLUMN] == 0).sum()),
        "target_undefined_before_drop": undefined_rows,
        "rows_removed_by_undefined_target": removed_rows,
        "target_distribution": {str(k): int(v) for k, v in distribution.items()},
    }
    return output, stats


def select_optional_temporal_columns(
    df: pd.DataFrame,
    candidate_columns: Sequence[str],
    max_null_ratio: float,
) -> Tuple[List[str], Dict[str, float]]:
    """Selecciona temporales disponibles con bajo porcentaje de nulos."""
    selected: List[str] = []
    null_ratios: Dict[str, float] = {}
    for col in candidate_columns:
        if col not in df.columns:
            continue
        ratio = float(df[col].isna().mean())
        null_ratios[col] = ratio
        if ratio <= max_null_ratio:
            selected.append(col)
    return selected, null_ratios


def build_dataset_by_columns(
    df: pd.DataFrame,
    common_columns: Sequence[str],
    specific_columns: Sequence[str],
    optional_temporal_columns: Sequence[str],
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Construye dataset final con las columnas candidatas disponibles."""
    candidates = list(common_columns) + list(specific_columns) + list(optional_temporal_columns)
    unique_candidates = list(dict.fromkeys(candidates))
    existing = [col for col in unique_candidates if col in df.columns]
    missing = [col for col in unique_candidates if col not in df.columns]
    return df[existing].copy(), existing, missing


def build_mid_dataset(
    df: pd.DataFrame,
    common_columns: Sequence[str],
    specific_columns: Sequence[str],
    temporal_candidates: Sequence[str],
    max_temporal_null_ratio: float,
) -> Tuple[pd.DataFrame, List[str], List[str], Dict[str, float]]:
    """Construye dataset MID y devuelve metadatos de inclusion de temporales."""
    selected_temporal, temporal_null_ratios = select_optional_temporal_columns(
        df=df,
        candidate_columns=temporal_candidates,
        max_null_ratio=max_temporal_null_ratio,
    )
    dataset, existing, missing = build_dataset_by_columns(
        df=df,
        common_columns=common_columns,
        specific_columns=specific_columns,
        optional_temporal_columns=selected_temporal,
    )
    return dataset, existing, missing, temporal_null_ratios


def build_transfer_dataset(
    df: pd.DataFrame,
    common_columns: Sequence[str],
    specific_columns: Sequence[str],
    temporal_candidates: Sequence[str],
    max_temporal_null_ratio: float,
) -> Tuple[pd.DataFrame, List[str], List[str], Dict[str, float]]:
    """Construye dataset TRANSFERENCIA y devuelve metadatos de temporales."""
    selected_temporal, temporal_null_ratios = select_optional_temporal_columns(
        df=df,
        candidate_columns=temporal_candidates,
        max_null_ratio=max_temporal_null_ratio,
    )
    dataset, existing, missing = build_dataset_by_columns(
        df=df,
        common_columns=common_columns,
        specific_columns=specific_columns,
        optional_temporal_columns=selected_temporal,
    )
    return dataset, existing, missing, temporal_null_ratios


def save_outputs(
    mid_dataset: pd.DataFrame,
    transfer_dataset: pd.DataFrame,
    output_dir: Path,
    mid_filename: str,
    transfer_filename: str,
) -> Tuple[Path, Path]:
    """Guarda datasets finales de limpieza en disco."""
    output_dir.mkdir(parents=True, exist_ok=True)
    mid_path = output_dir / mid_filename
    transfer_path = output_dir / transfer_filename
    mid_dataset.to_csv(mid_path, index=False)
    transfer_dataset.to_csv(transfer_path, index=False)
    return mid_path, transfer_path


def save_cleaning_report(report_data: Dict[str, object], report_path: Path) -> None:
    """Guarda reporte JSON de la etapa de limpieza."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report_data, file, indent=2, ensure_ascii=False)
