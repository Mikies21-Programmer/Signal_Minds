"""
Orquestador central del sistema INDIVISA INGENIUM 2026.
Coordina el ciclo de vida del backend, la ingesta multihilo y el flujo de datos.
"""

import time
from typing import Dict, Any, Optional
from .config_loader import ConfigLoader
from .logger import get_logger
from .health import HealthChecker

logger = get_logger("orchestrator")


class SystemOrchestrator:
    """Orquestador central del pipeline de procesamiento y evaluación LSM."""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config or ConfigLoader()
        self.health_checker = HealthChecker(self.config)
        self.is_running = False
        self.frame_count = 0
        self.target_sign = self.config.get("lsm", {}).get("default_target_sign", "A")

        # Lazy loading de módulos del pipeline
        self._init_subsystems()

    def _init_subsystems(self):
        """Inicializa las instancias de cada módulo de la arquitectura."""
        from ..camera.consumer import CameraConsumer
        from ..vision.pipeline import VisionPipeline
        from ..sensors.manager import SensorManager
        from ..fusion.engine import SensorFusionEngine
        from ..lsm.evaluator import LSMEvaluator
        from ..feedback.engine import FeedbackEngine

        self.camera = CameraConsumer(self.config)
        self.vision = VisionPipeline(self.config)
        self.sensors = SensorManager(self.config)
        self.fusion = SensorFusionEngine(self.config)
        self.lsm = LSMEvaluator(self.config)
        self.feedback = FeedbackEngine(self.config)

        logger.info("Todos los subsistemas inicializados correctamente.")

    def start(self) -> None:
        """Inicia los servicios del orquestador."""
        logger.info("Iniciando orquestador del sistema...")
        self.camera.start()
        self.sensors.start()
        self.is_running = True
        logger.info("Orquestador en ejecución activa.")

    def stop(self) -> None:
        """Detiene de forma ordenada todos los hilos y servicios."""
        logger.info("Deteniendo orquestador...")
        self.is_running = False
        self.camera.stop()
        self.sensors.stop()
        logger.info("Orquestador detenido exitosamente.")

    def set_target_sign(self, sign: str) -> None:
        """Actualiza la seña objetivo que se está evaluando."""
        self.target_sign = sign.upper()
        self.lsm.set_target_sign(self.target_sign)
        logger.info(f"Seña objetivo actualizada a: {self.target_sign}")

    def step(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo individual del pipeline (equivalente a 1 frame).
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

        # 5. Evaluación lingüística multinivel
        eval_result = self.lsm.evaluate(fused_state, target_sign=self.target_sign)

        # 6. Generación de feedback explicable
        feedback_msg = self.feedback.generate_feedback(eval_result)

        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        return {
            "frame_id": self.frame_count,
            "target_sign": self.target_sign,
            "pipeline_latency_ms": round(t_elapsed, 2),
            "evaluation": eval_result,
            "feedback": feedback_msg,
            "sensor_telemetry": sensor_data,
            "has_hand": landmarks_data is not None and landmarks_data.get("detected", False)
        }
