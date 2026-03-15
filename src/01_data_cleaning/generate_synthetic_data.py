"""Entrypoint de la etapa de datos sinteticos.

Este archivo inicializa logging, controla errores y delega
la ejecucion del pipeline sintetico a `modules.synthetic_pipeline`.

Ejecucion:
    python src/01_data_cleaning/generate_synthetic_data.py
    uv run -m src.01_data_cleaning.generate_synthetic_data
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
    from modules.synthetic_pipeline import run_synthetic_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_step

try:
    from .modules.synthetic_pipeline import run_synthetic_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success
except ImportError:
    from modules.synthetic_pipeline import run_synthetic_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success


def main() -> None:
    """Arranca la fase sintetica con trazas visuales por terminal."""
    logger = configure_visual_logger("generate_synthetic_data")
    log_banner(logger, "EJECUCION SOLO SINTETICO", style="bold magenta")
    try:
        run_synthetic_pipeline(logger)
        log_success("SINTETICO FINALIZADO CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en pipeline sintetico: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()