"""
Módulo de adquisición de imagen y cliente ESP32-CAM.
"""

from .consumer import CameraConsumer, ConnectionStatus

__all__ = ["CameraConsumer", "ConnectionStatus"]
