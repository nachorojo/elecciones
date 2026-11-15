import pandas as pd

csv_path = "../csv/06_participacion.csv" 
csv_edades = "../ine/Edad_media_ine.csv"  

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
df["Ano"] = df["Ano"].astype(str)

# 🔹 Asignar la edad media según la provincia y el año, usando 2019 si es 2019a o 2019b
df["Edad Media"] = df.apply(
    lambda row: edad_media_dict.get((row["Provincia"], "2019"), "") if row["Ano"] in ["2019a", "2019b"] 
    else edad_media_dict.get((row["Provincia"], row["Ano"]), ""),
    axis=1
)

# 📂 Guardar el CSV modificado
df.to_csv("07_edad_media.csv", index=False)

print("✅ CSV modificado guardado como '07_edad_media.csv'")
