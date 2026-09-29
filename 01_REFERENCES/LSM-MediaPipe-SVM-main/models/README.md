# Trained models

This folder contains the trained classifiers and preprocessing objects used in the paper.

## Files

| File | Description |
|------|-------------|
| `label_encoder.pkl` | LabelEncoder for the 21 LSM letters (A–Y) |
| `scaler.pkl` | StandardScaler fitted on the training set |
| `svm_linear_model.pkl` | Linear SVM (97.53% accuracy) |
| `svm_rbf_model.pkl` | RBF SVM (99.36% accuracy) — final model |
| `mlp_model.pkl` | Multi-layer perceptron (99.63% accuracy) |

## Usage

To load the final model (RBF SVM):

python
import joblib

model = joblib.load('models/svm_rbf_model.pkl')
scaler = joblib.load('models/scaler.pkl')
encoder = joblib.load('models/label_encoder.pkl')

All models were trained with random_state=42.
