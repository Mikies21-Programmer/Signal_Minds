# Registro de Decisiones de Arquitectura (ADR) — INDIVISA INGENIUM 2026

**Proyecto:** Dispositivo Mecatrónico y Sistema de Visión Artificial para Retroalimentación en Tiempo Real de LSM  
**Repositorio:** `INDIVISA_INGENIUM_2026`  
**Ubicación:** [`03_DOCS/architecture/ARCHITECTURE_DECISIONS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/architecture/ARCHITECTURE_DECISIONS.md)  
**Marco Normativo:** Sujeto a las reglas obligatorias de [`AGENTS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/AGENTS.md)  

---

## 1. Propósito y Metodología ADR

Este documento centraliza el historial formal de decisiones arquitectónicas del sistema. Cada decisión técnica de alto impacto debe registrarse siguiendo el formato estructurado para asegurar trazabilidad, justificación fundamentada en requisitos oficiales y reproducibilidad.

---

## 2. Plantilla Estándar para Nuevas Decisiones

```markdown
### ADR-[NUMERO]: [Título breve y descriptivo de la decisión]

- **Estado:** [ Propuesto | Aceptado | Rechazado | En Revisión | Obsoleto ]
- **Fecha:** YYYY-MM-DD
- **Responsables:** [Nombres / Roles]
- **Reglas del AGENTS.md vinculadas:** [Regla X, Regla Y]

#### Contexto y Necesidad
[Descripción del problema técnico, requerimiento del reto o restricción física que motiva la decisión.]

#### Opciones Evaluadas
1. **Opción A:** [Descripción breve]
   - *Ventajas:*
   - *Desventajas / Riesgos:*
2. **Opción B:** [Descripción breve]
   - *Ventajas:*
   - *Desventajas / Riesgos:*

#### Decisión Tomada y Racional
[Elección justificada bajo la jerarquía: Robustez > Explicabilidad > Latencia > Complejidad.]

#### Consecuencias y Mitigación
- **Impacto positivo:** [Beneficios directos]
- **Impacto negativo / Limitaciones:** [Costos o restricciones asumidas]
- **Estrategia de mitigación:** [Medidas para contrarrestar riesgos]

#### Hardware y Dependencias Involucradas
- **Hardware real comprobado:** [Nombre exacto y verificado; sin asumir pines]
- **Dependencias externas:** [Librerías, licencias verificadas]

#### Plan de Validación
- **Script de prueba en:** `02_PROJECT/tests/[nombre_script].py`
- **Evidencia requerida en:** `04_EVIDENCE/[corteX]/`
```

---

## 3. Decisiones Arquitectónicas Iniciales Verificadas

Las siguientes decisiones representan los pilares fundacionales del proyecto aprobados formalmente en la constitución técnica (`AGENTS.md`) y la convocatoria oficial:

---

### ADR-0001: Adopción de Raspberry Pi 5 como Cerebro Central de Procesamiento

- **Estado:** Aceptado
- **Fecha:** 2026-09-29
- **Reglas del AGENTS.md vinculadas:** Regla 6, Regla 18, Regla 19
- **Contexto:** El proyecto exige procesamiento de visión artificial en tiempo real, gestión de modelos de inferencia, correlación temporal de datos sensoriales y servicio de interfaz, todo en un esquema portátil y local para el maratón de 24 horas.
- **Decisión:** Establecer la placa **Raspberry Pi 5** como el nodo maestro computacional exclusivo para la ejecución de la lógica del backend, algoritmos de visión/ML y coordinación general del sistema.
- **Consecuencias:**
  - *Positivo:* Alta capacidad de cómputo en CPU/GPU móvil sin requerir servidores remotos.
  - *Mitigación:* Se debe vigilar la disipación térmica y el consumo energético durante las 24 horas de operación continua.

---

### ADR-0002: Requisito de Operación Autónoma 100% Local / Offline

- **Estado:** Aceptado
- **Fecha:** 2026-09-29
- **Reglas del AGENTS.md vinculadas:** Regla 4, Regla 5
- **Contexto:** Las condiciones del evento no garantizan conectividad a Internet estable, y el sistema debe ser un producto independiente capaz de operar en cualquier entorno vulnerable.
- **Decisión:** Prohibir cualquier dependencia de servicios en la nube, APIs externas en línea o descargas en tiempo de ejecución. Todo paquete, modelo, dataset y activo debe estar precargado y ejecutarse de manera autónoma en la red local del dispositivo.
- **Consecuencias:**
  - *Positivo:* Inmunidad ante caídas de red durante la demostración en vivo ante el jurado.
  - *Mitigación:* Todos los entornos virtuales y paquetes deben instalarse y empaquetarse previamente en local.

---

### ADR-0003: Exclusión de Pantalla CLB7INH y Desacoplamiento de UI para Laptop/PC

- **Estado:** Aceptado
- **Fecha:** 2026-09-29
- **Reglas del AGENTS.md vinculadas:** Regla 20, Regla 21
- **Contexto:** Se detectó la necesidad de evitar complejidades innecesarias asociadas al display CLB7INH (drivers incompatibles, sobrecarga de cableado GPIO y consumo eléctrico que comprometen la robustez en un plazo de 24 horas).
- **Decisión:** Excluir formalmente el periférico CLB7INH de la arquitectura. La interfaz de usuario del sistema se diseñará para visualizarse en una **laptop/computadora**, funcionando completamente desacoplada del backend mediante un protocolo de comunicación ligero y local.
- **Consecuencias:**
  - *Positivo:* Ahorro sustancial de tiempo en depuración de drivers, mejor ergonomía para el usuario y visualización más clara para el jurado calificador.
  - *Mitigación:* Mantener la capa de interfaz estrictamente separada de la lógica de evaluación sensorial para asegurar modularidad.

---

### ADR-0004: ESP32-CAM como Fuente de Adquisición Visual Remota

- **Estado:** Aceptado
- **Fecha:** 2026-09-29
- **Reglas del AGENTS.md vinculadas:** Regla 7, Regla 9, Regla 10
- **Contexto:** Se requiere capturar la imagen del usuario de forma versátil y ergonómica sin sobrecargar mecánicamente la estación central de cómputo.
- **Decisión:** Utilizar el módulo **ESP32-CAM** como periférico especializado de captura de video para transmitir los cuadros visuales al Raspberry Pi 5.
- **Consecuencias:**
  - *Positivo:* Flexibilidad en el posicionamiento físico de la cámara y bajo costo.
  - *Riesgo / Por verificar:* La latencia de transmisión, la resolución y la tasa de cuadros (FPS) deberán medirse en pruebas reales antes de congelar el protocolo de transporte.

---

### ADR-0005: Modelo Híbrido de Fusión Sensorial y Validación Integral de LSM

- **Estado:** Aceptado
- **Fecha:** 2026-09-29
- **Reglas del AGENTS.md vinculadas:** Regla 8, Regla 17
- **Contexto:** La convocatoria estipula explícitamente la integración obligatoria de mecatrónica y visión artificial, evaluada por expertos en LSM respecto a la corrección lingüística. Una clasificación visual simple es insuficiente para determinar la validez de un signo gestual.
- **Decisión:** El sistema validará las señas mediante un esquema multifactorial que combine:
  1. Adquisición visual (ESP32-CAM + MediaPipe/SVM) para estimar configuración y trayectoria.
  2. Segunda fuente física de sensores para validar contacto, flexión o flexibilización mecánica.
  3. Comprobación de los 4 parámetros formativos de la LSM: **configuración, orientación, movimiento y ubicación**.
- **Consecuencias:**
  - *Positivo:* Cumplimiento estricto de las bases oficiales y defensa sólida ante el jurado técnico y lingüístico.
  - *Mitigación:* Se priorizará un conjunto bien acotado de señas para garantizar alta precisión y latencia baja.

---

## 4. Decisiones Pendientes de Validación Técnica (Backlog de Arquitectura)

Las siguientes decisiones se encuentran en estado de **definición abierta** y NO se asumirán ni codificarán hasta que se disponga del hardware físico verificado y se realicen pruebas reales:

| Identificador | Tópico Técnico en Espera | Hardware / Variable a Comprobar | Criterio de Resolución |
| :--- | :--- | :--- | :--- |
| **ADR-PEND-01** | Protocolo de transporte de video ESP32-CAM $\to$ RPi5 | WiFi (HTTP MJPEG vs WebSockets vs UDP) vs Serial UART | Medición experimental de latencia y estabilidad de FPS |
| **ADR-PEND-02** | Selección del sensor secundario mecatrónico | Sensores de flexión vs IMU (MPU6050) vs sensores de contacto | Disponibilidad de componentes físicos sueltos y pines comprobados |
| **ADR-PEND-03** | Asignación formal de pines GPIO | Pines libres en RPi5 y ESP32-CAM sin conflicto de boot | Verificación contra esquemáticos y pruebas con multímetro/osciloscopio |
| **ADR-PEND-04** | Protocolo de desacoplamiento de Interfaz de Usuario | Web UI (FastAPI/WebSocket local) vs Desktop UI local | Facilidad de visualización en laptop y nula latencia |
| **ADR-PEND-05** | Catálogo específico de señas LSM del Nivel 1 | Señas estáticas vs dinámicas oficiales del reto | Análisis lingüístico de las señas reveladas en el reto a las 10:00 AM |
