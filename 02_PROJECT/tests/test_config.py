"""
Pruebas para el cargador de configuración.
Valida la carga por defecto en REAL HARDWARE MODE y la existencia de secciones críticas.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backend.config_loader import ConfigLoader


def test_load_default_config():
    loader = ConfigLoader()
    assert loader.get_app_name() == "INDIVISA_INGENIUM_2026"
    assert loader.get_app_version() == "0.1.0"
    # settings.json por defecto opera en REAL HARDWARE MODE (mock_mode = False)
    assert loader.is_camera_mock() is False
    assert loader.is_sensors_mock() is False
    assert loader.is_vision_mock() is False


def test_config_sections_exist():
    loader = ConfigLoader()
    raw = loader.raw_data
    assert "app" in raw
    assert "camera" in raw
    assert "sensors" in raw
    assert "vision" in raw
    assert "lsm" in raw
    assert "api" in raw
    assert "logging" in raw


def test_level_1_signs_configured():
    loader = ConfigLoader()
    lsm_conf = loader.get("lsm", {})
    signs = lsm_conf.get("level_1_signs", [])
    assert "A" in signs
    assert "B" in signs
    assert "C" in signs
    assert "L" in signs
    assert "Y" in signs
