"""
TESIS LSM + ROBOT - SISTEMA COMPLETO CON MOVIMIENTO LENTO
Modelo: SVM RBF (99.77%)
Autor: Juan Juárez Fuentes (AL12514850)
"""

import cv2
import numpy as np
import mediapipe as mp
import joblib
import time
from collections import deque, Counter
from sklearn.preprocessing import LabelEncoder

# ===================================================================
# CONFIGURACIÓN INICIAL
# ===================================================================
print("="*70)
print("🧪 TESIS LSM + ROBOT - SISTEMA DE RECONOCIMIENTO EN TIEMPO REAL")
print("="*70)
print(f"📅 {time.strftime('%d de %B de %Y')}")
print(f"👤 Juan Juárez Fuentes (AL12514850)")
print("="*70)

# ===================================================================
# 1. CARGA DE MODELOS
# ===================================================================
print("\n📂 Cargando modelos...")

try:
    modelo = joblib.load('modelo_rbf.pkl')
    scaler = joblib.load('scaler.pkl')
    
    print(f"✅ Modelo SVM RBF cargado")
    print(f"   Clases: {len(modelo.classes_)} letras")
    print(f"   Precisión reportada: 99.77%")
    
    label_encoder = LabelEncoder()
    label_encoder.classes_ = modelo.classes_

except FileNotFoundError as e:
    print(f"❌ Error: {e.filename} no encontrado")
    print("   Asegúrate de que los archivos están en el directorio actual")
    exit(1)

# ===================================================================
# 2. MAPEO LETRAS → COMANDOS
# ===================================================================
MAPEO_COMANDOS = {
    'A': 'AVANZAR', 
    'B': 'RETROCEDER', 
    'C': 'GIRAR_IZQUIERDA', 
    'D': 'GIRAR_DERECHA',
    'E': 'DETENER', 
    'F': 'SUBIR', 
    'G': 'BAJAR',
    'H': 'ABRIR_PINZA', 
    'I': 'CERRAR_PINZA',
    'L': 'LUZ_ON', 
    'M': 'LUZ_OFF',
    'R': 'VELOCIDAD_ALTA', 
    'S': 'VELOCIDAD_MEDIA', 
    'T': 'VELOCIDAD_BAJA',
    'U': 'MODO_AUTOMATICO', 
    'V': 'MODO_MANUAL',
    'N': 'MOVER_ARRIBA', 
    'O': 'MOVER_ABAJO',
    'P': 'MOVER_ADELANTE', 
    'W': 'ALARMA_ON', 
    'Y': 'RESET_SISTEMA'
}

# Estado del robot para simulación
POSICION_ROBOT = {
    'x': 0.0, 'y': 0.0,      # Posición (flotantes para movimiento suave)
    'pinza': False,           # False=abierta, True=cerrada
    'velocidad': 1,           # 1=baja, 2=media, 3=alta
    'luz': False,
    'velocidad_actual': 0.0   # Para suavizado
}

# ===================================================================
# 3. CONFIGURACIÓN MEDIAPIPE
# ===================================================================
print("\n📷 Configurando MediaPipe...")

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

print("✅ MediaPipe configurado")

# ===================================================================
# 4. PARÁMETROS
# ===================================================================
HISTORIAL_LEN = 5
CONFIANZA_MINIMA = 3

historial = deque(maxlen=HISTORIAL_LEN)
fps_mediciones = deque(maxlen=30)

ultima_letra = None

# 🐢 CONFIGURACIÓN DE VELOCIDAD LENTA
PASO_BASE = 0.08  # ← Más lento (0.08 = muy suave)
ACELERACION = 0.02
FRICCION = 0.92

# ===================================================================
# 5. FUNCIONES
# ===================================================================

def extraer_landmarks(hand_landmarks):
    landmarks = []
    for lm in hand_landmarks.landmark:
        landmarks.extend([lm.x, lm.y, lm.z])
    return np.array(landmarks).reshape(1, -1)

def predecir_letra(landmarks):
    try:
        landmarks_scaled = scaler.transform(landmarks)
        prediccion = modelo.predict(landmarks_scaled)
        
        if isinstance(prediccion[0], (int, np.integer)):
            pred_idx = int(prediccion[0])
            letra = modelo.classes_[pred_idx]
        else:
            letra = str(prediccion[0])
            if letra not in modelo.classes_:
                return None
        
        historial.append(letra)
        conteo = Counter(historial)
        letra_final = conteo.most_common(1)[0][0]
        
        if conteo[letra_final] >= CONFIANZA_MINIMA:
            return letra_final
        return None
    except:
        return None

def simular_robot(comando):
    """
    Simula el movimiento del robot con velocidad lenta y suave
    """
    global POSICION_ROBOT
    
    # Obtener velocidad según configuración
    velocidad_max = {
        1: 0.08,  # Baja (muy lento)
        2: 0.15,  # Media
        3: 0.30   # Alta
    }
    
    max_paso = velocidad_max.get(POSICION_ROBOT['velocidad'], 0.08)
    direccion = 0
    
    # Determinar dirección del movimiento
    if comando == 'AVANZAR':
        direccion = 1  # Arriba (Y negativo)
        POSICION_ROBOT['direccion'] = 'arriba'
    elif comando == 'RETROCEDER':
        direccion = 2  # Abajo (Y positivo)
        POSICION_ROBOT['direccion'] = 'abajo'
    elif comando == 'GIRAR_IZQUIERDA':
        direccion = 3  # Izquierda (X negativo)
        POSICION_ROBOT['direccion'] = 'izquierda'
    elif comando == 'GIRAR_DERECHA':
        direccion = 4  # Derecha (X positivo)
        POSICION_ROBOT['direccion'] = 'derecha'
    elif comando == 'SUBIR':
        direccion = 1
        max_paso *= 1.5
        POSICION_ROBOT['direccion'] = 'arriba'
    elif comando == 'BAJAR':
        direccion = 2
        max_paso *= 1.5
        POSICION_ROBOT['direccion'] = 'abajo'
    elif comando == 'ABRIR_PINZA':
        POSICION_ROBOT['pinza'] = False
        print("🔓 Pinza: ABIERTA")
        return
    elif comando == 'CERRAR_PINZA':
        POSICION_ROBOT['pinza'] = True
        print("🔒 Pinza: CERRADA")
        return
    elif comando == 'VELOCIDAD_ALTA':
        POSICION_ROBOT['velocidad'] = 3
        print("⚡ Velocidad: ALTA")
        return
    elif comando == 'VELOCIDAD_MEDIA':
        POSICION_ROBOT['velocidad'] = 2
        print("⚡ Velocidad: MEDIA")
        return
    elif comando == 'VELOCIDAD_BAJA':
        POSICION_ROBOT['velocidad'] = 1
        print("⚡ Velocidad: BAJA")
        return
    elif comando == 'LUZ_ON':
        POSICION_ROBOT['luz'] = True
        print("💡 Luz: ON")
        return
    elif comando == 'LUZ_OFF':
        POSICION_ROBOT['luz'] = False
        print("💡 Luz: OFF")
        return
    elif comando == 'DETENER':
        # Frenar suavemente
        POSICION_ROBOT['velocidad_actual'] *= 0.8
        print("⏹️ DETENER")
        return
    
    # Si no hay comando de movimiento, aplicar fricción
    if direccion == 0:
        POSICION_ROBOT['velocidad_actual'] *= FRICCION
        return
    
    # Aceleración suave
    if abs(POSICION_ROBOT['velocidad_actual']) < max_paso:
        POSICION_ROBOT['velocidad_actual'] += ACELERACION
    POSICION_ROBOT['velocidad_actual'] = min(POSICION_ROBOT['velocidad_actual'], max_paso)
    
    # Aplicar movimiento
    paso = POSICION_ROBOT['velocidad_actual']
    
    if direccion == 1:  # Arriba
        POSICION_ROBOT['y'] -= paso
        print(f"⬆️ AVANZAR → ({POSICION_ROBOT['x']:.2f}, {POSICION_ROBOT['y']:.2f})")
    elif direccion == 2:  # Abajo
        POSICION_ROBOT['y'] += paso
        print(f"⬇️ RETROCEDER → ({POSICION_ROBOT['x']:.2f}, {POSICION_ROBOT['y']:.2f})")
    elif direccion == 3:  # Izquierda
        POSICION_ROBOT['x'] -= paso
        print(f"⬅️ GIRAR IZQ → ({POSICION_ROBOT['x']:.2f}, {POSICION_ROBOT['y']:.2f})")
    elif direccion == 4:  # Derecha
        POSICION_ROBOT['x'] += paso
        print(f"➡️ GIRAR DER → ({POSICION_ROBOT['x']:.2f}, {POSICION_ROBOT['y']:.2f})")
    
    # Limitar posición
    POSICION_ROBOT['x'] = max(-5.0, min(5.0, POSICION_ROBOT['x']))
    POSICION_ROBOT['y'] = max(-5.0, min(5.0, POSICION_ROBOT['y']))

def dibujar_interfaz(frame, letra, comando, fps, tiempo_pred):
    h, w, _ = frame.shape
    
    # Panel superior
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (w-10, 220), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
    
    # FPS y tiempo
    cv2.putText(frame, f"FPS: {fps:.1f}", (w-180, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Pred: {tiempo_pred:.2f}ms", (w-180, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)
    
    # Letra
    if letra:
        cv2.putText(frame, f"LETRA: {letra}", (30, 55), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 255), 4)
    else:
        cv2.putText(frame, "ESPERANDO MANO...", (30, 55), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 100, 100), 2)
    
    # Comando
    if comando:
        cv2.putText(frame, f"COMANDO: {comando}", (30, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    else:
        cv2.putText(frame, "SIN COMANDO", (30, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 100, 100), 2)
    
    # Estado del robot
    estado = f"Pos: ({POSICION_ROBOT['x']:.1f},{POSICION_ROBOT['y']:.1f})"
    estado += f"  Pinza: {'CERRADA' if POSICION_ROBOT['pinza'] else 'ABIERTA'}"
    estado += f"  Vel: {POSICION_ROBOT['velocidad']}"
    estado += f"  Luz: {'ON' if POSICION_ROBOT['luz'] else 'OFF'}"
    estado += f"  Mov: {POSICION_ROBOT['velocidad_actual']:.2f}"
    
    cv2.putText(frame, estado, (30, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 255), 2)
    
    # Info modelo
    cv2.putText(frame, f"Modelo: SVM RBF (99.77%) | Clases: {len(modelo.classes_)}", 
                (30, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    cv2.putText(frame, "q=Salir  s=Guardar  r=Reiniciar  t=Toggle sim", 
                (30, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    return frame

def dibujar_simulacion(frame):
    h, w, _ = frame.shape
    
    sim_x = w - 250
    sim_y = h - 250
    sim_w = 230
    sim_h = 230
    
    cv2.rectangle(frame, (sim_x, sim_y), (sim_x + sim_w, sim_y + sim_h), 
                  (50, 50, 50), -1)
    cv2.rectangle(frame, (sim_x, sim_y), (sim_x + sim_w, sim_y + sim_h), 
                  (255, 255, 255), 2)
    
    cx = sim_x + sim_w // 2
    cy = sim_y + sim_h // 2
    step = 30
    
    # Grid
    for i in range(-5, 6):
        x = cx + i * step
        cv2.line(frame, (x, sim_y + 10), (x, sim_y + sim_h - 10), 
                 (80, 80, 80), 1)
        y = cy + i * step
        cv2.line(frame, (sim_x + 10, y), (sim_x + sim_w - 10, y), 
                 (80, 80, 80), 1)
    
    # 🔧 CORREGIDO: Convertir a enteros
    rx = int(cx + POSICION_ROBOT['x'] * step)
    ry = int(cy + POSICION_ROBOT['y'] * step)
    
    # Color según pinza
    color = (0, 255, 0) if not POSICION_ROBOT['pinza'] else (0, 0, 255)
    
    # Círculo del robot con tamaño según velocidad
    radio = 12 + POSICION_ROBOT['velocidad'] * 2
    
    # Sombra (efecto de movimiento)
    if abs(POSICION_ROBOT['velocidad_actual']) > 0.01:
        cv2.circle(frame, (rx - 5, ry - 5), radio, (100, 100, 100), -1)
    
    cv2.circle(frame, (rx, ry), radio, color, -1)
    cv2.circle(frame, (rx, ry), radio, (255, 255, 255), 2)
    
    # Pinza
    if POSICION_ROBOT['pinza']:
        cv2.line(frame, (rx-10, ry-8), (rx-15, ry-15), (255, 255, 0), 2)
        cv2.line(frame, (rx+10, ry-8), (rx+15, ry-15), (255, 255, 0), 2)
    else:
        cv2.line(frame, (rx-10, ry-8), (rx-20, ry-10), (255, 255, 0), 2)
        cv2.line(frame, (rx+10, ry-8), (rx+20, ry-10), (255, 255, 0), 2)
    
    # Luz
    if POSICION_ROBOT['luz']:
        cv2.circle(frame, (rx, ry - 20), 5, (0, 255, 255), -1)
    
    # Etiquetas
    cv2.putText(frame, "SIMULACION ROBOT", (sim_x+20, sim_y+20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.putText(frame, f"V: {POSICION_ROBOT['velocidad']}", (sim_x+10, sim_y+sim_h-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (150, 150, 150), 1)
    
    return frame

# ===================================================================
# 6. FUNCIÓN PRINCIPAL
# ===================================================================
def main():
    print("\n📷 Iniciando cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n✅ SISTEMA INICIADO")
    print("="*70)
    print(f"   Modelo: SVM RBF (99.77%)")
    print(f"   Clases: {len(modelo.classes_)} letras")
    print(f"   Velocidad: LENTA (PASO={PASO_BASE})")
    print("\n🎮 CONTROLES:")
    print("   q = Salir")
    print("   s = Guardar captura")
    print("   r = Reiniciar historial")
    print("   t = Activar/desactivar simulación")
    print("="*70)
    print("👉 Haz una letra LSM frente a la cámara\n")
    print("📌 Letras disponibles:")
    print("   A=AVANZAR  B=RETROCEDER  C=GIRAR_IZQ  D=GIRAR_DER")
    print("   E=DETENER  F=SUBIR  G=BAJAR  H=ABRIR  I=CERRAR")
    print("   L=LUZ_ON  M=LUZ_OFF  R=VEL_ALTA  S=VEL_MED  T=VEL_BAJA")
    print("="*70)
    
    global historial, ultima_letra
    
    mostrar_sim = True
    
    while True:
        start_time = time.time()
        
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = hands.process(rgb)
        
        letra = None
        comando = None
        tiempo_pred = 0
        
        if resultado.multi_hand_landmarks:
            hand = resultado.multi_hand_landmarks[0]
            
            # Dibujar landmarks
            mp_draw.draw_landmarks(
                frame, hand, mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2)
            )
            
            landmarks = extraer_landmarks(hand)
            
            pred_start = time.time()
            letra = predecir_letra(landmarks)
            tiempo_pred = (time.time() - pred_start) * 1000
            
            if letra:
                comando = MAPEO_COMANDOS.get(letra, None)
                if letra != ultima_letra:
                    print(f"✅ {time.strftime('%H:%M:%S')} - Letra: {letra} → {comando}")
                    ultima_letra = letra
                
                if comando and mostrar_sim:
                    simular_robot(comando)
        
        # Calcular FPS
        fps_frame = 1.0 / (time.time() - start_time)
        fps_mediciones.append(fps_frame)
        fps = sum(fps_mediciones) / len(fps_mediciones) if fps_mediciones else 0
        
        # Dibujar interfaz
        frame = dibujar_interfaz(frame, letra, comando, fps, tiempo_pred)
        
        if mostrar_sim:
            frame = dibujar_simulacion(frame)
        
        cv2.imshow('TESIS LSM + ROBOT - SVM RBF 99.77%', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            nombre = f"captura_tesis_{timestamp}.png"
            cv2.imwrite(nombre, frame)
            print(f"📸 Captura guardada: {nombre}")
        elif key == ord('r'):
            historial.clear()
            ultima_letra = None
            print("🔄 Historial reiniciado")
        elif key == ord('t'):
            mostrar_sim = not mostrar_sim
            print(f"🔄 Simulación: {'ACTIVADA' if mostrar_sim else 'DESACTIVADA'}")
    
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    
    print("\n" + "="*70)
    print("✅ SISTEMA FINALIZADO")
    print(f"   FPS promedio: {fps:.1f}")
    print("="*70)

if __name__ == "__main__":
    main()