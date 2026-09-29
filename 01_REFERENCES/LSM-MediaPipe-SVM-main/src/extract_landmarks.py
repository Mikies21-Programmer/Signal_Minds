import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import os
import glob
from tqdm import tqdm

# ============================================================
# 1. Inicializar MediaPipe Hands (NUEVA API)
# ============================================================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=1,
    min_detection_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

def extract_landmarks(image_path):
    """
    Extrae los 21 landmarks de una imagen.
    Retorna un vector de 63 características (21 * 3) o None si no detecta mano.
    """
    image = cv2.imread(image_path)
    if image is None:
        return None
    
    # Convertir a RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)
    
    if not results.multi_hand_landmarks:
        return None
    
    # Obtener la primera mano detectada
    landmarks = results.multi_hand_landmarks[0]
    feature_vector = []
    for lm in landmarks.landmark:
        feature_vector.extend([lm.x, lm.y, lm.z])
    
    return np.array(feature_vector)


# ============================================================
# 2. Recorrer todas las imágenes del dataset
# ============================================================
dataset_root = "MSL-ABC"

# Buscar TODOS los archivos .jpg y .png en cualquier subcarpeta
image_paths = glob.glob(os.path.join(dataset_root, "**", "*.jpg"), recursive=True)
image_paths += glob.glob(os.path.join(dataset_root, "**", "*.png"), recursive=True)

print(f"📸 Total de imágenes encontradas: {len(image_paths)}")

# Listas para almacenar datos
data = []
labels = []

# Procesar cada imagen con barra de progreso
for img_path in tqdm(image_paths, desc="🖐️ Extrayendo landmarks"):
    # Inferir la etiqueta (letra) del nombre de la carpeta contenedora
    label = os.path.basename(os.path.dirname(img_path))
    
    features = extract_landmarks(img_path)
    if features is not None:
        data.append(features)
        labels.append(label)

# ============================================================
# 3. Guardar en archivo CSV
# ============================================================
df = pd.DataFrame(data)
df['label'] = labels
df.to_csv('landmarks_dataset.csv', index=False)

print(f"✅ ¡Listo! Se procesaron {len(df)} imágenes.")
print(f"📁 Archivo guardado como: landmarks_dataset.csv")
print(f"📊 Dimensiones: {df.shape[0]} muestras × {df.shape[1]} columnas")