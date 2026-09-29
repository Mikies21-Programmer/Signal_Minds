"""
Módulo de carga y validación de configuración desde archivo JSON.
Garantiza configuración segura con valores por defecto y detección de rutas.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from .exceptions import ConfigurationError
from .logger import get_logger

logger = get_logger("config")


class ConfigLoader:
    """Cargador de configuración de INDIVISA INGENIUM 2026."""

    DEFAULT_CONFIG_REL_PATH = "config/settings.json"

    def __init__(self, config_path: Optional[str] = None):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.config_path = Path(config_path) if config_path else (self.project_root / self.DEFAULT_CONFIG_REL_PATH)
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Carga el archivo de configuración JSON desde disco."""
        if not self.config_path.exists():
            logger.warning(f"Archivo de configuración no encontrado en {self.config_path}. Creando fallback.")
            raise ConfigurationError(f"No existe el archivo de configuración: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(f"Configuración cargada exitosamente desde: {self.config_path.name}")
            return self._data
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Sintaxis JSON inválida en {self.config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error al leer configuración: {e}")

    @property
    def raw_data(self) -> Dict[str, Any]:
        return self._data

    def get(self, section: str, default: Any = None) -> Any:
        """Obtiene una sección o clave de la configuración."""
        return self._data.get(section, default)

    def get_app_version(self) -> str:
        return self._data.get("app", {}).get("version", "0.0.0")

    def get_app_name(self) -> str:
        return self._data.get("app", {}).get("name", "INDIVISA")

    def is_camera_mock(self) -> bool:
        return self._data.get("camera", {}).get("mock_mode", True)

    def is_sensors_mock(self) -> bool:
        return self._data.get("sensors", {}).get("mock_mode", True)

    def is_vision_mock(self) -> bool:
        return self._data.get("vision", {}).get("mock_mode", True)
