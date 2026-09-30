"""
Pruebas del gestor de instrumentación mecatrónica y driver de ultrasonido.
Valida la arquitectura SensorBackend, desconexión limpia, reporte de diagnóstico
y lectura de distancia ultrasónica en mock y hardware real.
"""

from src.sensors.manager import SensorManager, SensorStatus, MockUltrasonicBackend, RealUltrasonicBackend


def test_sensor_manager_mock_mode():
    config = {
        "sensors": {
            "mock_mode": True,
            "sensor_type": "ULTRASONIC",
            "distance_min_cm": 20,
            "distance_max_cm": 100
        }
    }
    manager = SensorManager(config)
    manager.start()
    assert manager.get_status() == SensorStatus.CONNECTED

    sample = manager.poll_sensors()
    assert sample["is_mock"] is True
    assert sample["is_connected"] is True
    assert sample["sensor_type"] == "ULTRASONIC"
    assert "distance_cm" in sample
    assert sample["distance_valid"] is True
    assert 20.0 <= sample["distance_cm"] <= 100.0
    assert sample["timestamp"] > 0

    manager.stop()
    assert manager.get_status() == SensorStatus.DISCONNECTED


def test_sensor_manager_real_mode_unconnected_does_not_invent_hardware():
    """
    En modo REAL, si no hay puerto serie físico de ultrasonido verificado,
    el driver debe reportar DISCONNECTED y NO debe inventar distancias ni lecturas falsas.
    """
    config = {
        "sensors": {
            "mock_mode": False,
            "sensor_type": "ULTRASONIC",
            "protocol": "ULTRASONIC_SERIAL",
            "port": "COM_NON_EXISTENT_PORT_99"
        }
    }
    manager = SensorManager(config)
    manager.start()

    assert manager.get_status() == SensorStatus.DISCONNECTED
    sample = manager.poll_sensors()

    assert sample["is_connected"] is False
    assert sample["status"] == "DISCONNECTED"
    assert sample["is_mock"] is False
    assert sample["distance_valid"] is False
    assert sample["distance_cm"] is None
    assert sample["diagnostics"]["diagnostic"] == "DISTANCIA NO DISPONIBLE"

    manager.stop()


def test_sensor_calibration():
    manager = SensorManager({"sensors": {"mock_mode": True}})
    res = manager.calibrate()
    assert "status" in res
    assert res["status"] in ["SUCCESS", "MOCK_CALIBRATED"]
