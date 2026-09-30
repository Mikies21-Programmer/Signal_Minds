"""
Orquestador central del sistema INDIVISA INGENIUM 2026.
Coordina el ciclo de vida del backend, la ingesta multihilo, la fusión temporal,
la anotación visual en tiempo real y la evaluación morfológica de LSM.
"""

import time
import threading
from typing import Dict, Any, Optional
import cv2
import numpy as np

from .config_loader import ConfigLoader
from .logger import get_logger
from .health import HealthChecker

logger = get_logger("orchestrator")

# Conexiones canónicas de los 21 landmarks de MediaPipe Hands
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Pulgar
    (0, 5), (5, 6), (6, 7), (7, 8),        # Índice
    (5, 9), (9, 10), (10, 11), (11, 12),   # Medio
    (9, 13), (13, 14), (14, 15), (15, 16), # Anular
    (13, 17), (17, 18), (18, 19), (19, 20),# Meñique
    (0, 17)                                # Base palma
]


class SystemOrchestrator:
    """Orquestador central del pipeline de procesamiento y evaluación LSM."""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config or ConfigLoader()
        self.health_checker = HealthChecker(self.config)
        self.is_running = False
        self.is_paused = False
        self.frame_count = 0
        self.target_sign = "A"

        lsm_conf = self.config.get("lsm", {}) if hasattr(self.config, "get") else {}
        self.target_sign = lsm_conf.get("default_target_sign", "A")

        self.latest_payload: Dict[str, Any] = {}
        self.latest_jpeg_frame: Optional[bytes] = None
        self._lock = threading.Lock()
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Modo de operación: AUTO (clasificación continua) o MANUAL (selección fija)
        self.mode = "AUTO"

        # Lazy loading de módulos del pipeline
        self._init_subsystems()

    def _init_subsystems(self):
        """Inicializa las instancias de cada módulo de la arquitectura."""
        from ..camera.consumer import CameraConsumer
        from ..vision.pipeline import VisionPipeline
        from ..sensors.manager import SensorManager
        from ..fusion.engine import SensorFusionEngine
        from ..lsm.evaluator import LSMEvaluator
        from ..lsm.classifier import AutomaticLSMClassifier
        from ..feedback.engine import FeedbackEngine

        self.camera = CameraConsumer(self.config)
        self.vision = VisionPipeline(self.config)
        self.sensors = SensorManager(self.config)
        self.fusion = SensorFusionEngine(self.config)
        self.lsm = LSMEvaluator(self.config)
        self.classifier = AutomaticLSMClassifier(evaluator=self.lsm, config=self.config)
        self.feedback = FeedbackEngine(self.config)

        self.lsm.set_target_sign(self.target_sign)
        logger.info("Todos los subsistemas inicializados correctamente.")

    def start(self, auto_loop: bool = False) -> None:
        """Inicia los servicios del orquestador y opcionalmente el hilo continuo de ejecución."""
        if self.is_running:
            return

        logger.info(f"Iniciando orquestador del sistema (auto_loop={auto_loop})...")
        self.camera.start()
        self.sensors.start()
        self.is_running = True
        self._stop_event.clear()

        if auto_loop:
            self._loop_thread = threading.Thread(target=self._run_loop, daemon=True, name="OrchestratorLoop")
            self._loop_thread.start()
            logger.info("Hilo continuo de orquestador iniciado.")

        logger.info("Orquestador en ejecución activa.")

    def stop(self) -> None:
        """Detiene de forma ordenada todos los hilos y servicios."""
        if not self.is_running:
            return

        logger.info("Deteniendo orquestador...")
        self.is_running = False
        self._stop_event.set()

        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2.0)

        self.camera.stop()
        self.sensors.stop()
        logger.info("Orquestador detenido exitosamente.")

    def set_mode(self, mode: str) -> None:
        """Alterna entre modo 'AUTO' (reconocimiento automático continuo) y 'MANUAL' (selección fija)."""
        clean_mode = mode.strip().upper()
        if clean_mode in ["AUTO", "MANUAL"]:
            self.mode = clean_mode
            with self._lock:
                if self.latest_payload:
                    self.latest_payload["mode"] = self.mode
            logger.info(f"Modo de orquestador cambiado a: {self.mode}")

    def set_target_sign(self, sign: str, switch_to_manual: bool = True) -> None:
        """Actualiza la seña objetivo que se está evaluando."""
        self.target_sign = sign.upper()
        if switch_to_manual:
            self.mode = "MANUAL"
        self.lsm.set_target_sign(self.target_sign)
        with self._lock:
            if self.latest_payload:
                self.latest_payload["target_sign"] = self.target_sign
                self.latest_payload["mode"] = self.mode
        logger.info(f"Seña objetivo actualizada a: {self.target_sign} (modo={self.mode})")

    def toggle_pause(self) -> bool:
        """Alterna el estado de pausa de evaluación."""
        self.is_paused = not self.is_paused
        logger.info(f"Estado de pausa cambiado a: {self.is_paused}")
        return self.is_paused

    def recalibrate_sensors(self) -> Dict[str, Any]:
        """Dispara rutina de tara/cero en instrumentación."""
        logger.info("Disparando calibración desde orquestador...")
        return self.sensors.calibrate()

    def _draw_hud_and_landmarks(
        self,
        frame: np.ndarray,
        landmarks_data: Optional[Dict[str, Any]],
        eval_result: Dict[str, Any],
        feedback_msg: Dict[str, Any],
        fps: float,
        classification: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """Dibuja el esqueleto de 21 puntos y el HUD visual en el frame BGR."""
        h, w = frame.shape[:2]
        annotated = frame.copy()

        # 1. Dibujar landmarks si están presentes
        if landmarks_data and landmarks_data.get("detected", False):
            raw_pts = landmarks_data.get("raw_landmarks", [])
            # Mapear coordenadas normalizadas a píxeles
            coords = []
            for p in raw_pts:
                px = int(p["x"] * w) if 0.0 <= p["x"] <= 1.0 else int(p["x"])
                py = int(p["y"] * h) if 0.0 <= p["y"] <= 1.0 else int(p["y"])
                coords.append((px, py))

            # Dibujar conexiones
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx < len(coords) and end_idx < len(coords):
                    cv2.line(annotated, coords[start_idx], coords[end_idx], (0, 220, 255), 2)

            # Dibujar puntos articulares
            is_valid = eval_result.get("is_valid", False)
            node_color = (0, 255, 100) if is_valid else (0, 140, 255)
            for idx, pt in enumerate(coords):
                cv2.circle(annotated, pt, 4, node_color, -1)
                cv2.circle(annotated, pt, 5, (255, 255, 255), 1)

        cv2.rectangle(annotated, (0, 0), (w, 30), (15, 20, 25), -1)

        auto_sign = classification.get("stable_sign") if classification else None
        auto_status = classification.get("status", "NO_HAND") if classification else "NO_HAND"
        if self.mode == "AUTO":
            sign_text = f"AUTO: {auto_sign}" if auto_sign else f"[{auto_status}]"
        else:
            sign_text = f"MANUAL: {self.target_sign}"

        status_color = (0, 255, 100) if (classification and classification.get("status") == "RECOGNIZED") or eval_result.get("is_valid", False) else (50, 160, 255)
        score_val = classification.get("score", eval_result.get("overall_score", 0.0)) if classification else eval_result.get("overall_score", 0.0)

        cv2.putText(annotated, sign_text, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
        cv2.putText(annotated, f"CONF: {int(score_val*100)}%", (170, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1)
        cv2.putText(annotated, f"{fps:.0f}FPS", (w - 55, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 255), 1)

        # Si está pausado
        if self.is_paused:
            cv2.rectangle(annotated, (w // 2 - 80, h // 2 - 20), (w // 2 + 80, h // 2 + 20), (0, 0, 0), -1)
            cv2.putText(annotated, "PAUSADO", (w // 2 - 60, h // 2 + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        return annotated

    def _run_loop(self) -> None:
        """Hilo continuo que procesa a la frecuencia objetivo."""
        while not self._stop_event.is_set():
            if not self.is_paused:
                try:
                    self.step()
                except Exception as e:
                    logger.error(f"Error en ciclo del orquestador: {e}")
            time.sleep(0.03)  # ~30 Hz máximo de muestreo

    def step(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo individual del pipeline (1 frame completo).
        Retorna el payload de telemetría y evaluación resultante.
        """
        self.frame_count += 1
        t_start = time.perf_counter()

        # 1. Ingesta de cuadro visual
        frame_data = self.camera.get_latest_frame()

        # 2. Ingesta de telemetría mecatrónica
        sensor_data = self.sensors.poll_sensors()

        # 3. Extracción de landmarks visuales
        landmarks_data = self.vision.process_frame(frame_data)

        # 4. Fusión sensorial (Visión + Sensores físicos)
        fused_state = self.fusion.fuse(landmarks_data, sensor_data)

        # 5. Clasificación automática LSM Nivel 1 (A, B, C, L, Y)
        classification = self.classifier.classify(fused_state)

        # Si estamos en modo AUTO y hay una seña estable reconocida, actualizar seña activa
        if self.mode == "AUTO":
            if classification.get("status") == "RECOGNIZED" and classification.get("stable_sign"):
                self.target_sign = classification["stable_sign"]
                self.lsm.set_target_sign(self.target_sign)

        # 6. Evaluación morfológica explicable de la seña activa
        eval_result = self.lsm.evaluate(fused_state, target_sign=self.target_sign)

        # 7. Generación de feedback pedagógico específico
        feedback_msg = self.feedback.generate_feedback(eval_result)

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        # Anotación y compresión JPEG para stream HTTP
        cam_fps = frame_data.get("fps", 0.0) if frame_data else 0.0
        if frame_data and "frame" in frame_data and isinstance(frame_data["frame"], np.ndarray):
            annotated_frame = self._draw_hud_and_landmarks(
                frame_data["frame"],
                landmarks_data,
                eval_result,
                feedback_msg,
                fps=cam_fps,
                classification=classification
            )
            success, enc = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if success:
                self.latest_jpeg_frame = enc.tobytes()
        else:
            # Si no hay frame de cámara, generar imagen de standby informativa
            standby = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(standby, "ESPERANDO CAMARA...", (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
            cv2.putText(standby, f"Estado: {self.camera.get_status().value}", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            success, enc = cv2.imencode(".jpg", standby)
            if success:
                self.latest_jpeg_frame = enc.tobytes()

        # Extraer estado mock de subsistemas
        cam_mock = frame_data.get("is_mock", self.camera.mock_mode) if frame_data else self.camera.mock_mode
        vis_mock = landmarks_data.get("is_mock", self.vision.mock_mode) if landmarks_data else self.vision.mock_mode
        sens_mock = sensor_data.get("is_mock", True) if sensor_data else True

        # Telemetría enriquecida para WebSocket y Frontend
        auto_info = {
            "sign": classification.get("stable_sign") or classification.get("predicted_sign"),
            "score": classification.get("score", 0.0),
            "margin": classification.get("margin", 0.0),
            "status": classification.get("status", "NO_HAND"),
            "confidence": classification.get("confidence", 0.0),
            "predicted_sign": classification.get("predicted_sign"),
            "stable_sign": classification.get("stable_sign"),
            "detected": classification.get("detected", False)
        }

        # Extraer diagnósticos morfológicos
        diag_data = classification.get("diagnostics", {}) or eval_result.get("diagnostics", {})

        # Registro periódico en logs de características diagnósticas (1 Hz aprox)
        if self.frame_count % 25 == 0 and landmarks_data and landmarks_data.get("detected", False):
            b_d = diag_data.get("b", {})
            c_d = diag_data.get("c", {})
            y_d = diag_data.get("y", {})
            logger.info(
                f"[DIAG LSM] Candidatos={classification.get('candidate_scores')} | "
                f"B(fold={b_d.get('thumb_fold', 0)}%, add={b_d.get('adduction', 0)}%) | "
                f"C(curv={c_d.get('curvature', 0)}%, open={c_d.get('opening', 0)}%) | "
                f"Y(th={y_d.get('thumb', 0)}%, pk={y_d.get('pinky', 0)}%, cflx={y_d.get('center_flex', 0)}%)"
            )

        payload = {
            "frame_id": self.frame_count,
            "timestamp": time.time(),
            "mode": self.mode,
            "target_sign": self.target_sign,
            "auto_classification": auto_info,
            "candidate_scores": classification.get("candidate_scores", {}),
            "diagnostics": diag_data,
            "is_paused": self.is_paused,
            "pipeline_latency_ms": round(t_elapsed, 2),
            "camera_status": self.camera.get_status().value,
            "camera_fps": cam_fps,
            "has_hand": landmarks_data is not None and landmarks_data.get("detected", False),
            "hand_count": landmarks_data.get("hand_count", 0) if landmarks_data else 0,
            "confidence": landmarks_data.get("confidence", 0.0) if landmarks_data else 0.0,
            "landmarks": landmarks_data.get("raw_landmarks", []) if landmarks_data else [],
            "fusion": {
                "valid_fusion": fused_state.get("valid_fusion", False),
                "vision_present": fused_state.get("vision_present", False),
                "sensors_present": fused_state.get("sensors_present", False)
            },
            "evaluation": eval_result,
            "feedback": feedback_msg,
            "sensor_telemetry": sensor_data,
            "subsystems_mock": {
                "camera": cam_mock,
                "vision": vis_mock,
                "sensors": sens_mock
            }
        }

        with self._lock:
            self.latest_payload = payload

        return payload

    def get_latest_payload(self) -> Dict[str, Any]:
        with self._lock:
            return self.latest_payload.copy() if self.latest_payload else {}

    def get_latest_jpeg(self) -> Optional[bytes]:
        return self.latest_jpeg_frame
