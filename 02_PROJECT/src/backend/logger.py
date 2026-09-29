"""
Sistema centralizado de registro y trazabilidad de eventos (Logging).
Garantiza registro dual: consola y archivo rotativo en logs/indivisa.log.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized_loggers = {}


def setup_logger(
    name: str = "indivisa",
    log_file: Optional[str] = "logs/indivisa.log",
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 3,
    log_to_console: bool = True,
    project_root: Optional[Path] = None
) -> logging.Logger:
    """
    Configura y retorna una instancia de logger configurada con rotación de archivos y consola.
    """
    if name in _initialized_loggers:
        return _initialized_loggers[name]

    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.propagate = False

    # Limpiar handlers previos si existieran
    while logger.handlers:
        logger.handlers.pop()

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # 1. Handler de Consola
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 2. Handler de Archivo con Rotación
    if log_file:
        if project_root is None:
            # Asume raíz en 02_PROJECT (dos niveles arriba de backend)
            project_root = Path(__file__).resolve().parent.parent.parent

        full_log_path = project_root / log_file
        full_log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=str(full_log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _initialized_loggers[name] = logger
    return logger


def get_logger(name: str = "indivisa") -> logging.Logger:
    """Retorna un logger existente o crea uno por defecto."""
    if name in _initialized_loggers:
        return _initialized_loggers[name]
    return setup_logger(name)
