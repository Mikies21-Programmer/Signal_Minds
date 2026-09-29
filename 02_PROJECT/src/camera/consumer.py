"""
Consumidor de flujo de video para el ESP32-CAM y cámaras locales.
Implementa hilo desacoplado con buffer=1, timeout configurable, reconexión automática,
cálculo de FPS, detección de pérdida de fotogramas y retorno de ndarray real de OpenCV.
"""

import time
import threading
from typing import Optional, Dict, Any, Union
from enum import Enum
import cv2
import numpy as np

from ..backend.logger import get_logger

logger = get_logger("camera")


class ConnectionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    STREAMING = "STREAMING"
    STALLED = "STALLED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class CameraConsumer:
    """
    Cliente consumidor de video para ESP32-CAM con buffer de 1 frame desacoplado,
    control de ciclo de vida, detección de pérdidas y soporte de ndarray real.
    """

    def __init__(self, config=None):
        self.config = config
        self.status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self.mock_mode: bool = False
        self.stream_url: Union[str, int] = "http://192.168.4.1/stream"
        self.timeout_sec: float = 2.0
        self.target_fps: int = 20
        self.resolution = (320, 240)

        # Estados de control y concurrencia
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Telemetría y métricas
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_timestamp: float = 0.0
        self._frame_count: int = 0
        self._dropped_frames: int = 0
        self._fps: float = 0.0
        self._last_fps_calc_time: float = time.time()
        self._frames_since_calc: int = 0

        self._parse_config(config)

    def _parse_config(self, config) -> None:
        if not config:
            return

        cam_conf = config.get("camera", {}) if hasattr(config, "get") else {}
        self.mock_mode = bool(cam_conf.get("mock_mode", False))
        raw_url = cam_conf.get("stream_url", self.stream_url)
        # Permitir índice entero si se configura "0" o un entero para cámara local
        if isinstance(raw_url, str) and raw_url.isdigit():
            self.stream_url = int(raw_url)
        else:
            self.stream_url = raw_url

        self.timeout_sec = float(cam_conf.get("timeout_sec", self.timeout_sec))
        self.target_fps = int(cam_conf.get("target_fps", self.target_fps))
        res = cam_conf.get("resolution", self.resolution)
        if isinstance(res, (list, tuple)) and len(res) == 2:
            self.resolution = (int(res[0]), int(res[1]))

    def start(self) -> None:
        """Inicia el cliente de captura en un hilo desacoplado."""
        if self._is_running:
            logger.warning("CameraConsumer ya se encuentra en ejecución.")
            return

        self._is_running = True
        self._stop_event.clear()

        if self.mock_mode:
            self.status = ConnectionStatus.STREAMING
            self._thread = threading.Thread(target=self._mock_capture_loop, daemon=True, name="CameraMockThread")
            logger.info("CameraConsumer iniciado en MOCK MODE (simulado para tests).")
        else:
            self.status = ConnectionStatus.CONNECTING
            self._thread = threading.Thread(target=self._real_capture_loop, daemon=True, name="CameraHwThread")
            logger.info(f"CameraConsumer iniciado en REAL HARDWARE MODE hacia stream: {self.stream_url}")

        self._thread.start()

    def stop(self) -> None:
        """Detiene el consumidor de video y libera recursos de forma segura."""
        if not self._is_running:
            return

        logger.info("Deteniendo CameraConsumer...")
        self._is_running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        with self._lock:
            self._latest_frame = None
            self.status = ConnectionStatus.DISCONNECTED

        logger.info("CameraConsumer detenido y recursos liberados.")

    def _update_fps(self) -> None:
        """Calcula FPS en ventana móvil de 1 segundo."""
        self._frames_since_calc += 1
        now = time.time()
        elapsed = now - self._last_fps_calc_time
        if elapsed >= 1.0:
            self._fps = round(self._frames_since_calc / elapsed, 1)
            self._frames_since_calc = 0
            self._last_fps_calc_time = now

    def _real_capture_loop(self) -> None:
        """Bucle de captura real desacoplado con OpenCV, buffer=1 y reconexión continua."""
        cap: Optional[cv2.VideoCapture] = None

        while not self._stop_event.is_set():
            if cap is None or not cap.isOpened():
                with self._lock:
                    self.status = ConnectionStatus.CONNECTING if self.status != ConnectionStatus.RECONNECTING else ConnectionStatus.RECONNECTING
                logger.info(f"Intentando conectar a stream de video: {self.stream_url}")

                try:
                    cap = cv2.VideoCapture(self.stream_url)
                    # Forzar buffer a 1 fotograma para no acumular latencia
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if hasattr(cv2, "CAP_PROP_FOURCC"):
                        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                except Exception as e:
                    logger.error(f"Error al inicializar VideoCapture para {self.stream_url}: {e}")
                    with self._lock:
                        self.status = ConnectionStatus.ERROR
                    time.sleep(min(self.timeout_sec, 2.0))
                    continue

                # Verificar si abrió correctamente
                if not cap.isOpened():
                    logger.warning(f"No fue posible abrir el stream {self.stream_url}. Reintentando en {self.timeout_sec}s...")
                    with self._lock:
                        self.status = ConnectionStatus.RECONNECTING
                    cap.release()
                    cap = None
                    self._stop_event.wait(timeout=self.timeout_sec)
                    continue

                logger.info(f"Conexión establecida con éxito con la cámara: {self.stream_url}")
                with self._lock:
                    self.status = ConnectionStatus.STREAMING

            # Leer fotograma
            try:
                ret, frame = cap.read()
            except Exception as e:
                logger.error(f"Excepción al leer fotograma del stream: {e}")
                ret = False
                frame = None

            now = time.time()

            if not ret or frame is None:
                # Comprobar si excedió timeout
                with self._lock:
                    time_since_last = now - self._latest_timestamp if self._latest_timestamp > 0 else self.timeout_sec + 1.0
                    if time_since_last > self.timeout_sec:
                        self.status = ConnectionStatus.STALLED
                        self._dropped_frames += 1
                        logger.warning(f"Stream STALLED: Sin fotogramas válidos en {time_since_last:.1f}s.")

                # Liberar para forzar reconexión limpia
                if cap is not None:
                    cap.release()
                    cap = None

                with self._lock:
                    self.status = ConnectionStatus.RECONNECTING
                self._stop_event.wait(timeout=min(self.timeout_sec, 1.5))
                continue

            # Fotograma válido recibido
            with self._lock:
                self.status = ConnectionStatus.STREAMING
                self._frame_count += 1
                self._latest_frame = frame
                self._latest_timestamp = now
                self._update_fps()

            # Evitar consumir 100% de CPU si el stream no tiene rate limiting propio
            if self.target_fps > 0:
                target_period = 1.0 / self.target_fps
                time.sleep(max(0.001, target_period * 0.1))

        # Al salir del bucle
        if cap is not None:
            cap.release()

    def _mock_capture_loop(self) -> None:
        """Bucle de fotogramas simulados con ndarray real para tests unitarios."""
        delay = 1.0 / max(1, self.target_fps)
        w, h = self.resolution

        while not self._stop_event.is_set():
            now = time.time()
            # Generar ndarray de prueba con OpenCV (fondo oscuro con patrón distintivo)
            mock_img = np.zeros((h, w, 3), dtype=np.uint8)
            cv2.putText(
                mock_img,
                f"MOCK FRAME {self._frame_count}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                1
            )

            with self._lock:
                self._frame_count += 1
                self._latest_frame = mock_img
                self._latest_timestamp = now
                self.status = ConnectionStatus.STREAMING
                self._update_fps()

            time.sleep(delay)

    def get_latest_frame(self) -> Optional[Dict[str, Any]]:
        """
        Retorna el fotograma más reciente disponible y su metadata.
        Retorna None si la cámara está detenida o no hay fotogramas listos.
        """
        if not self._is_running:
            return None

        with self._lock:
            if self._latest_frame is None:
                return None

            frame_copy = self._latest_frame.copy()
            h, w = frame_copy.shape[:2]
            return {
                "frame": frame_copy,
                "frame_id": self._frame_count,
                "timestamp": self._latest_timestamp,
                "width": w,
                "height": h,
                "format": "BGR",
                "fps": self._fps,
                "dropped_frames": self._dropped_frames,
                "status": self.status.value,
                "is_mock": self.mock_mode
            }

    def get_status(self) -> ConnectionStatus:
        """Retorna el estado de conexión actual."""
        with self._lock:
            return self.status
