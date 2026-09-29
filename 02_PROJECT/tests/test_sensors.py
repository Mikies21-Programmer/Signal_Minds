"""
Pruebas del gestor de instrumentación mecatrónica y driver de sensores.
Valida la arquitectura SensorBackend, desconexión limpia y reporte de diagnóstico.
"""

from src.sensors.manager import SensorManager, SensorStatus, RealHardwareSensorBackend, MockSensorBackend


def test_sensor_manager_mock_mode():
    config = {"sensors": {"mock_mode": True}}
    manager = SensorManager(config)
    manager.start()
    assert manager.get_status() == SensorStatus.CONNECTED

    sample = manager.poll_sensors()
    assert sample["is_mock"] is True
    assert sample["is_connected"] is True
    assert "flex_thumb" in sample
    assert "imu_roll_deg" in sample
    assert sample["timestamp"] > 0

    manager.stop()
    assert manager.get_status() == SensorStatus.DISCONNECTED


def test_sensor_manager_real_mode_unconnected_does_not_invent_hardware():
    """
    En modo REAL, si no hay puerto serie físico ni bus verificado,
    el driver debe reportar DISCONNECTED y NO debe inventar pines ni lecturas fijas.
    """
    config = {
        "sensors": {
            "mock_mode": False,
            "port": "COM_NON_EXISTENT_PORT_99",
            "bus_type": "UNKNOWN"
        }
    }
    manager = SensorManager(config)
    manager.start()

    assert manager.get_status() == SensorStatus.DISCONNECTED
    sample = manager.poll_sensors()

    assert sample["is_connected"] is False
    assert sample["status"] == "DISCONNECTED"
    assert sample["is_mock"] is False
    # No inventa lecturas falsas
    assert sample["flex_index"] == 0.0

    diag = sample["diagnostics"]
    assert "UNKNOWN" in diag["hardware_verification"]["imu_model"]
    assert "UNKNOWN" in diag["hardware_verification"]["pinout"]

    manager.stop()


def test_sensor_calibration():
    manager = SensorManager({"sensors": {"mock_mode": True}})
    res = manager.calibrate()
    assert "status" in res
