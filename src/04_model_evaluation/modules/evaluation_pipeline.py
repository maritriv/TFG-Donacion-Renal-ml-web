"""Pipeline de evaluacion final de los modelos ganadores por dataset.

Compara automaticamente los candidatos de:
- real
- real_plus_synthetic

para cada dataset (MID y TRANSFER), elige el mejor resumen disponible
y evalua ese modelo sobre su particion test correspondiente.
"""

from __future__ import annotations

from pathlib import Path

from .config import (
    BEST_MID_SUMMARY_FILENAME,
    BEST_TRANSFER_SUMMARY_FILENAME,
    MID_CLEAN_FILENAME,
    MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH,
    MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH,
    PROCESSED_DIR_RELATIVE_PATH,
    TARGET_COLUMN,
    TEST_SIZE,
    TRANSFER_CLEAN_FILENAME,
)
from .evaluation_steps import (
    evaluate_model,
    load_dataset,
    load_json,
    load_model,
    make_train_test_split,
    save_confusion_matrix_plot,
    save_json,
    save_predictions,
    split_features_target,
)
from src.common.visual_logger import (
    log_banner,
    log_kv,
    log_step,
    log_success,
    log_summary_panel,
    log_table,
)

AVAILABLE_EXPERIMENTS = ["real", "real_plus_synthetic"]


def project_root() -> Path:
    """Detecta raíz del proyecto."""
    return Path(__file__).resolve().parents[3]


def _resolve_dataset_path(processed_dir: Path, dataset_name: str) -> Path:
    """Devuelve la ruta del dataset real correspondiente."""
    if dataset_name == "mid":
        return processed_dir / MID_CLEAN_FILENAME
    if dataset_name == "transfer":
        return processed_dir / TRANSFER_CLEAN_FILENAME
    raise ValueError(f"Dataset no soportado: {dataset_name}")


def _score_summary(summary: dict) -> tuple[float, float, float]:
    """Devuelve score de comparacion para elegir mejor resumen."""
    metrics = summary.get("metrics", {})
    test_f1 = float(metrics.get("test_f1", 0.0) or 0.0)
    test_recall = float(metrics.get("test_recall", 0.0) or 0.0)
    cv_f1_mean = float(metrics.get("cv_f1_mean", 0.0) or 0.0)
    return (test_f1, test_recall, cv_f1_mean)


def _select_best_summary_across_experiments(
    training_root_dir: Path,
    summary_filename: str,
) -> tuple[Path, dict]:
    """Selecciona el mejor resumen entre real y real_plus_synthetic."""
    candidates: list[tuple[Path, dict]] = []

    for experiment_name in AVAILABLE_EXPERIMENTS:
        summary_path = training_root_dir / experiment_name / summary_filename
        if summary_path.exists():
            summary = load_json(summary_path)
            candidates.append((summary_path, summary))

    if not candidates:
        raise FileNotFoundError(
            f"No se encontro ningun resumen candidato para: {summary_filename}"
        )

    candidates.sort(
        key=lambda item: _score_summary(item[1]),
        reverse=True,
    )
    return candidates[0]


def _evaluate_one_summary(
    logger,
    summary_path: Path,
    summary: dict,
    processed_dir: Path,
    evaluation_output_dir: Path,
) -> dict:
    """Evalua un modelo ganador concreto a partir de su resumen."""
    selected_dataset = str(summary["dataset"])
    selected_model_name = str(summary["selected_model_name"])
    selected_model_path = Path(str(summary["selected_model_path"]))
    selected_seed = int(summary["selected_seed"])
    selected_experiment = str(summary["selected_experiment"])

    dataset_path = _resolve_dataset_path(processed_dir, selected_dataset)

    model = load_model(selected_model_path)
    df = load_dataset(dataset_path)

    x, y = split_features_target(df, TARGET_COLUMN)
    _, x_test, _, y_test = make_train_test_split(
        x=x,
        y=y,
        test_size=TEST_SIZE,
        random_state=selected_seed,
    )

    metrics = evaluate_model(model=model, x_test=x_test, y_test=y_test)

    dataset_output_dir = evaluation_output_dir / selected_dataset
    metrics_path = dataset_output_dir / "final_metrics.json"
    cm_path = dataset_output_dir / "final_confusion_matrix.png"
    predictions_path = dataset_output_dir / "test_predictions.csv"
    report_path = dataset_output_dir / "final_evaluation_report.json"

    save_json(metrics, metrics_path)
    save_confusion_matrix_plot(
        confusion_matrix_values=metrics["confusion_matrix"],
        output_path=cm_path,
        title=f"Final Evaluation - {selected_model_name} ({selected_dataset})",
    )
    save_predictions(model, x_test, y_test, predictions_path)

    final_report = {
        "selected_dataset": selected_dataset,
        "selected_model_name": selected_model_name,
        "selected_model_path": str(selected_model_path),
        "selected_experiment": selected_experiment,
        "selected_seed": selected_seed,
        "selected_summary_path": str(summary_path),
        "evaluation_dataset_path": str(dataset_path),
        "metrics": metrics,
    }
    save_json(final_report, report_path)

    log_summary_panel(
        f"Resultados evaluacion final · {selected_dataset.upper()}",
        {
            "Modelo": selected_model_name,
            "Experimento": selected_experiment,
            "Semilla": selected_seed,
            "Test F1": round(float(metrics["f1"]), 4),
            "Test Recall": round(float(metrics["recall"]), 4),
            "Metrics JSON": metrics_path,
        },
        border_style="blue",
    )

    return {
        "dataset": selected_dataset,
        "model": selected_model_name,
        "experiment": selected_experiment,
        "seed": selected_seed,
        "selected_model_path": str(selected_model_path),
        "selected_summary_path": str(summary_path),
        "dataset_path": str(dataset_path),
        "test_f1": float(metrics["f1"]),
        "test_recall": float(metrics["recall"]),
        "metrics_path": str(metrics_path),
        "cm_path": str(cm_path),
        "predictions_path": str(predictions_path),
        "report_path": str(report_path),
    }


def run_evaluation_pipeline(logger) -> None:
    """Evalua los dos modelos ganadores finales: MID y TRANSFER."""
    total_steps = 4
    root = project_root()

    training_root_dir = root / MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH
    evaluation_output_dir = root / MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH
    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH

    log_banner(logger, "INICIO EVALUACION FINAL", style="bold blue")
    log_kv(logger, "Experimentos candidatos", ", ".join(AVAILABLE_EXPERIMENTS))

    log_step(logger, 1, total_steps, "Carga de resúmenes ganadores", style="blue")

    best_mid_path, best_mid_summary = _select_best_summary_across_experiments(
        training_root_dir=training_root_dir,
        summary_filename=BEST_MID_SUMMARY_FILENAME,
    )
    best_transfer_path, best_transfer_summary = _select_best_summary_across_experiments(
        training_root_dir=training_root_dir,
        summary_filename=BEST_TRANSFER_SUMMARY_FILENAME,
    )

    log_kv(logger, "Resumen MID seleccionado", best_mid_path)
    log_kv(logger, "Resumen TRANSFER seleccionado", best_transfer_path)

    log_step(logger, 2, total_steps, "Evaluacion final de modelos MID y TRANSFER", style="blue")

    evaluation_results = []

    evaluation_results.append(
        _evaluate_one_summary(
            logger=logger,
            summary_path=best_mid_path,
            summary=best_mid_summary,
            processed_dir=processed_dir,
            evaluation_output_dir=evaluation_output_dir,
        )
    )

    evaluation_results.append(
        _evaluate_one_summary(
            logger=logger,
            summary_path=best_transfer_path,
            summary=best_transfer_summary,
            processed_dir=processed_dir,
            evaluation_output_dir=evaluation_output_dir,
        )
    )

    log_step(logger, 3, total_steps, "Construccion de resumen final", style="blue")

    comparison_rows = []
    for row in evaluation_results:
        comparison_rows.append([
            row["dataset"],
            row["model"],
            row["experiment"],
            row["seed"],
            row["test_f1"],
            row["test_recall"],
        ])

    log_table(
        title="Resumen evaluacion final",
        columns=["Dataset", "Modelo", "Experimento", "Seed", "Test F1", "Test Recall"],
        rows=comparison_rows,
        border_style="blue",
    )

    summary_report = {
        "candidate_experiments": AVAILABLE_EXPERIMENTS,
        "results": evaluation_results,
    }
    summary_report_path = evaluation_output_dir / "final_comparison_report.json"
    save_json(summary_report, summary_report_path)

    log_step(logger, 4, total_steps, "Fin de evaluacion", style="blue")
    log_success("Evaluacion final completada")
    log_summary_panel(
        "Salidas evaluacion final",
        {
            "Carpeta de salida": evaluation_output_dir,
            "Comparativa final": summary_report_path,
            "MID metrics": evaluation_output_dir / "mid" / "final_metrics.json",
            "TRANSFER metrics": evaluation_output_dir / "transfer" / "final_metrics.json",
        },
        border_style="blue",
    )
    log_banner(logger, "FIN EVALUACION FINAL", style="bold blue")