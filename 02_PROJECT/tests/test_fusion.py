"""
Pruebas del motor de fusión sensorial temporal y correlación multimodal.
Valida detección de obsolescencia, sincronización y rechazo de falsa fusión.
"""

import time
from src.fusion.engine import SensorFusionEngine


def test_fusion_requires_both_modalities_and_synchronization():
    engine = SensorFusionEngine({"fusion": {"max_staleness_sec": 0.5, "max_sync_delta_sec": 0.2}})
    now = time.time()

    # Caso 1: Solo visión (sensores ausentes o desconectados) -> NO debe ser valid_fusion
    vis_data = {
        "detected": True,
        "timestamp": now,
        "feature_vector_63": [0.1] * 63,
        "status": "STREAMING"
    }
    sens_disconnected = {
        "timestamp": now,
        "is_connected": False,
        "status": "DISCONNECTED"
    }
    res_vis_only = engine.fuse(vis_data, sens_disconnected)
    assert res_vis_only["valid_fusion"] is False
    assert res_vis_only["fusion_mode"] == "VISION_ONLY"
    assert res_vis_only["vision_present"] is True
    assert res_vis_only["sensors_present"] is False

    # Caso 2: Fusión multimodal completa (ambos presentes y sincronizados) -> valid_fusion = True
    sens_connected = {
        "timestamp": now + 0.02,
        "is_connected": True,
        "status": "CONNECTED",
        "flex_thumb": 0.1,
        "imu_roll_deg": 2.0
    }
    res_multimodal = engine.fuse(vis_data, sens_connected)
    assert res_multimodal["valid_fusion"] is True
    assert res_multimodal["fusion_mode"] == "FULL_MULTIMODAL"
    assert res_multimodal["is_synchronized"] is True


def test_fusion_staleness_detection():
    """Valida que datos antiguos (> max_staleness_sec) sean marcados como obsoletos y no produzcan fusión válida."""
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
        "status": "CONNECTED"
    }
    res = engine.fuse(vis_stale, sens_fresh)
    assert res["valid_fusion"] is False
    assert res["staleness"]["vision_stale"] is True
    assert res["vision_present"] is False


def test_fusion_camera_or_sensor_disconnected():
    engine = SensorFusionEngine()
    res = engine.fuse(None, None)
    assert res["valid_fusion"] is False
    assert res["fusion_mode"] == "NO_DATA"
    assert res["camera_connected"] is False
    assert res["sensor_connected"] is False
