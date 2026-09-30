"""
Gestor de adquisición para sensores mecatrónicos con arquitectura de driver desacoplada.
SensorManager coordina la lectura del sensor de distancia ultrasónico para toponema
(ubicación espacial de la mano frente al dispositivo), con detección de desconexión,
diagnóstico explícito de hardware, timestamps reales y regla estricta de no inventar datos.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

from .ultrasonic import UltrasonicSerial, DistanceReading, sensor_from_settings
from ..backend.logger import get_logger

logger = get_logger("sensors")


class SensorStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    DETECTING = "DETECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class SensorBackend(ABC):
    """Interfaz abstracta de backend de comunicación con instrumentación mecatrónica."""

    @abstractmethod
    def connect(self) -> bool:
        """Inicia la conexión o detección del puerto físico."""
        pass

    @abstractmethod
    def read_sample(self) -> Optional[Dict[str, Any]]:
        """Lee una muestra física instantánea con timestamp real."""
        pass

    @abstractmethod
    def get_status(self) -> SensorStatus:
        """Retorna el estado de conectividad del hardware."""
        pass

    @abstractmethod
    def get_diagnostics(self) -> Dict[str, Any]:
        """Retorna diagnóstico de hardware y estado de verificación."""
        pass

    @abstractmethod
    def calibrate(self) -> Dict[str, Any]:
        """Aplica rutina de tara/cero o reinicio."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra el puerto de comunicación."""
        pass


class RealHardwareSensorBackend(SensorBackend):
    """
    Driver de hardware físico para sensor ultrasónico serie.
    Protocolo esperado: US,<timestamp_ms>,<distance_cm>,<valid>
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.sensor_type: str = cfg.get("sensor_type", "ULTRASONIC")
        self.port: str = cfg.get("port", "AUTO")
        self.baudrate: int = int(cfg.get("baudrate", 115200))
        self.distance_min_cm: float = float(cfg.get("distance_min_cm", 20.0))
        self.distance_max_cm: float = float(cfg.get("distance_max_cm", 100.0))

        self.driver = UltrasonicSerial(
            port=self.port,
            baudrate=self.baudrate,
            distance_min_cm=self.distance_min_cm,
            distance_max_cm=self.distance_max_cm
        )
        self.status = SensorStatus.DISCONNECTED

    def connect(self) -> bool:
        logger.info(f"Conectando sensor ultrasónico en {self.port} @ {self.baudrate} baud...")
        self.status = SensorStatus.DETECTING
        ok = self.driver.connect()
        if ok:
            self.status = SensorStatus.CONNECTED
            logger.info(f"Sensor ultrasónico conectado en {self.driver.actual_port}.")
        else:
            self.status = SensorStatus.DISCONNECTED
            logger.warning("Sensor ultrasónico no conectado. Estado DISCONNECTED.")
        return ok

    def read_sample(self) -> Optional[Dict[str, Any]]:
        reading = self.driver.read_reading()
        if not reading:
            return None

        is_connected = self.driver.is_connected()
        self.status = SensorStatus.CONNECTED if is_connected else SensorStatus.DISCONNECTED

        return {
            "timestamp": time.time(),
            "sensor_type": "ULTRASONIC",
            "is_connected": is_connected,
            "is_valid": reading.is_valid,
            "distance_cm": reading.distance_cm,
            "distance_valid": reading.is_valid,
            "reading_status": reading.status,
            "is_mock": False,
            "raw_packet": reading.raw_packet
        }

    def get_status(self) -> SensorStatus:
        if self.driver.is_connected():
            return SensorStatus.CONNECTED
        return SensorStatus.DISCONNECTED

    def get_diagnostics(self) -> Dict[str, Any]:
        diag = self.driver.get_diagnostics()
        diag["status"] = self.get_status().value
        diag["is_mock"] = False
        return diag

    def calibrate(self) -> Dict[str, Any]:
        logger.info("Calibración / reseteo de buffer en sensor ultrasónico.")
        if self.driver.is_connected() and self.driver._serial:
            try:
                self.driver._serial.reset_input_buffer()
                return {"status": "SUCCESS", "message": "Buffer ultrasónico reseteado"}
            except Exception as e:
                return {"status": "ERROR", "message": str(e)}
        return {"status": "DISCONNECTED", "message": "Sensor no conectado"}

    def disconnect(self) -> None:
        self.driver.disconnect()
        self.status = SensorStatus.DISCONNECTED


class MockSensorBackend(SensorBackend):
    """Backend simulado exclusivo para pruebas automatizadas unitarias sin hardware."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.status = SensorStatus.CONNECTED
        self.mock_distance_cm = 45.0
        self.mock_valid = True

    def connect(self) -> bool:
        self.status = SensorStatus.CONNECTED
        return True

    def read_sample(self) -> Optional[Dict[str, Any]]:
        return {
            "timestamp": time.time(),
            "sensor_type": "ULTRASONIC",
            "is_connected": True,
            "is_valid": self.mock_valid,
            "distance_cm": self.mock_distance_cm,
            "distance_valid": self.mock_valid,
            "reading_status": "VALID" if self.mock_valid else "INVALID",
            "is_mock": True,
            "raw_packet": f"US,1000,{self.mock_distance_cm},1"
        }

    def get_status(self) -> SensorStatus:
        return self.status

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "driver_type": "MockSensorBackend",
            "sensor_type": "ULTRASONIC",
            "status": "MOCK_ACTIVE",
            "is_mock": True,
            "mock_distance_cm": self.mock_distance_cm,
            "is_connected": True
        }

    def calibrate(self) -> Dict[str, Any]:
        return {"status": "MOCK_CALIBRATED", "timestamp": time.time()}

    def disconnect(self) -> None:
        self.status = SensorStatus.DISCONNECTED


class SensorManager:
    """Controlador y muestreador de la instrumentación mecatrónica de distancia ultrasónica."""

    def __init__(self, config=None):
        self.config = config
        self.mock_mode = False
        self._is_running = False
        self._poll_count = 0
        self.backend: SensorBackend

        self._parse_config(config)

        if self.mock_mode:
            self.backend = MockSensorBackend(config)
            logger.info("SensorManager inicializado en MOCK MODE (simulado solo para tests).")
        else:
            sens_conf = config.get("sensors", {}) if hasattr(config, "get") else (config.get("sensors", {}) if isinstance(config, dict) else {})
            self.backend = RealHardwareSensorBackend(sens_conf)
            logger.info("SensorManager inicializado en REAL HARDWARE MODE con sensor ultrasónico.")

    def _parse_config(self, config) -> None:
        if not config:
            return
        sens_conf = config.get("sensors", {}) if hasattr(config, "get") else (config.get("sensors", {}) if isinstance(config, dict) else {})
        self.mock_mode = bool(sens_conf.get("mock_mode", False))

    def start(self) -> None:
        self._is_running = True
        self.backend.connect()
        logger.info(f"SensorManager iniciado. Estado backend: {self.backend.get_status().value}")

    def stop(self) -> None:
        self._is_running = False
        self.backend.disconnect()
        logger.info("SensorManager detenido.")

    def poll_sensors(self) -> Dict[str, Any]:
        """
        Retorna la muestra instantánea del sensor ultrasónico.
        Si el hardware físico está ausente o desconectado, reporta is_connected=False
        y NO inventa lecturas de distancia.
        """
        self._poll_count += 1
        now = time.time()
        backend_status = self.backend.get_status()
        sample = self.backend.read_sample()

        if sample is not None and sample.get("is_connected", False):
            dist = sample.get("distance_cm", 0.0)
            valid = sample.get("distance_valid", False)
            diag_str = f"{dist:.1f} cm" if valid else "DISTANCIA NO DISPONIBLE"

            return {
                "poll_id": self._poll_count,
                "timestamp": sample.get("timestamp", now),
                "status": backend_status.value,
                "is_connected": True,
                "sensor_type": "ULTRASONIC",
                "distance_cm": dist,
                "distance_valid": valid,
                "is_mock": sample.get("is_mock", self.mock_mode),
                "diagnostics": {
                    "diagnostic": diag_str,
                    "reading_status": sample.get("reading_status", "UNKNOWN"),
                    "raw_packet": sample.get("raw_packet", ""),
                    "hardware": self.backend.get_diagnostics()
                }
            }

        # Estado desconectado o sin muestra física
        return {
            "poll_id": self._poll_count,
            "timestamp": now,
            "status": backend_status.value,
            "is_connected": False,
            "sensor_type": "ULTRASONIC",
            "distance_cm": None,
            "distance_valid": False,
            "is_mock": self.mock_mode,
            "diagnostics": {
                "diagnostic": "DISTANCIA NO DISPONIBLE",
                "reading_status": "DISCONNECTED",
                "raw_packet": "",
                "hardware": self.backend.get_diagnostics()
            }
        }

    def calibrate(self) -> Dict[str, Any]:
        """Ejecuta una rutina de tara/cero o reseteo en el sensor."""
        return self.backend.calibrate()

    def get_status(self) -> SensorStatus:
        return self.backend.get_status()


# Alias para compatibilidad con pruebas de ultrasonido
MockUltrasonicBackend = MockSensorBackend
RealUltrasonicBackend = RealHardwareSensorBackend
