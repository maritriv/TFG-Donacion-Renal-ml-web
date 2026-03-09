"""Orquestador de la etapa de limpieza.

Coordina el orden de ejecucion de todos los pasos de calidad y
transformacion, registra trazas visuales y genera salidas finales.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .cleaning_steps import (
    build_mid_dataset,
    build_transfer_dataset,
    clean_binary_columns,
    clean_numeric_columns,
    create_target,
    drop_high_null_columns,
    drop_manual_columns,
    load_donor_sheet,
    normalize_column_names,
    remove_duplicates,
    save_cleaning_report,
    save_outputs,
)
from .config import (
    BINARY_CANDIDATE_COLUMNS,
    CLEANING_REPORT_FILENAME,
    COMMON_CANDIDATE_COLUMNS,
    EXCEL_RELATIVE_PATH,
    MANUAL_DROP_COLUMNS,
    MID_OUTPUT_FILENAME,
    MID_SPECIFIC_COLUMNS,
    NULL_THRESHOLD,
    PROCESSED_DIR_RELATIVE_PATH,
    PROTECTED_COLUMNS_FOR_TARGET,
    SHEET_NAME,
    TEMPORAL_MAX_NULL_RATIO,
    TEMPORAL_OPTIONAL_COLUMNS,
    TRANSFER_OUTPUT_FILENAME,
    TRANSFER_SPECIFIC_COLUMNS,
)
from .visual_logger import log_banner, log_kv, log_step


def project_root() -> Path:
    """Detecta raiz de repositorio desde `modules/`."""
    return Path(__file__).resolve().parents[3]


def run_cleaning_pipeline(logger) -> None:
    """Ejecuta pipeline completo de limpieza, con trazas visuales por paso."""
    total_steps = 11
    root = project_root()
    excel_path = root / EXCEL_RELATIVE_PATH
    output_dir = root / PROCESSED_DIR_RELATIVE_PATH
    report_path = output_dir / CLEANING_REPORT_FILENAME

    log_banner(logger, "INICIO PIPELINE DE LIMPIEZA")
    log_kv(logger, "Raiz del proyecto", root)

    report: Dict[str, object] = {
        "input_file": str(excel_path),
        "sheet_name": SHEET_NAME,
        "null_threshold": NULL_THRESHOLD,
    }

    log_step(logger, 1, total_steps, "Carga de datos")
    df = load_donor_sheet(excel_path=excel_path, sheet_name=SHEET_NAME)
    report["rows_initial"] = int(df.shape[0])
    report["columns_initial_count"] = int(df.shape[1])
    report["columns_initial"] = [str(c) for c in df.columns]
    log_kv(logger, "Filas iniciales", df.shape[0])
    log_kv(logger, "Columnas iniciales", df.shape[1])

    log_step(logger, 2, total_steps, "Normalizacion de columnas")
    df, rename_map = normalize_column_names(df)
    report["normalized_rename_map"] = rename_map
    log_kv(logger, "Columnas renombradas", len(rename_map))
    if rename_map:
        preview = list(rename_map.items())[:8]
        for original, normalized in preview:
            logger.info("  · Renombrado: '%s' -> '%s'", original, normalized)

    log_step(logger, 3, total_steps, "Eliminacion de duplicados")
    df, dedup_stats = remove_duplicates(df)
    report.update(dedup_stats)
    log_kv(logger, "Duplicados exactos", dedup_stats["exact_duplicates_found"])
    log_kv(logger, "Duplicados por ID", dedup_stats["id_duplicates_found"])
    log_kv(logger, "Filas tras deduplicar", dedup_stats["rows_after_exact_dedup"])

    log_step(logger, 4, total_steps, "Analisis y eliminacion por nulos")
    (
        df,
        dropped_by_nulls,
        null_ratio,
        protected_not_dropped,
    ) = drop_high_null_columns(
        df=df,
        threshold=NULL_THRESHOLD,
        protected_columns=PROTECTED_COLUMNS_FOR_TARGET,
    )
    report["null_ratio_by_column"] = null_ratio
    report["dropped_columns_high_nulls"] = dropped_by_nulls
    report["protected_columns_high_nulls_not_dropped"] = protected_not_dropped
    log_kv(logger, "Columnas eliminadas por nulos", len(dropped_by_nulls))
    if dropped_by_nulls:
        logger.warning("  · Eliminadas por nulos: %s", dropped_by_nulls)
    if protected_not_dropped:
        logger.warning("  · Protegidas (no eliminadas): %s", protected_not_dropped)

    log_step(logger, 5, total_steps, "Eliminacion manual de columnas")
    df, dropped_manual, missing_manual = drop_manual_columns(df, MANUAL_DROP_COLUMNS)
    report["dropped_columns_manual"] = dropped_manual
    report["manual_columns_not_present"] = missing_manual
    log_kv(logger, "Columnas manuales eliminadas", len(dropped_manual))
    log_kv(logger, "Columnas manuales no presentes", len(missing_manual))

    log_step(logger, 6, total_steps, "Limpieza de columnas binarias")
    df, binary_issues = clean_binary_columns(df, BINARY_CANDIDATE_COLUMNS)
    report["binary_cleaning_non_mappable_counts"] = binary_issues
    problematic_binary = {k: v for k, v in binary_issues.items() if v > 0}
    log_kv(logger, "Columnas binarias procesadas", len(binary_issues))
    log_kv(logger, "Columnas con incidencias binarias", len(problematic_binary))
    if problematic_binary:
        logger.warning("  · Incidencias binarias: %s", problematic_binary)

    log_step(logger, 7, total_steps, "Validacion de variables numericas")
    df, numeric_anomalies = clean_numeric_columns(df)
    report["numeric_anomaly_counts"] = numeric_anomalies
    problematic_numeric = {k: v for k, v in numeric_anomalies.items() if v > 0}
    log_kv(logger, "Reglas numericas aplicadas", len(numeric_anomalies))
    log_kv(logger, "Columnas con valores imposibles", len(problematic_numeric))
    if problematic_numeric:
        logger.warning("  · Valores imposibles detectados: %s", problematic_numeric)

    log_step(logger, 8, total_steps, "Creacion de variable objetivo")
    df, target_stats = create_target(df, drop_undefined_rows=True)
    report.update(target_stats)
    log_kv(logger, "Donantes validos (1)", target_stats["target_valid_1"])
    log_kv(logger, "Donantes no validos (0)", target_stats["target_invalid_0"])
    log_kv(logger, "Filas eliminadas por target indefinido", target_stats["rows_removed_by_undefined_target"])

    log_step(logger, 9, total_steps, "Construccion dataset MID")
    mid_dataset, mid_existing, mid_missing, mid_temporal_null_ratios = build_mid_dataset(
        df=df,
        common_columns=COMMON_CANDIDATE_COLUMNS,
        specific_columns=MID_SPECIFIC_COLUMNS,
        temporal_candidates=TEMPORAL_OPTIONAL_COLUMNS,
        max_temporal_null_ratio=TEMPORAL_MAX_NULL_RATIO,
    )
    report["mid_shape"] = [int(mid_dataset.shape[0]), int(mid_dataset.shape[1])]
    report["mid_columns_final"] = mid_existing
    report["mid_columns_missing"] = mid_missing
    report["mid_temporal_null_ratios"] = mid_temporal_null_ratios
    log_kv(logger, "MID filas", mid_dataset.shape[0])
    log_kv(logger, "MID columnas", mid_dataset.shape[1])

    log_step(logger, 10, total_steps, "Construccion dataset TRANSFERENCIA")
    transfer_dataset, transfer_existing, transfer_missing, transfer_temporal_null_ratios = build_transfer_dataset(
        df=df,
        common_columns=COMMON_CANDIDATE_COLUMNS,
        specific_columns=TRANSFER_SPECIFIC_COLUMNS,
        temporal_candidates=TEMPORAL_OPTIONAL_COLUMNS,
        max_temporal_null_ratio=TEMPORAL_MAX_NULL_RATIO,
    )
    report["transfer_shape"] = [int(transfer_dataset.shape[0]), int(transfer_dataset.shape[1])]
    report["transfer_columns_final"] = transfer_existing
    report["transfer_columns_missing"] = transfer_missing
    report["transfer_temporal_null_ratios"] = transfer_temporal_null_ratios
    log_kv(logger, "TRANSFER filas", transfer_dataset.shape[0])
    log_kv(logger, "TRANSFER columnas", transfer_dataset.shape[1])

    log_step(logger, 11, total_steps, "Guardado de salidas y reporte")
    mid_path, transfer_path = save_outputs(
        mid_dataset=mid_dataset,
        transfer_dataset=transfer_dataset,
        output_dir=output_dir,
        mid_filename=MID_OUTPUT_FILENAME,
        transfer_filename=TRANSFER_OUTPUT_FILENAME,
    )
    report["output_mid_path"] = str(mid_path)
    report["output_transfer_path"] = str(transfer_path)

    save_cleaning_report(report_data=report, report_path=report_path)
    log_kv(logger, "Dataset MID", mid_path)
    log_kv(logger, "Dataset TRANSFERENCIA", transfer_path)
    log_kv(logger, "Reporte limpieza", report_path)
    log_banner(logger, "FIN PIPELINE DE LIMPIEZA")
