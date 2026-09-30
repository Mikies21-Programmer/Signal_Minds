"""
Herramienta de Diagnóstico y Calibración de Precisión en Vivo para LSM Nivel 1.
Conecta a la cámara física (ESP32-S3 Sense a 640x480 o stream backend) y ejecuta
pruebas reales con landmarks anatómicos MediaPipe para A, B, C, L, Y y pruebas de confusión.

Sin ML nuevo. Sin reentrenamiento. Diagnóstico directo de reglas explicables.
"""

import sys
import time
import argparse
import math
from pathlib import Path
from collections import deque
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np

# Asegurar importación de módulos del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.config_loader import ConfigLoader
from src.vision.pipeline import VisionPipeline
from src.lsm.geometry import HandGeometryFeatures
from src.lsm.evaluator import LSMEvaluator
from src.lsm.classifier import AutomaticLSMClassifier


class RealSignCalibrator:
    """Ejecutor de pruebas de calibración y análisis de confusión en cámara real."""

    def __init__(self, stream_url: str = "http://192.168.4.1:81/stream", config=None):
        self.stream_url = stream_url
        self.config = config or ConfigLoader()
        self.vision = VisionPipeline(self.config)
        self.evaluator = LSMEvaluator(self.config)
        self.classifier = AutomaticLSMClassifier(evaluator=self.evaluator, config=self.config)
        self.cap: Optional[cv2.VideoCapture] = None

    def connect_camera(self) -> bool:
        """Establece conexión con el flujo de video MJPEG."""
        print(f"[*] Conectando a flujo de video: {self.stream_url} ...")
        # Intentar stream primario
        self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        t_start = time.time()
        connected = False
        while (time.time() - t_start) < 4.0:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    connected = True
                    h, w = frame.shape[:2]
                    print(f"[+] Conectado exitosamente. Resolución del stream: {w}x{h}")
                    return True
            time.sleep(0.2)

        # Fallback a stream local si uvicorn está activo ocupando el puerto 81
        if "192.168.4.1" in self.stream_url:
            fallback_url = "http://localhost:8000/video_feed"
            print(f"[-] Puerto 81 ocupado o no responde. Probando fallback: {fallback_url}")
            if self.cap:
                self.cap.release()
            self.cap = cv2.VideoCapture(fallback_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            t_fallback = time.time()
            while (time.time() - t_fallback) < 3.0:
                if self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        h, w = frame.shape[:2]
                        print(f"[+] Conectado a fallback local: {fallback_url} ({w}x{h})")
                        self.stream_url = fallback_url
                        return True
                time.sleep(0.2)

        print("[!] ERROR: No fue posible abrir el flujo de video.")
        return False

    def capture_sign_session(
        self,
        target_sign: str,
        duration_sec: float = 2.0
    ) -> Dict[str, Any]:
        """
        Captura frames durante duration_sec (~30-60 frames),
        calcula predicciones crudas y estables, estadísticas de puntajes y diagnósticos.
        """
        self.classifier.reset()
        samples: List[Dict[str, Any]] = []

        t_start = time.time()
        fps_count = 0

        while (time.time() - t_start) < duration_sec:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            fps_count += 1
            t_frame = time.time()

            # Procesar con MediaPipe
            landmarks_res = self.vision.process_frame(frame)
            if not landmarks_res or not landmarks_res.get("detected"):
                samples.append({
                    "has_hand": False,
                    "raw_pred": None,
                    "stable_pred": None,
                    "scores": {s: 0.0 for s in ["A", "B", "C", "L", "Y"]},
                    "diagnostics": {}
                })
                continue

            # Evaluar con clasificador automático
            fused_state = {
                "vision_present": True,
                "raw_landmarks": landmarks_res.get("raw_landmarks", []),
                "handedness": landmarks_res.get("handedness", "Right"),
                "timestamp": t_frame
            }

            clf_res = self.classifier.classify(fused_state)

            samples.append({
                "has_hand": True,
                "raw_pred": clf_res.get("predicted_sign"),
                "stable_pred": clf_res.get("stable_sign"),
                "scores": clf_res.get("candidate_scores", {}),
                "diagnostics": clf_res.get("diagnostics", {})
            })

            # Ritmo de captura ~25-30 FPS
            time.sleep(0.01)

        # Calcular métricas y estadísticas agregadas
        valid_samples = [s for s in samples if s["has_hand"]]
        n_total = len(samples)
        n_valid = len(valid_samples)

        score_stats: Dict[str, Dict[str, float]] = {}
        for s in ["A", "B", "C", "L", "Y"]:
            vals = [spl["scores"].get(s, 0.0) for spl in valid_samples] if valid_samples else [0.0]
            mean_v = sum(vals) / len(vals) if vals else 0.0
            std_v = math.sqrt(sum((v - mean_v)**2 for v in vals) / len(vals)) if len(vals) > 1 else 0.0
            score_stats[s] = {"mean": round(mean_v, 3), "std": round(std_v, 3)}

        # Diagnósticos promedio
        b_folds = [spl["diagnostics"].get("b", {}).get("thumb_fold", 0.0) for spl in valid_samples]
        b_adds = [spl["diagnostics"].get("b", {}).get("adduction", 0.0) for spl in valid_samples]
        c_curvs = [spl["diagnostics"].get("c", {}).get("curvature", 0.0) for spl in valid_samples]
        c_opens = [spl["diagnostics"].get("c", {}).get("opening", 0.0) for spl in valid_samples]
        y_ths = [spl["diagnostics"].get("y", {}).get("thumb", 0.0) for spl in valid_samples]
        y_pks = [spl["diagnostics"].get("y", {}).get("pinky", 0.0) for spl in valid_samples]
        y_cflxs = [spl["diagnostics"].get("y", {}).get("center_flex", 0.0) for spl in valid_samples]

        def avg(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0.0

        # Exactitud de predicción
        correct_raw = sum(1 for spl in valid_samples if spl["raw_pred"] == target_sign)
        correct_stable = sum(1 for spl in valid_samples if spl["stable_pred"] == target_sign)

        pct_raw = round((correct_raw / n_valid * 100.0), 1) if n_valid > 0 else 0.0
        pct_stable = round((correct_stable / n_valid * 100.0), 1) if n_valid > 0 else 0.0

        # Conteo de confusiones
        confusions: Dict[str, int] = {}
        for spl in valid_samples:
            pred = spl["stable_pred"] or spl["raw_pred"]
            if pred and pred != target_sign:
                confusions[pred] = confusions.get(pred, 0) + 1

        return {
            "target": target_sign,
            "total_frames": n_total,
            "valid_frames": n_valid,
            "fps": round(fps_count / duration_sec, 1),
            "score_stats": score_stats,
            "pct_raw": pct_raw,
            "pct_stable": pct_stable,
            "confusions": confusions,
            "diagnostics": {
                "b_thumb_fold": avg(b_folds),
                "b_adduction": avg(b_adds),
                "c_curvature": avg(c_curvs),
                "c_opening": avg(c_opens),
                "y_thumb": avg(y_ths),
                "y_pinky": avg(y_pks),
                "y_center_flex": avg(y_cflxs),
            }
        }

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None


def run_full_calibration(interactive: bool = False, stream_url: str = "http://192.168.4.1:81/stream"):
    print("=" * 70)
    print("  CALIBRACIÓN DE ALTA PRECISIÓN LSM — INDIVISA INGENIUM 2026")
    print("  Evaluación Canónica y de Confusiones en Cámara Real (640x480)")
    print("=" * 70)

    calib = RealSignCalibrator(stream_url=stream_url)
    if not calib.connect_camera():
        print("[!] No se pudo conectar a la cámara. Abortando.")
        return False

    signs = ["A", "B", "C", "L", "Y"]
    results: Dict[str, Any] = {}

    print("\n--- FASE 1: EVALUACIÓN DE SEÑAS CANÓNICAS ---")
    for s in signs:
        print(f"\n>>> SEÑA OBJETIVO: [{s}]")
        if interactive:
            input(f"Coloca tu mano mostrando la seña '{s}' y presiona ENTER para capturar 2 segundos...")
        else:
            print(f"Preparando captura para '{s}' en 2 segundos...")
            time.sleep(1.5)

        print(f"[*] Capturando seña '{s}' ...")
        res = calib.capture_sign_session(s, duration_sec=2.2)
        results[s] = res

        print(f"\nResultados para seña [{s}]:")
        print(f"  Frames analizados: {res['valid_frames']} / {res['total_frames']} ({res['fps']} FPS)")
        print(f"  Precisión Raw:    {res['pct_raw']}%")
        print(f"  Precisión Stable: {res['pct_stable']}%")
        print("  Puntajes promedio de candidatos:")
        for cand, stats in res["score_stats"].items():
            print(f"    {cand}: {stats['mean']:.3f} (±{stats['std']:.3f})")

        diag = res["diagnostics"]
        if s == "B":
            print(f"  Diagnóstico B: thumb_fold={diag['b_thumb_fold']}%, adduction={diag['b_adduction']}%")
        elif s == "C":
            print(f"  Diagnóstico C: curvature={diag['c_curvature']}%, opening={diag['c_opening']}%")
        elif s == "Y":
            print(f"  Diagnóstico Y: thumb={diag['y_thumb']}%, pinky={diag['y_pinky']}%, center_flex={diag['y_center_flex']}%")

        if res["confusions"]:
            print(f"  [!] Confusiones observadas: {res['confusions']}")
        else:
            print("  [+] Sin confusiones espurias.")

    print("\n--- FASE 2: PRUEBAS DE CONFUSIÓN Y RECHAZO ---")
    confusion_tests = [
        ("B -> Mano Abierta (dedos separados)", "REJECT_OPEN_B", "B"),
        ("C -> Mano Abierta (dedos rectos)", "REJECT_OPEN_C", "C"),
        ("C -> Puño cerrado (dedos en palma)", "REJECT_FIST_C", "C"),
        ("Y -> Mano Abierta (dedos extendidos)", "REJECT_OPEN_Y", "Y"),
        ("Y -> Seña L (índice erguido, meñique doblado)", "REJECT_L_AS_Y", "Y")
    ]

    confusion_results: List[Dict[str, Any]] = []

    for desc, code, target in confusion_tests:
        print(f"\n>>> PRUEBA DE RECHAZO: {desc}")
        if interactive:
            input(f"Muestra la postura errónea deliberada [{desc}] y presiona ENTER...")
        else:
            print(f"Preparando captura de postura [{desc}] en 1.5 s...")
            time.sleep(1.2)

        res_conf = calib.capture_sign_session(target, duration_sec=1.8)
        # Éxito significa que NO se reconoció erróneamente la seña objetivo (score bajo o rechazado)
        falsely_accepted = res_conf["pct_stable"] >= 50.0 or res_conf["pct_raw"] >= 50.0
        rejection_passed = not falsely_accepted

        confusion_results.append({
            "desc": desc,
            "target": target,
            "score_mean": res_conf["score_stats"].get(target, {}).get("mean", 0.0),
            "rejection_passed": rejection_passed,
            "pred_raw": res_conf["pct_raw"],
            "pred_stable": res_conf["pct_stable"]
        })

        status_str = "[PASS - RECHAZADO]" if rejection_passed else "[FAIL - FALSO POSITIVO]"
        print(f"  Veredicto: {status_str} (Puntaje asignado a {target}: {res_conf['score_stats'].get(target, {}).get('mean', 0.0):.2f})")

    calib.close()

    # Generar Reporte de Salida
    print("\n" + "=" * 70)
    print("  RESUMEN DE CALIBRACIÓN DE PRECISIÓN")
    print("=" * 70)
    for s, r in results.items():
        pass_qual = "PASS" if r["pct_stable"] >= 80.0 else "MARGINAL"
        print(f"  Letra {s}: {r['pct_stable']}% estable | Score promedio={r['score_stats'][s]['mean']:.2f} | [{pass_qual}]")

    print("\nPruebas de Rechazo de Confusión:")
    for cr in confusion_results:
        st = "PASS (Rechazado)" if cr["rejection_passed"] else "FAIL (Aceptado erróneamente)"
        print(f"  {cr['desc']}: {st} [Score: {cr['score_mean']:.2f}]")

    return results, confusion_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrador de Precisión LSM Nivel 1")
    parser.add_argument("--url", default="http://192.168.4.1:81/stream", help="URL del stream MJPEG")
    parser.add_argument("--interactive", action="store_true", help="Modo interactivo manual por consola")
    args = parser.parse_args()

    run_full_calibration(interactive=args.interactive, stream_url=args.url)
