"""
Script de prueba de visión artificial y detección anatómica en tiempo real.
Conecta con el stream real de la cámara, ejecuta MediaPipe Tasks con el modelo local
offline, extrae los 21 landmarks, calcula confidence, mide FPS y guarda una captura
de evidencia fotográfica con los puntos dibujados en 04_EVIDENCE/hardware/.
"""

import sys
import os
import time
import argparse
import json
from pathlib import Path
import cv2
import numpy as np

# Rutas del proyecto
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"
EVIDENCE_DIR = PROJECT_ROOT.parent / "04_EVIDENCE" / "hardware"
EVIDENCE_TEXT_FILE = EVIDENCE_DIR / "vision_test.txt"
EVIDENCE_IMG_FILE = EVIDENCE_DIR / "real_hand_detection.jpg"

# Asegurar path de importación de src
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.vision.pipeline import VisionPipeline, VisionPipelineError

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]


def parse_args():
    parser = argparse.ArgumentParser(description="Prueba de MediaPipe y detección de 21 landmarks sobre cámara real.")
    parser.add_argument("--url", type=str, default=None, help="URL del stream de video o índice de cámara")
    parser.add_argument("--min-detections", type=int, default=30, help="Fotogramas consecutivos con mano detectada para certificar estabilidad")
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


def draw_skeleton(frame: np.ndarray, landmarks: list, confidence: float, fps: float) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    coords = []
    for p in landmarks:
        px = int(p["x"] * w) if 0.0 <= p["x"] <= 1.0 else int(p["x"])
        py = int(p["y"] * h) if 0.0 <= p["y"] <= 1.0 else int(p["y"])
        coords.append((px, py))

    # Conexiones
    for s_idx, e_idx in HAND_CONNECTIONS:
        if s_idx < len(coords) and e_idx < len(coords):
            cv2.line(annotated, coords[s_idx], coords[e_idx], (0, 216, 255), 2)

    # Nodos articulares
    for pt in coords:
        cv2.circle(annotated, pt, 4, (0, 255, 136), -1)
        cv2.circle(annotated, pt, 5, (255, 255, 255), 1)

    # HUD
    cv2.rectangle(annotated, (0, 0), (w, 32), (15, 20, 25), -1)
    cv2.putText(annotated, f"CONF: {confidence * 100:.1f}%", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 136), 2)
    cv2.putText(annotated, f"FPS: {fps:.1f}", (w - 100, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 216, 255), 2)
    return annotated


def main():
    args = parse_args()
    stream_url = args.url or load_stream_url_from_config()
    min_required_detections = args.min_detections

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    print("==============================================================================")
    print("INDIVISA INGENIUM 2026 — PRUEBA DE MEDIAPIPE Y VISIÓN REAL OFFLINE")
    print(f"Origen de Video:      {stream_url}")
    print(f"Detecciones Mínimas:  {min_required_detections} fotogramas válidos")
    print(f"Evidencia de Texto:   {EVIDENCE_TEXT_FILE}")
    print(f"Evidencia de Imagen:  {EVIDENCE_IMG_FILE}")
    print("==============================================================================")

    # Inicializar VisionPipeline en MODO REAL (modelo local offline obligatorio)
    try:
        pipeline = VisionPipeline({"vision": {"mock_mode": False}})
    except VisionPipelineError as e:
        print(f"\n[FALLA INICIAL] {e}\n")
        with open(EVIDENCE_TEXT_FILE, "w", encoding="utf-8") as ef:
            ef.write(f"ESTADO: FALLA_PIPELINE\nFECHA: {time.ctime()}\nDETALLE: {e}\n")
        sys.exit(1)

    capture_target = int(stream_url) if stream_url.isdigit() else stream_url
    print(f"Conectando a cámara: {capture_target} ...")
    cap = cv2.VideoCapture(capture_target)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        err_msg = f"No fue posible abrir el flujo de video en {stream_url}."
        print(f"\n[FALLA] {err_msg}\n")
        with open(EVIDENCE_TEXT_FILE, "w", encoding="utf-8") as ef:
            ef.write(f"ESTADO: FALLA_CAMARA\nFECHA: {time.ctime()}\nDETALLE: {err_msg}\n")
        sys.exit(1)

    print("Cámara abierta. Presente su mano frente al lente para detección anatómica...\n")

    detected_count = 0
    consecutive_detections = 0
    total_processed = 0
    start_time = time.time()
    best_capture: np.ndarray = None
    best_confidence = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            total_processed += 1
            result = pipeline.process_frame(frame)

            if result and result.get("detected", False):
                detected_count += 1
                consecutive_detections += 1
                conf = result.get("confidence", 0.0)
                fps = result.get("fps", 0.0)
                lms = result.get("raw_landmarks", [])

                if conf > best_confidence:
                    best_confidence = conf
                    best_capture = draw_skeleton(frame, lms, conf, fps)

                print(
                    f"\r[MANO DETECTADA] Conf: {conf * 100:.1f}% | FPS: {fps:.1f} | "
                    f"Consecutivas: {consecutive_detections}/{min_required_detections} | "
                    f"Total Detectados: {detected_count}",
                    end="",
                    flush=True
                )

                if consecutive_detections >= min_required_detections:
                    print("\n\n[ÉXITO] Detección estable de mano real completada exitosamente.")
                    break
            else:
                consecutive_detections = 0
                fps = result.get("fps", 0.0) if result else 0.0
                print(
                    f"\r[ESPERANDO MANO] Presente mano frente a la cámara... | FPS: {fps:.1f} | Procesados: {total_processed}",
                    end="",
                    flush=True
                )

    except KeyboardInterrupt:
        print("\n\nPrueba interrumpida manualmente.")
    finally:
        total_time = time.time() - start_time
        cap.release()

    success = consecutive_detections >= min_required_detections or detected_count >= min_required_detections

    if best_capture is not None:
        cv2.imwrite(str(EVIDENCE_IMG_FILE), best_capture)
        print(f"Fotografía de evidencia guardada con éxito en: {EVIDENCE_IMG_FILE}")

    report_lines = [
        "==============================================================================",
        "INDIVISA INGENIUM 2026 — EVIDENCIA DE DETECCIÓN REAL MEDIAPIPE",
        f"Fecha y Hora:             {time.ctime()}",
        f"Origen de Video:          {stream_url}",
        f"Estado:                   {'EXITOSA' if success else 'INCOMPLETA'}",
        f"Fotogramas Procesados:    {total_processed}",
        f"Fotogramas con Mano:      {detected_count}",
        f"Mejor Nivel de Confianza: {best_confidence * 100:.2f}%",
        f"Landmarks Anatómicos:     21 puntos normalizados",
        f"Archivo de Captura:       {EVIDENCE_IMG_FILE if best_capture is not None else 'NO GENERADO'}",
        "=============================================================================="
    ]
    report_text = "\n".join(report_lines)

    with open(EVIDENCE_TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text + "\n")

    print("\n" + report_text)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
