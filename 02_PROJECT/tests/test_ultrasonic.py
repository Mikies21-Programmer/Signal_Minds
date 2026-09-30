"""
Pruebas unitarias para el driver y sensor de distancia ultrasónico (HC-SR04 / Serial).
Valida protocolo 'US,<timestamp_ms>,<distance_cm>,<valid>', estados de lectura,
detección de desconexión y fábrica de configuración sin fabricar datos falsos.
"""

import time
import pytest
from src.sensors.ultrasonic import (
    DistanceReading,
    AbstractDistanceSensor,
    UltrasonicSerial,
    sensor_from_settings
)


def test_distance_reading_dataclass():
    """Valida la estructura y comportamiento de DistanceReading."""
    r = DistanceReading(
        distance_cm=45.2,
        is_valid=True,
        timestamp_ms=12345,
        status="VALID",
        raw_packet="US,12345,45.2,1"
    )
    assert r.distance_cm == 45.2
    assert r.is_valid is True
    assert r.status == "VALID"
    assert r.timestamp_ms == 12345
    assert r.raw_packet == "US,12345,45.2,1"


def test_ultrasonic_parse_valid_packet():
    """Valida parsing de paquete canónico 'US,<timestamp_ms>,<distance_cm>,<valid>'."""
    sensor = UltrasonicSerial(port="TEST_PORT", distance_min_cm=20.0, distance_max_cm=100.0)

    # Paquete válido dentro de rango
    reading = sensor.parse_packet("US,10050,45.5,1\n")
    assert reading is not None
    assert reading.is_valid is True
    assert reading.distance_cm == 45.5
    assert reading.timestamp_ms == 10050
    assert reading.status == "VALID"

    # Paquete válido con espacios y retornos
    reading_cr = sensor.parse_packet("  US,20000,60.0,1 \r\n")
    assert reading_cr is not None
    assert reading_cr.is_valid is True
    assert reading_cr.distance_cm == 60.0


def test_ultrasonic_parse_invalid_packet():
    """Valida rechazo de paquetes corruptos, incompletos o fuera de rango."""
    sensor = UltrasonicSerial(port="TEST_PORT", distance_min_cm=20.0, distance_max_cm=100.0)

    # Flag valid = 0
    r_flag0 = sensor.parse_packet("US,10050,45.5,0\n")
    assert r_flag0 is not None
    assert r_flag0.is_valid is False
    assert r_flag0.status == "INVALID"

    # Fuera de rango inferior (< 20 cm)
    r_low = sensor.parse_packet("US,10050,15.0,1\n")
    assert r_low is not None
    assert r_low.is_valid is False
    assert r_low.status == "OUT_OF_RANGE"

    # Fuera de rango superior (> 100 cm)
    r_high = sensor.parse_packet("US,10050,120.0,1\n")
    assert r_high is not None
    assert r_high.is_valid is False
    assert r_high.status == "OUT_OF_RANGE"

    # Prefijo incorrecto
    r_bad_prefix = sensor.parse_packet("XX,10050,45.5,1\n")
    assert r_bad_prefix is None

    # Formato corrupto / texto aleatorio
    r_corrupt = sensor.parse_packet("HOLA MUNDO\n")
    assert r_corrupt is None

    # Paquete vacío
    assert sensor.parse_packet("") is None


def test_ultrasonic_disconnected_state():
    """Valida que un sensor no conectado no fabrique lecturas y reporte DISCONNECTED."""
    sensor = UltrasonicSerial(port="COM_NON_EXISTENT_99")
    assert sensor.is_connected() is False

    reading = sensor.read_reading()
    assert reading.is_valid is False
    assert reading.status == "DISCONNECTED"

    diag = sensor.get_diagnostics()
    assert diag["is_connected"] is False
    assert diag["actual_port"] is None
    assert diag["diagnostic"] == "DISTANCIA NO DISPONIBLE"


def test_sensor_from_settings_factory():
    """Valida la creación de la instancia a partir del diccionario de configuración de settings.json."""
    settings = {
        "sensors": {
            "sensor_type": "ULTRASONIC",
            "protocol": "ULTRASONIC_SERIAL",
            "port": "COM15",
            "baudrate": 115200,
            "distance_min_cm": 25.0,
            "distance_max_cm": 95.0,
            "mock_mode": False
        }
    }
    sensor = sensor_from_settings(settings)
    assert isinstance(sensor, AbstractDistanceSensor)
    assert sensor.port == "COM15"
    assert sensor.baudrate == 115200
    assert sensor.distance_min_cm == 25.0
    assert sensor.distance_max_cm == 95.0
