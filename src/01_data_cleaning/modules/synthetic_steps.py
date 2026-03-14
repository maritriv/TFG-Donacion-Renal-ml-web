"""Funciones de negocio para generacion sintetica tabular.

Incluye deteccion de tipos de variable, entrenamiento de CTGAN,
muestreo y validacion real vs sintetico.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import (
    RANDOM_STATE,
    SYNTHETIC_BINARY_COLUMNS,
    SYNTHETIC_NUMERIC_LIMITS,
    TARGET_COLUMN,
)

logger = logging.getLogger("synthetic_steps")


EXPLICIT_CATEGORICAL_COLUMNS = {
    "SEXO",
    "GRUPO_SANGUINEO",
    "CAUSA_FALLECIMIENTO_DANC",
    TARGET_COLUMN,
}

EXPLICIT_NUMERIC_COLUMNS = {
    "EDAD",
    "IMC",
    "ADRENALINA_N",
    "COLESTEROL",
    "CAPNOMETRIA_MEDIO",
    "CAPNOMETRIA_TRANSFERENCIA",
}


def _strip_accents(text: str) -> str:
    """Quita acentos para comparaciones robustas."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_text_value(value: object) -> str:
    """Normaliza texto para comparaciones."""
    text = str(value).strip()
    text = _strip_accents(text)
    text = re.sub(r"\s+", " ", text)
    return text.upper()


def load_clean_datasets(mid_path: Path, transfer_path: Path) -> Dict[str, pd.DataFrame]:
    """Carga datasets limpios de MID y TRANSFERENCIA."""
    paths = {"mid": mid_path, "transfer": transfer_path}
    datasets: Dict[str, pd.DataFrame] = {}

    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"No existe dataset limpio ({name}): {path}")
        datasets[name] = pd.read_csv(path)

    return datasets


def detect_column_types(df: pd.DataFrame, target_col: str = TARGET_COLUMN) -> Dict[str, List[str]]:
    """Detecta columnas numericas y categoricas para sintesis tabular."""
    categorical_cols: List[str] = []
    numeric_cols: List[str] = []

    for col in df.columns:
        if col == target_col:
            categorical_cols.append(col)
            continue

        if col.endswith("_MISSING"):
            categorical_cols.append(col)
            continue

        if col in EXPLICIT_CATEGORICAL_COLUMNS:
            categorical_cols.append(col)
            continue

        if col in EXPLICIT_NUMERIC_COLUMNS:
            numeric_cols.append(col)
            continue

        series = df[col]

        if pd.api.types.is_object_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
            categorical_cols.append(col)
            continue

        if pd.api.types.is_bool_dtype(series):
            categorical_cols.append(col)
            continue

        if pd.api.types.is_integer_dtype(series) and series.nunique(dropna=True) <= 12:
            categorical_cols.append(col)
            continue

        numeric_cols.append(col)

    return {"numeric": numeric_cols, "categorical": categorical_cols}


def train_synthesizer(
    df: pd.DataFrame,
    column_types: Dict[str, List[str]],
) -> Tuple[object, str]:
    """Entrena CTGAN mediante SDV. Es requisito obligatorio del proyecto."""
    _ = column_types  # Se mantiene por consistencia de interfaz

    try:
        from sdv.metadata import SingleTableMetadata
        from sdv.single_table import CTGANSynthesizer
    except ImportError as exc:
        raise ImportError(
            "La generacion sintetica requiere SDV/CTGAN. "
            "Instala la dependencia con 'uv sync --extra synthetic' "
            "o con 'pip install sdv'."
        ) from exc

    metadata = SingleTableMetadata()
    try:
        metadata.detect_from_dataframe(data=df)
    except TypeError:
        metadata.detect_from_dataframe(df)

    synthesizer = CTGANSynthesizer(metadata)
    synthesizer.fit(df)
    return synthesizer, "sdv_ctgan"


def normalize_target_column(series: pd.Series) -> pd.Series:
    """Normaliza DONANTE_VALIDO a 0/1 cuando es posible."""
    mapping = {
        "1": 1,
        "0": 0,
        "SI": 1,
        "NO": 0,
        "TRUE": 1,
        "FALSE": 0,
        "VERDADERO": 1,
        "FALSO": 0,
    }

    def map_value(value: object) -> Optional[int]:
        if pd.isna(value):
            return np.nan

        if isinstance(value, (int, float, np.integer, np.floating)):
            if value == 1:
                return 1
            if value == 0:
                return 0
            return np.nan

        return mapping.get(_normalize_text_value(value), np.nan)

    return series.map(map_value)


def _force_binary_columns(df: pd.DataFrame, binary_columns: List[str]) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Fuerza columnas binarias a valores 0/1."""
    output = df.copy()
    corrections: Dict[str, int] = {}

    for col in binary_columns:
        if col not in output.columns:
            continue

        before = output[col].copy()
        numeric = pd.to_numeric(output[col], errors="coerce")
        valid_mask = numeric.notna()

        output.loc[valid_mask, col] = (numeric[valid_mask] >= 0.5).astype(int)
        corrections[col] = int((before[valid_mask] != output.loc[valid_mask, col]).sum())

    return output, corrections


def apply_synthetic_clinical_constraints(
    synth_df: pd.DataFrame,
    real_df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Aplica constraints clinicos simples y consistencia post-sintesis."""
    output = synth_df.copy()
    clipped_columns: Dict[str, int] = {}

    for col, limits in SYNTHETIC_NUMERIC_LIMITS.items():
        if col not in output.columns:
            continue

        output[col] = pd.to_numeric(output[col], errors="coerce")
        before = output[col].copy()

        min_value = limits.get("min")
        max_value = limits.get("max")

        if min_value is not None:
            output[col] = output[col].clip(lower=min_value)
        if max_value is not None:
            output[col] = output[col].clip(upper=max_value)

        clipped_columns[col] = int((before != output[col]).fillna(False).sum())

    output, binary_corrections = _force_binary_columns(output, SYNTHETIC_BINARY_COLUMNS)

    if target_col in output.columns:
        output[target_col] = normalize_target_column(output[target_col])
        real_target_mode = normalize_target_column(real_df[target_col]).dropna().mode()
        if not real_target_mode.empty:
            output[target_col] = output[target_col].fillna(int(real_target_mode.iloc[0]))
        output[target_col] = output[target_col].astype(int)

    remaining_nulls = output.isna().sum()
    remaining_nulls = remaining_nulls[remaining_nulls > 0].sort_values(ascending=False)

    report = {
        "numeric_clipped_counts": clipped_columns,
        "binary_corrections": binary_corrections,
        "remaining_null_total": int(remaining_nulls.sum()),
        "remaining_nulls_by_column": {str(col): int(v) for col, v in remaining_nulls.items()},
    }
    return output, report


def generate_synthetic_samples(
    synthesizer: object,
    n_samples: int,
    base_df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
) -> pd.DataFrame:
    """Genera sintetico y aplica post-procesado minimo de consistencia."""
    synthetic_df = synthesizer.sample(num_rows=n_samples)
    synthetic_df = synthetic_df.reindex(columns=base_df.columns)

    if target_col in synthetic_df.columns:
        synthetic_df[target_col] = normalize_target_column(synthetic_df[target_col])
        real_target_mode = normalize_target_column(base_df[target_col]).dropna().mode()
        if not real_target_mode.empty:
            synthetic_df[target_col] = synthetic_df[target_col].fillna(int(real_target_mode.iloc[0]))
        synthetic_df[target_col] = synthetic_df[target_col].astype(int)

    return synthetic_df


def validate_synthetic_dataset(
    real_df: pd.DataFrame,
    synth_df: pd.DataFrame,
    column_types: Dict[str, List[str]],
    target_col: str = TARGET_COLUMN,
) -> Dict[str, object]:
    """Compara dataset real vs sintetico con metricas descriptivas y validaciones basicas."""
    report: Dict[str, object] = {
        "real_shape": [int(real_df.shape[0]), int(real_df.shape[1])],
        "synthetic_shape": [int(synth_df.shape[0]), int(synth_df.shape[1])],
        "synthetic_exact_duplicates": int(synth_df.duplicated().sum()),
        "synthetic_remaining_null_total": int(synth_df.isna().sum().sum()),
    }

    if target_col in real_df.columns and target_col in synth_df.columns:
        real_target = normalize_target_column(real_df[target_col]).value_counts(
            normalize=True,
            dropna=False,
        )
        synth_target = normalize_target_column(synth_df[target_col]).value_counts(
            normalize=True,
            dropna=False,
        )
        report["target_distribution"] = {
            "real": {str(k): float(v) for k, v in real_target.items()},
            "synthetic": {str(k): float(v) for k, v in synth_target.items()},
        }

    numeric_summary = {}
    for col in column_types["numeric"]:
        if col not in real_df.columns or col not in synth_df.columns:
            continue

        real_num = pd.to_numeric(real_df[col], errors="coerce")
        synth_num = pd.to_numeric(synth_df[col], errors="coerce")

        numeric_summary[col] = {
            "real_mean": float(real_num.mean()) if real_num.notna().any() else None,
            "real_std": float(real_num.std()) if real_num.notna().any() else None,
            "real_min": float(real_num.min()) if real_num.notna().any() else None,
            "real_max": float(real_num.max()) if real_num.notna().any() else None,
            "real_q25": float(real_num.quantile(0.25)) if real_num.notna().any() else None,
            "real_q50": float(real_num.quantile(0.50)) if real_num.notna().any() else None,
            "real_q75": float(real_num.quantile(0.75)) if real_num.notna().any() else None,
            "synthetic_mean": float(synth_num.mean()) if synth_num.notna().any() else None,
            "synthetic_std": float(synth_num.std()) if synth_num.notna().any() else None,
            "synthetic_min": float(synth_num.min()) if synth_num.notna().any() else None,
            "synthetic_max": float(synth_num.max()) if synth_num.notna().any() else None,
            "synthetic_q25": float(synth_num.quantile(0.25)) if synth_num.notna().any() else None,
            "synthetic_q50": float(synth_num.quantile(0.50)) if synth_num.notna().any() else None,
            "synthetic_q75": float(synth_num.quantile(0.75)) if synth_num.notna().any() else None,
        }
    report["numeric_summary"] = numeric_summary

    categorical_summary = {}
    for col in column_types["categorical"]:
        if col not in real_df.columns or col not in synth_df.columns:
            continue

        real_freq = real_df[col].astype(str).value_counts(normalize=True).head(5)
        synth_freq = synth_df[col].astype(str).value_counts(normalize=True).head(5)
        categorical_summary[col] = {
            "real_top_freq": {str(k): float(v) for k, v in real_freq.items()},
            "synthetic_top_freq": {str(k): float(v) for k, v in synth_freq.items()},
        }
    report["categorical_summary"] = categorical_summary

    numeric_cols_for_corr = [
        col for col in column_types["numeric"]
        if col in real_df.columns and col in synth_df.columns
    ]
    if len(numeric_cols_for_corr) >= 2:
        real_corr = real_df[numeric_cols_for_corr].apply(pd.to_numeric, errors="coerce").corr()
        synth_corr = synth_df[numeric_cols_for_corr].apply(pd.to_numeric, errors="coerce").corr()

        corr_diff = (real_corr - synth_corr).abs()
        report["correlation_difference_mean_abs"] = float(np.nanmean(corr_diff.values))

    return report


def save_synthetic_outputs(
    mid_synth_df: pd.DataFrame,
    transfer_synth_df: pd.DataFrame,
    output_dir: Path,
    mid_synth_filename: str,
    transfer_synth_filename: str,
) -> Tuple[Path, Path]:
    """Guarda datasets sinteticos en disco."""
    output_dir.mkdir(parents=True, exist_ok=True)
    mid_path = output_dir / mid_synth_filename
    transfer_path = output_dir / transfer_synth_filename
    mid_synth_df.to_csv(mid_path, index=False)
    transfer_synth_df.to_csv(transfer_path, index=False)
    return mid_path, transfer_path


def save_synthetic_report(report: Dict[str, object], report_path: Path) -> None:
    """Persiste el reporte JSON de la etapa sintetica."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)