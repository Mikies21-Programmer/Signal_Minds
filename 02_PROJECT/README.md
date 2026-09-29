# INDIVISA INGENIUM 2026 — Código del Proyecto

**Ubicación:** `C:\Users\migue\Downloads\SALLE\INDIVISA_INGENIUM_2026\02_PROJECT`  
**Versión:** 0.1.0  
**Estado:** Esqueleto base verificado (Health Check y Pruebas Unitarias Activas)  

---

## 1. Estructura de Paquetes en `src/`

```text
02_PROJECT/
├── README.md
├── requirements.txt
├── config/
│   └── settings.json          # Configuración centralizada de hardware y pipeline
├── logs/
│   └── indivisa.log           # Bitácora de ejecución con rotación automática
├── scripts/
│   └── run_health_check.py    # Script ejecutable de diagnóstico de arranque
├── src/
│   ├── backend/               # Orquestador, configuración, logger, excepciones y salud
│   ├── camera/                # Cliente de flujo de video y control de conexión ESP32-CAM
│   ├── vision/                # MediaPipe Hands y normalización de 63 landmarks
│   ├── sensors/               # Adquisición de la segunda fuente mecatrónica (flex/IMU)
│   ├── fusion/                # Fusión sensorial (Visión + Hardware físico)
│   ├── lsm/                   # Evaluador morfológico de 4 parámetros (Prioridad Nivel 1)
│   ├── feedback/              # Motor de retroalimentación pedagógica y explicable
│   └── frontend/              # Controlador de interfaz desacoplada y atajos de teclado
└── tests/                     # Suite de pruebas automatizadas con pytest
```

---

## 2. Instrucciones de Ejecución

### Ejecución del Diagnóstico de Arranque y Health Check
Para comprobar que el proyecto arranque, importe sus módulos, registre logs y reporte el estado de hardware:

```powershell
python scripts/run_health_check.py
```

### Ejecución de Pruebas Unitarias
Para ejecutar la suite completa de pruebas:

```powershell
pytest tests/ -v
```

---

## 3. Prioridad de Señas de Lengua de Señas Mexicana (LSM)

1. **Nivel 1 (Prioridad Inmediata):** Señas estáticas: **`A`**, **`B`**, **`C`**, **`L`**, **`Y`**.
   - Evaluación obligatoria de Configuración manual y Orientación de la palma.
   - Atajos directos por teclado de laptop: Teclas `A`, `B`, `C`, `L`, `Y`.
2. **Nivel 2 (Siguiente Fase):** Señas dinámicas: **`J`**, **`Ñ`**, **`Q`**, **`X`**, **`Z`** (pooling estadístico temporal).
3. **Nivel 3 (Fase Final):** Frases y vocabulario compuesto: **`HOLA`**, **`GRACIAS`**, **`POR FAVOR`**, **`AYUDA`**, **`MAMÁ`**.

---

## 4. Políticas Operativas
- **Sin conexión obligatoria:** Operación 100% local y offline.
- **Hardware verificado:** Todo periférico corre en modo seguro/mock hasta que el hardware físico sea inspeccionado y comprobado.
