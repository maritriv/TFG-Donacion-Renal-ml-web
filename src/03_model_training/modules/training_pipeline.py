"""Orquestador de la fase 03: entrenamiento, comparacion y seleccion de modelos."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import (
    BASELINE_MODEL_NAME,
    BEST_MID_SUMMARY_FILENAME,
    BEST_TRANSFER_SUMMARY_FILENAME,
    CV_N_SPLITS,
    MID_CLEAN_FILENAME,
    MID_SYNTH_FILENAME,
    MODEL_OUTPUT_DIR_RELATIVE_PATH,
    PARAM_GRIDS,
    PRIMARY_SCORING,
    PROCESSED_DIR_RELATIVE_PATH,
    RANDOM_STATES,
    TARGET_COLUMN,
    TEST_SIZE,
    TRANSFER_CLEAN_FILENAME,
    TRANSFER_SYNTH_FILENAME,
    TUNED_MODEL_NAMES,
    USE_VOTING_ENSEMBLE,
    VOTING_MODEL_NAME,
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


def _build_best_summary(
    df: pd.DataFrame,
    dataset_name: str,
    base_output_dir: Path,
) -> dict:
    """Selecciona la mejor estrategia para un dataset concreto."""
    subset = df[df["dataset"] == dataset_name].copy()
    if subset.empty:
        raise ValueError(f"No hay resultados para dataset '{dataset_name}'.")

    subset = subset.sort_values(
        by=["test_f1", "test_recall", "cv_f1_mean"],
        ascending=False,
    )
    best_row = subset.iloc[0]

    model_path = (
        base_output_dir
        / str(best_row["experiment"])
        / f"seed_{int(best_row['seed'])}"
        / dataset_name
        / str(best_row["model"])
        / "best_model.joblib"
    )

    return {
        "dataset": dataset_name,
        "selected_model_name": str(best_row["model"]),
        "selected_experiment": str(best_row["experiment"]),
        "selected_seed": int(best_row["seed"]),
        "selected_model_path": str(model_path),
        "selection_criteria": {
            "primary": "test_f1",
            "secondary": "test_recall",
            "tertiary": "cv_f1_mean",
        },
        "metrics": {
            "cv_accuracy_mean": float(best_row["cv_accuracy_mean"]) if pd.notna(best_row["cv_accuracy_mean"]) else None,
            "cv_balanced_accuracy_mean": float(best_row["cv_balanced_accuracy_mean"]) if pd.notna(best_row["cv_balanced_accuracy_mean"]) else None,
            "cv_precision_mean": float(best_row["cv_precision_mean"]) if pd.notna(best_row["cv_precision_mean"]) else None,
            "cv_recall_mean": float(best_row["cv_recall_mean"]) if pd.notna(best_row["cv_recall_mean"]) else None,
            "cv_f1_mean": float(best_row["cv_f1_mean"]) if pd.notna(best_row["cv_f1_mean"]) else None,
            "cv_roc_auc_mean": float(best_row["cv_roc_auc_mean"]) if pd.notna(best_row["cv_roc_auc_mean"]) else None,
            "test_accuracy": float(best_row["test_accuracy"]) if pd.notna(best_row["test_accuracy"]) else None,
            "test_balanced_accuracy": float(best_row["test_balanced_accuracy"]) if pd.notna(best_row["test_balanced_accuracy"]) else None,
            "test_precision": float(best_row["test_precision"]) if pd.notna(best_row["test_precision"]) else None,
            "test_recall": float(best_row["test_recall"]) if pd.notna(best_row["test_recall"]) else None,
            "test_f1": float(best_row["test_f1"]) if pd.notna(best_row["test_f1"]) else None,
            "test_roc_auc": float(best_row["test_roc_auc"]) if pd.notna(best_row["test_roc_auc"]) else None,
            "best_cv_score": float(best_row["best_cv_score"]) if pd.notna(best_row["best_cv_score"]) else None,
        },
        "best_params": best_row["best_params"],
    }


def _save_json(data: dict, path: Path) -> None:
    """Guarda JSON en disco."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_training_pipeline(logger, use_synthetic: bool = False) -> None:
    """Ejecuta tuning, entrenamiento, comparacion y seleccion final por dataset."""
    total_steps = 4
    root = project_root()

    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH
    base_output_dir = root / MODEL_OUTPUT_DIR_RELATIVE_PATH
    experiment_suffix = "real" if not use_synthetic else "real_plus_synthetic"
    experiment_output_dir = base_output_dir / experiment_suffix

    mid_path = processed_dir / MID_CLEAN_FILENAME
    transfer_path = processed_dir / TRANSFER_CLEAN_FILENAME
    mid_synth_path = processed_dir / MID_SYNTH_FILENAME
    transfer_synth_path = processed_dir / TRANSFER_SYNTH_FILENAME

    log_banner(logger, f"INICIO MODEL TRAINING [{experiment_suffix.upper()}]", style="bold green")
    log_kv(logger, "Raiz del proyecto", root)
    log_kv(logger, "Random states", RANDOM_STATES)
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

    all_comparison_rows: list[dict] = []

    datasets_loop = [
        ("mid", mid_df, mid_synth_df),
        ("transfer", transfer_df, transfer_synth_df),
    ]

    for seed in RANDOM_STATES:
        log_banner(logger, f"SEMILLA {seed}", style="bold yellow")

        for dataset_name, df, synth_df in datasets_loop:
            log_step(
                logger,
                2,
                total_steps,
                f"Preparacion dataset {dataset_name.upper()} · seed={seed}",
                style="green",
            )

            x, y = split_features_target(df, TARGET_COLUMN)
            x_train_real, x_test, y_train_real, y_test = make_train_test_split(
                x=x,
                y=y,
                test_size=TEST_SIZE,
                random_state=seed,
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

            log_step(
                logger,
                3,
                total_steps,
                f"Tuning y entrenamiento {dataset_name.upper()} · seed={seed}",
                style="green",
            )

            seed_output_dir = experiment_output_dir / f"seed_{seed}"

            # =========================
            # BASELINE SIN TUNING
            # =========================
            baseline_model = get_model(BASELINE_MODEL_NAME, random_state=seed)

            baseline_cv_metrics = cross_validate_model(
                model=baseline_model,
                x_train=x_train,
                y_train=y_train,
                n_splits=CV_N_SPLITS,
                random_state=seed,
            )
            baseline_test_metrics = train_and_evaluate_model(
                model=baseline_model,
                x_train=x_train,
                y_train=y_train,
                x_test=x_test,
                y_test=y_test,
            )

            baseline_output_dir = seed_output_dir / dataset_name / BASELINE_MODEL_NAME
            save_metrics(baseline_cv_metrics, baseline_output_dir / "cv_metrics.json")
            save_metrics(baseline_test_metrics, baseline_output_dir / "test_metrics.json")
            save_confusion_matrix_plot(
                confusion_matrix_values=baseline_test_metrics["confusion_matrix"],
                output_path=baseline_output_dir / "confusion_matrix.png",
                title=f"{dataset_name.upper()} - {BASELINE_MODEL_NAME} [{experiment_suffix}] [seed={seed}]",
            )

            baseline_row = build_comparison_row(
                dataset_name=dataset_name,
                model_name=BASELINE_MODEL_NAME,
                cv_metrics=baseline_cv_metrics,
                test_metrics=baseline_test_metrics,
            )
            baseline_row["seed"] = seed
            baseline_row["experiment"] = experiment_suffix
            all_comparison_rows.append(baseline_row)

            log_summary_panel(
                title=f"{dataset_name.upper()} · {BASELINE_MODEL_NAME} [{experiment_suffix}] [seed={seed}]",
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
                model = get_model(model_name, random_state=seed)

                search = tune_model_with_grid_search(
                    model=model,
                    param_grid=PARAM_GRIDS[model_name],
                    x_train=x_train,
                    y_train=y_train,
                    n_splits=CV_N_SPLITS,
                    scoring=PRIMARY_SCORING,
                    random_state=seed,
                )

                best_model = search.best_estimator_
                best_models[model_name] = best_model

                tuned_cv_metrics = cross_validate_model(
                    model=best_model,
                    x_train=x_train,
                    y_train=y_train,
                    n_splits=CV_N_SPLITS,
                    random_state=seed,
                )
                tuned_test_metrics = train_and_evaluate_model(
                    model=best_model,
                    x_train=x_train,
                    y_train=y_train,
                    x_test=x_test,
                    y_test=y_test,
                )

                model_output_dir = seed_output_dir / dataset_name / model_name

                save_metrics(
                    {
                        "best_params": search.best_params_,
                        "best_cv_score": float(search.best_score_),
                        "primary_scoring": PRIMARY_SCORING,
                        "seed": seed,
                        "experiment": experiment_suffix,
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
                    title=f"{dataset_name.upper()} - {model_name} [{experiment_suffix}] [seed={seed}]",
                )

                row = build_comparison_row(
                    dataset_name=dataset_name,
                    model_name=model_name,
                    cv_metrics=tuned_cv_metrics,
                    test_metrics=tuned_test_metrics,
                    best_params=search.best_params_,
                    best_cv_score=float(search.best_score_),
                )
                row["seed"] = seed
                row["experiment"] = experiment_suffix
                all_comparison_rows.append(row)

                log_summary_panel(
                    title=f"{dataset_name.upper()} · {model_name} [{experiment_suffix}] [seed={seed}]",
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
                    random_state=seed,
                )

                voting_test_metrics = train_and_evaluate_model(
                    model=voting_model,
                    x_train=x_train,
                    y_train=y_train,
                    x_test=x_test,
                    y_test=y_test,
                )

                voting_output_dir = seed_output_dir / dataset_name / VOTING_MODEL_NAME

                save_metrics(voting_cv_metrics, voting_output_dir / "cv_metrics.json")
                save_metrics(voting_test_metrics, voting_output_dir / "test_metrics.json")
                save_model(voting_model, voting_output_dir / "best_model.joblib")
                save_confusion_matrix_plot(
                    confusion_matrix_values=voting_test_metrics["confusion_matrix"],
                    output_path=voting_output_dir / "confusion_matrix.png",
                    title=f"{dataset_name.upper()} - {VOTING_MODEL_NAME} [{experiment_suffix}] [seed={seed}]",
                )

                voting_row = build_comparison_row(
                    dataset_name=dataset_name,
                    model_name=VOTING_MODEL_NAME,
                    cv_metrics=voting_cv_metrics,
                    test_metrics=voting_test_metrics,
                    best_params=None,
                    best_cv_score=voting_cv_metrics["f1_mean"],
                )
                voting_row["seed"] = seed
                voting_row["experiment"] = experiment_suffix
                all_comparison_rows.append(voting_row)

                log_summary_panel(
                    title=f"{dataset_name.upper()} · {VOTING_MODEL_NAME} [{experiment_suffix}] [seed={seed}]",
                    data={
                        "best_cv_score": round(voting_cv_metrics["f1_mean"], 4),
                        "cv_f1_mean": round(voting_cv_metrics["f1_mean"], 4),
                        "test_f1": round(voting_test_metrics["f1"], 4),
                        "test_recall": round(voting_test_metrics["recall"], 4),
                    },
                    border_style="green",
                )

    log_step(logger, 4, total_steps, "Guardado comparativa global y seleccion final", style="green")

    comparison_df = pd.DataFrame(all_comparison_rows)
    comparison_path = experiment_output_dir / "comparison" / "models_comparison.csv"
    save_comparison_table(all_comparison_rows, comparison_path)

    preview_rows = []
    for _, row in comparison_df.iterrows():
        preview_rows.append([
            row["seed"],
            row["experiment"],
            row["dataset"],
            row["model"],
            row["best_cv_score"] if pd.notna(row["best_cv_score"]) else row["cv_f1_mean"],
            row["test_f1"],
            row["test_recall"],
        ])

    log_table(
        title=f"Resumen comparativo de modelos [{experiment_suffix}]",
        columns=["Seed", "Experimento", "Dataset", "Modelo", "Best CV / CV F1", "Test F1", "Test Recall"],
        rows=preview_rows,
        border_style="green",
    )

    best_mid_summary = _build_best_summary(
        df=comparison_df,
        dataset_name="mid",
        base_output_dir=base_output_dir,
    )
    best_transfer_summary = _build_best_summary(
        df=comparison_df,
        dataset_name="transfer",
        base_output_dir=base_output_dir,
    )

    best_mid_path = experiment_output_dir / BEST_MID_SUMMARY_FILENAME
    best_transfer_path = experiment_output_dir / BEST_TRANSFER_SUMMARY_FILENAME

    _save_json(best_mid_summary, best_mid_path)
    _save_json(best_transfer_summary, best_transfer_path)

    log_success("Modelado finalizado correctamente")

    log_summary_panel(
        f"Mejor estrategia MID [{experiment_suffix}]",
        {
            "Modelo": best_mid_summary["selected_model_name"],
            "Experimento": best_mid_summary["selected_experiment"],
            "Semilla": best_mid_summary["selected_seed"],
            "Test F1": round(float(best_mid_summary["metrics"]["test_f1"]), 4),
            "Test Recall": round(float(best_mid_summary["metrics"]["test_recall"]), 4),
            "Resumen guardado": best_mid_path,
        },
        border_style="green",
    )

    log_summary_panel(
        f"Mejor estrategia TRANSFER [{experiment_suffix}]",
        {
            "Modelo": best_transfer_summary["selected_model_name"],
            "Experimento": best_transfer_summary["selected_experiment"],
            "Semilla": best_transfer_summary["selected_seed"],
            "Test F1": round(float(best_transfer_summary["metrics"]["test_f1"]), 4),
            "Test Recall": round(float(best_transfer_summary["metrics"]["test_recall"]), 4),
            "Resumen guardado": best_transfer_path,
        },
        border_style="green",
    )

    log_summary_panel(
        f"Salidas de modelado [{experiment_suffix}]",
        {
            "Carpeta de salida": experiment_output_dir,
            "Comparativa global": comparison_path,
            "Resumen MID": best_mid_path,
            "Resumen TRANSFER": best_transfer_path,
        },
        border_style="green",
    )

    log_banner(logger, f"FIN MODEL TRAINING [{experiment_suffix.upper()}]", style="bold green")