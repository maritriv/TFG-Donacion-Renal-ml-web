"""Orquestador de la etapa de datos sinteticos.

Carga los datasets limpios, ejecuta la sintesis para MID y
TRANSFERENCIA, guarda resultados y construye el reporte final.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from .config import (
    MID_CLEAN_FILENAME,
    MID_SYNTH_FILENAME,
    N_SYNTHETIC_MID,
    N_SYNTHETIC_TRANSFER,
    PROCESSED_DIR_RELATIVE_PATH,
    SYNTH_REPORT_FILENAME,
    TARGET_COLUMN,
    TRANSFER_CLEAN_FILENAME,
    TRANSFER_SYNTH_FILENAME,
)
from .synthetic_steps import (
    detect_column_types,
    generate_synthetic_samples,
    load_clean_datasets,
    save_synthetic_outputs,
    save_synthetic_report,
    train_synthesizer,
    validate_synthetic_dataset,
)
from .visual_logger import log_banner, log_kv, log_step


def project_root() -> Path:
    """Detecta raiz del proyecto desde `modules/`."""
    return Path(__file__).resolve().parents[3]


def process_dataset(
    name: str,
    real_df: pd.DataFrame,
    n_samples: int,
    logger,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Ejecuta el flujo sintetico para un dataset."""
    logger.info("  · Dataset: %s", name)
    logger.info("  · Shape real: %d x %d", real_df.shape[0], real_df.shape[1])

    column_types = detect_column_types(real_df, target_col=TARGET_COLUMN)
    logger.info(
        "  · Tipos detectados: %d numericas, %d categoricas",
        len(column_types["numeric"]),
        len(column_types["categorical"]),
    )

    synthesizer, engine = train_synthesizer(real_df, column_types)
    synthetic_df = generate_synthetic_samples(
        synthesizer=synthesizer,
        n_samples=n_samples,
        base_df=real_df,
        target_col=TARGET_COLUMN,
    )
    validation = validate_synthetic_dataset(
        real_df=real_df,
        synth_df=synthetic_df,
        column_types=column_types,
        target_col=TARGET_COLUMN,
    )

    dataset_report = {
        "engine": engine,
        "columns": list(real_df.columns),
        "n_real_rows": int(real_df.shape[0]),
        "n_synthetic_rows": int(synthetic_df.shape[0]),
        "column_types": column_types,
        "validation": validation,
    }
    return synthetic_df, dataset_report


def run_synthetic_pipeline(logger) -> None:
    """Ejecuta pipeline sintetico completo con salida visual por pasos."""
    total_steps = 6
    root = project_root()
    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH
    report_path = processed_dir / SYNTH_REPORT_FILENAME

    mid_clean_path = processed_dir / MID_CLEAN_FILENAME
    transfer_clean_path = processed_dir / TRANSFER_CLEAN_FILENAME

    log_banner(logger, "INICIO PIPELINE DE DATOS SINTETICOS")
    log_kv(logger, "Raiz del proyecto", root)

    log_step(logger, 1, total_steps, "Carga de datasets limpios")
    datasets = load_clean_datasets(mid_clean_path, transfer_clean_path)
    log_kv(logger, "MID shape", f"{datasets['mid'].shape[0]} x {datasets['mid'].shape[1]}")
    log_kv(
        logger,
        "TRANSFER shape",
        f"{datasets['transfer'].shape[0]} x {datasets['transfer'].shape[1]}",
    )

    log_step(logger, 2, total_steps, "Sintesis dataset MID")
    mid_synthetic_df, mid_report = process_dataset(
        name="mid",
        real_df=datasets["mid"],
        n_samples=N_SYNTHETIC_MID,
        logger=logger,
    )
    log_kv(logger, "MID sintetico filas", mid_synthetic_df.shape[0])

    log_step(logger, 3, total_steps, "Sintesis dataset TRANSFERENCIA")
    transfer_synthetic_df, transfer_report = process_dataset(
        name="transfer",
        real_df=datasets["transfer"],
        n_samples=N_SYNTHETIC_TRANSFER,
        logger=logger,
    )
    log_kv(logger, "TRANSFER sintetico filas", transfer_synthetic_df.shape[0])

    log_step(logger, 4, total_steps, "Guardado de datasets sinteticos")
    mid_synth_path, transfer_synth_path = save_synthetic_outputs(
        mid_synth_df=mid_synthetic_df,
        transfer_synth_df=transfer_synthetic_df,
        output_dir=processed_dir,
        mid_synth_filename=MID_SYNTH_FILENAME,
        transfer_synth_filename=TRANSFER_SYNTH_FILENAME,
    )
    log_kv(logger, "Salida MID sintetico", mid_synth_path)
    log_kv(logger, "Salida TRANSFER sintetico", transfer_synth_path)

    log_step(logger, 5, total_steps, "Construccion de reporte sintetico")
    full_report = {
        "config": {
            "target_column": TARGET_COLUMN,
            "n_synthetic_mid": N_SYNTHETIC_MID,
            "n_synthetic_transfer": N_SYNTHETIC_TRANSFER,
        },
        "outputs": {
            "mid_synthetic_path": str(mid_synth_path),
            "transfer_synthetic_path": str(transfer_synth_path),
        },
        "mid": mid_report,
        "transfer": transfer_report,
    }
    save_synthetic_report(report=full_report, report_path=report_path)
    log_kv(logger, "Reporte sintetico", report_path)

    log_step(logger, 6, total_steps, "Fin de proceso")
    log_banner(logger, "FIN PIPELINE DE DATOS SINTETICOS")
