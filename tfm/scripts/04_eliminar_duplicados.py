import pandas as pd

# Cargar el archivo CSV
df = pd.read_csv("04_votos_por_mesa.csv", dtype=str)

# Definir las columnas para identificar duplicados
columnas_clave = ["Ano", "Mesa", "Comunidad", "Provincia", "Municipio"]

# Eliminar duplicados conservando solo la primera aparición
df_sin_duplicados = df.drop_duplicates(subset=columnas_clave, keep="first")

# Guardar el archivo actualizado
df_sin_duplicados.to_csv("05_votos_sin_duplicados.csv", index=False, encoding="utf-8")

print(f"Fichero CSV 05_votos_sin_duplicados.csv generado correctamente sin duplicados.")