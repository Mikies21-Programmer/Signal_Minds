"""
Excepciones personalizadas para el proyecto INDIVISA INGENIUM 2026.
Jerarquía formal de errores para garantizar diagnóstico claro y explicable.
"""

class IndivisaError(Exception):
    """Excepción base para todos los errores de INDIVISA INGENIUM."""
    def __init__(self, message: str, module: str = "core", code: str = "ERR_GENERIC"):
        super().__init__(message)
        self.message = message
        self.module = module
        self.code = code

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "module": self.module,
            "code": self.code,
            "message": self.message
        }


class ConfigurationError(IndivisaError):
    """Error en la carga o validación de configuración."""
    def __init__(self, message: str):
        super().__init__(message, module="config", code="ERR_CONFIG")


class HardwareConnectionError(IndivisaError):
    """Error al comunicarse con un periférico de hardware real."""
    def __init__(self, message: str, device: str = "unknown"):
        super().__init__(f"[{device}] {message}", module="hardware", code="ERR_HW_CONN")
        self.device = device


class CameraStreamError(HardwareConnectionError):
    """Error en la ingesta o flujo de video del ESP32-CAM."""
    def __init__(self, message: str):
        super().__init__(message, device="ESP32-CAM")
        self.code = "ERR_CAMERA"


class SensorReadError(HardwareConnectionError):
    """Error al leer la segunda fuente mecatrónica de sensores."""
    def __init__(self, message: str):
        super().__init__(message, device="MecatronicSensors")
        self.code = "ERR_SENSOR"


class VisionInferenceError(IndivisaError):
    """Error en el pipeline de visión artificial o MediaPipe."""
    def __init__(self, message: str):
        super().__init__(message, module="vision", code="ERR_VISION")


class LSMValidationError(IndivisaError):
    """Error o discrepancia en el motor de validación lingüística de LSM."""
    def __init__(self, message: str, sign: str = ""):
        super().__init__(f"[{sign}] {message}", module="lsm", code="ERR_LSM_VAL")
        self.sign = sign
