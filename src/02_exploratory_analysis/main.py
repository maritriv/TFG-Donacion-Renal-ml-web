"""Entrypoint de la fase 02: exploratory analysis."""

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore",
    message="Unknown extension is not supported and will be removed",
    category=UserWarning,
)

try:
    from .modules.eda_pipeline import run_eda_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success
except ImportError:
    from modules.eda_pipeline import run_eda_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success


def main() -> None:
    """Arranca la fase de exploratory analysis."""
    logger = configure_visual_logger("exploratory_analysis")
    log_banner(logger, "EJECUCION EXPLORATORY ANALYSIS", style="bold yellow")
    try:
        run_eda_pipeline(logger)
        log_success("EXPLORATORY ANALYSIS FINALIZADO CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en exploratory analysis: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()