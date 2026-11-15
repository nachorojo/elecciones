import pandas as pd

# Parámetros del archivo de entrada y salida
nombre_fichero_csv = "eleccionesDB09.csv"
nombre_fichero_salida = "eleccionesDB09_sindup.csv"

# Cargar el archivo CSV
df = pd.read_csv(nombre_fichero_csv, dtype=str)

# Definir las columnas para identificar duplicados
columnas_clave = ["Año", "Mesa", "Comunidad", "Provincia", "Municipio"]

# Eliminar duplicados conservando solo la primera aparición
df_sin_duplicados = df.drop_duplicates(subset=columnas_clave, keep="first")

# Guardar el archivo actualizado
df_sin_duplicados.to_csv(nombre_fichero_salida, index=False, encoding="utf-8")

print(f"Fichero CSV '{nombre_fichero_salida}' generado correctamente sin duplicados.")