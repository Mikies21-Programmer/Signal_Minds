"""
Controlador de interfaz para la Laptop (Estación de visualización desacoplada).
Gestiona el estado visual, recepción de telemetría y atajos de teclado.
"""

from typing import Dict, Any, Optional
from ..backend.logger import get_logger

logger = get_logger("frontend")


class FrontendController:
    """Controlador de la capa visual en Laptop desacoplada."""

    def __init__(self, config=None):
        self.config = config
        self.current_sign = "A"
        self.is_paused = False
        self.level_1_signs = ["A", "B", "C", "L", "Y"]

        if config:
            lsm_conf = config.get("lsm", {})
            self.current_sign = lsm_conf.get("default_target_sign", "A")
            self.level_1_signs = lsm_conf.get("level_1_signs", self.level_1_signs)

        logger.info(f"FrontendController inicializado en Laptop. Seña activa: {self.current_sign}")

    def handle_keyboard_input(self, key: str) -> Dict[str, Any]:
        """
        Procesa eventos de pulsación de tecla física en la laptop:
        - Teclas A, B, C, L, Y: Selección directa de seña Nivel 1.
        - Barra espaciadora (' '): Pausa/Reanuda evaluación.
        - Tecla 'R' o 'r': Recalibración.
        - Tecla 'Tab': Siguiente seña.
        """
        key_upper = key.strip().upper()

        if key_upper in self.level_1_signs:
            self.current_sign = key_upper
            logger.info(f"[Teclado Laptop] Seña seleccionada: '{self.current_sign}'")
            return {"action": "SET_SIGN", "sign": self.current_sign}

        if key == " " or key_upper == "SPACE":
            self.is_paused = not self.is_paused
            status = "PAUSADO" if self.is_paused else "EN EJECUCIÓN"
            logger.info(f"[Teclado Laptop] Estado cambiado a: {status}")
            return {"action": "TOGGLE_PAUSE", "is_paused": self.is_paused}

        if key_upper == "R":
            logger.info("[Teclado Laptop] Solicitud de recalibración recibida.")
            return {"action": "RECALIBRATE"}

        if key_upper == "TAB":
            current_idx = self.level_1_signs.index(self.current_sign) if self.current_sign in self.level_1_signs else -1
            next_idx = (current_idx + 1) % len(self.level_1_signs)
            self.current_sign = self.level_1_signs[next_idx]
            logger.info(f"[Teclado Laptop] Seña avanzada a: '{self.current_sign}'")
            return {"action": "SET_SIGN", "sign": self.current_sign}

        return {"action": "IGNORED", "key": key}

    def format_view_payload(self, telemetry_frame: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara el objeto de renderizado para la pantalla de la laptop."""
        return {
            "target_sign": self.current_sign,
            "is_paused": self.is_paused,
            "telemetry": telemetry_frame
        }
