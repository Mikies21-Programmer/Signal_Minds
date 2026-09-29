"""
Pruebas del motor de retroalimentación pedagógica en tiempo real.
Verifica instrucciones específicas anatómicas y prohibición de frases genéricas vacías.
"""

from src.feedback.engine import FeedbackEngine


def test_feedback_success_message():
    engine = FeedbackEngine()
    eval_success = {
        "is_valid": True,
        "sign": "A",
        "overall_score": 0.88,
        "parameters": {
            "configuration": {"score": 0.90, "status": "PASS"},
            "orientation": {"score": 0.85, "status": "PASS"},
            "movement": {"score": 1.0, "status": "PASS"},
            "location": {"score": 0.95, "status": "PASS"}
        }
    }
    fb = engine.generate_feedback(eval_success)
    assert fb["status"] == "SUCCESS"
    assert "¡Excelente!" in fb["primary_message"]
    assert "A" in fb["primary_message"]
    assert "Inténtalo nuevamente" not in fb["primary_message"]
    assert "Inténtalo nuevamente" not in fb["secondary_message"]


def test_feedback_configuration_error_gives_specific_anatomical_hint():
    engine = FeedbackEngine()
    eval_fail_config = {
        "is_valid": False,
        "sign": "B",
        "overall_score": 0.50,
        "parameters": {
            "configuration": {
                "score": 0.40,
                "status": "CORRECT",
                "reason": "Extiende el dedo anular"
            },
            "orientation": {"score": 0.90, "status": "PASS"},
            "movement": {"score": 1.0, "status": "PASS"},
            "location": {"score": 0.95, "status": "PASS"}
        }
    }
    fb = engine.generate_feedback(eval_fail_config)
    assert fb["status"] == "NEEDS_CORRECTION"
    assert "Extiende el dedo anular" in fb["secondary_message"]
    assert "Inténtalo nuevamente" not in fb["primary_message"]
    assert "Inténtalo nuevamente" not in fb["secondary_message"]


def test_feedback_no_hand():
    engine = FeedbackEngine()
    eval_no_hand = {
        "is_valid": False,
        "sign": "L",
        "overall_score": 0.0,
        "message": "Sin mano detectada en el encuadre",
        "parameters": {
            "configuration": {"score": 0.0, "status": "FAIL", "reason": "No se detecta mano."},
            "orientation": {"score": 0.0, "status": "FAIL"},
            "movement": {"score": 0.0, "status": "FAIL"},
            "location": {"score": 0.0, "status": "FAIL"}
        }
    }
    fb = engine.generate_feedback(eval_no_hand)
    assert fb["status"] == "NO_HAND"
    assert "No se detecta mano" in fb["primary_message"]
    assert "Inténtalo nuevamente" not in fb["primary_message"]
