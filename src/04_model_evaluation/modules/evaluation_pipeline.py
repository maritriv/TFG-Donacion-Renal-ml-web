"""Pipeline de evaluacion final del modelo ganador."""

from __future__ import annotations

from pathlib import Path

from .config import (
    BEST_MODEL_SUMMARY_FILENAME,
    FINAL_EXPERIMENT_NAME,
    MID_CLEAN_FILENAME,
    MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH,
    MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH,
    PROCESSED_DIR_RELATIVE_PATH,
    RANDOM_STATE,
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
from src.common.visual_logger import log_banner, log_kv, log_step, log_success, log_summary_panel


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_evaluation_pipeline(logger) -> None:
    total_steps = 4
    root = project_root()

    training_output_dir = root / MODEL_TRAINING_OUTPUT_DIR_RELATIVE_PATH / FINAL_EXPERIMENT_NAME
    evaluation_output_dir = root / MODEL_EVALUATION_OUTPUT_DIR_RELATIVE_PATH
    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH

    summary_path = training_output_dir / BEST_MODEL_SUMMARY_FILENAME
    summary = load_json(summary_path)

    log_banner(logger, "INICIO EVALUACION FINAL", style="bold blue")
    log_kv(logger, "Experimento origen", FINAL_EXPERIMENT_NAME)
    log_kv(logger, "Resumen mejor modelo", summary_path)

    log_step(logger, 1, total_steps, "Carga de resumen y modelo ganador", style="blue")
    selected_dataset = str(summary["selected_dataset"])
    selected_model_name = str(summary["selected_model_name"])
    selected_model_path = Path(str(summary["selected_model_path"]))
    model = load_model(selected_model_path)

    log_kv(logger, "Dataset seleccionado", selected_dataset)
    log_kv(logger, "Modelo seleccionado", selected_model_name)
    log_kv(logger, "Ruta modelo", selected_model_path)

    log_step(logger, 2, total_steps, "Carga de dataset real", style="blue")
    if selected_dataset == "mid":
        dataset_path = processed_dir / MID_CLEAN_FILENAME
    elif selected_dataset == "transfer":
        dataset_path = processed_dir / TRANSFER_CLEAN_FILENAME
    else:
        raise ValueError(f"Dataset seleccionado no soportado: {selected_dataset}")

    df = load_dataset(dataset_path)
    x, y = split_features_target(df, TARGET_COLUMN)
    _, x_test, _, y_test = make_train_test_split(
        x=x,
        y=y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    log_kv(logger, "Dataset path", dataset_path)
    log_kv(logger, "Shape test", x_test.shape)

    log_step(logger, 3, total_steps, "Evaluacion final del modelo", style="blue")
    metrics = evaluate_model(model=model, x_test=x_test, y_test=y_test)

    metrics_path = evaluation_output_dir / "final_metrics.json"
    cm_path = evaluation_output_dir / "final_confusion_matrix.png"
    predictions_path = evaluation_output_dir / "test_predictions.csv"
    report_path = evaluation_output_dir / "final_evaluation_report.json"

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
        "evaluation_dataset_path": str(dataset_path),
        "metrics": metrics,
    }
    save_json(final_report, report_path)

    log_summary_panel(
        "Resultados evaluacion final",
        {
            "Modelo": selected_model_name,
            "Dataset": selected_dataset,
            "Test F1": round(float(metrics["f1"]), 4),
            "Test Recall": round(float(metrics["recall"]), 4),
            "Metrics JSON": metrics_path,
        },
        border_style="blue",
    )

    log_step(logger, 4, total_steps, "Fin de evaluacion", style="blue")
    log_success("Evaluacion final completada")
    log_summary_panel(
        "Salidas evaluacion final",
        {
            "Metricas": metrics_path,
            "Matriz confusion": cm_path,
            "Predicciones": predictions_path,
            "Reporte final": report_path,
        },
        border_style="blue",
    )
    log_banner(logger, "FIN EVALUACION FINAL", style="bold blue")