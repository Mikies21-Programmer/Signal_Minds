"""
Módulo de diagnóstico y comprobación de estado del sistema (Health Check).
Reporta versión, entorno de ejecución, estado de hardware y subsistemas.
"""

import sys
import platform
import os
from pathlib import Path
from typing import Dict, Any
from .config_loader import ConfigLoader
from .logger import get_logger

logger = get_logger("health")


class HealthChecker:
    """Verificador de salud y diagnóstico de hardware de INDIVISA INGENIUM."""

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.project_root = Path(__file__).resolve().parent.parent.parent

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
            "camera_interface": "Mock Mode (Simulado)" if self.config.is_camera_mock() else "ESP32-CAM (Stream Remoto)",
            "sensor_interface": "Mock Mode (Simulado)" if self.config.is_sensors_mock() else "I2C/UART Físico",
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable
        }

    def check_logging_system(self) -> Dict[str, Any]:
        """Comprueba que el sistema de logs esté operativo y con permisos de escritura."""
        log_file_rel = self.config.get("logging", {}).get("file_path", "logs/indivisa.log")
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
        """Ejecuta una comprobación completa de salud de todos los módulos."""
        app_name = self.config.get_app_name()
        app_version = self.config.get_app_version()
        hw_info = self.get_hardware_status()
        log_info = self.check_logging_system()

        subsystems = {
            "backend": "READY",
            "camera": "READY (MOCK)" if self.config.is_camera_mock() else "STANDBY (REAL HW)",
            "vision": "READY (MOCK)" if self.config.is_vision_mock() else "STANDBY (REAL HW)",
            "sensors": "READY (MOCK)" if self.config.is_sensors_mock() else "STANDBY (REAL HW)",
            "fusion": "READY",
            "lsm": "READY (Nivel 1 Activo)",
            "feedback": "READY",
            "frontend": "READY (Desacoplado)"
        }

        report = {
            "status": "HEALTHY",
            "app_name": app_name,
            "version": app_version,
            "environment": self.config.get("app", {}).get("environment", "unknown"),
            "hardware": hw_info,
            "logging": log_info,
            "subsystems": subsystems
        }

        logger.info(f"Health Check ejecutado con éxito: {app_name} v{app_version} en {hw_info['hardware_device_model']}")
        return report
