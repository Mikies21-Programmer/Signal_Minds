"""
Pruebas de la API local y WebSockets para INDIVISA INGENIUM 2026.
"""

import json
from fastapi.testclient import TestClient
from src.backend.api import create_app
from src.backend.orchestrator import SystemOrchestrator


def get_test_app():
    config = {
        "camera": {"mock_mode": True, "target_fps": 20},
        "vision": {"mock_mode": True},
        "sensors": {"mock_mode": True},
        "lsm": {"default_target_sign": "A"}
    }
    orchestrator = SystemOrchestrator(config)
    orchestrator.step()
    return create_app(orchestrator)


def test_api_index_html():
    client = TestClient(get_test_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "INDIVISA INGENIUM 2026" in response.text


def test_api_health_endpoint():
    client = TestClient(get_test_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "subsystems" in data


def test_api_set_sign_valid_and_invalid():
    client = TestClient(get_test_app())
    res_b = client.post("/api/sign/B")
    assert res_b.status_code == 200
    assert res_b.json()["target_sign"] == "B"

    res_inv = client.post("/api/sign/W")  # W no es parte de las señas implementadas
    assert res_inv.status_code == 400


def test_api_pause_and_recalibrate():
    client = TestClient(get_test_app())
    res_pause = client.post("/api/pause")
    assert res_pause.status_code == 200
    assert "is_paused" in res_pause.json()

    res_cal = client.post("/api/recalibrate")
    assert res_cal.status_code == 200
    assert res_cal.json()["status"] == "SUCCESS"


def test_api_websocket_telemetry():
    client = TestClient(get_test_app())
    with client.websocket_connect("/ws/telemetry") as websocket:
        data = websocket.receive_json()
        assert "target_sign" in data
        assert "camera_status" in data

        # Enviar comando de cambio de seña
        websocket.send_text(json.dumps({"action": "SET_SIGN", "sign": "L"}))
        data_updated = websocket.receive_json()
        assert data_updated["target_sign"] == "L"
