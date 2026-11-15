import pandas as pd


archivos_dat = {
    "1996": "../Datos_Mesas/02199603_MESA/10029603.DAT",
    "2000": "../Datos_Mesas/02200003_MESA/10020003.DAT",
    "2004": "../Datos_Mesas/02200403_MESA/10020403.DAT",
    "2008": "../Datos_Mesas/02200803_MESA/10020803.DAT",
    "2011": "../Datos_Mesas/02201111_MESA/10021111.DAT",
    "2015": "../Datos_Mesas/02201512_MESA/10021512.DAT",
    "2016": "../Datos_Mesas/02201606_MESA/10021606.DAT",
    "2019a": "../Datos_Mesas/02201904_MESA/10021904.DAT",
    "2019b": "../Datos_Mesas/02201911_MESA/10021911.DAT",
    "2023": "../Datos_Mesas/02202307_MESA/10022307.DAT",
}

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
df_10 = pd.read_csv("03_votos.csv", dtype=str)
df_09 = pd.read_csv("01_codigos.csv", dtype=str)

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
votos_agregados = df_10.groupby(["Ano", "Mesa", "Comunidad", "Provincia", "Municipio"])[columnas_votos].sum().reset_index()

# Fusionar con el archivo eleccionesDB09.csv
df_09_actualizado = df_09.merge(votos_agregados, on=["Ano", "Mesa", "Comunidad", "Provincia", "Municipio"], how="left", suffixes=("", "_votos"))

# Reemplazar los valores de votos en df_09_actualizado
df_09_actualizado[columnas_votos] = df_09_actualizado[[col + "_votos" for col in columnas_votos]].fillna(0).astype(int)

# Eliminar columnas temporales
df_09_actualizado = df_09_actualizado.drop(columns=[col + "_votos" for col in columnas_votos])

# Guardar el archivo actualizado
df_09_actualizado.to_csv("04_votos_por_mesa.csv", index=False, encoding="utf-8")

print(f"Fichero CSV 04_votos_por_mesa.csv actualizado correctamente con los votos sumados de 03_votos.csv.")
