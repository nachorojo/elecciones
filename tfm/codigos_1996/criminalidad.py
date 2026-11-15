import pandas as pd

# Cargar los CSVs
df_main = pd.read_csv('main.csv')
df_crime = pd.read_csv('crime.csv', sep=';')

# Procesar el CSV de criminalidad
df_crime['Codigo_Provincia'] = df_crime['Lugar de condena'].str.extract(r'(\d{2})')
df_crime['Ano'] = df_crime['Periodo'].astype(int)
df_crime['Total'] = df_crime['Total'].str.replace(',', '.').astype(float)

# Convertir la columna Ano en df_main a entero
df_main['Ano'] = df_main['Ano'].astype(int)
df_main['Provincia'] = df_main['Provincia'].astype(str).str.zfill(2)

# Crear un diccionario de criminalidad
crime_dict = df_crime.set_index(['Ano', 'Codigo_Provincia'])['Total'].to_dict()

# Llenar la columna Criminalidad en df_main
df_main['Criminalidad'] = df_main.apply(lambda row: crime_dict.get((row['Ano'], row['Provincia']), None), axis=1)

# Guardar el CSV resultante
df_main.to_csv('main_completed.csv', index=False)
