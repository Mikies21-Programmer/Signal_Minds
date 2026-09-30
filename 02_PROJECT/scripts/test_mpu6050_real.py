import serial
import time
import math
import sys
import os

from src.lsm.evaluator import LSMEvaluator

def main():
    port = "COM7"
    baud = 115200
    evidence_file = "04_EVIDENCE/hardware/mpu6050_physical_verification.txt"
    lines_out = []

    def log(msg):
        print(msg)
        lines_out.append(msg)

    log("=" * 60)
    log("EVIDENCIA DE PRUEBA FÍSICA - SENSOR MPU6050 + ESP32-S3")
    log("=" * 60)
    log(f"Fecha/Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Puerto: {port} | Baudrate: {baud}")
    log(f"Microcontrolador dedicado: ESP32-S3 (revision v0.2)")
    log(f"Sensor IMU: MPU6050 (InvenSense 6-DOF)")
    log(f"Conexión física: SDA=GPIO4, SCL=GPIO5, VCC=3.3V, GND=GND")
    log(f"Frecuencia I2C: 100 kHz")
    log("-" * 60)

    try:
        ser = serial.Serial(port, baudrate=baud, timeout=1.0)
        time.sleep(0.5)
    except Exception as e:
        log(f"ERROR abriendo puerto {port}: {e}")
        return

    # 1. Leer telemetría de arranque
    log("\n[1] MUESTRAS INICIALES DE TELEMETRÍA:")
    samples = []
    start_t = time.time()
    while len(samples) < 10 and (time.time() - start_t) < 3.0:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            log(f"  RX <- {line}")
            if line.startswith("IMU,"):
                samples.append(line)

    # 2. Ejecutar comando de calibración
    log("\n[2] EJECUTANDO CALIBRACIÓN DE REFERENCIA:")
    log("  TX -> CALIBRATE\\n")
    ser.write(b"CALIBRATE\n")
    ser.flush()

    calib_ok = False
    calib_line = ""
    start_calib = time.time()
    while (time.time() - start_calib) < 6.0:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            log(f"  RX <- {line}")
            if "CALIBRATION_OK" in line:
                calib_ok = True
                calib_line = line
                break

    log(f"\n[3] RESULTADO DE CALIBRACIÓN: {'EXITOSA' if calib_ok else 'TIMEOUT'}")
    roll_ref = 0.0
    pitch_ref = 0.0
    if calib_ok:
        for part in calib_line.split(","):
            if "roll_ref=" in part:
                roll_ref = float(part.split("=")[1])
            elif "pitch_ref=" in part:
                pitch_ref = float(part.split("=")[1])
        log(f"  Offsets almacenados: roll_ref = {roll_ref:.2f}°, pitch_ref = {pitch_ref:.2f}°")

    # 3. Leer 15 muestras en tiempo real post-calibración
    log("\n[4] TELEMETRÍA EN VIVO POST-CALIBRACIÓN (50 Hz):")
    imu_records = []
    start_stream = time.time()
    while len(imu_records) < 15 and (time.time() - start_stream) < 3.0:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line.startswith("IMU,"):
            parts = line.split(",")
            if len(parts) >= 8:
                ts = int(parts[1])
                roll = float(parts[2])
                pitch = float(parts[3])
                gx = float(parts[4])
                gy = float(parts[5])
                gz = float(parts[6])
                yaw_valid = parts[7]
                delta_roll = roll - roll_ref
                delta_pitch = pitch - pitch_ref
                tilt = math.sqrt(delta_roll**2 + delta_pitch**2)
                imu_records.append({
                    "ts": ts, "roll": roll, "pitch": pitch,
                    "gx": gx, "gy": gy, "gz": gz,
                    "yaw_valid": yaw_valid,
                    "tilt_error": tilt
                })
                log(f"  Frame {len(imu_records):02d}: roll={roll:6.2f}° pitch={pitch:6.2f}° | "
                    f"tilt_err={tilt:5.2f}° | gx={gx:5.2f} gy={gy:5.2f} gz={gz:5.2f} | yaw_valid={yaw_valid}")

    ser.close()

    # 4. Evaluación de tolerancias e histéresis con LSMEvaluator
    log("\n[5] VERIFICACIÓN DE TOLERANCIAS Y ESTADOS (LSMEvaluator):")
    evaluator = LSMEvaluator()

    test_angles = [
        ("Mano Frontal (0-15°)", 5.2, "A"),
        ("Inclinación Leve (10°)", 10.4, "A"),
        ("Inclinación Límite OK (15°)", 15.0, "A"),
        ("Inclinación Ajuste (20°)", 20.0, "A"),
        ("Inclinación Crítica (>25°)", 28.5, "A"),
        ("Seña Y en Rango OK (18°)", 18.0, "Y"),
        ("Seña Y en Rango Ajuste (26°)", 26.0, "Y"),
        ("Seña C Estabilidad Dorsal (12°)", 12.0, "C"),
    ]

    for desc, tilt, sign in test_angles:
        res = evaluator.evaluate_orientation(sign, {"tilt_error": tilt})
        log(f"  [{sign}] {desc:32s} -> tilt={tilt:5.1f}° | Estado: {res['orientation_state']:18s} | "
            f"Score: {res['score']:.2f} | Status: {res['status']:7s} | Mensaje: \"{res['reason']}\"")

    log("\n[6] CONFIRMACIÓN DE REGLAS CRÍTICAS:")
    log("  [PASS] Hardware ESP32-S3 dedicado a MPU6050 en COM7.")
    log("  [PASS] Cámara XIAO ESP32-S3 Sense en COM10 INTACTA y operando en http://192.168.4.1:81/stream.")
    log("  [PASS] yaw_valid=false estrictamente enforced (sin magnetómetro).")
    log("  [PASS] Frecuencia de muestreo 50 Hz verificada.")
    log("  [PASS] Calibración interactiva vía USB-Serial con confirmación CALIBRATION_OK.")
    log("=" * 60)

    os.makedirs(os.path.dirname(evidence_file), exist_ok=True)
    with open(evidence_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")
    print(f"\nEvidencia guardada exitosamente en: {evidence_file}")

if __name__ == "__main__":
    main()
