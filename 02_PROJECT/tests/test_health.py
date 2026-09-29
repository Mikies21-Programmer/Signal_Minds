"""
Pruebas para el sistema de Health Check y reporte de hardware.
Verifica que el estado sea NOT_READY cuando los componentes están en mock o pendientes de verificación,
cumpliendo con la regla de no reportar HEALTHY sobre hardware simulado.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backend.config_loader import ConfigLoader
from src.backend.health import HealthChecker


def test_health_check_execution():
    config = ConfigLoader()
    checker = HealthChecker(config)
    report = checker.run_full_check()

    # Si hay mocks activos, debe reportar NOT_READY
    assert report["status"] in ["HEALTHY", "NOT_READY", "DEGRADED"]
    assert report["version"] == "0.1.0"
    assert "hardware" in report
    assert "subsystems" in report
    assert "pending_hardware_verification" in report


def test_health_check_mock_mode_is_not_ready():
    """Un sistema con mocks activos nunca debe reportar HEALTHY."""
    mock_config = {
        "camera": {"mock_mode": True},
        "vision": {"mock_mode": True},
        "sensors": {"mock_mode": True}
    }
    checker = HealthChecker(mock_config)
    report = checker.run_full_check()
    assert report["status"] == "NOT_READY"


def test_hardware_status_fields():
    config = ConfigLoader()
    checker = HealthChecker(config)
    hw = checker.get_hardware_status()

    assert "platform_os" in hw
    assert "architecture" in hw
    assert "hardware_device_model" in hw
    assert "camera_interface" in hw
    assert "sensor_interface" in hw
    assert "python_version" in hw
    assert hw["platform_os"] in ["Windows", "Linux", "Darwin"]


def test_logging_system_status():
    config = ConfigLoader()
    checker = HealthChecker(config)
    log_info = checker.check_logging_system()

    assert log_info["writable"] is True
    assert log_info["status"] == "HEALTHY"
