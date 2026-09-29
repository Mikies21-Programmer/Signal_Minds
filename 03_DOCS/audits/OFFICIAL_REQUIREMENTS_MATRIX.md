# Matriz de Requisitos Oficiales — INDIVISA INGENIUM 2026

**Documento Fuente:** [`00_OFFICIAL/Convocatoria_Indivisa_Ingenium_2026.pdf`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/00_OFFICIAL/Convocatoria_Indivisa_Ingenium_2026.pdf)  
**Organizador:** Universidad La Salle Oaxaca  
**Fecha de emisión de convocatoria:** Septiembre 2026  
**Auditoría y Trazabilidad:** `03_DOCS/audits/OFFICIAL_REQUIREMENTS_MATRIX.md`  

---

## 1. Matriz de Trazabilidad y Cumplimiento

| ID | Requisito Oficial | Fuente | Prioridad | Cómo lo cumpliremos | Cómo se comprobará | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | **Integración Bidisciplinar Obligatoria:** Solución única que combine aplicación de software y dispositivo físico mecatrónico funcionando de forma integrada; no se aceptan soluciones de una sola disciplina. | Pág. 1, *Participantes* | **Crítica (Bloqueante)** | Arquitectura cliente-servidor/bus de datos donde el Raspberry Pi 5 procesa visión y correlaciona lecturas de sensores mecatrónicos físicos en tiempo real. | Inspección física del prototipo en funcionamiento integrado y flujo continuo de telemetría sensor-software. | Planeado |
| **REQ-02** | **Enfoque de Responsabilidad Social:** Beneficio directo a un sector vulnerable (Comunidad sorda y aprendices de LSM). | Pág. 1, *Reto de esta edición* | **Alta** | Sistema de tutoría y corrección en tiempo real para aprendices de LSM, reduciendo la brecha ante la escasez de intérpretes certificados en México. | Validación con usuarios o panel de expertos en LSM; manual y métricas de usabilidad en reporte APA. | Planeado |
| **REQ-03** | **Dispositivo Instrumentado con Sensores:** Dispositivo físico dotado de sensores para evaluar la ejecución de la seña. | Pág. 1, *Reto de esta edición* | **Crítica** | Instrumentación con una segunda fuente física de sensores (flexión / contacto / IMU) conectada a microcontrolador / RPi5. | Lectura de valores analógicos/digitales en `02_PROJECT/logs/` y prueba unitaria en `02_PROJECT/tests/test_sensors.py`. | Planeado |
| **REQ-04** | **Visión Artificial Integrada:** Aplicación de visión que evalúe la correcta ejecución de la seña. | Pág. 1, *Reto de esta edición* | **Crítica** | Adquisición con ESP32-CAM, extracción de landmarks con MediaPipe Hands y clasificación con SVM (RBF/Linear). | Inferencia en vivo con FPS $\ge 15$, precisión $\ge 95\%$ en validación cruzada y visualización de landmarks. | Planeado |
| **REQ-05** | **Retroalimentación en Tiempo Real:** Evaluación interactiva inmediata de la postura y dinámica del signo. | Pág. 1, *Reto de esta edición* | **Crítica** | Interfaz visual en laptop desacoplada que indica acierto/error y guía correctiva en < 150 ms tras emitir la seña. | Medición de latencia extremo a extremo con timestamp en telemetría y respuesta gráfica en pantalla. | Planeado |
| **REQ-06** | **Componentes Electrónicos Sueltos y sin Ensamblar:** Prohibido el uso de sensores previamente soldados, cableados permanentes o ensambles funcionales previos. | Pág. 2, *Hardware* | **Crítica (Bloqueante)** | Presentación de componentes en organizadores/bolsas antiestáticas independientes, sin soldadura ni arneses integrados previos. | Aprobación de la inspección técnica del comité antes de las 10:00 h del día 1. | Por verificar (Día 1) |
| **REQ-07** | **Ensamblaje Íntegro en 24 Horas:** Cableado, ensamblaje, calibración, programación e integración realizados dentro del evento. | Pág. 2, *Hardware* | **Crítica** | Cronograma de trabajo por fases (fase 1: hardware y cableado en primeras 4 horas; fase 2: calibración y firmware; fase 3: integración). | Bitácora de trabajo y registros temporales de commits/logs generados in situ. | Planeado |
| **REQ-08** | **1er Corte Evaluativo (15%):** Revisión de metodología, planeación, roles, wireframes y esquema de instrumentación (19:00 - 20:00 h, Día 1). | Pág. 3, *Formato de Evaluación* | **Alta** | Elaboración de diagrama de Gantt/Kanban, reparto de roles en documento formal, wireframes de la UI y diagrama esquemático de hardware. | Carpeta `04_EVIDENCE/corte1/` completa con PDFs, esquemáticos y maquetado antes de las 19:00 h. | Planeado |
| **REQ-09** | **2do Corte Evaluativo (25%):** Checkpoint de avance en video vía Drive: al menos una lectura de sensor funcionando y primera versión de interfaz o modelo en ejecución (06:00 - 07:00 h, Día 2). | Pág. 3, *Formato de Evaluación* | **Alta** | Grabación en video (1-2 min) que muestre el sensor físico reportando datos y el modelo o UI respondiendo a los cambios de estado. | Video renderizado y subido al enlace de Drive oficial antes de las 07:00 h; respaldo en `04_EVIDENCE/corte2/`. | Planeado |
| **REQ-10** | **Evaluación Final — Componente Lingüístico LSM:** Precisión y corrección lingüística del signo evaluada por expertos en LSM. | Pág. 3, *Formato de Evaluación* | **Crítica (60% bloque)** | Evaluación de los 4 parámetros formativos de LSM: Configuración (forma de dedos), Orientación, Movimiento y Ubicación. | Demostración en vivo ejecutando el catálogo oficial de señas sin falsos positivos y con retroalimentación correcta. | Planeado |
| **REQ-11** | **Evaluación Final — Integración Técnica y Hardware:** Robustez, ergonomía, calidad de feedback en tiempo real y solidez física. | Pág. 3, *Formato de Evaluación* | **Crítica (60% bloque)** | Chasis ergonómico, sujeción firme de cableado, gestión térmica del RPi5, conectores seguros y alimentación aislada/estable. | Prueba de esfuerzo continuo (demostración repetible de 15 min sin cuelgues ni caídas de frames). | Planeado |
| **REQ-12** | **Entregable Oficial: Dispositivo Físico Funcional:** Hardware físico operativo y calibrado. | Pág. 3, *Entregables esperados* | **Alta** | Prototipo físico integrado, con sensores montados de manera segura y ergonómica sobre el usuario o base. | Verificación física de encendido, lectura continua y respuesta mecánica/eléctrica. | Planeado |
| **REQ-13** | **Entregable Oficial: Aplicación de Software Integrada:** Aplicación vinculada al dispositivo. | Pág. 3, *Entregables esperados* | **Alta** | Software modular en `02_PROJECT/src/` con backend en RPi5 y frontend en Laptop comunicados por red local. | Pruebas de integración automatizadas en `02_PROJECT/tests/` ejecutadas sin fallas. | Planeado |
| **REQ-14** | **Entregable Oficial: Demostración en Vivo:** Reconocimiento y retroalimentación de las señas del reto. | Pág. 3, *Entregables esperados* | **Crítica** | Protocolo de demo ensayado previamente con escenarios de éxito y guía de usuario clara para los jueces. | Ejecución en vivo ante el jurado ampliado en la ventana 12:00 - 15:00 h del día 2. | Planeado |
| **REQ-15** | **Entregable Oficial: Presentación Ejecutiva Breve:** Defensa oral del equipo ante el panel evaluador. | Pág. 3, *Entregables esperados* | **Media** | Presentación estructurada (5-7 minutos): problema, solución mecatrónica, pipeline de IA, impacto social y resultados. | Diapositivas preparadas en `03_DOCS/reports/presentation.pdf` y guion de exposición. | Planeado |
| **REQ-16** | **Entregable Oficial: Reporte Tipo Artículo en Formato APA:** Documentación académica formal del desarrollo. | Pág. 3, *Entregables esperados* | **Alta** | Artículo científico (resumen, introducción, metodología mecatrónica y de visión, resultados experimentales, conclusiones y referencias APA). | Documento PDF final en `03_DOCS/reports/articulo_indivisa_2026.pdf` y respaldo en `04_EVIDENCE/final/`. | Planeado |

---

## 2. Ponderación de Calificación y Cronograma de Entregas

```text
+-----------------------------------------------------------------------------------+
| FASE EVALUATIVA               | HORARIO (DÍA 1 / DÍA 2)   | PESO (%) | ENTREGABLES |
+-----------------------------------------------------------------------------------+
| 1er Corte Evaluativo           | 19:00 - 20:00 h (Día 1)  |   15%    | Plan, roles, wireframes, esquema HW |
| 2do Corte Evaluativo           | 06:00 - 07:00 h (Día 2)  |   25%    | Video en Drive: sensor + software   |
| Evaluación Final (Bloque 3)    | 12:00 - 15:00 h (Día 2)  |   60%    | Demo en vivo, hardware, APA, pitch  |
+-----------------------------------------------------------------------------------+
| TOTAL                          |                          |  100%    | Solución integrada funcional        |
+-----------------------------------------------------------------------------------+
```
