"""Orquestador de la fase 03: entrenamiento de modelos."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import (
    CV_N_SPLITS,
    MID_CLEAN_FILENAME,
    MODEL_NAMES,
    MODEL_OUTPUT_DIR_RELATIVE_PATH,
    PROCESSED_DIR_RELATIVE_PATH,
    RANDOM_STATE,
    TARGET_COLUMN,
    TEST_SIZE,
    TRANSFER_CLEAN_FILENAME,
)
from .model_factory import get_model
from .training_steps import (
    build_comparison_row,
    cross_validate_model,
    load_dataset,
    make_train_test_split,
    save_comparison_table,
    save_confusion_matrix_plot,
    save_metrics,
    split_features_target,
    train_and_evaluate_model,
)
from src.common.visual_logger import (
    log_banner,
    log_kv,
    log_step,
    log_success,
    log_summary_panel,
    log_table,
)


def project_root() -> Path:
    """Detecta raíz del proyecto."""
    return Path(__file__).resolve().parents[3]


def run_training_pipeline(logger, use_synthetic: bool = False) -> None:
    """Ejecuta entrenamiento con validación cruzada y test final."""
    total_steps = 4
    root = project_root()

    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH
    experiment_suffix = "real" if not use_synthetic else "real_plus_synthetic"
    output_dir = root / MODEL_OUTPUT_DIR_RELATIVE_PATH / experiment_suffix

    mid_path = processed_dir / MID_CLEAN_FILENAME
    transfer_path = processed_dir / TRANSFER_CLEAN_FILENAME
    mid_synth_path = processed_dir / "dataset_mid_synthetic.csv"
    transfer_synth_path = processed_dir / "dataset_transfer_synthetic.csv"

    log_banner(logger, f"INICIO MODEL TRAINING [{experiment_suffix.upper()}]", style="bold green")
    log_kv(logger, "Raiz del proyecto", root)
    log_kv(logger, "Random state", RANDOM_STATE)
    log_kv(logger, "Test size", TEST_SIZE)
    log_kv(logger, "CV folds", CV_N_SPLITS)
    log_kv(logger, "Uso de datos sinteticos", use_synthetic)

    log_step(logger, 1, total_steps, "Carga de datasets", style="green")
    mid_df = load_dataset(mid_path)
    transfer_df = load_dataset(transfer_path)

    mid_synth_df = None
    transfer_synth_df = None
    if use_synthetic:
        mid_synth_df = load_dataset(mid_synth_path)
        transfer_synth_df = load_dataset(transfer_synth_path)

    log_kv(logger, "MID shape", f"{mid_df.shape[0]} x {mid_df.shape[1]}")
    log_kv(logger, "TRANSFER shape", f"{transfer_df.shape[0]} x {transfer_df.shape[1]}")

    if use_synthetic:
        log_kv(logger, "MID synthetic shape", f"{mid_synth_df.shape[0]} x {mid_synth_df.shape[1]}")
        log_kv(
            logger,
            "TRANSFER synthetic shape",
            f"{transfer_synth_df.shape[0]} x {transfer_synth_df.shape[1]}",
        )

    comparison_rows = []

    datasets_loop = [("mid", mid_df, mid_synth_df), ("transfer", transfer_df, transfer_synth_df)]

    for dataset_name, df, synth_df in datasets_loop:
        log_step(logger, 2, total_steps, f"Preparacion dataset {dataset_name.upper()}", style="green")

        x, y = split_features_target(df, TARGET_COLUMN)
        x_train_real, x_test, y_train_real, y_test = make_train_test_split(
            x=x,
            y=y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
        )

        if use_synthetic and synth_df is not None:
            x_synth, y_synth = split_features_target(synth_df, TARGET_COLUMN)
            x_train = pd.concat([x_train_real, x_synth], axis=0).reset_index(drop=True)
            y_train = pd.concat([y_train_real, y_synth], axis=0).reset_index(drop=True)
        else:
            x_synth = None
            y_synth = None
            x_train = x_train_real
            y_train = y_train_real

        log_kv(logger, f"{dataset_name.upper()} X train real", x_train_real.shape)
        log_kv(logger, f"{dataset_name.upper()} X test", x_test.shape)
        log_kv(logger, f"{dataset_name.upper()} y train real", y_train_real.shape)
        log_kv(logger, f"{dataset_name.upper()} y test", y_test.shape)

        if use_synthetic and x_synth is not None:
            log_kv(logger, f"{dataset_name.upper()} synthetic", x_synth.shape)
            log_kv(logger, f"{dataset_name.upper()} train total", x_train.shape)

        log_step(logger, 3, total_steps, f"Entrenamiento modelos {dataset_name.upper()}", style="green")

        for model_name in MODEL_NAMES:
            model = get_model(model_name, random_state=RANDOM_STATE)

            cv_metrics = cross_validate_model(
                model=model,
                x_train=x_train,
                y_train=y_train,
                n_splits=CV_N_SPLITS,
                random_state=RANDOM_STATE,
            )

            test_metrics = train_and_evaluate_model(
                model=model,
                x_train=x_train,
                y_train=y_train,
                x_test=x_test,
                y_test=y_test,
            )

            model_output_dir = output_dir / dataset_name / model_name

            save_metrics(cv_metrics, model_output_dir / "cv_metrics.json")
            save_metrics(test_metrics, model_output_dir / "test_metrics.json")

            save_confusion_matrix_plot(
                confusion_matrix_values=test_metrics["confusion_matrix"],
                output_path=model_output_dir / "confusion_matrix.png",
                title=f"{dataset_name.upper()} - {model_name} [{experiment_suffix}]",
            )

            comparison_rows.append(
                build_comparison_row(
                    dataset_name=dataset_name,
                    model_name=model_name,
                    cv_metrics=cv_metrics,
                    test_metrics=test_metrics,
                )
            )

            log_summary_panel(
                title=f"{dataset_name.upper()} · {model_name} [{experiment_suffix}]",
                data={
                    "cv_f1_mean": None if cv_metrics["f1_mean"] is None else round(cv_metrics["f1_mean"], 4),
                    "cv_recall_mean": None if cv_metrics["recall_mean"] is None else round(cv_metrics["recall_mean"], 4),
                    "cv_balanced_accuracy_mean": None if cv_metrics["balanced_accuracy_mean"] is None else round(cv_metrics["balanced_accuracy_mean"], 4),
                    "test_f1": round(test_metrics["f1"], 4),
                    "test_recall": round(test_metrics["recall"], 4),
                    "test_balanced_accuracy": round(test_metrics["balanced_accuracy"], 4),
                },
                border_style="green",
            )

    log_step(logger, 4, total_steps, "Guardado comparativa global", style="green")
    comparison_path = output_dir / "comparison" / "models_comparison.csv"
    save_comparison_table(comparison_rows, comparison_path)

    preview_rows = []
    for row in comparison_rows:
        preview_rows.append([
            row["dataset"],
            row["model"],
            row["cv_f1_mean"],
            row["test_f1"],
            row["test_recall"],
        ])

    log_table(
        title=f"Resumen comparativo de modelos [{experiment_suffix}]",
        columns=["Dataset", "Modelo", "CV F1 mean", "Test F1", "Test Recall"],
        rows=preview_rows,
        border_style="green",
    )

    log_success("Modelado finalizado correctamente")
    log_summary_panel(
        f"Salidas de modelado [{experiment_suffix}]",
        {
            "Carpeta de salida": output_dir,
            "Comparativa global": comparison_path,
        },
        border_style="green",
    )

    log_banner(logger, f"FIN MODEL TRAINING [{experiment_suffix.upper()}]", style="bold green")