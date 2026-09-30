"""
Motor de retroalimentación pedagógica en tiempo real para LSM.
Genera instrucciones correctivas específicas y anatómicas basadas en los parámetros
constitutivos (queirema, orientación, kinema, toponema).
Prohíbe terminantemente el uso de mensajes genéricos como 'Inténtalo nuevamente'.
"""

from typing import Dict, Any
from ..backend.logger import get_logger

logger = get_logger("feedback")


class FeedbackEngine:
    """Generador de directivas pedagógicas explicables para el usuario."""

    SIGN_DESCRIPTIONS: Dict[str, str] = {
        "A": "Configuración de mano compatible con A (puño con pulgar al costado).",
        "B": "Cuatro dedos extendidos y pulgar en palma.",
        "C": "Curva los dedos formando un arco.",
        "L": "Índice y pulgar forman la L.",
        "Y": "Pulgar y meñique extendidos.",
        "J": "Meñique extendido trazando una curva.",
        "Ñ": "Mano en N con movimiento ondulante.",
        "Q": "Índice y pulgar hacia abajo con giro de muñeca.",
        "X": "Índice en gancho con movimiento hacia atrás.",
        "Z": "Índice extendido trazando una Z en el aire."
    }

    def __init__(self, config=None):
        self.config = config
        logger.info("FeedbackEngine inicializado con retroalimentación específica.")

    def generate_feedback(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza detalladamente los 4 parámetros constitutivos y genera
        instrucciones concretas de corrección anatómica y espacial.
        """
        is_valid = evaluation.get("is_valid", False)
        sign = evaluation.get("sign", "")
        params = evaluation.get("parameters", {})
        score = evaluation.get("overall_score", 0.0)

        # 1. Éxito: Seña ejecutada correctamente
        if is_valid:
            desc = self.SIGN_DESCRIPTIONS.get(sign, "Postura anatómica validada correctamente.")
            return {
                "status": "SUCCESS",
                "color": "#00FF88",
                "primary_message": f"¡Excelente! Seña '{sign}' reconocida",
                "secondary_message": desc,
                "correction_hint": "",
                "score": score
            }

        # 2. Si no hay mano detectada
        if score == 0.0 and ("Sin mano" in evaluation.get("message", "") or not params.get("configuration", {}).get("reason")):
            return {
                "status": "NO_HAND",
                "color": "#FFAA00",
                "primary_message": "No se detecta mano en el encuadre.",
                "secondary_message": "Coloca tu mano frente al lente del ESP32-CAM.",
                "correction_hint": "Acerca la mano al área de ejecución visual.",
                "score": 0.0
            }

        config_info = params.get("configuration", {})
        orient_info = params.get("orientation", {})
        loc_info = params.get("location", {})
        mov_info = params.get("movement", {})

        # 3. Prioridad 1 de corrección: Toponema (Ubicación espacial fuera de encuadre)
        if loc_info.get("status") == "CORRECT":
            return {
                "status": "NEEDS_CORRECTION",
                "color": "#FFAA00",
                "primary_message": "Mano fuera del área de ejecución.",
                "secondary_message": loc_info.get("reason", "Centra la mano en el encuadre visual."),
                "correction_hint": "Acerca la mano a la zona central frente a la cámara.",
                "score": score
            }

        # 4. Prioridad 2 de corrección: Queirema (Configuración morfológica de los dedos)
        if config_info.get("status") == "CORRECT" or config_info.get("score", 0.0) < 0.75:
            reason = config_info.get("reason", f"Ajusta los dedos para la seña '{sign}'.")
            return {
                "status": "NEEDS_CORRECTION",
                "color": "#FF8800",
                "primary_message": f"Configuración de dedos incorrecta para '{sign}'.",
                "secondary_message": reason,
                "correction_hint": reason,
                "score": score
            }

        # 5. Prioridad 3 de corrección: Orientación de palma (IMU MPU6050)
        orient_state = orient_info.get("orientation_state", "")
        if orient_state == "ORIENTATION_UNAVAILABLE" or orient_info.get("status") == "UNAVAILABLE":
            return {
                "status": "NEEDS_CORRECTION",
                "color": "#94A3B8",
                "primary_message": "Orientación no disponible (ORIENTATION_UNAVAILABLE).",
                "secondary_message": "Verifica la conexión del sensor MPU6050 en el dorso de la mano.",
                "correction_hint": "Conecta y verifica el sensor MPU6050 para validar la seña.",
                "score": score
            }

        if orient_info.get("status") in ["CORRECT", "FAIL"] or orient_info.get("score", 0.0) < 0.75 or orient_state in ["ORIENTATION_FAIL", "ORIENTATION_ADJUST", "IMU_TILT_FAIL", "IMU_TILT_ADJUST"]:
            reason = orient_info.get("reason", "Ajusta la orientación de la mano.")
            primary = "Inclinación de la mano incorrecta." if "FAIL" in orient_state else "Ajusta la orientación de la mano."
            if orient_state == "IMU_TILT_FAIL":
                primary = "Inclinación de mano excesiva para C."
            elif orient_state == "IMU_TILT_ADJUST":
                primary = "Ajusta ligeramente la inclinación para C."

            return {
                "status": "NEEDS_CORRECTION",
                "color": "#EF4444" if "FAIL" in orient_state else "#FF8800",
                "primary_message": primary,
                "secondary_message": reason,
                "correction_hint": reason,
                "score": score
            }

        # 6. Prioridad 4 de corrección: Dinámica / Kinema
        if mov_info.get("status") in ["CORRECT", "FAIL", "PREPARING"]:
            if sign in ["J", "Ñ", "Q", "X", "Z"]:
                reason = mov_info.get("reason") or evaluation.get("message", "Realiza el movimiento de la seña.")
                return {
                    "status": "NEEDS_CORRECTION",
                    "color": "#FFAA00",
                    "primary_message": reason,
                    "secondary_message": reason,
                    "correction_hint": reason,
                    "score": score
                }
            return {
                "status": "NEEDS_CORRECTION",
                "color": "#FFAA00",
                "primary_message": "Inestabilidad en el gesto.",
                "secondary_message": "Mantén la mano estática para completar la evaluación de esta seña.",
                "correction_hint": "No muevas los dedos durante la fijación.",
                "score": score
            }

        # Fallback descriptivo si ninguno de los anteriores se activó
        msg = evaluation.get("message") or f"Ajusta la postura de tu mano para la seña '{sign}'."
        return {
            "status": "NEEDS_CORRECTION",
            "color": "#FFAA00",
            "primary_message": msg,
            "secondary_message": "Verifica la separación de los dedos y la orientación hacia la cámara.",
            "correction_hint": msg,
            "score": score
        }
