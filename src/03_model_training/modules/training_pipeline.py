"""Orquestador de la fase 03: entrenamiento de modelos tuneados."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import (
    BASELINE_MODEL_NAME,
    CV_N_SPLITS,
    MID_CLEAN_FILENAME,
    MID_SYNTH_FILENAME,
    MODEL_OUTPUT_DIR_RELATIVE_PATH,
    PARAM_GRIDS,
    PRIMARY_SCORING,
    PROCESSED_DIR_RELATIVE_PATH,
    RANDOM_STATE,
    TARGET_COLUMN,
    TEST_SIZE,
    TRANSFER_CLEAN_FILENAME,
    TRANSFER_SYNTH_FILENAME,
    TUNED_MODEL_NAMES,
    USE_VOTING_ENSEMBLE,
    VOTING_MODEL_NAME,
    BEST_MODEL_SUMMARY_FILENAME,
    SELECTION_PRIMARY_METRIC,
    SELECTION_SECONDARY_METRIC,
)
from .model_factory import get_model
from .training_steps import (
    build_comparison_row,
    build_voting_classifier,
    cross_validate_model,
    load_dataset,
    make_train_test_split,
    save_comparison_table,
    save_confusion_matrix_plot,
    save_grid_search_results,
    save_metrics,
    save_model,
    split_features_target,
    train_and_evaluate_model,
    tune_model_with_grid_search,
    save_best_model_summary,
    select_best_model,
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
    """Ejecuta train/test, tuning en train y evaluación final en test."""
    total_steps = 4
    root = project_root()

    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH
    experiment_suffix = "real" if not use_synthetic else "real_plus_synthetic"
    output_dir = root / MODEL_OUTPUT_DIR_RELATIVE_PATH / experiment_suffix

    mid_path = processed_dir / MID_CLEAN_FILENAME
    transfer_path = processed_dir / TRANSFER_CLEAN_FILENAME
    mid_synth_path = processed_dir / MID_SYNTH_FILENAME
    transfer_synth_path = processed_dir / TRANSFER_SYNTH_FILENAME

    log_banner(logger, f"INICIO MODEL TRAINING [{experiment_suffix.upper()}]", style="bold green")
    log_kv(logger, "Raiz del proyecto", root)
    log_kv(logger, "Random state", RANDOM_STATE)
    log_kv(logger, "Test size", TEST_SIZE)
    log_kv(logger, "CV folds", CV_N_SPLITS)
    log_kv(logger, "Scoring principal", PRIMARY_SCORING)
    log_kv(logger, "Uso de datos sinteticos", use_synthetic)
    log_kv(logger, "Voting ensemble", USE_VOTING_ENSEMBLE)

    log_step(logger, 1, total_steps, "Carga de datasets", style="green")
    mid_df = load_dataset(mid_path)
    transfer_df = load_dataset(transfer_path)

    mid_synth_df = None
    transfer_synth_df = None
    if use_synthetic:
        mid_synth_df = load_dataset(mid_synth_path)
        transfer_synth_df = load_dataset(transfer_synth_path)

    comparison_rows = []

    datasets_loop = [
        ("mid", mid_df, mid_synth_df),
        ("transfer", transfer_df, transfer_synth_df),
    ]

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
            x_train = x_train_real
            y_train = y_train_real

        log_kv(logger, f"{dataset_name.upper()} X train", x_train.shape)
        log_kv(logger, f"{dataset_name.upper()} X test", x_test.shape)
        log_kv(logger, f"{dataset_name.upper()} y train", y_train.shape)
        log_kv(logger, f"{dataset_name.upper()} y test", y_test.shape)

        log_step(logger, 3, total_steps, f"Tuning y entrenamiento {dataset_name.upper()}", style="green")

        # =========================
        # BASELINE SIN TUNING
        # =========================
        baseline_model = get_model(BASELINE_MODEL_NAME, random_state=RANDOM_STATE)

        baseline_cv_metrics = cross_validate_model(
            model=baseline_model,
            x_train=x_train,
            y_train=y_train,
            n_splits=CV_N_SPLITS,
            random_state=RANDOM_STATE,
        )
        baseline_test_metrics = train_and_evaluate_model(
            model=baseline_model,
            x_train=x_train,
            y_train=y_train,
            x_test=x_test,
            y_test=y_test,
        )

        baseline_output_dir = output_dir / dataset_name / BASELINE_MODEL_NAME
        save_metrics(baseline_cv_metrics, baseline_output_dir / "cv_metrics.json")
        save_metrics(baseline_test_metrics, baseline_output_dir / "test_metrics.json")
        save_confusion_matrix_plot(
            confusion_matrix_values=baseline_test_metrics["confusion_matrix"],
            output_path=baseline_output_dir / "confusion_matrix.png",
            title=f"{dataset_name.upper()} - {BASELINE_MODEL_NAME} [{experiment_suffix}]",
        )

        comparison_rows.append(
            build_comparison_row(
                dataset_name=dataset_name,
                model_name=BASELINE_MODEL_NAME,
                cv_metrics=baseline_cv_metrics,
                test_metrics=baseline_test_metrics,
            )
        )

        log_summary_panel(
            title=f"{dataset_name.upper()} · {BASELINE_MODEL_NAME} [{experiment_suffix}]",
            data={
                "cv_f1_mean": round(baseline_cv_metrics["f1_mean"], 4),
                "test_f1": round(baseline_test_metrics["f1"], 4),
                "test_recall": round(baseline_test_metrics["recall"], 4),
            },
            border_style="green",
        )

        # =========================
        # MODELOS TUNEADOS
        # =========================
        best_models = {}

        for model_name in TUNED_MODEL_NAMES:
            model = get_model(model_name, random_state=RANDOM_STATE)

            search = tune_model_with_grid_search(
                model=model,
                param_grid=PARAM_GRIDS[model_name],
                x_train=x_train,
                y_train=y_train,
                n_splits=CV_N_SPLITS,
                scoring=PRIMARY_SCORING,
                random_state=RANDOM_STATE,
            )

            best_model = search.best_estimator_
            best_models[model_name] = best_model

            tuned_cv_metrics = cross_validate_model(
                model=best_model,
                x_train=x_train,
                y_train=y_train,
                n_splits=CV_N_SPLITS,
                random_state=RANDOM_STATE,
            )
            tuned_test_metrics = train_and_evaluate_model(
                model=best_model,
                x_train=x_train,
                y_train=y_train,
                x_test=x_test,
                y_test=y_test,
            )

            model_output_dir = output_dir / dataset_name / model_name

            save_metrics(
                {
                    "best_params": search.best_params_,
                    "best_cv_score": float(search.best_score_),
                    "primary_scoring": PRIMARY_SCORING,
                },
                model_output_dir / "best_result.json",
            )
            save_metrics(tuned_cv_metrics, model_output_dir / "cv_metrics.json")
            save_metrics(tuned_test_metrics, model_output_dir / "test_metrics.json")
            save_grid_search_results(search, model_output_dir / "grid_search_results.csv")
            save_model(best_model, model_output_dir / "best_model.joblib")
            save_confusion_matrix_plot(
                confusion_matrix_values=tuned_test_metrics["confusion_matrix"],
                output_path=model_output_dir / "confusion_matrix.png",
                title=f"{dataset_name.upper()} - {model_name} [{experiment_suffix}]",
            )

            comparison_rows.append(
                build_comparison_row(
                    dataset_name=dataset_name,
                    model_name=model_name,
                    cv_metrics=tuned_cv_metrics,
                    test_metrics=tuned_test_metrics,
                    best_params=search.best_params_,
                    best_cv_score=float(search.best_score_),
                )
            )

            log_summary_panel(
                title=f"{dataset_name.upper()} · {model_name} [{experiment_suffix}]",
                data={
                    "best_cv_score": round(float(search.best_score_), 4),
                    "cv_f1_mean": round(tuned_cv_metrics["f1_mean"], 4),
                    "test_f1": round(tuned_test_metrics["f1"], 4),
                    "test_recall": round(tuned_test_metrics["recall"], 4),
                    "best_params": search.best_params_,
                },
                border_style="green",
            )

        # =========================
        # VOTING ENSEMBLE CON MODELOS TUNEADOS
        # =========================
        if USE_VOTING_ENSEMBLE:
            voting_model = build_voting_classifier(best_models)

            voting_cv_metrics = cross_validate_model(
                model=voting_model,
                x_train=x_train,
                y_train=y_train,
                n_splits=CV_N_SPLITS,
                random_state=RANDOM_STATE,
            )

            voting_test_metrics = train_and_evaluate_model(
                model=voting_model,
                x_train=x_train,
                y_train=y_train,
                x_test=x_test,
                y_test=y_test,
            )

            voting_output_dir = output_dir / dataset_name / VOTING_MODEL_NAME

            save_metrics(voting_cv_metrics, voting_output_dir / "cv_metrics.json")
            save_metrics(voting_test_metrics, voting_output_dir / "test_metrics.json")
            save_model(voting_model, voting_output_dir / "best_model.joblib")
            save_confusion_matrix_plot(
                confusion_matrix_values=voting_test_metrics["confusion_matrix"],
                output_path=voting_output_dir / "confusion_matrix.png",
                title=f"{dataset_name.upper()} - {VOTING_MODEL_NAME} [{experiment_suffix}]",
            )

            comparison_rows.append(
                build_comparison_row(
                    dataset_name=dataset_name,
                    model_name=VOTING_MODEL_NAME,
                    cv_metrics=voting_cv_metrics,
                    test_metrics=voting_test_metrics,
                    best_params=None,
                    best_cv_score=voting_cv_metrics["f1_mean"],
                )
            )

            log_summary_panel(
                title=f"{dataset_name.upper()} · {VOTING_MODEL_NAME} [{experiment_suffix}]",
                data={
                    "best_cv_score": round(voting_cv_metrics["f1_mean"], 4),
                    "cv_f1_mean": round(voting_cv_metrics["f1_mean"], 4),
                    "test_f1": round(voting_test_metrics["f1"], 4),
                    "test_recall": round(voting_test_metrics["recall"], 4),
                },
                border_style="green",
            )

        log_step(logger, 4, total_steps, "Guardado comparativa global y seleccion final", style="green")
    comparison_path = output_dir / "comparison" / "models_comparison.csv"
    save_comparison_table(comparison_rows, comparison_path)

    preview_rows = []
    for row in comparison_rows:
        preview_rows.append([
            row["dataset"],
            row["model"],
            row["best_cv_score"] if row["best_cv_score"] is not None else row["cv_f1_mean"],
            row["test_f1"],
            row["test_recall"],
        ])

    log_table(
        title=f"Resumen comparativo de modelos tuneados [{experiment_suffix}]",
        columns=["Dataset", "Modelo", "Best CV / CV F1", "Test F1", "Test Recall"],
        rows=preview_rows,
        border_style="green",
    )

    best_row = select_best_model(
        rows=comparison_rows,
        primary_metric=SELECTION_PRIMARY_METRIC,
        secondary_metric=SELECTION_SECONDARY_METRIC,
    )

    best_model_path = (
        output_dir
        / best_row["dataset"]
        / best_row["model"]
        / "best_model.joblib"
    )

    best_summary = {
        "experiment_name": experiment_suffix,
        "selection_primary_metric": SELECTION_PRIMARY_METRIC,
        "selection_secondary_metric": SELECTION_SECONDARY_METRIC,
        "selected_dataset": best_row["dataset"],
        "selected_model_name": best_row["model"],
        "selected_model_path": str(best_model_path),
        "comparison_csv_path": str(comparison_path),
        "metrics": {
            "test_accuracy": best_row["test_accuracy"],
            "test_balanced_accuracy": best_row["test_balanced_accuracy"],
            "test_precision": best_row["test_precision"],
            "test_recall": best_row["test_recall"],
            "test_f1": best_row["test_f1"],
            "test_roc_auc": best_row["test_roc_auc"],
            "cv_f1_mean": best_row["cv_f1_mean"],
            "best_cv_score": best_row["best_cv_score"],
        },
        "best_params": best_row["best_params"],
    }

    best_summary_path = output_dir / BEST_MODEL_SUMMARY_FILENAME
    save_best_model_summary(best_summary, best_summary_path)

    log_success("Modelado finalizado correctamente")
    log_summary_panel(
        f"Modelo seleccionado [{experiment_suffix}]",
        {
            "Dataset": best_row["dataset"],
            "Modelo": best_row["model"],
            "Test F1": round(float(best_row["test_f1"]), 4),
            "Test Recall": round(float(best_row["test_recall"]), 4),
            "Resumen guardado": best_summary_path,
        },
        border_style="green",
    )

    log_summary_panel(
        f"Salidas de modelado [{experiment_suffix}]",
        {
            "Carpeta de salida": output_dir,
            "Comparativa global": comparison_path,
            "Resumen mejor modelo": best_summary_path,
        },
        border_style="green",
    )

    log_banner(logger, f"FIN MODEL TRAINING [{experiment_suffix.upper()}]", style="bold green")