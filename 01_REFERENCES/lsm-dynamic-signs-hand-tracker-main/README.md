# 📌 Proyecto: Identificación de Gestos Dinámicos de la Lengua de Señas Mexicana (LSM)

**Institución:** Tecnológico de Monterrey  
**Departamento:** Departamento de Computación – Campus Monterrey  
**Equipo:** 12  

**Integrantes:**  
- Luis Ángel Seda Marcos — [A01795301@tec.mx](mailto:A01795301@tec.mx)  
- Christopher Flores González — [A01795419@tec.mx](mailto:A01795419@tec.mx)  
- Luis Felipe Nicanor Gutiérrez — [A01795631@tec.mx](mailto:A01795631@tec.mx)  

**Sponsor Académico:**  
Dr. Raúl Valente Ramírez Velarde — [rramirez@tec.mx](mailto:rramirez@tec.mx)

**Fecha:** 21/09/2025  

---

## 📖 Índice
1. [Antecedentes](#antecedentes)  
2. [Entendimiento del negocio (CRISP-ML)](#entendimiento-del-negocio-crisp-ml)  
   - [2.1 Formulación del problema](#21-formulación-del-problema)  
   - [2.2 Contexto e importancia](#22-contexto-e-importancia)  
   - [2.3 Objetivos](#23-objetivos)  
   - [2.4 Preguntas clave](#24-preguntas-clave)  
   - [2.5 Involucrados](#25-involucrados-y-tipo-de-participación)  
3. [Entendimiento de los datos (CRISP-ML)](#entendimiento-de-los-datos-crisp-ml)  
   - [3.1 Descripción de los datos](#31-descripción-de-los-datos-y-su-contexto)  
   - [3.2 Técnica de ML propuesta](#32-técnica-de-ml-propuesta)  
   - [3.3 Identificación de variables](#33-identificación-de-variables)  
   - [3.4 Métricas de éxito y criterios de calidad](#34-métricas-de-éxito-y-criterios-de-calidad)  
   - [3.5 Riesgos, supuestos y mitigación](#35-riesgos-supuestos-y-mitigación)  
4. [Convenios y aspectos éticos/legales](#convenios-y-aspectos-éticoslegales)  
5. [Bibliografía](#bibliografía)

---

## 1. Antecedentes

El **Tecnológico de Monterrey**, a través del **Departamento de Computación**, impulsa proyectos con impacto social y tecnológico.  
La **Lengua de Señas Mexicana (LSM)** es el medio de comunicación natural de la comunidad sorda en México. Sin embargo, existe una falta de herramientas tecnológicas que soporten el reconocimiento de **señas dinámicas** en tiempo real.

Durante la fase inicial, se desarrolló un sistema para la **detección de imágenes estáticas**. Esta nueva fase busca construir la base técnica para **captura, etiquetado y modelado temporal** de señas dinámicas usando visión computacional.

**Beneficios esperados:**
- Conjunto de datos etiquetado y reproducible.
- Prototipo de modelos secuenciales (LSTM/GRU/TCN/Transformers) a partir de landmarks de MediaPipe.
- Lineamientos de gobernanza de datos: privacidad, balance de clases, métricas de desempeño.

---

## 2. Entendimiento del negocio (CRISP-ML)

### 2.1 Formulación del problema
> **¿Cómo capturar y modelar la información espacio-temporal de las señas dinámicas de LSM para clasificarlas en tiempo casi real con precisión reproducible?**

### 2.2 Contexto e importancia
- **Accesibilidad:** No existen herramientas en español/LSM para comunicación en tiempo real.  
- **Impacto social:** Aumenta inclusión en trámites, educación, salud y participación pública.  
- **Viabilidad técnica:** Datasets de referencia (WLASL, MX-ITESO-100) y avances en modelos temporales permiten diseñar un pipeline reproducible.

### 2.3 Objetivos
**General:**  
Desarrollar un pipeline reproducible de **adquisición → etiquetado → entrenamiento → evaluación**, entregando dataset documentado, código y prototipo de inferencia.

**Específicos:**
1. Definir catálogo inicial de señas y protocolo de captura.
2. Capturar videos y extraer landmarks (MediaPipe Hands/Holistic).
3. Entrenar modelos secuenciales y comparar desempeño.
4. Definir métricas de calidad y umbrales.
5. Entregar prototipo funcional y dataset versionado.

### 2.4 Preguntas clave
- ¿Qué representación de entrada maximiza desempeño (video vs. landmarks normalizados)?  
- ¿Qué modelo temporal equilibra precisión y latencia (LSTM, GRU, TCN, Transformer)?  
- ¿Cómo balancear clases y asegurar generalización (variedad de señantes, iluminación)?  
- ¿Qué métricas definen éxito (F1 Macro, Top-k accuracy, latencia)?  

### 2.5 Involucrados y tipo de participación
- **Sponsor Académico:** Definición de alcance y validación técnica.
- **Equipo 12:** Diseño de protocolo, captura, anotación, modelado y demo.
- **Departamento de Computación:** Infraestructura, lineamientos éticos.
- **Usuarios piloto:** Pruebas de usabilidad y retroalimentación.

---

## 3. Entendimiento de los datos (CRISP-ML)

### 3.1 Descripción de los datos y su contexto
- **Fuentes:**  
  - Datasets públicos: WLASL (ASL), MX-ITESO-100 (LSM).  
  - Generación propia: videos en condiciones controladas y semi-realistas.  
- **Contenido esperado:**  
  - Clips cortos por seña + metadatos de señante, mano dominante, condiciones de captura.  
  - Series temporales de landmarks + features derivadas (distancias, ángulos, velocidades).  

### 3.2 Técnica de ML propuesta
- **Enfoque:** Clasificación multiclase supervisada con modelos temporales.
- **Candidatos:** LSTM, GRU, TCN, Transformers.
- **Representación:** Landmarks normalizados + features cinemáticas.
- **Regularización:** Early stopping, dropout, data augmentation (time-warping, jitter).

### 3.3 Identificación de variables
- **Entradas (X):** coordenadas x/y/z de landmarks + features derivadas.
- **Salida (y):** clase de seña.
- **Variables de control:** FPS, número de frames, condiciones de iluminación, mano dominante.

### 3.4 Métricas de éxito y criterios de calidad
- **Primarias:** F1 Macro ≥ 0.80, Top-1/Top-5 accuracy.  
- **De servicio:** Latencia p95 ≤ 200 ms por secuencia en equipo de referencia.  

### 3.5 Riesgos, supuestos y mitigación
- **Privacidad:** consentimiento informado y anonimización de metadatos.  
- **Desbalance de clases:** oversampling, augmentation y validación estratificada.  
- **Variabilidad de captura:** pruebas en entornos con diferente iluminación y fondo.

---

## 4. Convenios y aspectos éticos/legales
- Formalizar convenios de colaboración para uso de datos.
- Implementar aviso de privacidad y consentimiento informado.
- Respetar lineamientos éticos de trato digno a la población sorda.
- Verificar licencias de datasets y software (WLASL, MX-ITESO-100, MediaPipe).

---

## 5. Bibliografía
- Hernández-Sampieri, R., & Mendoza, C. (2023). *Metodología de la investigación* (3.ª ed.). McGraw-Hill.  
- Visengeriyeva, L., et al. (2023). *CRISP-ML(Q): The ML Lifecycle Process*. [ml-ops.org](https://ml-ops.org/content/crisp-ml)  
- Li, D., et al. (2020). *Word-level deep sign language recognition from video*. WACV.
- Navarrete López, J. A., & Lopez-Nava, I. H. (2025). Mexican Sign Language Alphabet (dynamic signs only) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.14689869 
- [WLASL Dataset](https://dxli94.github.io/WLASL/)  
- [MX-ITESO-100 Dataset](https://www.mdpi.com/2414-4088/7/8/83)  
- [MediaPipe Hands](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)  
- [MediaPipe Holistic](https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker)

