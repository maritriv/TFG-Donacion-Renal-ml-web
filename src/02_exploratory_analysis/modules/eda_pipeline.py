"""Orquestador de la fase 02: exploratory analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .config import (
    CATEGORICAL_CANDIDATE_COLUMNS,
    EDA_OUTPUT_DIR_RELATIVE_PATH,
    EDA_REPORT_FILENAME,
    MID_CLEAN_FILENAME,
    NUMERIC_CANDIDATE_COLUMNS,
    PROCESSED_DIR_RELATIVE_PATH,
    TARGET_COLUMN,
    TRANSFER_CLEAN_FILENAME,
)
from .eda_steps import (
    categorical_summary,
    correlation_matrix,
    dataset_basic_summary,
    detect_existing_columns,
    ensure_output_dir,
    load_dataset,
    numeric_summary,
    save_correlation_heatmap,
    save_eda_report,
    save_histograms,
    save_target_barplot,
)
from src.common.visual_logger import (
    log_banner,
    log_dataset_table,
    log_kv,
    log_step,
    log_success,
    log_summary_panel,
)


def project_root() -> Path:
    """Detecta raiz del proyecto."""
    return Path(__file__).resolve().parents[3]


def run_eda_pipeline(logger) -> None:
    """Ejecuta exploratory analysis sobre MID y TRANSFER."""
    total_steps = 5
    root = project_root()

    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH
    output_dir = root / EDA_OUTPUT_DIR_RELATIVE_PATH
    report_path = output_dir / EDA_REPORT_FILENAME

    mid_path = processed_dir / MID_CLEAN_FILENAME
    transfer_path = processed_dir / TRANSFER_CLEAN_FILENAME

    log_banner(logger, "INICIO EXPLORATORY ANALYSIS", style="bold yellow")
    log_kv(logger, "Raiz del proyecto", root)

    log_step(logger, 1, total_steps, "Carga de datasets limpios", style="yellow")
    ensure_output_dir(output_dir)
    mid_df = load_dataset(mid_path)
    transfer_df = load_dataset(transfer_path)

    log_kv(logger, "MID shape", f"{mid_df.shape[0]} x {mid_df.shape[1]}")
    log_kv(logger, "TRANSFER shape", f"{transfer_df.shape[0]} x {transfer_df.shape[1]}")

    log_step(logger, 2, total_steps, "Deteccion de columnas relevantes", style="yellow")
    mid_numeric = detect_existing_columns(mid_df, NUMERIC_CANDIDATE_COLUMNS)
    transfer_numeric = detect_existing_columns(transfer_df, NUMERIC_CANDIDATE_COLUMNS)

    mid_categorical = detect_existing_columns(mid_df, CATEGORICAL_CANDIDATE_COLUMNS)
    transfer_categorical = detect_existing_columns(transfer_df, CATEGORICAL_CANDIDATE_COLUMNS)

    log_summary_panel(
        "Columnas detectadas MID",
        {
            "Numericas": mid_numeric,
            "Categoricas/binarias": mid_categorical,
        },
        border_style="yellow",
    )
    log_summary_panel(
        "Columnas detectadas TRANSFER",
        {
            "Numericas": transfer_numeric,
            "Categoricas/binarias": transfer_categorical,
        },
        border_style="yellow",
    )

    log_step(logger, 3, total_steps, "Analisis descriptivo", style="yellow")
    mid_basic = dataset_basic_summary(mid_df, TARGET_COLUMN)
    transfer_basic = dataset_basic_summary(transfer_df, TARGET_COLUMN)

    mid_numeric_summary = numeric_summary(mid_df, mid_numeric)
    transfer_numeric_summary = numeric_summary(transfer_df, transfer_numeric)

    mid_categorical_summary = categorical_summary(mid_df, mid_categorical)
    transfer_categorical_summary = categorical_summary(transfer_df, transfer_categorical)

    log_dataset_table(
        title="Resumen basico de datasets EDA",
        datasets={
            "MID": {
                "rows": mid_basic["rows"],
                "columns": mid_basic["columns"],
                "remaining_null_total": mid_basic["missing_total"],
                "issues": [],
            },
            "TRANSFER": {
                "rows": transfer_basic["rows"],
                "columns": transfer_basic["columns"],
                "remaining_null_total": transfer_basic["missing_total"],
                "issues": [],
            },
        },
        border_style="yellow",
    )

    log_step(logger, 4, total_steps, "Generacion de graficos", style="yellow")
    mid_hist_paths = save_histograms(mid_df, mid_numeric, output_dir, "MID")
    transfer_hist_paths = save_histograms(transfer_df, transfer_numeric, output_dir, "TRANSFER")

    mid_target_plot = save_target_barplot(mid_df, TARGET_COLUMN, output_dir, "MID")
    transfer_target_plot = save_target_barplot(transfer_df, TARGET_COLUMN, output_dir, "TRANSFER")

    mid_corr = correlation_matrix(mid_df, mid_numeric)
    transfer_corr = correlation_matrix(transfer_df, transfer_numeric)

    mid_corr_path = save_correlation_heatmap(mid_corr, output_dir, "MID")
    transfer_corr_path = save_correlation_heatmap(transfer_corr, output_dir, "TRANSFER")

    log_kv(logger, "Graficos MID", len(mid_hist_paths) + int(mid_target_plot is not None) + int(mid_corr_path is not None))
    log_kv(
        logger,
        "Graficos TRANSFER",
        len(transfer_hist_paths) + int(transfer_target_plot is not None) + int(transfer_corr_path is not None),
    )

    log_step(logger, 5, total_steps, "Guardado de reporte EDA", style="yellow")
    report: Dict[str, object] = {
        "mid": {
            "basic_summary": mid_basic,
            "numeric_summary": mid_numeric_summary,
            "categorical_summary": mid_categorical_summary,
            "plots": {
                "histograms": mid_hist_paths,
                "target_distribution": mid_target_plot,
                "correlation_heatmap": mid_corr_path,
            },
        },
        "transfer": {
            "basic_summary": transfer_basic,
            "numeric_summary": transfer_numeric_summary,
            "categorical_summary": transfer_categorical_summary,
            "plots": {
                "histograms": transfer_hist_paths,
                "target_distribution": transfer_target_plot,
                "correlation_heatmap": transfer_corr_path,
            },
        },
    }

    save_eda_report(report, report_path)

    log_success("EDA finalizado correctamente")
    log_summary_panel(
        "Salidas de exploratory analysis",
        {
            "Carpeta de salida": output_dir,
            "Reporte EDA": report_path,
        },
        border_style="yellow",
    )

    log_banner(logger, "FIN EXPLORATORY ANALYSIS", style="bold green")