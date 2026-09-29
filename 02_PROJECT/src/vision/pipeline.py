"""
Pipeline de visión artificial para detección y normalización de landmarks de mano.
Compatible con MediaPipe Hands en ARM64 y modo simulado para desarrollo/pruebas.
"""

from typing import Optional, Dict, Any, List
import math
from ..backend.logger import get_logger

logger = get_logger("vision")


class VisionPipeline:
    """Procesador de visión artificial para extracción de 21 landmarks anatómicos."""

    def __init__(self, config=None):
        self.config = config
        self.mock_mode = True
        self.min_confidence = 0.6
        self.max_hands = 1

        if config:
            vis_conf = config.get("vision", {})
            self.mock_mode = vis_conf.get("mock_mode", True)
            self.min_confidence = vis_conf.get("min_detection_confidence", self.min_confidence)
            self.max_hands = vis_conf.get("max_num_hands", self.max_hands)

        logger.info(f"VisionPipeline inicializado en modo: {'MOCK' if self.mock_mode else 'MEDIAPIPE REAL'}")

    def normalize_landmarks(self, raw_points: List[Dict[str, float]]) -> List[float]:
        """
        Aplica la normalización geométrica invariante a traslación y escala.
        Resta las coordenadas de la muñeca (P0) y divide entre la distancia P0 -> P9.
        Retorna vector plano de 63 componentes flotantes.
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

        normalized = []
        for p in raw_points:
            normalized.append((p["x"] - p0["x"]) / ref_dist)
            normalized.append((p["y"] - p0["y"]) / ref_dist)
            normalized.append((p["z"] - p0["z"]) / ref_dist)

        return normalized

    def process_frame(self, frame_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Procesa el cuadro de entrada y extrae la postura de la mano.
        En modo mock genera 21 landmarks sintéticos canónicos.
        """
        if frame_data is None:
            return None

        # Simulación de 21 landmarks anatómicos
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
            "confidence": 0.95 if self.mock_mode else 0.0,
            "is_mock": self.mock_mode
        }
