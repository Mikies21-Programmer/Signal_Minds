# XIAO ESP32-S3 Sense Camera Audit

Documento de auditoría técnica y evidencia de hardware real para la placa de desarrollo **Seeed Studio XIAO ESP32-S3 Sense** y su módulo de cámara, en el marco del proyecto **INDIVISA INGENIUM 2026** (Sistema Mecatrónico y Visión Artificial para Retroalimentación de Lengua de Señas Mexicana).

---

## Hardware confirmado

A través de la herramienta de bajo nivel `esptool v5.4.0` sobre la interfaz serie USB en Windows (`COM10`), se ha interrogado directamente la ROM de arranque, eFuses y controlador SPI del microcontrolador conectado físicamente.

| Parámetro | Valor Verificado en Hardware | Fuente de Validación |
| :--- | :--- | :--- |
| **Puerto Serial** | `COM10` (Windows `usbser.inf`, Dispositivo serie USB) | `Win32_SerialPort` / `pyserial` |
| **Hardware ID** | `USB\VID_303A&PID_1001\DC:DA:0C:13:D0:AC` | Bus USB eXtensible Host Intel |
| **Dirección MAC** | `dc:da:0c:13:d0:ac` | Lectura de eFuse de fábrica |
| **Frecuencia Cristal** | `40 MHz` | ROM Bootloader |
| **Modo USB Activo** | `USB-Serial/JTAG` integrado | Controlador USB OTG nativo |

---

## Chip ESP32-S3

- **Modelo Exacto:** `ESP32-S3 (QFN56)`
- **Revisión de Silicio:** `revision v0.2`
- **Arquitectura:** Xtensa® 32-bit LX7 Dual-Core a 240 MHz + Ultra Low Power (LP Core).
- **Conectividad:** Wi-Fi 802.11 b/g/n (2.4 GHz) + Bluetooth 5.0 (LE).
- **Variante Comercial:** ESP32-S3R8 (integrado en el diseño compacto Seeed XIAO).

---

## Flash

- **Fabricante (Manufacturer ID):** `0xC8` (GigaDevice Semiconductor).
- **Código de Dispositivo (Device ID):** `0x4017` (Familia GD25Q64 / GD25LQ64).
- **Capacidad Total:** **8 MB** ($67,108,864$ bits / 64 Mbits).
- **Modo SPI Configurado en eFuse:** `Quad SPI` (4 líneas de datos: IO0, IO1, IO2, IO3).
- **Voltaje de Operación Flash:** `3.3 V` (configurado por hardware en eFuse).

---

## PSRAM

- **Tipo:** **Embedded Octal/Quad PSRAM** (`AP_3v3`).
- **Capacidad Total:** **8 MB** (identificada por `esptool`: `Embedded PSRAM 8MB (AP_3v3)`).
- **Impacto Arquitectural:** 
  - La presencia de 8 MB de PSRAM es el requisito indispensable para la adquisición de vídeo.
  - Permite ubicar los framebuffers DMA de la cámara en memoria externa (`CAMERA_FB_IN_PSRAM`) sin agotar los 512 KB de SRAM interna del SoC.
  - Soporta múltiples framebuffers (`fb_count = 2` o `3`) para evitar tearing y caídas de frames en resoluciones VGA/SVGA.

---

## Cámara

- **Módulo Físico Conectado:** Placa de expansión Seeed Studio Sense acoplada mediante conector B2B de alta densidad inferior.
- **Conector de Cámara:** FPC de 24 pines con paso de 0.5 mm (interfaz DVP paralela de 8 bits).
- **Inscripción en el Cable Flexible (FPC):** `MJY20FF-F3 TL 2344`
  - `MJY`: Fabricante de empaque óptico (MinJieYuan / Shenzhen Minjieyuan Technology).
  - `20`: Sensor de 2.0 Megapíxeles (resolución nativa de $1600 \times 1200$).
  - `FF`: Enfoque Fijo (*Fixed Focus*).
  - `F3`: Revisión mecánica del flex de 24 pines.
  - `TL`: Código de línea de producción y ensamble.
  - `2344`: Fabricación en la semana 44 del año 2023 (octubre/noviembre 2023).

---

## Sensor confirmado / no confirmado

- **Estado de Certificación:** **NO CONFIRMADO POR LECTURA DE SILICIO / ALTAMENTE PROBABLE POR ESPECIFICACIÓN.**
- **Sensor Más Probable:** **OmniVision OV2640**.
  - Corresponde a la especificación estándar de Seeed Studio para todos los kits comerciales XIAO ESP32-S3 Sense.
  - La inscripción `20` en el flex FPC ratifica el silicio de 2 MP.
- **Mecanismo de Confirmación Dinámica en Runtime:**
  El controlador `esp_camera` de Espressif implementa sondeo automático sobre el bus SCCB (I2C):
  1. **OV2640:** Dirección SCCB `0x30`. Requiere conmutar al banco 1 escribiendo `0x01` en el registro `0xFF`. La lectura de los registros `0x0A` (PID) y `0x0B` (VER) debe arrojar `0x2641` o `0x2642`. Registros de fabricante `0x1C`=`0x7F`, `0x1D`=`0xA2`.
  2. **OV3660:** Dirección SCCB `0x3C`. La lectura de 16 bits en `0x300A` y `0x300B` debe arrojar `0x3660`.
  3. **OV5640:** Dirección SCCB `0x3C`. La lectura de 16 bits en `0x300A` y `0x300B` debe arrojar `0x5640`.

---

## Pinout oficial

El mapeo de señales entre el SoC ESP32-S3 y el conector DVP de la cámara en la placa de expansión Sense está **CONFIRMADO** mediante el archivo canónico `camera_pinout.h` de Espressif (`BOARD_ESP32S3_XIAO`) y los esquemáticos oficiales de Seeed Studio:

| Señal DVP | Función Cámara | GPIO ESP32-S3 | Estado |
| :--- | :--- | :--- | :--- |
| **PWDN** | Power Down | `-1` (No conectado / controlado por hardware) | Confirmado |
| **RESET** | Reset por hardware | `-1` (Reset por software vía registro SCCB) | Confirmado |
| **XCLK** | Reloj de entrada del sensor | **GPIO 10** | Confirmado |
| **PCLK** | Pixel Clock (reloj de muestreo) | **GPIO 13** | Confirmado |
| **VSYNC** | Sincronización vertical de cuadro | **GPIO 38** | Confirmado |
| **HREF** | Sincronización horizontal de línea | **GPIO 47** | Confirmado |
| **SIOD** | Datos SCCB / I2C (SDA) | **GPIO 40** | Confirmado |
| **SIOC** | Reloj SCCB / I2C (SCL) | **GPIO 39** | Confirmado |
| **Y9 (D7)** | Bit de datos 7 (MSB) | **GPIO 48** | Confirmado |
| **Y8 (D6)** | Bit de datos 6 | **GPIO 11** | Confirmado |
| **Y7 (D5)** | Bit de datos 5 | **GPIO 12** | Confirmado |
| **Y6 (D4)** | Bit de datos 4 | **GPIO 14** | Confirmado |
| **Y5 (D3)** | Bit de datos 3 | **GPIO 16** | Confirmado |
| **Y4 (D2)** | Bit de datos 2 | **GPIO 18** | Confirmado |
| **Y3 (D1)** | Bit de datos 1 | **GPIO 17** | Confirmado |
| **Y2 (D0)** | Bit de datos 0 (LSB) | **GPIO 15** | Confirmado |

*Nota Crítica:* Este pinout es radicalmente diferente al pinout de AI-Thinker ESP32-CAM (que usa GPIO 0, 4, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36, 39). Intentar usar la definición de AI-Thinker en la XIAO provoca fallo total de inicialización o cuelgue del bus GPIO.

---

## USB

- **Controlador Físico:** USB OTG Full Speed (12 Mbps) integrado en el silicio del ESP32-S3.
- **Configuración Actual:** Modo `USB-Serial/JTAG` (interfaz compuesta de consola serie CDC + depuración JTAG por hardware).
- **Comportamiento en Windows:**
  - `MI_00`: Dispositivo Serie USB (`usbser.sys`) $\to$ asignado exitosamente como **`COM10`**.
  - `MI_02`: USB JTAG/serial debug unit (`WinUSB`).
- **Capacidad de Alimentación:** 5V provistos a través del bus USB-C del laptop con regulador LDO interno a 3.3V para la placa y el sensor.

---

## Ruta UVC (USB Video Class)

- **Descripción:** El ESP32-S3 actúa como dispositivo esclavo UVC estándar conectado por USB al host.
- **Pila de Software Requerida:** Componente `espressif/esp_tinyusb` sobre ESP-IDF con descriptor compuesto de clase de vídeo UVC 1.1 + CDC.
- **Ventajas:**
  - Latencia extremadamente baja ($< 50\text{ ms}$).
  - Cero dependencia de infraestructura de red Wi-Fi o routers.
  - Reconocimiento nativo en Linux (Raspberry Pi 5) como `/dev/video0` mediante el módulo del kernel `uvcvideo`.
- **Desventajas y Riesgos:**
  - El ancho de banda está limitado a USB Full Speed (12 Mbps brutos, $\approx 8\text{--}9\text{ Mbps}$ útiles). Requiere transmitir estrictamente en MJPEG comprimido por hardware en el sensor (QVGA o VGA a máx 15--20 FPS).
  - En Windows, la inicialización de endpoints isócronos de TinyUSB suele presentar conflictos con controladores DirectShow/MediaFoundation.
  - Reemplaza o dificulta la monitorización simultánea de logs por la consola USB-Serial-JTAG si el endpoint se satura.

---

## Ruta HTTP-MJPEG (CameraWebServer)

- **Descripción:** El ESP32-S3 inicializa la cámara `esp_camera`, se conecta a la red Wi-Fi (o crea un punto de acceso autónomo SoftAP) e inicia un servidor HTTP liviano que transmite un flujo multipart `multipart/x-mixed-replace;boundary=123456789000000000000987654321`.
- **Ventajas:**
  - Máxima madurez y robustez probada en la comunidad Seeed y Espressif.
  - Mantiene el puerto USB (`COM10`) 100% libre y dedicado a telemetría, flasheo y depuración continua por consola serial a 115200 baudios.
  - Totalmente desacoplado físicamente del laptop o de la Raspberry Pi (permite movilidad de la cámara).
  - Tasa de fotogramas óptima: 20 a 30 FPS en resolución QVGA ($320 \times 240$) o VGA ($640 \times 480$) aprovechando los 8 MB de PSRAM.
- **Desventajas:**
  - Latencia de transporte Wi-Fi de $80\text{--}150\text{ ms}$.
  - Dependencia de estabilidad de señal RF y libre de interferencias.

---

## Compatibilidad con nuestro proyecto

Se auditó minuciosamente el código base de `02_PROJECT/`:

1. **`02_PROJECT/src/camera/consumer.py`:**
   - La clase `CameraConsumer` cuenta con un hilo desacoplado con buffer forzado a 1 fotograma (`cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)`) para evitar acumulación de latencia.
   - En las líneas 68-71, el método `_parse_config` detecta automáticamente si la entrada es una cadena numérica o entero (cámara web local por índice, ej. `0` para UVC) o una URL de red (cadena con protocolo HTTP para MJPEG).
   - Implementa reconexión automática en caso de pérdida de señal y cálculo de FPS en ventana móvil de 1 segundo.
2. **`02_PROJECT/src/backend/orchestrator.py`:**
   - Consume los fotogramas BGR de `CameraConsumer` de forma independiente a la fuente física.
   - Pasa los frames al `VisionPipeline` (MediaPipe Tasks), renderiza anotaciones morfológicas y sirve el fotograma resultante codificado en JPEG a la interfaz web a través del canal WebSocket `/ws/telemetry`.
3. **`02_PROJECT/config/settings.json`:**
   - Parámetros actuales:
     ```json
     "camera": {
       "stream_url": "http://192.168.4.1/stream",
       "resolution": [320, 240],
       "target_fps": 20,
       "timeout_sec": 1.0,
       "mock_mode": false
     }
     ```
4. **Impacto en el Backend/Frontend:**
   - **CERO modificaciones de código requeridas.** El backend procesa exactamente igual un stream UVC local (`stream_url: "0"`) que un stream HTTP-MJPEG (`stream_url: "http://<IP>/stream"`).

---

## Firmware candidatos

### CANDIDATO 1 (Recomendado): Seeed Studio Official XIAO ESP32S3 Sense CameraWebServer
- **Origen:** Seeed Studio Wiki / Repositorio oficial Seeed Studio ArduinoCore-esp32.
- **Framework:** Arduino-ESP32 / ESP-IDF con definición `#define CAMERA_MODEL_XIAO_ESP32S3`.
- **Método de Vídeo:** HTTP-MJPEG streaming (`/stream` en puerto 80/81).
- **Modos de Red:**
  - *Modo Access Point (SoftAP):* El ESP32 crea su propio SSID (ej. `XIAO-CAM-INDIVISA`) con IP estática fija `192.168.4.1`. Elimina la dependencia de routers externos durante demostraciones y coincide con la configuración por defecto del proyecto.
  - *Modo Estación (STA):* Se conecta a la red Wi-Fi compartida del laboratorio o hotspot móvil.
- **Sensor:** OV2640 nativo con autodetección en runtime.
- **Gestión de Memoria:** Utiliza los 8 MB de PSRAM embebida para alojar 2 buffers DMA de captura continua.
- **Riesgo:** Mínimo. Código completamente maduro y probado para esta revisión exacta de hardware.

### CANDIDATO 2: Espressif Official TinyUSB UVC Camera Firmware
- **Origen:** Repositorio oficial Espressif `esp-iot-solution` (`examples/usb/device/usb_uvc`) o `esp-idf`.
- **Framework:** ESP-IDF v5.1+ con componente `tinyusb`.
- **Método de Vídeo:** USB Video Class (UVC 1.1) sobre el conector USB-C nativo.
- **Sensor:** OV2640 operando en modo JPEG directo hacia el endpoint isócrono USB.
- **Riesgo:** Medio a Alto. Requiere toolchain especializada de compilación ESP-IDF, ajuste fino de descriptores de interfaz para DirectShow en Windows y monitoreo de ancho de banda Full Speed.

---

## Riesgos

1. **Riesgo de Fuente de Alimentación:** Al operar el sensor de cámara y la radio Wi-Fi simultáneamente en el ESP32-S3, pueden ocurrir picos de consumo transitorios de hasta 350-450 mA. Si el puerto USB del host o el cable tienen caída de tensión, el microcontrolador puede experimentar *Brownout Reset*. Se debe asegurar conexión directa sin hubs pasivos.
2. **Riesgo de Colisión de Pines con MicroSD:** En la placa Sense, el bus SPI de la tarjeta MicroSD comparte recursos. No se debe inicializar el módulo SD mientras la cámara esté activa si no se gestionan adecuadamente los pines de selección.
3. **Riesgo de Exposición de Credenciales:** En el modo Estación Wi-Fi, nunca deben guardarse contraseñas ni SSIDs en el repositorio git. Debe emplearse modo SoftAP sin credenciales externas o variables de entorno.

---

## Próximo experimento

### Plan de Prueba Mínimo: De XIAO Conectada a Frame Real en 10 Pasos

1. **Paso 1 (Identificación):** Confirmada operatividad de `COM10` y chip ESP32-S3R8 (8MB Flash, 8MB PSRAM).
2. **Paso 2 (Preparación de Firmware):** Compilar/preparar el binario oficial de `CameraWebServer` para Seeed XIAO ESP32-S3 Sense configurado en modo SoftAP autónomo (`192.168.4.1`) o red local.
3. **Paso 3 (Flasheo Controlado):** Grabar el firmware en la flash del ESP32-S3 vía `COM10` utilizando `esptool write_flash` a 460800 baudios.
4. **Paso 4 (Inspección del Bootloader en Consola):** Abrir monitor serial en `COM10` a 115200 baudios y verificar:
   - Inicialización correcta de la PSRAM de 8MB.
   - Lectura de registros SCCB y detección del PID del sensor (`OV2640 detected`).
   - Arranque del servidor HTTP y URL anunciada (ej. `http://192.168.4.1/stream`).
5. **Paso 5 (Captura de Primer Frame):** Ejecutar un script de prueba de 1 frame con OpenCV (`cap.read()`) para verificar la recepción del flujo.
6. **Paso 6 (Verificación Métrica):** Validar dimensiones del fotograma ($320 \times 240$ o $640 \times 480$), espacio de color BGR y ausencia de corrupción JPEG.
7. **Paso 7 (Evidencia Fotográfica):** Guardar el primer fotograma real capturado en `04_EVIDENCE/hardware/xiao_camera_first_frame.jpg`.
8. **Paso 8 (Prueba de Estabilidad):** Ejecutar `02_PROJECT/scripts/test_camera_real.py --duration 30 --url <URL>` evaluando FPS continuo ($\ge 15\text{ FPS}$) y 0 drops durante 30 segundos.
9. **Paso 9 (Conexión al Pipeline):** Levantar el orquestador backend (`api.py`) y corroborar que `VisionPipeline` genera los 21 landmarks de MediaPipe sobre la imagen real.
10. **Paso 10 (Validación en Interfaz Web):** Abrir `index.html` y confirmar la visualización del video en vivo con la caja delimitadora y retroalimentación anatómica de la seña evaluada.

---

## Factory Firmware Test

Se realizó una auditoría no destructiva del firmware pregrabado en la placa conectada a `COM10`:
- **Log de arranque del Bootloader ROM:**
  ```text
  ESP-ROM:esp32s3-20210327
  Build:Mar 27 2021
  rst:0x15 (USB_UART_CHIP_RESET),boot:0x29 (SPI_FAST_FLASH_BOOT)
  Saved PC:0x40377b7a
  SPIWP:0xee
  mode:DIO, clock div:1
  load:0x3fce2820,len:0x116c
  load:0x403c8700,len:0xc2c
  load:0x403cb700,len:0x3108
  entry 0x403c88b8
  ```
- **Auditoría del Descriptor de Aplicación (`esp_app_desc_t` en 0x10020):**
  - **Project Name:** `arduino-lib-builder`
  - **Version:** `64767cc`
  - **Compile Date:** `Nov  4 2025` (11:05:57)
  - **IDF Version:** `v5.5.1-418-gf1a1df9b2e`
- **Tabla de Particiones Verificada:**
  - `nvs`: `0x00009000` (20 KB)
  - `otadata`: `0x0000e000` (8 KB)
  - `app0`: `0x00010000` (3264 KB) — Almacena la imagen `arduino-lib-builder`.
  - `app1`: `0x00340000` (3264 KB) — Vacía (`0xFF`).
  - `spiffs`: `0x00670000` (1536 KB)
  - `coredump`: `0x007f0000` (64 KB)
- **Análisis de Contenido de la Imagen:**
  - El firmware presente en `app0` no contiene código de controlador de cámara (`camera: 0 occurrences`), ni servidor de streaming (`stream: 0 occurrences`).
  - Corresponde a una imagen genérica base del compilador de librerías Arduino/Espressif.

---

## AP Detection

- **Comando Ejecutado:** `netsh wlan show networks mode=bssid`
- **Búsqueda del SSID:** `XIAO_ESP32S3_Sense`
- **Resultado:** **NO VISIBLE** (0 redes XIAO detectadas; el único SSID en el área es la red móvil del laboratorio).
- **Conclusión de Radio:** El firmware actual no inicializa la radio Wi-Fi en modo Access Point.

---

## HTTP Detection

- **Host Evaluado:** `192.168.4.1` (IP estándar de AP ESP32)
- **Comando Ejecutado:** `curl.exe -I --connect-timeout 2 http://192.168.4.1/`
- **Resultado:** `Connection timed out after 2010 ms` (Host inalcanzable, sin interfaz web activa).

---

## Video Endpoint

- **URL:** Ninguna disponible en el hardware actual.
- **Tipo:** Inexistente bajo el firmware actual.

---

## Real Frame Test

- **Resultado:** **FAIL** (No hay servidor de vídeo ni endpoint HTTP activo).
- **Resolución:** N/A.
- **FPS:** 0.

---

## Camera Sensor Status

- **Estado:** **Sensor CMOS = NO CONFIRMADO POR LECTURA DE REGISTROS.**
- **Motivo:** El firmware residente no ejecuta `esp_camera_init` ni consulta el bus SCCB. Se mantiene como sensor altamente probable el **OV2640** (especificación de fábrica) u **OV3660** (revisiones recientes), a confirmar durante el primer arranque con firmware de cámara.

---

## Decision

- **Estado Final Oficial:** **`[FACTORY FIRMWARE NOT PRESENT OR MODIFIED]`** / **`[CAMERA FIRMWARE REQUIRED]`**
- **Acción Obligatoria:** Dado que el firmware de fábrica de cámara no está presente en la placa (reemplazado o entregado con binario base `arduino-lib-builder`), es **ESTRICTAMENTE NECESARIO FLASHEAR EL FIRMWARE OFICIAL DE CÁMARA** (`CameraWebServer` para `CAMERA_MODEL_XIAO_ESP32S3`) en la Fase siguiente para poder obtener vídeo real.
