"""Pipeline de exportacion final del modelo ganador."""

from __future__ import annotations

from pathlib import Path

from .config import (
    BEST_MODEL_SUMMARY_FILENAME,
    FINAL_EVALUATION_REPORT_FILENAME,
    FINAL_EXPERIMENT_NAME,
    FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH,
    MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH,
    MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH,
)
from .export_steps import copy_file, load_json, save_json
from src.common.visual_logger import log_banner, log_kv, log_step, log_success, log_summary_panel


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_export_pipeline(logger) -> None:
    total_steps = 3
    root = project_root()

    training_output_dir = root / MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH / FINAL_EXPERIMENT_NAME
    evaluation_output_dir = root / MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH
    export_output_dir = root / FINAL_MODEL_EXPORT_DIR_RELATIVE_PATH

    summary_path = training_output_dir / BEST_MODEL_SUMMARY_FILENAME
    evaluation_report_path = evaluation_output_dir / FINAL_EVALUATION_REPORT_FILENAME

    log_banner(logger, "INICIO EXPORTACION FINAL", style="bold yellow")

    log_step(logger, 1, total_steps, "Carga de artefactos previos", style="yellow")
    summary = load_json(summary_path)
    evaluation_report = load_json(evaluation_report_path)

    selected_model_path = Path(str(summary["selected_model_path"]))

    log_kv(logger, "Resumen seleccionado", summary_path)
    log_kv(logger, "Reporte evaluacion", evaluation_report_path)
    log_kv(logger, "Modelo origen", selected_model_path)

    log_step(logger, 2, total_steps, "Copia del modelo final", style="yellow")
    final_model_path = export_output_dir / "final_model.joblib"
    final_metadata_path = export_output_dir / "final_model_metadata.json"
    final_metrics_path = export_output_dir / "final_metrics.json"

    copy_file(selected_model_path, final_model_path)

    final_metadata = {
        "selected_experiment": FINAL_EXPERIMENT_NAME,
        "selected_model_name": summary["selected_model_name"],
        "selected_dataset": summary["selected_dataset"],
        "original_model_path": str(selected_model_path),
        "exported_model_path": str(final_model_path),
        "selection_summary_path": str(summary_path),
        "evaluation_report_path": str(evaluation_report_path),
    }
    save_json(final_metadata, final_metadata_path)
    save_json(evaluation_report["metrics"], final_metrics_path)

    log_step(logger, 3, total_steps, "Fin de exportacion", style="yellow")
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