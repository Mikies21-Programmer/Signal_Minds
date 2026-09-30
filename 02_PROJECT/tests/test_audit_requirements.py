"""
Pruebas obligatorias de la Auditoría Z.ai para sustitución de MPU6050 por
Orientación Visual + Sensor de Distancia Ultrasónico.

Cubre exhaustivamente los requisitos de la Sección 10:
1. A sin IMU
2. B sin IMU
3. C sin IMU
4. L sin IMU
5. Y sin IMU
6. A incorrecta (rechazo)
7. Orientación visual PALM
8. Orientación visual BACK
9. Orientación visual SIDE
10. Orientación visual UNKNOWN (score neutro, no bloquea)
11. Ultrasónico valid
12. Ultrasónico invalid
13. Ultrasónico disconnected
14. Q: rotación visual suficiente
15. Q: rotación visual insuficiente
16. Nivel 1 aislado: A/B/C/L/Y
17. Nivel 2 aislado: J/Ñ/Q/X/Z
18. NO crossover entre niveles
"""

import math
import pytest
from src.lsm.geometry import (
    HandGeometryFeatures,
    get_hand_orientation_visual,
    OrientationEstimator
)
from src.lsm.evaluator import LSMEvaluator
from src.lsm.classifier import AutomaticLSMClassifier
from src.sensors.ultrasonic import DistanceReading
from tests.test_lsm_geometric import (
    make_landmarks_fist_a,
    make_landmarks_flat_hand_b,
    make_landmarks_c_shape,
    make_landmarks_l_shape,
    make_landmarks_y_shape,
    make_landmarks_open_hand
)
from tests.test_dynamic import make_landmarks_q_base


# =============================================================================
# 1. EVALUACIÓN DE NIVEL 1 SIN IMU (A, B, C, L, Y)
# =============================================================================

def test_a_sin_imu():
    """Seña 'A' se evalúa y aprueba sin presencia ni dependencia funcional de IMU."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "handedness": "Right"
        # Sin imu_present, sin roll, sin pitch, sin yaw, sin tilt_error
    }
    res = evaluator.evaluate(state, target_sign="A")
    assert res["is_valid"] is True
    assert res["sign"] == "A"
    assert res["overall_score"] >= evaluator.threshold
    assert "tilt_error" not in res["parameters"]["orientation"]


def test_b_sin_imu():
    """Seña 'B' se evalúa y aprueba sin presencia ni dependencia funcional de IMU."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_flat_hand_b(),
        "handedness": "Right"
    }
    res = evaluator.evaluate(state, target_sign="B")
    assert res["is_valid"] is True
    assert res["sign"] == "B"
    assert res["overall_score"] >= evaluator.threshold


def test_c_sin_imu():
    """Seña 'C' se evalúa y aprueba sin presencia ni dependencia funcional de IMU."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_c_shape(),
        "handedness": "Right"
    }
    res = evaluator.evaluate(state, target_sign="C")
    assert res["is_valid"] is True
    assert res["sign"] == "C"
    assert res["overall_score"] >= evaluator.threshold


def test_l_sin_imu():
    """Seña 'L' se evalúa y aprueba sin presencia ni dependencia funcional de IMU."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_l_shape(),
        "handedness": "Right"
    }
    res = evaluator.evaluate(state, target_sign="L")
    assert res["is_valid"] is True
    assert res["sign"] == "L"
    assert res["overall_score"] >= evaluator.threshold


def test_y_sin_imu():
    """Seña 'Y' se evalúa y aprueba sin presencia ni dependencia funcional de IMU."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_y_shape(),
        "handedness": "Right"
    }
    res = evaluator.evaluate(state, target_sign="Y")
    assert res["is_valid"] is True
    assert res["sign"] == "Y"
    assert res["overall_score"] >= evaluator.threshold


def test_a_incorrecta_rechazada():
    """Una postura errónea (mano abierta pretendiendo ser 'A') es categóricamente rechazada."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_open_hand(),
        "handedness": "Right"
    }
    res = evaluator.evaluate(state, target_sign="A")
    assert res["is_valid"] is False
    assert res["overall_score"] < evaluator.threshold
    assert res["parameters"]["configuration"]["status"] == "CORRECT" or res["parameters"]["configuration"]["score"] < 0.70


# =============================================================================
# 2. ORIENTACIÓN VISUAL (PALM, BACK, SIDE, UNKNOWN)
# =============================================================================

def test_visual_orientation_palm():
    """Landmarks canónicos frontales estiman orientación PALM con confianza positiva."""
    lms = make_landmarks_fist_a()
    res = get_hand_orientation_visual(lms, handedness="Right", orientation_invert=False)
    assert res["orientation"] == "PALM"
    assert res["confidence"] > 0.60
    assert "signed_cross" in res


def test_visual_orientation_back_and_invert():
    """Verifica orientación BACK y calibración de inversión física (orientation_invert)."""
    lms = make_landmarks_fist_a()
    # Con orientation_invert=True, el signo se invierte a BACK
    res_inv = get_hand_orientation_visual(lms, handedness="Right", orientation_invert=True)
    assert res_inv["orientation"] == "BACK"

    # Evaluador con orientación BACK para seña A penaliza pero reporta estado BACK
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": lms,
        "handedness": "Right",
        "orientation": "BACK"
    }
    res_eval = evaluator.evaluate_orientation("A", state)
    assert res_eval["orientation_state"] == "BACK"
    assert res_eval["score"] <= 0.40
    assert res_eval["status"] == "FAIL"


def test_visual_orientation_side():
    """Landmarks comprimidos lateralmente clasifican como SIDE (perfil)."""
    # Crear landmarks colapsados en eje X para simular mano de perfil
    side_lms = [{"id": i, "x": 0.50 + 0.005 * (i % 3), "y": 0.3 + 0.02 * i, "z": 0.0} for i in range(21)]
    res = get_hand_orientation_visual(side_lms, handedness="Right")
    assert res["orientation"] == "SIDE"

    # En seña C, la orientación SIDE es completamente aceptada (score 1.0)
    evaluator = LSMEvaluator()
    eval_c = evaluator.evaluate_orientation("C", {"orientation": "SIDE"})
    assert eval_c["orientation_state"] == "SIDE"
    assert eval_c["score"] == 1.0
    assert eval_c["status"] == "PASS"


def test_visual_orientation_unknown():
    """Orientación UNKNOWN proporciona score neutro y NO bloquea una seña morfológicamente correcta."""
    res = get_hand_orientation_visual([], handedness="Right")
    assert res["orientation"] == "UNKNOWN"

    evaluator = LSMEvaluator()
    eval_res = evaluator.evaluate_orientation("A", {"orientation": "UNKNOWN"})
    assert eval_res["orientation_state"] == "UNKNOWN"
    assert eval_res["score"] == 0.75
    assert eval_res["status"] == "NEUTRAL"

    # Seña A con UNKNOWN orientation debe ser válida si los dedos son correctos
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "handedness": "Right",
        "orientation": "UNKNOWN"
    }
    res_a = evaluator.evaluate(state, target_sign="A")
    assert res_a["is_valid"] is True


# =============================================================================
# 3. ULTRASÓNICO (VALID, INVALID, DISCONNECTED)
# =============================================================================

def test_ultrasonic_valid():
    """Lectura ultrasónica válida dentro de rango produce status PASS y score 1.0."""
    evaluator = LSMEvaluator({"sensors": {"distance_min_cm": 20.0, "distance_max_cm": 100.0}})
    state = {
        "distance_valid": True,
        "distance_cm": 45.0,
        "sensor_connected": True
    }
    us_eval = evaluator.evaluate_ultrasonic(state)
    assert us_eval["status"] == "PASS"
    assert us_eval["score"] == 1.0
    assert us_eval["distance_cm"] == 45.0
    assert us_eval["distance_valid"] is True


def test_ultrasonic_invalid():
    """Lectura ultrasónica fuera de rango (< 20 cm o > 100 cm) produce advertencia pero no destruye evaluación."""
    evaluator = LSMEvaluator({"sensors": {"distance_min_cm": 20.0, "distance_max_cm": 100.0}})
    state = {
        "distance_valid": True,
        "distance_cm": 12.0,  # Demasiado cerca (< 20 cm)
        "sensor_connected": True
    }
    us_eval = evaluator.evaluate_ultrasonic(state)
    assert us_eval["status"] == "CORRECT"
    assert us_eval["score"] == 0.60
    assert "próxima" in us_eval["reason"].lower()


def test_ultrasonic_disconnected():
    """Sensor ultrasónico desconectado proporciona score neutro (0.85) y NO destruye una letra correcta."""
    evaluator = LSMEvaluator()
    state = {
        "distance_valid": False,
        "distance_cm": None,
        "sensor_connected": False
    }
    us_eval = evaluator.evaluate_ultrasonic(state)
    assert us_eval["status"] == "NEUTRAL"
    assert us_eval["score"] == 0.85
    assert us_eval["distance_valid"] is False

    # Letra A con sensor desconectado sigue evaluando y aprobando por visión
    full_state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "handedness": "Right",
        "distance_valid": False,
        "distance_cm": None,
        "sensor_connected": False
    }
    res_a = evaluator.evaluate(full_state, target_sign="A")
    assert res_a["is_valid"] is True
    assert res_a["parameters"]["location"]["status"] == "NEUTRAL"


# =============================================================================
# 4. SEÑA Q: ROTACIÓN VISUAL SUFICIENTE VS INSUFICIENTE
# =============================================================================

def test_q_rotacion_visual_suficiente():
    """Q con rotación angular visual de muñeca >= 7.0° es reconocida exitosamente."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Q")
    t0 = 1000.0

    res = None
    for i in range(14):
        angle_rad = math.radians(i * 1.5)  # 0 a 19.5 grados de rotación
        base_lms = make_landmarks_q_base()
        rotated_lms = []
        wx, wy = base_lms[0]["x"], base_lms[0]["y"]
        for p in base_lms:
            dx = p["x"] - wx
            dy = p["y"] - wy
            rx = wx + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            ry = wy + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
            rotated_lms.append({"id": p["id"], "x": rx, "y": ry, "z": p["z"]})

        state = {
            "vision_present": True,
            "raw_landmarks": rotated_lms,
            "handedness": "Right",
            "timestamp": t0 + i * 0.05
        }
        res = evaluator.evaluate(state, target_sign="Q")

    assert res is not None
    assert res["is_valid"] is True
    assert res["dynamic_status"] == "RECOGNIZED"
    assert res["trajectory_metrics"]["visual_rotation_change_deg"] >= 7.0


def test_q_rotacion_visual_insuficiente():
    """Q estática (sin rotación visual angular) es rechazada."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Q")
    t0 = 1000.0

    res = None
    for i in range(14):
        state = {
            "vision_present": True,
            "raw_landmarks": make_landmarks_q_base(),  # Estático sin rotación
            "handedness": "Right",
            "timestamp": t0 + i * 0.05
        }
        res = evaluator.evaluate(state, target_sign="Q")

    assert res is not None
    assert res["is_valid"] is False
    assert res["dynamic_status"] in ["PREPARING", "NO_MOTION", "EVALUATING", "MOVING"]
    assert res["trajectory_metrics"]["visual_rotation_change_deg"] < 7.0


# =============================================================================
# 5. AISLAMIENTO POR NIVELES (NIVEL 1 VS NIVEL 2, SIN CROSSOVER)
# =============================================================================

def test_nivel_1_aislado():
    """En Nivel 1 activo, el clasificador evalúa SOLO A, B, C, L, Y."""
    classifier = AutomaticLSMClassifier(active_level=1)
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "handedness": "Right"
    }
    res = classifier.classify(state)
    assert set(res["candidate_scores"].keys()) == set(AutomaticLSMClassifier.LEVEL_1_SIGNS)
    for s in AutomaticLSMClassifier.LEVEL_2_SIGNS:
        assert s not in res["candidate_scores"]


def test_nivel_2_aislado():
    """En Nivel 2 activo, el clasificador evalúa SOLO J, Ñ, Q, X, Z."""
    classifier = AutomaticLSMClassifier(active_level=2)
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_q_base(),
        "handedness": "Right"
    }
    res = classifier.classify(state)
    assert set(res["candidate_scores"].keys()) == set(AutomaticLSMClassifier.LEVEL_2_SIGNS)
    for s in AutomaticLSMClassifier.LEVEL_1_SIGNS:
        assert s not in res["candidate_scores"]


def test_no_crossover_entre_niveles():
    """Garantiza que no hay contaminación cruzada de candidatos ni márgenes entre niveles."""
    classifier_l1 = AutomaticLSMClassifier(active_level=1)
    classifier_l2 = AutomaticLSMClassifier(active_level=2)

    # Nivel 1 nunca produce signos de Nivel 2 en predicción
    state_a = {"vision_present": True, "raw_landmarks": make_landmarks_fist_a(), "handedness": "Right"}
    for _ in range(8):
        res1 = classifier_l1.classify(state_a)
    if res1["stable_sign"]:
        assert res1["stable_sign"] in AutomaticLSMClassifier.LEVEL_1_SIGNS
        assert res1["stable_sign"] not in AutomaticLSMClassifier.LEVEL_2_SIGNS

    # Nivel 2 nunca produce signos de Nivel 1 en predicción
    state_q = {"vision_present": True, "raw_landmarks": make_landmarks_q_base(), "handedness": "Right"}
    for _ in range(8):
        res2 = classifier_l2.classify(state_q)
    if res2["stable_sign"]:
        assert res2["stable_sign"] in AutomaticLSMClassifier.LEVEL_2_SIGNS
        assert res2["stable_sign"] not in AutomaticLSMClassifier.LEVEL_1_SIGNS
