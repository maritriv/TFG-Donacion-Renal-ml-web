"""Entrypoint unificado para ejecutar pipelines de data cleaning.

Uso:
    python src/01_data_cleaning/main.py

Comportamiento:
    - Ejecuta siempre limpieza y despues sintetico.

Este archivo es el punto de entrada principal de la fase 01
y permite lanzar el flujo completo con un solo comando.
"""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Unknown extension is not supported and will be removed",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    message="The 'SingleTableMetadata' is deprecated.*",
    category=FutureWarning,
)

warnings.filterwarnings(
    "ignore",
    message="We strongly recommend saving the metadata.*",
    category=UserWarning,
)

try:
    from .modules.cleaning_pipeline import run_cleaning_pipeline
    from .modules.synthetic_pipeline import run_synthetic_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_step
except ImportError:
    from modules.cleaning_pipeline import run_cleaning_pipeline

try:
    from .modules.cleaning_pipeline import run_cleaning_pipeline
    from .modules.synthetic_pipeline import run_synthetic_pipeline
    from src.common.visual_logger import (
        configure_visual_logger,
        log_banner,
        log_step,
        log_success,
    )
except ImportError:
    from modules.cleaning_pipeline import run_cleaning_pipeline
    from modules.synthetic_pipeline import run_synthetic_pipeline
    from src.common.visual_logger import (
        configure_visual_logger,
        log_banner,
        log_step,
        log_success,
    )


def main() -> None:
    """Ejecuta pipeline principal: limpieza y sintetico."""
    logger = configure_visual_logger("pipeline_main")

    log_banner(logger, "MAIN PIPELINE 01_DATA_CLEANING", style="bold blue")
    logger.info("[bold white]Modo seleccionado:[/bold white] limpieza + sintetico")

    try:
        log_step(logger, 1, 2, "Ejecucion de limpieza", style="cyan")
        run_cleaning_pipeline(logger)

        log_step(logger, 2, 2, "Ejecucion de sintetico", style="magenta")
        run_synthetic_pipeline(logger)

        log_success("MAIN FINALIZADO CORRECTAMENTE")
        log_banner(logger, "PIPELINE COMPLETO FINALIZADO", style="bold green")
    except Exception as exc:
        logger.error("Fallo en main pipeline: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()