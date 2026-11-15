import pandas as pd

# Cargar el CSV con las tasas de pobreza
pobreza_df = pd.read_csv('tasa_pobreza.csv', sep=';')
pobreza_df['Autonomous Communities and Cities'] = pobreza_df['Autonomous Communities and Cities'].str.strip()
pobreza_df['Period'] = pobreza_df['Period'].astype(str)

# Crear un diccionario para mapear (comunidad, año) -> tasa de pobreza
pobreza_dict = {(row['Autonomous Communities and Cities'].split()[0], row['Period']): row['Total'] for _, row in pobreza_df.iterrows()}

# Cargar el CSV que debe ser modificado
datos_df = pd.read_csv('inmigracion_f.csv')

# Llenar la columna 'Tasa de Pobreza' usando el diccionario
for index, row in datos_df.iterrows():
    key = (str(row['Comunidad']).zfill(2), str(row['Ano']))
    if key in pobreza_dict:
        datos_df.at[index, 'Tasa de Pobreza'] = pobreza_dict[key]

# Guardar el CSV modificado
datos_df.to_csv('pobreza.csv', index=False)

print("La columna 'Tasa de Pobreza' ha sido rellenada correctamente.")
