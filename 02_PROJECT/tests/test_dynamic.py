"""
Pruebas unitarias de lógica cinemática y evaluadores dinámicos para LSM Nivel 2.
Verifica:
- J: meñique extendido + trayectoria en el aire vs estático
- Ñ: postura base N + ondulación multiaje vs estático
- Q: postura base Q + rotación de muñeca/MPU6050 vs sin rotación
- X: postura de gancho en índice + movimiento vs índice recto vs estático
- Z: índice apuntador + trayectoria de 3 tramos (Z) con >= 2 giros vs recta vs corta
- Resiliencia: no_hand, IMU unavailable, stale sensor, recuperación
NOTA: Estas trayectorias sintéticas evalúan exclusivamente la lógica algorítmica.
"""

import pytest
import time
from typing import List, Dict, Any
from src.lsm.dynamic import DynamicGestureTracker
from src.lsm.evaluator import LSMEvaluator
from src.lsm.geometry import HandGeometryFeatures
from tests.test_lsm_geometric import make_landmarks_fist_a


def make_landmarks_j_base(dx=0.0, dy=0.0):
    """Genera 21 puntos para postura base J (meñique extendido, otros 3 cerrados)."""
    pts = [{"id": 0, "x": 0.50, "y": 0.75, "z": 0.0}]
    # Pulgar flexionado cerca del puño
    pts.append({"id": 1, "x": 0.46, "y": 0.70, "z": 0.0})
    pts.append({"id": 2, "x": 0.44, "y": 0.65, "z": 0.0})
    pts.append({"id": 3, "x": 0.45, "y": 0.60, "z": 0.0})
    pts.append({"id": 4, "x": 0.48, "y": 0.58, "z": 0.0})
    # Índice, medio, anular cerrados en puño
    for mcp, bx in [(5, 0.47), (9, 0.50), (13, 0.53)]:
        pts.append({"id": mcp, "x": bx, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp + 1, "x": bx, "y": 0.55, "z": -0.04})
        pts.append({"id": mcp + 2, "x": bx, "y": 0.59, "z": -0.04})
        pts.append({"id": mcp + 3, "x": bx, "y": 0.63, "z": 0.0})
    # Meñique extendido con movimiento armónico del dedo
    pts.append({"id": 17, "x": 0.56, "y": 0.60, "z": 0.0})
    pts.append({"id": 18, "x": 0.56 + dx * 0.3, "y": 0.52 + dy * 0.3, "z": 0.0})
    pts.append({"id": 19, "x": 0.56 + dx * 0.7, "y": 0.46 + dy * 0.7, "z": 0.0})
    pts.append({"id": 20, "x": 0.56 + dx, "y": 0.40 + dy, "z": 0.0})
    return pts


def make_landmarks_n_base(hand_center_x=0.50, hand_center_y=0.50):
    """Genera 21 puntos para postura base N (índice y medio extendidos juntos hacia abajo/adelante)."""
    pts = [{"id": 0, "x": hand_center_x, "y": hand_center_y + 0.20, "z": 0.0}]
    pts.append({"id": 1, "x": hand_center_x - 0.04, "y": hand_center_y + 0.15, "z": 0.0})
    pts.append({"id": 2, "x": hand_center_x - 0.03, "y": hand_center_y + 0.10, "z": 0.0})
    pts.append({"id": 3, "x": hand_center_x, "y": hand_center_y + 0.08, "z": 0.0})
    pts.append({"id": 4, "x": hand_center_x + 0.02, "y": hand_center_y + 0.06, "z": 0.0})
    # Índice extendido
    pts.append({"id": 5, "x": hand_center_x - 0.02, "y": hand_center_y + 0.05, "z": 0.0})
    pts.append({"id": 6, "x": hand_center_x - 0.02, "y": hand_center_y - 0.03, "z": 0.0})
    pts.append({"id": 7, "x": hand_center_x - 0.02, "y": hand_center_y - 0.09, "z": 0.0})
    pts.append({"id": 8, "x": hand_center_x - 0.02, "y": hand_center_y - 0.15, "z": 0.0})
    # Medio extendido junto al índice
    pts.append({"id": 9, "x": hand_center_x + 0.01, "y": hand_center_y + 0.05, "z": 0.0})
    pts.append({"id": 10, "x": hand_center_x + 0.01, "y": hand_center_y - 0.03, "z": 0.0})
    pts.append({"id": 11, "x": hand_center_x + 0.01, "y": hand_center_y - 0.09, "z": 0.0})
    pts.append({"id": 12, "x": hand_center_x + 0.01, "y": hand_center_y - 0.15, "z": 0.0})
    # Anular y meñique cerrados
    for mcp, bx in [(13, hand_center_x + 0.04), (17, hand_center_x + 0.07)]:
        pts.append({"id": mcp, "x": bx, "y": hand_center_y + 0.06, "z": 0.0})
        pts.append({"id": mcp + 1, "x": bx, "y": hand_center_y + 0.02, "z": -0.04})
        pts.append({"id": mcp + 2, "x": bx, "y": hand_center_y + 0.05, "z": -0.04})
        pts.append({"id": mcp + 3, "x": bx, "y": hand_center_y + 0.09, "z": 0.0})
    return pts


def make_landmarks_q_base():
    """Genera 21 puntos para postura base Q (índice y pulgar hacia abajo)."""
    pts = [{"id": 0, "x": 0.50, "y": 0.40, "z": 0.0}]  # Muñeca arriba
    # Pulgar hacia abajo
    pts.append({"id": 1, "x": 0.46, "y": 0.45, "z": 0.0})
    pts.append({"id": 2, "x": 0.44, "y": 0.50, "z": 0.0})
    pts.append({"id": 3, "x": 0.44, "y": 0.55, "z": 0.0})
    pts.append({"id": 4, "x": 0.45, "y": 0.60, "z": 0.0})
    # Índice extendido hacia abajo
    pts.append({"id": 5, "x": 0.48, "y": 0.48, "z": 0.0})
    pts.append({"id": 6, "x": 0.48, "y": 0.55, "z": 0.0})
    pts.append({"id": 7, "x": 0.48, "y": 0.62, "z": 0.0})
    pts.append({"id": 8, "x": 0.48, "y": 0.70, "z": 0.0})
    # Dedos medio, anular, meñique flexionados
    for mcp, bx in [(9, 0.52), (13, 0.55), (17, 0.58)]:
        pts.append({"id": mcp, "x": bx, "y": 0.48, "z": 0.0})
        pts.append({"id": mcp + 1, "x": bx, "y": 0.44, "z": -0.04})
        pts.append({"id": mcp + 2, "x": bx, "y": 0.46, "z": -0.04})
        pts.append({"id": mcp + 3, "x": bx, "y": 0.49, "z": 0.0})
    return pts


def make_landmarks_x_hook(hooked=True, tip_y=0.56):
    """Genera 21 puntos para postura X con índice en gancho (PIP ~90°) o recto."""
    pts = [{"id": 0, "x": 0.50, "y": 0.75, "z": 0.0}]
    # Pulgar doblado
    pts.append({"id": 1, "x": 0.46, "y": 0.70, "z": 0.0})
    pts.append({"id": 2, "x": 0.44, "y": 0.66, "z": 0.0})
    pts.append({"id": 3, "x": 0.45, "y": 0.62, "z": 0.0})
    pts.append({"id": 4, "x": 0.48, "y": 0.60, "z": 0.0})
    if hooked:
        # Gancho: MCP(5) -> PIP(6) arriba, DIP(7) lateral/abajo, TIP(8) hacia abajo (PIP ~ 90°)
        pts.append({"id": 5, "x": 0.48, "y": 0.60, "z": 0.0})
        pts.append({"id": 6, "x": 0.48, "y": 0.50, "z": 0.0})
        pts.append({"id": 7, "x": 0.44, "y": 0.50, "z": 0.0})
        pts.append({"id": 8, "x": 0.44, "y": tip_y, "z": 0.0})
    else:
        # Recto: todos los segmentos hacia arriba
        pts.append({"id": 5, "x": 0.48, "y": 0.60, "z": 0.0})
        pts.append({"id": 6, "x": 0.48, "y": 0.50, "z": 0.0})
        pts.append({"id": 7, "x": 0.48, "y": 0.42, "z": 0.0})
        pts.append({"id": 8, "x": 0.48, "y": 0.35, "z": 0.0})
    # Medio, anular, meñique cerrados
    for mcp, bx in [(9, 0.52), (13, 0.55), (17, 0.58)]:
        pts.append({"id": mcp, "x": bx, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp + 1, "x": bx, "y": 0.55, "z": -0.04})
        pts.append({"id": mcp + 2, "x": bx, "y": 0.59, "z": -0.04})
        pts.append({"id": mcp + 3, "x": bx, "y": 0.63, "z": 0.0})
    return pts


def make_landmarks_z_pointer(idx_x=0.50, idx_y=0.40):
    """Genera 21 puntos para postura base Z (índice extendido apuntador, otros cerrados)."""
    pts = [{"id": 0, "x": idx_x, "y": 0.75, "z": 0.0}]
    pts.append({"id": 1, "x": idx_x - 0.04, "y": 0.70, "z": 0.0})
    pts.append({"id": 2, "x": idx_x - 0.03, "y": 0.66, "z": 0.0})
    pts.append({"id": 3, "x": idx_x - 0.02, "y": 0.62, "z": 0.0})
    pts.append({"id": 4, "x": idx_x - 0.01, "y": 0.60, "z": 0.0})
    # Índice apuntador
    pts.append({"id": 5, "x": idx_x - 0.02, "y": 0.60, "z": 0.0})
    pts.append({"id": 6, "x": idx_x - 0.01, "y": 0.52, "z": 0.0})
    pts.append({"id": 7, "x": idx_x - 0.005, "y": 0.45, "z": 0.0})
    pts.append({"id": 8, "x": idx_x, "y": idx_y, "z": 0.0})
    # Medio, anular, meñique cerrados
    for mcp, bx in [(9, idx_x + 0.02), (13, idx_x + 0.05), (17, idx_x + 0.08)]:
        pts.append({"id": mcp, "x": bx, "y": 0.60, "z": 0.0})
        pts.append({"id": mcp + 1, "x": bx, "y": 0.55, "z": -0.04})
        pts.append({"id": mcp + 2, "x": bx, "y": 0.59, "z": -0.04})
        pts.append({"id": mcp + 3, "x": bx, "y": 0.63, "z": 0.0})
    return pts


# =========================================================================
# PRUEBAS OBLIGATORIAS: J
# =========================================================================

def test_dynamic_j_correct_motion():
    """J con meñique extendido y trayectoria en curva -> RECOGNIZED."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("J")
    t0 = 1000.0

    # Trayectoria del meñique trazando curva descendente y lateral
    res = None
    for i in range(14):
        dx = -0.08 * (i / 13.0)
        dy = 0.06 * (i / 13.0)
        lms = make_landmarks_j_base(dx=dx, dy=dy)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="J")

    assert res is not None
    assert res["is_valid"] is True
    assert res["dynamic_status"] == "RECOGNIZED"


def test_dynamic_j_no_motion_rejects():
    """J con meñique extendido pero sin movimiento -> REJECT (MOVING / PREPARING)."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("J")
    t0 = 1000.0

    res = None
    for i in range(14):
        # Meñique estático
        lms = make_landmarks_j_base(dx=0.0, dy=0.0)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="J")

    assert res is not None
    assert res["is_valid"] is False
    assert "movimiento" in res["message"].lower()


# =========================================================================
# PRUEBAS OBLIGATORIAS: Ñ
# =========================================================================

def test_dynamic_nn_wave_motion():
    """Ñ con configuración N y movimiento ondulante (oscilaciones) -> RECOGNIZED."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Ñ")
    t0 = 1000.0

    # Ondulación: centro oscila izquierda-derecha-izquierda
    offsets = [0.0, 0.04, 0.07, 0.03, -0.02, -0.06, -0.02, 0.03, 0.06, 0.02, -0.01, -0.04, 0.0]
    res = None
    for i, dx in enumerate(offsets):
        lms = make_landmarks_n_base(hand_center_x=0.50 + dx, hand_center_y=0.50)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="Ñ")

    assert res is not None
    assert res["is_valid"] is True
    assert res["dynamic_status"] == "RECOGNIZED"


def test_dynamic_nn_static_rejects():
    """Ñ con postura N pero estática -> REJECT e informar falta de ondulación."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Ñ")
    t0 = 1000.0

    res = None
    for i in range(12):
        lms = make_landmarks_n_base(hand_center_x=0.50, hand_center_y=0.50)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="Ñ")

    assert res is not None
    assert res["is_valid"] is False
    assert "ondulante" in res["message"].lower()


# =========================================================================
# PRUEBAS OBLIGATORIAS: Q
# =========================================================================

def test_dynamic_q_with_rotation():
    """Q con postura de índice/pulgar hacia abajo y rotación angular de muñeca -> RECOGNIZED."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Q")
    t0 = 1000.0

    # Rotación en MPU (roll incrementa 15-20 grados)
    res = None
    for i in range(14):
        roll_val = 5.0 + 1.2 * i
        lms = make_landmarks_q_base()
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0},
            "sensor_telemetry": {
                "is_connected": True,
                "imu_roll_deg": roll_val,
                "imu_pitch_deg": 10.0,
                "tilt_error_deg": 5.0
            }
        }
        res = evaluator.evaluate(state, target_sign="Q")

    assert res is not None
    assert res["is_valid"] is True
    assert res["dynamic_status"] == "RECOGNIZED"


def test_dynamic_q_no_rotation_rejects():
    """Q sin rotación angular de muñeca -> REJECT."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Q")
    t0 = 1000.0

    res = None
    for i in range(14):
        lms = make_landmarks_q_base()
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0},
            "sensor_telemetry": {
                "is_connected": True,
                "imu_roll_deg": 5.0,
                "imu_pitch_deg": 10.0,
                "tilt_error_deg": 5.0
            }
        }
        res = evaluator.evaluate(state, target_sign="Q")

    assert res is not None
    assert res["is_valid"] is False
    assert "giro" in res["message"].lower() or "muñeca" in res["message"].lower()


# =========================================================================
# PRUEBAS OBLIGATORIAS: X
# =========================================================================

def test_dynamic_x_hook_and_motion():
    """X con índice en gancho y movimiento de retracción -> RECOGNIZED."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("X")
    t0 = 1000.0

    res = None
    for i in range(14):
        # Punta del gancho se retrae
        ty = 0.56 + 0.015 * i
        lms = make_landmarks_x_hook(hooked=True, tip_y=ty)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="X")

    assert res is not None
    assert res["is_valid"] is True
    assert res["dynamic_status"] == "RECOGNIZED"


def test_dynamic_x_straight_finger_rejects():
    """X con índice recto -> REJECT inmediato por configuración incorrecta."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("X")

    lms_straight = make_landmarks_x_hook(hooked=False)
    state = {
        "vision_present": True,
        "raw_landmarks": lms_straight,
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "timestamp": 1000.0,
        "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
    }
    res = evaluator.evaluate(state, target_sign="X")
    assert res["is_valid"] is False
    assert "gancho" in res["message"].lower()


# =========================================================================
# PRUEBAS OBLIGATORIAS: Z
# =========================================================================

def test_dynamic_z_complete_trajectory():
    """Z con trayectoria de 3 tramos (horizontal -> diagonal -> horizontal) -> RECOGNIZED."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Z")
    t0 = 1000.0

    # Definir los 3 tramos de la letra Z para la punta del índice (landmark 8)
    coords = [
        # Tramo 1: Horizontal a la derecha
        (0.40, 0.35), (0.45, 0.35), (0.50, 0.35), (0.55, 0.35),
        # Tramo 2: Diagonal hacia abajo y a la izquierda
        (0.50, 0.40), (0.45, 0.45), (0.40, 0.50),
        # Tramo 3: Horizontal a la derecha
        (0.45, 0.50), (0.50, 0.50), (0.55, 0.50), (0.60, 0.50)
    ]

    res = None
    for i, (x, y) in enumerate(coords):
        lms = make_landmarks_z_pointer(idx_x=x, idx_y=y)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="Z")

    assert res is not None
    assert res["is_valid"] is True
    assert res["dynamic_status"] == "RECOGNIZED"


def test_dynamic_z_straight_line_rejects():
    """Z con trayectoria en línea recta (sin giros de Z) -> REJECT."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Z")
    t0 = 1000.0

    # Línea recta continua hacia la derecha (0 cambios de dirección)
    res = None
    for i in range(12):
        x = 0.35 + 0.025 * i
        y = 0.40
        lms = make_landmarks_z_pointer(idx_x=x, idx_y=y)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="Z")

    assert res is not None
    assert res["is_valid"] is False
    assert "cambios de dirección" in res["message"].lower() or "z completa" in res["message"].lower()


def test_dynamic_z_short_path_rejects():
    """Z con movimiento microscópico o casi nulo -> REJECT."""
    evaluator = LSMEvaluator()
    evaluator.set_target_sign("Z")
    t0 = 1000.0

    res = None
    for i in range(12):
        lms = make_landmarks_z_pointer(idx_x=0.50, idx_y=0.40)
        state = {
            "vision_present": True,
            "raw_landmarks": lms,
            "valid_fusion": True,
            "sensor_connected": True,
            "sensors_present": True,
            "timestamp": t0 + i * 0.05,
            "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
        }
        res = evaluator.evaluate(state, target_sign="Z")

    assert res is not None
    assert res["is_valid"] is False


# =========================================================================
# PRUEBAS DE RESILIENCIA Y MANEJO DE ERRORES SENSORIALES
# =========================================================================

def test_dynamic_tracker_no_hand_resilience():
    """Garantiza que la pérdida de mano limpie adecuadamente el tracker."""
    tracker = DynamicGestureTracker()
    tracker.add_sample([], timestamp=1.0)
    assert tracker.state == "NO_HAND"
    assert tracker.get_sample_count() == 0


def test_dynamic_tracker_window_pruning():
    """Descarta muestras con más de window_duration_sec de antigüedad."""
    tracker = DynamicGestureTracker(window_duration_sec=1.0)
    lms = make_landmarks_j_base()

    tracker.add_sample(lms, timestamp=10.0)
    tracker.add_sample(lms, timestamp=10.5)
    assert tracker.get_sample_count() == 2

    # Nueva muestra 1.2 segundos después -> la primera debe ser podada
    tracker.add_sample(lms, timestamp=11.2)
    assert tracker.get_sample_count() == 2  # Quedan la de 10.5 y 11.2


def test_resilience_no_hand():
    """Evaluar sin detección de mano retorna is_valid=False."""
    evaluator = LSMEvaluator()
    res = evaluator.evaluate({"vision_present": False, "raw_landmarks": []}, target_sign="A")
    assert res["is_valid"] is False
    assert res["overall_score"] == 0.0
    assert "Sin mano" in res["message"]


def test_resilience_stale_sensor():
    """Evaluar con sensor MPU6050 obsoleto (stale) rechaza validación estricta."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "staleness": {"sensor_stale": True},
        "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 5.0}
    }
    res = evaluator.evaluate(state, target_sign="A")
    assert res["is_valid"] is False
    assert res["parameters"]["orientation"]["status"] == "UNAVAILABLE"


def test_resilience_imu_unavailable():
    """Evaluar con IMU ausente/desconectado rechaza validación."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "valid_fusion": False,
        "sensor_connected": False,
        "sensors_present": False,
        "hand_orientation": {"imu_present": False, "sensor_type": "NONE"}
    }
    res = evaluator.evaluate(state, target_sign="A")
    assert res["is_valid"] is False
    assert res["parameters"]["orientation"]["status"] == "UNAVAILABLE"
    assert "no disponible" in res["message"].lower()


def test_resilience_camera_disconnected():
    """Cámara desconectada (vision_present=False) no evalúa seña como correcta."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": False,
        "raw_landmarks": None,
        "valid_fusion": False,
        "sensor_connected": True,
        "sensors_present": True,
        "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 2.0}
    }
    res = evaluator.evaluate(state, target_sign="B")
    assert res["is_valid"] is False
    assert res["parameters"]["configuration"]["score"] == 0.0


def test_resilience_invalid_fusion():
    """Fusión inválida nunca produce veredicto positivo."""
    evaluator = LSMEvaluator()
    state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "valid_fusion": False,
        "sensor_connected": False,
        "sensors_present": True,
        "hand_orientation": {"imu_present": False, "sensor_type": "MPU6050", "tilt_error": 2.0}
    }
    res = evaluator.evaluate(state, target_sign="A")
    assert res["is_valid"] is False


def test_resilience_sensor_recovery():
    """El sistema se recupera de desconexión previa cuando el sensor vuelve a emitir datos válidos."""
    evaluator = LSMEvaluator()

    # 1. Muestra con desconexión
    disconnected_state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "valid_fusion": False,
        "sensor_connected": False,
        "sensors_present": False,
        "hand_orientation": {"imu_present": False, "sensor_type": "NONE"}
    }
    res_bad = evaluator.evaluate(disconnected_state, target_sign="A")
    assert res_bad["is_valid"] is False
    assert res_bad["parameters"]["orientation"]["status"] == "UNAVAILABLE"

    # 2. Sensor se recupera y envía telemetría válida
    recovered_state = {
        "vision_present": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "valid_fusion": True,
        "sensor_connected": True,
        "sensors_present": True,
        "hand_orientation": {"imu_present": True, "sensor_type": "MPU6050", "tilt_error": 3.0}
    }
    res_good = evaluator.evaluate(recovered_state, target_sign="A")
    assert res_good["is_valid"] is True
    assert res_good["parameters"]["orientation"]["status"] == "PASS"
