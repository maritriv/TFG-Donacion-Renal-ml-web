"""Pipeline de exportacion final del modelo ganador reentrenado con todos los datos."""

from __future__ import annotations

from pathlib import Path

import joblib

from .config import (
    BEST_MID_SUMMARY_FILENAME,
    BEST_TRANSFER_SUMMARY_FILENAME,
    FINAL_COMPARISON_REPORT_FILENAME,
    FINAL_EXPERIMENT_NAME,
    FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH,
    MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH,
    MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH,
    PROCESSED_DIR_RELATIVE_PATH,
    MID_CLEAN_FILENAME,
    TRANSFER_CLEAN_FILENAME,
    TARGET_COLUMN,
)
from .export_steps import load_json, save_json
from importlib import import_module

training_steps = import_module("src.03_model_training.modules.training_steps")

load_dataset = training_steps.load_dataset
split_features_target = training_steps.split_features_target

from src.common.visual_logger import log_banner, log_kv, log_step, log_success, log_summary_panel


def project_root() -> Path:
    """Detecta raíz del proyecto."""
    return Path(__file__).resolve().parents[3]


def _select_final_candidate(results: list[dict]) -> dict:
    """Selecciona el mejor candidato final a exportar."""
    if not results:
        raise ValueError("No hay resultados finales de evaluacion para seleccionar modelo exportable.")

    sorted_results = sorted(
        results,
        key=lambda row: (
            float(row.get("test_f1", 0.0) or 0.0),
            float(row.get("test_recall", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return sorted_results[0]


def _resolve_dataset_path(processed_dir: Path, dataset_name: str) -> Path:
    """Devuelve la ruta del dataset real correspondiente."""
    if dataset_name == "mid":
        return processed_dir / MID_CLEAN_FILENAME
    if dataset_name == "transfer":
        return processed_dir / TRANSFER_CLEAN_FILENAME
    raise ValueError(f"Dataset no soportado para exportacion: {dataset_name}")


def run_export_pipeline(logger) -> None:
    """Exporta el modelo final tras reentrenarlo con todos los datos del dataset ganador."""
    total_steps = 4
    root = project_root()

    training_output_dir = root / MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH / FINAL_EXPERIMENT_NAME
    evaluation_output_dir = root / MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH
    export_output_dir = root / FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH
    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH

    best_mid_summary_path = training_output_dir / BEST_MID_SUMMARY_FILENAME
    best_transfer_summary_path = training_output_dir / BEST_TRANSFER_SUMMARY_FILENAME
    final_comparison_report_path = evaluation_output_dir / FINAL_COMPARISON_REPORT_FILENAME

    log_banner(logger, "INICIO EXPORTACION FINAL", style="bold yellow")

    log_step(logger, 1, total_steps, "Carga de artefactos previos", style="yellow")
    best_mid_summary = load_json(best_mid_summary_path)
    best_transfer_summary = load_json(best_transfer_summary_path)
    final_comparison_report = load_json(final_comparison_report_path)

    log_kv(logger, "Resumen MID", best_mid_summary_path)
    log_kv(logger, "Resumen TRANSFER", best_transfer_summary_path)
    log_kv(logger, "Comparativa final", final_comparison_report_path)

    log_step(logger, 2, total_steps, "Seleccion del candidato final", style="yellow")
    final_candidate = _select_final_candidate(final_comparison_report["results"])

    selected_dataset = str(final_candidate["dataset"])
    selected_model_name = str(final_candidate["model"])
    selected_experiment = str(final_candidate["experiment"])
    selected_seed = int(final_candidate["seed"])

    # Recuperar el path del modelo desde el resumen correspondiente
    if selected_dataset == "mid":
        selected_summary = best_mid_summary
    elif selected_dataset == "transfer":
        selected_summary = best_transfer_summary
    else:
        raise ValueError(f"Dataset final no soportado: {selected_dataset}")

    selected_model_path = Path(str(selected_summary["selected_model_path"]))
    dataset_path = _resolve_dataset_path(processed_dir, selected_dataset)

    log_kv(logger, "Dataset final seleccionado", selected_dataset)
    log_kv(logger, "Modelo final seleccionado", selected_model_name)
    log_kv(logger, "Experimento final", selected_experiment)
    log_kv(logger, "Semilla final", selected_seed)
    log_kv(logger, "Modelo origen", selected_model_path)
    log_kv(logger, "Dataset para reentrenamiento", dataset_path)

    log_step(logger, 3, total_steps, "Reentrenamiento con todos los datos", style="yellow")
    model = joblib.load(selected_model_path)

    df = load_dataset(dataset_path)
    x_all, y_all = split_features_target(df, TARGET_COLUMN)
    model.fit(x_all, y_all)

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
        "dataset_used_for_retraining": str(dataset_path),
        "exported_model_path": str(final_model_path),
        "best_mid_summary_path": str(best_mid_summary_path),
        "best_transfer_summary_path": str(best_transfer_summary_path),
        "evaluation_report_path": str(final_comparison_report_path),
        "retrained_with_full_dataset": True,
        "n_training_rows_full_dataset": int(df.shape[0]),
        "n_training_columns_full_dataset": int(df.shape[1]),
    }
    save_json(final_metadata, final_metadata_path)

    final_metrics = {
        "test_f1": final_candidate["test_f1"],
        "test_recall": final_candidate["test_recall"],
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