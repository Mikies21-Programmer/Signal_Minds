"""
Motor de fusión sensorial multimodal (Visión Artificial + Instrumentación Mecatrónica).
Aplica correlación temporal estricta con timestamps reales, detección de obsolescencia
y discriminación explícita entre visión única, sensor único y fusión multimodal válida.
Elimina la presunción errónea de 'has_vision OR has_sensors' como evidencia de fusión.
"""

import time
from typing import Optional, Dict, Any, List
from ..backend.logger import get_logger

logger = get_logger("fusion")


class SensorFusionEngine:
    """
    Motor de fusión temporal que valida sincronización y frescura entre
    landmarks visuales de MediaPipe y telemetría cinemática de sensores.
    """

    def __init__(self, config=None):
        self.config = config
        self.max_staleness_sec = 0.5  # Muestra con > 500 ms de antigüedad se considera obsoleta
        self.max_sync_delta_sec = 0.2  # Desfase temporal máximo tolerado: 200 ms

        if config:
            fus_conf = config.get("fusion", {}) if hasattr(config, "get") else {}
            self.max_staleness_sec = float(fus_conf.get("max_staleness_sec", self.max_staleness_sec))
            self.max_sync_delta_sec = float(fus_conf.get("max_sync_delta_sec", self.max_sync_delta_sec))

        logger.info(
            f"SensorFusionEngine inicializado (max_staleness={self.max_staleness_sec*1000}ms, "
            f"max_sync_delta={self.max_sync_delta_sec*1000}ms)."
        )

    def fuse(
        self,
        vision_data: Optional[Dict[str, Any]],
        sensor_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Produce un estado fusionado con verificación temporal estricta.
        Distigue rigurosamente entre:
        - FULL_MULTIMODAL: Fusión válida y sincrónica (visión y sensores activos).
        - VISION_ONLY: Solo visión (sensores desconectados o ausentes).
        - SENSORS_ONLY: Solo sensores (mano fuera de encuadre o cámara desconectada).
        - NO_DATA: Sin datos utilizables o datos obsoletos.
        """
        now = time.time()

        # 1. Extracción y validación de timestamps
        ts_vision = vision_data.get("timestamp") if (vision_data and isinstance(vision_data, dict)) else None
        ts_sensor = sensor_data.get("timestamp") if (sensor_data and isinstance(sensor_data, dict)) else None

        # Detección de timestamps inválidos (futuro improbable o <= 0)
        valid_ts_vision = (ts_vision is not None and 0 < ts_vision <= (now + 1.0))
        valid_ts_sensor = (ts_sensor is not None and 0 < ts_sensor <= (now + 1.0))

        # Detección de obsolescencia
        vision_stale = (not valid_ts_vision) or ((now - ts_vision) > self.max_staleness_sec)
        sensor_stale = (not valid_ts_sensor) or ((now - ts_sensor) > self.max_staleness_sec)

        # 2. Estado de conexión física de cada fuente
        camera_connected = vision_data is not None and vision_data.get("status") != "DISCONNECTED"
        sensor_connected = sensor_data is not None and bool(sensor_data.get("is_connected", False))

        # 3. Presencia de información útil
        vision_present = bool(
            valid_ts_vision and not vision_stale and vision_data.get("detected", False)
        )
        sensors_present = bool(
            valid_ts_sensor and not sensor_stale and sensor_connected
        )

        # 4. Cálculo de desincronización temporal (delta t)
        sync_delta_sec: Optional[float] = None
        is_synchronized = False
        if valid_ts_vision and valid_ts_sensor:
            sync_delta_sec = abs(ts_vision - ts_sensor)
            is_synchronized = sync_delta_sec <= self.max_sync_delta_sec

        # 5. Determinación de modo de fusión y validez
        # REGLA ESTRICTA: NO aceptar 'has_vision OR has_sensors' como evidencia suficiente de fusión
        valid_fusion = False
        if vision_present and sensors_present and is_synchronized:
            fusion_mode = "FULL_MULTIMODAL"
            valid_fusion = True
        elif vision_present and not sensors_present:
            fusion_mode = "VISION_ONLY"
            valid_fusion = False
        elif sensors_present and not vision_present:
            fusion_mode = "SENSORS_ONLY"
            valid_fusion = False
        else:
            fusion_mode = "NO_DATA"
            valid_fusion = False

        # 6. Extracción de vectores numéricos
        features_63: List[float] = (
            vision_data.get("feature_vector_63", []) if (vision_data and vision_present) else []
        )
        raw_landmarks = (
            vision_data.get("raw_landmarks", []) if (vision_data and vision_present) else []
        )

        flex_vector = [
            float(sensor_data.get("flex_thumb", 0.0)),
            float(sensor_data.get("flex_index", 0.0)),
            float(sensor_data.get("flex_middle", 0.0)),
            float(sensor_data.get("flex_ring", 0.0)),
            float(sensor_data.get("flex_pinky", 0.0))
        ] if (sensor_data and sensors_present) else [0.0] * 5

        imu_data = {
            "roll": float(sensor_data.get("imu_roll_deg", 0.0)),
            "pitch": float(sensor_data.get("imu_pitch_deg", 0.0)),
            "yaw": float(sensor_data.get("imu_yaw_deg", 0.0))
        } if (sensor_data and sensors_present) else {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}

        return {
            "valid_fusion": valid_fusion,
            "fusion_mode": fusion_mode,
            "vision_present": vision_present,
            "sensors_present": sensors_present,
            "camera_connected": camera_connected,
            "sensor_connected": sensor_connected,
            "timestamp_vision": ts_vision,
            "timestamp_sensor": ts_sensor,
            "sync_delta_ms": round(sync_delta_sec * 1000.0, 2) if sync_delta_sec is not None else None,
            "is_synchronized": is_synchronized,
            "staleness": {
                "vision_stale": vision_stale,
                "sensor_stale": sensor_stale
            },
            "features_63": features_63,
            "raw_landmarks": raw_landmarks,
            "finger_flexion": flex_vector,
            "hand_orientation": imu_data,
            "contact_active": bool(sensor_data.get("contact_sensor", False)) if (sensor_data and sensors_present) else False
        }
