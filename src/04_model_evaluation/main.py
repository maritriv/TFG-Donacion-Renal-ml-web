"""Entrypoint de la fase 04: evaluacion final del modelo ganador."""

from __future__ import annotations

try:
    from .modules.evaluation_pipeline import run_evaluation_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success
except ImportError:
    from modules.evaluation_pipeline import run_evaluation_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success


def main() -> None:
    """Arranca la fase de evaluacion final."""
    logger = configure_visual_logger("model_evaluation")
    log_banner(logger, "EJECUCION MODEL EVALUATION", style="bold blue")

    try:
        run_evaluation_pipeline(logger)
        log_success("MODEL EVALUATION FINALIZADO CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en model evaluation: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()