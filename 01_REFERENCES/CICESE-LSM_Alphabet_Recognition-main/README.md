# LSM Alphabet Recognition

Exploración y experimentación para el reconocimiento del abecedario de la **Lengua de Señas Mexicana (LSM)** usando keypoints extraídos con MediaPipe y modelos de clasificación clásicos y de deep learning.

Trabajo realizado durante una estancia de investigación en el **Centro de Investigación Científica y de Educación Superior de Ensenada (CICESE)**, bajo la supervisión del **Dr. Irvin Hussein López Nava**.

---

## Contexto

El proyecto toma como referencia dos trabajos:

- La tesis de **Ricardo Fernando Morfin Chávez**: *"Reconocimiento continuo de la lengua de señas mexicanas"*
- El paper: *"Dynamic Strategy for Recognizing the Mexican Sign Language Alphabet: Bringing Static and Dynamic Signs"*

El objetivo principal fue explorar distintas estrategias para clasificar tanto letras **estáticas** (posición fija de la mano) como **dinámicas** (letras que requieren movimiento, como la J o la Z).

---

## Dataset

- **MSL-ABC** — Imágenes y videos del abecedario LSM
- **MSL-dynamic-signs** — Videos de señas dinámicas

---

## Estructura del proyecto

```
lsm-alphabet-recognition/
├── LSM.ipynb                      # EDA del dataset, keypoints en tiempo real, clasificación de letras estáticas
├── SVM_POOLING_CONTINUOS.ipynb    # SVM con técnica de pooling estadístico para señas dinámicas y continuas
├── SVM_STACKING_SETTING_UP.ipynb  # SVM con stacking + padding, reconstrucción del paper de Morfin Chávez
└── CNN.ipynb                      # Experimento inicial de arquitectura CNN con tensores Frames × Coords × Keypoints
```

---

## Metodología

### Extracción de keypoints
Se utilizó **MediaPipe Hands** para extraer 21 keypoints por mano (coordenadas X, Y), generando vectores de características por frame.

### Letras estáticas
Clasificación frame a frame con SVM sobre los keypoints normalizados.

### Letras dinámicas
Se exploraron dos estrategias para manejar la dimensión temporal:

- **Pooling estadístico** — Se extraen estadísticas (media, desviación estándar, etc.) de los keypoints a lo largo de los frames del video, generando un vector fijo independiente de la duración.
- **Stacking + Padding** — Se apilan los frames en secuencias de longitud fija (T = 2, 5, 10, 30 frames), rellenando con padding cuando es necesario.

### CNN (experimental)
Arquitectura basada en tensores `Frames × Coordenadas × Keypoints` para capturar la dimensión temporal de forma explícita.

---

## Stack tecnológico

- Python 3
- MediaPipe
- OpenCV
- scikit-learn
- TensorFlow / Keras
- NumPy, Pandas, Matplotlib, Seaborn

---

## Notas

- Este repositorio forma parte de `Proyectos_CICESE`, un conjunto de trabajos realizados durante la estancia. El código y los experimentos aquí presentes fueron desarrollados por mí como parte de la investigación, pero el contexto académico y los datasets pertenecen al laboratorio.
- Los datasets **no están incluidos** en el repositorio por su tamaño. Contactar al laboratorio de CICESE para acceso.
