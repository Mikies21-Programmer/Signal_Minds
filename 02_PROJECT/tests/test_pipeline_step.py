"""
Pruebas del ciclo del pipeline integrado y evaluación Nivel 1.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.backend.config_loader import ConfigLoader
from src.backend.orchestrator import SystemOrchestrator
from src.frontend.controller import FrontendController


def test_orchestrator_single_step():
    config = ConfigLoader()
    orchestrator = SystemOrchestrator(config)
    orchestrator.start()
    result = orchestrator.step()
    orchestrator.stop()

    assert result["frame_id"] == 1
    assert result["target_sign"] == "A"
    assert result["pipeline_latency_ms"] >= 0.0
    assert "evaluation" in result
    assert "feedback" in result
    assert "sensor_telemetry" in result
    assert result["has_hand"] is True


def test_level_1_signs_evaluation():
    config = ConfigLoader()
    orchestrator = SystemOrchestrator(config)
    orchestrator.start()

    level_1 = ["A", "B", "C", "L", "Y"]
    for sign in level_1:
        orchestrator.set_target_sign(sign)
        res = orchestrator.step()
        assert res["target_sign"] == sign
        eval_data = res["evaluation"]
        assert eval_data["sign"] == sign
        assert "configuration" in eval_data["parameters"]
        assert "orientation" in eval_data["parameters"]
        assert "movement" in eval_data["parameters"]
        assert "location" in eval_data["parameters"]

    orchestrator.stop()


def test_frontend_keyboard_shortcuts():
    config = ConfigLoader()
    controller = FrontendController(config)

    # Test selección directa
    res_b = controller.handle_keyboard_input("b")
    assert res_b["action"] == "SET_SIGN"
    assert res_b["sign"] == "B"

    res_y = controller.handle_keyboard_input("Y")
    assert res_y["action"] == "SET_SIGN"
    assert res_y["sign"] == "Y"

    # Test pausa
    res_pause = controller.handle_keyboard_input(" ")
    assert res_pause["action"] == "TOGGLE_PAUSE"
    assert res_pause["is_paused"] is True

    # Test recalibración
    res_recal = controller.handle_keyboard_input("r")
    assert res_recal["action"] == "RECALIBRATE"
