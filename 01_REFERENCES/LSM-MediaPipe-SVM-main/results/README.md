# Results

This folder contains the reproducible results reported in the paper.

## Files

### Comparison table

- `tabla_comparativa_21clases.csv` — Accuracy and training time for the four classifiers

### Confusion matrices

- `cm_svm_lineal.png` — Linear SVM (97.53%)
- `cm_svm_rbf.png` — RBF SVM (99.36%)
- `cm_mlp.png` — Multi-layer perceptron (99.63%)

### Real-time captures

- `captura_A.png` — Letter A: AVANZAR
- `captura_B.png` — Letter B: RETROCEDER
- `captura_C.png` — Letter C: GIRAR IZQUIERDA
- `captura_D.png` — Letter D: GIRAR DERECHA

## Reproducibility

All results were generated with `random_state=42` and can be reproduced by running:

python src/compare_models.py
