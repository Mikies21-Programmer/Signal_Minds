"""
Clasificador automático de Lengua de Señas Mexicana (LSM) Nivel 1 y Nivel 2.
Evalúa landmarks anatómicos reales contra el conjunto de candidatos canónicos por nivel:
- Nivel 1: A, B, C, L, Y
- Nivel 2: J, Ñ, Q, X, Z

Aplica separación estricta por nivel:
- En modo automático de Nivel 1: evalúa SOLO A, B, C, L, Y. Los signos de Nivel 2 no afectan el margen.
- En modo automático de Nivel 2: evalúa SOLO J, Ñ, Q, X, Z.
- En modo target explícito: evalúa ÚNICAMENTE target_sign (sin competencia multiclase).
"""

from collections import deque
from typing import Dict, Any, Optional, List
from .evaluator import LSMEvaluator
from ..backend.logger import get_logger

logger = get_logger("classifier")


class AutomaticLSMClassifier:
    """Clasificador multiclase automático para el alfabeto LSM Nivel 1 y Nivel 2 dinámico."""

    LEVEL_1_SIGNS: List[str] = ["A", "B", "C", "L", "Y"]
    LEVEL_2_SIGNS: List[str] = ["J", "Ñ", "Q", "X", "Z"]
    SIGNS: List[str] = ["A", "B", "C", "L", "Y", "J", "Ñ", "Q", "X", "Z"]

    def __init__(
        self,
        evaluator: Optional[LSMEvaluator] = None,
        config: Optional[Any] = None,
        threshold: float = 0.78,
        margin: float = 0.08,
        window_size: int = 7,
        active_level: int = 1
    ):
        self.evaluator = evaluator or LSMEvaluator(config)
        self.threshold = threshold
        self.margin = margin
        self.window_size = window_size
        self.active_level = active_level
        if config and hasattr(config, "get"):
            lsm_conf = config.get("lsm", {})
            self.active_level = int(lsm_conf.get("active_level", self.active_level))
        self.target_sign: Optional[str] = None

        # Cola de histórico para suavizado temporal de Nivel 1 (7 frames)
        self.history: deque = deque(maxlen=window_size)
        self.stable_sign: Optional[str] = None
        self.stable_score: float = 0.0
        self.stable_count: int = 0

        logger.info(
            f"AutomaticLSMClassifier inicializado: nivel={self.active_level}, "
            f"umbral={self.threshold}, margen={self.margin}, ventana={self.window_size} frames."
        )

    def set_active_level(self, level: int) -> None:
        """Establece el nivel activo (1 o 2)."""
        if level in [1, 2]:
            self.active_level = level
            if self.evaluator:
                self.evaluator.active_level = level
            self.reset()
            logger.info(f"AutomaticLSMClassifier: Nivel activo establecido en {self.active_level}")

    def set_target_sign(self, sign: Optional[str]) -> None:
        """Establece la seña objetivo o None para modo automático multiclase."""
        if sign:
            clean_sign = sign.upper()
            self.target_sign = clean_sign
            self.evaluator.set_target_sign(self.target_sign)
            if clean_sign in self.LEVEL_1_SIGNS:
                self.active_level = 1
            elif clean_sign in self.LEVEL_2_SIGNS:
                self.active_level = 2
        else:
            self.target_sign = None

    def reset(self) -> None:
        """Reinicia el histórico de suavizado temporal."""
        self.history.clear()
        self.stable_sign = None
        self.stable_score = 0.0
        self.stable_count = 0

    def classify(
        self,
        fused_state: Dict[str, Any],
        target_sign: Optional[str] = None,
        level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Clasifica la postura/movimiento de la mano separando estrictamente por nivel o evaluando
        únicamente la seña objetivo en modo target explícito.
        """
        has_vision = fused_state.get("vision_present", False)
        raw_landmarks = fused_state.get("raw_landmarks", [])
        active_target = (target_sign or self.target_sign)

        # Determinar nivel efectivo
        if active_target:
            t_upper = active_target.upper()
            if t_upper in self.LEVEL_2_SIGNS:
                eff_level = 2
            elif t_upper in self.LEVEL_1_SIGNS:
                eff_level = 1
            else:
                eff_level = level or self.active_level
        else:
            eff_level = level or self.active_level

        candidate_list = self.LEVEL_1_SIGNS if eff_level == 1 else self.LEVEL_2_SIGNS

        # 1. Comprobar presencia de mano real
        if not has_vision or not raw_landmarks or len(raw_landmarks) < 21:
            self.history.append(None)
            none_count = sum(1 for p in self.history if p is None)
            if none_count >= 4:
                self.stable_sign = None
                self.stable_score = 0.0
                self.stable_count = 0

            return {
                "detected": False,
                "predicted_sign": None,
                "stable_sign": None,
                "score": 0.0,
                "margin": 0.0,
                "confidence": 0.0,
                "status": "NO_HAND",
                "candidate_scores": {s: 0.0 for s in candidate_list},
                "best_candidate": None,
                "second_candidate": None,
                "stable_count": 0,
                "diagnostics": {"finger_states": {}}
            }

        # Extraer estados anatómicos individuales de dedos para diagnóstico
        handedness = fused_state.get("handedness", "Right")
        from .geometry import HandGeometryFeatures
        geom = HandGeometryFeatures(raw_landmarks, handedness=handedness)
        finger_states = geom.get_finger_extension_states()

        # =========================================================================
        # REQUISITO 4: MODO TARGET EXPLÍCITO (evalúa ÚNICAMENTE target_sign, sin multiclase)
        # =========================================================================
        if active_target:
            t_sign = active_target.upper()
            eval_res = self.evaluator.evaluate(fused_state, target_sign=t_sign)
            is_valid = eval_res.get("is_valid", False)
            score = float(eval_res.get("overall_score", 0.0))
            reason = eval_res.get("message", "")
            params = eval_res.get("parameters", {})

            # Caso Nivel 2 en target explícito
            if t_sign in self.LEVEL_2_SIGNS:
                dyn_status = eval_res.get("dynamic_status", "PREPARING")
                final_status = "RECOGNIZED" if is_valid else dyn_status
                out_sign = t_sign if is_valid else None
                out_score = score if is_valid else 0.0
                scores = {s: (score if s == t_sign else 0.0) for s in self.LEVEL_2_SIGNS}

                diag = eval_res.get("diagnostics", {})
                diag["finger_states"] = finger_states
                diag["level"] = 2
                diag["best_candidate"] = t_sign
                diag["best_score"] = round(score, 3)
                diag["second_candidate"] = None
                diag["second_score"] = 0.0
                diag["margin"] = 1.0 if is_valid else 0.0
                diag["stable_count"] = 10 if is_valid else 0

                return {
                    "detected": True,
                    "predicted_sign": out_sign,
                    "stable_sign": out_sign,
                    "score": round(out_score, 3),
                    "margin": 1.0 if is_valid else 0.0,
                    "confidence": round(score, 3),
                    "status": final_status,
                    "candidate_scores": scores,
                    "best_candidate": t_sign,
                    "second_candidate": None,
                    "stable_count": 10 if is_valid else 0,
                    "diagnostics": diag,
                    "message": reason
                }

            # Caso Nivel 1 en target explícito (A, B, C, L, Y)
            if is_valid and score >= self.threshold:
                instant_pred = t_sign
                instant_status = "RECOGNIZED"
            elif score >= 0.65:
                instant_pred = None
                c_stat = params.get("configuration", {}).get("status", "FAIL")
                o_stat = params.get("orientation", {}).get("status", "FAIL")
                instant_status = "CORRECT" if (c_stat == "CORRECT" or o_stat == "CORRECT") else "AMBIGUOUS"
            else:
                instant_pred = None
                instant_status = "HAND_DETECTED"

            # Suavizado temporal de 7 frames para Nivel 1
            self.history.append(instant_pred)
            match_count = sum(1 for item in self.history if item == t_sign)
            if match_count >= 4:
                if self.stable_sign != t_sign:
                    self.stable_sign = t_sign
                    self.stable_count = 1
                else:
                    self.stable_count += 1
                self.stable_score = score
                final_status = "RECOGNIZED"
                out_sign = t_sign
                out_score = self.stable_score
            else:
                none_count = sum(1 for p in self.history if p is None)
                if none_count >= 5:
                    self.stable_sign = None
                    self.stable_score = 0.0
                    self.stable_count = 0
                final_status = instant_status
                out_sign = self.stable_sign
                out_score = self.stable_score if out_sign else 0.0

            scores = {s: (round(score, 3) if s == t_sign else 0.0) for s in self.LEVEL_1_SIGNS}
            diag = eval_res.get("diagnostics", {})
            diag["finger_states"] = finger_states
            diag["level"] = 1
            diag["best_candidate"] = t_sign
            diag["best_score"] = round(score, 3)
            diag["second_candidate"] = None
            diag["second_score"] = 0.0
            diag["margin"] = 1.0 if is_valid else 0.0
            diag["stable_count"] = self.stable_count

            # Diagnóstico específico si es A
            if t_sign == "A":
                c_score = params.get("configuration", {}).get("score", 0.0)
                o_score = params.get("orientation", {}).get("score", 0.0)
                diag["a_details"] = {
                    "config_score": round(c_score, 3),
                    "orientation_score": round(o_score, 3),
                    "overall_score": round(score, 3),
                    "is_valid": is_valid,
                    "reason": reason
                }

            return {
                "detected": True,
                "predicted_sign": instant_pred,
                "stable_sign": out_sign,
                "score": round(out_score, 3),
                "margin": 1.0 if is_valid else 0.0,
                "confidence": round(score, 3),
                "status": final_status,
                "candidate_scores": scores,
                "best_candidate": t_sign,
                "second_candidate": None,
                "stable_count": self.stable_count,
                "diagnostics": diag,
                "message": reason
            }

        # =========================================================================
        # REQUISITO 2: MODO AUTOMÁTICO NIVEL 1 (evalúa SOLO A, B, C, L, Y)
        # =========================================================================
        if eff_level == 1:
            scores: Dict[str, float] = {}
            eval_results: Dict[str, Any] = {}
            for s in self.LEVEL_1_SIGNS:
                res_s = self.evaluator.evaluate(fused_state, target_sign=s)
                scores[s] = float(res_s.get("overall_score", 0.0))
                eval_results[s] = res_s

            # Ordenar candidatos exclusivamente de Nivel 1
            sorted_candidates = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            best_sign, best_score = sorted_candidates[0]
            second_sign, second_score = sorted_candidates[1]
            margin = best_score - second_score

            # Regla de decisión instantánea con threshold=0.78 y margin=0.08
            instant_pred: Optional[str] = None
            if best_score >= self.threshold and margin >= self.margin:
                instant_pred = best_sign
                instant_status = "RECOGNIZED"
            elif best_score >= 0.65:
                instant_pred = None
                instant_status = "AMBIGUOUS"
            else:
                instant_pred = None
                instant_status = "HAND_DETECTED"

            # Suavizado temporal: ventana de 7 frames, requiere 4
            self.history.append(instant_pred)
            counts: Dict[str, int] = {}
            for item in self.history:
                if item is not None:
                    counts[item] = counts.get(item, 0) + 1

            promoted_sign: Optional[str] = None
            for sign_cand, cnt in counts.items():
                if cnt >= 4:
                    promoted_sign = sign_cand
                    break

            if promoted_sign is not None:
                if self.stable_sign != promoted_sign:
                    self.stable_sign = promoted_sign
                    self.stable_count = 1
                else:
                    self.stable_count += 1
                self.stable_score = scores.get(promoted_sign, best_score)
            else:
                none_count = sum(1 for p in self.history if p is None)
                if none_count >= 5:
                    self.stable_sign = None
                    self.stable_score = 0.0
                    self.stable_count = 0

            if self.stable_sign is not None:
                final_status = "RECOGNIZED"
                out_sign = self.stable_sign
                out_score = self.stable_score
            elif best_score >= 0.65:
                final_status = "AMBIGUOUS"
                out_sign = None
                out_score = 0.0
            else:
                final_status = "HAND_DETECTED"
                out_sign = None
                out_score = 0.0

            # Diagnóstico exigido para Nivel 1 (Requisitos 7 y 8)
            diag = eval_results.get(best_sign, {}).get("diagnostics", {})
            diag["finger_states"] = finger_states
            diag["level"] = 1
            diag["best_candidate"] = best_sign
            diag["best_score"] = round(best_score, 3)
            diag["second_candidate"] = second_sign
            diag["second_score"] = round(second_score, 3)
            diag["margin"] = round(margin, 3)
            diag["stable_count"] = self.stable_count

            # Diagnóstico para A
            a_res = eval_results.get("A", {})
            a_params = a_res.get("parameters", {})
            a_cfg = a_params.get("configuration", {})
            a_ori = a_params.get("orientation", {})
            diag["a_details"] = {
                "config_score": round(a_cfg.get("score", 0.0), 3),
                "orientation_score": round(a_ori.get("score", 0.0), 3),
                "overall_score": round(scores.get("A", 0.0), 3),
                "is_valid": a_res.get("is_valid", False),
                "reason": a_res.get("message", "")
            }

            logger.debug(
                f"[NIVEL 1 AUTO] best={best_sign} ({best_score:.3f}), 2nd={second_sign} ({second_score:.3f}), "
                f"margin={margin:.3f}, stable={self.stable_count}, fingers={finger_states}"
            )
            a_d = diag["a_details"]
            logger.debug(
                f"[DIAG A] cfg={a_d['config_score']:.3f}, ori={a_d['orientation_score']:.3f}, "
                f"tot={a_d['overall_score']:.3f}, valid={a_d['is_valid']}, reason='{a_d['reason']}'"
            )

            return {
                "detected": True,
                "predicted_sign": instant_pred,
                "stable_sign": out_sign,
                "score": round(out_score, 3),
                "margin": round(margin, 3),
                "confidence": round(out_score if out_sign else best_score, 3),
                "status": final_status,
                "candidate_scores": {k: round(v, 3) for k, v in scores.items()},
                "best_candidate": best_sign,
                "second_candidate": second_sign,
                "stable_count": self.stable_count,
                "diagnostics": diag,
                "message": eval_results.get(best_sign, {}).get("message", "")
            }

        # =========================================================================
        # REQUISITO 3: MODO AUTOMÁTICO NIVEL 2 (evalúa SOLO J, Ñ, Q, X, Z)
        # =========================================================================
        scores: Dict[str, float] = {}
        eval_results: Dict[str, Any] = {}
        for s in self.LEVEL_2_SIGNS:
            res_s = self.evaluator.evaluate(fused_state, target_sign=s)
            scores[s] = float(res_s.get("overall_score", 0.0))
            eval_results[s] = res_s

        sorted_candidates = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_sign, best_score = sorted_candidates[0]
        second_sign, second_score = sorted_candidates[1]
        margin = best_score - second_score

        best_res = eval_results[best_sign]
        is_dyn_valid = best_res.get("is_valid", False)
        dyn_status = best_res.get("dynamic_status", "PREPARING")

        if is_dyn_valid and best_score >= self.threshold and margin >= self.margin:
            final_status = "RECOGNIZED"
            out_sign = best_sign
            out_score = best_score
        else:
            final_status = dyn_status if is_dyn_valid or dyn_status != "RECOGNIZED" else "MOVING"
            out_sign = None
            out_score = 0.0

        diag = best_res.get("diagnostics", {})
        diag["finger_states"] = finger_states
        diag["level"] = 2
        diag["best_candidate"] = best_sign
        diag["best_score"] = round(best_score, 3)
        diag["second_candidate"] = second_sign
        diag["second_score"] = round(second_score, 3)
        diag["margin"] = round(margin, 3)
        diag["stable_count"] = 10 if is_dyn_valid else 0

        return {
            "detected": True,
            "predicted_sign": out_sign,
            "stable_sign": out_sign,
            "score": round(out_score, 3),
            "margin": round(margin, 3),
            "confidence": round(best_score, 3),
            "status": final_status,
            "candidate_scores": {k: round(v, 3) for k, v in scores.items()},
            "best_candidate": best_sign,
            "second_candidate": second_sign,
            "stable_count": 10 if is_dyn_valid else 0,
            "diagnostics": diag,
            "message": best_res.get("message", "")
        }
