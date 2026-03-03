# ==========================================
# 1. Importar bibliotecas
# ==========================================
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import numpy as np
import joblib
# ==========================================
# 2. Carregar dataset Iris
# ==========================================
iris = load_iris()

X = iris.data            # Variáveis de entrada
y = iris.target          # Variável de saída (species)

# ==========================================
# 3. Dividir em treino e teste (supervisionado)
# ==========================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# ==========================================
# 4. Normalização (boa prática)
# ==========================================
scaler = StandardScaler() # (X-media)/desvpad
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# ==========================================
# 5. MODELO SUPERVISIONADO (KNN)
# ==========================================
knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(X_train, y_train)

y_pred = knn.predict(X_test)

print("=== MODELO SUPERVISIONADO (KNN) ===")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("Matriz de Confusão:\n", confusion_matrix(y_test, y_pred))
print("Relatório:\n", classification_report(y_test, y_pred))

# ==========================================
# 6. GRAVAR MODELO SUPERVISIONADO (K-Means)
# ==========================================
joblib.dump(knn, "modelo_supervisionado_knn.pkl")
joblib.dump(scaler, "scaler.pkl")