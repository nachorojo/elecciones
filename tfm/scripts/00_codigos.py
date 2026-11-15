import csv
import pandas as pd


archivos_dat = {
    "1996": "../Datos_Mesas/02199603_MESA/09029603.DAT",
    "2000": "../Datos_Mesas/02200003_MESA/09020003.DAT",
    "2004": "../Datos_Mesas/02200403_MESA/09020403.DAT",
    "2008": "../Datos_Mesas/02200803_MESA/09020803.DAT",
    "2011": "../Datos_Mesas/02201111_MESA/09021111.DAT",
    "2015": "../Datos_Mesas/02201512_MESA/09021512.DAT",
    "2016": "../Datos_Mesas/02201606_MESA/09021606.DAT",
    "2019a": "../Datos_Mesas/02201904_MESA/09021904.DAT",
    "2019b": "../Datos_Mesas/02201911_MESA/09021911.DAT",
    "2023": "../Datos_Mesas/02202307_MESA/09022307.DAT"
}

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
    "censo_ine": (24, 30),
    "censo_escrutinio": (31, 37),
    "censo_cere": (38, 44),
    "total_votantes": (45, 51),
    "votantes_1er": (52, 58),
    "votantes_2do": (59, 65),
    "votos_en_blanco": (66, 72),
    "votos_nulos": (73, 79),
    "votos_a_candidaturas": (80, 86),
    "votos_afirmativos_referendum": (87, 93),
    "votos_negativos_referendum": (94, 100),
    "datos_oficiales": (101, 101),
}

def extraer_valor(linea, inicio, fin):
    """Extrae un valor de una línea dado un rango de posiciones."""
    return linea[inicio-1:fin].strip()

# Cargar el archivo CSV existente
df = pd.read_csv("00_DB_vacia.csv", dtype=str)

# Procesar todos los archivos .DAT
nuevas_filas = []

for año, archivo in archivos_dat.items():
    try:
        with open(archivo, "r", encoding="latin-1") as infile:
            for linea in infile:
                codigo_mesa = extraer_valor(linea, *dat_columns["codigo_mesa"])
                codigo_comunidad = extraer_valor(linea, *dat_columns["codigo_comunidad"])
                codigo_provincia = extraer_valor(linea, *dat_columns["codigo_provincia"])
                codigo_municipio = extraer_valor(linea, *dat_columns["codigo_municipio"])
                
                nuevas_filas.append([año, codigo_mesa, codigo_comunidad, codigo_provincia, codigo_municipio])
    except FileNotFoundError:
        print(f"Archivo no encontrado: {archivo}, omitiendo...")

# Convertir las nuevas filas en un DataFrame
df_nuevo = pd.DataFrame(nuevas_filas, columns=df.columns[:5])

# Agregar los nuevos datos al DataFrame existente
df = pd.concat([df, df_nuevo], ignore_index=True)

# Guardar de nuevo el archivo CSV
df.to_csv("01_codigos.csv", index=False, encoding="utf-8")

print("Fichero CSV 01_codigos.csv actualizado correctamente.")

