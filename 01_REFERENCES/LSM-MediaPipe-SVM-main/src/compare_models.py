"""
ESTUDIO COMPARATIVO - SVM Lineal vs SVM RBF
Genera y guarda TODOS los modelos con 21 clases
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import time
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os

print("=" * 70)
print("🔬 ESTUDIO COMPARATIVO - 21 CLASES")
print("=" * 70)

# ============================================================
# 1. Cargar datos
# ============================================================
print("\n📂 Cargando landmarks_dataset.csv...")
df = pd.read_csv('landmarks_dataset.csv')
X = df.iloc[:, :-1].values
y = df['label'].values

print(f"✅ Datos: {len(X)} muestras, {len(np.unique(y))} clases")
print(f"   Clases: {sorted(np.unique(y))}")

# Dividir
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# Escalar
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# LabelEncoder
le = LabelEncoder()
le.fit(y)

print(f"📚 Entrenamiento: {len(X_train)} | 🧪 Prueba: {len(X_test)}")
print(f"🏷️ Clases: {le.classes_}")

# ============================================================
# 2. SVM Lineal
# ============================================================
print("\n" + "-" * 50)
print("📊 2.1 SVM Lineal")
print("-" * 50)

start = time.time()
svm_linear = SVC(kernel='linear', C=1.0, random_state=42)
svm_linear.fit(X_train_scaled, y_train)
time_linear = time.time() - start

y_pred_linear = svm_linear.predict(X_test_scaled)
acc_linear = accuracy_score(y_test, y_pred_linear)

print(f"✅ Precisión: {acc_linear*100:.2f}%")
print(f"⏱️ Tiempo: {time_linear:.2f}s")

# ============================================================
# 3. SVM RBF
# ============================================================
print("\n" + "-" * 50)
print("📊 3.2 SVM RBF (C=10, gamma=0.01)")
print("-" * 50)

start = time.time()
svm_rbf = SVC(kernel='rbf', C=10, gamma=0.01, random_state=42)
svm_rbf.fit(X_train_scaled, y_train)
time_rbf = time.time() - start

y_pred_rbf = svm_rbf.predict(X_test_scaled)
acc_rbf = accuracy_score(y_test, y_pred_rbf)

print(f"✅ Precisión: {acc_rbf*100:.2f}%")
print(f"⏱️ Tiempo: {time_rbf:.2f}s")

# ============================================================
# 4. Red Neuronal (MLPClassifier - sin TensorFlow)
# ============================================================
print("\n" + "-" * 50)
print("📊 4.3 Red Neuronal (MLPClassifier)")
print("-" * 50)

start = time.time()
nn = MLPClassifier(
    hidden_layer_sizes=(128, 64),
    activation='relu',
    max_iter=300,
    random_state=42,
    verbose=False
)
nn.fit(X_train_scaled, y_train)
time_nn = time.time() - start

y_pred_nn = nn.predict(X_test_scaled)
acc_nn = accuracy_score(y_test, y_pred_nn)

print(f"✅ Precisión: {acc_nn*100:.2f}%")
print(f"⏱️ Tiempo: {time_nn:.2f}s")

# ============================================================
# 5. k-NN
# ============================================================
print("\n" + "-" * 50)
print("📊 4.4 k-NN (k=5)")
print("-" * 50)

start = time.time()
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train_scaled, y_train)
time_knn = time.time() - start

y_pred_knn = knn.predict(X_test_scaled)
acc_knn = accuracy_score(y_test, y_pred_knn)

print(f"✅ Precisión: {acc_knn*100:.2f}%")
print(f"⏱️ Tiempo: {time_knn:.2f}s")

# ============================================================
# 6. GUARDAR TODOS LOS MODELOS
# ============================================================
print("\n" + "=" * 60)
print("💾 GUARDANDO MODELOS")
print("=" * 60)

joblib.dump(svm_linear, 'svm_linear_model.pkl')
joblib.dump(svm_rbf, 'svm_rbf_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
joblib.dump(le, 'label_encoder.pkl')
joblib.dump(nn, 'mlp_model.pkl')

print("✅ Modelos guardados:")
print("   - svm_linear_model.pkl  (SVM Lineal, 21 clases)")
print("   - svm_rbf_model.pkl     (SVM RBF, 21 clases)")
print("   - mlp_model.pkl         (Red Neuronal, 21 clases)")
print("   - scaler.pkl")
print("   - label_encoder.pkl")

# ============================================================
# 7. TABLA COMPARATIVA
# ============================================================
print("\n" + "=" * 60)
print("📊 TABLA COMPARATIVA")
print("=" * 60)

comparison_df = pd.DataFrame([
    ['SVM Lineal', f'{acc_linear*100:.2f}%', f'{time_linear:.2f}s'],
    ['SVM RBF', f'{acc_rbf*100:.2f}%', f'{time_rbf:.2f}s'],
    ['Red Neuronal', f'{acc_nn*100:.2f}%', f'{time_nn:.2f}s'],
    ['k-NN (k=5)', f'{acc_knn*100:.2f}%', f'{time_knn:.2f}s']
], columns=['Modelo', 'Precisión', 'Tiempo Entrenamiento'])

print("\n" + comparison_df.to_string(index=False))
comparison_df.to_csv('tabla_comparativa_21clases.csv', index=False)
print("\n💾 Tabla guardada: tabla_comparativa_21clases.csv")

# ============================================================
# 8. MATRICES DE CONFUSIÓN
# ============================================================
print("\n📊 Generando matrices de confusión...")
classes = sorted(np.unique(y))

# Lineal
cm_linear = confusion_matrix(y_test, y_pred_linear)
plt.figure(figsize=(10, 8))
sns.heatmap(cm_linear, annot=True, fmt='d', cmap='Blues',
            xticklabels=classes, yticklabels=classes)
plt.title(f'SVM Lineal - {acc_linear*100:.2f}%')
plt.tight_layout()
plt.savefig('cm_svm_lineal.png', dpi=300)
plt.close()

# RBF
cm_rbf = confusion_matrix(y_test, y_pred_rbf)
plt.figure(figsize=(10, 8))
sns.heatmap(cm_rbf, annot=True, fmt='d', cmap='Greens',
            xticklabels=classes, yticklabels=classes)
plt.title(f'SVM RBF - {acc_rbf*100:.2f}%')
plt.tight_layout()
plt.savefig('cm_svm_rbf.png', dpi=300)
plt.close()

# NN
cm_nn = confusion_matrix(y_test, y_pred_nn)
plt.figure(figsize=(10, 8))
sns.heatmap(cm_nn, annot=True, fmt='d', cmap='Oranges',
            xticklabels=classes, yticklabels=classes)
plt.title(f'Red Neuronal - {acc_nn*100:.2f}%')
plt.tight_layout()
plt.savefig('cm_mlp.png', dpi=300)
plt.close()

print("✅ Matrices de confusión guardadas")

# ============================================================
# 9. VERIFICACIÓN FINAL
# ============================================================
print("\n" + "=" * 60)
print("🔍 VERIFICACIÓN FINAL")
print("=" * 60)

archivos = ['svm_linear_model.pkl', 'svm_rbf_model.pkl', 'mlp_model.pkl',
            'scaler.pkl', 'label_encoder.pkl']

print("\nArchivos generados:")
for archivo in archivos:
    if os.path.exists(archivo):
        print(f"   ✅ {archivo}")
    else:
        print(f"   ❌ {archivo} (FALTA)")

print("\n" + "=" * 60)
print("✅ ¡ESTUDIO COMPARATIVO COMPLETADO!")
print("=" * 60)