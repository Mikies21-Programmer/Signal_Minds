# Source code

This folder contains the source code of the system.

## Files

| File | Description |
|------|-------------|
| `compare_models.py` | Full pipeline: landmark extraction, training of the four classifiers, evaluation, and comparison |
| `extract_landmarks.py` | MediaPipe Hands landmark extraction from the Zenodo dataset |
| `hri_interface.py` | Human-robot interaction GUI with real-time sign recognition and robot simulation |

## Pipeline

The full pipeline is:

1. `extract_landmarks.py` — reads the images from the Zenodo dataset and generates `landmarks_dataset.csv`
2. `compare_models.py` — trains and evaluates the four classifiers, saves the models, and generates the confusion matrices and comparison table
3. `hri_interface.py` — loads the trained RBF SVM model and runs the real-time recognition GUI

## Requirements

See `requirements.txt` in the repository root.

## Usage

python src/extract_landmarks.py --data-dir ./data --output ./data/landmarks_dataset.csv

python src/compare_models.py

python src/hri_interface.py
