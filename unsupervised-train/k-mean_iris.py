# ==========================================
# K-MEANS NÃO SUPERVISIONADO - IRIS
# ==========================================

from sklearn.datasets import load_iris
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import pandas as pd
import joblib
import os

# 1. Pedir número de clusters
while True:
    try:
        n_clusters = int(input("Indique o número de clusters (>1): "))
        if n_clusters > 1:
            break
        else:
            print("O número deve ser maior que 1.")
    except ValueError:
        print("Introduza um número inteiro válido.")

# 2. Carregar dataset
iris = load_iris()

X = iris.data                 # Features (usadas no treino)
y = iris.target               # Species (NÃO usada no treino)

feature_names = iris.feature_names
species_names = iris.target_names

# Criar DataFrame original completo
df_original = pd.DataFrame(X, columns=feature_names)
df_original["species"] = [species_names[i] for i in y]

# 3. Normalização das features
scaler = StandardScaler()
X_normalizado = scaler.fit_transform(X)

# 4. Treinar K-Means (apenas com X)
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
kmeans.fit(X_normalizado)

print("\nClusters criados com sucesso!")

# 5. Criar coluna cluster
clusters_numericos = kmeans.labels_
df_original["cluster"] = [f"Cluster {i+1}" for i in clusters_numericos]

# 6. Mostrar novo dataset
print("\nNovo dataset com classificação de cluster:")
print(df_original.head())

# 7. Guardar modelo
guardar_modelo = input("\nDeseja guardar o modelo? (s/n): ")

if guardar_modelo.lower() == "s":
    if not os.path.exists("modelos"):
        os.makedirs("modelos")

    joblib.dump(kmeans, "modelos/modelo_kmeans.pkl")
    joblib.dump(scaler, "modelos/scaler_kmeans.pkl")
    print("Modelo e scaler guardados com sucesso!")

# 8. Guardar novo dataset
guardar_dataset = input("Deseja guardar o dataset com clusters? (s/n): ")

if guardar_dataset.lower() == "s":
    nome_ficheiro = f"iris_com_{n_clusters}_clusters.csv"
    df_original.to_csv(nome_ficheiro, index=False)
    print(f"Dataset guardado como {nome_ficheiro}")