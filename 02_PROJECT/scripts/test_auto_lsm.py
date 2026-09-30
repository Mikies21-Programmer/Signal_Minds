"""
Script de validación y prueba en vivo del Clasificador Automático LSM Nivel 1.
Conecta al stream real del ESP32-S3 (http://192.168.4.1:81/stream), procesa landmarks con MediaPipe
y evalúa las señas canónicas A, B, C, L, Y sin mocks ni imágenes sintéticas.

Uso:
  python 02_PROJECT/scripts/test_auto_lsm.py [--frames 30] [--sign LETRA]
"""

import sys
import time
import argparse
from pathlib import Path
from collections import Counter
from typing import Dict, Any

# Agregar directorio raíz del proyecto
PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_ROOT))

from src.backend.config_loader import ConfigLoader
from src.camera.consumer import CameraConsumer
from src.vision.pipeline import VisionPipeline
from src.fusion.engine import SensorFusionEngine
from src.lsm.evaluator import LSMEvaluator
from src.lsm.classifier import AutomaticLSMClassifier


def run_live_test(target_frames: int = 30, prompt_sign: str = "A", stream_url: str = None):
    config = ConfigLoader()
    cam_cfg = config.get("camera", {})
    if not stream_url:
        stream_url = cam_cfg.get("stream_url", "http://192.168.4.1:81/stream")

    # Si uvicorn está ocupando el puerto 81, permitir fallback transparente a localhost
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8000/api/status", timeout=0.5)
        # Si localhost está activo y stream es 192.168.4.1, usar video_feed para no colisionar en puerto 81
        if "192.168.4.1" in stream_url:
            stream_url = "http://localhost:8000/video_feed"
    except Exception:
        pass

    if "camera" not in config._data:
        config._data["camera"] = {}
    config._data["camera"]["stream_url"] = stream_url

    print("=" * 60)
    print("INDIVISA INGENIUM 2026 — PRUEBA REAL DE CLASIFICACIÓN LSM")
    print(f"Stream: {stream_url}")
    print(f"Muestras por seña: {target_frames} frames")
    print(f"Modo: Sin Mocks — Cámara Real + MediaPipe Real + Reglas Geométricas")
    print("=" * 60)

    camera = CameraConsumer(config)
    vision = VisionPipeline(config)
    fusion = SensorFusionEngine(config)
    evaluator = LSMEvaluator(config)
    classifier = AutomaticLSMClassifier(evaluator=evaluator, config=config)

    print("\n[1/4] Iniciando consumidor de cámara real...")
    camera.start()
    
    # Esperar hasta 8 segundos a que lleguen los primeros frames del hardware
    first_frame = None
    for i in range(40):
        first_frame = camera.get_latest_frame()
        if first_frame and first_frame.get("frame") is not None:
            break
        time.sleep(0.2)

    if not first_frame or first_frame.get("frame") is None:
        print("[ERROR] No se pudo obtener frame de la cámara. Verifica conexión a " + str(stream_url))
        camera.stop()
        return

    print(f"[2/4] Cámara operativa. FPS: {first_frame.get('fps', 0.0):.1f} | Res: {first_frame['frame'].shape[1]}x{first_frame['frame'].shape[0]}")
    print("[3/4] Inicializando pipeline MediaPipe + AutomaticLSMClassifier...")

    classifier.reset()
    collected_predictions = []
    collected_scores = {s: [] for s in classifier.SIGNS}

    print(f"\n>>> COLOCA TU MANO HACIENDO LA SEÑA '{prompt_sign.upper()}' FRENTE A LA CÁMARA <<<")
    print("Iniciando muestreo en 2 segundos...")
    time.sleep(2.0)

    frame_count = 0
    valid_hand_frames = 0
    start_time = time.time()

    while valid_hand_frames < target_frames and (time.time() - start_time) < 25.0:
        f_data = camera.get_latest_frame()
        if not f_data or f_data.get("frame") is None:
            time.sleep(0.02)
            continue

        frame_count += 1
        landmarks_data = vision.process_frame(f_data)
        fused_state = fusion.fuse(landmarks_data, sensor_data={"is_mock": False})

        res = classifier.classify(fused_state)
        status = res.get("status")
        detected = res.get("detected", False)

        if detected:
            valid_hand_frames += 1
            pred = res.get("stable_sign") or res.get("predicted_sign")
            collected_predictions.append(pred)

            for s, sc in res.get("candidate_scores", {}).items():
                collected_scores[s].append(sc)

            scores_str = " | ".join(f"{s}:{res['candidate_scores'].get(s, 0.0):.2f}" for s in classifier.SIGNS)
            print(f"[{valid_hand_frames:02d}/{target_frames}] Estado: {status:<13} | Pred: {str(pred):<4} | Conf: {res.get('confidence', 0.0):.2f} | Margen: {res.get('margin', 0.0):.2f} | [{scores_str}]")
        else:
            print(f"[ Esperando mano frente al sensor... Frame {frame_count} ]", end="\r")

        time.sleep(0.04)

    camera.stop()

    print("\n" + "=" * 60)
    print(f"RESULTADOS PARA SEÑA: '{prompt_sign.upper()}'")
    print(f"Total frames con mano procesados: {valid_hand_frames}")

    if valid_hand_frames == 0:
        print("[FALLO] No se detectó ninguna mano durante la prueba.")
        return

    # Predicción dominante
    counts = Counter(collected_predictions)
    dominant_pred, dominant_count = counts.most_common(1)[0]
    consistency_pct = (dominant_count / valid_hand_frames) * 100.0

    print(f"Predicción dominante: {dominant_pred}")
    print(f"Consistencia en prueba de demostración: {consistency_pct:.1f}% ({dominant_count}/{valid_hand_frames} frames)")
    print(f"Distribución de predicciones: {dict(counts)}")

    # Promedio de scores por candidato
    print("\nPromedio de puntuaciones por candidato:")
    for s in classifier.SIGNS:
        avg_s = sum(collected_scores[s]) / len(collected_scores[s]) if collected_scores[s] else 0.0
        bar = "█" * int(avg_s * 25)
        print(f"  {s}: {avg_s:.2f} ({int(avg_s*100)}%)  |{bar:<25}|")

    match = (dominant_pred == prompt_sign.upper())
    print("-" * 60)
    print(f"VEREDICTO: {'PASS (COINCIDE)' if match else 'NEEDS TUNING'}")
    print("=" * 60)

    return {
        "sign": prompt_sign.upper(),
        "dominant_prediction": dominant_pred,
        "consistency_pct": consistency_pct,
        "match": match,
        "valid_frames": valid_hand_frames,
        "distribution": dict(counts)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba automática de LSM Nivel 1")
    parser.add_argument("--frames", type=int, default=30, help="Número de frames a recolectar")
    parser.add_argument("--sign", type=str, default="A", help="Seña esperada a evaluar (A, B, C, L, Y)")
    parser.add_argument("--url", type=str, default=None, help="URL de stream MJPEG")
    args = parser.parse_args()

    run_live_test(target_frames=args.frames, prompt_sign=args.sign, stream_url=args.url)
