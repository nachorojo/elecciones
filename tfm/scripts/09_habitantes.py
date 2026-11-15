import pandas as pd

# Cargar los CSVs
csv_votos = '09_esperanza_vida.csv'
csv_habitantes = '../ine/poblacion.csv'

# Asegurar que 'Ano' se lea como string para evitar problemas con tipos mezclados
votos_df = pd.read_csv(csv_votos, dtype={"Ano": str}, low_memory=False)
habitantes_df = pd.read_csv(csv_habitantes, sep=';', encoding='latin1')

# Limpiar y convertir datos
habitantes_df['Periodo'] = habitantes_df['Periodo'].astype(str)  # Convertir a string para coincidencia
habitantes_df['Total'] = pd.to_numeric(habitantes_df['Total'].str.replace('.', '').str.replace(',', '.'), errors='coerce')

# Crear diccionario de habitantes por provincia
habitantes_dict = {
    (row['Periodo'], row['Provincias'][:2]): row['Total']
    for _, row in habitantes_df.iterrows()
}

# Asignar los valores de habitantes
def asignar_habitantes(row):
    anio = row['Ano']
    prov = str(row['Provincia']).zfill(2)

    # Si el año es 2019a o 2019b, usar los datos de 2019
    if anio in ["2019a", "2019b"]:
        return habitantes_dict.get(("2019", prov), None)
    
    return habitantes_dict.get((anio, prov), None)

votos_df['Habitantes Provincia'] = votos_df.apply(asignar_habitantes, axis=1)

# Guardar el CSV actualizado
votos_df.to_csv('10_habitantes.csv', index=False)

print("✅ CSV actualizado guardado como '10_habitantes.csv'")
