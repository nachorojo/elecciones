import pandas as pd

# Cargar los CSVs
df_main = pd.read_csv('main.csv')
df_unemployment = pd.read_csv('unemployment.csv', sep=';')

# Limpiar y procesar el CSV de desempleo
df_unemployment['Codigo_Provincia'] = df_unemployment['Provincias'].str.extract(r'(\d{2})')
df_unemployment['Ano'] = df_unemployment['Periodo'].str.extract(r'(\d{4})').astype(int)
df_unemployment['Total'] = df_unemployment['Total'].str.replace(',', '.').astype(float)

# Convertir la columna Ano en df_main a entero
df_main['Ano'] = df_main['Ano'].astype(int)
df_main['Provincia'] = df_main['Provincia'].astype(str).str.zfill(2)

# Crear un diccionario de tasas de desempleo
unemployment_dict = df_unemployment.set_index(['Ano', 'Codigo_Provincia'])['Total'].to_dict()

# Llenar la columna Tasa Desempleo en df_main
df_main['Tasa Desempleo'] = df_main.apply(lambda row: unemployment_dict.get((row['Ano'], row['Provincia']), None), axis=1)

# Guardar el CSV resultante
df_main.to_csv('main_completed.csv', index=False)
