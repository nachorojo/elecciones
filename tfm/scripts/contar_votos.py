import pandas as pd

# Cargar el archivo con los votos detallados
archivo_votos = "05_votos_sin_duplicados.csv"

# Leer el CSV
df = pd.read_csv(archivo_votos, dtype=str)

# Convertir columnas de votos a tipo numérico (int)
columnas_votos = [
    "Votos Derecha",
    "Votos Izquierda",
    "Votos Centro Izquierda",
    "Votos Centro Derecha",
    "Votos Regionalista Izquierda",
    "Votos Regionalista Derecha",
]

for col in columnas_votos:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# Sumar los votos por año
df_total_votos = df.groupby("Ano")[columnas_votos].sum().reset_index()

# Agregar una columna con el total de votos de cada año
df_total_votos["Total Votos"] = df_total_votos[columnas_votos].sum(axis=1)

# Guardar el resultado en un nuevo archivo CSV
df_total_votos.to_csv("votos_totales_por_anio.csv", index=False, encoding="utf-8")

print("Fichero CSV 'votos_totales_por_anio.csv' generado correctamente con los votos totales por año.")
