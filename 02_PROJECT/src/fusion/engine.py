"""
Motor de fusión sensorial multimodal (Visión Artificial + Telemetría de Ultrasonido).
Aplica correlación temporal con timestamps reales, detección de obsolescencia
y estimación de orientación visual integrada con medición de proximidad ultrasónica.
Elimina dependencias funcionales de acelerómetros, giróscopos e IMUs.
"""

import time
from typing import Optional, Dict, Any, List
from ..lsm.geometry import get_hand_orientation_visual
from ..backend.logger import get_logger

logger = get_logger("fusion")


class SensorFusionEngine:
    """
    Motor de fusión temporal que valida sincronización y frescura entre
    landmarks visuales de MediaPipe y sensor de distancia ultrasónico.
    """

    def __init__(self, config=None):
        self.config = config
        self.max_staleness_sec = 0.5  # Muestra con > 500 ms de antigüedad se considera obsoleta
        self.max_sync_delta_sec = 0.25  # Desfase temporal máximo tolerado: 250 ms
        self.orientation_invert = False

        if config:
            fus_conf = config.get("fusion", {}) if hasattr(config, "get") else (config.get("fusion", {}) if isinstance(config, dict) else {})
            self.max_staleness_sec = float(fus_conf.get("max_staleness_sec", self.max_staleness_sec))
            self.max_sync_delta_sec = float(fus_conf.get("max_sync_delta_sec", self.max_sync_delta_sec))
            cam_conf = config.get("camera", {}) if hasattr(config, "get") else (config.get("camera", {}) if isinstance(config, dict) else {})
            self.orientation_invert = bool(cam_conf.get("orientation_invert", False))

        logger.info(
            f"SensorFusionEngine inicializado (max_staleness={self.max_staleness_sec*1000}ms, "
            f"max_sync_delta={self.max_sync_delta_sec*1000}ms, orientation_invert={self.orientation_invert})."
        )

    def fuse(
        self,
        vision_data: Optional[Dict[str, Any]],
        sensor_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Produce un estado fusionado que combina visión y sensor ultrasónico.
        Devuelve como mínimo:
        hand_detected, handedness, orientation, orientation_confidence,
        distance_cm, distance_valid, sensor_connected, movement, diagnostics.
        """
        now = time.time()

        # 1. Extracción y validación de timestamps
        ts_vision = vision_data.get("timestamp") if (vision_data and isinstance(vision_data, dict)) else None
        ts_sensor = sensor_data.get("timestamp") if (sensor_data and isinstance(sensor_data, dict)) else None

        valid_ts_vision = (ts_vision is not None and 0 < ts_vision <= (now + 1.0))
        valid_ts_sensor = (ts_sensor is not None and 0 < ts_sensor <= (now + 1.0))

        vision_stale = (not valid_ts_vision) or ((now - ts_vision) > self.max_staleness_sec)
        sensor_stale = (not valid_ts_sensor) or ((now - ts_sensor) > self.max_staleness_sec)

        # 2. Conectividad y presencia de información
        camera_connected = vision_data is not None and vision_data.get("status") != "DISCONNECTED"
        sensor_connected = sensor_data is not None and bool(sensor_data.get("is_connected", False))

        vision_present = bool(
            valid_ts_vision and not vision_stale and vision_data.get("detected", False)
        )
        sensors_present = bool(
            valid_ts_sensor and not sensor_stale and sensor_connected
        )

        # 3. Sincronización temporal
        sync_delta_sec: Optional[float] = None
        is_synchronized = False
        if valid_ts_vision and valid_ts_sensor:
            sync_delta_sec = abs(ts_vision - ts_sensor)
            is_synchronized = sync_delta_sec <= self.max_sync_delta_sec

        # 4. Modo de fusión
        if vision_present and sensors_present and is_synchronized:
            fusion_mode = "FULL_MULTIMODAL"
            valid_fusion = True
        elif vision_present:
            fusion_mode = "VISION_ONLY"
            valid_fusion = True  # La visión sola permite evaluación válida de señas
        elif sensors_present:
            fusion_mode = "SENSORS_ONLY"
            valid_fusion = False
        else:
            fusion_mode = "NO_DATA"
            valid_fusion = False

        # 5. Landmarks visuales y orientación visual
        raw_landmarks = (
            vision_data.get("raw_landmarks", []) if (vision_data and vision_present) else []
        )
        handedness = vision_data.get("handedness", "Right") if vision_data else "Right"
        hand_detected = bool(vision_present and len(raw_landmarks) >= 21)

        vis_orient = get_hand_orientation_visual(
            raw_landmarks,
            handedness=handedness,
            orientation_invert=self.orientation_invert
        )

        orientation = vis_orient.get("orientation", "UNKNOWN")
        orientation_confidence = vis_orient.get("confidence", 0.0)

        # 6. Datos de distancia ultrasónica
        dist_cm = None
        dist_valid = False
        if sensor_data and sensors_present:
            dist_cm = sensor_data.get("distance_cm")
            dist_valid = bool(sensor_data.get("distance_valid", False))

        # 7. Diagnósticos de movimiento y telemetría
        movement = {
            "is_moving": False,
            "speed": 0.0,
            "status": "STABLE"
        }

        diagnostics = {
            "fusion_mode": fusion_mode,
            "is_synchronized": is_synchronized,
            "sync_delta_ms": round(sync_delta_sec * 1000.0, 2) if sync_delta_sec is not None else None,
            "visual_orientation": vis_orient,
            "ultrasonic": {
                "distance_cm": dist_cm,
                "is_valid": dist_valid,
                "diagnostic": f"{dist_cm:.1f} cm" if (dist_valid and dist_cm is not None) else "DISTANCIA NO DISPONIBLE"
            }
        }

        features_63 = (
            vision_data.get("feature_vector_63", []) if (vision_data and vision_present) else []
        )

        return {
            "hand_detected": hand_detected,
            "handedness": handedness,
            "orientation": orientation,
            "orientation_confidence": orientation_confidence,
            "distance_cm": dist_cm,
            "distance_valid": dist_valid,
            "sensor_connected": sensor_connected,
            "movement": movement,
            "diagnostics": diagnostics,
            "valid_fusion": valid_fusion,
            "fusion_mode": fusion_mode,
            "vision_present": vision_present,
            "sensors_present": sensors_present,
            "camera_connected": camera_connected,
            "timestamp_vision": ts_vision,
            "timestamp_sensor": ts_sensor,
            "raw_landmarks": raw_landmarks,
            "features_63": features_63,
            "sensor_telemetry": sensor_data or {}
        }
