import pandas as pd

# Diccionario con los archivos .DAT de cada año
archivos_dat = {
    "1996": "../Datos_Mesas/02199603_MESA/03029603.DAT",
    "2000": "../Datos_Mesas/02200003_MESA/03020003.DAT",
    "2004": "../Datos_Mesas/02200403_MESA/03020403.DAT",
    "2008": "../Datos_Mesas/02200803_MESA/03020803.DAT",
    "2011": "../Datos_Mesas/02201111_MESA/03021111.DAT",
    "2015": "../Datos_Mesas/02201512_MESA/03021512.DAT",
    "2016": "../Datos_Mesas/02201606_MESA/03021606.DAT",
    "2019": "../Datos_Mesas/02201904_MESA/03021904.DAT",
    "2019": "../Datos_Mesas/02201911_MESA/03021911.DAT",
    "2023": "../Datos_Mesas/02202307_MESA/03022307.DAT"
}

# Definir la posición de los datos en el archivo .DAT
def extraer_codigo(linea):
    return linea[8:14].strip()

def extraer_siglas(linea):
    return linea[14:54].strip()

def extraer_denominacion(linea):
    return linea[54:154].strip()

# Leer todos los archivos .DAT y extraer la información de los partidos
partidos = {}

for año, archivo in archivos_dat.items():
    try:
        with open(archivo, "r", encoding="latin-1") as infile:
            for linea in infile:
                codigo = extraer_codigo(linea)
                siglas = extraer_siglas(linea)
                denominacion = extraer_denominacion(linea)
                
                # Evitar duplicados basándose en el código de partido
                if codigo not in partidos:
                    partidos[codigo] = [codigo, siglas, denominacion, ""]
    except FileNotFoundError:
        print(f"Archivo no encontrado: {archivo}, omitiendo...")

# Crear un DataFrame con los datos procesados
df_partidos = pd.DataFrame(partidos.values(), columns=["Código", "Siglas", "Denominación", "Clasificacion"])

# Guardar el archivo CSV
df_partidos.to_csv("02_partidos_clasificados.csv", index=False, encoding="utf-8")

print("Fichero CSV 02_partidos_clasificados.csv generado correctamente")
