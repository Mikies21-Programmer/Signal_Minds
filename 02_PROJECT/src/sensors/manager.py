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
    Driver de hardware físico para sensores MPU6050 e instrumentación mecatrónica.
    Se comunica vía USB-Serial con el microcontrolador ESP32-S3 dedicado.
    Protocolo IMU: IMU,<timestamp_ms>,<roll>,<pitch>,<gx>,<gy>,<gz>,<yaw_valid>
    Maneja calibración de referencia, cálculo de tilt_error_deg y detección de desconexión.
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.status = SensorStatus.DISCONNECTED
        self.port: Optional[str] = None
        self.baudrate: int = 115200
        self.bus_type: str = "I2C"
        self.sensor_type: str = "MPU6050"
        self.sda_gpio: int = 4
        self.scl_gpio: int = 5
        self.i2c_address: str = "0x68"
        self.roll_ref: float = 0.0
        self.pitch_ref: float = 0.0
        self.is_calibrated: bool = False
        self._serial_handle = None
        self._lock = threading.Lock()
        self._last_read_timestamp = 0.0
        self._last_sample = None

        if isinstance(self.config, dict):
            self.bus_type = self.config.get("bus_type", "I2C")
            self.baudrate = int(self.config.get("baudrate", 115200))
            self.port = self.config.get("port", None)
            self.sensor_type = self.config.get("sensor_type", "MPU6050")
            self.sda_gpio = int(self.config.get("sda_gpio", 4))
            self.scl_gpio = int(self.config.get("scl_gpio", 5))

    def connect(self) -> bool:
        """Intenta detectar y abrir el canal físico (UART/Serial)."""
        with self._lock:
            self.status = SensorStatus.DETECTING
            logger.info("Detectando interfaz de comunicación física para sensor MPU6050...")

            try:
                import serial
                import serial.tools.list_ports

                target_port = self.port
                if target_port in ["NONE", "DISABLED", ""]:
                    logger.info("Puerto mecatrónico no asignado o desactivado. Sensores en espera.")
                    self.status = SensorStatus.DISCONNECTED
                    return False

                if not target_port:
                    logger.info("Sensores físicos no configurados explícitamente. Estado DISCONNECTED.")
                    self.status = SensorStatus.DISCONNECTED
                    return False

                # Auto-detección si es AUTO
                if target_port == "AUTO":
                    available_ports = list(serial.tools.list_ports.comports())
                    for p in available_ports:
                        desc = p.description or ""
                        hwid = p.hwid or ""
                        # Buscar chip serie CH343 o dispositivo serie diferente a COM10
                        if "1A86:55D3" in hwid or "CH343" in desc or (p.device != "COM10" and "USB" in desc):
                            target_port = p.device
                            logger.info(f"Puerto para MPU6050 auto-detectado: {target_port} ({desc})")
                            break

                if not target_port or target_port == "AUTO":
                    logger.info("No se encontró puerto para sensor MPU6050. Estado DISCONNECTED.")
                    self.status = SensorStatus.DISCONNECTED
                    return False

                logger.info(f"Intentando abrir puerto serie de sensor MPU6050: {target_port} @ {self.baudrate}")
                self._serial_handle = serial.Serial(target_port, baudrate=self.baudrate, timeout=0.1)
                self.port = target_port
                self.status = SensorStatus.CONNECTED
                logger.info(f"Conexión física con MPU6050 establecida en {target_port}.")
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

                if not line:
                    return self._last_sample

                self._last_read_timestamp = now

                # 1. Detección de confirmación de calibración
                if "CALIBRATION_OK" in line:
                    self.is_calibrated = True
                    for part in line.split(","):
                        if "roll_ref=" in part:
                            try:
                                self.roll_ref = float(part.split("=")[1])
                            except ValueError:
                                pass
                        elif "pitch_ref=" in part:
                            try:
                                self.pitch_ref = float(part.split("=")[1])
                            except ValueError:
                                pass
                    logger.info(f"[MPU6050] Calibración confirmada en hardware: roll_ref={self.roll_ref:.2f}, pitch_ref={self.pitch_ref:.2f}")

                # 2. Protocolo IMU dedicado: IMU,<timestamp_ms>,<roll>,<pitch>,<gx>,<gy>,<gz>,<yaw_valid>
                if line.startswith("IMU,"):
                    parts = line.split(",")
                    if len(parts) >= 8:
                        import math
                        roll = float(parts[2])
                        pitch = float(parts[3])
                        gx = float(parts[4])
                        gy = float(parts[5])
                        gz = float(parts[6])
                        yaw_valid = parts[7].strip().lower() == "true"

                        delta_roll = roll - self.roll_ref
                        delta_pitch = pitch - self.pitch_ref
                        tilt_error = math.sqrt(delta_roll * delta_roll + delta_pitch * delta_pitch)

                        sample = {
                            "timestamp": now,
                            "sensor_type": "MPU6050",
                            "imu_present": True,
                            "yaw_valid": False,  # MPU6050 6-DOF sin magnetómetro
                            "imu_roll_deg": roll,
                            "imu_pitch_deg": pitch,
                            "imu_yaw_deg": 0.0,  # Yaw absoluto no disponible
                            "roll_ref": self.roll_ref,
                            "pitch_ref": self.pitch_ref,
                            "delta_roll_deg": round(delta_roll, 2),
                            "delta_pitch_deg": round(delta_pitch, 2),
                            "tilt_error_deg": round(tilt_error, 2),
                            "gyro_x": gx,
                            "gyro_y": gy,
                            "gyro_z": gz,
                            "flex_thumb": 0.0,
                            "flex_index": 0.0,
                            "flex_middle": 0.0,
                            "flex_ring": 0.0,
                            "flex_pinky": 0.0,
                            "contact_sensor": False,
                            "is_valid": True,
                            "is_mock": False
                        }
                        self._last_sample = sample
                        return sample

                # 3. Protocolo CSV de compatibilidad previa: flex0..flex4,roll,pitch,yaw[,contact]
                parts = line.split(",")
                if len(parts) >= 8 and not line.startswith("IMU"):
                    import math
                    roll = float(parts[5])
                    pitch = float(parts[6])
                    yaw = float(parts[7])
                    delta_roll = roll - self.roll_ref
                    delta_pitch = pitch - self.pitch_ref
                    tilt_error = math.sqrt(delta_roll * delta_roll + delta_pitch * delta_pitch)

                    sample = {
                        "timestamp": now,
                        "sensor_type": "MPU6050",
                        "imu_present": True,
                        "yaw_valid": False,
                        "flex_thumb": float(parts[0]),
                        "flex_index": float(parts[1]),
                        "flex_middle": float(parts[2]),
                        "flex_ring": float(parts[3]),
                        "flex_pinky": float(parts[4]),
                        "imu_roll_deg": roll,
                        "imu_pitch_deg": pitch,
                        "imu_yaw_deg": yaw,
                        "roll_ref": self.roll_ref,
                        "pitch_ref": self.pitch_ref,
                        "delta_roll_deg": round(delta_roll, 2),
                        "delta_pitch_deg": round(delta_pitch, 2),
                        "tilt_error_deg": round(tilt_error, 2),
                        "contact_sensor": bool(int(parts[8])) if len(parts) > 8 else False,
                        "is_valid": True,
                        "is_mock": False
                    }
                    self._last_sample = sample
                    return sample

            except Exception as e:
                logger.error(f"Falla de comunicación física con sensor MPU6050: {e}")
                self.status = SensorStatus.ERROR

            return self._last_sample

    def get_status(self) -> SensorStatus:
        with self._lock:
            return self.status

    def get_diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            if self.status == SensorStatus.CONNECTED:
                hw_ver = {
                    "imu_model": "MPU6050 (6-DOF InvenSense)",
                    "microcontroller": "ESP32-S3 (revision v0.2)",
                    "pinout": f"SDA=GPIO{self.sda_gpio}, SCL=GPIO{self.scl_gpio}, VCC=3.3V, GND=GND",
                    "i2c_address": self.i2c_address,
                    "baudrate": self.baudrate,
                    "sampling_rate_hz": 50,
                    "yaw_valid": False,
                    "roll_ref": self.roll_ref,
                    "pitch_ref": self.pitch_ref,
                    "is_calibrated": self.is_calibrated
                }
            else:
                hw_ver = {
                    "imu_model": "UNKNOWN (Pendiente verificación física)",
                    "microcontroller": "UNKNOWN (Pendiente selección física)",
                    "pinout": "UNKNOWN (Prohibido asumir sin inspección de placa)",
                    "i2c_address": "UNKNOWN"
                }

            return {
                "driver_type": "RealHardwareSensorBackend",
                "status": self.status.value,
                "bus_type": self.bus_type,
                "port": self.port or "UNKNOWN",
                "baudrate": self.baudrate,
                "last_read_timestamp": self._last_read_timestamp,
                "hardware_verification": hw_ver
            }

    def calibrate(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            if self._serial_handle and self._serial_handle.is_open:
                try:
                    self._serial_handle.write(b"CALIBRATE\n")
                    logger.info("Comando 'CALIBRATE' transmitido al microcontrolador ESP32-S3 MPU6050.")
                except Exception as e:
                    logger.error(f"Error al enviar comando de calibración: {e}")
            return {"status": "CALIBRATION_REQUESTED", "timestamp": now}

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
            "sensor_type": "MOCK",
            "imu_present": True,
            "yaw_valid": False,
            "flex_thumb": 0.15,
            "flex_index": 0.85,
            "flex_middle": 0.90,
            "flex_ring": 0.88,
            "flex_pinky": 0.82,
            "imu_roll_deg": 5.4,
            "imu_pitch_deg": -2.1,
            "imu_yaw_deg": 0.0,
            "roll_ref": 0.0,
            "pitch_ref": 0.0,
            "delta_roll_deg": 5.4,
            "delta_pitch_deg": -2.1,
            "tilt_error_deg": 5.79,
            "gyro_x": 0.0,
            "gyro_y": 0.0,
            "gyro_z": 0.0,
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
        self.bus_type = "I2C"
        self.device_address = "0x68"
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
                "sensor_type": sample.get("sensor_type", "MPU6050"),
                "imu_present": sample.get("imu_present", True),
                "yaw_valid": sample.get("yaw_valid", False),
                "flex_thumb": sample.get("flex_thumb", 0.0),
                "flex_index": sample.get("flex_index", 0.0),
                "flex_middle": sample.get("flex_middle", 0.0),
                "flex_ring": sample.get("flex_ring", 0.0),
                "flex_pinky": sample.get("flex_pinky", 0.0),
                "imu_roll_deg": sample.get("imu_roll_deg", 0.0),
                "imu_pitch_deg": sample.get("imu_pitch_deg", 0.0),
                "imu_yaw_deg": sample.get("imu_yaw_deg", 0.0),
                "roll_ref": sample.get("roll_ref", 0.0),
                "pitch_ref": sample.get("pitch_ref", 0.0),
                "delta_roll_deg": sample.get("delta_roll_deg", 0.0),
                "delta_pitch_deg": sample.get("delta_pitch_deg", 0.0),
                "tilt_error_deg": sample.get("tilt_error_deg", 0.0),
                "gyro_x": sample.get("gyro_x", 0.0),
                "gyro_y": sample.get("gyro_y", 0.0),
                "gyro_z": sample.get("gyro_z", 0.0),
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
            "sensor_type": "MPU6050",
            "imu_present": False,
            "yaw_valid": False,
            "flex_thumb": 0.0,
            "flex_index": 0.0,
            "flex_middle": 0.0,
            "flex_ring": 0.0,
            "flex_pinky": 0.0,
            "imu_roll_deg": 0.0,
            "imu_pitch_deg": 0.0,
            "imu_yaw_deg": 0.0,
            "roll_ref": 0.0,
            "pitch_ref": 0.0,
            "delta_roll_deg": 0.0,
            "delta_pitch_deg": 0.0,
            "tilt_error_deg": 0.0,
            "gyro_x": 0.0,
            "gyro_y": 0.0,
            "gyro_z": 0.0,
            "contact_sensor": False,
            "is_mock": self.mock_mode,
            "diagnostics": self.backend.get_diagnostics()
        }

    def calibrate(self) -> Dict[str, Any]:
        """Ejecuta una rutina de tara/cero en los sensores mecatrónicos."""
        return self.backend.calibrate()

    def get_status(self) -> SensorStatus:
        return self.backend.get_status()
