"""Orquestador de la etapa de datos sinteticos.

Carga los datasets limpios, ejecuta la sintesis para MID y
TRANSFERENCIA, guarda resultados y construye el reporte final.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from .config import (
    MID_CLEAN_FILENAME,
    MID_SYNTH_FILENAME,
    N_SYNTHETIC_MID,
    N_SYNTHETIC_TRANSFER,
    PROCESSED_DIR_RELATIVE_PATH,
    RANDOM_STATE,
    SYNTH_REPORT_FILENAME,
    TARGET_COLUMN,
    TRANSFER_CLEAN_FILENAME,
    TRANSFER_SYNTH_FILENAME,
)
from .synthetic_steps import (
    apply_synthetic_clinical_constraints,
    detect_column_types,
    generate_synthetic_samples,
    load_clean_datasets,
    save_synthetic_outputs,
    save_synthetic_report,
    train_synthesizer,
    validate_synthetic_dataset,
)
from .visual_logger import (
    log_banner,
    log_dataset_table,
    log_kv,
    log_step,
    log_success,
    log_summary_panel,
)


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
    log_kv(logger, "Dataset", name)
    log_kv(logger, "Shape real", f"{real_df.shape[0]} x {real_df.shape[1]}")

    ratio = float(n_samples / max(real_df.shape[0], 1))
    log_kv(logger, "Ratio sintetico/real", f"{ratio:.2f}")

    column_types = detect_column_types(real_df, target_col=TARGET_COLUMN)
    log_kv(logger, "Variables numericas", len(column_types["numeric"]))
    log_kv(logger, "Variables categoricas", len(column_types["categorical"]))

    synthesizer, engine = train_synthesizer(real_df, column_types)
    synthetic_df = generate_synthetic_samples(
        synthesizer=synthesizer,
        n_samples=n_samples,
        base_df=real_df,
        target_col=TARGET_COLUMN,
    )

    synthetic_df, constraints_report = apply_synthetic_clinical_constraints(
        synth_df=synthetic_df,
        real_df=real_df,
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
        "n_synthetic_rows_requested": int(n_samples),
        "n_synthetic_rows_final": int(synthetic_df.shape[0]),
        "synthetic_to_real_ratio": ratio,
        "column_types": column_types,
        "constraints_report": constraints_report,
        "validation": validation,
    }
    return synthetic_df, dataset_report


def run_synthetic_pipeline(logger) -> None:
    """Ejecuta pipeline sintetico completo con salida visual por pasos."""
    total_steps = 6
    root = project_root()
    processed_dir = root / PROCESSED_DIR_RELATIVE_PATH
    report_path = processed_dir / SYNTH_REPORT_FILENAME

    np.random.seed(RANDOM_STATE)
    random.seed(RANDOM_STATE)

    mid_clean_path = processed_dir / MID_CLEAN_FILENAME
    transfer_clean_path = processed_dir / TRANSFER_CLEAN_FILENAME

    log_banner(logger, "INICIO PIPELINE DE DATOS SINTETICOS", style="bold magenta")
    log_kv(logger, "Raiz del proyecto", root)
    log_kv(logger, "Random state", RANDOM_STATE)

    log_step(logger, 1, total_steps, "Carga de datasets limpios", style="magenta")
    datasets = load_clean_datasets(mid_clean_path, transfer_clean_path)
    log_kv(logger, "MID shape", f"{datasets['mid'].shape[0]} x {datasets['mid'].shape[1]}")
    log_kv(logger, "TRANSFER shape", f"{datasets['transfer'].shape[0]} x {datasets['transfer'].shape[1]}")

    log_step(logger, 2, total_steps, "Sintesis dataset MID", style="magenta")
    mid_synthetic_df, mid_report = process_dataset(
        name="mid",
        real_df=datasets["mid"],
        n_samples=N_SYNTHETIC_MID,
        logger=logger,
    )

    log_step(logger, 3, total_steps, "Sintesis dataset TRANSFERENCIA", style="magenta")
    transfer_synthetic_df, transfer_report = process_dataset(
        name="transfer",
        real_df=datasets["transfer"],
        n_samples=N_SYNTHETIC_TRANSFER,
        logger=logger,
    )

    log_step(logger, 4, total_steps, "Guardado de datasets sinteticos", style="magenta")
    mid_synth_path, transfer_synth_path = save_synthetic_outputs(
        mid_synth_df=mid_synthetic_df,
        transfer_synth_df=transfer_synthetic_df,
        output_dir=processed_dir,
        mid_synth_filename=MID_SYNTH_FILENAME,
        transfer_synth_filename=TRANSFER_SYNTH_FILENAME,
    )

    log_step(logger, 5, total_steps, "Construccion de reporte sintetico", style="magenta")
    full_report = {
        "config": {
            "target_column": TARGET_COLUMN,
            "random_state": RANDOM_STATE,
            "n_synthetic_mid": N_SYNTHETIC_MID,
            "n_synthetic_transfer": N_SYNTHETIC_TRANSFER,
            "synthetic_engine": "sdv_ctgan",
        },
        "outputs": {
            "mid_synthetic_path": str(mid_synth_path),
            "transfer_synthetic_path": str(transfer_synth_path),
        },
        "mid": mid_report,
        "transfer": transfer_report,
    }
    save_synthetic_report(report=full_report, report_path=report_path)

    log_dataset_table(
        title="Resumen datasets sinteticos",
        datasets={
            "MID_SYNTH": {
                "rows": mid_synthetic_df.shape[0],
                "columns": mid_synthetic_df.shape[1],
                "remaining_null_total": mid_report["constraints_report"]["remaining_null_total"],
                "issues": [],
            },
            "TRANSFER_SYNTH": {
                "rows": transfer_synthetic_df.shape[0],
                "columns": transfer_synthetic_df.shape[1],
                "remaining_null_total": transfer_report["constraints_report"]["remaining_null_total"],
                "issues": [],
            },
        },
        border_style="magenta",
    )

    log_success("Datasets sinteticos guardados correctamente")
    log_summary_panel(
        "Salidas de sintetico",
        {
            "Dataset MID sintetico": mid_synth_path,
            "Dataset TRANSFER sintetico": transfer_synth_path,
            "Reporte sintetico": report_path,
        },
        border_style="magenta",
    )

    log_step(logger, 6, total_steps, "Fin de proceso", style="magenta")
    log_banner(logger, "FIN PIPELINE DE DATOS SINTETICOS", style="bold green")