import pandas as pd

# Parámetros de los archivos de entrada y salida
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
    "codigo_mesa": (23, 23),
    "codigo_comunidad": (10, 11),
    "codigo_provincia": (12, 13),
    "codigo_municipio": (14, 16),
    "codigo_candidatura": (24, 29),
    "votos": (30, 36),
}

# Función para extraer valores de una línea del archivo .DAT
def extraer_valor(linea, inicio, fin):
    return linea[inicio - 1 : fin].strip()

# Cargar la clasificación de los partidos
partidos_df = pd.read_csv("02_partidos_clasificados.csv", dtype=str)
partidos_df["Código"] = partidos_df["Código"].astype(int).astype(str).str.zfill(6)
clasificacion_partidos = partidos_df.set_index("Código")["Clasificacion"].to_dict()

# Definir las columnas de votos
columnas_votos = [
    "Votos Derecha",
    "Votos Izquierda",
    "Votos Centro Izquierda",
    "Votos Centro Derecha",
    "Votos Regionalista Izquierda",
    "Votos Regionalista Derecha",
]

# Crear una lista para almacenar los datos finales
datos_finales = []

# Procesar todos los archivos .DAT
for año, archivo in archivos_dat.items():
    try:
        with open(archivo, "r", encoding="latin-1") as infile:
            for linea in infile:
                codigo_mesa = extraer_valor(linea, *dat_columns["codigo_mesa"])
                codigo_comunidad = extraer_valor(linea, *dat_columns["codigo_comunidad"])
                codigo_provincia = extraer_valor(linea, *dat_columns["codigo_provincia"])
                codigo_municipio = extraer_valor(linea, *dat_columns["codigo_municipio"])
                codigo_candidatura = extraer_valor(linea, *dat_columns["codigo_candidatura"])
                votos = int(extraer_valor(linea, *dat_columns["votos"]))

                # Crear diccionario para los votos inicializados en 0
                votos_dict = {col: 0 for col in columnas_votos}

                # Asignar votos a la clasificación correspondiente
                clasificacion = clasificacion_partidos.get(codigo_candidatura, None)
                if clasificacion and f"Votos {clasificacion}" in votos_dict:
                    votos_dict[f"Votos {clasificacion}"] = votos

                # Crear la fila con los datos y los votos
                fila = [año, codigo_mesa, codigo_comunidad, codigo_provincia, codigo_municipio]
                fila.extend([votos_dict[col] for col in columnas_votos])
                datos_finales.append(fila)

    except FileNotFoundError:
        print(f"Archivo no encontrado: {archivo}, omitiendo...")

# Crear DataFrame final con todos los datos
columnas_finales = ["Ano", "Mesa", "Comunidad", "Provincia", "Municipio"] + columnas_votos
df_final = pd.DataFrame(datos_finales, columns=columnas_finales)

# Guardar el archivo CSV actualizado
df_final.to_csv("03_votos.csv", index=False, encoding="utf-8")

print("Fichero CSV 03_votos.csv actualizado.")
