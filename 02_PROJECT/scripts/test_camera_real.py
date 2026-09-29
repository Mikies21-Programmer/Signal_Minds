"""
Script de prueba de transmisión continua para ESP32-CAM con hardware real.
Evalúa estabilidad, FPS, resolución, pérdidas de fotogramas y tiempo de conexión.
Criterio de éxito: Mínimo 5 minutos (300 s) de transmisión estable con hardware real.
Guarda evidencia en 04_EVIDENCE/hardware/camera_test.txt.
"""

import sys
import os
import time
import argparse
import json
from pathlib import Path
import cv2

# Rutas del proyecto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"
EVIDENCE_DIR = PROJECT_ROOT.parent / "04_EVIDENCE" / "hardware"
EVIDENCE_FILE = EVIDENCE_DIR / "camera_test.txt"


def parse_args():
    parser = argparse.ArgumentParser(description="Prueba de estabilidad y streaming para ESP32-CAM real.")
    parser.add_argument("--url", type=str, default=None, help="URL del stream MJPEG/HTTP (ej. http://192.168.4.1/stream)")
    parser.add_argument("--duration", type=int, default=300, help="Duración mínima de la prueba en segundos (defecto: 300s = 5 min)")
    parser.add_argument("--timeout", type=float, default=3.0, help="Timeout por fotograma en segundos")
    return parser.parse_args()


def load_stream_url_from_config() -> str:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("camera", {}).get("stream_url", "http://192.168.4.1/stream")
        except Exception:
            pass
    return "http://192.168.4.1/stream"


def main():
    args = parse_args()
    stream_url = args.url or load_stream_url_from_config()
    target_duration = args.duration
    frame_timeout = args.timeout

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    print("==============================================================================")
    print("INDIVISA INGENIUM 2026 — PRUEBA DE STREAMING ESP32-CAM CON HARDWARE REAL")
    print(f"URL de Prueba:        {stream_url}")
    print(f"Duración Objetivo:    {target_duration} s ({target_duration / 60:.1f} minutos)")
    print(f"Timeout por Cuadro:   {frame_timeout} s")
    print(f"Archivo de Evidencia: {EVIDENCE_FILE}")
    print("==============================================================================")

    # Permitir índice entero si se pasa "0"
    capture_target = int(stream_url) if stream_url.isdigit() else stream_url

    print(f"Intentando abrir conexión con: {capture_target} ...")
    cap = cv2.VideoCapture(capture_target)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        err_msg = (
            f"ERROR FÍSICO: No fue posible abrir el stream de la cámara en {stream_url}.\n"
            "Verifique que el ESP32-CAM esté encendido, conectado a la misma red Wi-Fi y con el firmware de streaming activo."
        )
        print(f"\n[FALLA] {err_msg}\n")
        with open(EVIDENCE_FILE, "w", encoding="utf-8") as ef:
            ef.write(f"ESTADO: FALLA_CONEXION\nFECHA: {time.ctime()}\nURL: {stream_url}\nDETALLE: {err_msg}\n")
        sys.exit(1)

    print("Conexión inicial establecida exitosamente. Iniciando prueba de estabilidad...\n")

    start_time = time.time()
    last_frame_time = time.time()
    total_frames = 0
    dropped_frames = 0
    fps = 0.0
    frames_in_sec = 0
    fps_timer = time.time()
    resolution = "DESCONOCIDA"

    try:
        while True:
            now = time.time()
            elapsed = now - start_time

            if elapsed >= target_duration:
                print("\n\n[ÉXITO] Duración objetivo de 5 minutos alcanzada sin interrupciones críticas.")
                break

            ret, frame = cap.read()
            now_read = time.time()

            if not ret or frame is None:
                if (now_read - last_frame_time) > frame_timeout:
                    dropped_frames += 1
                    print(f"\r[ALERTA] Cuadro perdido. Sin datos en {now_read - last_frame_time:.1f}s | Drops: {dropped_frames}", end="")
                    if (now_read - last_frame_time) > (frame_timeout * 3):
                        print(f"\n[FALLA CRÍTICA] Stream congelado durante más de {frame_timeout * 3}s. Abortando.")
                        break
                time.sleep(0.01)
                continue

            last_frame_time = now_read
            total_frames += 1
            frames_in_sec += 1

            if resolution == "DESCONOCIDA" and frame is not None:
                h, w = frame.shape[:2]
                resolution = f"{w}x{h}"

            # Cálculo de FPS cada 1 segundo
            if (now_read - fps_timer) >= 1.0:
                fps = frames_in_sec / (now_read - fps_timer)
                frames_in_sec = 0
                fps_timer = now_read

            rem_sec = int(target_duration - elapsed)
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            print(
                f"\r[STREAMING REAL] URL: {stream_url} | Res: {resolution} | FPS: {fps:.1f} | "
                f"Tiempo: {mins:02d}:{secs:02d} / {target_duration // 60:02d}:00 | "
                f"Frames: {total_frames} | Drops: {dropped_frames}",
                end="",
                flush=True
            )

    except KeyboardInterrupt:
        print("\n\nPrueba interrumpida manualmente por el usuario.")
    finally:
        total_time = time.time() - start_time
        cap.release()

    # Guardar reporte de evidencia
    success = (total_time >= (target_duration * 0.95)) and (total_frames > (target_duration * 5))
    result_status = "EXITOSA" if success else "INCOMPLETA_O_FALLIDA"

    report_lines = [
        "==============================================================================",
        "INDIVISA INGENIUM 2026 — EVIDENCIA DE TRANSMISIÓN REAL ESP32-CAM",
        f"Fecha y Hora:           {time.ctime()}",
        f"URL Evaluada:           {stream_url}",
        f"Estado Final:           {result_status}",
        f"Tiempo Total Conectado: {total_time:.2f} s ({total_time / 60:.2f} min)",
        f"Resolución de Video:    {resolution}",
        f"Fotogramas Recibidos:   {total_frames}",
        f"Fotogramas Perdidos:    {dropped_frames}",
        f"FPS Promedio:           {(total_frames / max(1.0, total_time)):.2f}",
        "=============================================================================="
    ]
    report_text = "\n".join(report_lines)

    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        f.write(report_text + "\n")

    print("\n\n" + report_text)
    print(f"\nEvidencia guardada en: {EVIDENCE_FILE}")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
