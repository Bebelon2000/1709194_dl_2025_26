# ==========================================
# PREDIÇÃO - MODELO SUPERVISIONADO (KNN)
# ==========================================

import joblib
import numpy as np

# 1. Carregar modelo e scaler
knn = joblib.load("modelo_supervisionado_knn.pkl")
scaler = joblib.load("scaler.pkl")

# 2. Pedir input ao utilizador
print("Introduza as medidas da flor Iris:")

sepal_length = float(input("Sepal length (cm): "))
sepal_width = float(input("Sepal width (cm): "))
petal_length = float(input("Petal length (cm): "))
petal_width = float(input("Petal width (cm): "))

# 3. Criar array com os valores
novo_dado = np.array([[sepal_length,
                       sepal_width,
                       petal_length,
                       petal_width]])

# 4. Normalizar com o scaler já treinado
novo_dado_normalizado = scaler.transform(novo_dado)

# 5. Fazer previsão
predicao = knn.predict(novo_dado_normalizado)

# 6. Converter número para nome da espécie
classes = ["setosa", "versicolor", "virginica"]

print("\nEspécie prevista:", classes[predicao[0]])