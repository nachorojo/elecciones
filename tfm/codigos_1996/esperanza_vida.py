import pandas as pd

# Cargar los CSVs
csv_votos = 'escolarizacion_bueno.csv'
csv_esperanza = 'esperanzaVida.csv'

votos_df = pd.read_csv(csv_votos)
esperanza_df = pd.read_csv(csv_esperanza, sep=';', encoding='latin1')

# Limpiar y convertir datos
esperanza_df['Periodo'] = esperanza_df['Periodo'].astype(int)
esperanza_df['Total'] = pd.to_numeric(esperanza_df['Total'].str.replace(',', '.'), errors='coerce')

# Crear diccionario de esperanza de vida
esperanza_dict = {}
for _, row in esperanza_df.iterrows():
    codigo_provincia = row['Provincias'][:2]  # Los dos primeros dígitos son el código de provincia
    esperanza_dict[(row['Periodo'], codigo_provincia)] = row['Total']

def asignar_esperanza(row):
    anio = row['Año']
    prov = str(row['Provincia']).zfill(2)
    return esperanza_dict.get((anio, prov), None)

votos_df['Esperanza de Vida'] = votos_df.apply(asignar_esperanza, axis=1)
votos_df.to_csv('esperanza.csv', index=False)

print("CSV actualizado guardado como 'esperanza.csv'")