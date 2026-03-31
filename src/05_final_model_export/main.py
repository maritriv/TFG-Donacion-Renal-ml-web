"""Entrypoint de la fase 05: exportacion final del modelo."""

from __future__ import annotations

try:
    from .modules.export_pipeline import run_export_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success
except ImportError:
    from modules.export_pipeline import run_export_pipeline
    from src.common.visual_logger import configure_visual_logger, log_banner, log_success


def main() -> None:
    logger = configure_visual_logger("final_model_export")
    log_banner(logger, "EJECUCION FINAL MODEL EXPORT", style="bold yellow")

    try:
        run_export_pipeline(logger)
        log_success("FINAL MODEL EXPORT FINALIZADO CORRECTAMENTE")
    except Exception as exc:
        logger.error("Fallo en final model export: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()