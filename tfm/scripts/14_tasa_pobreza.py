import pandas as pd

# 📌 Cargar el CSV con las tasas de pobreza
pobreza_df = pd.read_csv('../ine/tasa_pobreza.csv', sep=';')

# 🔹 Limpiar y convertir datos
pobreza_df['Autonomous Communities and Cities'] = pobreza_df['Autonomous Communities and Cities'].str.strip()
pobreza_df['Period'] = pobreza_df['Period'].astype(str)

# 🔹 Crear un diccionario para mapear (comunidad, año) → tasa de pobreza
pobreza_dict = {
    (row['Autonomous Communities and Cities'].split()[0], row['Period']): row['Total']
    for _, row in pobreza_df.iterrows()
}

# 📌 Cargar el CSV que debe ser modificado
datos_df = pd.read_csv('14_inmigracion.csv')

# 🔹 Función para asignar la tasa de pobreza
def asignar_pobreza(row):
    key = (str(row['Comunidad']).zfill(2), str(row['Ano']))
    
    # Si el año es 2019a o 2019b, usar los datos de 2019
    if key[1] in ["2019a", "2019b"]:
        return pobreza_dict.get((key[0], "2019"), None)
    
    return pobreza_dict.get(key, None)

# 🔹 Llenar la columna 'Tasa de Pobreza'
datos_df['Tasa de Pobreza'] = datos_df.apply(asignar_pobreza, axis=1)

# 📂 Guardar el CSV modificado
datos_df.to_csv('15_tasa_pobreza.csv', index=False)

print("✅ La columna 'Tasa de Pobreza' ha sido rellenada correctamente en '15_tasa_pobreza.csv'.")
