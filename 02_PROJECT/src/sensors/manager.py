"""
Gestor de adquisición para sensores mecatrónicos con arquitectura de driver desacoplada.
SensorManager coordina un SensorBackend (Real o Mock) con detección de desconexión,
diagnóstico explícito de hardware, timestamps reales y regla estricta de no inventar hardware ni pines.
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

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
        """Inicia la conexión o detección del bus/puerto físico."""
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
        """Aplica tara/cero en instrumentación."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra el puerto o bus de comunicación."""
        pass


class RealHardwareSensorBackend(SensorBackend):
    """
    Driver de hardware físico para sensores de flexión e IMU.
    No inventa pines, modelos ni direcciones I2C/UART si el hardware físico no está verificado.
    Detecta desconexiones y marca UNKNOWN cuando falte identificación física.
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.status = SensorStatus.DISCONNECTED
        self.port: Optional[str] = None
        self.baudrate: int = 115200
        self.bus_type: str = "UNKNOWN"
        self._serial_handle = None
        self._lock = threading.Lock()
        self._last_read_timestamp = 0.0

        if isinstance(self.config, dict):
            self.bus_type = self.config.get("bus_type", "UNKNOWN")
            self.baudrate = self.config.get("baudrate", 115200)
            self.port = self.config.get("port", None)

    def connect(self) -> bool:
        """Intenta detectar y abrir el canal físico (UART/Serial o I2C)."""
        with self._lock:
            self.status = SensorStatus.DETECTING
            logger.info("Detectando interfaz de comunicación física para sensores...")

            # Detección Serial vía pyserial
            try:
                import serial
                import serial.tools.list_ports

                ports = list(serial.tools.list_ports.comports())
                if not ports and not self.port:
                    logger.warning(
                        "No se detectaron puertos serie conectados. "
                        "El hardware mecatrónico permanece en estado DISCONNECTED (UNKNOWN)."
                    )
                    self.status = SensorStatus.DISCONNECTED
                    return False

                target_port = self.port or (ports[0].device if ports else None)
                if not target_port:
                    self.status = SensorStatus.DISCONNECTED
                    return False

                logger.info(f"Intentando abrir puerto serie mecatrónico: {target_port}")
                self._serial_handle = serial.Serial(target_port, baudrate=self.baudrate, timeout=0.1)
                self.status = SensorStatus.CONNECTED
                logger.info(f"Conexión física establecida en {target_port}.")
                return True

            except Exception as e:
                logger.warning(f"No fue posible conectar con hardware físico en puerto {self.port}: {e}")
                self.status = SensorStatus.DISCONNECTED
                return False

    def read_sample(self) -> Optional[Dict[str, Any]]:
        """Lee muestra física. Si el sensor está desconectado, retorna None sin inventar datos."""
        with self._lock:
            if self.status != SensorStatus.CONNECTED or self._serial_handle is None:
                return None

            try:
                line = self._serial_handle.readline().decode("utf-8", errors="ignore").strip()
                now = time.time()
                self._last_read_timestamp = now

                # Si no llegó línea válida
                if not line:
                    return None

                # Protocolo CSV básico esperado: flex0,flex1,flex2,flex3,flex4,roll,pitch,yaw,contact
                parts = line.split(",")
                if len(parts) >= 8:
                    return {
                        "timestamp": now,
                        "flex_thumb": float(parts[0]),
                        "flex_index": float(parts[1]),
                        "flex_middle": float(parts[2]),
                        "flex_ring": float(parts[3]),
                        "flex_pinky": float(parts[4]),
                        "imu_roll_deg": float(parts[5]),
                        "imu_pitch_deg": float(parts[6]),
                        "imu_yaw_deg": float(parts[7]),
                        "contact_sensor": bool(int(parts[8])) if len(parts) > 8 else False,
                        "is_valid": True,
                        "is_mock": False
                    }
            except Exception as e:
                logger.error(f"Falla de comunicación física con sensor: {e}")
                self.status = SensorStatus.ERROR

            return None

    def get_status(self) -> SensorStatus:
        with self._lock:
            return self.status

    def get_diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "driver_type": "RealHardwareSensorBackend",
                "status": self.status.value,
                "bus_type": self.bus_type,
                "port": self.port or "UNKNOWN",
                "baudrate": self.baudrate,
                "last_read_timestamp": self._last_read_timestamp,
                "hardware_verification": {
                    "imu_model": "UNKNOWN (Pendiente verificación física)",
                    "microcontroller": "UNKNOWN (Pendiente selección física)",
                    "pinout": "UNKNOWN (Prohibido asumir sin inspección de placa)",
                    "i2c_address": "UNKNOWN"
                }
            }

    def calibrate(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            if self._serial_handle and self._serial_handle.is_open:
                try:
                    self._serial_handle.write(b"CALIBRATE\n")
                    logger.info("Comando de calibración transmitido al microcontrolador de sensores.")
                except Exception as e:
                    logger.error(f"Error al enviar comando de calibración: {e}")
            return {"status": "CALIBRATED_ATTEMPTED", "timestamp": now}

    def disconnect(self) -> None:
        with self._lock:
            if self._serial_handle is not None:
                try:
                    self._serial_handle.close()
                except Exception:
                    pass
                self._serial_handle = None
            self.status = SensorStatus.DISCONNECTED
            logger.info("Backend de sensor físico desconectado.")


class MockSensorBackend(SensorBackend):
    """Backend simulado exclusivo para pruebas unitarias automatizadas."""

    def __init__(self, config=None):
        self.status = SensorStatus.CONNECTED
        self._count = 0

    def connect(self) -> bool:
        self.status = SensorStatus.CONNECTED
        return True

    def read_sample(self) -> Optional[Dict[str, Any]]:
        self._count += 1
        now = time.time()
        return {
            "timestamp": now,
            "flex_thumb": 0.15,
            "flex_index": 0.85,
            "flex_middle": 0.90,
            "flex_ring": 0.88,
            "flex_pinky": 0.82,
            "imu_roll_deg": 5.4,
            "imu_pitch_deg": -2.1,
            "imu_yaw_deg": 12.0,
            "contact_sensor": True,
            "is_valid": True,
            "is_mock": True
        }

    def get_status(self) -> SensorStatus:
        return self.status

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "driver_type": "MockSensorBackend",
            "status": "MOCK_ACTIVE",
            "is_mock": True
        }

    def calibrate(self) -> Dict[str, Any]:
        return {"status": "MOCK_CALIBRATED", "timestamp": time.time()}

    def disconnect(self) -> None:
        self.status = SensorStatus.DISCONNECTED


class SensorManager:
    """Controlador y muestreador de la instrumentación mecatrónica."""

    def __init__(self, config=None):
        self.config = config
        self.mock_mode = False
        self.sampling_rate_hz = 50
        self.bus_type = "UNKNOWN"
        self.device_address = "UNKNOWN"
        self._is_running = False
        self._poll_count = 0
        self.backend: SensorBackend

        self._parse_config(config)

        if self.mock_mode:
            self.backend = MockSensorBackend(config)
            logger.info("SensorManager inicializado en MOCK MODE (simulado solo para tests).")
        else:
            sens_conf = config.get("sensors", {}) if hasattr(config, "get") else {}
            self.backend = RealHardwareSensorBackend(sens_conf)
            logger.info("SensorManager inicializado en REAL HARDWARE MODE con backend desacoplado.")

    def _parse_config(self, config) -> None:
        if not config:
            return

        sens_conf = config.get("sensors", {}) if hasattr(config, "get") else {}
        self.mock_mode = bool(sens_conf.get("mock_mode", False))
        self.sampling_rate_hz = int(sens_conf.get("sampling_rate_hz", self.sampling_rate_hz))
        self.bus_type = sens_conf.get("bus_type", self.bus_type)
        self.device_address = sens_conf.get("device_address", self.device_address)

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
        Retorna la muestra instantánea de la instrumentación mecatrónica.
        Si el hardware físico está ausente o desconectado, reporta is_connected=False
        y NO inventa lecturas de contacto ni flexión.
        """
        self._poll_count += 1
        now = time.time()
        backend_status = self.backend.get_status()
        sample = self.backend.read_sample()

        if sample is not None and sample.get("is_valid", False):
            return {
                "poll_id": self._poll_count,
                "timestamp": sample["timestamp"],
                "status": backend_status.value,
                "is_connected": True,
                "flex_thumb": sample["flex_thumb"],
                "flex_index": sample["flex_index"],
                "flex_middle": sample["flex_middle"],
                "flex_ring": sample["flex_ring"],
                "flex_pinky": sample["flex_pinky"],
                "imu_roll_deg": sample["imu_roll_deg"],
                "imu_pitch_deg": sample["imu_pitch_deg"],
                "imu_yaw_deg": sample["imu_yaw_deg"],
                "contact_sensor": sample.get("contact_sensor", False),
                "is_mock": sample.get("is_mock", self.mock_mode),
                "diagnostics": self.backend.get_diagnostics()
            }

        # Estado desconectado o sin muestra física
        return {
            "poll_id": self._poll_count,
            "timestamp": now,
            "status": backend_status.value,
            "is_connected": False,
            "flex_thumb": 0.0,
            "flex_index": 0.0,
            "flex_middle": 0.0,
            "flex_ring": 0.0,
            "flex_pinky": 0.0,
            "imu_roll_deg": 0.0,
            "imu_pitch_deg": 0.0,
            "imu_yaw_deg": 0.0,
            "contact_sensor": False,
            "is_mock": self.mock_mode,
            "diagnostics": self.backend.get_diagnostics()
        }

    def calibrate(self) -> Dict[str, Any]:
        """Ejecuta una rutina de tara/cero en los sensores mecatrónicos."""
        return self.backend.calibrate()

    def get_status(self) -> SensorStatus:
        return self.backend.get_status()
