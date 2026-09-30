"""
Script de monitoreo y validación End-to-End para Fase 3.
Conecta a WebSocket /ws/telemetry y valida en vivo:
1. Cámara real streaming 640x480
2. IMU MPU6050 conectado por COM7 reportando Roll/Pitch/Tilt
3. Fusión sensorial (valid_fusion)
4. MediaPipe Hand Landmarker
5. Evaluación multimodal estricta
"""

import sys
import time
import json
import asyncio
import websockets

async def main(samples=15):
    uri = "ws://localhost:8000/ws/telemetry"
    print(f"[*] Conectando a {uri}...")
    async with websockets.connect(uri) as ws:
        print("[*] WebSocket conectado exitosamente. Recibiendo muestras...")
        for i in range(1, samples + 1):
            raw = await ws.recv()
            data = json.loads(raw)
            fid = data.get("frame_id")
            cam_fps = data.get("camera_fps", 0.0)
            latency = data.get("pipeline_latency_ms", 0.0)
            has_hand = data.get("has_hand", False)
            fusion = data.get("fusion", {})
            sens = data.get("sensor_telemetry", {})
            ev = data.get("evaluation", {})
            fb = data.get("feedback", {})
            auto = data.get("auto_classification", {})
            orient_param = ev.get("parameters", {}).get("orientation", {})

            roll = sens.get("imu_roll_deg", 0.0)
            pitch = sens.get("imu_pitch_deg", 0.0)
            tilt = sens.get("tilt_error_deg", 0.0)
            is_conn = sens.get("is_connected", False)
            v_fusion = fusion.get("valid_fusion", False)
            o_state = orient_param.get("orientation_state", "N/A")
            is_valid = ev.get("is_valid", False)
            msg = ev.get("message", "")
            pri_msg = fb.get("primary_message", "")

            print(
                f"[{i:02d}] Frame {fid:05d} | FPS={cam_fps:.1f} Lat={latency:.1f}ms | "
                f"Mano={has_hand} | IMU_conn={is_conn} | "
                f"R={roll:6.2f}° P={pitch:6.2f}° TILT={tilt:5.2f}° | "
                f"FUSIÓN={v_fusion} | ORIENT={o_state} | "
                f"VALID={is_valid} | MSG='{msg}'"
            )
            await asyncio.sleep(0.05)

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    asyncio.run(main(count))
