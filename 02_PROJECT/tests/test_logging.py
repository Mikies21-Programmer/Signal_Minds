"""
Pruebas del sistema de registro y logging.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backend.logger import setup_logger


def test_logger_file_write(tmp_path):
    log_file = tmp_path / "test_run.log"
    logger = setup_logger(
        name="test_logger",
        log_file=str(log_file),
        level="DEBUG",
        project_root=tmp_path
    )

    test_message = "Mensaje de prueba para trazabilidad INDIVISA"
    logger.info(test_message)

    # Verificar que el log exista y contenga el mensaje
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert test_message in content
    assert "[INFO]" in content
