"""
Pruebas de importación de módulos para INDIVISA INGENIUM 2026.
Garantiza que todos los subsistemas puedan importarse limpiamente sin errores de sintaxis o dependencias circulares.
"""

import sys
from pathlib import Path

# Asegurar path de 02_PROJECT
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_import_backend():
    import src.backend as backend
    assert hasattr(backend, "ConfigLoader")
    assert hasattr(backend, "HealthChecker")
    assert hasattr(backend, "SystemOrchestrator")
    assert hasattr(backend, "setup_logger")
    assert hasattr(backend, "IndivisaError")


def test_import_camera():
    import src.camera as camera
    assert hasattr(camera, "CameraConsumer")
    assert hasattr(camera, "ConnectionStatus")


def test_import_vision():
    import src.vision as vision
    assert hasattr(vision, "VisionPipeline")


def test_import_sensors():
    import src.sensors as sensors
    assert hasattr(sensors, "SensorManager")


def test_import_fusion():
    import src.fusion as fusion
    assert hasattr(fusion, "SensorFusionEngine")


def test_import_lsm():
    import src.lsm as lsm
    assert hasattr(lsm, "LSMEvaluator")


def test_import_feedback():
    import src.feedback as feedback
    assert hasattr(feedback, "FeedbackEngine")


def test_import_frontend():
    import src.frontend as frontend
    assert hasattr(frontend, "FrontendController")


def test_import_external_dependencies():
    import numpy as np
    import cv2
    import mediapipe as mp
    import fastapi
    import uvicorn
    import websockets
    import serial
    assert np is not None
    assert cv2 is not None
    assert mp is not None
    assert fastapi is not None
    assert uvicorn is not None
    assert websockets is not None
    assert serial is not None
