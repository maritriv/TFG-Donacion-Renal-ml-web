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


NUMERIC_VALIDATION_RULES: Dict[str, Dict[str, Optional[float]]] = {
    "EDAD": {"min": 0, "max": 100},
    "CAPNOMETRIA_MEDIO": {"min": 0, "max": 100},
    "CAPNOMETRIA_TRANSFERENCIA": {"min": 0, "max": 100},
    "IMC": {"min": 0.01, "max": 80},
    "ADRENALINA_N": {"min": 0, "max": 50},
}


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


def _normalize_text_value(value: object) -> str:
    """Normaliza un valor textual para comparaciones robustas."""
    text = str(value).strip()
    text = _strip_accents(text)
    text = re.sub(r"\s+", " ", text)
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


def analyze_null_ratio(df: pd.DataFrame) -> Dict[str, float]:
    """Devuelve porcentaje de nulos por columna (orden descendente)."""
    null_ratio = df.isna().mean().sort_values(ascending=False)
    return {str(col): float(ratio) for col, ratio in null_ratio.items()}


def create_missing_indicators(
    df: pd.DataFrame,
    source_columns: Sequence[str],
    suffix: str = "_MISSING",
) -> Tuple[pd.DataFrame, List[str], List[str], Dict[str, int]]:
    """Crea indicadores binarios de missing para columnas clinicas clave."""
    output = df.copy()
    created: List[str] = []
    source_missing: List[str] = []
    missing_counts: Dict[str, int] = {}

    for col in source_columns:
        if col not in output.columns:
            source_missing.append(col)
            continue
        indicator = f"{col}{suffix}"
        output[indicator] = output[col].isna().astype(int)
        created.append(indicator)
        missing_counts[indicator] = int(output[indicator].sum())

    return output, created, source_missing, missing_counts


def detect_variable_types(
    df: pd.DataFrame,
    binary_candidate_columns: Sequence[str],
    numeric_exclude_columns: Optional[Sequence[str]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """Separa columnas en numericas, categoricas y binarias."""
    binary_columns = [col for col in binary_candidate_columns if col in df.columns]
    numeric_excluded = set(numeric_exclude_columns or [])

    numeric_columns = [
        col
        for col in df.select_dtypes(include=["number"]).columns
        if col not in binary_columns and col not in numeric_excluded
    ]
    categorical_columns = list(df.select_dtypes(include=["object", "category", "string"]).columns)
    return numeric_columns, categorical_columns, binary_columns


def impute_numeric_with_median(
    df: pd.DataFrame,
    numeric_columns: Sequence[str],
    fallback_value: float = 0.0,
) -> Tuple[pd.DataFrame, Dict[str, int], List[str]]:
    """Imputa nulos en numericas con mediana; si toda la columna es NaN usa fallback."""
    output = df.copy()
    filled_counts: Dict[str, int] = {}
    fallback_used_columns: List[str] = []

    for col in numeric_columns:
        if col not in output.columns:
            continue

        output[col] = pd.to_numeric(output[col], errors="coerce")
        missing_before = int(output[col].isna().sum())
        if missing_before == 0:
            continue

        non_null_count = int(output[col].notna().sum())
        if non_null_count == 0:
            fill_value = fallback_value
            fallback_used_columns.append(col)
        else:
            median_value = output[col].median(skipna=True)
            fill_value = float(median_value)

        output[col] = output[col].fillna(fill_value)
        missing_after = int(output[col].isna().sum())
        filled_counts[col] = int(missing_before - missing_after)

    return output, filled_counts, fallback_used_columns


def impute_categorical_with_label(
    df: pd.DataFrame,
    categorical_columns: Sequence[str],
    fill_value: str,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Imputa nulos categoricos con una etiqueta explicita."""
    output = df.copy()
    filled_counts: Dict[str, int] = {}

    for col in categorical_columns:
        if col not in output.columns:
            continue
        missing_before = int(output[col].isna().sum())
        if missing_before == 0:
            continue

        if isinstance(output[col].dtype, pd.CategoricalDtype):
            if fill_value not in output[col].cat.categories:
                output[col] = output[col].cat.add_categories([fill_value])

        output[col] = output[col].fillna(fill_value)
        missing_after = int(output[col].isna().sum())
        filled_counts[col] = int(missing_before - missing_after)

    return output, filled_counts


def impute_binary_with_mode(
    df: pd.DataFrame,
    binary_columns: Sequence[str],
    fallback_value: int = 0,
) -> Tuple[pd.DataFrame, Dict[str, int], Dict[str, int], List[str]]:
    """Imputa nulos en binarias con la moda; si no existe usa fallback."""
    output = df.copy()
    filled_counts: Dict[str, int] = {}
    mode_used_by_column: Dict[str, int] = {}
    fallback_used_columns: List[str] = []

    for col in binary_columns:
        if col not in output.columns:
            continue
        missing_before = int(output[col].isna().sum())
        if missing_before == 0:
            continue

        mode_values = output[col].dropna().mode()
        if mode_values.empty:
            fill_value = fallback_value
            fallback_used_columns.append(col)
        else:
            fill_value = int(mode_values.iloc[0])

        output[col] = output[col].fillna(fill_value)
        missing_after = int(output[col].isna().sum())
        filled_counts[col] = int(missing_before - missing_after)
        mode_used_by_column[col] = int(fill_value)

    return output, filled_counts, mode_used_by_column, fallback_used_columns


def summarize_remaining_nulls(df: pd.DataFrame) -> Tuple[int, Dict[str, int]]:
    """Resume nulos restantes para validacion final del pipeline."""
    remaining = df.isna().sum()
    remaining = remaining[remaining > 0].sort_values(ascending=False)
    return int(remaining.sum()), {str(col): int(value) for col, value in remaining.items()}


def drop_manual_columns(
    df: pd.DataFrame,
    manual_columns: Sequence[str],
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Elimina columnas irrelevantes o con fuga sin romper si faltan."""
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

    text = _normalize_text_value(value)

    positives = {"1", "SI", "S", "YES", "Y", "TRUE", "T", "VERDADERO", "V"}
    negatives = {"0", "NO", "N", "FALSE", "F"}

    if text in positives:
        return 1
    if text in negatives:
        return 0
    return np.nan


def clean_binary_columns(
    df: pd.DataFrame,
    candidate_columns: Sequence[str],
) -> Tuple[pd.DataFrame, Dict[str, int], Dict[str, List[str]]]:
    """Convierte columnas binarias detectadas a 0/1 y reporta valores no mapeables."""
    output = df.copy()
    issue_count: Dict[str, int] = {}
    issue_examples: Dict[str, List[str]] = {}

    for col in candidate_columns:
        if col not in output.columns:
            continue

        before = output[col].copy()
        mapped = before.map(map_binary_value)
        output[col] = mapped

        invalid_mask = before.notna() & mapped.isna()
        issue_count[col] = int(invalid_mask.sum())

        if invalid_mask.any():
            examples = sorted({str(v) for v in before[invalid_mask].tolist()})
            issue_examples[col] = examples[:10]

    return output, issue_count, issue_examples


def clean_numeric_columns(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, int], Dict[str, Dict[str, Optional[float]]]]:
    """Valida columnas numericas y transforma valores imposibles a NaN."""
    output = df.copy()
    anomaly_counts: Dict[str, int] = {}
    rules_applied: Dict[str, Dict[str, Optional[float]]] = {}

    for col, limits in NUMERIC_VALIDATION_RULES.items():
        if col not in output.columns:
            continue

        output[col] = pd.to_numeric(output[col], errors="coerce")
        invalid_mask = pd.Series(False, index=output.index)

        min_value = limits.get("min")
        max_value = limits.get("max")

        if min_value is not None:
            invalid_mask = invalid_mask | (output[col] < min_value)
        if max_value is not None:
            invalid_mask = invalid_mask | (output[col] > max_value)

        invalid_mask = invalid_mask & output[col].notna()

        anomaly_counts[col] = int(invalid_mask.sum())
        rules_applied[col] = {"min": min_value, "max": max_value}
        output.loc[invalid_mask, col] = np.nan

    return output, anomaly_counts, rules_applied


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

    output = df.copy()
    output[right_col] = right
    output[left_col] = left

    target = pd.Series(np.nan, index=df.index, dtype="float")
    target[(right == 1) | (left == 1)] = 1
    target[(right == 0) & (left == 0)] = 0

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
        "right_kidney_missing_after_binary_mapping": int(right.isna().sum()),
        "left_kidney_missing_after_binary_mapping": int(left.isna().sum()),
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


def treat_missing_values_for_model_dataset(
    df: pd.DataFrame,
    numeric_columns: Sequence[str],
    categorical_columns: Sequence[str],
    binary_columns: Sequence[str],
    indicator_source_columns: Optional[Sequence[str]] = None,
    categorical_fill_value: str = "DESCONOCIDO",
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Trata nulos en un dataset final de modelado sin eliminar columnas."""
    output = df.copy()

    numeric_columns = [col for col in numeric_columns if col != TARGET_COLUMN and col in output.columns]
    categorical_columns = [col for col in categorical_columns if col != TARGET_COLUMN and col in output.columns]
    binary_columns = [col for col in binary_columns if col != TARGET_COLUMN and col in output.columns]

    created_indicators: List[str] = []
    missing_indicator_sources: List[str] = []
    indicator_missing_counts: Dict[str, int] = {}

    if indicator_source_columns:
        output, created_indicators, missing_indicator_sources, indicator_missing_counts = create_missing_indicators(
            df=output,
            source_columns=indicator_source_columns,
        )

    output, numeric_filled_counts, numeric_fallback_columns = impute_numeric_with_median(
        df=output,
        numeric_columns=numeric_columns,
    )

    output, categorical_filled_counts = impute_categorical_with_label(
        df=output,
        categorical_columns=categorical_columns,
        fill_value=categorical_fill_value,
    )

    output, binary_filled_counts, binary_mode_used, binary_fallback_columns = impute_binary_with_mode(
        df=output,
        binary_columns=binary_columns,
    )

    remaining_null_total, remaining_nulls_by_column = summarize_remaining_nulls(output)

    report = {
        "missing_indicators_created": created_indicators,
        "missing_indicator_source_columns_not_found": missing_indicator_sources,
        "missing_indicator_positive_counts": indicator_missing_counts,
        "numeric_missing_filled": numeric_filled_counts,
        "numeric_fallback_columns": numeric_fallback_columns,
        "categorical_missing_filled": categorical_filled_counts,
        "categorical_fill_value": categorical_fill_value,
        "binary_missing_filled": binary_filled_counts,
        "binary_mode_used": binary_mode_used,
        "binary_fallback_columns": binary_fallback_columns,
        "remaining_null_total": remaining_null_total,
        "remaining_nulls_by_column": remaining_nulls_by_column,
    }

    return output, report


def validate_final_dataset_for_model(
    df: pd.DataFrame,
    dataset_name: str,
    required_columns: Optional[Sequence[str]] = None,
    forbidden_columns: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Valida condiciones mínimas del dataset final antes de guardarlo."""
    issues: List[str] = []

    if TARGET_COLUMN not in df.columns:
        issues.append(f"{dataset_name}: falta la columna target {TARGET_COLUMN}")

    if df.columns.duplicated().any():
        issues.append(f"{dataset_name}: hay columnas duplicadas")

    forbidden = set(forbidden_columns or [])
    suspicious = [col for col in df.columns if col in forbidden]
    if suspicious:
        issues.append(f"{dataset_name}: columnas no permitidas detectadas: {suspicious}")

    required_missing = [col for col in (required_columns or []) if col not in df.columns]
    if required_missing:
        issues.append(f"{dataset_name}: faltan columnas requeridas: {required_missing}")

    remaining_null_total, remaining_nulls_by_column = summarize_remaining_nulls(df)

    return {
        "dataset_name": dataset_name,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "issues": issues,
        "remaining_null_total": remaining_null_total,
        "remaining_nulls_by_column": remaining_nulls_by_column,
    }


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