"""
Pipeline de visión artificial para detección y normalización de 21 landmarks de mano.
Utiliza modelo local de MediaPipe (sin descargas en runtime) y procesamiento de fotogramas reales de OpenCV.
"""

import time
import math
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import cv2
import numpy as np

from ..backend.logger import get_logger

logger = get_logger("vision")


class VisionPipelineError(Exception):
    """Excepción para errores irrecuperables en el pipeline de visión."""
    pass


class VisionPipeline:
    """
    Procesador de visión artificial para extracción de 21 landmarks anatómicos
    mediante MediaPipe Tasks con modelo local (.task) offline.
    """

    def __init__(self, config=None):
        self.config = config
        self.mock_mode = False
        self.min_confidence = 0.6
        self.max_hands = 1
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.model_path = self.project_root / "models" / "hand_landmarker.task"

        # Métricas de rendimiento
        self._fps = 0.0
        self._frame_count = 0
        self._last_fps_calc_time = time.time()
        self._frames_since_calc = 0

        self.detector = None
        self._parse_config(config)

        if not self.mock_mode:
            self._init_real_mediapipe()
        else:
            logger.info("VisionPipeline inicializado en MOCK MODE (landmarks sintéticos solo para tests).")

    def _parse_config(self, config) -> None:
        if not config:
            return

        vis_conf = config.get("vision", {}) if hasattr(config, "get") else {}
        self.mock_mode = bool(vis_conf.get("mock_mode", False))
        self.min_confidence = float(vis_conf.get("min_detection_confidence", self.min_confidence))
        self.max_hands = int(vis_conf.get("max_num_hands", self.max_hands))

        custom_model = vis_conf.get("model_path")
        if custom_model:
            cand = Path(custom_model)
            self.model_path = cand if cand.is_absolute() else (self.project_root / custom_model)

    def _init_real_mediapipe(self) -> None:
        """Comprueba existencia del modelo local e inicializa MediaPipe sin internet."""
        # 1. Comprobar que el modelo existe
        if not self.model_path.exists():
            error_msg = (
                f"ERROR CLARO DE MODELO LOCAL: No se encontró el archivo de modelo MediaPipe en '{self.model_path}'. "
                "Por política de seguridad y operación offline de la demostración, no se permite la descarga "
                "automática desde Internet en tiempo de ejecución. Deposite 'hand_landmarker.task' en el directorio "
                "02_PROJECT/models/."
            )
            logger.error(error_msg)
            raise VisionPipelineError(error_msg)

        # 4. Registrar la ruta utilizada
        logger.info(f"Cargando modelo local de MediaPipe desde ruta verificada: {self.model_path.resolve()}")

        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            base_options = mp_python.BaseOptions(model_asset_path=str(self.model_path.resolve()))
            options = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=self.max_hands,
                min_hand_detection_confidence=self.min_confidence,
                min_hand_presence_confidence=self.min_confidence,
                min_tracking_confidence=self.min_confidence
            )
            self.detector = mp_vision.HandLandmarker.create_from_options(options)
            logger.info("Detector HandLandmarker de MediaPipe cargado exitosamente en modo offline.")
        except Exception as e:
            err_details = f"Falla al instanciar detector de MediaPipe: {e}"
            logger.error(err_details)
            raise VisionPipelineError(err_details)

    def _update_fps(self) -> None:
        self._frames_since_calc += 1
        now = time.time()
        elapsed = now - self._last_fps_calc_time
        if elapsed >= 1.0:
            self._fps = round(self._frames_since_calc / elapsed, 1)
            self._frames_since_calc = 0
            self._last_fps_calc_time = now

    def normalize_landmarks(self, raw_points: List[Dict[str, float]]) -> List[float]:
        """
        Aplica la normalización geométrica invariante a traslación y escala:
        Resta las coordenadas de la muñeca (P0) y divide entre la distancia P0 -> P9 (nudillo medio).
        Retorna vector plano de 63 componentes flotantes [x0, y0, z0, x1, y1, z1, ...].
        """
        if not raw_points or len(raw_points) < 21:
            return []

        p0 = raw_points[0]
        p9 = raw_points[9]

        ref_dist = math.sqrt(
            (p9["x"] - p0["x"]) ** 2 +
            (p9["y"] - p0["y"]) ** 2 +
            (p9["z"] - p0["z"]) ** 2
        )
        if ref_dist < 1e-6:
            ref_dist = 1.0

        normalized: List[float] = []
        for p in raw_points:
            normalized.append(round((p["x"] - p0["x"]) / ref_dist, 5))
            normalized.append(round((p["y"] - p0["y"]) / ref_dist, 5))
            normalized.append(round((p["z"] - p0["z"]) / ref_dist, 5))

        return normalized

    def process_frame(self, frame_input: Optional[Union[Dict[str, Any], np.ndarray]]) -> Optional[Dict[str, Any]]:
        """
        Procesa el fotograma de entrada mediante MediaPipe real o simulador de test.
        Acepta un diccionario generado por CameraConsumer o un ndarray directo de OpenCV.
        REAL MODE nunca fabrica landmarks si no hay una mano detectada.
        """
        if frame_input is None:
            return None

        # Extraer ndarray
        raw_bgr: Optional[np.ndarray] = None
        input_timestamp = time.time()

        if isinstance(frame_input, dict):
            raw_bgr = frame_input.get("frame")
            input_timestamp = frame_input.get("timestamp", input_timestamp)
        elif isinstance(frame_input, np.ndarray):
            raw_bgr = frame_input

        if raw_bgr is None or not isinstance(raw_bgr, np.ndarray):
            return None

        self._frame_count += 1
        self._update_fps()
        now = time.time()

        # MODO MOCK (Solo para tests sintéticos aislados)
        if self.mock_mode:
            simulated_raw = []
            for i in range(21):
                simulated_raw.append({
                    "id": i,
                    "x": 0.5 + 0.05 * math.sin(i),
                    "y": 0.6 - 0.02 * i,
                    "z": 0.01 * math.cos(i)
                })

            normalized_vector = self.normalize_landmarks(simulated_raw)
            return {
                "detected": True,
                "hand_count": 1,
                "raw_landmarks": simulated_raw,
                "feature_vector_63": normalized_vector,
                "confidence": 0.95,
                "timestamp": now,
                "fps": self._fps,
                "is_mock": True
            }

        # MODO REAL HARDWARE / MEDIAPIPE REAL
        if self.detector is None:
            raise VisionPipelineError("VisionPipeline no tiene detector instanciado en modo real.")

        import mediapipe as mp

        # Convertir BGR de OpenCV a RGB para MediaPipe
        rgb_frame = cv2.cvtColor(raw_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Ejecución sincrónica de inferencia local
        detection_result = self.detector.detect(mp_image)

        # Si NO se detectó ninguna mano, reportar detected=False sin inventar puntos
        if not detection_result.hand_landmarks or len(detection_result.hand_landmarks) == 0:
            return {
                "detected": False,
                "hand_count": 0,
                "raw_landmarks": [],
                "feature_vector_63": [],
                "confidence": 0.0,
                "timestamp": now,
                "fps": self._fps,
                "is_mock": False
            }

        # Extraer primera mano detectada
        first_hand = detection_result.hand_landmarks[0]
        raw_landmarks: List[Dict[str, float]] = []
        for idx, lm in enumerate(first_hand):
            raw_landmarks.append({
                "id": idx,
                "x": float(lm.x),
                "y": float(lm.y),
                "z": float(lm.z)
            })

        # Calcular vector canónico normalizado de 63 dimensiones
        vector_63 = self.normalize_landmarks(raw_landmarks)

        # Extraer confidence
        confidence = self.min_confidence
        if detection_result.handedness and len(detection_result.handedness) > 0:
            if len(detection_result.handedness[0]) > 0:
                confidence = round(float(detection_result.handedness[0][0].score), 3)

        return {
            "detected": True,
            "hand_count": len(detection_result.hand_landmarks),
            "raw_landmarks": raw_landmarks,
            "feature_vector_63": vector_63,
            "confidence": confidence,
            "timestamp": now,
            "fps": self._fps,
            "is_mock": False
        }
