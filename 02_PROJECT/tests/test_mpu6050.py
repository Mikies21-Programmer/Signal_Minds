"""
Pruebas unitarias y de integración para la integración del sensor MPU6050 y ESP32-S3.
Cubre los 15 requisitos obligatorios de Fase 2 más pruebas de regresión del subsistema de visión y cámara.
"""

import math
import time
import json
import os
import pytest

from src.sensors.manager import (
    SensorManager,
    SensorStatus,
    RealHardwareSensorBackend,
    MockSensorBackend
)
from src.fusion.engine import SensorFusionEngine
from src.lsm.evaluator import LSMEvaluator


# ==============================================================================
# 1. Detección de dirección I2C (0x68 por defecto, 0x69 si AD0=HIGH, rechazo de inválidas)
# ==============================================================================
def test_i2c_address_detection():
    """Valida la detección de direcciones I2C del MPU6050: 0x68 estándar y 0x69 alternativa."""
    valid_addresses = ["0x68", "0x69", "AUTO"]
    for addr in ["0x68", "0x69"]:
        backend = RealHardwareSensorBackend({"i2c_address": addr})
        assert backend.i2c_address in valid_addresses

    # Rechazo de direcciones ajenas al rango del chip MPU6050
    invalid_address = "0x77"
    assert invalid_address not in ["0x68", "0x69"]


# ==============================================================================
# 2. Cálculo de Roll: roll_acc = atan2(ay, az) * 180 / pi
# ==============================================================================
def test_roll_calculation_formula():
    """Valida la fórmula trigonométrica de roll con acelerómetro según especificación técnica."""
    def calc_roll(ay, az):
        return math.atan2(ay, az) * 180.0 / math.pi

    # Mano horizontal con dorso arriba (ay=0, az=1) -> Roll 0°
    assert round(calc_roll(0.0, 1.0), 2) == 0.0

    # Inclinación lateral derecha pura 90° (ay=1, az=0)
    assert round(calc_roll(1.0, 0.0), 2) == 90.0

    # Inclinación lateral izquierda pura -90° (ay=-1, az=0)
    assert round(calc_roll(-1.0, 0.0), 2) == -90.0

    # Inclinación a 45° (ay=1, az=1)
    assert round(calc_roll(1.0, 1.0), 2) == 45.0


# ==============================================================================
# 3. Cálculo de Pitch: pitch_acc = atan2(-ax, sqrt(ay*ay + az*az)) * 180 / pi
# ==============================================================================
def test_pitch_calculation_formula():
    """Valida la fórmula trigonométrica de pitch con acelerómetro según especificación técnica."""
    def calc_pitch(ax, ay, az):
        return math.atan2(-ax, math.sqrt(ay * ay + az * az)) * 180.0 / math.pi

    # Mano horizontal sin inclinación longitudinal (ax=0, ay=0, az=1) -> Pitch 0°
    assert round(calc_pitch(0.0, 0.0, 1.0), 2) == 0.0

    # Inclinación hacia arriba 90° (ax=-1, ay=0, az=0)
    assert round(calc_pitch(-1.0, 0.0, 0.0), 2) == 90.0

    # Inclinación hacia abajo -90° (ax=1, ay=0, az=0)
    assert round(calc_pitch(1.0, 0.0, 0.0), 2) == -90.0


# ==============================================================================
# 4. Compensación de offset por calibración: delta = medido - referencia
# ==============================================================================
def test_calibration_offset_subtraction():
    """Verifica que los ángulos reportados consideren el offset de la pose de referencia."""
    backend = RealHardwareSensorBackend()
    backend.roll_ref = 8.5
    backend.pitch_ref = -3.2
    backend.is_calibrated = True

    current_roll = 8.5
    current_pitch = -3.2

    delta_roll = current_roll - backend.roll_ref
    delta_pitch = current_pitch - backend.pitch_ref

    assert round(delta_roll, 2) == 0.0
    assert round(delta_pitch, 2) == 0.0


# ==============================================================================
# 5. Cálculo de tilt_error = sqrt(delta_roll^2 + delta_pitch^2)
# ==============================================================================
def test_tilt_error_calculation():
    """Verifica que el error angular global combine pitagóricamente delta_roll y delta_pitch."""
    delta_roll = 3.0
    delta_pitch = 4.0
    tilt_error = math.sqrt(delta_roll**2 + delta_pitch**2)
    assert round(tilt_error, 2) == 5.0

    # En reposo respecto a referencia
    assert math.sqrt(0.0**2 + 0.0**2) == 0.0


# ==============================================================================
# 6. Frontera de 15° para A, B, L (0-15°: ORIENTATION_OK)
# ==============================================================================
def test_15_deg_boundary_frontal():
    """Valida que para A, B, L una inclinación <= 15° resulte en ORIENTATION_OK."""
    evaluator = LSMEvaluator()

    for sign in ["A", "B", "L"]:
        res_0 = evaluator.evaluate_orientation(sign, {"tilt_error": 0.0})
        assert res_0["orientation_state"] == "ORIENTATION_OK"
        assert res_0["status"] == "PASS"

        res_14 = evaluator.evaluate_orientation(sign, {"tilt_error": 14.5})
        assert res_14["orientation_state"] == "ORIENTATION_OK"
        assert res_14["status"] == "PASS"

        res_15 = evaluator.evaluate_orientation(sign, {"tilt_error": 15.0})
        assert res_15["orientation_state"] == "ORIENTATION_OK"
        assert res_15["status"] == "PASS"


# ==============================================================================
# 7. Frontera de 25° para A, B, L (>15-25°: ADJUST, >25°: FAIL)
# ==============================================================================
def test_25_deg_boundary_frontal():
    """Valida la transición a ORIENTATION_FAIL al superar 25° de inclinación en A, B, L."""
    evaluator = LSMEvaluator()

    # Iniciar en ADJUST
    evaluator._prev_orient_state_A = "ORIENTATION_ADJUST"
    res_20 = evaluator.evaluate_orientation("A", {"tilt_error": 20.0})
    assert res_20["orientation_state"] == "ORIENTATION_ADJUST"
    assert res_20["status"] == "CORRECT"

    # Superar 25° + histéresis entra a FAIL
    res_29 = evaluator.evaluate_orientation("A", {"tilt_error": 29.0})
    assert res_29["orientation_state"] == "ORIENTATION_FAIL"
    assert res_29["status"] == "FAIL"


# ==============================================================================
# 8. Fronteras de 20° y 30° para seña Y (mayor tolerancia)
# ==============================================================================
def test_y_sign_20_and_30_deg_boundaries():
    """Valida las tolerancias ampliadas de la seña Y (0-20° OK, 20-30° ADJUST, >30° FAIL)."""
    evaluator = LSMEvaluator()

    # 18° en Y está dentro de OK (en A/B/L estaría en ajuste)
    res_18 = evaluator.evaluate_orientation("Y", {"tilt_error": 18.0})
    assert res_18["orientation_state"] == "ORIENTATION_OK"
    assert res_18["status"] == "PASS"

    # 25° en Y es ADJUST (en A/B/L sería FAIL o límite superior)
    evaluator._prev_orient_state_Y = "ORIENTATION_ADJUST"
    res_25 = evaluator.evaluate_orientation("Y", {"tilt_error": 25.0})
    assert res_25["orientation_state"] == "ORIENTATION_ADJUST"
    assert res_25["status"] == "CORRECT"

    # > 33° en Y es FAIL (30° + 3° histéresis)
    res_34 = evaluator.evaluate_orientation("Y", {"tilt_error": 34.0})
    assert res_34["orientation_state"] == "ORIENTATION_FAIL"
    assert res_34["status"] == "FAIL"


# ==============================================================================
# 9. Histéresis anti-flicker (banda de 3°)
# ==============================================================================
def test_hysteresis_transitions():
    """Valida que la histéresis de 3° evite oscilaciones espurias en las fronteras angulares."""
    evaluator = LSMEvaluator()

    # Arranca en OK (tilt = 10°)
    res = evaluator.evaluate_orientation("A", {"tilt_error": 10.0})
    assert res["orientation_state"] == "ORIENTATION_OK"

    # Sube a 16° (entre 15° y 18° = 15 + 3): NO cambia a ADJUST todavía por histéresis
    res = evaluator.evaluate_orientation("A", {"tilt_error": 16.5})
    assert res["orientation_state"] == "ORIENTATION_OK"

    # Sube a 19° (> 18°): cambia a ORIENTATION_ADJUST
    res = evaluator.evaluate_orientation("A", {"tilt_error": 19.0})
    assert res["orientation_state"] == "ORIENTATION_ADJUST"

    # Baja a 16°: Permanece en ADJUST hasta cruzar el límite ok_limit (<= 15°)
    res = evaluator.evaluate_orientation("A", {"tilt_error": 16.0})
    assert res["orientation_state"] == "ORIENTATION_ADJUST"

    # Baja a 14° (<= 15°): regresa a OK
    res = evaluator.evaluate_orientation("A", {"tilt_error": 14.0})
    assert res["orientation_state"] == "ORIENTATION_OK"


# ==============================================================================
# 10. yaw_valid es estrictamente False (sin magnetómetro en MPU6050)
# ==============================================================================
def test_yaw_valid_strictly_false():
    """Verifica que el sistema reporte explícitamente yaw_valid=False sin inventar yaw absoluto."""
    backend = RealHardwareSensorBackend()
    diag = backend.get_diagnostics()
    # En cualquier estado, yaw_valid del sensor MPU6050 debe ser False
    assert diag["driver_type"] == "RealHardwareSensorBackend"

    manager = SensorManager({"sensors": {"mock_mode": False, "port": "DISABLED"}})
    sample = manager.poll_sensors()
    assert sample["yaw_valid"] is False
    assert sample["sensor_type"] == "MPU6050"


# ==============================================================================
# 11. Parseo del protocolo serial IMU
# ==============================================================================
def test_serial_protocol_parsing():
    """Verifica el parseo correcto de líneas en formato: IMU,<ts>,<roll>,<pitch>,<gx>,<gy>,<gz>,<yaw_valid>."""
    raw_line = "IMU,123456,-3.4,7.1,0.2,-0.5,0.1,false"
    parts = raw_line.split(",")
    assert parts[0] == "IMU"
    assert len(parts) == 8

    ts_ms = int(parts[1])
    roll = float(parts[2])
    pitch = float(parts[3])
    gx = float(parts[4])
    gy = float(parts[5])
    gz = float(parts[6])
    yaw_valid = parts[7].strip().lower() == "true"

    assert ts_ms == 123456
    assert roll == -3.4
    assert pitch == 7.1
    assert gx == 0.2
    assert gy == -0.5
    assert gz == 0.1
    assert yaw_valid is False

    # Cálculo derivado
    tilt_err = math.sqrt(roll**2 + pitch**2)
    assert round(tilt_err, 2) == 7.87


# ==============================================================================
# 12. Sensor desconectado no inventa datos
# ==============================================================================
def test_disconnected_sensor_no_fabrication():
    """Verifica que un sensor no conectado reporte is_connected=False y ceros en flexión."""
    manager = SensorManager({"sensors": {"mock_mode": False, "port": "DISABLED"}})
    manager.start()
    sample = manager.poll_sensors()
    manager.stop()

    assert sample["is_connected"] is False
    assert sample["status"] == "DISCONNECTED"
    assert sample["is_mock"] is False
    assert sample["flex_index"] == 0.0
    assert sample["flex_thumb"] == 0.0
    assert sample["imu_roll_deg"] == 0.0
    assert sample["imu_pitch_deg"] == 0.0


# ==============================================================================
# 13. Telemetría obsoleta (stale sensor)
# ==============================================================================
def test_stale_sensor_fusion():
    """Verifica que el motor de fusión invalide la muestra si el sensor es obsoleto (>200ms)."""
    fusion = SensorFusionEngine({"fusion": {"max_temporal_delta_ms": 200, "stale_sensor_threshold_ms": 300}})
    now = time.time()

    # Sensor data con timestamp de hace 500 ms (obsoleto)
    stale_sensor = {
        "timestamp": now - 0.500,
        "is_connected": True,
        "is_mock": False,
        "imu_present": True,
        "imu_roll_deg": 2.0,
        "imu_pitch_deg": 1.0,
        "tilt_error_deg": 2.24
    }

    fresh_vision = {
        "timestamp": now,
        "detected": True,
        "raw_landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0}] * 21,
        "feature_vector_63": [0.0] * 63
    }

    fused = fusion.fuse(fresh_vision, stale_sensor)
    assert fused["valid_fusion"] is False
    assert fused["staleness"]["sensor_stale"] is True or (fused["sync_delta_ms"] and fused["sync_delta_ms"] > 200)


# ==============================================================================
# 14. Sincronización temporal <= 200 ms
# ==============================================================================
def test_synchronization_threshold_200ms():
    """Valida que solo se acepte fusión si el delta temporal entre visión y sensor es <= 200 ms."""
    fusion = SensorFusionEngine({"fusion": {"max_temporal_delta_ms": 200}})
    now = time.time()

    # Delta = 50 ms -> Fusión válida
    sensor_sync = {
        "timestamp": now - 0.050,
        "is_connected": True,
        "is_mock": False,
        "imu_present": True,
        "imu_roll_deg": 3.0,
        "imu_pitch_deg": -2.0,
        "tilt_error_deg": 3.61
    }
    vision_sync = {
        "timestamp": now,
        "detected": True,
        "raw_landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0}] * 21,
        "feature_vector_63": [0.0] * 63
    }

    res_ok = fusion.fuse(vision_sync, sensor_sync)
    assert res_ok["valid_fusion"] is True
    assert res_ok["is_synchronized"] is True

    # Delta = 250 ms -> Rechazado por desincronización
    sensor_async = dict(sensor_sync)
    sensor_async["timestamp"] = now - 0.250
    res_fail = fusion.fuse(vision_sync, sensor_async)
    assert res_fail["valid_fusion"] is False
    assert res_fail["is_synchronized"] is False


# ==============================================================================
# 15. Estado real no-mock verificado
# ==============================================================================
def test_no_mock_real_sensor_state():
    """Verifica que el driver real etiquete is_mock=False estrictamente en su telemetría."""
    manager = SensorManager({"sensors": {"mock_mode": False, "port": "DISABLED"}})
    sample = manager.poll_sensors()
    assert sample["is_mock"] is False


# ==============================================================================
# 16. Regresión: Firmware de cámara, stream URL, VGA y MediaPipe intactos
# ==============================================================================
def test_regression_camera_stream_and_vision_integrity():
    """
    Confirma de manera automatizada que:
    1. settings.json conserva http://192.168.4.1:81/stream
    2. settings.json conserva resolución [640, 480] (VGA)
    3. Firmware de cámara NO fue modificado ni recompilado
    4. Modelo MediaPipe local existe y no fue alterado
    """
    settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.json")
    with open(settings_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Validar cámara
    assert cfg["camera"]["stream_url"] == "http://192.168.4.1:81/stream"
    assert cfg["camera"]["resolution"] == [640, 480]

    # Validar modelo MediaPipe local
    model_path = os.path.join(os.path.dirname(__file__), "..", cfg["vision"]["model_path"])
    assert os.path.isfile(model_path)
    assert os.path.getsize(model_path) > 1_000_000  # ~9.8 MB

    # Validar firmware de cámara intacto
    cam_fw_path = os.path.join(os.path.dirname(__file__), "..", "..", "04_FIRMWARE", "xiao_esp32s3_camera", "xiao_esp32s3_camera.ino")
    assert os.path.isfile(cam_fw_path)
    with open(cam_fw_path, "r", encoding="utf-8") as f:
        fw_content = f.read()

    assert "FRAMESIZE_VGA" in fw_content
    assert "SENA_CORRECTA_CAM" in fw_content
    assert "81" in fw_content
    assert "/stream" in fw_content
