"""
Pruebas unitarias para AutomaticLSMClassifier (LSM Nivel 1).
Verifica:
- Clasificación de señas canónicas A, B, L
- Filtrado temporal anti-flicker (ventana de 7 frames, 4 requeridos para transición)
- Distinción entre NO_HAND, HAND_DETECTED, AMBIGUOUS y RECOGNIZED
- Margin y threshold
"""

import pytest
from src.lsm.classifier import AutomaticLSMClassifier
from src.lsm.evaluator import LSMEvaluator
from tests.test_lsm_geometric import make_landmarks_fist_a, make_landmarks_flat_hand_b, make_landmarks_l_shape


def test_classifier_initialization():
    clf = AutomaticLSMClassifier(threshold=0.78, margin=0.08, window_size=7)
    assert clf.SIGNS == ["A", "B", "C", "L", "Y"]
    assert clf.threshold == 0.78
    assert clf.margin == 0.08
    assert clf.window_size == 7
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
    for s in ["A", "B", "C", "L", "Y"]:
        assert res["candidate_scores"][s] == 0.0


def test_classifier_sign_a_recognition():
    clf = AutomaticLSMClassifier(threshold=0.75, margin=0.05)
    pts_a = make_landmarks_fist_a()
    state = {"vision_present": True, "raw_landmarks": pts_a}

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

    state_a = {"vision_present": True, "raw_landmarks": pts_a}
    state_b = {"vision_present": True, "raw_landmarks": pts_b}

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
    state = {"vision_present": True, "raw_landmarks": pts_a}

    for _ in range(5):
        res = clf.classify(state)

    # Al no superar el margen/umbral estricto, no debe declarar RECOGNIZED
    assert res["predicted_sign"] is None
    assert res["stable_sign"] is None
    assert res["status"] in ["AMBIGUOUS", "HAND_DETECTED"]
