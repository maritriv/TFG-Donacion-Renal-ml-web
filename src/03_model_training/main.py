"""Entrypoint de la fase 03: model training."""

from __future__ import annotations

try:
    from .modules.training_pipeline import run_training_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success
except ImportError:
    from modules.training_pipeline import run_training_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success


def main() -> None:
    """Arranca la fase de entrenamiento de modelos."""
    logger = configure_visual_logger("model_training")
    log_banner(logger, "EJECUCION MODEL TRAINING", style="bold green")

    try:
        log_banner(logger, "EXPERIMENTO 1: SOLO DATOS REALES", style="bold cyan")
        run_training_pipeline(logger, use_synthetic=False)
        log_success("EXPERIMENTO SOLO DATOS REALES FINALIZADO CORRECTAMENTE")

        log_banner(logger, "EXPERIMENTO 2: DATOS REALES + SINTETICOS", style="bold magenta")
        run_training_pipeline(logger, use_synthetic=True)
        log_success("EXPERIMENTO REALES + SINTETICOS FINALIZADO CORRECTAMENTE")

        log_success("MODEL TRAINING FINALIZADO CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en model training: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()