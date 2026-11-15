import pandas as pd

# 📌 Cargar los CSVs
df_main = pd.read_csv('16_tasa_desempleo.csv', dtype={"Ano": str})
df_crime = pd.read_csv('../ine/criminalidad.csv', sep=';', encoding='latin1', dtype={"Periodo": str})

# 🔹 Extraer código de provincia y asegurarse de que el año sea string
df_crime['Codigo_Provincia'] = df_crime['Lugar de condena'].str.extract(r'(\d{2})')
df_crime['Ano'] = df_crime['Periodo'].astype(str)

# 🔹 Convertir 'Total' a string antes de reemplazar comas y luego a float
df_crime['Total'] = pd.to_numeric(df_crime['Total'].astype(str).str.replace(',', '.'), errors='coerce')

# 🔹 Asegurar que 'Ano' y 'Provincia' sean string en df_main
df_main['Ano'] = df_main['Ano'].astype(str)
df_main['Provincia'] = df_main['Provincia'].astype(str).str.zfill(2)

# 🔹 Crear un diccionario de criminalidad {(Año, Provincia) → Total delitos}
crime_dict = df_crime.set_index(['Ano', 'Codigo_Provincia'])['Total'].to_dict()

# 🔹 Función para asignar criminalidad
def asignar_criminalidad(row):
    key = (row['Ano'], row['Provincia'])
    
    # Si el año es 2019a o 2019b, usar los datos de 2019
    if key[0] in ["2019a", "2019b"]:
        return crime_dict.get(("2019", key[1]), None)
    
    return crime_dict.get(key, None)

# 🔹 Llenar la columna 'Criminalidad'
df_main['Criminalidad'] = df_main.apply(asignar_criminalidad, axis=1)

# 📂 Guardar el CSV modificado
df_main.to_csv('17_criminalidad.csv', index=False)

print("✅ La columna 'Criminalidad' ha sido rellenada correctamente en '17_criminalidad.csv'.")
