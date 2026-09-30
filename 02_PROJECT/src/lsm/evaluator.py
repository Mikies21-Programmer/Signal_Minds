"""
Evaluador morfológico y lingüístico de Lengua de Señas Mexicana (LSM).
Aplica análisis geométrico explicable para las 5 señas de Nivel 1: A, B, C, L, Y
y señas dinámicas de Nivel 2: J, Ñ, Q, X, Z.
Trazable a 03_DOCS/lsm/LSM_LEVEL_1_SPECIFICATION.md.
NUNCA afirma 'seña correcta' únicamente por la presencia de una mano.
Incluye calibración discriminativa de alta precisión para rechazar manos abiertas y posturas ambiguas.
Utiliza estimación de orientación visual (heurística física landmarks+handedness) y ubicación ultrasónica.
"""

import time
from typing import Dict, Any, Optional, List
from .geometry import HandGeometryFeatures, euclidean_distance_3d, clamp, get_hand_orientation_visual
from .dynamic import DynamicGestureTracker
from ..backend.logger import get_logger

logger = get_logger("lsm")


class LSMEvaluator:
    """Evaluador de corrección fonológica y anatómica de LSM para Nivel 1 y Nivel 2."""

    def __init__(self, config=None):
        self.config = config
        self.active_level = 1
        self.target_sign = "A"
        self.threshold = 0.78
        self.dynamic_tracker = DynamicGestureTracker()

        if config:
            lsm_conf = config.get("lsm", {}) if hasattr(config, "get") else (config.get("lsm", {}) if isinstance(config, dict) else {})
            self.active_level = int(lsm_conf.get("active_level", 1))
            self.target_sign = lsm_conf.get("default_target_sign", "A").upper()
            self.threshold = float(lsm_conf.get("confidence_threshold", 0.78))

            sens_conf = config.get("sensors", {}) if hasattr(config, "get") else (config.get("sensors", {}) if isinstance(config, dict) else {})
            self.distance_min_cm = float(sens_conf.get("distance_min_cm", 20.0))
            self.distance_max_cm = float(sens_conf.get("distance_max_cm", 100.0))

            cam_conf = config.get("camera", {}) if hasattr(config, "get") else (config.get("camera", {}) if isinstance(config, dict) else {})
            self.orientation_invert = bool(cam_conf.get("orientation_invert", False))
        else:
            self.distance_min_cm = 20.0
            self.distance_max_cm = 100.0
            self.orientation_invert = False

        if self.target_sign in DynamicGestureTracker.LEVEL_2_SIGNS:
            self.active_level = 2

        logger.info(f"LSMEvaluator inicializado con reglas Nivel 1 y Nivel 2 dinámico. Seña inicial: '{self.target_sign}' (Nivel {self.active_level}).")

    def set_target_sign(self, sign: str) -> None:
        self.target_sign = sign.upper()
        if self.target_sign in DynamicGestureTracker.LEVEL_2_SIGNS:
            self.active_level = 2
            self.dynamic_tracker.reset()
        else:
            self.active_level = 1

    def evaluate_orientation(self, sign: str, fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa la orientación visual de la mano mediante estimación geométrica
        (palma vs dorso vs perfil lateral vs desconocido).
        Estados: PALM, BACK, SIDE, UNKNOWN.
        UNKNOWN proporciona score neutro (0.75).
        NO efectúa regla dura de bloqueo automático.
        """
        if not fused or not isinstance(fused, dict):
            return {
                "score": 0.75,
                "status": "NEUTRAL",
                "orientation_state": "UNKNOWN",
                "confidence": 0.0,
                "reason": "Orientación visual no disponible (score neutro)"
            }

        orient_state = fused.get("orientation")
        conf = float(fused.get("orientation_confidence", 0.0))

        if not orient_state or orient_state == "UNKNOWN":
            raw_landmarks = fused.get("raw_landmarks", [])
            if raw_landmarks and len(raw_landmarks) >= 21:
                handedness = fused.get("handedness", "Right")
                vis = get_hand_orientation_visual(
                    raw_landmarks,
                    handedness=handedness,
                    orientation_invert=self.orientation_invert
                )
                orient_state = vis.get("orientation", "UNKNOWN")
                conf = float(vis.get("confidence", 0.0))
            else:
                orient_state = "UNKNOWN"

        if orient_state == "UNKNOWN":
            return {
                "score": 0.75,
                "status": "NEUTRAL",
                "orientation_state": "UNKNOWN",
                "confidence": conf,
                "reason": "Orientación visual neutra (score neutro)"
            }

        if sign == "C":
            # Para C en LSM: la mano típicamente se muestra de perfil (SIDE) o semi-frontal (PALM)
            if orient_state in ["SIDE", "PALM"]:
                return {
                    "score": 1.0,
                    "status": "PASS",
                    "orientation_state": orient_state,
                    "confidence": conf,
                    "reason": f"Orientación adecuada para C ({orient_state})"
                }
            else:  # BACK
                return {
                    "score": 0.45,
                    "status": "FAIL",
                    "orientation_state": orient_state,
                    "confidence": conf,
                    "reason": "Orienta la mano de perfil para formar la letra C"
                }

        if sign == "Q":
            # Para Q en LSM: la mano apunta hacia abajo con rotación; BACK, SIDE o PALM son posturas válidas durante el giro
            if orient_state in ["BACK", "SIDE", "PALM"]:
                return {
                    "score": 1.0,
                    "status": "PASS",
                    "orientation_state": orient_state,
                    "confidence": conf,
                    "reason": f"Orientación adecuada para Q ({orient_state})"
                }

        # Para A, B, L, Y (y señas frontales estándar en LSM): se espera PALM
        if orient_state == "PALM":
            return {
                "score": 1.0,
                "status": "PASS",
                "orientation_state": "PALM",
                "confidence": conf,
                "reason": "Orientación frontal (palma) correcta"
            }
        elif orient_state == "SIDE":
            return {
                "score": 0.55,
                "status": "CORRECT",
                "orientation_state": "SIDE",
                "confidence": conf,
                "reason": "Gira la palma hacia el frente"
            }
        elif orient_state == "BACK":
            return {
                "score": 0.35,
                "status": "FAIL",
                "orientation_state": "BACK",
                "confidence": conf,
                "reason": "Muestra la palma hacia la cámara, no el dorso"
            }
        else:
            return {
                "score": 0.75,
                "status": "NEUTRAL",
                "orientation_state": "UNKNOWN",
                "confidence": conf,
                "reason": "Orientación neutra"
            }

    def evaluate_ultrasonic(self, fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa la ubicación de la mano mediante el sensor de distancia ultrasónico.
        Si el sensor está ausente, desconectado o la lectura es inválida, devuelve score neutro (0.85).
        NO bloquea automáticamente una letra correcta.
        """
        if not fused or not isinstance(fused, dict):
            return {
                "score": 0.85,
                "status": "NEUTRAL",
                "distance_cm": None,
                "distance_valid": False,
                "reason": "Ultrasonido ausente (score neutro)"
            }

        dist_valid = bool(fused.get("distance_valid", False))
        dist_cm = fused.get("distance_cm")

        if not dist_valid or dist_cm is None:
            return {
                "score": 0.85,
                "status": "NEUTRAL",
                "distance_cm": None,
                "distance_valid": False,
                "reason": "Ultrasonido ausente o lectura no disponible (score neutro)"
            }

        # Si hay distancia válida, evaluar dentro del rango objetivo
        if self.distance_min_cm <= dist_cm <= self.distance_max_cm:
            return {
                "score": 1.0,
                "status": "PASS",
                "distance_cm": round(dist_cm, 1),
                "distance_valid": True,
                "reason": f"Ubicación ultrasónica óptima ({dist_cm:.1f} cm)"
            }
        elif dist_cm < self.distance_min_cm:
            return {
                "score": 0.60,
                "status": "CORRECT",
                "distance_cm": round(dist_cm, 1),
                "distance_valid": True,
                "reason": f"Mano demasiado próxima al sensor ({dist_cm:.1f} cm)"
            }
        else:
            return {
                "score": 0.60,
                "status": "CORRECT",
                "distance_cm": round(dist_cm, 1),
                "distance_valid": True,
                "reason": f"Mano demasiado lejana al sensor ({dist_cm:.1f} cm)"
            }

    def evaluate(self, fused_state: Dict[str, Any], target_sign: Optional[str] = None) -> Dict[str, Any]:
        """
        Evalúa el estado sensorial contra la seña objetivo mediante cinemática explicable.
        Para Nivel 1:
          75% configuración geométrica (Queirema)
          15% orientación visual (heurística)
          10% ubicación ultrasónica
        Retorna veredicto global, desglose por los 4 parámetros constitutivos y telemetría diagnóstica.
        """
        sign = (target_sign or self.target_sign).upper()

        # 1. Comprobar si hay mano detectada
        has_vision = fused_state.get("vision_present", False)
        raw_landmarks = fused_state.get("raw_landmarks", [])

        if not has_vision or not raw_landmarks or len(raw_landmarks) < 21:
            orient_eval = self.evaluate_orientation(sign, fused_state)
            us_eval = self.evaluate_ultrasonic(fused_state)
            return {
                "sign": sign,
                "level": self.active_level,
                "is_valid": False,
                "overall_score": 0.0,
                "threshold": self.threshold,
                "message": "Sin mano detectada en el encuadre",
                "parameters": {
                    "configuration": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."},
                    "orientation": {
                        "score": orient_eval["score"],
                        "status": orient_eval["status"],
                        "orientation_state": orient_eval["orientation_state"],
                        "param_name": "Orientación visual de palma",
                        "reason": orient_eval["reason"]
                    },
                    "movement": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."},
                    "location": {
                        "score": us_eval["score"],
                        "status": us_eval["status"],
                        "distance_cm": us_eval.get("distance_cm"),
                        "distance_valid": us_eval.get("distance_valid", False),
                        "param_name": "Toponema (Ubicación ultrasónica)",
                        "reason": us_eval["reason"]
                    }
                },
                "diagnostics": {
                    "b": {"thumb_fold": 0.0, "adduction": 0.0},
                    "c": {"curvature": 0.0, "opening": 0.0, "thumb_arc": 0.0, "arc_consistency": 0.0},
                    "y": {"thumb": 0.0, "pinky": 0.0, "center_flex": 0.0, "lateral_sep": 0.0}
                }
            }

        # 2. Registrar muestra en el DynamicGestureTracker
        sensor_data = fused_state.get("sensor_telemetry")
        ts = fused_state.get("timestamp_vision") or fused_state.get("timestamp") or time.time()
        self.dynamic_tracker.add_sample(raw_landmarks, sensor_telemetry=sensor_data, timestamp=ts)

        # 3. Análisis geométrico de la mano
        handedness = fused_state.get("handedness", "Right")
        geom = HandGeometryFeatures(raw_landmarks, handedness=handedness)
        ext = geom.get_finger_extension_states()

        # EVALUACIÓN DE SEÑAS DINÁMICAS (NIVEL 2: J, Ñ, Q, X, Z)
        if sign in DynamicGestureTracker.LEVEL_2_SIGNS:
            self.active_level = 2
            dyn_eval = self.dynamic_tracker.evaluate_sign(sign, geom)
            orient_eval = self.evaluate_orientation(sign, fused_state)
            us_eval = self.evaluate_ultrasonic(fused_state)

            dyn_status = dyn_eval.get("status", "EVALUATING")
            is_dyn_valid = dyn_eval.get("is_valid", False)

            dyn_score = dyn_eval.get("score", 0.0)
            overall = (dyn_score * 0.75) + (orient_eval["score"] * 0.15) + (us_eval["score"] * 0.10)
            is_valid = is_dyn_valid and (overall >= self.threshold) and (orient_eval["score"] >= 0.50)

            if is_valid:
                message = "Seña correcta"
            elif not is_dyn_valid:
                message = dyn_eval.get("message", "Completa el movimiento dinámico.")
            elif orient_eval["score"] < 0.50:
                message = orient_eval["reason"]
            else:
                message = dyn_eval.get("message", "Perfecciona el movimiento.")

            return {
                "sign": sign,
                "level": 2,
                "is_valid": is_valid,
                "overall_score": round(overall, 3),
                "threshold": self.threshold,
                "message": message,
                "dynamic_status": dyn_status,
                "parameters": {
                    "configuration": {
                        "score": round(dyn_eval.get("score", 0.0), 3),
                        "status": dyn_eval.get("param_status", {}).get("config", "PASS"),
                        "param_name": "Queirema (Configuración de dedos)",
                        "reason": dyn_eval.get("message", "Configuración de mano")
                    },
                    "orientation": {
                        "score": round(orient_eval["score"], 3),
                        "status": orient_eval["status"],
                        "orientation_state": orient_eval["orientation_state"],
                        "param_name": "Orientación visual de palma",
                        "reason": orient_eval["reason"]
                    },
                    "movement": {
                        "score": round(dyn_eval.get("metrics", {}).get("path_length", 0.0), 3),
                        "status": dyn_eval.get("param_status", {}).get("mov", "CORRECT"),
                        "param_name": "Kinema (Dinámica)",
                        "reason": dyn_eval.get("message", "Movimiento dinámico")
                    },
                    "location": {
                        "score": round(us_eval["score"], 3),
                        "status": us_eval["status"],
                        "distance_cm": us_eval.get("distance_cm"),
                        "distance_valid": us_eval.get("distance_valid", False),
                        "param_name": "Toponema (Ubicación ultrasónica)",
                        "reason": us_eval["reason"]
                    }
                },
                "diagnostics": geom.get_diagnostics(),
                "trajectory_metrics": dyn_eval.get("metrics", {})
            }

        # EVALUACIÓN DE SEÑAS ESTÁTICAS (NIVEL 1: A, B, C, L, Y)
        self.active_level = 1
        if sign == "A":
            eval_dict = self._evaluate_sign_a(geom, ext, fused_state)
        elif sign == "B":
            eval_dict = self._evaluate_sign_b(geom, ext, fused_state)
        elif sign == "C":
            eval_dict = self._evaluate_sign_c(geom, ext, fused_state)
        elif sign == "L":
            eval_dict = self._evaluate_sign_l(geom, ext, fused_state)
        elif sign == "Y":
            eval_dict = self._evaluate_sign_y(geom, ext, fused_state)
        else:
            orient_eval = self.evaluate_orientation(sign, fused_state)
            eval_dict = {
                "config_score": 0.0,
                "config_reason": f"Seña '{sign}' no implementada",
                "orient_score": orient_eval["score"],
                "orient_reason": orient_eval["reason"],
                "orient_status": orient_eval["status"],
                "orientation_state": orient_eval["orientation_state"]
            }

        orient_eval = self.evaluate_orientation(sign, fused_state)
        us_eval = self.evaluate_ultrasonic(fused_state)

        c_score = eval_dict["config_score"]
        o_score = orient_eval["score"]
        u_score = us_eval["score"]

        # Ponderación Nivel 1:
        # 75% configuración geométrica
        # 15% orientación visual
        # 10% ubicación ultrasónica
        overall = (c_score * 0.75) + (o_score * 0.15) + (u_score * 0.10)

        # Regla de validez:
        # - Configuración morfológica mínima requerida: 0.70
        # - Umbral global: 0.78
        # - UNKNOWN orientation (score 0.70) y ultrasonido ausente (score 0.70)
        #   producen score neutro y NO destruyen una letra correcta.
        is_valid = (overall >= self.threshold) and (c_score >= 0.70)
        if is_valid:
            message = "Seña correcta"
        elif c_score < 0.70:
            message = eval_dict["config_reason"]
        elif o_score < 0.50:
            message = orient_eval["reason"]
        elif u_score < 0.70:
            message = us_eval["reason"]
        else:
            message = eval_dict["config_reason"]

        return {
            "sign": sign,
            "level": 1,
            "is_valid": is_valid,
            "overall_score": round(overall, 3),
            "threshold": self.threshold,
            "message": message,
            "parameters": {
                "configuration": {
                    "score": round(c_score, 3),
                    "status": "PASS" if c_score >= 0.75 else "CORRECT",
                    "param_name": "Queirema (Forma de dedos)",
                    "reason": eval_dict["config_reason"]
                },
                "orientation": {
                    "score": round(o_score, 3),
                    "status": orient_eval["status"],
                    "orientation_state": orient_eval.get("orientation_state", "UNKNOWN"),
                    "param_name": "Orientación visual de palma",
                    "reason": orient_eval["reason"]
                },
                "movement": {
                    "score": 1.0,
                    "status": "PASS",
                    "param_name": "Kinema (Dinámica)",
                    "reason": "Postura estática correcta"
                },
                "location": {
                    "score": round(u_score, 3),
                    "status": us_eval["status"],
                    "distance_cm": us_eval.get("distance_cm"),
                    "distance_valid": us_eval.get("distance_valid", False),
                    "param_name": "Toponema (Ubicación ultrasónica)",
                    "reason": us_eval["reason"]
                }
            },
            "diagnostics": geom.get_diagnostics()
        }

    # =========================================================================
    # EVALUADORES INDIVIDUALES DE QUEIREMA (A, B, C, L, Y)
    # =========================================================================

    def _evaluate_sign_a(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """Seña 'A': 4 dedos cerrados en puño, pulgar extendido/erguido al costado."""
        errors = []
        c_score = 1.0
        finger_names_es = {"index": "índice", "middle": "medio", "ring": "anular", "pinky": "meñique"}

        # Los 4 dedos deben estar flexionados
        for f in ["index", "middle", "ring", "pinky"]:
            if ext[f]:
                c_score -= 0.25
                errors.append(f"Flexiona el dedo {finger_names_es[f]}.")

        # Pulgar debe estar al costado del índice
        scale = geom.get_palm_scale()
        d_th_mcp5 = euclidean_distance_3d(geom.pts[4], geom.pts[5]) / scale
        if d_th_mcp5 > 0.65:
            c_score -= 0.20
            errors.append("Coloca el pulgar al costado de la mano.")

        # Rechazo explícito: si meñique está extendido (como en Y) o índice extendido (como en L)
        if ext["pinky"] or ext["index"]:
            c_score = min(c_score, 0.35)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Puño cerrado con pulgar al costado correcto"

        orient_eval = self.evaluate_orientation("A", fused)
        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": orient_eval["score"],
            "orient_reason": orient_eval["reason"],
            "orient_status": orient_eval["status"],
            "orientation_state": orient_eval["orientation_state"]
        }

    def _evaluate_sign_b(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seña 'B': 4 dedos extendidos y juntos (aducidos), pulgar firmemente flexionado sobre la palma.
        Rechaza categóricamente la mano abierta o pulgar extendido.
        """
        errors = []
        finger_names_es = {"index": "índice", "middle": "medio", "ring": "anular", "pinky": "meñique"}
        ext_count = sum(1.0 for f in ["index", "middle", "ring", "pinky"] if ext[f])
        ext_ratio = ext_count / 4.0

        for f in ["index", "middle", "ring", "pinky"]:
            if not ext[f]:
                errors.append(f"Extiende el dedo {finger_names_es[f]}.")

        thumb_fold = geom.get_thumb_fold_score()
        adduction = geom.get_finger_adduction_score()

        if thumb_fold < 0.50 or ext["thumb"]:
            errors.append("Flexiona el pulgar sobre la palma.")

        if adduction < 0.55:
            errors.append("Junta los cuatro dedos.")

        c_score = 0.40 * ext_ratio + 0.35 * thumb_fold + 0.25 * adduction

        # REGLA ESTRICTA DE RECHAZO: Mano abierta (pulgar no doblado o dedos splay) NO puede pasar
        if thumb_fold < 0.45 or ext["thumb"]:
            c_score = min(c_score, 0.35)
        if adduction < 0.50:
            c_score = min(c_score, 0.35)
        if ext_ratio < 0.75:
            c_score = min(c_score, 0.35)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Cuatro dedos extendidos y juntos con pulgar en palma correcto"

        orient_eval = self.evaluate_orientation("B", fused)
        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": orient_eval["score"],
            "orient_reason": orient_eval["reason"],
            "orient_status": orient_eval["status"],
            "orientation_state": orient_eval["orientation_state"]
        }

    def _evaluate_sign_c(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seña 'C': Dedos curvados formando un arco semicircular continuo con apertura cóncava.
        Combina: 40% curvatura + 25% apertura + 20% arco del pulgar + 15% consistencia de arco.
        Diferencia explícitamente entre MANO ABIERTA, PUÑO y C.
        """
        c_curv = geom.get_c_curvature_score()
        c_open = geom.get_c_opening_score()
        c_th = geom.get_c_thumb_score()
        c_arc = geom.get_c_arc_consistency()

        c_score = 0.40 * c_curv + 0.25 * c_open + 0.20 * c_th + 0.15 * c_arc

        # Puertas duras de discriminación
        thumb_fold = geom.get_thumb_fold_score()
        scale = geom.get_palm_scale()
        d_idx_mcp = euclidean_distance_3d(geom.pts[8], geom.pts[5]) / scale
        mean_pip = sum(geom.get_finger_pip_angle(f) for f in ["index", "middle", "ring", "pinky"]) / 4.0
        errors = []

        if mean_pip > 165.0 or c_curv < 0.40:
            c_score = min(c_score, 0.30)
            errors.append("Curva los cuatro dedos en arco.")

        if thumb_fold > 0.55 or d_idx_mcp < 0.30:
            c_score = min(c_score, 0.30)
            errors.append("Abre la mano y forma un arco con los dedos.")

        if c_curv < 0.58:
            errors.append("Curva suavemente los dedos simulando un arco.")
        if c_open < 0.50:
            errors.append("Separa el pulgar del índice manteniendo la abertura de la C.")
        if c_th < 0.50:
            errors.append("Arquea el pulgar formando la C.")

        reason = errors[0] if errors else "Curvatura en arco de la letra C correcta"

        orient_eval = self.evaluate_orientation("C", fused)
        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": orient_eval["score"],
            "orient_reason": orient_eval["reason"],
            "orient_status": orient_eval["status"],
            "orientation_state": orient_eval["orientation_state"]
        }

    def _evaluate_sign_l(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """Seña 'L': Pulgar e índice extendidos formando ~90°, medio, anular y meñique cerrados."""
        errors = []
        c_score = 1.0
        finger_names_es = {"middle": "medio", "ring": "anular", "pinky": "meñique"}

        if not ext["index"]:
            c_score -= 0.30
            errors.append("Extiende el dedo índice.")

        th_ext = geom.get_y_thumb_extension_score()
        if th_ext < 0.55:
            c_score -= 0.30
            errors.append("Extiende el pulgar.")

        for f in ["middle", "ring", "pinky"]:
            if ext[f]:
                c_score = min(c_score, 0.35)
                errors.append(f"Flexiona el dedo {finger_names_es[f]}.")

        ang = geom.get_thumb_index_angle_deg()
        if not (50.0 <= ang <= 135.0):
            c_score = min(c_score, 0.40)
            errors.append("Forma un ángulo de 90 grados entre pulgar e índice.")

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Forma en 'L' entre pulgar e índice correcta"

        orient_eval = self.evaluate_orientation("L", fused)
        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": orient_eval["score"],
            "orient_reason": orient_eval["reason"],
            "orient_status": orient_eval["status"],
            "orientation_state": orient_eval["orientation_state"]
        }

    def _evaluate_sign_y(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seña 'Y': Pulgar y meñique extendidos, índice, medio y anular flexionados.
        Requiere una clara separación lateral pulgar-meñique mayor a los dedos centrales.
        """
        errors = []
        finger_names_es = {"index": "índice", "middle": "medio", "ring": "anular"}
        th_y = geom.get_y_thumb_extension_score()
        pk_y = geom.get_y_pinky_extension_score()
        cf_y = geom.get_y_center_flexion_score()
        lat_y = geom.get_y_lateral_separation_score()

        if th_y < 0.55:
            errors.append("Extiende el pulgar.")
        if pk_y < 0.55:
            errors.append("Extiende el dedo meñique.")

        for f in ["index", "middle", "ring"]:
            if ext[f]:
                errors.append(f"Flexiona el dedo {finger_names_es[f]}.")

        if lat_y < 0.50:
            errors.append("Separa bien el pulgar y el meñique.")

        c_score = geom.get_y_composite_score()

        if ext["index"] or ext["middle"] or ext["ring"]:
            c_score = min(c_score, 0.35)

        if pk_y < 0.50 or th_y < 0.50 or cf_y < 0.50:
            c_score = min(c_score, 0.35)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Pulgar y meñique extendidos en 'Y' correcto"

        orient_eval = self.evaluate_orientation("Y", fused)
        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": orient_eval["score"],
            "orient_reason": orient_eval["reason"],
            "orient_status": orient_eval["status"],
            "orientation_state": orient_eval["orientation_state"]
        }
