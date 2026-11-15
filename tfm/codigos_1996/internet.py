import pandas as pd

# Cargar el CSV principal
df_main = pd.read_csv('habitantes.csv')

# Cargar el CSV secundario con el delimitador correcto
df_internet = pd.read_csv('viviendas_con_internet.csv', sep=';')

# Crear un diccionario para mapear el codigo de comunidad al acceso a internet
internet_mapping = {}
for index, row in df_internet.iterrows():
    codigo_comunidad = row['Comunidades y Ciudades Autonomas'][:2]  # Extraer los dos primeros digitos
    internet_mapping[codigo_comunidad] = float(row['Total'].replace(',', '.'))

# Rellenar la columna Acceso a Internet en el CSV principal
def map_internet(comunidad):
    codigo = str(comunidad).zfill(2)
    return internet_mapping.get(codigo, None)

df_main['Acceso a Internet'] = df_main['Comunidad'].apply(map_internet)

# Guardar el nuevo CSV
df_main.to_csv('acceso_a_internet.csv', index=False)
