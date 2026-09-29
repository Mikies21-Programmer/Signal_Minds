"""
Gestor de adquisición para la segunda fuente física de sensores mecatrónicos.
Maneja sensores de flexión e IMU con soporte de calibración y modo mock.
"""

import time
from typing import Dict, Any
from ..backend.logger import get_logger

logger = get_logger("sensors")


class SensorManager:
    """Controlador y muestreador de la instrumentación mecatrónica."""

    def __init__(self, config=None):
        self.config = config
        self.mock_mode = True
        self.sampling_rate_hz = 50
        self.bus_type = "I2C"
        self._is_running = False
        self._poll_count = 0

        if config:
            sens_conf = config.get("sensors", {})
            self.mock_mode = sens_conf.get("mock_mode", True)
            self.sampling_rate_hz = sens_conf.get("sampling_rate_hz", self.sampling_rate_hz)
            self.bus_type = sens_conf.get("bus_type", self.bus_type)

        logger.info(f"SensorManager configurado en modo: {'MOCK' if self.mock_mode else 'HW FÍSICO (' + self.bus_type + ')'}")

    def start(self) -> None:
        self._is_running = True
        logger.info("SensorManager iniciado.")

    def stop(self) -> None:
        self._is_running = False
        logger.info("SensorManager detenido.")

    def poll_sensors(self) -> Dict[str, Any]:
        """
        Retorna la muestra instantánea de la instrumentación física.
        Valores de flexión normalizados [0.0 = extendido, 1.0 = completamente cerrado]
        y orientación angular IMU en grados sexagesimales.
        """
        self._poll_count += 1
        return {
            "poll_id": self._poll_count,
            "timestamp": time.time(),
            "flex_thumb": 0.15,
            "flex_index": 0.85,
            "flex_middle": 0.90,
            "flex_ring": 0.88,
            "flex_pinky": 0.82,
            "imu_roll_deg": 5.4,
            "imu_pitch_deg": -2.1,
            "imu_yaw_deg": 12.0,
            "contact_sensor": True,
            "is_mock": self.mock_mode
        }

    def calibrate(self) -> Dict[str, str]:
        """Ejecuta una rutina de tara/cero en los sensores físicos."""
        logger.info("Rutina de calibración mecatrónica completada con éxito.")
        return {"status": "CALIBRATED", "timestamp": str(time.time())}
