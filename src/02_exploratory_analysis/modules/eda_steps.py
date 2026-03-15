"""Funciones de negocio para exploratory analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """Carga un dataset CSV."""
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")
    return pd.read_csv(csv_path)


def ensure_output_dir(output_dir: Path) -> None:
    """Crea la carpeta de salida si no existe."""
    output_dir.mkdir(parents=True, exist_ok=True)


def detect_existing_columns(df: pd.DataFrame, candidates: List[str]) -> List[str]:
    """Devuelve columnas candidatas que existen realmente en el dataframe."""
    return [col for col in candidates if col in df.columns]


def dataset_basic_summary(df: pd.DataFrame, target_col: str) -> Dict[str, object]:
    """Resume forma general del dataset."""
    summary = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_total": int(df.isna().sum().sum()),
        "duplicated_rows": int(df.duplicated().sum()),
    }

    if target_col in df.columns:
        target_dist = df[target_col].value_counts(dropna=False).to_dict()
        summary["target_distribution"] = {str(k): int(v) for k, v in target_dist.items()}

    return summary


def numeric_summary(df: pd.DataFrame, numeric_columns: List[str]) -> Dict[str, Dict[str, float | None]]:
    """Calcula estadisticos descriptivos basicos para columnas numericas."""
    result: Dict[str, Dict[str, float | None]] = {}

    for col in numeric_columns:
        series = pd.to_numeric(df[col], errors="coerce")
        result[col] = {
            "mean": float(series.mean()) if series.notna().any() else None,
            "std": float(series.std()) if series.notna().any() else None,
            "min": float(series.min()) if series.notna().any() else None,
            "q25": float(series.quantile(0.25)) if series.notna().any() else None,
            "median": float(series.quantile(0.50)) if series.notna().any() else None,
            "q75": float(series.quantile(0.75)) if series.notna().any() else None,
            "max": float(series.max()) if series.notna().any() else None,
        }

    return result


def categorical_summary(df: pd.DataFrame, categorical_columns: List[str]) -> Dict[str, Dict[str, float]]:
    """Calcula frecuencias relativas para variables categoricas/binarias."""
    result: Dict[str, Dict[str, float]] = {}

    for col in categorical_columns:
        freq = df[col].astype(str).value_counts(normalize=True, dropna=False)
        result[col] = {str(k): float(v) for k, v in freq.items()}

    return result


def correlation_matrix(df: pd.DataFrame, numeric_columns: List[str]) -> pd.DataFrame:
    """Calcula matriz de correlacion numerica."""
    if len(numeric_columns) < 2:
        return pd.DataFrame()

    numeric_df = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    return numeric_df.corr()


def save_histograms(df: pd.DataFrame, numeric_columns: List[str], output_dir: Path, prefix: str) -> List[str]:
    """Guarda histogramas de variables numericas."""
    saved_paths: List[str] = []

    for col in numeric_columns:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue

        plt.figure(figsize=(7, 4))
        plt.hist(series, bins=15)
        plt.title(f"{prefix} - Histograma de {col}")
        plt.xlabel(col)
        plt.ylabel("Frecuencia")
        plt.tight_layout()

        path = output_dir / f"{prefix.lower()}_hist_{col.lower()}.png"
        plt.savefig(path, dpi=150)
        plt.close()
        saved_paths.append(str(path))

    return saved_paths


def save_target_barplot(df: pd.DataFrame, target_col: str, output_dir: Path, prefix: str) -> str | None:
    """Guarda grafico de barras del target."""
    if target_col not in df.columns:
        return None

    counts = df[target_col].value_counts(dropna=False).sort_index()
    if counts.empty:
        return None

    plt.figure(figsize=(6, 4))
    plt.bar([str(x) for x in counts.index], counts.values)
    plt.title(f"{prefix} - Distribucion de {target_col}")
    plt.xlabel(target_col)
    plt.ylabel("Frecuencia")
    plt.tight_layout()

    path = output_dir / f"{prefix.lower()}_target_distribution.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return str(path)


def save_correlation_heatmap(corr_df: pd.DataFrame, output_dir: Path, prefix: str) -> str | None:
    """Guarda un heatmap simple de correlacion."""
    if corr_df.empty:
        return None

    plt.figure(figsize=(7, 6))
    plt.imshow(corr_df, aspect="auto")
    plt.colorbar()
    plt.xticks(range(len(corr_df.columns)), corr_df.columns, rotation=45, ha="right")
    plt.yticks(range(len(corr_df.index)), corr_df.index)
    plt.title(f"{prefix} - Matriz de correlacion")
    plt.tight_layout()

    path = output_dir / f"{prefix.lower()}_correlation_heatmap.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return str(path)


def save_eda_report(report_data: Dict[str, object], report_path: Path) -> None:
    """Guarda reporte JSON del EDA."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report_data, file, indent=2, ensure_ascii=False)