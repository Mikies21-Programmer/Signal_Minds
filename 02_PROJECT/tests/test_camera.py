"""
Pruebas unitarias y de integración para CameraConsumer.
Valida estados, buffer=1, producción de ndarray real y diferenciación mock vs real.
"""

import time
import numpy as np
import pytest
from src.camera.consumer import CameraConsumer, ConnectionStatus


def test_camera_initial_state():
    consumer = CameraConsumer()
    assert consumer.get_status() == ConnectionStatus.DISCONNECTED
    assert consumer.get_latest_frame() is None


def test_camera_mock_mode_produces_real_ndarray():
    config = {
        "camera": {
            "mock_mode": True,
            "target_fps": 30,
            "resolution": [320, 240]
        }
    }
    consumer = CameraConsumer(config)
    consumer.start()
    assert consumer.get_status() == ConnectionStatus.STREAMING

    # Esperar al primer fotograma generado en el hilo
    time.sleep(0.1)
    frame_data = consumer.get_latest_frame()
    assert frame_data is not None
    assert "frame" in frame_data
    assert isinstance(frame_data["frame"], np.ndarray)
    assert frame_data["frame"].shape == (240, 320, 3)
    assert frame_data["is_mock"] is True
    assert frame_data["status"] == "STREAMING"
    assert frame_data["timestamp"] > 0

    consumer.stop()
    assert consumer.get_status() == ConnectionStatus.DISCONNECTED


def test_camera_real_mode_unreachable_does_not_fabricate_data():
    """
    En REAL HARDWARE MODE, si la IP/stream no existe, NO debe devolver frames simulados.
    Debe reportar CONNECTING o RECONNECTING y devolver None para get_latest_frame.
    """
    config = {
        "camera": {
            "mock_mode": False,
            "stream_url": "http://192.0.2.1:9999/nonexistent_stream",
            "timeout_sec": 0.5
        }
    }
    consumer = CameraConsumer(config)
    consumer.start()

    # Inmediatamente tras arrancar en modo real debe estar conectando/reconectando
    status = consumer.get_status()
    assert status in (ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING, ConnectionStatus.ERROR)

    # NO debe haber inventado ningún fotograma
    assert consumer.get_latest_frame() is None

    consumer.stop()
    assert consumer.get_status() == ConnectionStatus.DISCONNECTED
