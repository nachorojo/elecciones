import pandas as pd

# 📂 Rutas (¡Cambia estas rutas por las tuyas!)
csv_path = "participacion.csv"  # CSV principal
csv_edades = "Edad_media_ine.csv"  # CSV de edades medias

# 📌 Cargar el CSV de edades medias
df_edades = pd.read_csv(csv_edades, delimiter=";")  # CSV separado por ';'

# 🔹 Filtrar solo "Ambos sexos"
df_edades = df_edades[df_edades["Sexo"] == "Ambos sexos"]

# 🔹 Crear un diccionario con { (provincia, año) : edad_media }
edad_media_dict = {
    (row["Provincias"][:2], str(row["Periodo"])): float(row["Total"].replace(",", "."))
    for _, row in df_edades.iterrows()
}

# 📂 Cargar el CSV principal
df = pd.read_csv(csv_path)

# 🔹 Asegurar que Provincia y Año sean strings para hacer el mapeo correctamente
df["Provincia"] = df["Provincia"].astype(str).str.zfill(2)
df["Año"] = df["Año"].astype(str)

# 🔹 Asignar la edad media según la provincia y el año
df["Edad Media"] = df.apply(
    lambda row: edad_media_dict.get((row["Provincia"], row["Año"]), ""), axis=1
)

# 📂 Guardar el CSV modificado
df.to_csv("edad_media.csv", index=False)

print("✅ CSV modificado guardado como 'edad_media.csv'")
