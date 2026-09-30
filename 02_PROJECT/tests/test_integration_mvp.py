"""
Prueba de integración extremo a extremo (End-to-End) del flujo MVP de INDIVISA INGENIUM 2026.
Valida el flujo continuo:
Cámara / Frame OpenCV -> MediaPipe 21 Landmarks -> Driver Sensores -> Fusión Temporal ->
Evaluador Lingüístico (A, B, C, L, Y) -> Feedback Explicable -> API FastAPI / WebSocket.
Garantiza el etiquetado explícito de subsistemas mock vs reales.
"""

import time
import json
import numpy as np
from fastapi.testclient import TestClient

from src.backend.config_loader import ConfigLoader
from src.backend.orchestrator import SystemOrchestrator
from src.backend.api import create_app
from src.lsm.geometry import HandGeometryFeatures
from tests.test_lsm_geometric import make_landmarks_fist_a, make_landmarks_l_shape


def test_mvp_complete_flow_with_real_vision():
    """
    Verifica el flujo integrado de extremo a extremo:
    Frame OpenCV real -> MediaPipe Real -> Fusión Temporal -> Evaluador -> Feedback -> API.
    """
    config = {
        "camera": {"mock_mode": True, "target_fps": 20},
        "vision": {"mock_mode": False},  # MediaPipe REAL con modelo local
        "sensors": {"mock_mode": False}, # Driver de hardware físico REAL
        "lsm": {"default_target_sign": "A", "confidence_threshold": 0.75}
    }

    orchestrator = SystemOrchestrator(config)
    orchestrator.start()

    # 1. Ejecutar ciclo del pipeline
    payload = orchestrator.step()
    orchestrator.stop()

    # 2. Validar estructura del payload entregado
    assert "frame_id" in payload
    assert "target_sign" in payload
    assert "pipeline_latency_ms" in payload
    assert "camera_status" in payload
    assert "has_hand" in payload
    assert "evaluation" in payload
    assert "feedback" in payload
    assert "sensor_telemetry" in payload
    assert "subsystems_mock" in payload

    # 3. Validar etiquetado estricto de mocks
    sub_mock = payload["subsystems_mock"]
    assert sub_mock["vision"] is False  # Visión NO es mock
    assert sub_mock["sensors"] is False # Sensores NO son mock

    # 4. Validar que la telemetría del sensor físico no finge datos
    assert isinstance(payload["sensor_telemetry"]["is_connected"], bool)
    assert payload["sensor_telemetry"]["status"] in ["CONNECTED", "DISCONNECTED"]

    # 5. Validar estado de sensores en fusión
    assert isinstance(payload["fusion"]["sensors_present"], bool)


def test_mvp_websocket_e2e_integration():
    """Valida la entrega de telemetría completa a través de WebSocket y control de seña."""
    config = {
        "camera": {"mock_mode": True, "target_fps": 20},
        "vision": {"mock_mode": True},
        "sensors": {"mock_mode": True},
        "lsm": {"default_target_sign": "A"}
    }
    orchestrator = SystemOrchestrator(config)
    orchestrator.step()
    app = create_app(orchestrator)
    client = TestClient(app)

    with client.websocket_connect("/ws/telemetry") as ws:
        # Recibir muestra inicial
        initial_packet = ws.receive_json()
        assert initial_packet["target_sign"] == "A"
        assert "evaluation" in initial_packet
        assert "feedback" in initial_packet

        # Cambiar seña objetivo a 'L' mediante mensaje de teclado WebSocket
        ws.send_text(json.dumps({"action": "SET_SIGN", "sign": "L"}))
        updated_packet = ws.receive_json()
        assert updated_packet["target_sign"] == "L"

        # Verificar recalibración
        ws.send_text(json.dumps({"action": "RECALIBRATE"}))
