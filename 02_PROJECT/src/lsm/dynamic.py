"""
Módulo de procesamiento y evaluación temporal dinámica para Lengua de Señas Mexicana (LSM) Nivel 2.
Gestiona el seguimiento temporal de trayectorias (DynamicGestureTracker) para J, Ñ, Q, X, Z.
Aplica ventanas temporales reales (1.0 - 2.0 s), análisis cinemático explicable (desplazamiento,
longitud de trayectoria, cambios de dirección, rotación angular IMU) y máquinas de estados
para garantizar que ninguna seña de Nivel 2 se evalúe de forma puramente estática.
"""

import time
import math
from collections import deque
from typing import Dict, Any, List, Optional, Tuple

from .geometry import HandGeometryFeatures, euclidean_distance_3d, clamp
from ..backend.logger import get_logger

logger = get_logger("dynamic_lsm")


class DynamicGestureTracker:
    """
    Rastreador temporal de trayectorias anatómicas y cinemática mecatrónica para señas dinámicas.
    Mantiene una ventana deslizante de muestras con timestamps reales y descarta datos obsoletos.
    """

    LEVEL_2_SIGNS: List[str] = ["J", "Ñ", "Q", "X", "Z"]

    def __init__(
        self,
        window_duration_sec: float = 1.5,
        min_frames: int = 10,
        max_samples: int = 60
    ):
        self.window_duration_sec = float(window_duration_sec)
        self.min_frames = int(min_frames)
        self.max_samples = int(max_samples)

        # Cola de muestras temporales: cada elemento es un dict con ts, landmarks, imu, etc.
        self._samples: deque = deque(maxlen=self.max_samples)

        # Estado del tracker
        self.state: str = "NO_HAND"  # NO_HAND, HAND_DETECTED, PREPARING, MOVING, EVALUATING, RECOGNIZED, AMBIGUOUS, INCORRECT_MOVEMENT
        self.active_sign: Optional[str] = None
        self.recognized_sign: Optional[str] = None
        self.last_evaluation: Dict[str, Any] = {}

        logger.info(
            f"DynamicGestureTracker inicializado: ventana={self.window_duration_sec}s, min_frames={self.min_frames}."
        )

    def reset(self) -> None:
        """Reinicia la ventana temporal y el estado cinemático."""
        self._samples.clear()
        self.state = "NO_HAND"
        self.recognized_sign = None
        self.last_evaluation.clear()

    def add_sample(
        self,
        raw_landmarks: List[Dict[str, float]],
        sensor_telemetry: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ) -> None:
        """
        Agrega una muestra del pipeline sensorial con timestamp real.
        Descarta automáticamente muestras con antigüedad superior a window_duration_sec.
        """
        now = timestamp if timestamp is not None else time.time()

        if not raw_landmarks or len(raw_landmarks) < 21:
            # Si no hay mano, podar ventana
            self._prune_stale(now)
            if len(self._samples) == 0:
                self.state = "NO_HAND"
            return

        # Evitar muestras duplicadas dentro del mismo frame
        if self._samples:
            last = self._samples[-1]
            if abs(last["timestamp"] - now) < 1e-4 or (
                abs(last["timestamp"] - now) < 0.01 and
                abs(last["wrist"][0] - raw_landmarks[0]["x"]) < 1e-5 and
                abs(last["wrist"][1] - raw_landmarks[0]["y"]) < 1e-5
            ):
                return

        imu_data = sensor_telemetry or {}
        roll = float(imu_data.get("imu_roll_deg", 0.0))
        pitch = float(imu_data.get("imu_pitch_deg", 0.0))
        tilt = float(imu_data.get("tilt_error_deg", 0.0))
        imu_conn = bool(imu_data.get("is_connected", False))

        pts = {int(p.get("id", idx)): p for idx, p in enumerate(raw_landmarks)}
        scale = euclidean_distance_3d(pts[0], pts[9])
        scale = scale if scale > 1e-4 else 1.0

        sample = {
            "timestamp": now,
            "raw_landmarks": raw_landmarks,
            "pts": pts,
            "scale": scale,
            "wrist": (pts[0]["x"], pts[0]["y"], pts[0].get("z", 0.0)),
            "index_tip": (pts[8]["x"], pts[8]["y"], pts[8].get("z", 0.0)),
            "index_pip": (pts[6]["x"], pts[6]["y"], pts[6].get("z", 0.0)),
            "middle_tip": (pts[12]["x"], pts[12]["y"], pts[12].get("z", 0.0)),
            "pinky_tip": (pts[20]["x"], pts[20]["y"], pts[20].get("z", 0.0)),
            "hand_center": (
                sum(p["x"] for p in pts.values()) / 21.0,
                sum(p["y"] for p in pts.values()) / 21.0
            ),
            "imu": {
                "roll": roll,
                "pitch": pitch,
                "tilt": tilt,
                "connected": imu_conn
            }
        }

        self._samples.append(sample)
        self._prune_stale(now)

    def _prune_stale(self, now: float) -> None:
        """Elimina muestras fuera de la ventana temporal activa."""
        cutoff = now - self.window_duration_sec
        while self._samples and self._samples[0]["timestamp"] < cutoff:
            self._samples.popleft()

    def get_sample_count(self) -> int:
        return len(self._samples)

    def compute_trajectory_metrics(self, landmark_key: str = "index_tip") -> Dict[str, float]:
        """
        Calcula descriptores cinemáticos objetivos sobre la trayectoria de un landmark:
        - displacement: distancia lineal neta entre inicio y fin normalizada
        - path_length: recorrido total punto a punto normalizado
        - mean_speed: velocidad media normalizada por segundo
        - peak_speed: velocidad punta instantánea
        - direction_changes: cambios de dirección significativos (ángulos > 50°)
        - angular_change: variación angular IMU (roll/pitch)
        """
        n = len(self._samples)
        if n < 2:
            return {
                "displacement": 0.0,
                "path_length": 0.0,
                "duration_sec": 0.0,
                "mean_speed": 0.0,
                "peak_speed": 0.0,
                "direction_changes": 0.0,
                "angular_change": 0.0
            }

        t_start = self._samples[0]["timestamp"]
        t_end = self._samples[-1]["timestamp"]
        duration = max(1e-4, t_end - t_start)
        mean_scale = sum(s["scale"] for s in self._samples) / n

        # Puntos de trayectoria en el plano XY normalizado
        points = [s[landmark_key] for s in self._samples]

        # 1. Desplazamiento neto
        p0 = points[0]
        pN = points[-1]
        dx_net = (pN[0] - p0[0]) / mean_scale
        dy_net = (pN[1] - p0[1]) / mean_scale
        displacement = math.sqrt(dx_net * dx_net + dy_net * dy_net)

        # 2. Longitud de trayectoria punto a punto y velocidad punta
        path_length = 0.0
        peak_speed = 0.0
        step_vectors = []

        for i in range(len(points) - 1):
            dt = max(1e-4, self._samples[i + 1]["timestamp"] - self._samples[i]["timestamp"])
            dx = (points[i + 1][0] - points[i][0]) / mean_scale
            dy = (points[i + 1][1] - points[i][1]) / mean_scale
            dist = math.sqrt(dx * dx + dy * dy)
            path_length += dist

            speed = dist / dt
            if speed > peak_speed:
                peak_speed = speed

            if dist > 0.015:  # Filtro de micro-temblor para vectores de dirección
                step_vectors.append((dx, dy))

        mean_speed = path_length / duration

        # 3. Cambios de dirección (giros > 50 grados entre tramos)
        dir_changes = 0
        for i in range(len(step_vectors) - 1):
            v1 = step_vectors[i]
            v2 = step_vectors[i + 1]
            mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
            if mag1 > 1e-4 and mag2 > 1e-4:
                cos_ang = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (mag1 * mag2)))
                ang_deg = math.degrees(math.acos(cos_ang))
                if ang_deg >= 50.0:
                    dir_changes += 1

        # 4. Variación angular en IMU
        rolls = [s["imu"]["roll"] for s in self._samples if s["imu"]["connected"]]
        pitches = [s["imu"]["pitch"] for s in self._samples if s["imu"]["connected"]]
        if rolls and pitches:
            delta_roll = max(rolls) - min(rolls)
            delta_pitch = max(pitches) - min(pitches)
            angular_change = math.sqrt(delta_roll**2 + delta_pitch**2)
        else:
            angular_change = 0.0

        return {
            "displacement": round(displacement, 3),
            "path_length": round(path_length, 3),
            "duration_sec": round(duration, 3),
            "mean_speed": round(mean_speed, 3),
            "peak_speed": round(peak_speed, 3),
            "direction_changes": float(dir_changes),
            "angular_change": round(angular_change, 2)
        }

    # =========================================================================
    # EVALUADORES INDIVIDUALES PARA SEÑAS DINÁMICAS (NIVEL 2)
    # =========================================================================

    def evaluate_sign_j(self, geom: HandGeometryFeatures) -> Dict[str, Any]:
        """
        Seña 'J': Meñique extendido trazando una trayectoria en el aire.
        Exige meñique claramente extendido en la secuencia y longitud acumulada mínima.
        """
        # 1. Configuración anatómica instantánea
        ext = geom.get_finger_extension_states()
        j_config = geom.get_j_configuration_score()
        c_status = "PASS" if j_config >= 0.70 else "CORRECT"

        if not ext["pinky"]:
            return {
                "sign": "J",
                "is_valid": False,
                "score": j_config * 0.4,
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "FAIL", "mov": "FAIL"},
                "message": "Extiende el meñique y completa el movimiento."
            }

        if len(self._samples) < self.min_frames:
            return {
                "sign": "J",
                "is_valid": False,
                "score": 0.50,
                "status": "PREPARING",
                "param_status": {"config": c_status, "mov": "PREPARING"},
                "message": "Extiende el meñique y completa el movimiento."
            }

        # 2. Análisis de trayectoria del meñique (landmark 20)
        metrics = self.compute_trajectory_metrics(landmark_key="pinky_tip")
        p_len = metrics["path_length"]
        disp = metrics["displacement"]

        # Verificar proporción de la secuencia con meñique extendido
        pk_ext_ratio = sum(
            1.0 for s in self._samples
            if s["pts"][20]["y"] < s["pts"][18]["y"] or euclidean_distance_3d(s["pts"][20], s["pts"][0]) > euclidean_distance_3d(s["pts"][18], s["pts"][0])
        ) / len(self._samples)

        if pk_ext_ratio < 0.60:
            return {
                "sign": "J",
                "is_valid": False,
                "score": 0.40,
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "CORRECT", "mov": "FAIL"},
                "message": "Extiende el meñique y completa el movimiento."
            }

        # Longitud acumulada mínima requerida (~0.25 normalizada por escala de palma)
        if p_len < 0.22 or disp < 0.12:
            return {
                "sign": "J",
                "is_valid": False,
                "score": round(0.45 + min(0.20, p_len), 3),
                "status": "MOVING",
                "param_status": {"config": "PASS", "mov": "CORRECT"},
                "message": "Extiende el meñique y completa el movimiento."
            }

        mov_score = clamp((p_len - 0.20) / 0.35)
        overall = 0.45 * j_config + 0.55 * mov_score
        is_valid = overall >= 0.75

        return {
            "sign": "J",
            "is_valid": is_valid,
            "score": round(overall, 3),
            "status": "RECOGNIZED" if is_valid else "MOVING",
            "param_status": {"config": "PASS", "mov": "PASS" if is_valid else "CORRECT"},
            "message": "Seña correcta" if is_valid else "Extiende el meñique y completa el movimiento.",
            "metrics": metrics
        }

    def evaluate_sign_nn(self, geom: HandGeometryFeatures) -> Dict[str, Any]:
        """
        Seña 'Ñ': Configuración base 'N' con movimiento ondulante (múltiples cambios de dirección).
        Si no hay movimiento pero la configuración es N: rechaza indicando falta de ondulación.
        Si hay movimiento con mala configuración: indica corregir configuración.
        """
        n_config = geom.get_n_configuration_score()

        if n_config < 0.55:
            return {
                "sign": "Ñ",
                "is_valid": False,
                "score": round(n_config * 0.4, 3),
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "FAIL", "mov": "FAIL"},
                "message": "Corrige la configuración y repite el movimiento."
            }

        if len(self._samples) < self.min_frames:
            return {
                "sign": "Ñ",
                "is_valid": False,
                "score": 0.50,
                "status": "PREPARING",
                "param_status": {"config": "PASS", "mov": "PREPARING"},
                "message": "Falta el movimiento ondulante de Ñ."
            }

        # Trayectoria del centro de la mano o punta de dedos índice/medio
        metrics = self.compute_trajectory_metrics(landmark_key="hand_center")
        dir_changes = metrics["direction_changes"]
        p_len = metrics["path_length"]

        # Ondulación: exige al menos 2 cambios suaves de dirección y desplazamiento
        if p_len < 0.18 or dir_changes < 2:
            return {
                "sign": "Ñ",
                "is_valid": False,
                "score": round(0.50 + min(0.18, p_len), 3),
                "status": "MOVING",
                "param_status": {"config": "PASS", "mov": "CORRECT"},
                "message": "Falta el movimiento ondulante de Ñ."
            }

        mov_score = clamp(0.50 * (p_len / 0.35) + 0.50 * (dir_changes / 3.0))
        overall = 0.45 * n_config + 0.55 * mov_score
        is_valid = overall >= 0.75 and dir_changes >= 2

        return {
            "sign": "Ñ",
            "is_valid": is_valid,
            "score": round(overall, 3),
            "status": "RECOGNIZED" if is_valid else "MOVING",
            "param_status": {"config": "PASS", "mov": "PASS" if is_valid else "CORRECT"},
            "message": "Seña correcta" if is_valid else "Falta el movimiento ondulante de Ñ.",
            "metrics": metrics
        }

    def evaluate_sign_q(self, geom: HandGeometryFeatures) -> Dict[str, Any]:
        """
        Seña 'Q': Configuración con índice y pulgar hacia abajo + giro/oscilación de muñeca.
        Integra MPU6050 para detectar cambio angular real de roll/pitch (sin inventar yaw).
        """
        q_config = geom.get_q_configuration_score()

        if q_config < 0.50:
            return {
                "sign": "Q",
                "is_valid": False,
                "score": round(q_config * 0.4, 3),
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "FAIL", "mov": "FAIL"},
                "message": "Corrige la configuración de Q (índice y pulgar hacia abajo)."
            }

        if len(self._samples) < self.min_frames:
            return {
                "sign": "Q",
                "is_valid": False,
                "score": 0.50,
                "status": "PREPARING",
                "param_status": {"config": "PASS", "mov": "PREPARING"},
                "message": "Realiza el giro/oscilación de la muñeca."
            }

        metrics = self.compute_trajectory_metrics(landmark_key="wrist")
        ang_change = metrics["angular_change"]
        p_len = metrics["path_length"]

        # Giro excesivo (> 60°) o giro nulo (< 7° y sin desplazamiento)
        if ang_change > 65.0:
            return {
                "sign": "Q",
                "is_valid": False,
                "score": 0.45,
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "PASS", "mov": "FAIL"},
                "message": "Reduce el giro excesivo de la muñeca para Q."
            }

        # Exigir cambio angular o movimiento de oscilación en muñeca
        has_rotation = (7.0 <= ang_change <= 60.0) or (p_len >= 0.20)

        if not has_rotation:
            return {
                "sign": "Q",
                "is_valid": False,
                "score": round(0.48 + min(0.20, ang_change / 30.0), 3),
                "status": "MOVING",
                "param_status": {"config": "PASS", "mov": "CORRECT"},
                "message": "Realiza el giro/oscilación de la muñeca."
            }

        rot_score = clamp(ang_change / 15.0) if ang_change >= 7.0 else clamp(p_len / 0.22)
        overall = 0.45 * q_config + 0.55 * rot_score
        is_valid = (overall >= 0.70) and has_rotation

        return {
            "sign": "Q",
            "is_valid": is_valid,
            "score": round(overall, 3),
            "status": "RECOGNIZED" if is_valid else "MOVING",
            "param_status": {"config": "PASS", "mov": "PASS" if is_valid else "CORRECT"},
            "message": "Seña correcta" if is_valid else "Realiza el giro/oscilación de la muñeca.",
            "metrics": metrics
        }

    def evaluate_sign_x(self, geom: HandGeometryFeatures) -> Dict[str, Any]:
        """
        Seña 'X': Dedo índice en gancho (NO recto) + movimiento de tracción hacia atrás.
        Rechaza categóricamente índice recto (>140°) o secuencia estática.
        """
        is_hook, hook_score = geom.is_index_hooked()
        ang_pip = geom.get_finger_pip_angle("index")

        # Rechazo explícito si índice recto
        if ang_pip > 135.0 or not is_hook:
            return {
                "sign": "X",
                "is_valid": False,
                "score": round(hook_score * 0.4, 3),
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "FAIL", "mov": "FAIL"},
                "message": "Forma el gancho con el índice y completa el movimiento."
            }

        if len(self._samples) < self.min_frames:
            return {
                "sign": "X",
                "is_valid": False,
                "score": 0.52,
                "status": "PREPARING",
                "param_status": {"config": "PASS", "mov": "PREPARING"},
                "message": "Forma el gancho con el índice y completa el movimiento."
            }

        metrics = self.compute_trajectory_metrics(landmark_key="index_tip")
        p_len = metrics["path_length"]
        disp = metrics["displacement"]

        if p_len < 0.16 or disp < 0.08:
            return {
                "sign": "X",
                "is_valid": False,
                "score": round(0.50 + min(0.18, p_len), 3),
                "status": "MOVING",
                "param_status": {"config": "PASS", "mov": "CORRECT"},
                "message": "Forma el gancho con el índice y completa el movimiento."
            }

        mov_score = clamp((p_len - 0.12) / 0.28)
        overall = 0.50 * hook_score + 0.50 * mov_score
        is_valid = overall >= 0.74

        return {
            "sign": "X",
            "is_valid": is_valid,
            "score": round(overall, 3),
            "status": "RECOGNIZED" if is_valid else "MOVING",
            "param_status": {"config": "PASS", "mov": "PASS" if is_valid else "CORRECT"},
            "message": "Seña correcta" if is_valid else "Forma el gancho con el índice y completa el movimiento.",
            "metrics": metrics
        }

    def evaluate_sign_z(self, geom: HandGeometryFeatures) -> Dict[str, Any]:
        """
        Seña 'Z': Dedo índice extendido trazando una Z en el aire.
        Exige patrón de tres tramos con cambios de dirección marcados (>= 2 giros)
        y rechaza desplazamientos pequeños o líneas rectas.
        """
        z_config = geom.get_z_configuration_score()
        ext = geom.get_finger_extension_states()

        if not ext["index"]:
            return {
                "sign": "Z",
                "is_valid": False,
                "score": round(z_config * 0.35, 3),
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "FAIL", "mov": "FAIL"},
                "message": "Extiende el índice para trazar la Z."
            }

        if len(self._samples) < self.min_frames:
            return {
                "sign": "Z",
                "is_valid": False,
                "score": 0.50,
                "status": "PREPARING",
                "param_status": {"config": "PASS", "mov": "PREPARING"},
                "message": "Traza la Z completa."
            }

        metrics = self.compute_trajectory_metrics(landmark_key="index_tip")
        p_len = metrics["path_length"]
        dir_changes = int(metrics["direction_changes"])
        disp = metrics["displacement"]

        # Rechazo de trayectoria demasiado corta
        if p_len < 0.28:
            return {
                "sign": "Z",
                "is_valid": False,
                "score": round(0.40 + min(0.20, p_len), 3),
                "status": "MOVING",
                "param_status": {"config": "PASS", "mov": "CORRECT"},
                "message": "Traza la Z completa."
            }

        # Rechazo si no tiene los giros de la Z (línea recta sin cambios de dirección)
        if dir_changes < 2:
            return {
                "sign": "Z",
                "is_valid": False,
                "score": 0.52,
                "status": "INCORRECT_MOVEMENT",
                "param_status": {"config": "PASS", "mov": "CORRECT"},
                "message": "Traza la Z completa con sus cambios de dirección."
            }

        mov_score = clamp(0.50 * (p_len / 0.50) + 0.50 * (dir_changes / 2.0))
        overall = 0.45 * z_config + 0.55 * mov_score
        is_valid = overall >= 0.75 and dir_changes >= 2

        return {
            "sign": "Z",
            "is_valid": is_valid,
            "score": round(overall, 3),
            "status": "RECOGNIZED" if is_valid else "MOVING",
            "param_status": {"config": "PASS", "mov": "PASS" if is_valid else "CORRECT"},
            "message": "Seña correcta" if is_valid else "Traza la Z completa.",
            "metrics": metrics
        }

    def evaluate_sign(self, sign: str, geom: HandGeometryFeatures) -> Dict[str, Any]:
        """Evalúa cualquiera de las 5 señas dinámicas de Nivel 2."""
        s = sign.upper()
        if s == "J":
            res = self.evaluate_sign_j(geom)
        elif s in ["Ñ", "NN"]:
            res = self.evaluate_sign_nn(geom)
        elif s == "Q":
            res = self.evaluate_sign_q(geom)
        elif s == "X":
            res = self.evaluate_sign_x(geom)
        elif s == "Z":
            res = self.evaluate_sign_z(geom)
        else:
            res = {
                "sign": s,
                "is_valid": False,
                "score": 0.0,
                "status": "AMBIGUOUS",
                "param_status": {"config": "FAIL", "mov": "FAIL"},
                "message": f"Seña dinámica '{s}' no reconocida en Nivel 2."
            }

        self.last_evaluation = res
        self.state = res.get("status", "EVALUATING")
        if res.get("is_valid", False):
            self.recognized_sign = s
        return res
