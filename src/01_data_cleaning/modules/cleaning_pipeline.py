"""Orquestador de la etapa de limpieza.

Coordina el orden de ejecucion de todos los pasos de calidad y
transformacion, registra trazas visuales y genera salidas finales.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .cleaning_steps import (
    analyze_null_ratio,
    build_mid_dataset,
    build_transfer_dataset,
    clean_binary_columns,
    clean_numeric_columns,
    create_target,
    drop_manual_columns,
    load_donor_sheet,
    normalize_column_names,
    remove_duplicates,
    save_cleaning_report,
    save_outputs,
    treat_missing_values_for_model_dataset,
    validate_final_dataset_for_model,
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
    SHEET_NAME,
    TARGET_COLUMN,
    TEMPORAL_MAX_NULL_RATIO,
    TEMPORAL_OPTIONAL_COLUMNS,
    TRANSFER_OUTPUT_FILENAME,
    TRANSFER_SPECIFIC_COLUMNS,
    UNKNOWN_CATEGORY_LABEL,
)
from .visual_logger import (
    log_banner,
    log_dataset_table,
    log_kv,
    log_list,
    log_step,
    log_success,
    log_summary_panel,
    log_table,
    log_warning,
)


def project_root() -> Path:
    """Detecta raiz de repositorio desde `modules/`."""
    return Path(__file__).resolve().parents[3]


def run_cleaning_pipeline(logger) -> None:
    """Ejecuta pipeline completo de limpieza, con trazas visuales por paso."""
    total_steps = 13
    root = project_root()
    excel_path = root / EXCEL_RELATIVE_PATH
    output_dir = root / PROCESSED_DIR_RELATIVE_PATH
    report_path = output_dir / CLEANING_REPORT_FILENAME

    log_banner(logger, "INICIO PIPELINE DE LIMPIEZA", style="bold cyan")
    log_kv(logger, "Raiz del proyecto", root)

    report: Dict[str, object] = {
        "input_file": str(excel_path),
        "sheet_name": SHEET_NAME,
        "null_threshold_diagnostic": NULL_THRESHOLD,
        "missing_value_strategy": {
            "numeric": "median",
            "categorical": UNKNOWN_CATEGORY_LABEL,
            "binary": "mode",
            "applied_after_dataset_build": True,
        },
    }

    log_step(logger, 1, total_steps, "Carga de datos", style="cyan")
    df = load_donor_sheet(excel_path=excel_path, sheet_name=SHEET_NAME)
    report["rows_initial"] = int(df.shape[0])
    report["columns_initial_count"] = int(df.shape[1])
    report["columns_initial"] = [str(c) for c in df.columns]
    log_kv(logger, "Filas iniciales", df.shape[0])
    log_kv(logger, "Columnas iniciales", df.shape[1])

    log_step(logger, 2, total_steps, "Normalizacion de columnas", style="cyan")
    df, rename_map = normalize_column_names(df)
    report["normalized_rename_map"] = rename_map
    log_kv(logger, "Columnas renombradas", len(rename_map))
    if rename_map:
        preview_rows = [[original, normalized] for original, normalized in list(rename_map.items())[:10]]
        log_table(
            title="Preview de columnas renombradas",
            columns=["Original", "Normalizada"],
            rows=preview_rows,
            border_style="cyan",
        )

    log_step(logger, 3, total_steps, "Eliminacion de duplicados", style="cyan")
    df, dedup_stats = remove_duplicates(df)
    report.update(dedup_stats)
    log_summary_panel(
        "Resumen de duplicados",
        {
            "Duplicados exactos": dedup_stats["exact_duplicates_found"],
            "Duplicados por ID": dedup_stats["id_duplicates_found"],
            "Filas tras deduplicar": dedup_stats["rows_after_exact_dedup"],
        },
        border_style="blue",
    )

    log_step(logger, 4, total_steps, "Analisis diagnostico de nulos", style="cyan")
    null_ratio = analyze_null_ratio(df)
    high_null_columns = [col for col, ratio in null_ratio.items() if ratio > NULL_THRESHOLD]
    report["null_ratio_by_column_before_processing"] = null_ratio
    report["columns_over_diagnostic_null_threshold"] = high_null_columns
    log_kv(logger, "Columnas > umbral de nulos (diagnostico)", len(high_null_columns))
    if high_null_columns:
        log_warning(f"Columnas sobre umbral de nulos: {high_null_columns[:15]}")

    log_step(logger, 5, total_steps, "Eliminacion manual de columnas", style="cyan")
    df, dropped_manual, missing_manual = drop_manual_columns(df, MANUAL_DROP_COLUMNS)
    report["dropped_columns_manual"] = dropped_manual
    report["manual_columns_not_present"] = missing_manual
    log_kv(logger, "Columnas manuales eliminadas", len(dropped_manual))
    log_kv(logger, "Columnas manuales no presentes", len(missing_manual))
    if dropped_manual:
        log_list("Columnas eliminadas manualmente", dropped_manual[:15], style="green")
    if missing_manual:
        log_warning(f"Columnas manuales no encontradas: {missing_manual[:15]}")

    log_step(logger, 6, total_steps, "Limpieza de columnas binarias", style="cyan")
    df, binary_issues, binary_issue_examples = clean_binary_columns(df, BINARY_CANDIDATE_COLUMNS)
    report["binary_cleaning_non_mappable_counts"] = binary_issues
    report["binary_cleaning_non_mappable_examples"] = binary_issue_examples
    problematic_binary = {k: v for k, v in binary_issues.items() if v > 0}
    log_kv(logger, "Columnas binarias procesadas", len(binary_issues))
    log_kv(logger, "Columnas con incidencias binarias", len(problematic_binary))
    if problematic_binary:
        rows = [[col, count, binary_issue_examples.get(col, [])] for col, count in problematic_binary.items()]
        log_table(
            title="Incidencias en binarias",
            columns=["Columna", "No mapeables", "Ejemplos"],
            rows=rows,
            border_style="yellow",
        )

    log_step(logger, 7, total_steps, "Validacion de variables numericas", style="cyan")
    df, numeric_anomalies, numeric_rules_applied = clean_numeric_columns(df)
    report["numeric_anomaly_counts"] = numeric_anomalies
    report["numeric_rules_applied"] = numeric_rules_applied
    problematic_numeric = {k: v for k, v in numeric_anomalies.items() if v > 0}
    log_kv(logger, "Reglas numericas aplicadas", len(numeric_rules_applied))
    log_kv(logger, "Columnas con valores imposibles", len(problematic_numeric))
    if problematic_numeric:
        rows = [
            [col, count, numeric_rules_applied.get(col, {})]
            for col, count in problematic_numeric.items()
        ]
        log_table(
            title="Anomalias numericas detectadas",
            columns=["Columna", "Valores invalidos", "Reglas"],
            rows=rows,
            border_style="yellow",
        )

    log_step(logger, 8, total_steps, "Creacion de variable objetivo", style="cyan")
    df, target_stats = create_target(df, drop_undefined_rows=True)
    report.update(target_stats)
    log_summary_panel(
        "Resumen target",
        {
            "Donantes validos (1)": target_stats["target_valid_1"],
            "Donantes no validos (0)": target_stats["target_invalid_0"],
            "Filas eliminadas target indefinido": target_stats["rows_removed_by_undefined_target"],
        },
        border_style="green",
    )

    log_step(logger, 9, total_steps, "Construccion dataset MID", style="cyan")
    mid_dataset, mid_existing, mid_missing, mid_temporal_null_ratios = build_mid_dataset(
        df=df,
        common_columns=COMMON_CANDIDATE_COLUMNS,
        specific_columns=MID_SPECIFIC_COLUMNS,
        temporal_candidates=TEMPORAL_OPTIONAL_COLUMNS,
        max_temporal_null_ratio=TEMPORAL_MAX_NULL_RATIO,
    )
    report["mid_shape_before_missing_treatment"] = [int(mid_dataset.shape[0]), int(mid_dataset.shape[1])]
    report["mid_columns_selected"] = mid_existing
    report["mid_columns_missing"] = mid_missing
    report["mid_temporal_null_ratios"] = mid_temporal_null_ratios
    log_kv(logger, "MID filas", mid_dataset.shape[0])
    log_kv(logger, "MID columnas", mid_dataset.shape[1])

    log_step(logger, 10, total_steps, "Construccion dataset TRANSFERENCIA", style="cyan")
    transfer_dataset, transfer_existing, transfer_missing, transfer_temporal_null_ratios = build_transfer_dataset(
        df=df,
        common_columns=COMMON_CANDIDATE_COLUMNS,
        specific_columns=TRANSFER_SPECIFIC_COLUMNS,
        temporal_candidates=TEMPORAL_OPTIONAL_COLUMNS,
        max_temporal_null_ratio=TEMPORAL_MAX_NULL_RATIO,
    )
    report["transfer_shape_before_missing_treatment"] = [
        int(transfer_dataset.shape[0]),
        int(transfer_dataset.shape[1]),
    ]
    report["transfer_columns_selected"] = transfer_existing
    report["transfer_columns_missing"] = transfer_missing
    report["transfer_temporal_null_ratios"] = transfer_temporal_null_ratios
    log_kv(logger, "TRANSFER filas", transfer_dataset.shape[0])
    log_kv(logger, "TRANSFER columnas", transfer_dataset.shape[1])

    log_step(logger, 11, total_steps, "Tratamiento de nulos en datasets finales", style="cyan")
    mid_dataset, mid_missing_report = treat_missing_values_for_model_dataset(
        df=mid_dataset,
        numeric_columns=["EDAD", "IMC", "ADRENALINA_N", "CAPNOMETRIA_MEDIO"],
        categorical_columns=["GRUPO_SANGUINEO", "CAUSA_FALLECIMIENTO_DANC"],
        binary_columns=["SEXO", "CARDIOCOMPRESION_EXTRAHOSPITALARIA", "RECUPERACION_ALGUN_MOMENTO", "COLESTEROL"],
        indicator_source_columns=["CAPNOMETRIA_MEDIO", "ADRENALINA_N"],
        categorical_fill_value=UNKNOWN_CATEGORY_LABEL,
    )

    transfer_dataset, transfer_missing_report = treat_missing_values_for_model_dataset(
        df=transfer_dataset,
        numeric_columns=["EDAD", "IMC", "ADRENALINA_N", "CAPNOMETRIA_TRANSFERENCIA"],
        categorical_columns=["GRUPO_SANGUINEO", "CAUSA_FALLECIMIENTO_DANC"],
        binary_columns=["SEXO", "CARDIOCOMPRESION_EXTRAHOSPITALARIA", "RECUPERACION_ALGUN_MOMENTO", "COLESTEROL"],
        indicator_source_columns=["CAPNOMETRIA_TRANSFERENCIA", "ADRENALINA_N"],
        categorical_fill_value=UNKNOWN_CATEGORY_LABEL,
    )

    report["mid_missing_treatment"] = mid_missing_report
    report["transfer_missing_treatment"] = transfer_missing_report
    log_kv(logger, "MID nulos restantes", mid_missing_report["remaining_null_total"])
    log_kv(logger, "TRANSFER nulos restantes", transfer_missing_report["remaining_null_total"])

    log_step(logger, 12, total_steps, "Validacion final de datasets", style="cyan")
    mid_validation = validate_final_dataset_for_model(
        mid_dataset,
        "MID",
        required_columns=[TARGET_COLUMN, "CAPNOMETRIA_MEDIO"],
        forbidden_columns=["RINON_DCHO_VALIDO", "RINON_IZDO_VALIDO", "CAPNOMETRIA_TRANSFERENCIA"],
    )
    transfer_validation = validate_final_dataset_for_model(
        transfer_dataset,
        "TRANSFER",
        required_columns=[TARGET_COLUMN, "CAPNOMETRIA_TRANSFERENCIA"],
        forbidden_columns=["RINON_DCHO_VALIDO", "RINON_IZDO_VALIDO", "CAPNOMETRIA_MEDIO"],
    )

    report["mid_validation"] = mid_validation
    report["transfer_validation"] = transfer_validation
    report["mid_shape_final"] = [int(mid_dataset.shape[0]), int(mid_dataset.shape[1])]
    report["transfer_shape_final"] = [int(transfer_dataset.shape[0]), int(transfer_dataset.shape[1])]

    if mid_validation["issues"]:
        log_warning(f"Problemas detectados en MID: {mid_validation['issues']}")
    if transfer_validation["issues"]:
        log_warning(f"Problemas detectados en TRANSFER: {transfer_validation['issues']}")

    log_dataset_table(
        title="Resumen datasets finales de limpieza",
        datasets={
            "MID": mid_validation,
            "TRANSFER": transfer_validation,
        },
        border_style="green",
    )

    log_step(logger, 13, total_steps, "Guardado de salidas y reporte", style="cyan")
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
    log_success("Datasets limpios guardados correctamente")
    log_summary_panel(
        "Salidas de limpieza",
        {
            "Dataset MID": mid_path,
            "Dataset TRANSFERENCIA": transfer_path,
            "Reporte limpieza": report_path,
        },
        border_style="cyan",
    )

    log_banner(logger, "FIN PIPELINE DE LIMPIEZA", style="bold green")