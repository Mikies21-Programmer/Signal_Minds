"""
Servidor de API Local y WebSockets para INDIVISA INGENIUM 2026.
Provee streaming de video MJPEG, telemetría WebSocket en tiempo real,
control de señas vía teclado/HTTP y diagnóstico de salud del sistema.
"""

import asyncio
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config_loader import ConfigLoader
from .orchestrator import SystemOrchestrator
from .logger import get_logger

logger = get_logger("api")

# Directorio de plantillas y estáticos
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"


def create_app(orchestrator: Optional[SystemOrchestrator] = None) -> FastAPI:
    config_loader = ConfigLoader()
    app_orchestrator = orchestrator or SystemOrchestrator(config_loader)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Iniciando servicios de API y orquestador central...")
        app_orchestrator.start(auto_loop=True)
        yield
        logger.info("Deteniendo servicios de API y orquestador...")
        app_orchestrator.stop()

    app = FastAPI(
        title="INDIVISA INGENIUM 2026 — LSM Telemetry API",
        version=config_loader.get_app_version(),
        description="API y Streaming de Visión y Mecatrónica para Evaluación de Lengua de Señas Mexicana",
        lifespan=lifespan
    )

    @app.get("/", response_class=HTMLResponse)
    async def get_index():
        """Sirve la interfaz web visual para la Laptop."""
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(
            content="<h1>INDIVISA INGENIUM 2026</h1><p>Interfaz web no encontrada en static/index.html.</p>"
        )

    @app.get("/api/health")
    async def get_health():
        """Reporta diagnóstico de salud del sistema y subsistemas."""
        return app_orchestrator.health_checker.run_full_check()

    @app.get("/api/status")
    async def get_status():
        """Retorna la última muestra de telemetría y estado."""
        return app_orchestrator.get_latest_payload()

    @app.post("/api/sign/{sign}")
    async def set_target_sign(sign: str):
        """Actualiza la seña objetivo evaluada (A, B, C, L, Y) en modo manual."""
        clean_sign = sign.strip().upper()
        allowed = ["A", "B", "C", "L", "Y", "J", "Ñ", "Q", "X", "Z"]
        if clean_sign not in allowed:
            raise HTTPException(status_code=400, detail=f"Seña no válida. Permitidas: {allowed}")

        app_orchestrator.set_target_sign(clean_sign, switch_to_manual=True)
        return {"status": "SUCCESS", "target_sign": clean_sign, "mode": app_orchestrator.mode}

    @app.post("/api/mode/{mode}")
    async def set_mode(mode: str):
        """Cambia el modo de operación entre 'AUTO' (clasificación automática) y 'MANUAL'."""
        clean_mode = mode.strip().upper()
        if clean_mode not in ["AUTO", "MANUAL"]:
            raise HTTPException(status_code=400, detail="Modo no válido. Use 'AUTO' o 'MANUAL'.")
        app_orchestrator.set_mode(clean_mode)
        return {"status": "SUCCESS", "mode": clean_mode}

    @app.post("/api/pause")
    async def toggle_pause():
        """Pausa o reanuda la evaluación."""
        is_paused = app_orchestrator.toggle_pause()
        return {"status": "SUCCESS", "is_paused": is_paused}

    @app.post("/api/recalibrate")
    async def recalibrate():
        """Ejecuta calibración de sensores."""
        res = app_orchestrator.recalibrate_sensors()
        return {"status": "SUCCESS", "result": res}

    @app.get("/video_feed")
    def video_feed():
        """Flujo de video continuo MJPEG con HUD y landmarks superpuestos."""
        def frame_generator():
            while True:
                jpeg_bytes = app_orchestrator.get_latest_jpeg()
                if jpeg_bytes:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
                    )
                time.sleep(0.04)  # ~25 FPS

        return StreamingResponse(
            frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        """Canal dúplex de telemetría y comandos de teclado en tiempo real."""
        await websocket.accept()
        logger.info("Cliente WebSocket conectado a telemetría.")

        try:
            while True:
                # Comprobar si el cliente envió comandos (no bloqueante)
                try:
                    raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.04)
                    data = json.loads(raw_msg)
                    action = data.get("action", "")

                    if action == "SET_SIGN":
                        new_sign = data.get("sign", "A").upper()
                        if new_sign in ["A", "B", "C", "L", "Y", "J", "Ñ", "Q", "X", "Z"]:
                            app_orchestrator.set_target_sign(new_sign, switch_to_manual=True)
                    elif action == "SET_MODE":
                        new_mode = data.get("mode", "AUTO").upper()
                        app_orchestrator.set_mode(new_mode)
                    elif action == "TOGGLE_PAUSE":
                        app_orchestrator.toggle_pause()
                    elif action == "RECALIBRATE":
                        app_orchestrator.recalibrate_sensors()
                    elif action == "NEXT_SIGN":
                        current = app_orchestrator.target_sign
                        signs = ["A", "B", "C", "L", "Y", "J", "Ñ", "Q", "X", "Z"]
                        idx = signs.index(current) if current in signs else -1
                        next_sign = signs[(idx + 1) % len(signs)]
                        app_orchestrator.set_target_sign(next_sign, switch_to_manual=True)

                except asyncio.TimeoutError:
                    pass
                except json.JSONDecodeError:
                    pass

                # Enviar payload más reciente
                payload = app_orchestrator.get_latest_payload()
                if payload:
                    await websocket.send_json(payload)

        except WebSocketDisconnect:
            logger.info("Cliente WebSocket desconectado.")
        except Exception as e:
            logger.error(f"Error en websocket_telemetry: {e}")

    return app


# Instancia por defecto para ejecutores ASGI (uvicorn src.backend.api:app)
app = create_app()

if __name__ == "__main__":
    import uvicorn
    cfg = ConfigLoader()
    api_cfg = cfg.get("api", {})
    host = api_cfg.get("host", "0.0.0.0")
    port = api_cfg.get("port", 8000)
    uvicorn.run("src.backend.api:app", host=host, port=port, reload=False)
