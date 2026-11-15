import pandas as pd

# Cargar los CSVs
csv_votos = '08_escolarizacion.csv'
csv_esperanza = '../ine/esperanzaVida.csv'

# Asegurar que 'Ano' se lea como string para evitar problemas con tipos mezclados
votos_df = pd.read_csv(csv_votos, dtype={"Ano": str}, low_memory=False)
esperanza_df = pd.read_csv(csv_esperanza, sep=';', encoding='latin1')

# Limpiar y convertir datos
esperanza_df['Periodo'] = esperanza_df['Periodo'].astype(str)  # Convertir a string para coincidencia
esperanza_df['Total'] = pd.to_numeric(esperanza_df['Total'].str.replace(',', '.'), errors='coerce')

# Crear un diccionario de esperanza de vida con clave (Periodo, Provincia)
esperanza_dict = {
    (row['Periodo'], row['Provincias'][:2]): row['Total']
    for _, row in esperanza_df.iterrows()
}

# Asignar los valores de esperanza de vida
def asignar_esperanza(row):
    anio = row['Ano']
    prov = str(row['Provincia']).zfill(2)

    # Si el año es 2019a o 2019b, usar los datos de 2019
    if anio in ["2019a", "2019b"]:
        return esperanza_dict.get(("2019", prov), None)
    
    return esperanza_dict.get((anio, prov), None)

votos_df['Esperanza de Vida'] = votos_df.apply(asignar_esperanza, axis=1)

# Guardar el CSV actualizado
votos_df.to_csv('09_esperanza_vida.csv', index=False)

print("✅ CSV actualizado guardado como '09_esperanza_vida.csv'")
