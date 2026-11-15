import csv
import pandas as pd

# Parámetros del archivo de entrada y salida
nombre_fichero_dat = "02199603_MESA/10029603.DAT"  # Ajustar según la elección específica
nombre_fichero_csv = "eleccionesDB10.csv"
nombre_fichero_csv_09 = "eleccionesDB09.csv"
nombre_fichero_partidos = "partidos_clasificados.csv"

# Definir las columnas del archivo .DAT
dat_columns = {
    "tipo_eleccion": (1, 2),
    "año": (3, 6),
    "mes": (7, 8),
    "vuelta": (9, 9),
    "codigo_comunidad": (10, 11),
    "codigo_provincia": (12, 13),
    "codigo_municipio": (14, 16),
    "distrito": (17, 18),
    "codigo_seccion": (19, 22),
    "codigo_mesa": (23, 23),
    "codigo_candidatura": (24, 29),
    "votos": (30, 36),
}

# Función para extraer valores de una línea del archivo .DAT
def extraer_valor(linea, inicio, fin):
    return linea[inicio-1:fin].strip()

# Cargar el archivo CSV existente
df_10 = pd.read_csv(nombre_fichero_csv, dtype=str)
df_09 = pd.read_csv(nombre_fichero_csv_09, dtype=str)

# Definir las columnas de votos
columnas_votos = [
    "Votos Derecha",
    "Votos Izquierda",
    "Votos Centro Izquierda",
    "Votos Centro Derecha",
    "Votos Regionalista Izquierda",
    "Votos Regionalista Derecha",
]

# Asegurar que las columnas de votos sean numéricas
df_10[columnas_votos] = df_10[columnas_votos].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
df_09[columnas_votos] = 0

# Agrupar los votos por combinación de Año, Mesa, Comunidad, Provincia y Municipio
votos_agregados = df_10.groupby(["Año", "Mesa", "Comunidad", "Provincia", "Municipio"])[columnas_votos].sum().reset_index()

# Fusionar con el archivo eleccionesDB09.csv
df_09_actualizado = df_09.merge(votos_agregados, on=["Año", "Mesa", "Comunidad", "Provincia", "Municipio"], how="left", suffixes=("", "_votos"))

# Reemplazar los valores de votos en df_09_actualizado
df_09_actualizado[columnas_votos] = df_09_actualizado[[col + "_votos" for col in columnas_votos]].fillna(0).astype(int)

# Eliminar columnas temporales
df_09_actualizado = df_09_actualizado.drop(columns=[col + "_votos" for col in columnas_votos])

# Guardar el archivo actualizado
df_09_actualizado.to_csv(nombre_fichero_csv_09, index=False, encoding="utf-8")

print(f"Fichero CSV '{nombre_fichero_csv_09}' actualizado correctamente con los votos sumados de '{nombre_fichero_csv}'.")
