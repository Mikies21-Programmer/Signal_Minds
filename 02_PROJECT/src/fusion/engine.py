"""
Motor de fusión sensorial (Fusión Visión Artificial + Sensores Físicos).
Correlaciona temporalmente los landmarks con la postura y cinemática mecatrónica.
"""

from typing import Optional, Dict, Any
from ..backend.logger import get_logger

logger = get_logger("fusion")


class SensorFusionEngine:
    """Combina descriptores visuales de MediaPipe con lecturas de flexión e inercia."""

    def __init__(self, config=None):
        self.config = config
        logger.info("SensorFusionEngine inicializado.")

    def fuse(
        self,
        vision_data: Optional[Dict[str, Any]],
        sensor_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Produce un estado unificado del signo gestual.
        Permite validar posturas con oclusión mediante la resistencia física de flexión.
        """
        has_vision = vision_data is not None and vision_data.get("detected", False)
        has_sensors = sensor_data is not None

        features_63 = vision_data.get("feature_vector_63", []) if has_vision else []
        flex_vector = [
            sensor_data.get("flex_thumb", 0.0),
            sensor_data.get("flex_index", 0.0),
            sensor_data.get("flex_middle", 0.0),
            sensor_data.get("flex_ring", 0.0),
            sensor_data.get("flex_pinky", 0.0)
        ] if has_sensors else [0.0] * 5

        imu_data = {
            "roll": sensor_data.get("imu_roll_deg", 0.0) if has_sensors else 0.0,
            "pitch": sensor_data.get("imu_pitch_deg", 0.0) if has_sensors else 0.0,
            "yaw": sensor_data.get("imu_yaw_deg", 0.0) if has_sensors else 0.0
        }

        # Estado unificado
        return {
            "valid_fusion": has_vision or has_sensors,
            "vision_present": has_vision,
            "sensors_present": has_sensors,
            "features_63": features_63,
            "finger_flexion": flex_vector,
            "hand_orientation": imu_data,
            "contact_active": sensor_data.get("contact_sensor", False) if has_sensors else False
        }
