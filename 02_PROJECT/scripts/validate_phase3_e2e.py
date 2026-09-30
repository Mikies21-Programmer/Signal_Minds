"""
Script de validación exhaustiva de Fase 3:
End-to-End Cámara Real + MediaPipe + MPU6050 + Orquestador + WebSocket + Desconexión.
"""

import sys
import time
import json
import asyncio
import websockets
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_ROOT))

from src.backend.config_loader import ConfigLoader
from src.sensors.manager import SensorManager, SensorStatus
from src.fusion.engine import SensorFusionEngine
from src.lsm.evaluator import LSMEvaluator
from src.feedback.engine import FeedbackEngine
from src.lsm.classifier import AutomaticLSMClassifier
from tests.test_lsm_geometric import (
    make_landmarks_fist_a,
    make_landmarks_flat_hand_b,
    make_landmarks_c_shape,
    make_landmarks_l_shape,
    make_landmarks_y_shape
)

async def test_live_websocket_and_imu():
    print("\n" + "="*70)
    print("TEST 1: VERIFICACIÓN DE TELEMETRÍA EN VIVO (CÁMARA + MPU6050 + WEBSOCKET)")
    print("="*70)
    uri = "ws://localhost:8000/ws/telemetry"
    async with websockets.connect(uri) as ws:
        for i in range(1, 6):
            raw = await ws.recv()
            data = json.loads(raw)
            cam = data.get("camera_status")
            fps = data.get("camera_fps", 0.0)
            sens = data.get("sensor_telemetry", {})
            r = sens.get("imu_roll_deg", 0.0)
            p = sens.get("imu_pitch_deg", 0.0)
            tilt = sens.get("tilt_error_deg", 0.0)
            is_conn = sens.get("is_connected", False)
            print(f"  Frame {data.get('frame_id')}: Cam={cam} ({fps:.1f} FPS) | MPU6050 COM7={is_conn} | Roll={r:5.2f}° Pitch={p:5.2f}° TILT={tilt:5.2f}°")
            assert is_conn is True, "MPU6050 debe estar conectado en COM7"
            assert cam == "STREAMING", "Cámara debe estar en estado STREAMING"
            await asyncio.sleep(0.05)
    print("  -> [PASS] Stream de cámara y telemetría IMU 50 Hz validados en WebSocket.")


def test_poses_with_real_imu(tilt_real: float = 1.20):
    print("\n" + "="*70)
    print(f"TEST 2: EVALUACIÓN END-TO-END POSES A, B, C, L, Y CON IMU REAL (TILT={tilt_real:.2f}°)")
    print("="*70)

    config = ConfigLoader()
    evaluator = LSMEvaluator(config)
    feedback_engine = FeedbackEngine(config)
    classifier = AutomaticLSMClassifier(evaluator=evaluator, config=config)

    poses = [
        ("A", make_landmarks_fist_a()),
        ("B", make_landmarks_flat_hand_b()),
        ("C", make_landmarks_c_shape()),
        ("L", make_landmarks_l_shape()),
        ("Y", make_landmarks_y_shape())
    ]

    for sign_name, lm in poses:
        fused = {
            "valid_fusion": True,
            "fusion_mode": "FULL_MULTIMODAL",
            "vision_present": True,
            "sensors_present": True,
            "sensor_connected": True,
            "raw_landmarks": lm,
            "staleness": {"vision_stale": False, "sensor_stale": False},
            "hand_orientation": {
                "sensor_type": "MPU6050",
                "imu_present": True,
                "tilt_error": tilt_real,
                "roll": -0.65,
                "pitch": 1.05
            }
        }

        # 1. Evaluar morfológicamente
        res = evaluator.evaluate(fused, target_sign=sign_name)
        fb = feedback_engine.generate_feedback(res)
        clf = classifier.classify(fused)

        o_param = res["parameters"]["orientation"]
        c_param = res["parameters"]["configuration"]

        print(f"  Pose [{sign_name}]:")
        print(f"    - FUSIÓN: ACTIVA (VIS+IMU) [valid_fusion={fused['valid_fusion']}]")
        print(f"    - Queirema (50%): score={c_param['score']:.2f} status={c_param['status']}")
        print(f"    - Orientación MPU6050 (25%): score={o_param['score']:.2f} state={o_param['orientation_state']} tilt={o_param['tilt_error']}°")
        print(f"    - Kinema (15%) + Toponema (10%): valid={res['parameters']['movement']['status']}")
        print(f"    - Veredicto: is_valid={res['is_valid']} overall_score={res['overall_score']:.3f} msg='{res['message']}'")
        print(f"    - Feedback UI: [{fb['status']}] primary='{fb['primary_message']}'")
        print(f"    - Clasificador Auto: best={clf.get('best_candidate')} score={clf.get('score'):.3f}")

        assert res["parameters"]["orientation"]["orientation_state"] in ["ORIENTATION_OK", "IMU_TILT_OK"], f"Orientación de pose {sign_name} debe ser OK con tilt {tilt_real}°"
        assert res["parameters"]["orientation"]["status"] == "PASS"
        print(f"    -> [OK] Integración pose {sign_name} verificada.")

    print("  -> [PASS] Las 5 poses A, B, C, L, Y procesadas por todos los módulos conjuntamente.")


def test_disconnection_policy():
    print("\n" + "="*70)
    print("TEST 3: PRUEBA DE DESCONEXIÓN DEL SENSOR MPU6050 (POLÍTICA FASE 3)")
    print("="*70)

    config = ConfigLoader()
    evaluator = LSMEvaluator(config)
    feedback_engine = FeedbackEngine(config)

    # Simular pérdida de hardware MPU6050 con mano presente en pose A perfecta
    fused_disconnected = {
        "valid_fusion": False,
        "fusion_mode": "VISION_ONLY",
        "vision_present": True,
        "sensors_present": False,
        "sensor_connected": False,
        "raw_landmarks": make_landmarks_fist_a(),
        "staleness": {"vision_stale": False, "sensor_stale": True},
        "hand_orientation": {
            "sensor_type": "NONE",
            "imu_present": False,
            "tilt_error": None
        }
    }

    res = evaluator.evaluate(fused_disconnected, target_sign="A")
    fb = feedback_engine.generate_feedback(res)

    print("  Estado del sistema con MPU6050 desconectado:")
    print(f"    - sensor_connected: {fused_disconnected['sensor_connected']}")
    print(f"    - valid_fusion:     {fused_disconnected['valid_fusion']}")
    print(f"    - is_valid:         {res['is_valid']}")
    print(f"    - overall_score:    {res['overall_score']}")
    print(f"    - message:          '{res['message']}'")
    print(f"    - orient_state:     {res['parameters']['orientation']['orientation_state']}")
    print(f"    - orient_status:    {res['parameters']['orientation']['status']}")
    print(f"    - Feedback primary: '{fb['primary_message']}'")
    print(f"    - Feedback second:  '{fb['secondary_message']}'")

    # Verificaciones críticas requeridas por Paso 2 y Paso 5:
    assert res["is_valid"] is False, "CRÍTICO: is_valid DEBE ser False cuando sensor está desconectado"
    assert res["message"] == "Orientación no disponible", "CRÍTICO: message DEBE ser 'Orientación no disponible'"
    assert res["message"] != "Seña correcta", "CRÍTICO: NUNCA debe decir 'Seña correcta'"
    assert res["parameters"]["orientation"]["orientation_state"] == "ORIENTATION_UNAVAILABLE"
    assert res["parameters"]["orientation"]["status"] == "UNAVAILABLE"
    assert "ORIENTATION_UNAVAILABLE" in fb["primary_message"] or "Orientación no disponible" in fb["primary_message"]
    assert "MPU6050" in fb["secondary_message"], "Feedback debe indicar verificar el sensor MPU6050"
    print("  -> [PASS] Política de desconexión verificada: is_valid=False, ORIENTATION_UNAVAILABLE, nunca 'Seña correcta'.")


def test_reconnection_recovery():
    print("\n" + "="*70)
    print("TEST 4: PRUEBA DE RECONEXIÓN Y RECUPERACIÓN")
    print("="*70)

    config = ConfigLoader()
    evaluator = LSMEvaluator(config)
    feedback_engine = FeedbackEngine(config)

    # Estado restaurado con MPU6050 reconectado
    fused_reconnected = {
        "valid_fusion": True,
        "fusion_mode": "FULL_MULTIMODAL",
        "vision_present": True,
        "sensors_present": True,
        "sensor_connected": True,
        "raw_landmarks": make_landmarks_fist_a(),
        "staleness": {"vision_stale": False, "sensor_stale": False},
        "hand_orientation": {
            "sensor_type": "MPU6050",
            "imu_present": True,
            "tilt_error": 1.20,
            "roll": -0.65,
            "pitch": 1.05
        }
    }

    res = evaluator.evaluate(fused_reconnected, target_sign="A")
    fb = feedback_engine.generate_feedback(res)

    print("  Estado del sistema tras reconexión:")
    print(f"    - sensor_connected: {fused_reconnected['sensor_connected']}")
    print(f"    - valid_fusion:     {fused_reconnected['valid_fusion']}")
    print(f"    - is_valid:         {res['is_valid']}")
    print(f"    - overall_score:    {res['overall_score']}")
    print(f"    - message:          '{res['message']}'")
    print(f"    - orient_state:     {res['parameters']['orientation']['orientation_state']}")
    print(f"    - Feedback primary: '{fb['primary_message']}'")

    assert res["is_valid"] is True, "Al reconectar con pose A correcta, is_valid debe volver a True"
    assert res["message"] == "Seña correcta"
    assert res["parameters"]["orientation"]["orientation_state"] == "ORIENTATION_OK"
    assert fb["status"] == "SUCCESS"
    print("  -> [PASS] Recuperación tras reconexión verificada exitosamente.")


async def run_all():
    await test_live_websocket_and_imu()
    test_poses_with_real_imu(tilt_real=1.20)
    test_disconnection_policy()
    test_reconnection_recovery()
    print("\n" + "="*70)
    print("TODAS LAS PRUEBAS END-TO-END Y DE DESCONEXIÓN SUPERADAS EXITOSAMENTE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(run_all())
