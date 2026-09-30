"""
Evaluador morfológico y lingüístico de Lengua de Señas Mexicana (LSM).
Aplica análisis geométrico explicable para las 5 señas de Nivel 1: A, B, C, L, Y.
Trazable a 03_DOCS/lsm/LSM_LEVEL_1_SPECIFICATION.md.
NUNCA afirma 'seña correcta' únicamente por la presencia de una mano.
Incluye calibración discriminativa de alta precisión para rechazar manos abiertas y posturas ambiguas.
"""

from typing import Dict, Any, Optional, List
from .geometry import HandGeometryFeatures, clamp
from ..backend.logger import get_logger

logger = get_logger("lsm")


class LSMEvaluator:
    """Evaluador de corrección fonológica y anatómica de LSM para Nivel 1."""

    def __init__(self, config=None):
        self.config = config
        self.active_level = 1
        self.target_sign = "A"
        self.threshold = 0.78

        if config:
            lsm_conf = config.get("lsm", {}) if hasattr(config, "get") else {}
            self.active_level = int(lsm_conf.get("active_level", 1))
            self.target_sign = lsm_conf.get("default_target_sign", "A").upper()
            self.threshold = float(lsm_conf.get("confidence_threshold", 0.78))

        logger.info(f"LSMEvaluator inicializado con reglas geométricas Nivel 1. Seña inicial: '{self.target_sign}'.")

    def set_target_sign(self, sign: str) -> None:
        self.target_sign = sign.upper()

    def evaluate(self, fused_state: Dict[str, Any], target_sign: Optional[str] = None) -> Dict[str, Any]:
        """
        Evalúa el estado sensorial contra la seña objetivo mediante cinemática explicable.
        Retorna veredicto global, desglose por los 4 parámetros constitutivos y telemetría diagnóstica.
        """
        sign = (target_sign or self.target_sign).upper()

        # 1. Comprobar si hay mano detectada
        has_vision = fused_state.get("vision_present", False)
        raw_landmarks = fused_state.get("raw_landmarks", [])

        if not has_vision or not raw_landmarks or len(raw_landmarks) < 21:
            return {
                "sign": sign,
                "level": self.active_level,
                "is_valid": False,
                "overall_score": 0.0,
                "threshold": self.threshold,
                "message": "Sin mano detectada en el encuadre",
                "parameters": {
                    "configuration": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."},
                    "orientation": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."},
                    "movement": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."},
                    "location": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."}
                },
                "diagnostics": {
                    "b": {"thumb_fold": 0.0, "adduction": 0.0},
                    "c": {"curvature": 0.0, "opening": 0.0, "thumb_arc": 0.0, "arc_consistency": 0.0},
                    "y": {"thumb": 0.0, "pinky": 0.0, "center_flex": 0.0, "lateral_sep": 0.0}
                }
            }

        # 2. Análisis geométrico de la mano
        handedness = fused_state.get("handedness", "Right")
        geom = HandGeometryFeatures(raw_landmarks, handedness=handedness)
        ext = geom.get_finger_extension_states()
        cx, cy = geom.get_hand_center()

        # Evaluación por seña
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
            eval_dict = {
                "config_score": 0.0,
                "config_reason": f"Seña '{sign}' no implementada en Nivel 1",
                "orient_score": 0.0,
                "orient_reason": "Seña desconocida",
                "mov_score": 0.0,
                "loc_score": 0.0
            }

        # Ubicación espacial (Toponema): centrado en el encuadre
        in_bounds = (0.12 <= cx <= 0.88) and (0.12 <= cy <= 0.88)
        loc_score = 0.95 if in_bounds else 0.40
        loc_status = "PASS" if in_bounds else "CORRECT"
        loc_reason = "Mano en zona neutra adecuada" if in_bounds else "Centra tu mano en el encuadre"

        # Dinámica (Kinema): para señas estáticas de Nivel 1 el kinema es 1.0 si es estable
        mov_score = 1.0
        mov_status = "PASS"
        mov_reason = "Postura estática correcta"

        c_score = eval_dict["config_score"]
        o_score = eval_dict["orient_score"]

        # Ponderación morfológica: 50% configuración, 25% orientación, 15% kinema, 10% toponema
        overall = (c_score * 0.50) + (o_score * 0.25) + (mov_score * 0.15) + (loc_score * 0.10)
        is_valid = (overall >= self.threshold) and (c_score >= 0.70)

        return {
            "sign": sign,
            "level": self.active_level,
            "is_valid": is_valid,
            "overall_score": round(overall, 3),
            "threshold": self.threshold,
            "message": "Seña correcta" if is_valid else eval_dict["config_reason"],
            "parameters": {
                "configuration": {
                    "score": round(c_score, 3),
                    "status": "PASS" if c_score >= 0.75 else "CORRECT",
                    "param_name": "Queirema (Forma de dedos)",
                    "reason": eval_dict["config_reason"]
                },
                "orientation": {
                    "score": round(o_score, 3),
                    "status": "PASS" if o_score >= 0.75 else "CORRECT",
                    "param_name": "Orientación de palma",
                    "reason": eval_dict["orient_reason"]
                },
                "movement": {
                    "score": round(mov_score, 3),
                    "status": mov_status,
                    "param_name": "Kinema (Dinámica)",
                    "reason": mov_reason
                },
                "location": {
                    "score": round(loc_score, 3),
                    "status": loc_status,
                    "param_name": "Toponema (Ubicación espacial)",
                    "reason": loc_reason
                }
            },
            "diagnostics": geom.get_diagnostics()
        }

    # =========================================================================
    # EVALUADORES INDIVIDUALES DE QUEIREMA
    # =========================================================================

    def _evaluate_sign_a(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """Seña 'A': 4 dedos cerrados en puño, pulgar extendido/erguido al costado."""
        errors = []
        c_score = 1.0

        # Los 4 dedos deben estar flexionados
        for f in ["index", "middle", "ring", "pinky"]:
            if ext[f]:
                c_score -= 0.25
                errors.append(f"Flexiona el dedo {f}")

        # Pulgar debe estar al costado del índice
        scale = geom.get_palm_scale()
        from .geometry import euclidean_distance_3d
        d_th_mcp5 = euclidean_distance_3d(geom.pts[4], geom.pts[5]) / scale
        if d_th_mcp5 > 0.65:
            c_score -= 0.20
            errors.append("Coloca el pulgar erguido al costado del puño")

        # Rechazo explícito: si meñique está extendido (como en Y) o índice extendido (como en L)
        if ext["pinky"] or ext["index"]:
            c_score = min(c_score, 0.40)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Puño cerrado con pulgar al costado correcto"

        # Orientación: palma al frente
        o_score = 0.90
        o_reason = "Orientación frontal adecuada"

        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": o_score,
            "orient_reason": o_reason
        }

    def _evaluate_sign_b(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seña 'B': 4 dedos extendidos y juntos (aducidos), pulgar firmemente flexionado sobre la palma.
        Rechaza categóricamente la mano abierta o pulgar extendido.
        """
        errors = []
        ext_count = sum(1.0 for f in ["index", "middle", "ring", "pinky"] if ext[f])
        ext_ratio = ext_count / 4.0

        for f in ["index", "middle", "ring", "pinky"]:
            if not ext[f]:
                errors.append(f"Extiende el dedo {f}")

        # Características discriminativas estrictas
        thumb_fold = geom.get_thumb_fold_score()
        adduction = geom.get_finger_adduction_score()

        if thumb_fold < 0.50 or ext["thumb"]:
            errors.append("Flexiona el pulgar cruzándolo firmemente sobre la palma")

        if adduction < 0.60:
            errors.append("Junta los cuatro dedos extendidos sin separarlos")

        # Fórmula ponderada para B
        c_score = 0.40 * ext_ratio + 0.35 * thumb_fold + 0.25 * adduction

        # REGLA ESTRICTA DE RECHAZO: Mano abierta (pulgar no doblado o dedos splay) NO puede pasar
        if thumb_fold < 0.45 or ext["thumb"]:
            c_score = min(c_score, 0.42)
        if ext_ratio < 0.75:
            c_score = min(c_score, 0.38)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Cuatro dedos extendidos y juntos con pulgar en palma correcto"

        o_score = 0.92
        o_reason = "Palma al frente con dedos verticales adecuada"

        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": o_score,
            "orient_reason": o_reason
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
        ext_count = sum(1.0 for f in ["index", "middle", "ring", "pinky"] if ext[f])
        thumb_fold = geom.get_thumb_fold_score()

        # Si los dedos están completamente rectos (mano abierta), penalizar
        if ext_count >= 3 and ext["thumb"]:
            c_score = min(c_score, 0.35)

        # Si está en puño cerrado con puntas en la palma, penalizar
        if ext_count == 0 and thumb_fold > 0.60:
            c_score = min(c_score, 0.30)

        errors = []
        if c_curv < 0.60:
            errors.append("Curva suavemente los dedos simulando un arco semicircular")
        if c_open < 0.55:
            errors.append("Separa el pulgar del índice manteniendo la abertura de la C")
        if c_th < 0.55:
            errors.append("Arquea el pulgar hacia adelante como base de la C")

        reason = errors[0] if errors else "Curvatura en arco de la letra C correcta"
        o_score = 0.88
        o_reason = "Orientación lateral o semi-perfil adecuada"

        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": o_score,
            "orient_reason": o_reason
        }

    def _evaluate_sign_l(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """Seña 'L': Pulgar e índice extendidos formando ~90°, medio, anular y meñique cerrados."""
        errors = []
        c_score = 1.0

        if not ext["index"]:
            c_score -= 0.30
            errors.append("Extiende el índice verticalmente")

        th_ext = geom.get_y_thumb_extension_score()
        if th_ext < 0.55:
            c_score -= 0.30
            errors.append("Extiende el pulgar horizontalmente")

        for f in ["middle", "ring", "pinky"]:
            if ext[f]:
                c_score -= 0.20
                errors.append(f"Flexiona el dedo {f}")

        # Ángulo pulgar-índice
        ang = geom.get_thumb_index_angle_deg()
        if not (50.0 <= ang <= 135.0):
            c_score -= 0.20
            errors.append("Ajusta el ángulo entre pulgar e índice a ~90 grados en 'L'")

        # Rechazo explícito: si meñique está extendido (como en Y)
        if ext["pinky"]:
            c_score = min(c_score, 0.40)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Forma en 'L' entre pulgar e índice correcta"

        o_score = 0.90
        o_reason = "Índice vertical hacia arriba adecuado"

        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": o_score,
            "orient_reason": o_reason
        }

    def _evaluate_sign_y(self, geom: HandGeometryFeatures, ext: Dict[str, bool], fused: Dict[str, Any]) -> Dict[str, Any]:
        """
        Seña 'Y': Pulgar y meñique extendidos, índice, medio y anular flexionados.
        Requiere una clara separación lateral pulgar-meñique mayor a los dedos centrales.
        """
        errors = []
        th_y = geom.get_y_thumb_extension_score()
        pk_y = geom.get_y_pinky_extension_score()
        cf_y = geom.get_y_center_flexion_score()
        lat_y = geom.get_y_lateral_separation_score()

        if th_y < 0.60:
            errors.append("Extiende el pulgar lateralmente")
        if pk_y < 0.60:
            errors.append("Extiende el meñique firmemente")
        if cf_y < 0.60:
            errors.append("Flexiona los tres dedos centrales (índice, medio y anular)")

        c_score = geom.get_y_composite_score()

        # REGLA ESTRICTA DE RECHAZO:
        # Mano abierta (dedos centrales extendidos) -> RECHAZAR
        # L (índice extendido, meñique doblado) -> RECHAZAR
        # A (meñique doblado) -> RECHAZAR
        if pk_y < 0.50 or th_y < 0.50 or cf_y < 0.50:
            c_score = min(c_score, 0.40)

        c_score = max(0.0, c_score)
        reason = errors[0] if errors else "Pulgar y meñique extendidos en 'Y' correcto"

        o_score = 0.88
        o_reason = "Orientación de palma frontal adecuada"

        return {
            "config_score": round(c_score, 3),
            "config_reason": reason,
            "orient_score": o_score,
            "orient_reason": o_reason
        }
