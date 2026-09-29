"""
Evaluador lingüístico de Lengua de Señas Mexicana (LSM).
Evalúa los 4 parámetros constitutivos: Configuración, Orientación, Movimiento y Ubicación.
Prioridad Nivel 1: Señas estáticas (A, B, C, L, Y).
"""

from typing import Dict, Any, Optional
from ..backend.logger import get_logger

logger = get_logger("lsm")


class LSMEvaluator:
    """Evaluador de corrección morfológica y lingüística en LSM."""

    def __init__(self, config=None):
        self.config = config
        self.active_level = 1
        self.target_sign = "A"
        self.threshold = 0.80

        if config:
            lsm_conf = config.get("lsm", {})
            self.active_level = lsm_conf.get("active_level", 1)
            self.target_sign = lsm_conf.get("default_target_sign", "A")
            self.threshold = lsm_conf.get("confidence_threshold", 0.80)

        logger.info(f"LSMEvaluator inicializado. Nivel activo: {self.active_level}, Seña inicial: '{self.target_sign}'")

    def set_target_sign(self, sign: str) -> None:
        self.target_sign = sign.upper()

    def evaluate(self, fused_state: Dict[str, Any], target_sign: Optional[str] = None) -> Dict[str, Any]:
        """
        Evalúa el estado fusionado contra la seña objetivo.
        Retorna veredicto general y desglose por los 4 parámetros lingüísticos.
        """
        sign = (target_sign or self.target_sign).upper()

        if not fused_state.get("valid_fusion", False):
            return {
                "sign": sign,
                "is_valid": False,
                "overall_score": 0.0,
                "message": "Sin datos de visión ni de sensores disponibles",
                "parameters": {
                    "configuration": {"score": 0.0, "status": "FAIL", "reason": "No data"},
                    "orientation": {"score": 0.0, "status": "FAIL", "reason": "No data"},
                    "movement": {"score": 0.0, "status": "FAIL", "reason": "No data"},
                    "location": {"score": 0.0, "status": "FAIL", "reason": "No data"}
                }
            }

        # Evaluación estructural para Nivel 1 (A, B, C, L, Y)
        # Nota: En esta fase de esqueleto se verifica consistencia de descriptores
        # sin cargar modelos pesados (regla de no entrenar modelos todavía).
        config_score = 0.92 if fused_state.get("vision_present") else 0.50
        orientation_score = 0.88 if abs(fused_state.get("hand_orientation", {}).get("roll", 0)) < 25.0 else 0.40
        movement_score = 1.0  # Señas Nivel 1 son estáticas por definición
        location_score = 0.90

        overall = (config_score * 0.4) + (orientation_score * 0.3) + (movement_score * 0.2) + (location_score * 0.1)
        is_valid = overall >= self.threshold

        return {
            "sign": sign,
            "level": self.active_level,
            "is_valid": is_valid,
            "overall_score": round(overall, 3),
            "threshold": self.threshold,
            "parameters": {
                "configuration": {
                    "score": round(config_score, 3),
                    "status": "PASS" if config_score >= 0.80 else "CORRECT",
                    "param_name": "Queirema (Forma de dedos)"
                },
                "orientation": {
                    "score": round(orientation_score, 3),
                    "status": "PASS" if orientation_score >= 0.80 else "CORRECT",
                    "param_name": "Orientación de palma"
                },
                "movement": {
                    "score": round(movement_score, 3),
                    "status": "PASS",
                    "param_name": "Kinema (Dinámica)"
                },
                "location": {
                    "score": round(location_score, 3),
                    "status": "PASS",
                    "param_name": "Toponema (Ubicación espacial)"
                }
            }
        }
