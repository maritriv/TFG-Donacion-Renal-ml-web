"""Funciones de negocio para generacion sintetica tabular.

Incluye deteccion de tipos de variable, entrenamiento de sintetizador
(SDV/CTGAN o fallback), muestreo y validacion basica real vs sintetico.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import TARGET_COLUMN

logger = logging.getLogger("synthetic_steps")


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
    """Detecta columnas numericas y categoricas para tabular synthesis."""
    categorical_cols: List[str] = []
    numeric_cols: List[str] = []

    for col in df.columns:
        if col == target_col:
            categorical_cols.append(col)
            continue

        series = df[col]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
            categorical_cols.append(col)
            continue

        if pd.api.types.is_bool_dtype(series):
            categorical_cols.append(col)
            continue

        # Enteros con cardinalidad baja se tratan como categoricos clinicos.
        if pd.api.types.is_integer_dtype(series) and series.nunique(dropna=True) <= 12:
            categorical_cols.append(col)
            continue

        numeric_cols.append(col)

    return {"numeric": numeric_cols, "categorical": categorical_cols}


class BootstrapSynthesizer:
    """Fallback simple de sintesis independiente por columna."""

    def __init__(self, df: pd.DataFrame, column_types: Dict[str, List[str]]) -> None:
        self.df = df.copy()
        self.column_types = column_types

    def sample(self, num_rows: int) -> pd.DataFrame:
        """Genera muestras con bootstrap por columna."""
        data = {}
        for col in self.df.columns:
            source = self.df[col].dropna()
            if source.empty:
                data[col] = [np.nan] * num_rows
                continue

            if col in self.column_types["numeric"]:
                numeric_source = pd.to_numeric(source, errors="coerce").dropna()
                if numeric_source.empty:
                    data[col] = [np.nan] * num_rows
                    continue

                sampled = np.random.choice(numeric_source.values, size=num_rows, replace=True)
                if numeric_source.nunique() > 15:
                    std = float(np.nanstd(numeric_source.values))
                    if std > 0:
                        noise = np.random.normal(loc=0.0, scale=std * 0.03, size=num_rows)
                        sampled = sampled + noise
                data[col] = sampled
            else:
                data[col] = np.random.choice(source.values, size=num_rows, replace=True)

        return pd.DataFrame(data, columns=self.df.columns)


def train_synthesizer(
    df: pd.DataFrame, column_types: Dict[str, List[str]]
) -> Tuple[object, str]:
    """Entrena CTGAN (SDV) si existe; si no, usa fallback bootstrap."""
    try:
        from sdv.metadata import SingleTableMetadata
        from sdv.single_table import CTGANSynthesizer

        metadata = SingleTableMetadata()
        try:
            metadata.detect_from_dataframe(data=df)
        except TypeError:
            metadata.detect_from_dataframe(df)

        synthesizer = CTGANSynthesizer(metadata)
        synthesizer.fit(df)
        return synthesizer, "sdv_ctgan"
    except ImportError:
        logger.warning("SDV no instalado. Se usara fallback bootstrap.")
    except Exception as exc:
        logger.warning("Fallo al entrenar CTGAN (%s). Se usara fallback bootstrap.", exc)

    return BootstrapSynthesizer(df=df, column_types=column_types), "bootstrap_independiente"


def normalize_target_column(series: pd.Series) -> pd.Series:
    """Normaliza DONANTE_VALIDO a 0/1 cuando es posible."""
    mapping = {
        "1": 1,
        "0": 0,
        "SI": 1,
        "NO": 0,
        "TRUE": 1,
        "FALSE": 0,
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
        return mapping.get(str(value).strip().upper(), np.nan)

    return series.map(map_value)


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
    """Compara dataset real vs sintetico con metricas descriptivas basicas."""
    report: Dict[str, object] = {
        "real_shape": [int(real_df.shape[0]), int(real_df.shape[1])],
        "synthetic_shape": [int(synth_df.shape[0]), int(synth_df.shape[1])],
    }

    if target_col in real_df.columns and target_col in synth_df.columns:
        real_target = normalize_target_column(real_df[target_col]).value_counts(
            normalize=True, dropna=False
        )
        synth_target = normalize_target_column(synth_df[target_col]).value_counts(
            normalize=True, dropna=False
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
            "synthetic_mean": float(synth_num.mean()) if synth_num.notna().any() else None,
            "synthetic_std": float(synth_num.std()) if synth_num.notna().any() else None,
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
