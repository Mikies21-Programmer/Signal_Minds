# Auditoría Técnica de Repositorios de Referencia — INDIVISA INGENIUM 2026

**Ubicación de Referencias:** [`01_REFERENCES/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/01_REFERENCES)  
**Marco de Auditoría:** Evaluación técnica de componentes, licenciamiento y compatibilidad de hardware (Raspberry Pi 5 + ESP32-CAM).  
**Regla de Oro:** Repositorios de solo lectura; prohibida su alteración directa ([`AGENTS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/AGENTS.md), Regla 2).

---

## 1. Resumen Ejecutivo de la Auditoría

| Repositorio | Licencia | Rol Técnico Potencial | Reusabilidad Directa | Compatibilidad RPi 5 | Compatibilidad ESP32-CAM |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **`LSM-MediaPipe-SVM-main`** | **MIT** | Pipeline de inferencia estática (21 letras) + modelos preentrenados | **Muy Alta** | **Excelente (1.2 ms/frame)** | Incompatible (procesamiento en RPi) |
| **`esp32-cam-ai-thinker-master`** | **Apache 2.0** | Firmware emisor de video + esquemáticos y pinouts AI-Thinker | **Alta** | No aplica | **Nativa (OV2640)** |
| **`esp32-camera-master`** | **Apache 2.0** | Driver oficial Espressif para adquisición de imagen en DMA | **Alta (Librería)** | No aplica | **Nativa (Bajo nivel)** |
| **`mediapipe-samples-main`** | **Apache 2.0** | Ejemplos oficiales Google de Hand Landmarker para Raspberry Pi | **Media-Alta** | **Excelente** | Incompatible |
| **`documentation-master`** | **CC BY-SA 4.0 / BSD** | Documentación de hardware Raspberry Pi 5, GPIO y cámara | **Informativa** | **Nativa** | No aplica |
| **`CICESE-LSM_Alphabet_Recognition-main`** | **Sin licencia** | Técnicas de pooling estadístico y stacking para señas dinámicas | **Consultiva** | Buena (Python) | Incompatible |
| **`lsm-dynamic-signs-hand-tracker-main`** | **Sin licencia** | Estado del arte LSM y metodologías temporales (CRISP-ML) | **Consultiva** | Buena (Python) | Incompatible |

---

## 2. Auditoría Detallada por Repositorio

---

### 1. `LSM-MediaPipe-SVM-main`

- **Propósito:** Benchmark reproducible de clasificadores para el abecedario estático de LSM en hardware sin aceleración GPU (CPU estándar), logrando hasta 99.36% de precisión con RBF SVM y 1.20 ms de inferencia.
- **Tecnología:** Python 3.8+, MediaPipe Hands (`solutions.hands`), Scikit-learn, OpenCV, NumPy, Joblib.
- **Componentes reutilizables:**
  - Modelos ya entrenados y serializados en `models/`: `svm_rbf_model.pkl` (12.5 MB), `svm_linear_model.pkl` (14.5 MB), `scaler.pkl` y `label_encoder.pkl` (21 clases estáticas: A–Y, excluyendo señas dinámicas).
  - Algoritmo de normalización y extracción de los 63 descriptores numéricos (21 puntos $\times$ 3 coordenadas $x, y, z$).
- **Archivos importantes:**
  - `src/extract_landmarks.py`: Función de extracción con MediaPipe.
  - `src/hri_interface.py`: Lógica de buffer temporal y suavizado de predicciones mediante colas de decisión (`deque` y `Counter`).
  - `models/svm_rbf_model.pkl` y `models/scaler.pkl`: Pesos preentrenados listos para inferencia offline.
- **Licencia:** **MIT License** (Permite copia, modificación, distribución e integración manteniendo aviso de copyright).
- **Qué conviene estudiar:**
  - La normalización de landmarks centrada en la muñeca (landmark 0), lo que confiere invarianza a traslación espacial.
  - El filtrado de predicciones por moda estadística temporal en ventanas móviles para evitar parpadeo o jitter.
- **Qué NO conviene copiar:**
  - La interfaz gráfica monolítica de `hri_interface.py` que usa `cv2.imshow` en bucle bloqueante (viola la Regla 21 de desacoplamiento de interfaz en Laptop).
  - Rutas de archivo absolutas o relativas no parametrizadas.
- **Compatibilidad con Raspberry Pi 5:** **Sobresaliente.** Inferencia de 1.2 ms en CPU x86 equivale a menos de 5 ms en el procesador quad-core Cortex-A76 a 2.4 GHz de la RPi 5, permitiendo sobradamente los 15-20 FPS requeridos.
- **Compatibilidad con ESP32-CAM:** **Incompatible en el microcontrolador.** El ESP32 no cuenta con memoria ni CPU para ejecutar MediaPipe Hands.

---

### 2. `esp32-cam-ai-thinker-master`

- **Propósito:** Proporcionar firmware, ejemplos y esquemáticos validados para la placa AI-Thinker ESP32-CAM con sensor OV2640.
- **Tecnología:** C/C++, PlatformIO / Arduino Core para ESP32, FreeRTOS.
- **Componentes reutilizables:**
  - Mapeo exacto de pines del sensor OV2640 para la tarjeta AI-Thinker.
  - Ejemplo `examples/http_jpg/` para transmisión de streaming JPEG vía socket HTTP local hacia la red compartida.
- **Archivos importantes:**
  - `docs/about-esp32-cam.md`: Especificaciones del sensor, PSRAM y capacidades.
  - `examples/http_jpg/`: Servidor de streaming ligero.
  - `assets/Wiring-with-usb-ttl.png`: Diagrama de conexión FTDI para flasheo seguro.
- **Licencia:** **Apache License 2.0** (Permisiva, requiere mención de cambios y atribución).
- **Qué conviene estudiar:**
  - Manejo de voltajes y consumo: La placa demanda picos de corriente superiores a 500 mA durante la transmisión de ráfagas WiFi. Alimentarla desde el puerto USB de la RPi o laptop puede provocar `brownout reset` (reinicio cíclico).
  - El proceso de flasheo: Puentear `GPIO0` a `GND` durante encendido para modo bootloader, y dejarlo al aire para operación normal.
- **Qué NO conviene copiar:**
  - El ejemplo `examples/google_storage/` que envía imágenes a la nube de Google Storage (viola la Regla 4 de cero dependencia de Internet).
  - Cualquier código que sature la memoria interna DRAM sin aprovechar la PSRAM externa.
- **Compatibilidad con Raspberry Pi 5:** No aplica como software para RPi, pero es el complemento idóneo para enviar video por red local hacia la RPi 5.
- **Compatibilidad con ESP32-CAM:** **Nativa 100%.** Específicamente optimizado para la placa AI-Thinker.

---

### 3. `esp32-camera-master`

- **Propósito:** Driver oficial de bajo nivel desarrollado por Espressif para adquisición directa de video con soporte de aceleración DMA y decodificación JPEG en hardware.
- **Tecnología:** C puro, ESP-IDF Component API, FreeRTOS, DMA.
- **Componentes reutilizables:**
  - Driver `esp_camera` oficial (`esp_camera_init()`, `esp_camera_fb_get()`, `esp_camera_fb_return()`).
  - Conversiones optimizadas de formatos de imagen (`conversions/include/img_converters.h`).
- **Archivos importantes:**
  - `driver/include/esp_camera.h`: Interfaz del driver.
  - `target/esp32/camera_pin.h`: Definiciones de pines por modelo.
  - `conversions/src/img_converters.c`: Rutas críticas de compresión y descompresión rápida.
- **Licencia:** **Apache License 2.0**.
- **Qué conviene estudiar:**
  - La directriz oficial de Espressif: si WiFi está activo, transmitir directamente en **JPEG comprimido** con resoluciones como QVGA (320x240) o CIF (400x296). Operar en RGB crudo satura el bus PSRAM y descarta fotogramas.
  - La liberación obligatoria del framebuffer (`esp_camera_fb_return`) para evitar fugas de memoria crítica en el heap.
- **Qué NO conviene copiar:**
  - No duplicar el código del driver; debe integrarse como componente formal de ESP-IDF o biblioteca en el firmware del ESP32.
- **Compatibilidad con Raspberry Pi 5:** No aplica (código de silicio para microcontroladores Espressif).
- **Compatibilidad con ESP32-CAM:** **Nativa 100%.** Es el estándar de la industria para dicha placa.

---

### 4. `mediapipe-samples-main`

- **Propósito:** Demostraciones y guías oficiales de Google para el despliegue de MediaPipe Solutions y MediaPipe Tasks en plataformas embebidas y móviles.
- **Tecnología:** Python 3, MediaPipe Tasks, TensorFlow Lite, OpenCV, Linux ARM64.
- **Componentes reutilizables:**
  - Estructura del ejemplo específico para Raspberry Pi: `examples/hand_landmarker/raspberry_pi/` (`detect.py`).
  - Lógica de visualización y trazado de esqueleto de mano sobre frames en vivo.
- **Archivos importantes:**
  - `examples/hand_landmarker/raspberry_pi/detect.py`: Pipeline optimizado para Raspberry Pi OS.
  - `examples/hand_landmarker/raspberry_pi/requirements.txt`: Dependencias mínimas.
- **Licencia:** **Apache License 2.0**.
- **Qué conviene estudiar:**
  - El uso de la nueva API MediaPipe Tasks (`HandLandmarkerOptions`, modo `RunningMode.LIVE_STREAM`) con timestamps continuos en milisegundos para minimizar la latencia.
- **Qué NO conviene copiar:**
  - El script `setup.sh` que ejecuta `wget https://storage.googleapis.com/...` en caliente durante la configuración (debe disponerse del modelo `.task` localmente en `02_PROJECT/models/` antes del evento para cumplir la regla offline).
  - Los 15 ejemplos restantes no relacionados (audio, lenguaje natural, etc.) para mantener la limpieza del proyecto.
- **Compatibilidad con Raspberry Pi 5:** **Sobresaliente.** Soporta arquitecturas ARM64 (aarch64) de Raspberry Pi OS Bookworm.
- **Compatibilidad con ESP32-CAM:** Incompatible en el microcontrolador.

---

### 5. `documentation-master`

- **Propósito:** Documentación canónica y exhaustiva de todo el ecosistema de hardware y software de Raspberry Pi.
- **Tecnología:** Markdown, AsciiDoc, Jekyll, CMake.
- **Componentes reutilizables:**
  - Mapeo oficial del conector GPIO de 40 pines para Raspberry Pi 5 (controlado por el chip RP1).
  - Directrices de configuración de interfaces de comunicación UART, I2C, SPI y configuración de red local (Hotspot Wi-Fi / IP estática).
- **Archivos importantes:**
  - `documentation/computers/raspberry-pi/`: Hojas de características de Raspberry Pi 5.
  - `documentation/computers/os/`: Guías de configuración de sistema, gestión de energía y reloj de CPU.
- **Licencia:** **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** para el contenido; **BSD 3-Clause** para herramientas.
- **Qué conviene estudiar:**
  - El pinout de la RPi 5: identificar con exactitud los pines libres para comunicación con la segunda fuente de sensores mecatrónicos (pines I2C GPIO 2/3 o UART GPIO 14/15) sin interferir con interfaces del sistema.
  - Regímenes térmicos del procesador Broadcom BCM2712 y uso del Active Cooler.
- **Qué NO conviene copiar:**
  - No transferir código Ruby, Jekyll ni estructuras de compilación web al proyecto.
- **Compatibilidad con Raspberry Pi 5:** **Nativa absoluta.**
- **Compatibilidad con ESP32-CAM:** No aplica.

---

### 6. `CICESE-LSM_Alphabet_Recognition-main`

- **Propósito:** Trabajo de investigación académica en el CICESE (Tesis Morfín Chávez y Dr. Irvin Hussein López Nava) sobre reconocimiento de señas estáticas y dinámicas de LSM combinando MediaPipe con clasificadores clásicos y redes neuronales.
- **Tecnología:** Python 3, MediaPipe, Scikit-learn, TensorFlow/Keras, Jupyter Notebooks.
- **Componentes reutilizables:**
  - Concepto matemático de **Pooling Estadístico:** cálculo de media, varianza, mínimos y máximos de los landmarks a lo largo de una ventana temporal para reducir secuencias dinámicas a un vector de dimensión fija.
- **Archivos importantes:**
  - `SVM_POOLING_CONTINUOS.ipynb`: Lógica de inferencia continua sobre signos dinámicos.
  - `SVM_STACKING_SETTING_UP.ipynb`: Experimentación de secuencias con padding fijo ($T = 5, 10, 30$ frames).
- **Licencia:** **Sin archivo de licencia formal** (Código académico con derechos reservados del autor y del CICESE).
- **Qué conviene estudiar:**
  - La formulación del algoritmo de pooling para señas dinámicas (como 'J' o 'Z'), el cual permite evaluar la componente de movimiento con bajo costo computacional.
- **Qué NO conviene copiar:**
  - **No copiar código textualmente** debido a la falta de licencia explícita abierta (Regla 11 del `AGENTS.md`).
  - No replicar el modelo CNN de `CNN.ipynb`, el cual presenta sobrecarga innecesaria para inferencia en tiempo real en comparación con SVM.
- **Compatibilidad con Raspberry Pi 5:** MediaPipe y Scikit-learn son compatibles, pero se debe reimplementar la lógica en scripts limpios `.py`.
- **Compatibilidad con ESP32-CAM:** Incompatible.

---

### 7. `lsm-dynamic-signs-hand-tracker-main`

- **Propósito:** Proyecto académico del Tecnológico de Monterrey enfocado en la formulación metodológica (CRISP-ML) y estado del arte para la detección de señas dinámicas de la Lengua de Señas Mexicana.
- **Tecnología:** Python 3, MediaPipe, OpenCV, Scikit-learn, Pandas, Jupyter Notebooks.
- **Componentes reutilizables:**
  - Marco conceptual en `Estado de Arte LSM.pdf`: delimitación lingüística de las señas dinámicas en el contexto mexicano.
  - Planteamiento de métricas de calidad y criterios de segmentación gestual (identificación de inicio, punto culminante y retorno a reposo).
- **Archivos importantes:**
  - `Estado de Arte LSM.pdf`: Marco teórico y referencias bibliográficas de LSM.
  - `notebooks/feature_engineering/`: Tratamiento de series temporales de coordenadas gestuales.
- **Licencia:** **Sin archivo de licencia formal** (Proyecto académico de autoría reservada del ITESM).
- **Qué conviene estudiar:**
  - La definición de los parámetros de calidad lingüística (orientación y trayectoria) que los jueces y expertos en LSM evaluarán durante la ronda final.
- **Qué NO conviene copiar:**
  - Código fuente directo sin licencia explícita.
  - Estructuras complejas de notebooks no preparadas para entornos de ejecución continua.
- **Compatibilidad con Raspberry Pi 5:** Conceptual únicamente; la implementación debe ser código propio en `02_PROJECT/`.
- **Compatibilidad con ESP32-CAM:** Incompatible.

---

## 3. Matriz de Síntesis Tecnológica para el Proyecto

```text
+-----------------------------------------------------------------------------------+
| COMPONENTE DEL SISTEMA    | FUENTE DE INSPIRACIÓN TÉCNICA   | IMPLEMENTACIÓN PROPIA |
+-----------------------------------------------------------------------------------+
| Adquisición de Video       | esp32-cam-ai-thinker / camera   | 02_PROJECT/src/camera |
| Extracción de Landmarks    | LSM-MediaPipe-SVM / mediapipe   | 02_PROJECT/src/vision |
| Clasificador Estático LSM  | LSM-MediaPipe-SVM (MIT, SVM)    | 02_PROJECT/models/    |
| Inferencia Dinámica LSM    | CICESE (Pooling) + ITESM (LSM)  | 02_PROJECT/src/lsm/   |
| Hardware y Pinout RPi 5    | documentation-master (RPi doc)  | 03_DOCS/hardware/     |
| Interfaz de Usuario        | Propia y desacoplada (Laptop)   | 02_PROJECT/src/ui/    |
| Segunda Fuente Sensorial   | Requisito mecatrónico oficial   | 02_PROJECT/src/hw/    |
+-----------------------------------------------------------------------------------+
```
