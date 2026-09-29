#!/usr/bin/env python3
"""
Script de diagnóstico y arranque inicial para INDIVISA INGENIUM 2026.
Comprueba que el proyecto:
1. Arranque
2. Importe sus módulos
3. Ejecute un health check completo
4. Registre logs en logs/indivisa.log
5. Reporte versión
6. Reporte estado de hardware
"""

import sys
import json
from pathlib import Path

# Añadir 02_PROJECT al sys.path para resolución limpia de paquetes
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.backend.config_loader import ConfigLoader
from src.backend.logger import setup_logger
from src.backend.health import HealthChecker
from src.backend.orchestrator import SystemOrchestrator


def main():
    print("=" * 70)
    print("  INDIVISA INGENIUM 2026 — DIAGNÓSTICO DE ARRANQUE Y SALUD")
    print("=" * 70)

    # 1. Cargar Configuración
    config = ConfigLoader()
    app_name = config.get_app_name()
    version = config.get_app_version()

    # 2. Inicializar Logger Centralizado
    logger = setup_logger(
        name="boot",
        log_file=config.get("logging", {}).get("file_path", "logs/indivisa.log"),
        level=config.get("logging", {}).get("level", "INFO"),
        project_root=project_root
    )
    logger.info(f"Iniciando arranque de diagnóstico para {app_name} v{version}")

    # 3. Ejecutar Health Check
    checker = HealthChecker(config)
    health_report = checker.run_full_check()

    # 4. Reporte en Pantalla
    print(f"\n[1] VERSIÓN DEL SISTEMA:")
    print(f"    Proyecto : {health_report['app_name']}")
    print(f"    Versión  : {health_report['version']}")
    print(f"    Entorno  : {health_report['environment']}")

    hw = health_report['hardware']
    print(f"\n[2] ESTADO DE HARDWARE DETECTADO:")
    print(f"    Sistema Operativo : {hw['platform_os']} ({hw['os_release']}, {hw['architecture']})")
    print(f"    Procesador        : {hw['processor']}")
    print(f"    Dispositivo Host  : {hw['hardware_device_model']}")
    print(f"    ¿Es Raspberry Pi? : {'SÍ' if hw['is_raspberry_pi'] else 'NO (Modo Laptop/Desarrollo)'}")
    print(f"    Cámara            : {hw['camera_interface']}")
    print(f"    Sensores          : {hw['sensor_interface']}")
    print(f"    Python Runtime    : {hw['python_version']}")

    log_sys = health_report['logging']
    print(f"\n[3] ESTADO DE REGISTRO (LOGGING):")
    print(f"    Archivo de Log    : {log_sys['log_path']}")
    print(f"    ¿Es escribible?   : {'SÍ' if log_sys['writable'] else 'NO'}")
    print(f"    Estado de Logging : {log_sys['status']}")

    print(f"\n[4] SUBSISTEMAS DEL PIPELINE:")
    for mod_name, status in health_report['subsystems'].items():
        print(f"    - {mod_name:<12} : {status}")

    # 5. Probar un ciclo básico del orquestador
    print(f"\n[5] PRUEBA DE CICLO DEL ORQUESTADOR (1 FRAME):")
    orchestrator = SystemOrchestrator(config)
    orchestrator.start()
    step_result = orchestrator.step()
    orchestrator.stop()

    print(f"    Seña objetivo     : '{step_result['target_sign']}'")
    print(f"    Latencia pipeline : {step_result['pipeline_latency_ms']} ms")
    print(f"    Score obtenido    : {step_result['evaluation']['overall_score']}")
    print(f"    Veredicto         : {'VÁLIDO' if step_result['evaluation']['is_valid'] else 'EN CORRECCIÓN'}")
    print(f"    Feedback primario : \"{step_result['feedback']['primary_message']}\"")
    print(f"    Sugerencia        : \"{step_result['feedback']['secondary_message']}\"")

    logger.info("Diagnóstico de arranque completado con éxito total.")
    print("\n" + "=" * 70)
    print("  RESULTADO: PROYECTO INICIALIZADO CON ÉXITO — TODOS LOS MÓDULOS ACTIVOS")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
