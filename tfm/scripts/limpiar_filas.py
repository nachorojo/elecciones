import pandas as pd

# 📌 Cargar el CSV
archivo_csv = '22_FINAL_DB.csv'  # Cambia esto si el archivo tiene otro nombre
df = pd.read_csv(archivo_csv, sep=',', dtype=str)

# 📌 Contar filas antes de la eliminación
filas_antes = len(df)
filas_con_99 = len(df[df['Provincia'] == '99'])

# 📌 Eliminar filas donde "Provincia" es '99'
df = df[df['Provincia'] != '99']

# 📌 Contar filas después de la eliminación
filas_despues = len(df)

# 📌 Guardar el resultado en un nuevo archivo
df.to_csv('22_FINAL_DB.csv', index=False, sep=',')

# 📌 Imprimir resultados
print(f"🔍 Filas antes de la eliminación: {filas_antes}")
print(f"❌ Filas eliminadas (Provincia = 99): {filas_con_99}")
print(f"✅ Filas restantes después de la eliminación: {filas_despues}")
print("📂 Se ha guardado el nuevo archivo como '22_FINAL_DB_SIN_99.csv'")
