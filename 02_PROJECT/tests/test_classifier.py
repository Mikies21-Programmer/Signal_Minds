"""
Pruebas unitarias para AutomaticLSMClassifier (LSM Nivel 1 y Nivel 2).
Verifica:
- Separación estricta de candidatos por nivel (Nivel 1 vs Nivel 2)
- Una 'A' no puede perder contra X/Q/J/Z
- X/Q/J/Z no aparecen como candidatos en Nivel 1
- Una mano 'A' correcta alcanza RECOGNIZED
- Nivel 2 sigue requiriendo su movimiento dinámico real
- Modo target explícito sin competencia multiclase
- Filtrado temporal anti-flicker (ventana de 7 frames, 4 requeridos para transición)
- Distinción entre NO_HAND, HAND_DETECTED, AMBIGUOUS y RECOGNIZED
"""

import pytest
from src.lsm.classifier import AutomaticLSMClassifier
from src.lsm.evaluator import LSMEvaluator
from tests.test_lsm_geometric import make_landmarks_fist_a, make_landmarks_flat_hand_b, make_landmarks_l_shape


def test_classifier_initialization():
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08, window_size=7)
    assert clf.SIGNS == ["A", "B", "C", "L", "Y", "J", "Ñ", "Q", "X", "Z"]
    assert clf.LEVEL_1_SIGNS == ["A", "B", "C", "L", "Y"]
    assert clf.LEVEL_2_SIGNS == ["J", "Ñ", "Q", "X", "Z"]
    assert clf.threshold == 0.78
    assert clf.margin == 0.08
    assert clf.window_size == 7
    assert clf.active_level == 1
    assert clf.stable_sign is None


def test_classifier_no_hand():
    clf = AutomaticLSMClassifier()
    state = {"vision_present": False, "raw_landmarks": []}
    res = clf.classify(state)

    assert res["detected"] is False
    assert res["predicted_sign"] is None
    assert res["stable_sign"] is None
    assert res["status"] == "NO_HAND"
    assert res["score"] == 0.0
    # En Nivel 1 (por defecto), solo candidatos de Nivel 1
    assert list(res["candidate_scores"].keys()) == ["A", "B", "C", "L", "Y"]
    for s in ["A", "B", "C", "L", "Y"]:
        assert res["candidate_scores"][s] == 0.0


def test_classifier_no_hand_level2():
    clf = AutomaticLSMClassifier(active_level=2)
    state = {"vision_present": False, "raw_landmarks": []}
    res = clf.classify(state)

    assert res["status"] == "NO_HAND"
    assert list(res["candidate_scores"].keys()) == ["J", "Ñ", "Q", "X", "Z"]


def make_multimodal_state(landmarks, tilt_error=2.0):
    return {
        "vision_present": True,
        "raw_landmarks": landmarks,
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "staleness": {"sensor_stale": False},
        "hand_orientation": {
            "imu_present": True,
            "sensor_type": "MPU6050",
            "tilt_error": tilt_error
        },
        "sensor_telemetry": {
            "is_connected": True,
            "imu_roll_deg": 1.0,
            "imu_pitch_deg": 1.0,
            "tilt_error_deg": tilt_error
        }
    }


def test_classifier_sign_a_recognition():
    clf = AutomaticLSMClassifier(threshold=0.75, margin=0.05)
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=2.0)

    # Primer frame: instant_pred es A, pero stable_sign aún no hasta acumular historia
    res1 = clf.classify(state)
    assert res1["detected"] is True
    assert res1["candidate_scores"]["A"] > 0.75
    assert res1["best_candidate"] == "A"

    # Enviar 3 frames adicionales (total 4 frames de A)
    for _ in range(3):
        res = clf.classify(state)

    # Ahora debe haberse estabilizado
    assert res["stable_sign"] == "A"
    assert res["status"] == "RECOGNIZED"
    assert res["score"] > 0.75


def test_temporal_smoothing_anti_flicker():
    clf = AutomaticLSMClassifier(threshold=0.75, margin=0.05, window_size=7)
    pts_a = make_landmarks_fist_a()
    pts_b = make_landmarks_flat_hand_b()

    state_a = make_multimodal_state(pts_a, tilt_error=2.0)
    state_b = make_multimodal_state(pts_b, tilt_error=2.0)

    # Establecer postura A durante 5 frames
    for _ in range(5):
        clf.classify(state_a)

    assert clf.stable_sign == "A"

    # 1 solo frame espurio de B NO debe cambiar el stable_sign
    res_glitch = clf.classify(state_b)
    assert res_glitch["predicted_sign"] == "B"  # instantáneo detecta B
    assert res_glitch["stable_sign"] == "A"     # pero el estable se mantiene en A

    # Ahora enviar B persistentemente (3 frames más para sumar 4 de B)
    for _ in range(3):
        res_stable = clf.classify(state_b)

    # Ahora sí debe haber transitado a B
    assert res_stable["stable_sign"] == "B"
    assert res_stable["status"] == "RECOGNIZED"


def test_ambiguous_rejection():
    clf = AutomaticLSMClassifier(threshold=0.99, margin=0.50)  # Umbrales inalcanzables deliberadamente
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=2.0)

    for _ in range(5):
        res = clf.classify(state)

    # Al no superar el margen/umbral estricto, no debe declarar RECOGNIZED
    assert res["predicted_sign"] is None
    assert res["stable_sign"] is None
    assert res["status"] in ["AMBIGUOUS", "HAND_DETECTED"]


# =========================================================================
# REQUISITO 9: PRUEBAS OBLIGATORIAS DE AUDITORÍA Y REGRESIÓN
# =========================================================================

def test_a_cannot_lose_against_level2_signs():
    """
    Demuestra que una mano 'A' no puede perder ni ser perjudicada por X/Q/J/Z.
    En Nivel 1 automático, el margen se calcula exclusivamente contra candidatos de Nivel 1.
    """
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08)
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=3.0)

    res = clf.classify(state)
    assert res["best_candidate"] == "A"
    assert res["second_candidate"] in ["B", "C", "L", "Y"]
    assert res["second_candidate"] not in ["J", "Ñ", "Q", "X", "Z"]
    assert res["margin"] >= 0.08
    assert res["predicted_sign"] == "A"


def test_level2_signs_do_not_appear_as_candidates_in_level1():
    """
    Demuestra que X/Q/J/Z no aparecen en candidate_scores durante Nivel 1.
    """
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08)
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=3.0)

    res = clf.classify(state)
    candidate_keys = list(res["candidate_scores"].keys())
    assert candidate_keys == ["A", "B", "C", "L", "Y"]
    for l2_sign in ["J", "Ñ", "Q", "X", "Z"]:
        assert l2_sign not in candidate_keys


def test_correct_a_hand_reaches_recognized():
    """
    Demuestra que una mano A correcta alcanza RECOGNIZED si cumple sus condiciones anatómicas e IMU.
    Incluye los diagnósticos de A exigidos por el requisito 7 y 8.
    """
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08, window_size=7)
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=2.5)

    # 4 frames consecutivos de A correcta
    for _ in range(4):
        res = clf.classify(state)

    assert res["status"] == "RECOGNIZED"
    assert res["stable_sign"] == "A"
    assert res["score"] >= 0.78

    # Diagnósticos temporales de Nivel 1 y detalle de A
    diag = res["diagnostics"]
    assert "finger_states" in diag
    assert diag["finger_states"]["index"] is False  # índice flexionado
    assert diag["finger_states"]["pinky"] is False  # meñique flexionado
    assert diag["best_candidate"] == "A"
    assert diag["second_candidate"] in ["B", "C", "L", "Y"]
    assert diag["margin"] >= 0.08

    # Detalle específico de A (Requisito 8)
    assert "a_details" in diag
    a_det = diag["a_details"]
    assert a_det["config_score"] >= 0.75
    assert a_det["orientation_score"] >= 0.65
    assert a_det["overall_score"] >= 0.78
    assert a_det["is_valid"] is True


def test_level2_requires_real_dynamic_movement_in_auto():
    """
    Demuestra que Nivel 2 sigue requiriendo su movimiento dinámico real y
    no se reconoce mediante una sola captura estática en modo automático.
    """
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08, active_level=2)
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=2.5)

    # Una captura estática no puede reconocer una seña dinámica de Nivel 2
    res = clf.classify(state)
    assert res["status"] != "RECOGNIZED"
    assert res["predicted_sign"] is None
    assert list(res["candidate_scores"].keys()) == ["J", "Ñ", "Q", "X", "Z"]


def test_explicit_target_mode_no_multiclass_competition():
    """
    Demuestra que en modo target explícito:
    - Se evalúa únicamente target_sign
    - No hay competencia multiclase (second_candidate es None)
    """
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08)
    pts_a = make_landmarks_fist_a()
    state = make_multimodal_state(pts_a, tilt_error=2.5)

    # Target explícito 'A'
    for _ in range(4):
        res = clf.classify(state, target_sign="A")

    assert res["status"] == "RECOGNIZED"
    assert res["stable_sign"] == "A"
    assert res["best_candidate"] == "A"
    assert res["second_candidate"] is None
    assert res["margin"] == 1.0
