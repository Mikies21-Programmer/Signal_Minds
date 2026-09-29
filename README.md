# INDIVISA INGENIUM 2026

**Evento:** Desafío de Innovación y Maratón de Desarrollo (24 horas)  
**Institución:** Universidad La Salle Oaxaca  
**Reto:** Lengua de Señas Mexicana (LSM) — Integración de Mecatrónica y Visión Artificial  
**Eje:** Responsabilidad Social y accesibilidad para sectores vulnerables  

---

## Estructura y Propósito de Carpetas

Este repositorio y espacio de trabajo ha sido organizado de manera estandarizada y modular para garantizar un flujo de trabajo eficiente durante las 24 horas continuas del evento, facilitando la colaboración entre las áreas de software y mecatrónica.

```text
INDIVISA_INGENIUM_2026/
├── 00_OFFICIAL/
├── 01_REFERENCES/
├── 02_PROJECT/
│   ├── src/
│   ├── models/
│   ├── data/
│   ├── tests/
│   ├── logs/
│   ├── scripts/
│   └── config/
├── 03_DOCS/
│   ├── architecture/
│   ├── hardware/
│   ├── lsm/
│   ├── audits/
│   └── reports/
└── 04_EVIDENCE/
    ├── corte1/
    ├── corte2/
    └── final/
```

---

### `00_OFFICIAL/`
Contiene toda la documentación oficial provista por el comité organizador:
- Convocatoria oficial del evento (`Convocatoria_Indivisa_Ingenium_2026.pdf`).
- Guías y documentos de revelación del reto entregados por los coordinadores.
- Rúbricas oficiales de evaluación y lineamientos de entrega.

---

### `01_REFERENCES/`
Repositorios, librerías y códigos base de consulta técnica (solo lectura):
- **`CICESE-LSM_Alphabet_Recognition-main`:** Implementaciones y datasets base para reconocimiento del alfabeto LSM.
- **`documentation-master`:** Documentación técnica integral de soporte.
- **`esp32-cam-ai-thinker-master`:** Ejemplos, firmware y configuraciones para el módulo ESP32-CAM AI-Thinker.
- **`esp32-camera-master`:** Controladores de bajo nivel y drivers de cámara para arquitectura ESP32.
- **`lsm-dynamic-signs-hand-tracker-main`:** Seguimiento y tracking de señas dinámicas en LSM.
- **`LSM-MediaPipe-SVM-main`:** Pipeline de extracción de landmarks con MediaPipe y clasificación mediante Support Vector Machines (SVM).
- **`mediapipe-samples-main`:** Repositorio oficial de ejemplos y modelos de visión de Google MediaPipe.

---

### `02_PROJECT/`
Área principal de desarrollo de la solución técnica. Aquí residirá el código y artefactos producidos por el equipo:
- **`src/`:** Código fuente de la aplicación (captura de video, detección de landmarks, comunicación serial/WiFi, interfaz gráfica, retroalimentación en tiempo real).
- **`models/`:** Modelos de machine learning entrenados o exportados (pesos, clasificadores SVM, modelos TFLite, etc.).
- **`data/`:** Datos de calibración de sensores, matrices de landmarks capturados y datasets locales de señas.
- **`tests/`:** Scripts de pruebas unitarias, de integración hardware-software y validación de latencia.
- **`logs/`:** Salidas de registro en tiempo de ejecución, trazas de depuración y telemetría de comunicación.
- **`scripts/`:** Scripts auxiliares de soporte (captura rápida de muestras, conversiones de formato, flasheo o configuración de microcontroladores).
- **`config/`:** Archivos de configuración y variables de entorno (parámetros de cámara, umbrales de flexión/sensores, puertos COM, credenciales de red).

---

### `03_DOCS/`
Documentación técnica, lingüística y de gestión del proyecto:
- **`architecture/`:** Diagramas de arquitectura del sistema, diagramas de bloques, flujo de datos y protocolos de comunicación.
- **`hardware/`:** Esquemáticos de circuitos electrónicos, pinouts, diagramas de conexión del sensor/ESP32 y lista de materiales (BOM).
- **`lsm/`:** Fichas morfológicas y lingüísticas de las señas seleccionadas para el reto, con sus criterios de corrección según expertos en LSM.
- **`audits/`:** Auditorías técnicas del workspace, bitácora de revisiones y registros de inventario (`WORKSPACE_INVENTORY.md`).
- **`reports/`:** Redacción del reporte técnico tipo artículo bajo formato APA y diapositivas para la presentación final.

---

### `04_EVIDENCE/`
Almacén de entregables y evidencias obligatorias para cada uno de los hitos evaluativos del maratón:
- **`corte1/` (19:00 a 20:00 h, Día 1 — 15%):**
  - Documentos de metodología de trabajo y asignación de roles.
  - Wireframes / maquetado de la interfaz de usuario.
  - Esquema de instrumentación y arquitectura del dispositivo mecatrónico.
- **`corte2/` (06:00 a 07:00 h, Día 2 — 25%):**
  - Video demostrativo de avance funcional (lectura de al menos un sensor físico en vivo y primera versión del software/modelo en ejecución).
  - Enlaces y comprobantes de subida al Drive asignado.
- **`final/` (12:00 a 15:00 h, Día 2 — 60%):**
  - Materiales para la demostración en vivo ante el panel y expertos en LSM.
  - Reporte tipo artículo en formato APA concluido.
  - Presentación ejecutiva del equipo.

---

## Políticas Operativas del Workspace
1. **Conservación de originales:** Los archivos originales descargados en `C:\Users\migue\Downloads\SALLE` y en `00_ORIGINAL_ZIPS\` no se modifican ni se eliminan.
2. **Referencias inmutables:** Las carpetas dentro de `01_REFERENCES/` son de solo consulta; cualquier derivación debe implementarse dentro de `02_PROJECT/`.
3. **Control y trazabilidad:** Toda evidencia debe subirse puntualmente en la subcarpeta correspondiente de `04_EVIDENCE/` para su respaldo previo a la evaluación formal.
