"""Entrypoint de la etapa de limpieza.

Este archivo inicializa logging, controla errores y delega
la ejecucion completa al orquestador `modules.cleaning_pipeline`.

Ejecucion:
    python src/01_data_cleaning/clean_data.py
    uv run -m src.01_data_cleaning.clean_data
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
    from .modules.visual_logger import configure_visual_logger, log_banner, log_step
except ImportError:
    from modules.cleaning_pipeline import run_cleaning_pipeline
    from modules.synthetic_pipeline import run_synthetic_pipeline
    from modules.visual_logger import configure_visual_logger, log_banner, log_step

try:
    from .modules.cleaning_pipeline import run_cleaning_pipeline
    from .modules.visual_logger import configure_visual_logger, log_banner, log_success
except ImportError:
    from modules.cleaning_pipeline import run_cleaning_pipeline
    from modules.visual_logger import configure_visual_logger, log_banner, log_success


def main() -> None:
    """Arranca la fase de limpieza con salida visual por consola."""
    logger = configure_visual_logger("clean_data")
    log_banner(logger, "EJECUCION SOLO LIMPIEZA", style="bold cyan")
    try:
        run_cleaning_pipeline(logger)
        log_success("LIMPIEZA FINALIZADA CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en pipeline de limpieza: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()