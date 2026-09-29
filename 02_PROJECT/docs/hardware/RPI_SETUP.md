# Guía de Configuración de Entorno en Raspberry Pi 5 (ARM64) — INDIVISA INGENIUM 2026

**Fecha de Registro:** 29 de septiembre de 2026  
**Ubicación:** [`02_PROJECT/docs/hardware/RPI_SETUP.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/02_PROJECT/docs/hardware/RPI_SETUP.md)  
**Arquitectura:** aarch64 / ARM64 (Broadcom BCM2712)  
**Sistema Operativo Objetivo:** Raspberry Pi OS 64-bit (Debian 12 Bookworm)

---

## 1. Requisitos Previos en la Raspberry Pi 5

Asegúrate de que la Raspberry Pi 5 esté encendida con una fuente oficial de 5V / 5A USB-C PD, conectada a la red local (Wi-Fi o Ethernet) y accesible vía SSH o terminal local.

---

## 2. Actualización del Sistema y Dependencias Nativas de C/C++

MediaPipe y OpenCV headless en Linux ARM64 requieren bibliotecas del sistema para decodificación de video y manejo de hilos. Ejecuta:

```bash
sudo apt update && sudo apt upgrade -y

# Dependencias nativas requeridas para OpenCV, MediaPipe y comunicación serie
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    v4l-utils \
    i2c-tools
```

---

## 3. Clonación / Sincronización del Repositorio

Si aún no has clonado el repositorio en la Raspberry Pi 5:

```bash
cd ~
git clone https://github.com/Mikies21-Programmer/Signal_Minds.git
cd Signal_Minds
```

---

## 4. Creación y Activación del Entorno Virtual (venv)

Debian 12 (Bookworm) impone PEP 668 (`externally-managed-environment`), por lo que **es mandatorio** utilizar un entorno virtual aislado:

```bash
cd ~/Signal_Minds/02_PROJECT

# Crear entorno virtual aislado
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate

# Actualizar el gestor de paquetes pip
pip install --upgrade pip
```

---

## 5. Instalación de Dependencias del Proyecto

Instala las dependencias verificadas desde el archivo de requisitos:

```bash
pip install -r requirements.txt
```

> [!IMPORTANT]
> **Compatibilidad NumPy y MediaPipe:**
> `requirements.txt` restringe estrictamente `numpy>=1.24.0,<2.0.0` porque las extensiones C++ de MediaPipe (`mediapipe-tasks`) requieren compatibilidad con la ABI de NumPy 1.x. No instales NumPy 2.x en la Raspberry Pi.

---

## 6. Verificación de Importaciones en la Raspberry Pi 5

Ejecuta el siguiente comando para certificar que todos los módulos binarios cargan limpiamente en ARM64:

```bash
python -c "
import numpy as np
import cv2
import mediapipe as mp
import fastapi
import uvicorn
import websockets
import serial
import pytest
print('========================================')
print('VERIFICACIÓN EXITOSA EN RASPBERRY PI 5')
print('NumPy:', np.__version__)
print('OpenCV:', cv2.__version__)
print('MediaPipe:', mp.__version__)
print('FastAPI:', fastapi.__version__)
print('========================================')
"
```

---

## 7. Ejecución de la Recolección Diagnóstica de Hardware

Genera la evidencia física oficial del nodo Raspberry Pi 5 ejecutando el script preparado:

```bash
chmod +x scripts/collect_rpi_info.sh
./scripts/collect_rpi_info.sh
```

El script imprimirá en pantalla y guardará automáticamente el resultado en:
`04_EVIDENCE/hardware/rpi_info.txt`.

---

## 8. Verificación de la Suite de Pruebas en ARM64

Para comprobar la integridad del software antes de conectar los periféricos físicos:

```bash
pytest
```

Todas las 46 pruebas automatizadas deben pasar en verde.

---

## 9. Inicio del Servicio en la Raspberry Pi 5

Para arrancar el servidor backend del orquestador y la API en la Raspberry Pi:

```bash
# Con el entorno virtual activo:
uvicorn src.backend.api:app --host 0.0.0.0 --port 8000
```

Desde la Laptop, abre en el navegador web:
`http://<IP_DE_LA_RASPBERRY_PI>:8000`
