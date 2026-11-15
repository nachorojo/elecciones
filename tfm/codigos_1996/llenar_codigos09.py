import csv
import pandas as pd

# Parámetros del archivo de entrada y salida
nombre_fichero_dat = "02199603_MESA/09029603.DAT"  # Ajustar según la elección específica
nombre_fichero_csv = "eleccionesDB09.csv"

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
df = pd.read_csv(nombre_fichero_csv, dtype=str)

# Procesar el fichero .DAT
nuevas_filas = []
with open(nombre_fichero_dat, "r", encoding="latin-1") as infile:
    for linea in infile:
        codigo_mesa = extraer_valor(linea, *dat_columns["codigo_mesa"])
        codigo_comunidad = extraer_valor(linea, *dat_columns["codigo_comunidad"])
        codigo_provincia = extraer_valor(linea, *dat_columns["codigo_provincia"])
        codigo_municipio = extraer_valor(linea, *dat_columns["codigo_municipio"])
        
        nuevas_filas.append(["1996", codigo_mesa, codigo_comunidad, codigo_provincia, codigo_municipio])

# Convertir las nuevas filas en un DataFrame
df_nuevo = pd.DataFrame(nuevas_filas, columns=df.columns[:5])

# Agregar los nuevos datos al DataFrame existente
df = pd.concat([df, df_nuevo], ignore_index=True)

# Guardar de nuevo el archivo CSV
df.to_csv(nombre_fichero_csv, index=False, encoding="utf-8")

print(f"Fichero CSV '{nombre_fichero_csv}' actualizado correctamente.")

