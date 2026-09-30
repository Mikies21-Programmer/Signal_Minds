"""
Pruebas del motor de fusión sensorial temporal y correlación multimodal
(Visión Artificial + Telemetría de Ultrasonido).
Valida detección de obsolescencia, sincronización, modos de fusión,
orientación visual y distancia ultrasónica.
"""

import time
from src.fusion.engine import SensorFusionEngine


def test_fusion_modes_and_synchronization():
    engine = SensorFusionEngine({"fusion": {"max_staleness_sec": 0.5, "max_sync_delta_sec": 0.2}})
    now = time.time()

    # Caso 1: Solo visión (sensor ausente o desconectado)
    vis_data = {
        "detected": True,
        "timestamp": now,
        "raw_landmarks": [{"id": i, "x": 0.5, "y": 0.5, "z": 0.0} for i in range(21)],
        "handedness": "Right",
        "feature_vector_63": [0.1] * 63,
        "status": "STREAMING"
    }
    sens_disconnected = {
        "timestamp": now,
        "is_connected": False,
        "distance_valid": False,
        "distance_cm": None,
        "status": "DISCONNECTED"
    }
    res_vis_only = engine.fuse(vis_data, sens_disconnected)
    assert res_vis_only["fusion_mode"] == "VISION_ONLY"
    assert res_vis_only["vision_present"] is True
    assert res_vis_only["sensors_present"] is False
    assert res_vis_only["hand_detected"] is True
    assert res_vis_only["distance_valid"] is False
    assert res_vis_only["orientation"] in ["PALM", "BACK", "SIDE", "UNKNOWN"]

    # Caso 2: Fusión multimodal completa (visión + ultrasonido conectados y sincronizados)
    sens_connected = {
        "timestamp": now + 0.02,
        "is_connected": True,
        "distance_valid": True,
        "distance_cm": 45.5,
        "status": "CONNECTED"
    }
    res_multimodal = engine.fuse(vis_data, sens_connected)
    assert res_multimodal["valid_fusion"] is True
    assert res_multimodal["fusion_mode"] == "FULL_MULTIMODAL"
    assert res_multimodal["diagnostics"]["is_synchronized"] is True
    assert res_multimodal["distance_valid"] is True
    assert res_multimodal["distance_cm"] == 45.5
    assert res_multimodal["sensor_connected"] is True


def test_fusion_staleness_detection():
    """Valida que datos antiguos (> max_staleness_sec) sean marcados como obsoletos y no produzcan fusión completa."""
    engine = SensorFusionEngine({"fusion": {"max_staleness_sec": 0.3}})
    old_timestamp = time.time() - 2.0  # 2 segundos de antigüedad

    vis_stale = {
        "detected": True,
        "timestamp": old_timestamp,
        "feature_vector_63": [0.1] * 63
    }
    sens_fresh = {
        "timestamp": time.time(),
        "is_connected": True,
        "distance_valid": True,
        "distance_cm": 35.0,
        "status": "CONNECTED"
    }
    res = engine.fuse(vis_stale, sens_fresh)
    assert res["vision_present"] is False
    assert res["sensors_present"] is True
    assert res["fusion_mode"] == "SENSORS_ONLY"
    assert res["valid_fusion"] is False


def test_fusion_camera_or_sensor_disconnected():
    engine = SensorFusionEngine()
    res = engine.fuse(None, None)
    assert res["valid_fusion"] is False
    assert res["fusion_mode"] == "NO_DATA"
    assert res["camera_connected"] is False
    assert res["sensor_connected"] is False
    assert res["distance_valid"] is False
    assert res["orientation"] == "UNKNOWN"
