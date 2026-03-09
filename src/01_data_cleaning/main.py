"""Entrypoint unificado para ejecutar pipelines de data cleaning.

Uso:
    python src/01_data_cleaning/main.py

Comportamiento:
    - Ejecuta siempre limpieza y despues sintetico.

Este archivo es el punto de entrada principal de la fase 01
y permite lanzar el flujo completo con un solo comando.
"""

from __future__ import annotations

try:
    # Modo modulo: uv run -m src.01_data_cleaning.main
    from .modules.cleaning_pipeline import run_cleaning_pipeline
    from .modules.synthetic_pipeline import run_synthetic_pipeline
    from .modules.visual_logger import configure_visual_logger, log_banner, log_step
except ImportError:
    # Modo script directo: python src/01_data_cleaning/main.py
    from modules.cleaning_pipeline import run_cleaning_pipeline
    from modules.synthetic_pipeline import run_synthetic_pipeline
    from modules.visual_logger import configure_visual_logger, log_banner, log_step


def main() -> None:
    """Ejecuta pipeline principal: limpieza y sintetico."""
    logger = configure_visual_logger("pipeline_main")

    log_banner(logger, "MAIN PIPELINE 01_DATA_CLEANING")
    logger.info("Modo seleccionado: limpieza + sintetico")

    try:
        log_step(logger, 1, 2, "Ejecucion de limpieza")
        run_cleaning_pipeline(logger)

        log_step(logger, 2, 2, "Ejecucion de sintetico")
        run_synthetic_pipeline(logger)

        log_banner(logger, "MAIN FINALIZADO CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en main pipeline: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
