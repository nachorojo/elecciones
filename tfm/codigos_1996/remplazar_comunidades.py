import pandas as pd

# Diccionarios de mapeo según los códigos de comunidad, provincia y municipio
comunidades = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Baleares",
    "05": "Canarias", "06": "Cantabria", "07": "Castilla - La Mancha", "08": "Castilla y León",
    "09": "Cataluña", "10": "Extremadura", "11": "Galicia", "12": "Madrid",
    "13": "Navarra", "14": "País Vasco", "15": "Región de Murcia", "16": "La Rioja",
    "17": "Comunidad Valenciana", "18": "Ceuta", "19": "Melilla"
}

# Cargar el archivo CSV existente
ruta_csv = "eleccionesDB_fin.csv"
df = pd.read_csv(ruta_csv, dtype=str)

# Reemplazar códigos por nombres
df["Comunidad"] = df["Comunidad"].map(comunidades).fillna(df["Comunidad"])

# Guardar los cambios
df.to_csv(ruta_csv, index=False, encoding="utf-8")

print("Los códigos han sido reemplazados correctamente en el archivo CSV.")
