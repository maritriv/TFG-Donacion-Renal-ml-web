"""Utilidades para logs visuales en terminal con Rich.

Estandariza formato de mensajes, banners de inicio/fin, cabeceras
de paso y tablas/resumenes para mejorar la trazabilidad durante
la ejecucion.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()


def configure_visual_logger(logger_name: str) -> logging.Logger:
    """Crea un logger visual basado en Rich."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    handler = RichHandler(
        console=console,
        show_time=False,
        show_level=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(getattr(logging, log_level, logging.INFO))
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(handler)
    return logger


def log_banner(logger: logging.Logger, title: str, style: str = "bold cyan") -> None:
    """Imprime un panel visual grande para inicio/fin de ejecucion."""
    console.print("")
    console.print(
        Panel.fit(
            f"[{style}]{title}[/{style}]",
            border_style=style,
            padding=(0, 2),
        )
    )


def log_step(
    logger: logging.Logger,
    step: int,
    total_steps: int,
    title: str,
    style: str = "cyan",
) -> None:
    """Imprime cabecera visual de cada paso del pipeline."""
    console.print("")
    console.print(
        Rule(
            title=f"[bold {style}]PASO {step:02d}/{total_steps:02d} · {title}[/bold {style}]",
            style=style,
        )
    )


def log_section(title: str, style: str = "yellow") -> None:
    """Imprime una seccion destacada sin usar logger."""
    console.print("")
    console.print(Rule(title=f"[bold {style}]{title}[/bold {style}]", style=style))


def log_kv(logger: logging.Logger, key: str, value: Any, key_style: str = "bold white", value_style: str = "cyan") -> None:
    """Imprime pares clave/valor de forma uniforme."""
    console.print(f"[{key_style}]• {key}:[/{key_style}] [{value_style}]{value}[/{value_style}]")


def log_info(message: str) -> None:
    """Mensaje informativo visual."""
    console.print(f"[white]{message}[/white]")


def log_success(message: str) -> None:
    """Mensaje de exito visual."""
    console.print(f"[bold green]{message}[/bold green]")


def log_warning(message: str) -> None:
    """Mensaje de warning visual."""
    console.print(f"[bold yellow]{message}[/bold yellow]")


def log_error(message: str) -> None:
    """Mensaje de error visual."""
    console.print(f"[bold red]{message}[/bold red]")


def log_list(title: str, items: Iterable[Any], style: str = "white") -> None:
    """Imprime una lista simple."""
    items = list(items)
    if not items:
        return

    console.print(f"[bold]{title}[/bold]")
    for item in items:
        console.print(f"  - [{style}]{item}[/{style}]")


def log_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    title_style: str = "bold cyan",
    header_style: str = "bold white",
    border_style: str = "cyan",
) -> None:
    """Muestra una tabla visual con Rich."""
    table = Table(title=title, title_style=title_style, header_style=header_style, border_style=border_style)
    for col in columns:
        table.add_column(str(col), overflow="fold")
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)


def log_summary_panel(title: str, data: Dict[str, Any], border_style: str = "green") -> None:
    """Muestra un resumen tipo panel con pares clave/valor."""
    lines = []
    for key, value in data.items():
        lines.append(f"[bold]{key}:[/bold] {value}")
    body = "\n".join(lines) if lines else "[dim]Sin datos[/dim]"
    console.print(Panel(body, title=title, border_style=border_style))


def log_dataset_table(
    title: str,
    datasets: Dict[str, Dict[str, Any]],
    border_style: str = "magenta",
) -> None:
    """Tabla resumen para varios datasets."""
    table = Table(title=title, border_style=border_style, header_style="bold white")
    table.add_column("Dataset", style="bold cyan")
    table.add_column("Filas", justify="right")
    table.add_column("Columnas", justify="right")
    table.add_column("Nulos restantes", justify="right")
    table.add_column("Issues", justify="right")

    for name, info in datasets.items():
        table.add_row(
            str(name),
            str(info.get("rows", "-")),
            str(info.get("columns", "-")),
            str(info.get("remaining_null_total", "-")),
            str(len(info.get("issues", []))),
        )

    console.print(table)