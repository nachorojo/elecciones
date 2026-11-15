import pandas as pd

# Cargar los CSVs
csv_votos = 'esperanza.csv'
csv_habitantes = 'poblacion.csv'

votos_df = pd.read_csv(csv_votos)
habitantes_df = pd.read_csv(csv_habitantes, sep=';', encoding='latin1')

# Limpiar y convertir datos
habitantes_df['Periodo'] = habitantes_df['Periodo'].astype(int)
habitantes_df['Total'] = pd.to_numeric(habitantes_df['Total'].str.replace('.', '').str.replace(',', '.'), errors='coerce')

# Crear diccionario de habitantes por provincia
habitantes_dict = {}
for _, row in habitantes_df.iterrows():
    codigo_provincia = row['Provincias'][:2]  # Los dos primeros dígitos son el código de provincia
    habitantes_dict[(row['Periodo'], codigo_provincia)] = row['Total']

def asignar_habitantes(row):
    anio = row['Año']
    prov = str(row['Provincia']).zfill(2)
    return habitantes_dict.get((anio, prov), None)

votos_df['Habitantes Provincia'] = votos_df.apply(asignar_habitantes, axis=1)
votos_df.to_csv('habitantes.csv', index=False)

print("CSV actualizado guardado como 'habitantes.csv'")