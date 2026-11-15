import pandas as pd

# 📌 Cargar los CSVs con la codificación correcta
df_main = pd.read_csv('15_tasa_pobreza.csv', dtype={"Ano": str}, low_memory=False)

df_unemployment1 = pd.read_csv('../ine/paro_2004_2016.csv', sep=';', encoding='latin1')
df_unemployment2 = pd.read_csv('../ine/paro_2019_2023.csv', sep=';', encoding='latin1')

# 🔹 Unificar ambos datasets en uno solo
df_unemployment = pd.concat([df_unemployment1, df_unemployment2], ignore_index=True)

# 🔹 Extraer el código de provincia y el año (ignorando T4)
df_unemployment['Codigo_Provincia'] = df_unemployment['Provincias'].str.extract(r'(\d{2})')
df_unemployment['Ano'] = df_unemployment['Periodo'].str.extract(r'(\d{4})')

# 🔹 Asegurar que 'Ano' es string para coincidir con df_main
df_unemployment['Ano'] = df_unemployment['Ano'].astype(str)

# 🔹 Convertir 'Total' a string antes de reemplazar comas y luego a float
df_unemployment['Total'] = pd.to_numeric(df_unemployment['Total'].astype(str).str.replace(',', '.'), errors='coerce')

# 🔹 Convertir la columna 'Ano' en df_main a string y normalizar 'Provincia'
df_main['Ano'] = df_main['Ano'].astype(str)
df_main['Provincia'] = df_main['Provincia'].astype(str).str.zfill(2)

# 🔹 Crear un diccionario de tasas de desempleo {(Año, Provincia) → Tasa}
unemployment_dict = df_unemployment.set_index(['Ano', 'Codigo_Provincia'])['Total'].to_dict()

# 🔹 Función para asignar la tasa de desempleo
def asignar_desempleo(row):
    key = (row['Ano'], row['Provincia'])
    
    # Si el año es 2019a o 2019b, usar los datos de 2019
    if key[0] in ["2019a", "2019b"]:
        return unemployment_dict.get(("2019", key[1]), None)
    
    return unemployment_dict.get(key, None)

# 🔹 Llenar la columna 'Tasa Desempleo'
df_main['Tasa Desempleo'] = df_main.apply(asignar_desempleo, axis=1)

# 📂 Guardar el CSV modificado
df_main.to_csv('16_tasa_desempleo.csv', index=False)

print("✅ La columna 'Tasa Desempleo' ha sido rellenada correctamente en '16_tasa_desempleo.csv'.")
