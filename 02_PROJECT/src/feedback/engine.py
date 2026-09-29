"""
Motor de retroalimentación pedagógica en tiempo real.
Transforma el diagnóstico de los 4 parámetros en instrucciones correctivas directas.
"""

from typing import Dict, Any
from ..backend.logger import get_logger

logger = get_logger("feedback")


class FeedbackEngine:
    """Generador de instrucciones explicables y correctivas para el usuario."""

    def __init__(self, config=None):
        self.config = config
        logger.info("FeedbackEngine inicializado.")

    def generate_feedback(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza los parámetros evaluados y produce retroalimentación clara.
        """
        is_valid = evaluation.get("is_valid", False)
        sign = evaluation.get("sign", "")
        params = evaluation.get("parameters", {})

        if is_valid:
            return {
                "status": "SUCCESS",
                "color": "#00FF66",
                "primary_message": f"¡Excelente! Seña '{sign}' ejecutada correctamente.",
                "secondary_message": "Mantén la postura estable.",
                "correction_hint": ""
            }

        # Analizar cuál parámetro falló para dar retroalimentación pedagógica
        config_stat = params.get("configuration", {}).get("status", "")
        orient_stat = params.get("orientation", {}).get("status", "")
        mov_stat = params.get("movement", {}).get("status", "")

        if config_stat == "CORRECT":
            hint = f"Ajusta la curvatura y separación de los dedos para la seña '{sign}'."
            primary = "Postura de mano incorrecta."
        elif orient_stat == "CORRECT":
            hint = "Gira la muñeca para orientar la palma directamente hacia la cámara."
            primary = "Orientación de la palma incorrecta."
        elif mov_stat == "CORRECT":
            hint = "El movimiento debe ser fluido y con la trayectoria esperada."
            primary = "Dinámica del signo incorrecta."
        else:
            hint = "Coloca tu mano claramente frente a la cámara dentro del encuadre."
            primary = "Ajusta la posición de tu mano."

        return {
            "status": "NEEDS_CORRECTION",
            "color": "#FFA500",
            "primary_message": primary,
            "secondary_message": hint,
            "correction_hint": hint
        }
