"""
Clasificador automático de Lengua de Señas Mexicana (LSM) Nivel 1.
Evalúa landmarks anatómicos reales contra el conjunto de candidatos canónicos: A, B, C, L, Y.
Aplica umbral estricto (>= 0.78), margen de desempate (>= 0.08) y filtrado temporal (cola de 7 frames)
para evitar falsos positivos y parpadeos espurios.
"""

from collections import deque
from typing import Dict, Any, Optional, List
from .evaluator import LSMEvaluator
from ..backend.logger import get_logger

logger = get_logger("classifier")


class AutomaticLSMClassifier:
    """Clasificador multiclase automático para el alfabeto LSM Nivel 1 y Nivel 2 dinámico."""

    SIGNS: List[str] = [
        "A", "B", "C", "L", "Y",
        "J", "Ñ", "Q", "X", "Z"
    ]
    LEVEL_1_SIGNS: List[str] = ["A", "B", "C", "L", "Y"]
    LEVEL_2_SIGNS: List[str] = ["J", "Ñ", "Q", "X", "Z"]

    def __init__(
        self,
        evaluator: Optional[LSMEvaluator] = None,
        config: Optional[Any] = None,
        threshold: float = 0.78,
        margin: float = 0.08,
        window_size: int = 7
    ):
        self.evaluator = evaluator or LSMEvaluator(config)
        self.threshold = threshold
        self.margin = margin
        self.window_size = window_size
        self.target_sign: Optional[str] = None

        # Cola de histórico para suavizado temporal de Nivel 1 (7 frames)
        self.history: deque = deque(maxlen=window_size)
        self.stable_sign: Optional[str] = None
        self.stable_score: float = 0.0
        self.stable_count: int = 0

        logger.info(
            f"AutomaticLSMClassifier inicializado: señas={self.SIGNS}, "
            f"umbral={self.threshold}, margen={self.margin}, ventana={self.window_size} frames."
        )

    def set_target_sign(self, sign: Optional[str]) -> None:
        """Establece la seña objetivo o None para modo automático multiclase."""
        if sign:
            self.target_sign = sign.upper()
            self.evaluator.set_target_sign(self.target_sign)
        else:
            self.target_sign = None

    def reset(self) -> None:
        """Reinicia el histórico de suavizado temporal."""
        self.history.clear()
        self.stable_sign = None
        self.stable_score = 0.0
        self.stable_count = 0

    def classify(self, fused_state: Dict[str, Any], target_sign: Optional[str] = None) -> Dict[str, Any]:
        """
        Clasifica la postura/movimiento de la mano para Nivel 1 (estático) o Nivel 2 (dinámico).
        Para señas de Nivel 2, exige ventana temporal (>=10 frames) y nunca reconoce en un solo frame.
        
        Args:
            fused_state: Diccionario con telemetría de fusión y raw_landmarks (21 puntos).
            target_sign: Seña específica opcional a evaluar.
            
        Returns:
            Dict con predicted_sign, stable_sign, candidate_scores, status y score.
        """
        has_vision = fused_state.get("vision_present", False)
        raw_landmarks = fused_state.get("raw_landmarks", [])
        active_target = (target_sign or self.target_sign)

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
                "candidate_scores": {s: 0.0 for s in self.SIGNS},
                "best_candidate": None,
                "second_candidate": None,
                "stable_count": 0
            }

        # CASO A: Seña objetivo explícita de Nivel 2
        if active_target and active_target.upper() in self.LEVEL_2_SIGNS:
            sign_l2 = active_target.upper()
            eval_res = self.evaluator.evaluate(fused_state, target_sign=sign_l2)
            is_valid = eval_res.get("is_valid", False)
            dyn_status = eval_res.get("dynamic_status", "PREPARING")
            score = float(eval_res.get("overall_score", 0.0))

            final_status = "RECOGNIZED" if is_valid else dyn_status
            out_sign = sign_l2 if is_valid else None

            scores = {s: 0.0 for s in self.SIGNS}
            scores[sign_l2] = score

            return {
                "detected": True,
                "predicted_sign": sign_l2 if is_valid else None,
                "stable_sign": out_sign,
                "score": round(score, 3),
                "margin": 1.0 if is_valid else 0.0,
                "confidence": round(score, 3),
                "status": final_status,
                "candidate_scores": scores,
                "best_candidate": sign_l2,
                "second_candidate": None,
                "stable_count": 10 if is_valid else 0,
                "diagnostics": eval_res.get("diagnostics", {}),
                "message": eval_res.get("message", "")
            }

        # CASO B: Modo multiclase / Nivel 1
        scores: Dict[str, float] = {}
        last_diagnostics: Dict[str, Any] = {}
        for s in self.SIGNS:
            eval_res = self.evaluator.evaluate(fused_state, target_sign=s)
            scores[s] = float(eval_res.get("overall_score", 0.0))
            if "diagnostics" in eval_res and not last_diagnostics:
                last_diagnostics = eval_res["diagnostics"]

        # 3. Ordenar candidatos por puntuación descendente
        sorted_candidates = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_sign, best_score = sorted_candidates[0]
        second_sign, second_score = sorted_candidates[1]
        margin = best_score - second_score

        # 4. Regla de decisión instantánea (Nivel 2 exige reconocimiento dinámico completo)
        instant_pred: Optional[str] = None
        instant_status: str = "AMBIGUOUS"

        if best_score >= self.threshold and margin >= self.margin:
            if best_sign in self.LEVEL_2_SIGNS:
                # Nivel 2 solo se predice si el tracker dinámico lo reconoció
                if self.evaluator.dynamic_tracker.state == "RECOGNIZED":
                    instant_pred = best_sign
                    instant_status = "RECOGNIZED"
                else:
                    instant_pred = None
                    instant_status = self.evaluator.dynamic_tracker.state
            else:
                instant_pred = best_sign
                instant_status = "RECOGNIZED"
        else:
            instant_pred = None
            instant_status = "AMBIGUOUS"

        # 5. Suavizado temporal para Nivel 1 (ventana de 7 frames)
        self.history.append(instant_pred)

        # Contar frecuencias de candidatos válidos en la ventana
        counts: Dict[str, int] = {}
        for item in self.history:
            if item is not None:
                counts[item] = counts.get(item, 0) + 1

        # Criterio de transición de estado: requiere al menos 4 de los últimos 7 frames
        promoted_sign: Optional[str] = None
        for sign_candidate, count in counts.items():
            if count >= 4:
                promoted_sign = sign_candidate
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

        # Determinar estado de salida
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

        return {
            "detected": True,
            "predicted_sign": instant_pred,
            "stable_sign": out_sign,
            "score": round(out_score, 3),
            "margin": round(margin, 3),
            "confidence": round(out_score, 3),
            "status": final_status,
            "candidate_scores": {k: round(v, 3) for k, v in scores.items()},
            "best_candidate": best_sign,
            "second_candidate": second_sign,
            "stable_count": self.stable_count,
            "diagnostics": last_diagnostics
        }
