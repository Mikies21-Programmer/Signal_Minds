# LSM-MediaPipe-SVM

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![IEEE](https://img.shields.io/badge/Paper-IEEE%20Latin%20America%20Transactions-blue)]()

Reproducible benchmark of classifiers for the static alphabet of Mexican Sign Language (LSM) on GPU-less hardware.

## 📌 Overview

This repository contains the full source code, trained models, and reproducible results for the paper:

> **"Reproducible Benchmark of Classifiers for the Static Alphabet of Mexican Sign Language on GPU-less Hardware"**
> Juan Juárez Fuentes, Hugo Alberto Flores Arguedas, Eduardo Sánchez Soto
> *IEEE Latin America Transactions* (under review)

The system recognizes the static alphabet of Mexican Sign Language (LSM) in real time using:

- **MediaPipe Hands** for 21 hand landmarks extraction (63 normalized features)
- **SVM with RBF kernel** as the final classifier
- **No GPU required** — runs on a standard CPU (Ryzen 5, 16 GB RAM)

## 🎯 Results

| Model | Accuracy | Train time (s) | Inference (ms) |
|-------|----------|----------------|----------------|
| Linear SVM | 97.53% | 230.54 | 0.65 |
| **RBF SVM** | **99.36%** | **174.41** | **1.20** |
| k-NN (k=5) | 99.09% | 0.43 | 2.30 |
| MLP (128, 64) | 99.63% | 327.85 | 1.85 |

- **Real-time performance:** 16.8 FPS with full GUI
- **Hardware:** Dell Ryzen 5, 16 GB RAM, no dedicated GPU
- **Validation:** service-robotics simulation on 11×11 grid

## 📁 Repository structure

LSM-MediaPipe-SVM/
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── src/
│   ├── compare_models.py       # Full pipeline: extraction, training & comparison
│   ├── extract_landmarks.py    # MediaPipe landmark extraction
│   └── hri_interface.py        # Human-robot interaction GUI
├── models/
│   ├── label_encoder.pkl
│   ├── scaler.pkl
│   ├── svm_linear_model.pkl
│   ├── svm_rbf_model.pkl
│   └── mlp_model.pkl
├── results/
│   ├── tabla_comparativa_21clases.csv
│   ├── cm_svm_lineal.png
│   ├── cm_svm_rbf.png
│   ├── cm_mlp.png
│   ├── captura_A.png
│   ├── captura_B.png
│   ├── captura_C.png
│   └── captura_D.png
└── data/
    └── README.md               # Instructions to regenerate the dataset

## 🚀 Installation

git clone https://github.com/juanjuarezf/LSM-MediaPipe-SVM.git

cd LSM-MediaPipe-SVM

python -m venv venv

source venv/bin/activate   # Linux/Mac

venv\Scripts\activate      # Windows

pip install -r requirements.txt

## 📊 Dataset

The dataset used in this work is publicly available on Zenodo:

> Chacon Quintero, A. et al. (2022). *Dataset LSM Lenguaje de señas mexicanas*. Zenodo.
> DOI: [10.5281/zenodo.6554337](https://doi.org/10.5281/zenodo.6554337)

We used the complete public dataset from Zenodo, consisting of 276,152 images across 21 LSM letters:
A, B, C, D, E, F, G, H, I, L, M, N, O, P, R, S, T, U, V, W, Y.

Excluded letters: J, K, Z (require motion) and Q, X, Ñ (high visual similarity).

**Note:** The extracted features file (`landmarks_dataset.csv`, 336 MB) is not included in this repository due to GitHub's file size limit (25 MB). It can be regenerated following the instructions below.

## 🧪 Reproducibility

To reproduce the results reported in the paper:

1. Download the dataset from Zenodo (DOI: 10.5281/zenodo.6554337)
2. Run `extract_landmarks.py` to generate `landmarks_dataset.csv` (336 MB, not included due to GitHub size limits)
3. Run `compare_models.py` to train and evaluate all classifiers
4. Run `hri_interface.py` to launch the human-robot interaction demo

python src/extract_landmarks.py --data-dir ./data --output ./features.npy

python src/compare_models.py --features ./features.npy --output ./models

python src/hri_interface.py --model ./models/svm_rbf_model.pkl

All experiments were run with random_state=42 for reproducibility.

## 📖 Citation

If you use this code in your research, please cite:

@article{juarez2026lsm,
  title={Reproducible Benchmark of Classifiers for the Static Alphabet of Mexican Sign Language on GPU-less Hardware},
  author={Ju{\'a}rez Fuentes, Juan and Flores Arguedas, Hugo Alberto and S{\'a}nchez Soto, Eduardo},
  journal={IEEE Latin America Transactions},
  year={2026},
  note={Under review}
}

## 📜 License

This project is licensed under the MIT License — see the LICENSE file for details.

The dataset is licensed under CC BY 4.0 by its original authors.

## 👤 Author

**Juan Juárez Fuentes**
- Matrícula: AL12514850
- Universidad Abierta y a Distancia de México (UnADM)
- Email: al12514850@unadmexico.mx
- GitHub: [@juanjuarezf](https://github.com/juanjuarezf)

## 🙏 Acknowledgments

- Dr. Hugo Alberto Flores Arguedas (internal advisor)
- Dr. Eduardo Sánchez Soto (external advisor)
- UnADM for academic support

## 📬 Contact

For questions or collaborations, please open an issue or contact the author directly.
