"""Pipeline de exportacion final del modelo ganador reentrenado con todos los datos.

Selecciona el mejor candidato final desde la comparativa de evaluacion,
y lo reentrena con:
- todos los datos reales del dataset ganador
- y ademas los sinteticos si el experimento ganador fue real_plus_synthetic
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import joblib
import pandas as pd

from .config import (
    FINAL_COMPARISON_REPORT_FILENAME,
    FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH,
    MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH,
    PROCESSED_DIR_RELATIVE_PATH,
    MID_CLEAN_FILENAME,
    MID_SYNTH_FILENAME,
    TARGET_COLUMN,
    TRANSFER_CLEAN_FILENAME,
    TRANSFER_SYNTH_FILENAME,
)
from .export_steps import load_json, save_json
from src.common.visual_logger import (
    log_banner,
    log_kv,
    log_step,
    log_success,
    log_summary_panel,
)

training_steps = import_module("src.03_model_training.modules.training_steps")
load_dataset = training_steps.load_dataset
split_features_target = training_steps.split_features_target


def project_root() -> Path:
    """Detecta raíz del proyecto."""
    return Path(__file__).resolve().parents[3]


def _select_final_candidate(results: list[dict]) -> dict:
    """Selecciona el mejor candidato final a exportar."""
    if not results:
        raise ValueError(
            "No hay resultados finales de evaluacion para seleccionar modelo exportable."
        )

    sorted_results = sorted(
        results,
        key=lambda row: (
            float(row.get("test_f1", 0.0) or 0.0),
            float(row.get("test_recall", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return sorted_results[0]


def _resolve_real_dataset_path(processed_dir: Path, dataset_name: str) -> Path:
    """Devuelve la ruta del dataset real correspondiente."""
    if dataset_name == "mid":
        return processed_dir / MID_CLEAN_FILENAME
    if dataset_name == "transfer":
        return processed_dir / TRANSFER_CLEAN_FILENAME
    raise ValueError(f"Dataset no soportado para exportacion: {dataset_name}")


def _resolve_synth_dataset_path(processed_dir: Path, dataset_name: str) -> Path:
    """Devuelve la ruta del dataset sintetico correspondiente."""
    if dataset_name == "mid":
        return processed_dir / MID_SYNTH_FILENAME
    if dataset_name == "transfer":
        return processed_dir / TRANSFER_SYNTH_FILENAME
    raise ValueError(f"Dataset no soportado para sintetico: {dataset_name}")


def _load_full_training_data(
    processed_dir: Path,
    dataset_name: str,
    experiment_name: str,
) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Carga todos los datos para reentrenamiento final."""
    real_dataset_path = _resolve_real_dataset_path(processed_dir, dataset_name)
    real_df = load_dataset(real_dataset_path)

    x_real, y_real = split_features_target(real_df, TARGET_COLUMN)

    training_info = {
        "real_dataset_path": str(real_dataset_path),
        "synthetic_dataset_path": None,
        "used_synthetic_data": False,
        "n_real_rows": int(real_df.shape[0]),
        "n_synthetic_rows": 0,
    }

    if experiment_name == "real_plus_synthetic":
        synth_dataset_path = _resolve_synth_dataset_path(processed_dir, dataset_name)
        synth_df = load_dataset(synth_dataset_path)

        x_synth, y_synth = split_features_target(synth_df, TARGET_COLUMN)

        x_full = pd.concat([x_real, x_synth], axis=0).reset_index(drop=True)
        y_full = pd.concat([y_real, y_synth], axis=0).reset_index(drop=True)

        training_info["synthetic_dataset_path"] = str(synth_dataset_path)
        training_info["used_synthetic_data"] = True
        training_info["n_synthetic_rows"] = int(synth_df.shape[0])

        return x_full, y_full, training_info

    return x_real, y_real, training_info


def run_export_pipeline(logger) -> None:
    """Exporta el modelo final tras reentrenarlo con todos los datos."""
    total_steps = 4
    root = project_root()

    evaluation_output_dir = root / MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH
    export_output_dir = root / FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH
    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH

    final_comparison_report_path = evaluation_output_dir / FINAL_COMPARISON_REPORT_FILENAME

    log_banner(logger, "INICIO EXPORTACION FINAL", style="bold yellow")

    log_step(logger, 1, total_steps, "Carga de artefactos previos", style="yellow")
    final_comparison_report = load_json(final_comparison_report_path)

    log_kv(logger, "Comparativa final", final_comparison_report_path)

    log_step(logger, 2, total_steps, "Seleccion del candidato final", style="yellow")
    final_candidate = _select_final_candidate(final_comparison_report["results"])

    selected_dataset = str(final_candidate["dataset"])
    selected_model_name = str(final_candidate["model"])
    selected_experiment = str(final_candidate["experiment"])
    selected_seed = int(final_candidate["seed"])
    selected_model_path = Path(str(final_candidate["selected_model_path"]))

    log_kv(logger, "Dataset final seleccionado", selected_dataset)
    log_kv(logger, "Modelo final seleccionado", selected_model_name)
    log_kv(logger, "Experimento final", selected_experiment)
    log_kv(logger, "Semilla final", selected_seed)
    log_kv(logger, "Modelo origen", selected_model_path)

    log_step(logger, 3, total_steps, "Reentrenamiento con todos los datos", style="yellow")
    model = joblib.load(selected_model_path)

    x_full, y_full, training_info = _load_full_training_data(
        processed_dir=processed_dir,
        dataset_name=selected_dataset,
        experiment_name=selected_experiment,
    )
    model.fit(x_full, y_full)

    final_model_path = export_output_dir / "final_model.joblib"
    final_metadata_path = export_output_dir / "final_model_metadata.json"
    final_metrics_path = export_output_dir / "final_metrics.json"

    export_output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, final_model_path)

    final_metadata = {
        "selected_experiment": selected_experiment,
        "selected_model_name": selected_model_name,
        "selected_dataset": selected_dataset,
        "selected_seed": selected_seed,
        "original_model_path": str(selected_model_path),
        "evaluation_report_path": str(final_comparison_report_path),
        "exported_model_path": str(final_model_path),
        "retrained_with_full_dataset": True,
        "used_synthetic_data": training_info["used_synthetic_data"],
        "real_dataset_path": training_info["real_dataset_path"],
        "synthetic_dataset_path": training_info["synthetic_dataset_path"],
        "n_real_rows": training_info["n_real_rows"],
        "n_synthetic_rows": training_info["n_synthetic_rows"],
        "n_training_rows_full_dataset": int(len(y_full)),
        "n_training_features": int(x_full.shape[1]),
    }
    save_json(final_metadata, final_metadata_path)

    final_metrics = {
        "test_f1": final_candidate["test_f1"],
        "test_recall": final_candidate["test_recall"],
        "selected_dataset": selected_dataset,
        "selected_model_name": selected_model_name,
        "selected_experiment": selected_experiment,
        "selected_seed": selected_seed,
        "selection_based_on": {
            "primary": "test_f1",
            "secondary": "test_recall",
        },
    }
    save_json(final_metrics, final_metrics_path)

    log_step(logger, 4, total_steps, "Fin de exportacion", style="yellow")
    log_success("Exportacion final completada")
    log_summary_panel(
        "Salidas exportacion final",
        {
            "Modelo final": final_model_path,
            "Metadata": final_metadata_path,
            "Metricas finales": final_metrics_path,
        },
        border_style="yellow",
    )
    log_banner(logger, "FIN EXPORTACION FINAL", style="bold yellow")