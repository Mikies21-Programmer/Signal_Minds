# Constitución Técnica del Proyecto — INDIVISA INGENIUM 2026

**Proyecto:** Dispositivo Mecatrónico y Sistema de Visión Artificial para Retroalimentación en Tiempo Real de Lengua de Señas Mexicana (LSM)  
**Marco:** Convocatoria Oficial Indivisa Ingenium 2026 — Universidad La Salle Oaxaca  
**Vigencia:** 29 y 30 de septiembre de 2026  
**Ámbito:** Obligatorio para todos los agentes de Inteligencia Artificial, desarrolladores, diseñadores e ingenieros que intervengan en este workspace.

---

## Preámbulo y Alcance

Este documento constituye la norma suprema técnica, metodológica y operativa del proyecto. Ninguna instrucción, optimización heurística, librería o suposición podrá invalidar las reglas aquí descritas. Cualquier intervención en el código, arquitectura o documentación debe alinearse de manera estricta con estas cláusulas.

---

## Artículos y Reglas Obligatorias

### 1. Fuente Principal de Requisitos
El documento oficial del reto ubicado en [`00_OFFICIAL/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/00_OFFICIAL) es la **única fuente primaria de verdad** y requisitos funcionales y no funcionales. Toda especificación no presente en los documentos oficiales debe tratarse como hipótesis sujeta a verificación.

### 2. Inmutabilidad de Referencias
Los repositorios y recursos alojados en [`01_REFERENCES/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/01_REFERENCES) son **estrictamente de solo consulta y material de referencia**. Queda terminantemente prohibido modificar, sobreescribir, renombrar o eliminar cualquier archivo dentro de este directorio.

### 3. Delimitación del Código Propio
Todo el código propio, implementaciones, adaptaciones, artefactos derivados y módulos del equipo se desarrollarán **exclusivamente dentro de [`02_PROJECT/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/02_PROJECT)** respetando la estructura interna de subdirectorios (`src/`, `models/`, `data/`, `tests/`, `logs/`, `scripts/`, `config/`).

### 4. Independencia de Red e Internet
**No se permite introducir dependencias obligatorias de Internet** para la ejecución final del sistema. La solución integrada debe funcionar de principio a fin sin conexión externa activa (red aislada / offline).

### 5. Arquitectura Local y Autónoma
La arquitectura completa de software y hardware debe garantizar una **operación 100% local y offline** durante las pruebas, cortes evaluativos y demostración final ante el panel.

### 6. Cerebro de Procesamiento Principal
La plataforma **Raspberry Pi 5** actuará como el cerebro central y nodo maestro de procesamiento para la orquestación del sistema, inferencia de modelos, correlación de datos y servicio de la interfaz.

### 7. Fuente de Adquisición Visual
El módulo **ESP32-CAM** será utilizado como la fuente primaria de adquisición y transmisión de imagen/video hacia el nodo central.

### 8. Instrumentación Mecatrónica Obligatoria
Debe existir una **segunda fuente física de sensores** (sensores de flexión, contacto, IMU, etc.) para la instrumentación física del dispositivo, asegurando el cumplimiento de la naturaleza mecatrónica del reto (fusión sensor-visión).

### 9. Comprobación Rigurosa de Hardware
**Prohibido asumir el modelo exacto, versión o revisión de cualquier componente de hardware** sin haberlo verificado física, técnica o documentalmente de manera previa.

### 10. Prohibición de Asignación Arbitraria de GPIO
**Prohibido inventar o asumir pines GPIO** tanto en la Raspberry Pi 5 como en el ESP32-CAM y placas auxiliares. Toda asignación de pines debe comprobarse contra los pinouts y datasheets oficiales de cada fabricante.

### 11. Cumplimiento Estricto de Licencias
**Prohibido copiar, transferir o adaptar código de terceros** sin haber verificado y validado previamente su licencia de uso (MIT, Apache 2.0, BSD, GPL, etc.) y su compatibilidad con las políticas del proyecto.

### 12. Documentación de Dependencias Externas
Toda dependencia externa (paquetes de Python, bibliotecas de C/C++, binarios compilados o herramientas de sistema) debe ser documentada obligatoriamente en archivos formales de requerimientos (`requirements.txt`, `CMakeLists.txt`, etc.) y registrada en la bitácora técnica.

### 13. Registro Centralizado de Decisiones de Arquitectura
Toda decisión arquitectónica relevante (ADR), cambio estructural o elección tecnológica debe registrarse y formalizarse dentro de [`03_DOCS/architecture/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/architecture).

### 14. Registro de Pruebas y Evidencias
Toda prueba ejecutada debe contar con su script y registro formal en [`02_PROJECT/tests/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/02_PROJECT/tests). Toda evidencia gráfica, audiovisual o de telemetría exigida para los cortes debe organizarse y almacenarse en [`04_EVIDENCE/`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/04_EVIDENCE).

### 15. Prohibición de Parches Destructivos
**No se permite eliminar ni mutilar funcionalidad existente** para solventar un bug o error imprevisto sin documentar previamente la justificación técnica, el análisis de impacto y obtener validación explícita.

### 16. Protocolo de Acreditación de Funcionalidad
Antes de afirmar o reportar que un módulo o función se encuentra operativo, es requisito indispensable:
- Ejecutar la prueba formalmente.
- Registrar el resultado obtenido (métricas cuantitativas/cualitativas).
- Registrar los errores o excepciones observados.
- Indicar explícitamente el hardware real utilizado en la prueba.

### 17. Criterios de Validación Lingüística en LSM
**Prohibido afirmar el reconocimiento correcto de una seña de LSM únicamente a partir de una predicción visual o clasificación aislada.** El sistema debe evaluar y validar los parámetros formativos del signo lingüístico:
1. **Configuración manual (Queirema):** Forma de la mano y dedos.
2. **Orientación:** Dirección de la palma y eje de la mano.
3. **Movimiento (Kinema):** Trayectoria, repetición y dinamismo del signo.
4. **Ubicación (Toponema):** Posición espacial de la mano con respecto al cuerpo o espacio gestual.

### 18. Prioridad Escalonada por Niveles
**El Nivel 1 (funcionalidad base e integración inicial indispensable) tiene prioridad absoluta** sobre el Nivel 2 y el Nivel 3. No se avanzará a refinamientos o características avanzadas mientras los cimientos no estén verificados y estables.

### 19. Jerarquía de Atributos de Calidad
En todo momento de toma de decisiones técnicas, diseño y optimización, la jerarquía de prioridad innegociable es:
$$\mathbf{Robustez} > \mathbf{Explicabilidad} > \mathbf{Latencia} > \mathbf{Complejidad\ del\ Modelo}$$

### 20. Exclusión Explícita de Hardware CLB7INH
El componente / pantalla **CLB7INH queda COMPLETAMENTE FUERA DEL PROYECTO**. Queda terminantemente prohibido generar código, drivers, esquemáticos, presupuestos de pines o dependencias arquitectónicas vinculadas a dicha pantalla.

### 21. Desacoplamiento de la Interfaz de Usuario
La interfaz actual se diseñará para su visualización y operación en una **computadora / laptop**, manteniéndose estrictamente **desacoplada del backend** (comunicación mediante APIs limpias, WebSockets o sockets locales).

### 22. Estándar de Modularidad para Nuevos Componentes
Todo nuevo módulo, servicio o script que se integre al proyecto debe incluir en su encabezado y documentación:
- **Propósito:** Función concreta y justificación técnica.
- **Entradas:** Tipos de datos, formatos, rangos o pines requeridos.
- **Salidas:** Estructura de respuesta, estados y códigos de retorno.
- **Dependencias:** Librerías o módulos de los que requiere para operar.
- **Prueba mínima:** Procedimiento o script para su testeo unitario inmediato.

### 23. Resolución de Discrepancias
Si en cualquier momento se detecta un conflicto o contradicción entre una suposición del modelo/desarrollo y lo establecido en un documento oficial, el agente o desarrollador debe **detenerse inmediatamente, señalar la discrepancia y solicitar aclaración**.

### 24. Aprobación Previa de Cambios Masivos
**Queda prohibido realizar cambios masivos, reestructuraciones de carpetas o refactorizaciones profundas** sin presentar previamente un plan detallado de acción al responsable del proyecto.

---

## Compromiso Institucional
> *"INDIVISA MANENT — Lo unido permanece."*  
> La disciplina técnica, el respeto por las normas de ingeniería y la responsabilidad social hacia la comunidad sorda son los pilares que rigen este desarrollo.
