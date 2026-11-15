import pandas as pd

# 📌 Cargar el CSV
archivo_csv = '22_FINAL_DB.csv'  # Cambia esto si el archivo tiene otro nombre
df = pd.read_csv(archivo_csv, sep=',', dtype=str)

# 📌 Contar las columnas vacías por fila
df['Columnas_Vacias'] = df.isna().sum(axis=1)

# 📌 Contar filas con más de X columnas vacías y cuántas de ellas tienen "Provincia" = 99
conteo_vacias = {}
conteo_provincia_99 = {}

for x in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]:
    filas_filtro = df[df['Columnas_Vacias'] > x]
    conteo_vacias[x] = len(filas_filtro)
    conteo_provincia_99[x] = len(filas_filtro[filas_filtro['Provincia'] == '99'])

# 📌 Imprimir resultados
for columnas in conteo_vacias:
    print(f"🔍 Filas con más de {columnas} columnas vacías: {conteo_vacias[columnas]}")
    print(f"    ➡️ De estas, filas con 'Provincia' = 99: {conteo_provincia_99[columnas]}")

print("✅ Análisis de filas con columnas vacías y 'Provincia' = 99 completado.")
