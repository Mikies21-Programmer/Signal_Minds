"""
Módulo de diagnóstico y comprobación de estado del sistema (Health Check).
Reporta versión, entorno de ejecución, estado de hardware y subsistemas reales.
Estados válidos de salud: HEALTHY, DEGRADED, NOT_READY, ERROR.
NUNCA reporta HEALTHY si los subsistemas están en modo MOCK o con hardware UNKNOWN.
"""

import sys
import platform
from pathlib import Path
from typing import Dict, Any, Union
from .config_loader import ConfigLoader
from .logger import get_logger

logger = get_logger("health")


class HealthChecker:
    """Verificador de salud y diagnóstico de hardware de INDIVISA INGENIUM."""

    def __init__(self, config_loader: Union[ConfigLoader, Dict[str, Any]]):
        self.config = config_loader
        self.project_root = Path(__file__).resolve().parent.parent.parent

    def _get_config_val(self, section: str, key: str, default: Any = None) -> Any:
        if hasattr(self.config, "get"):
            sec = self.config.get(section, {})
            if isinstance(sec, dict):
                return sec.get(key, default)
            return sec
        return default

    def is_camera_mock(self) -> bool:
        if hasattr(self.config, "is_camera_mock"):
            return self.config.is_camera_mock()
        return bool(self._get_config_val("camera", "mock_mode", True))

    def is_sensors_mock(self) -> bool:
        if hasattr(self.config, "is_sensors_mock"):
            return self.config.is_sensors_mock()
        return bool(self._get_config_val("sensors", "mock_mode", True))

    def is_vision_mock(self) -> bool:
        if hasattr(self.config, "is_vision_mock"):
            return self.config.is_vision_mock()
        return bool(self._get_config_val("vision", "mock_mode", True))

    def get_hardware_status(self) -> Dict[str, Any]:
        """Inspecciona y reporta el entorno de hardware real detectado."""
        system_platform = platform.system()
        machine = platform.machine()
        processor = platform.processor()

        is_rpi = False
        rpi_model = "UNKNOWN"

        # Detección de Raspberry Pi (en Linux)
        if system_platform == "Linux":
            try:
                with open("/proc/device-tree/model", "r", encoding="utf-8") as f:
                    rpi_model = f.read().strip("\x00\n ")
                    is_rpi = "Raspberry Pi" in rpi_model
            except Exception:
                pass

        return {
            "platform_os": system_platform,
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": machine,
            "processor": processor or "UNKNOWN",
            "is_raspberry_pi": is_rpi,
            "hardware_device_model": rpi_model if is_rpi else ("Laptop / Dev Host" if system_platform == "Windows" else "Generic Linux Host"),
            "camera_interface": "MOCK (Simulado)" if self.is_camera_mock() else "ESP32-CAM (Stream Remoto)",
            "sensor_interface": "MOCK (Simulado)" if self.is_sensors_mock() else "UNKNOWN (Pendiente Verificación)",
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable
        }

    def check_logging_system(self) -> Dict[str, Any]:
        """Comprueba que el sistema de logs esté operativo y con permisos de escritura."""
        log_file_rel = self._get_config_val("logging", "file_path", "logs/indivisa.log")
        log_path = self.project_root / log_file_rel
        can_write = False
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("")
            can_write = True
        except Exception as e:
            logger.error(f"Falla al verificar escritura en archivo de log: {e}")

        return {
            "log_path": str(log_path),
            "log_exists": log_path.exists(),
            "writable": can_write,
            "status": "HEALTHY" if can_write else "DEGRADED"
        }

    def run_full_check(self) -> Dict[str, Any]:
        """
        Ejecuta comprobación estricta de salud:
        - Si algún subsistema crítico está en MOCK: estado = NOT_READY (nunca HEALTHY para demo).
        - Si el sensor está en UNKNOWN sin verificar: estado = NOT_READY.
        - Si hay fallas de escritura o recursos: DEGRADED o ERROR.
        - Solo si todo el hardware real está operativo y verificado: HEALTHY.
        """
        app_name = (
            self.config.get_app_name()
            if hasattr(self.config, "get_app_name")
            else self._get_config_val("app", "name", "INDIVISA_INGENIUM_2026")
        )
        app_version = (
            self.config.get_app_version()
            if hasattr(self.config, "get_app_version")
            else self._get_config_val("app", "version", "0.1.0")
        )
        environment = self._get_config_val("app", "environment", "development")

        hw_info = self.get_hardware_status()
        log_info = self.check_logging_system()

        cam_mock = self.is_camera_mock()
        vis_mock = self.is_vision_mock()
        sens_mock = self.is_sensors_mock()

        subsystems = {
            "backend": "READY",
            "camera": "MOCK_ACTIVE (NOT_READY para demo real)" if cam_mock else "READY (REAL HW)",
            "vision": "MOCK_ACTIVE (NOT_READY para demo real)" if vis_mock else "READY (MEDIAPIPE REAL)",
            "sensors": "MOCK_ACTIVE (NOT_READY para demo real)" if sens_mock else "PENDING_HARDWARE_VERIFICATION (UNKNOWN)",
            "fusion": "READY",
            "lsm": "READY (Nivel 1 Activo)",
            "feedback": "READY",
            "frontend": "READY (Laptop Desacoplada)"
        }

        # Determinación rigurosa del estado global
        if log_info.get("status") != "HEALTHY":
            overall_status = "DEGRADED"
        elif cam_mock or vis_mock or sens_mock:
            # Nunca decir que el hardware real funciona si solamente funciona el mock
            overall_status = "NOT_READY"
        else:
            # Si no es mock pero sensor sigue como UNKNOWN
            overall_status = "NOT_READY"

        report = {
            "status": overall_status,
            "app_name": app_name,
            "version": app_version,
            "environment": environment,
            "hardware": hw_info,
            "logging": log_info,
            "subsystems": subsystems,
            "pending_hardware_verification": [
                "ESP32-CAM (Modelo exacto de sensor y PCB)",
                "Sensor Mecatrónico (Modelo de IMU, galgas de flexión, bus físico I2C/UART y pines)"
            ]
        }

        logger.info(f"Health Check ejecutado: Estado={overall_status}, Hardware={hw_info['hardware_device_model']}")
        return report
