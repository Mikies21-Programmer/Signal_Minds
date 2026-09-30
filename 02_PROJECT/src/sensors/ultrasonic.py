"""
Módulo de sensor de distancia ultrasónico para ubicación espacial (Toponema).
Reemplaza la dependencia del acelerómetro/giróscopo por medición de proximidad
mano-cámara o mano-sensor mediante protocolo serie:
US,<timestamp_ms>,<distance_cm>,<valid>
"""

import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from ..backend.logger import get_logger

logger = get_logger("ultrasonic")


@dataclass
class DistanceReading:
    """Estructura canónica para una lectura de distancia ultrasónica."""
    distance_cm: float
    timestamp_ms: float
    is_valid: bool
    status: str  # "VALID", "OUT_OF_RANGE", "INVALID_FORMAT", "DISCONNECTED", "NO_READING"
    raw_packet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AbstractDistanceSensor(ABC):
    """Interfaz abstracta para sensores de distancia."""

    @abstractmethod
    def connect(self) -> bool:
        """Inicia la conexión física con el sensor."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra la conexión con el sensor."""
        pass

    @abstractmethod
    def read_reading(self) -> Optional[DistanceReading]:
        """Obtiene la lectura de distancia más reciente."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Indica si el sensor está conectado físicamente."""
        pass

    @abstractmethod
    def get_diagnostics(self) -> Dict[str, Any]:
        """Retorna información de diagnóstico del sensor."""
        pass


class UltrasonicSerial(AbstractDistanceSensor):
    """
    Driver para sensor ultrasónico comunicado vía puerto serie.
    Protocolo esperado:
    US,<timestamp_ms>,<distance_cm>,<valid>
    Ejemplo: US,123456,35.4,1
    """

    def __init__(
        self,
        port: str = "AUTO",
        baudrate: int = 115200,
        distance_min_cm: float = 20.0,
        distance_max_cm: float = 100.0,
        timeout_sec: float = 0.05
    ):
        self.port = port
        self.target_port = port
        self.actual_port: Optional[str] = None
        self.baudrate = baudrate
        self.distance_min_cm = distance_min_cm
        self.distance_max_cm = distance_max_cm
        self.timeout_sec = timeout_sec

        self._serial = None
        self._connected = False
        self._last_reading: Optional[DistanceReading] = None
        self._packets_received = 0
        self._packets_valid = 0
        self._last_raw_packet = ""

    def _auto_detect_port(self) -> Optional[str]:
        """Detecta automáticamente el puerto serie donde se encuentra el microcontrolador del ultrasónico."""
        try:
            import serial.tools.list_ports as lp
            available_ports = list(lp.comports())
            logger.info(f"Puertos serie detectados para sensor ultrasónico: {[p.device for p in available_ports]}")

            for p in available_ports:
                desc = (p.description or "").lower()
                # Priorizar CH340/CH343/USB-Serial/ESP32
                if any(k in desc for k in ["ch34", "usb-serial", "usb serial", "esp32", "serial"]):
                    logger.info(f"Puerto ultrasónico candidato seleccionado: {p.device} ({p.description})")
                    return p.device

            if available_ports:
                return available_ports[0].device
        except Exception as e:
            logger.warning(f"Error durante auto-detección de puerto serie: {e}")
        return None

    def connect(self) -> bool:
        """Abre la conexión serie con el microcontrolador del ultrasónico."""
        try:
            import serial
        except ImportError:
            logger.error("pyserial no está instalado.")
            self._connected = False
            return False

        port_to_open = self.target_port
        if port_to_open == "AUTO" or not port_to_open:
            port_to_open = self._auto_detect_port()

        if not port_to_open:
            logger.warning("No se encontró ningún puerto serie para sensor ultrasónico. Estado DISCONNECTED.")
            self._connected = False
            return False

        try:
            logger.info(f"Intentando conectar ultrasónico en {port_to_open} @ {self.baudrate} baud...")
            self._serial = serial.Serial(
                port=port_to_open,
                baudrate=self.baudrate,
                timeout=self.timeout_sec,
                write_timeout=0.2
            )
            self._serial.reset_input_buffer()
            self._connected = True
            self.actual_port = port_to_open
            logger.info(f"Conexión física con sensor ultrasónico establecida en {port_to_open}.")
            return True
        except Exception as e:
            logger.warning(f"No fue posible abrir {port_to_open} para sensor ultrasónico: {e}")
            self._connected = False
            self.actual_port = None
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
            return False

    def disconnect(self) -> None:
        """Cierra el puerto serie."""
        self._connected = False
        if self._serial:
            try:
                self._serial.close()
            except Exception as e:
                logger.debug(f"Error cerrando puerto serie ultrasónico: {e}")
            self._serial = None
        self.actual_port = None
        logger.info("Sensor ultrasónico desconectado.")

    def is_connected(self) -> bool:
        return self._connected and (self._serial is not None and self._serial.is_open)

    def parse_packet(self, line: str) -> Optional[DistanceReading]:
        """
        Parsea un paquete del protocolo US:
        US,<timestamp_ms>,<distance_cm>,<valid>
        """
        clean = line.strip()
        self._last_raw_packet = clean
        if not clean:
            return None

        # Formato esperado: US,<ts>,<dist>,<val>
        parts = clean.split(",")
        if len(parts) >= 4 and parts[0].upper() == "US":
            try:
                ts_ms = float(parts[1])
                dist_cm = float(parts[2])
                raw_valid = parts[3].strip().lower()
                packet_valid = raw_valid in ["1", "true", "valid", "ok"]

                in_range = (self.distance_min_cm <= dist_cm <= self.distance_max_cm)
                is_valid = packet_valid and in_range and dist_cm > 0.0

                status = "VALID" if is_valid else ("OUT_OF_RANGE" if not in_range else "INVALID")
                self._packets_received += 1
                if is_valid:
                    self._packets_valid += 1

                reading = DistanceReading(
                    distance_cm=round(dist_cm, 1),
                    timestamp_ms=ts_ms,
                    is_valid=is_valid,
                    status=status,
                    raw_packet=clean
                )
                self._last_reading = reading
                return reading
            except (ValueError, IndexError) as err:
                logger.debug(f"Error parseando paquete ultrasónico '{clean}': {err}")

        return None

    def read_reading(self) -> Optional[DistanceReading]:
        """Lee el paquete de distancia más reciente sin bloquear."""
        if not self.is_connected():
            return DistanceReading(
                distance_cm=0.0,
                timestamp_ms=time.time() * 1000.0,
                is_valid=False,
                status="DISCONNECTED",
                raw_packet=""
            )

        try:
            line = None
            # Drenar buffer para obtener la muestra más reciente
            while self._serial.in_waiting > 0:
                raw_line = self._serial.readline().decode("utf-8", errors="ignore")
                if raw_line:
                    line = raw_line

            if line:
                return self.parse_packet(line)

            # Si no hubo nueva línea en este ciclo, retornar última lectura conocida o NO_READING
            if self._last_reading:
                return self._last_reading

            return DistanceReading(
                distance_cm=0.0,
                timestamp_ms=time.time() * 1000.0,
                is_valid=False,
                status="NO_READING",
                raw_packet=""
            )
        except Exception as e:
            logger.warning(f"Error leyendo sensor ultrasónico: {e}")
            self.disconnect()
            return DistanceReading(
                distance_cm=0.0,
                timestamp_ms=time.time() * 1000.0,
                is_valid=False,
                status="DISCONNECTED",
                raw_packet=""
            )

    def get_diagnostics(self) -> Dict[str, Any]:
        return {
            "sensor_type": "ULTRASONIC",
            "protocol": "ULTRASONIC_SERIAL",
            "target_port": self.target_port,
            "actual_port": self.actual_port,
            "is_connected": self.is_connected(),
            "packets_received": self._packets_received,
            "packets_valid": self._packets_valid,
            "distance_min_cm": self.distance_min_cm,
            "distance_max_cm": self.distance_max_cm,
            "diagnostic": f"{self._last_reading.distance_cm:.1f} cm" if (self._last_reading and self._last_reading.is_valid) else "DISTANCIA NO DISPONIBLE",
            "last_reading": self._last_reading.to_dict() if self._last_reading else None,
            "last_raw_packet": self._last_raw_packet
        }


def sensor_from_settings(config: Optional[Any] = None) -> AbstractDistanceSensor:
    """Factory function para instanciar el sensor ultrasónico desde configuración."""
    sensors_conf = {}
    if config:
        if hasattr(config, "get"):
            sensors_conf = config.get("sensors", {})
        elif isinstance(config, dict):
            sensors_conf = config.get("sensors", {})

    port = sensors_conf.get("port", "AUTO")
    baudrate = int(sensors_conf.get("baudrate", 115200))
    dist_min = float(sensors_conf.get("distance_min_cm", 20.0))
    dist_max = float(sensors_conf.get("distance_max_cm", 100.0))

    return UltrasonicSerial(
        port=port,
        baudrate=baudrate,
        distance_min_cm=dist_min,
        distance_max_cm=dist_max
    )
