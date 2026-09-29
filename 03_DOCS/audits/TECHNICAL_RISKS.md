# Matriz de Riesgos Técnicos y Plan de Mitigación — INDIVISA INGENIUM 2026

**Proyecto:** Dispositivo Mecatrónico y Visión Artificial para LSM  
**Fecha de Auditoría:** 29 de septiembre de 2026  
**Documento Fuente:** [`00_OFFICIAL/Convocatoria_Indivisa_Ingenium_2026.pdf`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/00_OFFICIAL/Convocatoria_Indivisa_Ingenium_2026.pdf) y auditoría de [`01_REFERENCES/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/01_REFERENCES)  
**Marco de Control:** [`AGENTS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/AGENTS.md)  

---

## 1. Clasificación General de Riesgos

Los riesgos se evalúan en función de su **Probabilidad de Ocurrencia** y su **Impacto en el Cumplimiento del Reto**:

- **BLOQUEANTE:** Impide la entrega o descalifica automáticamente al equipo (incumplimiento de requisitos oficiales o falla total en vivo).
- **ALTO:** Compromete la calificación final de manera severa (>25% de puntuación) o degrada críticamente el desempeño del sistema.
- **MEDIO:** Provoca retrasos en el cronograma de 24 horas, problemas de ergonomía o dificultades de depuración subsanables.
- **BAJO:** Impacto cosmético o marginal en el flujo de trabajo sin afectación funcional.

```text
+---------------+-------------------------------------------------------------------+
| NIVEL         | RIESGOS IDENTIFICADOS                                             |
+---------------+-------------------------------------------------------------------+
| BLOQUEANTE    | R-01 (Sin Internet / Offline), R-02 (Falta de 2da Fuente Sensor),  |
|               | R-03 (Robustez en Demostración Final ante Jurado)                 |
+---------------+-------------------------------------------------------------------+
| ALTO          | R-04 (Transmisión ESP32-CAM y Congestión RF),                      |
|               | R-05 (Desconexión de Cámara / Brownout Reset),                    |
|               | R-06 (Latencia Extremo a Extremo > 150 ms),                       |
|               | R-07 (MediaPipe en Linux ARM64 / Compatibilidad de Wheel),        |
|               | R-08 (Datos de Prueba Sesgados / Falla con Expertos LSM),         |
|               | R-09 (Identificación Incorrecta de Pines / Hardware)              |
+---------------+-------------------------------------------------------------------+
| MEDIO         | R-10 (Régimen Térmico y Throttling en RPi 5),                     |
|               | R-11 (Acoplamiento de Interfaz de Usuario),                       |
|               | R-12 (Infracción de Licencias en Referencias Académicas)           |
+---------------+-------------------------------------------------------------------+
| BAJO          | R-13 (Espacio en Disco / Archivos Temporales de Logs)              |
+---------------+-------------------------------------------------------------------+
```

---

## 2. Análisis Exhaustivo y Estrategias de Mitigación

---

### R-01. Funcionamiento sin Internet / Modo Offline Estricto
- **Clasificación:** **BLOQUEANTE**
- **Descripción:** Las instalaciones del evento pueden experimentar saturación severa de WiFi o carecer de salida a Internet. Si el sistema o un script auxiliar (`setup.sh`, `pip install`, CDNs de Bootstrap o llamadas a APIs remotas) requiere conectividad externa, la solución colapsará en el momento decisivo.
- **Causa Raíz:** Dependencias implícitas de red (e.g. `mediapipe-samples` descarga el archivo `hand_landmarker.task` desde Google Cloud en tiempo de ejecución).
- **Plan de Mitigación Obligatorio:**
  1. Descargar y almacenar localmente todos los modelos binarios (`svm_rbf_model.pkl`, `scaler.pkl`, `hand_landmarker.task`) dentro de `02_PROJECT/models/`.
  2. Preparar el entorno virtual Python en la Raspberry Pi 5 con todos los paquetes preinstalados (`wheel` cache local offline).
  3. La interfaz web debe servirse de manera autónoma con librerías CSS/JS locales, sin referencias a fuentes externas de Google Fonts ni CDNs de JavaScript.
- **Comprobación:** Desconectar físicamente el cable de red y apagar el WiFi de la Raspberry Pi 5; ejecutar el pipeline completo en modo avión y verificar operación al 100%.

---

### R-02. Segunda Fuente Física de Sensores e Instrumentación Mecatrónica
- **Clasificación:** **BLOQUEANTE**
- **Descripción:** La convocatoria exige de forma estricta la integración de mecatrónica y visión artificial (solución bidisciplinar). Presentar una solución basada exclusivamente en visión computacional por cámara causará la descalificación inmediata o la anulación del bloque técnico (60%).
- **Causa Raíz:** Dependencia excesiva de la facilidad de MediaPipe y omisión del circuito electrónico instrumentado con sensores sueltos.
- **Plan de Mitigación Obligatorio:**
  1. Incorporar físicamente la segunda fuente sensorial (sensores de flexión resistiva para apertura/cierre de dedos, acelerómetro/giróscopo IMU MPU6050 para orientación de muñeca, o microswitches de contacto táctil).
  2. Conectar los sensores mediante acondicionamiento de señal a las entradas analógicas/digitales (vía microcontrolador auxiliar o ADC I2C como ADS1115 en RPi 5).
  3. Fusión sensorial explícita en software: la clasificación de la seña requiere la validación simultánea de los descriptores visuales de MediaPipe y el estado físico de los sensores.
- **Comprobación:** Test unitario en `02_PROJECT/tests/test_sensors.py` que demuestre que si el sensor físico no detecta la postura o contacto requerido, la seña se marca como incompleta o incorrecta.

---

### R-03. Robustez y Tolerancia a Fallos durante la Demostración en Vivo
- **Clasificación:** **BLOQUEANTE**
- **Descripción:** Un bloqueo del software (pantalla congelada, excepción no manejada de Python, segmentation fault o reinicio súbito) durante la demostración ante el panel multidisciplinario y los evaluadores de LSM (12:00 - 15:00 h) arruinaría la presentación y el 60% de la calificación final.
- **Causa Raíz:** Código frágil que no gestiona valores nulos (`None` cuando MediaPipe pierde la mano), desbordamiento de búferes o pérdida momentánea del socket.
- **Plan de Mitigación Obligatorio:**
  1. Envolventes de seguridad (`try/except/finally`) en todos los bucles de captura, inferencia y comunicación.
  2. Servicio gestionado por `systemd` o script watchdog en Bash que reinicie automáticamente el backend en menos de 2 segundos en caso de muerte imprevista del proceso.
  3. Modo de respaldo en caliente (Fallback Dataset): precargar secuencias de video grabadas en `02_PROJECT/data/sample_streams/` para demostrar el algoritmo si la cámara sufre daño físico accidental durante el evento.
- **Comprobación:** Prueba de esfuerzo (*stress test*) de 30 minutos ininterrumpidos registrando memoria RAM, tasa de FPS y reconexión forzada.

---

### R-04. Transmisión ESP32-CAM y Congestión de Radiofrecuencia
- **Clasificación:** **ALTO**
- **Descripción:** Con 8 equipos universitarios compitiendo en el mismo espacio físico con routers, laptops y microcontroladores emitiendo en la banda de 2.4 GHz, la saturación del espectro WiFi provocará caídas drásticas de ancho de banda y pérdida severa de paquetes.
- **Causa Raíz:** El ESP32-CAM posee una antena PCB básica y opera únicamente en 2.4 GHz con una pila de red ligera.
- **Plan de Mitigación Obligatorio:**
  1. Configurar un canal WiFi estático con menor interferencia (escaneado previo con `iwlist` o WiFi Analyzer) o crear un Access Point directo desde la Raspberry Pi 5.
  2. Optimizar el flujo de video: Resolución QVGA (320x240) o CIF (400x296) en JPEG con factor de calidad 12-15; esto reduce el tamaño de frame a < 8 KB, garantizando 20 FPS con menos de 1.5 Mbps de ancho de banda.
  3. Plan de Contingencia Físico: Disponer de un cable serial USB-UART (o conexión directa por pines UART RX/TX a alta velocidad 921600 baud) entre el ESP32-CAM y la RPi 5 si el espectro inalámbrico queda inutilizable.
- **Comprobación:** Simular pérdida de paquetes del 15% con `tc` o `iptables` y verificar que el flujo de video no se congele.

---

### R-05. Desconexión de Cámara y Reinicios por Caída de Tensión (Brownout)
- **Clasificación:** **ALTO**
- **Descripción:** El ESP32-CAM demanda picos de hasta 500-600 mA al encender el módem WiFi y transmitir ráfagas de paquetes de imagen. Si se alimenta directamente del pin de 3.3V o de un puerto USB compartido de la laptop o RPi, el voltaje cae por debajo de 2.8V y se produce un bucle de reinicios infinitos (`Brownout detector was triggered`).
- **Causa Raíz:** Alimentación insuficiente y falta de desacoplamiento de alta frecuencia.
- **Plan de Mitigación Obligatorio:**
  1. Alimentación externa dedicada e independiente: módulo regulador de 5V a 2A mínimo exclusivo para el ESP32-CAM.
  2. Soldar/conectar un condensador electrolítico de 100 µF a 470 µF en paralelo con un cerámico de 100 nF directamente entre los pines `5V` y `GND` del módulo ESP32-CAM.
  3. Lógica de cliente en Python con reconexión automática tras timeout: si la cámara no envía frame en 1.0 segundo, cerrar el descriptor de socket y reintentar conexión en bucle no bloqueante.
- **Comprobación:** Medición de rizado de voltaje con multímetro/osciloscopio en el ESP32-CAM durante transmisión activa de video a 20 FPS.

---

### R-06. Latencia Extremo a Extremo (> 150 ms)
- **Clasificación:** **ALTO**
- **Descripción:** La retroalimentación al usuario debe ser en tiempo real. Si existe un retraso acumulado superior a 150-200 ms entre que el usuario hace la seña y la pantalla reacciona, la experiencia de usuario se degrada y los jueces penalizarán la interactividad.
- **Causa Raíz:** Búfer de captura por defecto en OpenCV (`cv2.VideoCapture` acumula 3-5 frames en cola interna si el procesamiento tarda más que la tasa de refresco).
- **Plan de Mitigación Obligatorio:**
  1. Arquitectura de captura multihilo (*threaded capture worker*): un hilo dedicado lee constantemente frames y mantiene en memoria compartida únicamente el **último frame recibido**, descartando los anteriores.
  2. Uso de clasificadores ultra rápidos: el modelo RBF SVM de `LSM-MediaPipe-SVM-main` ejecuta inferencia en ~1.2 ms, frente a los 40-80 ms que requeriría una red neuronal recurrente o convolucional pesada.
- **Comprobación:** Medir con `time.perf_counter()` la diferencia temporal desde la recepción del frame hasta la emisión del veredicto lingüístico; el tiempo total debe ser $\le 45$ ms en procesamiento local.

---

### R-07. MediaPipe en Linux ARM64 (Raspberry Pi 5)
- **Clasificación:** **ALTO**
- **Descripción:** Históricamente, instalar MediaPipe en entornos ARM64 (Raspberry Pi) requería compilar con Bazel durante horas. Aunque actualmente existen binarios precompilados oficiales para Linux aarch64, incompatibilidades entre versiones de GLIBC o NumPy 2.0 pueden romper el entorno.
- **Causa Raíz:** Dependencias nativas C++ de MediaPipe (`libmediapipe_framework.so`) y dependencias cruzadas con OpenCV y libcamera.
- **Plan de Mitigación Obligatorio:**
  1. Validar inmediatamente en la Raspberry Pi 5 física que el wheel `mediapipe==0.10.x` y `opencv-python-headless` funcionen en el OS Bookworm de 64 bits.
  2. Fijar versiones exactas en `02_PROJECT/config/requirements_rpi.txt` (`numpy<2.0.0`, `scikit-learn`, `joblib`).
  3. Contar con una imagen de respaldo de la tarjeta MicroSD / SSD NVMe lista para clonar si el entorno se corrompe.
- **Comprobación:** Ejecutar script unitario de verificación de extracción de landmarks sobre una imagen de prueba en la RPi 5 física reportando éxito antes de iniciar el maratón.

---

### R-08. Datos de Prueba Sesgados y Evaluación con Expertos en LSM
- **Clasificación:** **ALTO**
- **Descripción:** El modelo puede arrojar 99% de precisión con las manos de los integrantes del equipo bajo iluminación controlada, pero fallar al ser probado por los evaluadores y expertos en LSM (manos de diferente tamaño, piel, presencia de accesorios, ángulo de cámara diferente).
- **Causa Raíz:** Sobreajuste (*overfitting*) a las características antropomórficas y ambientales del equipo de desarrollo.
- **Plan de Mitigación Obligatorio:**
  1. Normalización estricta de coordenadas: restar la coordenada de la muñeca (landmark 0) y normalizar por la distancia euclidiana entre la muñeca y la base del dedo medio (landmark 9), asegurando invarianza completa a escala de mano y distancia a la cámara.
  2. Evaluación de los 4 parámetros formativos lingüísticos (Regla 17 de `AGENTS.md`): configuración digital, orientación de la palma, movimiento y posición espacial.
  3. Validación in situ con al menos 4 personas distintas del equipo durante la madrugada (Día 2).
- **Comprobación:** Matriz de confusión generada con datos de validación cruzada y pruebas a ciegas antes del mediodía del día 2.

---

### R-09. Identificación Incorrecta de Hardware y Conflicto de Pines GPIO
- **Clasificación:** **ALTO**
- **Descripción:** Quemar un pin GPIO del microcontrolador o de la RPi 5 por asignarlo erróneamente a 5V en vez de 3.3V, o utilizar pines con funciones reservadas de arranque (strapping pins en ESP32 como GPIO0, GPIO2, GPIO15) provocando que el sistema no inicie.
- **Causa Raíz:** Asumir esquemáticos de memoria sin consultar la hoja de datos oficial.
- **Plan de Mitigación Obligatorio:**
  1. Cumplimiento de las Reglas 9 y 10 de `AGENTS.md`: prohibido asumir pines o modelos.
  2. Generar el documento formal de esquemático y pinout en `03_DOCS/hardware/PINOUT_MAP.md` antes de conectar cualquier cable.
  3. Verificación con multímetro de continuidad y nivel de voltaje (3.3V vs 5V) previo a la energización.
- **Comprobación:** Inspección cruzada por dos miembros del equipo antes del encendido inicial de la circuitería.

---

### R-10. Régimen Térmico y Estrangulamiento de Frecuencia (Throttling) en RPi 5
- **Clasificación:** **MEDIO**
- **Descripción:** La Raspberry Pi 5 opera a 2.4 GHz pero alcanza temperaturas superiores a 80°C bajo carga continua de CPU si no cuenta con refrigeración activa, reduciendo automáticamente su velocidad de reloj a 1.5 GHz o menos (*thermal throttling*).
- **Causa Raíz:** Inferencia continua de visión y decodificación de video durante 24 horas continuas de maratón.
- **Plan de Mitigación:**
  1. Montaje indispensable del **Active Cooler oficial** de Raspberry Pi 5 (disipador de aluminio anodizado con ventilador controlado por PWM).
  2. Ajustar la frecuencia de procesamiento visual a 15-20 FPS; procesar a 60 FPS desperdicia energía y genera calor innecesario para la dinámica de la LSM.
  3. Registrar la temperatura periódicamente mediante `vcgencmd measure_temp` en los logs del sistema.
- **Comprobación:** Monitoreo térmico durante una prueba continua de 20 minutos; la temperatura debe mantenerse por debajo de 65°C.

---

### R-11. Acoplamiento de la Interfaz de Usuario y Violación de la Regla 20/21
- **Clasificación:** **MEDIO**
- **Descripción:** Intentar crear interfaces directamente sobre el framebuffer de la RPi o reincorporar la pantalla CLB7INH provocaría retrasos y desperdicio de horas de desarrollo.
- **Causa Raíz:** Falta de desacoplamiento entre la capa de presentación y el motor de inferencia.
- **Plan de Mitigación:**
  1. Respetar la Regla 20 (`AGENTS.md`): pantalla CLB7INH excluida sin excepción.
  2. Respetar la Regla 21 (`AGENTS.md`): interfaz web moderna desacoplada servida por FastAPI / WebSocket local hacia el navegador de la laptop.
  3. El motor de inferencia en RPi 5 sólo envía eventos JSON ligeros (`{"seña": "A", "confianza": 0.98, "status": "CORRECTO", "feedback": "Abre más el pulgar"}`) y el stream visual en baja latencia.
- **Comprobación:** Desconectar la laptop de la red; la RPi 5 debe seguir ejecutando el backend y registrando datos sin bloquearse.

---

### R-12. Infracción de Licencias en Referencias Académicas
- **Clasificación:** **MEDIO**
- **Descripción:** Copiar código textualmente de repositorios como `CICESE-LSM_Alphabet_Recognition-main` o `lsm-dynamic-signs-hand-tracker-main`, los cuales no disponen de una licencia abierta formalmente declarada, expone al equipo a reclamos de propiedad intelectual y penalizaciones del jurado.
- **Causa Raíz:** Comodidad al copiar fragmentos de notebooks académicos preexistentes.
- **Plan de Mitigación:**
  1. Dar cumplimiento a la Regla 11 de `AGENTS.md`.
  2. Utilizar únicamente librerías de código abierto verificadas (MIT de `LSM-MediaPipe-SVM-main` y Apache 2.0 de `esp32-camera` y `mediapipe-samples`).
  3. Los conceptos de pooling dinámico de CICESE deben tomarse únicamente como fundamento matemático teórico e implementarse con código propio, modular y documentado en `02_PROJECT/src/`.
- **Comprobación:** Auditoría de código previa a cada corte con búsqueda de cadenas y revisión de atribución de autoría.

---

### R-13. Saturación de Almacenamiento por Archivos de Registro y Frames
- **Clasificación:** **BAJO**
- **Descripción:** Guardar frames completos o logs excesivamente verbosos durante 24 horas continuas de prueba puede llenar el almacenamiento de la tarjeta MicroSD.
- **Causa Raíz:** Debuggers activos que graban imágenes en disco en cada iteración del bucle principal.
- **Plan de Mitigación:**
  1. Configuración de logging con rotación automática de archivos (máximo 10 MB por archivo, conservar los últimos 3).
  2. Almacenar imágenes únicamente bajo demanda cuando el usuario presione un botón de captura de muestra para calibración.
- **Comprobación:** Verificación de espacio libre con `df -h` antes y después de sesiones prolongadas de prueba.

---

## 3. Matriz de Priorización y Semáforo de Riesgos

```text
IMPACTO ^
        |
CRÍTICO |         [R-06 Latencia]   [R-04 Transmisión]   [R-01 Sin Internet]
        |                           [R-05 Desconexión]   [R-02 2da Fuente Sensor]
        |                                                [R-03 Robustez Demo]
        |
MODERADO| [R-12 Licencias]          [R-07 ARM64]         [R-08 Datos Prueba]
        | [R-11 Interfaz]           [R-10 Térmico]       [R-09 Hardware/Pines]
        |
MENOR   | [R-13 Disco]
        +-------------------------------------------------------------------->
          BAJA                      MEDIA                ALTA       PROBABILIDAD
```
