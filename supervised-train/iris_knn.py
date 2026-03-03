# ==============================
# 1. Importar bibliotecas
# ==============================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# ==============================
# 2. Carregar o dataset Iris
# ==============================
iris = load_iris()

X = iris.data          # Features
y = iris.target        # Labels

# ==============================
# 3. Dividir em treino e teste
# ==============================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.2, 
    random_state=42,
    stratify=y
)

# ==============================
# 4. Padronização (ESSENCIAL para KNN)
# ==============================
scaler = StandardScaler()

X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# ==============================
# 5. Criar modelo KNN
# ==============================
knn = KNeighborsClassifier(n_neighbors=5)

# ==============================
# 6. Treinar modelo
# ==============================
knn.fit(X_train, y_train)

# ==============================
# 7. Fazer previsões
# ==============================
y_pred = knn.predict(X_test)

# ==============================
# 8. Avaliação
# ==============================
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred, target_names=iris.target_names))

print("\nConfusion Matrix:\n")
print(confusion_matrix(y_test, y_pred))