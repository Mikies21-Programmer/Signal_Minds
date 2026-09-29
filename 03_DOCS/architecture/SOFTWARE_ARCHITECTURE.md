# Arquitectura de Software — INDIVISA INGENIUM 2026

**Documento:** [`03_DOCS/architecture/SOFTWARE_ARCHITECTURE.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/architecture/SOFTWARE_ARCHITECTURE.md)  
**Proyecto:** Sistema Mecatrónico y Visión Artificial para Retroalimentación de LSM en Tiempo Real  
**Fundamento:** Convocatoria Oficial ([`00_OFFICIAL/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/00_OFFICIAL)), Repositorios de Referencia ([`01_REFERENCES/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/01_REFERENCES)), Auditorías ([`03_DOCS/audits/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/audits)) e Inventario de Hardware ([`03_DOCS/hardware/HARDWARE_INVENTORY.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/hardware/HARDWARE_INVENTORY.md)).  
**Cumplimiento Normativo:** Sujeto a las 24 Reglas Obligatorias de [`AGENTS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/AGENTS.md).

---

## 1. Topología del Sistema Distribuido

La arquitectura se divide en tres niveles de cómputo físicamente distribuidos y desacoplados:

```text
+---------------------+         Red Local / Bus Serial        +-----------------------------------------------+
|      ESP32-CAM      | ------------------------------------> |                RASPBERRY PI 5                 |
| (Adquisición Video) |       Stream MJPEG / JPEG             |        (Cerebro Central de Cómputo)           |
+---------------------+                                       |                                               |
                                                              |  [camera]  -> Ingesta multihilo               |
+---------------------+         I2C / UART / GPIO             |  [vision]  -> MediaPipe Hands (ARM64)         |
|  Segunda Fuente     | ------------------------------------> |  [sensors] -> Muestreo y filtrado mecatrónico |
|  de Sensores (HW)   |       Telemetría Física               |  [fusion]  -> Fusión Visión + Sensor Físico   |
+---------------------+                                       |  [lsm]     -> Validación Lingüística 4 Puntos |
                                                              |  [feedback]-> Motor de Corrección Explicable  |
                                                              |  [backend] -> Orquestador de Ciclo de Vida    |
                                                              |  [api]     -> Servidor Local WebSocket/HTTP   |
                                                              +-----------------------------------------------+
                                                                                      |
                                                                                      | WebSocket / JSON
                                                                                      | Red Local Offline
                                                                                      v
                                                              +-----------------------------------------------+
                                                              |                    LAPTOP                     |
                                                              |            (Estación de Control)              |
                                                              |                                               |
                                                              |  [frontend]-> Interfaz Gráfica Desacoplada    |
                                                              |  [keyboard]-> Selección de Seña / Control     |
                                                              |  [display] -> Visualización y Guía de Usuario |
                                                              +-----------------------------------------------+
```

---

## 2. Descomposición Modular y Responsabilidades

```text
02_PROJECT/
├── src/
│   ├── backend/      # Orquestador central y supervisor de tareas
│   ├── vision/       # Pipeline MediaPipe Hands y extracción de 63 landmarks
│   ├── camera/       # Cliente de red y consumidor de frames del ESP32-CAM
│   ├── sensors/      # Adquisición, calibración y filtrado de sensores físicos
│   ├── fusion/       # Correlación temporal y espacial (Visión + Sensores)
│   ├── lsm/          # Evaluador lingüístico de señas (Nivel 1, 2 y 3)
│   ├── feedback/     # Motor generador de retroalimentación pedagógica
│   ├── api/          # Servicio WebSocket / REST local para la interfaz
│   └── ui/           # Frontend desacoplado servido a la Laptop
├── models/           # Clasificadores SVM preentrenados y escaladores
├── config/           # Configuraciones de red, puertos y umbrales
└── tests/            # Suite de pruebas unitarias y de integración
```

---

### Módulo 1: `camera/` (Consumidor de Video ESP32-CAM)
- **Responsabilidad:** Conectarse al stream HTTP/MJPEG del ESP32-CAM mediante un hilo independiente (`ThreadedFrameConsumer`), extraer fotogramas JPEG, decodificarlos con OpenCV y mantener en memoria compartida **únicamente el cuadro más reciente** (buffer size = 1) para erradicar la latencia acumulada.
- **Manejo de Desconexión:** Watchdog con temporizador de 1.0 s. Si no se reciben frames, conmuta a estado `RECONNECTING` reintentando sin bloquear el sistema principal.
- **Interfaz Python:**
```python
class CameraConsumer:
    def __init__(self, stream_url: str, timeout_sec: float = 1.0): ...
    def start(self) -> None: ...
    def get_latest_frame(self) -> Optional[np.ndarray]: ...
    def get_status(self) -> ConnectionStatus: ...
    def stop(self) -> None: ...
```

---

### Módulo 2: `vision/` (Pipeline de Visión y Landmarks)
- **Responsabilidad:** Ejecutar el modelo MediaPipe Hands en la CPU Cortex-A76 (ARM64) de la RPi 5. Procesa el frame BGR en modo `IMAGE` o `VIDEO`, detecta la presencia de mano, extrae los 21 puntos anatómicos ($x, y, z$) y aplica normalización con respecto a la muñeca (landmark 0) y distancia euclidiana entre landmark 0 y landmark 9 (base del dedo medio) para invarianza de escala.
- **Salida:** Vector estructurado de 63 descriptores normalizados y estructura de confianza por landmark.
- **Interfaz Python:**
```python
class VisionPipeline:
    def __init__(self, min_detection_confidence: float = 0.6): ...
    def process_frame(self, frame: np.ndarray) -> Optional[HandLandmarksData]: ...
```

---

### Módulo 3: `sensors/` (Adquisición de la Segunda Fuente Mecatrónica)
- **Responsabilidad:** Leer periódicamente la instrumentación física mecatrónica (sensores de flexión o IMU) conectada a la RPi 5 vía bus I2C o UART a 50 Hz. Aplica un filtro de media móvil o paso bajo para suprimir ruido eléctrico y calibra lecturas a rangos normalizados $[0.0, 1.0]$ o ángulos de Euler en grados.
- **Salida:** `SensorFrame` con timestamp de alta resolución sincronizado con el reloj del sistema (`time.perf_counter()`).
- **Interfaz Python:**
```python
class SensorManager:
    def __init__(self, bus_id: int, sampling_rate_hz: int = 50): ...
    def poll_sensors(self) -> SensorFrame: ...
    def calibrate(self) -> CalibrationProfile: ...
```

---

### Módulo 4: `fusion/` (Motor de Fusión Sensorial)
- **Responsabilidad:** Fusión temprana y tardía de datos: correlaciona temporalmente el `HandLandmarksData` más reciente con el `SensorFrame` correspondiente en una ventana de tolerancia $\le 20$ ms. Valida físicamente lo que la visión no puede resolver (e.g. oclusión de dedos en signos cerrados mediante flexión física, y rotación espacial de la muñeca mediante acelerómetro/giróscopo).
- **Salida:** `FusedFeatureVector` que unifica los 63 landmarks visuales con los datos sensoriales físicos.
- **Interfaz Python:**
```python
class SensorFusionEngine:
    def fuse(self, vision_data: Optional[HandLandmarksData], sensor_data: SensorFrame) -> FusedSignState: ...
```

---

### Módulo 5: `lsm/` (Evaluador Lingüístico de LSM)
- **Responsabilidad:** Evaluar los 4 parámetros constitutivos del signo lingüístico:
  1. **Configuración manual (Queirema):** Distancia y curvatura entre dedos, clasificada mediante SVM RBF preentrenado (`LSM-MediaPipe-SVM-main`).
  2. **Orientación:** Vector normal a la palma ($P_0 \to P_5 \times P_0 \to P_{17}$) y verificación con datos de aceleración IMU.
  3. **Movimiento (Kinema):** Monitoreo de trayectoria espacial mediante técnica de pooling temporal (media, desviación y delta de posición de landmarks en ventana de 15 frames) para signos dinámicos.
  4. **Ubicación (Toponema):** Altura y posición relativa de la mano respecto al eje del usuario.
- **Estructura Jerárquica de Señas:**
  - **Nivel 1 (Prioridad Máxima - Estáticas):** `A`, `B`, `C`, `L`, `Y`. Evaluación estricta de Configuración y Orientación.
  - **Nivel 2 (Prioridad Media - Dinámicas/Giro):** `J`, `Ñ`, `Q`, `X`, `Z`. Evaluación de trayectoria, aceleración y pooling estadístico.
  - **Nivel 3 (Prioridad Final - Léxico Complejo):** `HOLA`, `GRACIAS`, `POR FAVOR`, `AYUDA`, `MAMÁ`. Reconocimiento secuencial de estados gestuales compuestos.
- **Interfaz Python:**
```python
class LSMEvaluator:
    def set_target_sign(self, sign_id: str) -> None: ...
    def evaluate(self, state: FusedSignState) -> EvaluationResult: ...
```

---

### Módulo 6: `feedback/` (Motor de Retroalimentación en Tiempo Real)
- **Responsabilidad:** Comparar el estado actual del usuario con el perfil morfológico esperado de la seña objetivo. Si un parámetro no cumple los umbrales mínimos, genera una instrucción pedagógica atómica y comprensible.
- **Reglas de Explicabilidad (Robustez > Explicabilidad):**
  - Si la palma no mira al frente $\to$ *"Gira la palma hacia la cámara"*.
  - Si el pulgar está metido en la seña 'A' $\to$ *"Pega el pulgar al lateral del puño"*.
  - Si la flexión física no coincide $\to$ *"Cierra firmemente los dedos medio y anular"*.
  - Si la seña es correcta $\to$ *"¡Excelente! Postura y orientación correctas"*.
- **Interfaz Python:**
```python
class FeedbackEngine:
    def generate_feedback(self, eval_result: EvaluationResult) -> FeedbackMessage: ...
```

---

### Módulo 7: `api/` y `backend/` (Servicios y Orquestador Central)
- **Responsabilidad:** Orquestar el ciclo infinito de ejecución a 20 FPS en RPi 5. Servir un endpoint WebSocket local (`/ws/telemetry`) que emite eventos en JSON y frames comprimidos JPEG hacia la Laptop anfitriona sin dependencias externas de red.
- **Control de Ciclo:**
```python
class SystemOrchestrator:
    def run_pipeline_step(self) -> None:
        frame = self.camera.get_latest_frame()
        sensors = self.sensors.poll_sensors()
        vision = self.vision.process_frame(frame)
        fused = self.fusion.fuse(vision, sensors)
        evaluation = self.lsm.evaluate(fused)
        feedback = self.feedback.generate_feedback(evaluation)
        self.api.broadcast(evaluation, feedback, frame)
```

---

### Módulo 8: `frontend/` (Capa de Interfaz en Laptop)
- **Responsabilidad:** Aplicación web cliente ejecutada en la Laptop ASUS (desacoplada del backend).
- **Funciones:**
  - Visualización del stream de video en baja latencia.
  - Sobreimpresión de landmarks y vectores de orientación.
  - Indicador de estado de conexión (ESP32-CAM, Sensores, RPi 5).
  - Panel de telemetría de sensores mecatrónicos en tiempo real.
  - Guía pedagógica y avatar/tarjeta de la seña objetivo.
  - **Control por Teclado:** Atajos rápidos con el teclado de la laptop:
    - Teclas `A`, `B`, `C`, `L`, `Y`: Selección directa de seña Nivel 1.
    - Barra espaciadora: Pausa / Reanudar evaluación.
    - Tecla `R`: Recalibración de sensor mecatrónico / centro de visión.
    - Tecla `Tab`: Avanzar a la siguiente seña del plan de estudio.

---

## 3. Contratos de Datos y Formato de Mensajes (JSON Schemas)

### Mensaje de Telemetría y Feedback (RPi 5 $\to$ Laptop vía WebSocket)

```json
{
  "timestamp": 1790695200.125,
  "frame_id": 4821,
  "system_status": {
    "camera_connected": true,
    "sensors_connected": true,
    "fps": 18.5,
    "rpi_temp_c": 54.2
  },
  "target_sign": "A",
  "level": 1,
  "evaluation": {
    "is_valid": false,
    "overall_score": 0.72,
    "parameters": {
      "configuration": {
        "status": "VALID",
        "score": 0.94,
        "detail": "Puño cerrado correctamente"
      },
      "orientation": {
        "status": "INVALID",
        "score": 0.45,
        "detail": "Palma inclinada hacia la derecha"
      },
      "movement": {
        "status": "VALID",
        "score": 1.0,
        "detail": "Seña estática estable"
      },
      "location": {
        "status": "VALID",
        "score": 0.88,
        "detail": "Mano en encuadre correcto"
      }
    }
  },
  "feedback": {
    "status": "CORRECTING",
    "primary_message": "Gira la palma hacia el frente",
    "secondary_message": "Alinea la muñeca con el eje vertical",
    "color_code": "#FFA500"
  },
  "sensor_telemetry": {
    "flex_index": 0.92,
    "flex_middle": 0.95,
    "imu_roll": 14.5,
    "imu_pitch": -3.2
  },
  "landmarks": [
    {"id": 0, "x": 0.512, "y": 0.741, "z": 0.0},
    {"id": 4, "x": 0.485, "y": 0.520, "z": -0.045}
  ]
}
```

### Mensaje de Control (Laptop $\to$ RPi 5 vía WebSocket / Teclado)

```json
{
  "action": "SET_TARGET_SIGN",
  "target_sign": "L",
  "level": 1,
  "timestamp": 1790695201.050
}
```

---

## 4. Presupuesto de Latencia (Latency Budget)

Para asegurar una experiencia interactiva sin fricción ante los jueces y expertos, la latencia total desde la captura física hasta la respuesta visual debe ser inferior a 100 ms:

| Etapa del Pipeline | Componente / Hardware | Latencia Nominal | Límite Máximo Permitido |
| :--- | :--- | :---: | :---: |
| 1. Adquisición y Compresión JPEG | ESP32-CAM (DMA + OV2640) | 18 ms | 30 ms |
| 2. Transporte de Red Local | Wi-Fi Local (Socket MJPEG) | 8 ms | 15 ms |
| 3. Ingesta, Descompresión y Muestreo | Hilo de Video en RPi 5 | 5 ms | 8 ms |
| 4. Extracción de Landmarks | MediaPipe Hands (ARM64 Cortex-A76) | 22 ms | 32 ms |
| 5. Adquisición y Filtrado de Sensor | I2C / UART en RPi 5 (Hilo paralelo) | 2 ms | 4 ms |
| 6. Fusión Sensorial y Clasificador | SVM RBF + Correlación | 2 ms | 4 ms |
| 7. Motor de Feedback Explicable | Lógica de parámetros LSM | 1 ms | 2 ms |
| 8. Serialización y Emisión WS | FastAPI WebSocket | 3 ms | 5 ms |
| 9. Renderizado y Display en UI | Laptop ASUS (Chrome/Edge local) | 8 ms | 15 ms |
| **TOTAL EXTREMO A EXTREMO** | **Sistema Completo Integrado** | **~69 ms** | **< 115 ms** |

---

## 5. Estrategia de Manejo de Errores y Degradación Elegante

1. **Pérdida de Señal de Cámara (ESP32-CAM desconectado):**
   - El backend detecta timeout de 1.0 s en `camera/`.
   - La UI muestra notificación en rojo: `"Cámara desconectada — Reintentando enlace local"`.
   - Se activa el modo de prueba (`02_PROJECT/data/fallback/`) permitiendo continuar la evaluación con secuencias de validación grabadas para no interrumpir la presentación ante el jurado.
2. **Oclusión Parcial de Mano:**
   - Si MediaPipe pierde la detección de landmarks ($\text{confianza} < 0.5$), el sistema **no lanza excepción**: el motor de feedback emite `"Mano fuera de encuadre o no detectada"`.
   - La segunda fuente de sensores mantiene el monitoreo de tensión física para validar que el usuario no retiró el dispositivo.
3. **Desconexión del Sensor Físico:**
   - Si el bus I2C/UART falla, el gestor marca `sensors_connected = false`.
   - El sistema conmuta a modo degradado solo-visión, alertando al operador en la UI y registrando el incidente en `02_PROJECT/logs/`.
