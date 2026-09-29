# Bitácora de Progreso de Implementación MVP — INDIVISA INGENIUM 2026

**Fecha de Actualización:** 29 de septiembre de 2026  
**Objetivo:** Transición de MVP de Software a Integración de Hardware Físico-Real.  
**Estándar:** Sin mocks en modo real, sin suposición de hardware ni pines, evidencia física obligatoria.

---

## 1. SOFTWARE VERIFIED (100% COMPLETADO)

Todas las pruebas de software base, lógica morfológica, streaming y APIs se encuentran completamente implementadas y certificadas con **46/46 pruebas unitarias y de integración pasando en verde**.

| PASO | CAMBIO | PRUEBA | RESULTADO | ERRORES | ESTADO |
|------|--------|--------|-----------|---------|--------|
| **P0-1** | Descomentar y fijar dependencias compatibles en `requirements.txt` (numpy 1.26.4, opencv-python-headless 4.10, mediapipe 1.0.1, fastapi, uvicorn, websockets, pyserial, pytest). Purga de 27 archivos `.pyc` en git index y actualización de `.gitignore`. | `python -c "import numpy, cv2, mediapipe, fastapi, uvicorn, websockets, serial, pytest"` y `pytest tests/test_imports.py` | 100% éxito en importación y resolución de dependencias binarias. | Ninguno tras compatibilizar numpy 1.x con mediapipe. | **SOFTWARE VERIFIED** |
| **P0-2** | Implementación de `CameraConsumer` real en `src/camera/consumer.py` con hilo desacoplado, buffer=1 de OpenCV, timeout, reconexión automática, métricas de FPS, timestamp real y retorno de ndarray. | `pytest tests/test_camera.py` | 3 pruebas pasadas: estados DISCONNECTED/STREAMING, producción de ndarray real, rechazo de datos inventados si la cámara está ausente. | Ninguno. | **SOFTWARE VERIFIED** |
| **P0-3** | Implementación de `VisionPipeline` real en `src/vision/pipeline.py` con modelo local offline `models/hand_landmarker.task`. Verificación de existencia del archivo (error claro sin descargas en runtime), extracción de 21 landmarks reales, vector normalizado 63D, sin landmarks sintéticos en modo real. | `pytest tests/test_vision.py` | 4 pruebas pasadas: rechazo de archivo inexistente, imagen negra devuelve detected=False sin inventar puntos, normalización P0 en origen [0,0,0], etiquetado de mock. | Ninguno. | **SOFTWARE VERIFIED** |
| **P0-4** | Creación de servidor FastAPI en `src/backend/api.py` con streaming MJPEG `/video_feed` con HUD anotado, WebSocket dúplex `/ws/telemetry`, endpoints REST de control y lifespan asíncrono. | `pytest tests/test_api.py` | 5 pruebas pasadas: servicio de index HTML, health check, cambio de seña A/B/C/L/Y, pausa, recalibración y telemetría WebSocket. | Deprecación de on_event corregida a lifespan. | **SOFTWARE VERIFIED** |
| **P0-5** | Desarrollo de interfaz web desacoplada en `src/frontend/static/index.html` para la Laptop (sin pantalla CLB7INH). Muestra video, estado de cámara, FPS, landmarks, seña objetivo, veredicto, score, feedback explicable, telemetría y atajos de teclado físicos (A, B, C, L, Y, ESPACIO, R, TAB). | Inspección de DOM, validación de binding WebSocket y `test_api_index_html`. | Renderizado visual y canalización de atajos de teclado hacia el backend. | Ninguno. | **SOFTWARE VERIFIED** |
| **P1-1** | Arquitectura de driver para sensores en `src/sensors/manager.py` (`SensorManager` y `SensorBackend`: `RealHardwareSensorBackend` y `MockSensorBackend`). Detección de puertos serie, timestamps reales, diagnóstico sin asumir pines/direcciones desconocidas. | `pytest tests/test_sensors.py` | 3 pruebas pasadas: modo mock etiquetado, modo real sin conexión reporta DISCONNECTED sin inventar lecturas, tara/calibración. | Ninguno. | **SOFTWARE VERIFIED** |
| **P1-2** | Fusión sensorial con verificación temporal estricta en `src/fusion/engine.py`. Detección de obsolescencia (>500ms), delta temporal de sincronización (<200ms) y rechazo explícito de `has_vision OR has_sensors` como falsa fusión. | `pytest tests/test_fusion.py` | 3 pruebas pasadas: distinción FULL_MULTIMODAL vs VISION_ONLY vs SENSORS_ONLY, detección de timestamps obsoletos. | Ninguno. | **SOFTWARE VERIFIED** |
| **P1-3** | Creación de especificación en `03_DOCS/lsm/LSM_LEVEL_1_SPECIFICATION.md`, módulo de cinemática explicable `src/lsm/geometry.py` y evaluador morfológico en `src/lsm/evaluator.py` para señas A, B, C, L, Y con relaciones articulares y distancias inter-falángicas. | `pytest tests/test_lsm_geometric.py` | 3 pruebas pasadas: extracción de flexión/extensión, rechazo de seña incorrecta aunque haya mano presente, validación de A, B, C, L, Y. | Ninguno. | **SOFTWARE VERIFIED** |
| **P1-4** | Motor de feedback pedagógico en `src/feedback/engine.py` estructurado por parámetros constitutivos (queirema, orientación, kinema, toponema). Emite directivas anatómicas concretas y prohíbe frases genéricas como 'Inténtalo nuevamente'. | `pytest tests/test_feedback.py` | 3 pruebas pasadas: mensaje de éxito, pista anatómica específica de flexión/extensión y detección de ausencia de mano. | Ninguno. | **SOFTWARE VERIFIED** |
| **P1-5** | Endurecimiento de `HealthChecker` (estados HEALTHY, DEGRADED, NOT_READY, ERROR; nunca reporta HEALTHY si hay mocks o hardware UNKNOWN). Pruebas de integración E2E en `tests/test_integration_mvp.py` y catálogo de `PENDING HARDWARE VERIFICATION`. | `pytest tests/test_health.py tests/test_integration_mvp.py` y suite completa de 46 tests. | 46/46 pruebas pasadas con 100% de éxito. Flujo físico-real validado en software. | Ninguno. | **SOFTWARE VERIFIED** |

---

## 2. HARDWARE VERIFIED (FASE FÍSICA EN PROCESO)

Esta sección registra únicamente las comprobaciones realizadas sobre componentes físicos reales presentes en el banco de trabajo.

| COMPONENTE FÍSICO | ACCIÓN REQUERIDA | SCRIPT / HERRAMIENTA | EVIDENCIA REQUERIDA | ESTADO ACTUAL |
|-------------------|------------------|----------------------|---------------------|---------------|
| **Raspberry Pi 5** | Encender placa, configurar venv y extraer diagnóstico de hardware con comandos oficiales. | `02_PROJECT/scripts/collect_rpi_info.sh` | `04_EVIDENCE/hardware/rpi_info.txt` | **PENDIENTE ARRANQUE FÍSICO** |
| **ESP32-CAM** | Inspección visual de serigrafía (frontal y trasera) para determinar fabricante, sensor óptico y PSRAM. | Inspección física / Fotografías | Entrada en `HARDWARE_INVENTORY.md` | **PENDIENTE FOTOGRAFÍAS** |
| **Stream ESP32-CAM** | Transmisión continua Wi-Fi hacia Raspberry Pi / Laptop durante mínimo 5 minutos ininterrumpidos. | `02_PROJECT/scripts/test_camera_real.py` | `04_EVIDENCE/hardware/camera_test.txt` | **PENDIENTE IDENTIFICACIÓN CÁMARA** |
| **MediaPipe en Video Real** | Detección estable de mano física real (mínimo 30 frames consecutivos con conf > 70%). | `02_PROJECT/scripts/test_vision_real.py` | `04_EVIDENCE/hardware/vision_test.txt` y captura fotográfica | **PENDIENTE TRANSMISIÓN DE CÁMARA** |
| **Sensor Mecatrónico** | Proporcionar componente físico en mesa; verificar interfaz (I2C/UART), pines y alimentación. | Detección de puerto / `i2cdetect` | `04_EVIDENCE/hardware/sensor_test.txt` | **PENDIENTE COMPONENTE FÍSICO** |
| **Fusión Real** | Fusión temporal en vivo ($\Delta t \le 200\text{ ms}$) con cámara y sensor físico operando simultáneamente. | `src/backend/api.py` (Orchestrator) | `04_EVIDENCE/hardware/integration_test.txt` | **PENDIENTE CÁMARA + SENSOR REAL** |
| **Demostración MVP Completa** | Visualización en vivo en Laptop Browser sin CLB7INH con control por teclado (A, B, C, L, Y). | Laptop Browser (`http://localhost:8000`) | Registro de sesión y telemetría completa | **PENDIENTE INTEGRACIÓN FINAL** |
