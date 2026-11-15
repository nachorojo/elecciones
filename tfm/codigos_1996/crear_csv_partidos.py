import pandas as pd

# Parámetros del archivo de entrada y salida
nombre_fichero_dat = "02199603_MESA/03029603.DAT"
nombre_fichero_csv = "partidos_generados.csv"

# Definir la posición del código de partido en el archivo .DAT
def extraer_codigo(linea):
    return linea[8:14].strip()

def extraer_siglas(linea):
    return linea[14:54].strip()

def extraer_denominacion(linea):
    return linea[54:154].strip()

# Leer el archivo .DAT y extraer la información de los partidos
partidos = []
with open(nombre_fichero_dat, "r", encoding="latin-1") as infile:
    for linea in infile:
        codigo = extraer_codigo(linea)
        siglas = extraer_siglas(linea)
        denominacion = extraer_denominacion(linea)
        partidos.append([codigo, siglas, denominacion, ""])

# Crear un DataFrame con los datos procesados
df_partidos = pd.DataFrame(partidos, columns=["Código", "Siglas", "Denominación", "Clasificacion"])

# Guardar el archivo CSV
df_partidos.to_csv(nombre_fichero_csv, index=False, encoding="utf-8")

print(f"Fichero CSV '{nombre_fichero_csv}' generado correctamente con la columna 'Clasificacion' vacía.")
