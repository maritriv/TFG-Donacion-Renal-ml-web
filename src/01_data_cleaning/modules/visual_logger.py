"""Utilidades para logs visuales en terminal.

Estandariza formato de mensajes, banners de inicio/fin y cabeceras
de paso para mejorar trazabilidad durante la ejecucion.
"""

from __future__ import annotations

import logging
import os
from typing import Any

LINE = "=" * 92
SUBLINE = "-" * 92


def configure_visual_logger(logger_name: str) -> logging.Logger:
    """Crea un logger con formato compacto y consistente."""
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.DEBUG),
        format="[%(levelname)s] %(message)s",
    )
    return logging.getLogger(logger_name)


def log_banner(logger: logging.Logger, title: str) -> None:
    """Imprime un bloque visual grande para inicio/fin de ejecucion."""
    logger.info(LINE)
    logger.info(" %s", title.upper())
    logger.info(LINE)


def log_step(logger: logging.Logger, step: int, total_steps: int, title: str) -> None:
    """Imprime cabecera visual de cada paso del pipeline."""
    logger.info("")
    logger.info(SUBLINE)
    logger.info(" PASO %02d/%02d | %s", step, total_steps, title)
    logger.info(SUBLINE)


def log_kv(logger: logging.Logger, key: str, value: Any) -> None:
    """Imprime pares clave/valor de forma uniforme."""
    logger.info("  · %-38s %s", f"{key}:", value)
