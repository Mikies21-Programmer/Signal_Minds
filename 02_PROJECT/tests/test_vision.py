"""
Pruebas para VisionPipeline.
Valida carga offline de modelo local, comportamiento real vs mock y normalización geométrica.
"""

import numpy as np
import pytest
from src.vision.pipeline import VisionPipeline, VisionPipelineError


def test_vision_pipeline_missing_model_raises_clear_error():
    config = {
        "vision": {
            "mock_mode": False,
            "model_path": "models/non_existent_model_file.task"
        }
    }
    with pytest.raises(VisionPipelineError) as exc_info:
        VisionPipeline(config)
    assert "ERROR CLARO DE MODELO LOCAL" in str(exc_info.value)
    assert "no se permite la descarga automática" in str(exc_info.value)


def test_vision_pipeline_real_mode_empty_image_never_fabricates_landmarks():
    """En modo REAL, si no hay mano visible, detected debe ser False y landmarks vacíos."""
    config = {
        "vision": {
            "mock_mode": False,
            "min_detection_confidence": 0.5
        }
    }
    pipeline = VisionPipeline(config)
    black_image = np.zeros((240, 320, 3), dtype=np.uint8)

    result = pipeline.process_frame(black_image)
    assert result is not None
    assert result["detected"] is False
    assert result["hand_count"] == 0
    assert result["raw_landmarks"] == []
    assert result["feature_vector_63"] == []
    assert result["confidence"] == 0.0
    assert result["is_mock"] is False


def test_vision_pipeline_mock_mode_tagging():
    """En modo MOCK, se etiquetan explícitamente los datos como is_mock=True."""
    config = {
        "vision": {
            "mock_mode": True
        }
    }
    pipeline = VisionPipeline(config)
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = pipeline.process_frame(dummy_img)

    assert result is not None
    assert result["detected"] is True
    assert result["is_mock"] is True
    assert len(result["raw_landmarks"]) == 21
    assert len(result["feature_vector_63"]) == 63


def test_vision_normalization_p0_at_origin():
    """Verifica que la normalización invariante fije la muñeca P0 en [0, 0, 0]."""
    pipeline = VisionPipeline({"vision": {"mock_mode": True}})
    raw = [{"id": i, "x": float(i), "y": float(i * 2), "z": 0.5} for i in range(21)]
    norm = pipeline.normalize_landmarks(raw)

    assert len(norm) == 63
    # P0 (x0, y0, z0) debe ser (0, 0, 0)
    assert norm[0] == 0.0
    assert norm[1] == 0.0
    assert norm[2] == 0.0
