"""
Pruebas del evaluador morfológico geométrico de Lengua de Señas Mexicana (LSM) Nivel 1.
Valida las reglas explicables para A, B, C, L, Y y garantiza que la sola presencia de una mano
no califique como seña correcta si la configuración anatómica no coincide.
"""

from src.lsm.geometry import HandGeometryFeatures, euclidean_distance_3d, angle_between_points_deg
from src.lsm.evaluator import LSMEvaluator


def make_landmarks_fist_a():
    """Genera 21 puntos para seña 'A' (puño cerrado, pulgar al costado)."""
    pts = []
    # Muñeca
    pts.append({"id": 0, "x": 0.5, "y": 0.7, "z": 0.0})
    # Pulgar (extendido/erguido)
    pts.append({"id": 1, "x": 0.46, "y": 0.65, "z": 0.0})
    pts.append({"id": 2, "x": 0.43, "y": 0.58, "z": 0.0})
    pts.append({"id": 3, "x": 0.42, "y": 0.51, "z": 0.0})
    pts.append({"id": 4, "x": 0.42, "y": 0.45, "z": 0.0})
    # Dedos 4 en puño (puntas cerca de la base, doblados hacia abajo)
    for mcp_idx, base_x in [(5, 0.47), (9, 0.50), (13, 0.53), (17, 0.56)]:
        pts.append({"id": mcp_idx, "x": base_x, "y": 0.55, "z": 0.0})
        pts.append({"id": mcp_idx + 1, "x": base_x, "y": 0.50, "z": -0.05})
        pts.append({"id": mcp_idx + 2, "x": base_x, "y": 0.54, "z": -0.05})
        pts.append({"id": mcp_idx + 3, "x": base_x, "y": 0.57, "z": 0.0})  # Punta curled
    return pts


def make_landmarks_flat_hand_b():
    """Genera 21 puntos para seña 'B' (4 dedos extendidos juntos, pulgar flexionado)."""
    pts = []
    pts.append({"id": 0, "x": 0.5, "y": 0.75, "z": 0.0})
    # Pulgar flexionado sobre palma
    pts.append({"id": 1, "x": 0.47, "y": 0.70, "z": 0.0})
    pts.append({"id": 2, "x": 0.48, "y": 0.65, "z": -0.02})
    pts.append({"id": 3, "x": 0.50, "y": 0.62, "z": -0.02})
    pts.append({"id": 4, "x": 0.52, "y": 0.60, "z": -0.01})
    # 4 dedos rectos hacia arriba
    for mcp_idx, base_x in [(5, 0.48), (9, 0.50), (13, 0.52), (17, 0.54)]:
        pts.append({"id": mcp_idx, "x": base_x, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp_idx + 1, "x": base_x, "y": 0.50, "z": 0.0})
        pts.append({"id": mcp_idx + 2, "x": base_x, "y": 0.42, "z": 0.0})
        pts.append({"id": mcp_idx + 3, "x": base_x, "y": 0.35, "z": 0.0})
    return pts


def make_landmarks_l_shape():
    """Genera 21 puntos para seña 'L' (índice arriba, pulgar lateral, otros 3 cerrados)."""
    pts = []
    pts.append({"id": 0, "x": 0.5, "y": 0.75, "z": 0.0})
    # Pulgar extendido horizontalmente hacia la izquierda
    pts.append({"id": 1, "x": 0.46, "y": 0.72, "z": 0.0})
    pts.append({"id": 2, "x": 0.42, "y": 0.70, "z": 0.0})
    pts.append({"id": 3, "x": 0.36, "y": 0.69, "z": 0.0})
    pts.append({"id": 4, "x": 0.30, "y": 0.68, "z": 0.0})
    # Índice extendido hacia arriba
    pts.append({"id": 5, "x": 0.48, "y": 0.60, "z": 0.0})
    pts.append({"id": 6, "x": 0.48, "y": 0.50, "z": 0.0})
    pts.append({"id": 7, "x": 0.48, "y": 0.42, "z": 0.0})
    pts.append({"id": 8, "x": 0.48, "y": 0.35, "z": 0.0})
    # Medio, anular y meñique cerrados
    for mcp_idx, base_x in [(9, 0.52), (13, 0.55), (17, 0.58)]:
        pts.append({"id": mcp_idx, "x": base_x, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp_idx + 1, "x": base_x, "y": 0.55, "z": -0.04})
        pts.append({"id": mcp_idx + 2, "x": base_x, "y": 0.59, "z": -0.04})
        pts.append({"id": mcp_idx + 3, "x": base_x, "y": 0.63, "z": 0.0})
    return pts


def make_landmarks_y_shape():
    """Genera 21 puntos para seña 'Y' (pulgar y meñique extendidos, 3 medios cerrados)."""
    pts = []
    pts.append({"id": 0, "x": 0.5, "y": 0.75, "z": 0.0})
    # Pulgar extendido
    pts.append({"id": 1, "x": 0.45, "y": 0.72, "z": 0.0})
    pts.append({"id": 2, "x": 0.40, "y": 0.70, "z": 0.0})
    pts.append({"id": 3, "x": 0.35, "y": 0.68, "z": 0.0})
    pts.append({"id": 4, "x": 0.30, "y": 0.67, "z": 0.0})
    # Índice, medio y anular cerrados
    for mcp_idx, base_x in [(5, 0.48), (9, 0.51), (13, 0.54)]:
        pts.append({"id": mcp_idx, "x": base_x, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp_idx + 1, "x": base_x, "y": 0.55, "z": -0.04})
        pts.append({"id": mcp_idx + 2, "x": base_x, "y": 0.59, "z": -0.04})
        pts.append({"id": mcp_idx + 3, "x": base_x, "y": 0.63, "z": 0.0})
    # Meñique extendido
    pts.append({"id": 17, "x": 0.57, "y": 0.62, "z": 0.0})
    pts.append({"id": 18, "x": 0.61, "y": 0.55, "z": 0.0})
    pts.append({"id": 19, "x": 0.65, "y": 0.48, "z": 0.0})
    pts.append({"id": 20, "x": 0.70, "y": 0.42, "z": 0.0})
    return pts


def test_hand_geometry_features_finger_extension():
    fist_pts = make_landmarks_fist_a()
    geom_fist = HandGeometryFeatures(fist_pts)
    ext_fist = geom_fist.get_finger_extension_states()

    # En puño, índice, medio, anular y meñique deben ser False
    assert ext_fist["index"] is False
    assert ext_fist["middle"] is False
    assert ext_fist["ring"] is False
    assert ext_fist["pinky"] is False

    flat_pts = make_landmarks_flat_hand_b()
    geom_flat = HandGeometryFeatures(flat_pts)
    ext_flat = geom_flat.get_finger_extension_states()

    # En mano plana, los 4 dedos deben ser True
    assert ext_flat["index"] is True
    assert ext_flat["middle"] is True
    assert ext_flat["ring"] is True
    assert ext_flat["pinky"] is True


def test_evaluator_rejects_wrong_sign_even_if_hand_present():
    """
    CRÍTICO: No afirmar 'seña correcta' solamente porque hay una mano.
    Si la mano hace 'A' (puño), la evaluación para 'B' o 'L' DEBE fallar.
    """
    evaluator = LSMEvaluator()
    fused_state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "hand_orientation": {
            "imu_present": True,
            "sensor_type": "MPU6050",
            "tilt_error": 5.0
        }
    }

    # Evaluar 'A' con puño y orientación válida -> Debe ser correcto
    res_a = evaluator.evaluate(fused_state, target_sign="A")
    assert res_a["is_valid"] is True
    assert res_a["overall_score"] >= 0.75

    # Evaluar 'B' con el mismo puño -> DEBE FALLAR
    res_b = evaluator.evaluate(fused_state, target_sign="B")
    assert res_b["is_valid"] is False
    assert res_b["parameters"]["configuration"]["status"] == "CORRECT"

    # Evaluar 'L' con el mismo puño -> DEBE FALLAR
    res_l = evaluator.evaluate(fused_state, target_sign="L")
    assert res_l["is_valid"] is False


def make_landmarks_open_hand():
    """Genera 21 puntos para palma abierta (pulgar extendido lateralmente, 4 dedos separados)."""
    pts = [{"id": 0, "x": 0.5, "y": 0.75, "z": 0.0}]
    pts.append({"id": 1, "x": 0.44, "y": 0.72, "z": 0.0})
    pts.append({"id": 2, "x": 0.38, "y": 0.68, "z": 0.0})
    pts.append({"id": 3, "x": 0.33, "y": 0.64, "z": 0.0})
    pts.append({"id": 4, "x": 0.28, "y": 0.60, "z": 0.0})  # Pulgar muy separado
    fingers_x = [
        (5, [0.44, 0.42, 0.40, 0.38]),
        (9, [0.49, 0.49, 0.49, 0.49]),
        (13, [0.54, 0.56, 0.58, 0.60]),
        (17, [0.59, 0.63, 0.67, 0.71])
    ]
    for mcp_idx, xs in fingers_x:
        pts.append({"id": mcp_idx, "x": xs[0], "y": 0.60, "z": 0.0})
        pts.append({"id": mcp_idx + 1, "x": xs[1], "y": 0.50, "z": 0.0})
        pts.append({"id": mcp_idx + 2, "x": xs[2], "y": 0.42, "z": 0.0})
        pts.append({"id": mcp_idx + 3, "x": xs[3], "y": 0.35, "z": 0.0})
    return pts


def make_landmarks_c_shape():
    """Genera 21 puntos para seña 'C' (dedos curvados en arco continuo)."""
    pts = [{"id": 0, "x": 0.5, "y": 0.75, "z": 0.0}]
    pts.append({"id": 1, "x": 0.46, "y": 0.70, "z": 0.0})
    pts.append({"id": 2, "x": 0.43, "y": 0.66, "z": -0.02})
    pts.append({"id": 3, "x": 0.43, "y": 0.60, "z": -0.05})
    pts.append({"id": 4, "x": 0.45, "y": 0.55, "z": -0.06})
    for mcp_idx, base_x in [(5, 0.48), (9, 0.50), (13, 0.52), (17, 0.54)]:
        pts.append({"id": mcp_idx, "x": base_x, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp_idx + 1, "x": base_x, "y": 0.51, "z": -0.03})
        pts.append({"id": mcp_idx + 2, "x": base_x - 0.02, "y": 0.46, "z": -0.07})
        pts.append({"id": mcp_idx + 3, "x": base_x - 0.03, "y": 0.49, "z": -0.09})
    return pts


def test_evaluator_l_and_y_signs():
    evaluator = LSMEvaluator()

    orient_ok = {
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "hand_orientation": {
            "imu_present": True,
            "sensor_type": "MPU6050",
            "tilt_error": 5.0
        }
    }

    # Test seña L con orientación válida
    state_l = {"vision_present": True, "raw_landmarks": make_landmarks_l_shape(), **orient_ok}
    res_l = evaluator.evaluate(state_l, target_sign="L")
    assert res_l["is_valid"] is True

    # Test seña Y con orientación válida
    state_y = {"vision_present": True, "raw_landmarks": make_landmarks_y_shape(), **orient_ok}
    res_y = evaluator.evaluate(state_y, target_sign="Y")
    assert res_y["is_valid"] is True


def test_evaluator_rejects_open_hand_for_b():
    """CRÍTICO: B debe rechazar categóricamente una mano abierta."""
    evaluator = LSMEvaluator()
    state_open = {"vision_present": True, "raw_landmarks": make_landmarks_open_hand()}
    res_b = evaluator.evaluate(state_open, target_sign="B")

    assert res_b["is_valid"] is False
    assert res_b["overall_score"] < 0.70
    assert "diagnostics" in res_b
    assert res_b["diagnostics"]["b"]["thumb_fold"] < 40.0


def test_evaluator_c_shape_and_fist_rejection():
    """C debe rechazar puño y mano abierta."""
    evaluator = LSMEvaluator()
    # Puño evaluado para C -> Debe fallar
    state_fist = {"vision_present": True, "raw_landmarks": make_landmarks_fist_a()}
    res_c_fist = evaluator.evaluate(state_fist, target_sign="C")
    assert res_c_fist["is_valid"] is False

    # Mano abierta evaluada para C -> Debe fallar
    state_open = {"vision_present": True, "raw_landmarks": make_landmarks_open_hand()}
    res_c_open = evaluator.evaluate(state_open, target_sign="C")
    assert res_c_open["is_valid"] is False


def test_evaluator_y_rejections():
    """Y debe rechazar mano abierta, L y A."""
    evaluator = LSMEvaluator()
    # Mano abierta no debe pasar Y
    res_open = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_open_hand()}, target_sign="Y")
    assert res_open["is_valid"] is False

    # L no debe pasar Y
    res_l = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_l_shape()}, target_sign="Y")
    assert res_l["is_valid"] is False

    # A (puño) no debe pasar Y
    res_a = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_fist_a()}, target_sign="Y")
    assert res_a["is_valid"] is False


def make_landmarks_a_with_index_extended():
    """Seña A errónea: puño pero con índice extendido (debe rechazarse)."""
    pts = make_landmarks_fist_a()
    # Extender índice (5, 6, 7, 8)
    for p in pts:
        if p["id"] == 6:
            p["y"] = 0.48
            p["z"] = 0.0
        elif p["id"] == 7:
            p["y"] = 0.42
            p["z"] = 0.0
        elif p["id"] == 8:
            p["y"] = 0.35
            p["z"] = 0.0
    return pts


def make_landmarks_a_with_pinky_extended():
    """Seña A errónea: puño pero con meñique extendido (debe rechazarse)."""
    pts = make_landmarks_fist_a()
    # Extender meñique (17, 18, 19, 20)
    for p in pts:
        if p["id"] == 18:
            p["y"] = 0.48
            p["z"] = 0.0
        elif p["id"] == 19:
            p["y"] = 0.42
            p["z"] = 0.0
        elif p["id"] == 20:
            p["y"] = 0.35
            p["z"] = 0.0
    return pts


def make_landmarks_b_with_thumb_extended():
    """Seña B errónea: 4 dedos extendidos pero pulgar extendido al costado."""
    pts = make_landmarks_flat_hand_b()
    for p in pts:
        if p["id"] == 1:
            p["x"] = 0.44
        elif p["id"] == 2:
            p["x"] = 0.38
        elif p["id"] == 3:
            p["x"] = 0.32
        elif p["id"] == 4:
            p["x"] = 0.26
    return pts


def make_landmarks_b_with_splayed_fingers():
    """Seña B errónea: 4 dedos extendidos pero muy separados (splay)."""
    pts = make_landmarks_flat_hand_b()
    for p in pts:
        if p["id"] == 8:
            p["x"] = 0.38
        elif p["id"] == 12:
            p["x"] = 0.48
        elif p["id"] == 16:
            p["x"] = 0.58
        elif p["id"] == 20:
            p["x"] = 0.68
    return pts


def make_landmarks_l_with_middle_extended():
    """Seña L errónea: índice y pulgar extendidos pero dedo medio también extendido."""
    pts = make_landmarks_l_shape()
    for p in pts:
        if p["id"] == 10:
            p["y"] = 0.50
        elif p["id"] == 11:
            p["y"] = 0.42
        elif p["id"] == 12:
            p["y"] = 0.35
    return pts


def make_landmarks_y_with_index_extended():
    """Seña Y errónea: pulgar y meñique extendidos pero índice también extendido."""
    pts = make_landmarks_y_shape()
    for p in pts:
        if p["id"] == 6:
            p["y"] = 0.50
        elif p["id"] == 7:
            p["y"] = 0.42
        elif p["id"] == 8:
            p["y"] = 0.35
    return pts


def make_landmarks_y_with_ring_extended():
    """Seña Y errónea: pulgar y meñique extendidos pero anular también extendido."""
    pts = make_landmarks_y_shape()
    for p in pts:
        if p["id"] == 14:
            p["y"] = 0.50
        elif p["id"] == 15:
            p["y"] = 0.42
        elif p["id"] == 16:
            p["y"] = 0.35
    return pts


def test_level_1_strict_anatomical_rejections():
    """Verifica todas las pruebas negativas y positivas obligatorias de Nivel 1."""
    evaluator = LSMEvaluator()
    orient_ok = {
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "hand_orientation": {
            "imu_present": True,
            "sensor_type": "MPU6050",
            "tilt_error": 4.0
        }
    }

    # A: correcto
    res_a_ok = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_fist_a(), **orient_ok}, target_sign="A")
    assert res_a_ok["is_valid"] is True

    # A: índice extendido -> reject
    res_a_idx = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_a_with_index_extended(), **orient_ok}, target_sign="A")
    assert res_a_idx["is_valid"] is False
    assert "índice" in res_a_idx["message"]

    # A: meñique extendido -> reject
    res_a_pk = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_a_with_pinky_extended(), **orient_ok}, target_sign="A")
    assert res_a_pk["is_valid"] is False
    assert "meñique" in res_a_pk["message"]

    # B: correcto
    res_b_ok = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_flat_hand_b(), **orient_ok}, target_sign="B")
    assert res_b_ok["is_valid"] is True

    # B: pulgar extendido -> reject
    res_b_th = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_b_with_thumb_extended(), **orient_ok}, target_sign="B")
    assert res_b_th["is_valid"] is False
    assert "pulgar" in res_b_th["message"]

    # B: dedos separados -> reject
    res_b_splay = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_b_with_splayed_fingers(), **orient_ok}, target_sign="B")
    assert res_b_splay["is_valid"] is False

    # C: correcto
    res_c_ok = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_c_shape(), **orient_ok}, target_sign="C")
    assert res_c_ok["is_valid"] is True

    # C: mano abierta -> reject
    res_c_open = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_open_hand(), **orient_ok}, target_sign="C")
    assert res_c_open["is_valid"] is False

    # C: puño cerrado -> reject
    res_c_fist = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_fist_a(), **orient_ok}, target_sign="C")
    assert res_c_fist["is_valid"] is False

    # L: correcto
    res_l_ok = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_l_shape(), **orient_ok}, target_sign="L")
    assert res_l_ok["is_valid"] is True

    # L: medio extendido -> reject
    res_l_mid = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_l_with_middle_extended(), **orient_ok}, target_sign="L")
    assert res_l_mid["is_valid"] is False
    assert "medio" in res_l_mid["message"]

    # Y: correcto
    res_y_ok = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_y_shape(), **orient_ok}, target_sign="Y")
    assert res_y_ok["is_valid"] is True

    # Y: índice extendido -> reject
    res_y_idx = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_y_with_index_extended(), **orient_ok}, target_sign="Y")
    assert res_y_idx["is_valid"] is False
    assert "índice" in res_y_idx["message"]

    # Y: anular extendido -> reject
    res_y_ring = evaluator.evaluate({"vision_present": True, "raw_landmarks": make_landmarks_y_with_ring_extended(), **orient_ok}, target_sign="Y")
    assert res_y_ring["is_valid"] is False
    assert "anular" in res_y_ring["message"]
