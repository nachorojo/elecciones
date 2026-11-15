import csv
import pandas as pd

# Parámetros del archivo de entrada y salida
nombre_fichero_dat = "02199603_MESA/10029603.DAT"  # Ajustar según la elección específica
nombre_fichero_csv = "eleccionesDB10.csv"
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
df = pd.read_csv(nombre_fichero_csv, dtype=str)

# Cargar la clasificación de los partidos
partidos_df = pd.read_csv(nombre_fichero_partidos, dtype=str)
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

# Inicializar las columnas de votos si no existen
for col in columnas_votos:
    if col not in df.columns:
        df[col] = 0

# Procesar el fichero .DAT
nuevas_filas = []
with open(nombre_fichero_dat, "r", encoding="latin-1") as infile:
    for linea in infile:
        codigo_mesa = extraer_valor(linea, *dat_columns["codigo_mesa"])
        codigo_comunidad = extraer_valor(linea, *dat_columns["codigo_comunidad"])
        codigo_provincia = extraer_valor(linea, *dat_columns["codigo_provincia"])
        codigo_municipio = extraer_valor(linea, *dat_columns["codigo_municipio"])
        codigo_candidatura = extraer_valor(linea, *dat_columns["codigo_candidatura"])
        votos = int(extraer_valor(linea, *dat_columns["votos"]))
        
        fila = ["1996", codigo_mesa, codigo_comunidad, codigo_provincia, codigo_municipio]
        votos_dict = {col: 0 for col in columnas_votos}
        
        clasificacion = clasificacion_partidos.get(codigo_candidatura, None)
        if clasificacion and f"Votos {clasificacion}" in votos_dict:
            votos_dict[f"Votos {clasificacion}"] = votos
        
        fila.extend([votos_dict[col] for col in columnas_votos])
        nuevas_filas.append(fila)

# Convertir las nuevas filas en un DataFrame
df_nuevo = pd.DataFrame(nuevas_filas, columns=list(df.columns[:5]) + columnas_votos)

# Agregar los nuevos datos al DataFrame existente
df = pd.concat([df, df_nuevo], ignore_index=True)

# Guardar el archivo CSV actualizado
df.to_csv(nombre_fichero_csv, index=False, encoding="utf-8")

print(f"Fichero CSV '{nombre_fichero_csv}' actualizado correctamente.")