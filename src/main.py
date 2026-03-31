"""
Main global del proyecto.

Orquesta la ejecucion de todas las fases:
01 -> limpieza + sintetico
02 -> analisis exploratorio
03 -> model training
04 -> evaluacion
05 -> export final
"""

from __future__ import annotations

from importlib import import_module

from src.common.visual_logger import log_banner, log_step, log_success


def _load_main(module_path: str):
    """Carga dinamicamente la funcion main de un modulo."""
    module = import_module(module_path)
    return module.main


def run_pipeline():
    """Ejecuta todas las fases del proyecto en orden."""
    total_steps = 5

    log_banner(None, "EJECUCION COMPLETA DEL PIPELINE", style="bold cyan")

    # 01 · DATA CLEANING + SYNTHETIC
    log_step(None, 1, total_steps, "Fase 01 · Data Cleaning + Synthetic", style="cyan")
    cleaning_main = _load_main("src.01_data_cleaning.main")
    cleaning_main()

    # 02 · EDA
    log_step(None, 2, total_steps, "Fase 02 · Exploratory Analysis", style="cyan")
    eda_main = _load_main("src.02_exploratory_analysis.main")
    eda_main()

    # 03 · MODEL TRAINING
    log_step(None, 3, total_steps, "Fase 03 · Model Training", style="cyan")
    training_main = _load_main("src.03_model_training.main")
    training_main()

    # 04 · MODEL EVALUATION
    log_step(None, 4, total_steps, "Fase 04 · Model Evaluation", style="cyan")
    evaluation_main = _load_main("src.04_model_evaluation.main")
    evaluation_main()

    # 05 · EXPORT FINAL
    log_step(None, 5, total_steps, "Fase 05 · Final Model Export", style="cyan")
    export_main = _load_main("src.05_final_model_export.main")
    export_main()

    log_success("PIPELINE COMPLETO FINALIZADO CORRECTAMENTE")


if __name__ == "__main__":
    run_pipeline()