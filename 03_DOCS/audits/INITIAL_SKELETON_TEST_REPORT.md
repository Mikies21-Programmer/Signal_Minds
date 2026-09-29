# Reporte de Pruebas del Esqueleto Inicial — INDIVISA INGENIUM 2026

**Fecha:** 29 de septiembre de 2026  
**Ubicación:** [`03_DOCS/audits/INITIAL_SKELETON_TEST_REPORT.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/audits/INITIAL_SKELETON_TEST_REPORT.md)  
**Proyecto:** Esqueleto Base del Software (`02_PROJECT/`)  
**Responsable:** Agente Técnico de Arquitectura e Integración  
**Cumplimiento Normativo:** Regla 14 y 16 de [`AGENTS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/AGENTS.md) (ejecutar pruebas, registrar resultados, registrar errores e indicar hardware real).

---

## 1. Entorno Real de Ejecución

- **Hardware Real Utilizado:** Laptop Host (ASUS Vivobook 12th Gen Intel Core i5-1235U, 10 Cores, 24 GB RAM)
- **Sistema Operativo:** Microsoft Windows 11 Home Single Language (Versión 10.0.26200, 64-bit)
- **Python Runtime:** Python 3.11.9 (64-bit)
- **Framework de Pruebas:** `pytest-9.1.1`

---

## 2. Resultados del Diagnóstico de Arranque (Health Check)

Ejecución del comando: `python scripts/run_health_check.py`

```text
======================================================================
  INDIVISA INGENIUM 2026 — DIAGNÓSTICO DE ARRANQUE Y SALUD
======================================================================
[1] VERSIÓN DEL SISTEMA:
    Proyecto : INDIVISA_INGENIUM_2026
    Versión  : 0.1.0
    Entorno  : development

[2] ESTADO DE HARDWARE DETECTADO:
    Sistema Operativo : Windows (10, AMD64)
    Procesador        : Intel64 Family 6 Model 154 Stepping 4, GenuineIntel
    Dispositivo Host  : Laptop / Dev Host
    ¿Es Raspberry Pi? : NO (Modo Laptop/Desarrollo)
    Cámara            : Mock Mode (Simulado)
    Sensores          : Mock Mode (Simulado)
    Python Runtime    : 3.11.9

[3] ESTADO DE REGISTRO (LOGGING):
    Archivo de Log    : 02_PROJECT/logs/indivisa.log
    ¿Es escribible?   : SÍ
    Estado de Logging : HEALTHY

[4] SUBSISTEMAS DEL PIPELINE:
    - backend      : READY
    - camera       : READY (MOCK)
    - vision       : READY (MOCK)
    - sensors      : READY (MOCK)
    - fusion       : READY
    - lsm          : READY (Nivel 1 Activo)
    - feedback     : READY
    - frontend     : READY (Desacoplado)

[5] PRUEBA DE CICLO DEL ORQUESTADOR (1 FRAME):
    Seña objetivo     : 'A'
    Latencia pipeline : 0.07 ms (Mock)
    Score obtenido    : 0.922
    Veredicto         : VÁLIDO
    Feedback primario : "¡Excelente! Seña 'A' ejecutada correctamente."
    Sugerencia        : "Mantén la postura estable."

======================================================================
  RESULTADO: PROYECTO INICIALIZADO CON ÉXITO — TODOS LOS MÓDULOS ACTIVOS
======================================================================
```

---

## 3. Resultados de la Suite Automatizada de Pruebas (Pytest)

Ejecución del comando: `python -m pytest tests/ -v`

| Archivo de Prueba | Caso de Prueba | Resultado | Tiempo |
| :--- | :--- | :---: | :---: |
| `tests/test_config.py` | `test_load_default_config` | **PASSED** | < 0.01 s |
| `tests/test_config.py` | `test_config_sections_exist` | **PASSED** | < 0.01 s |
| `tests/test_config.py` | `test_level_1_signs_configured` | **PASSED** | < 0.01 s |
| `tests/test_health.py` | `test_health_check_execution` | **PASSED** | < 0.01 s |
| `tests/test_health.py` | `test_hardware_status_fields` | **PASSED** | < 0.01 s |
| `tests/test_health.py` | `test_logging_system_status` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_backend` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_camera` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_vision` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_sensors` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_fusion` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_lsm` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_feedback` | **PASSED** | < 0.01 s |
| `tests/test_imports.py` | `test_import_frontend` | **PASSED** | < 0.01 s |
| `tests/test_logging.py` | `test_logger_file_write` | **PASSED** | 0.01 s |
| `tests/test_pipeline_step.py` | `test_orchestrator_single_step` | **PASSED** | 0.01 s |
| `tests/test_pipeline_step.py` | `test_level_1_signs_evaluation` | **PASSED** | 0.02 s |
| `tests/test_pipeline_step.py` | `test_frontend_keyboard_shortcuts` | **PASSED** | < 0.01 s |
| **TOTAL** | **18 pruebas ejecutadas** | **18 PASSED (100%)** | **0.26 s** |

---

## 4. Registro de Errores e Incidencias Subsanadas

1. **Typo Booleano en logger:**
   - *Error:* Se detectó `log_to_console: bool = true` (minúscula) en `src/backend/logger.py`.
   - *Solución:* Corregido inmediatamente a `True` de acuerdo a la sintaxis estricta de Python.
2. **Dependencias Circulares:**
   - *Resultado:* Cero dependencias circulares. Todos los submódulos se importan jerárquicamente de manera limpia.
3. **Persistencia de Logs:**
   - *Resultado:* Archivo [`02_PROJECT/logs/indivisa.log`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/02_PROJECT/logs/indivisa.log) creado con rotación y verificado.
