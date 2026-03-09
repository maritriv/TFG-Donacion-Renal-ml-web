import json
from pathlib import Path
from typing import Dict

import pandas as pd


def _detectar_columna_objetivo(df: pd.DataFrame) -> str:
    candidatos = ["target", "label", "objetivo", "viable", "viabilidad"]
    columnas_lower = {str(c).lower(): str(c) for c in df.columns}
    for c in candidatos:
        if c in columnas_lower:
            return columnas_lower[c]
    raise ValueError(
        "No se detecto columna objetivo. Usa --target en el comando del pipeline."
    )


def _accuracy_mayoritaria(y: pd.Series, clase_mayoritaria: object) -> float:
    if y.empty:
        return 0.0
    return float((y == clase_mayoritaria).mean())


def ejecutar_modelado(
    df: pd.DataFrame,
    model_path: Path,
    metrics_path: Path,
    target_col: str | None = None,
) -> Dict[str, object]:
    objetivo = target_col or _detectar_columna_objetivo(df)
    y = df[objetivo].dropna()
    if y.empty:
        raise ValueError(f"La columna objetivo '{objetivo}' no contiene datos validos.")

    clase_mayoritaria = y.mode(dropna=True).iloc[0]
    accuracy_train = _accuracy_mayoritaria(y, clase_mayoritaria)

    model_artifact = {
        "model_type": "majority_class_baseline",
        "target_col": objetivo,
        "majority_class": str(clase_mayoritaria),
    }
    metrics = {
        "metric_name": "accuracy_train_majority_baseline",
        "value": accuracy_train,
        "n_samples": int(y.shape[0]),
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with model_path.open("w", encoding="utf-8") as f:
        json.dump(model_artifact, f, indent=2, ensure_ascii=False)

    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    return {"model_artifact": model_artifact, "metrics": metrics}
