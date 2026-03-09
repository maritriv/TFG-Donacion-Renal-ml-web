"""Entrypoint de la etapa de datos sinteticos.

Este archivo inicializa logging, controla errores y delega
la ejecucion del pipeline sintetico a `modules.synthetic_pipeline`.

Ejecucion:
    python src/01_data_cleaning/generate_synthetic_data.py
    uv run -m src.01_data_cleaning.generate_synthetic_data
"""

from __future__ import annotations

try:
    # Modo modulo: uv run -m src.01_data_cleaning.generate_synthetic_data
    from .modules.synthetic_pipeline import run_synthetic_pipeline
    from .modules.visual_logger import configure_visual_logger
except ImportError:
    # Modo script directo: python src/01_data_cleaning/generate_synthetic_data.py
    from modules.synthetic_pipeline import run_synthetic_pipeline
    from modules.visual_logger import configure_visual_logger


def main() -> None:
    """Arranca la fase sintetica con trazas visuales por terminal."""
    logger = configure_visual_logger("generate_synthetic_data")
    try:
        run_synthetic_pipeline(logger)
    except Exception as exc:
        logger.error("Fallo en pipeline sintetico: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
