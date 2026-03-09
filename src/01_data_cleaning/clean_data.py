"""Entrypoint de la etapa de limpieza.

Este archivo inicializa logging, controla errores y delega
la ejecucion completa al orquestador `modules.cleaning_pipeline`.

Ejecucion:
    python src/01_data_cleaning/clean_data.py
    uv run -m src.01_data_cleaning.clean_data
"""

from __future__ import annotations

try:
    # Modo modulo: uv run -m src.01_data_cleaning.clean_data
    from .modules.cleaning_pipeline import run_cleaning_pipeline
    from .modules.visual_logger import configure_visual_logger
except ImportError:
    # Modo script directo: python src/01_data_cleaning/clean_data.py
    from modules.cleaning_pipeline import run_cleaning_pipeline
    from modules.visual_logger import configure_visual_logger


def main() -> None:
    """Arranca la fase de limpieza con salida visual por consola."""
    logger = configure_visual_logger("clean_data")
    try:
        run_cleaning_pipeline(logger)
    except Exception as exc:
        logger.error("Fallo en pipeline de limpieza: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
