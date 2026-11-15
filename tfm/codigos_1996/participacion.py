import pandas as pd
import os
import re

# Ruta de los ficheros de datos electorales
ruta_ficheros = "02199603_MESA/"

# Ruta del CSV a modificar
csv_path = "eleccionesDB_fin.csv"

# 📌 Columnas de los archivos .DAT
dat_columns = {
    "tipo_eleccion": (1, 2),
    "año": (3, 6),
    "mes": (7, 8),
    "vuelta": (9, 9),
    "codigo_comunidad": (10, 11),
    "codigo_provincia": (12, 13),
    "codigo_municipio": (14, 16),
    "censo_ine": (78, 85),
    "censo_escrutinio": (86, 93),
    "total_votantes": (110, 117),  # Total de votantes
}

# 📌 Diccionario para almacenar la tasa de participación por provincia
tasa_participacion_provincia = {}

# 📂 Procesar ficheros 05xxaamm.DAT y 07xxaamm.DAT
for fichero in os.listdir(ruta_ficheros):
    if fichero.startswith(("05", "07")) and fichero.endswith(".DAT"):
        with open(os.path.join(ruta_ficheros, fichero), "r", encoding="latin-1") as file:
            for linea in file:
                provincia = linea[dat_columns["codigo_provincia"][0] - 1:dat_columns["codigo_provincia"][1]].strip()
                censo = int(linea[dat_columns["censo_ine"][0] - 1:dat_columns["censo_ine"][1]].strip() or 0)
                votantes = int(linea[dat_columns["total_votantes"][0] - 1:dat_columns["total_votantes"][1]].strip() or 0)

                if provincia and censo > 0:
                    tasa_participacion = (votantes / censo) * 100
                    tasa_participacion_provincia[provincia.zfill(2)] = round(tasa_participacion, 2)

# 📌 Mostrar las tasas extraídas para depuración
print("📊 Tasas de Participación extraídas:")
for prov, tasa in tasa_participacion_provincia.items():
    print(f"🔹 Provincia {prov}: {tasa}%")

# 📂 Cargar el CSV
df = pd.read_csv(csv_path)

# 🔹 Asegurar que la columna Provincia sea de dos dígitos
df["Provincia"] = df["Provincia"].astype(str).str.zfill(2)

# 🔹 Mapear la tasa de participación al CSV
df["Tasa de Participacion"] = df["Provincia"].map(tasa_participacion_provincia)

# 📂 Guardar el CSV modificado
df.to_csv("participacion.csv", index=False)

print("✅ CSV modificado guardado como 'participacion.csv'")
