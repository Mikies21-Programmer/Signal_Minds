#!/bin/bash
# ==============================================================================
# INDIVISA INGENIUM 2026 — Recolección Diagnóstica de Hardware en Raspberry Pi 5
# ==============================================================================
# Este script inspecciona el hardware real de la Raspberry Pi y genera la
# evidencia requerida en 04_EVIDENCE/hardware/rpi_info.txt.
# No asume valores teóricos; extrae directamente los descriptores del sistema.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/04_EVIDENCE/hardware"
OUTPUT_FILE="$EVIDENCE_DIR/rpi_info.txt"

mkdir -p "$EVIDENCE_DIR"

echo "=============================================================================="
echo "INDIVISA INGENIUM 2026 — RECOLECCIÓN DIAGNÓSTICA DE HARDWARE RPi 5"
echo "Fecha y Hora UTC: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=============================================================================="

{
    echo "=============================================================================="
    echo "INDIVISA INGENIUM 2026 — REPORTE DE HARDWARE FÍSICO RASPBERRY PI"
    echo "Fecha y Hora UTC: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "Host: $(hostname)"
    echo "=============================================================================="
    echo ""

    echo "--- 1. MODELO DE DISPOSITIVO (/proc/device-tree/model) ---"
    if [ -f /proc/device-tree/model ]; then
        tr -d '\0' < /proc/device-tree/model
        echo ""
    else
        echo "NO DISPONIBLE (No es un dispositivo Device-Tree o archivo inaccesible)"
    fi
    echo ""

    echo "--- 2. KERNEL Y SISTEMA OPERATIVO (uname -a) ---"
    uname -a
    echo ""

    echo "--- 3. ARQUITECTURA DEL PROCESADOR (uname -m) ---"
    uname -m
    echo ""

    echo "--- 4. DISTRIBUCIÓN LINUX (/etc/os-release) ---"
    if [ -f /etc/os-release ]; then
        cat /etc/os-release
    else
        echo "ARCHIVO /etc/os-release NO ENCONTRADO"
    fi
    echo ""

    echo "--- 5. MEMORIA RAM FÍSICA Y SWAP (free -h) ---"
    free -h
    echo ""

    echo "--- 6. ALMACENAMIENTO Y PARTICIONES (df -h) ---"
    df -h
    echo ""

    echo "--- 7. TEMPERATURA DEL SOC (vcgencmd measure_temp) ---"
    if command -v vcgencmd >/dev/null 2>&1; then
        vcgencmd measure_temp
    else
        if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
            MILLI_C=$(cat /sys/class/thermal/thermal_zone0/temp)
            echo "temp=$(awk "BEGIN {print $MILLI_C/1000}")'C (vía sysfs)"
        else
            echo "vcgencmd no instalado y thermal_zone0 inaccesible"
        fi
    fi
    echo ""

    echo "--- 8. ESTADO DE THROTTLING / ALIMENTACIÓN (vcgencmd get_throttled) ---"
    if command -v vcgencmd >/dev/null 2>&1; then
        vcgencmd get_throttled
    else
        echo "vcgencmd no disponible en la ruta del sistema"
    fi
    echo ""

    echo "--- 9. ENUMERACIÓN DE PUERTOS USB Y DISPOSITIVOS CONECTADOS (lsusb) ---"
    if command -v lsusb >/dev/null 2>&1; then
        lsusb
    else
        echo "lsusb no disponible"
    fi
    echo ""

    echo "--- 10. ENUMERACIÓN DE INTERFACES I2C / UART (/dev) ---"
    ls -l /dev/i2c* /dev/ttyUSB* /dev/ttyAMA* /dev/serial* 2>/dev/null || echo "No se detectaron nodos I2C/ttyUSB activos en /dev"
    echo ""

    echo "=============================================================================="
    echo "FIN DEL REPORTE DIAGNÓSTICO RPi 5"
    echo "=============================================================================="
} | tee "$OUTPUT_FILE"

echo ""
echo "Reporte guardado exitosamente en: $OUTPUT_FILE"
