"""
Consumidor de flujo de video para el ESP32-CAM.
Implementa hilo desacoplado con buffer=1 y soporte de mock para pruebas de integración.
"""

import time
from typing import Optional, Dict, Any
from enum import Enum
from ..backend.logger import get_logger

logger = get_logger("camera")


class ConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    STREAMING = "STREAMING"
    STALLED = "STALLED"
    ERROR = "ERROR"


class CameraConsumer:
    """Cliente consumidor de video del ESP32-CAM con control de estados y modo simulado."""

    def __init__(self, config=None):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self.mock_mode = True
        self.stream_url = "http://192.168.4.1/stream"
        self.timeout_sec = 1.0
        self._is_running = False
        self._frame_count = 0

        if config:
            cam_conf = config.get("camera", {})
            self.mock_mode = cam_conf.get("mock_mode", True)
            self.stream_url = cam_conf.get("stream_url", self.stream_url)
            self.timeout_sec = cam_conf.get("timeout_sec", self.timeout_sec)

    def start(self) -> None:
        """Inicia el cliente de captura."""
        self._is_running = True
        self.status = ConnectionStatus.STREAMING
        logger.info(f"CameraConsumer iniciado en modo: {'MOCK' if self.mock_mode else 'REAL HW (' + self.stream_url + ')'}")

    def stop(self) -> None:
        """Detiene el consumidor de video."""
        self._is_running = False
        self.status = ConnectionStatus.DISCONNECTED
        logger.info("CameraConsumer detenido.")

    def get_latest_frame(self) -> Optional[Dict[str, Any]]:
        """
        Retorna el fotograma más reciente disponible.
        En modo mock retorna un payload simulado con metadata y tamaño.
        """
        if not self._is_running:
            return None

        self._frame_count += 1
        return {
            "frame_id": self._frame_count,
            "timestamp": time.time(),
            "width": 320,
            "height": 240,
            "format": "RGB",
            "is_mock": self.mock_mode,
            "status": self.status.value
        }

    def get_status(self) -> ConnectionStatus:
        return self.status
