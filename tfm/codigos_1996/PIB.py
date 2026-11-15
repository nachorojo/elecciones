import pandas as pd

# Cargar el CSV con PIB per cápita
pib_df = pd.read_csv('pib.csv', sep=',')
pib_df.set_index('Provincia', inplace=True)

# Convertir columnas de PIB al formato numérico
pib_df = pib_df.applymap(lambda x: float(str(x).replace(',', '.')))

# Cargar el CSV que debe ser modificado
datos_df = pd.read_csv('datos.csv')

# Rellenar la columna 'PIB per capita de Provincia' coincidiendo año y provincia
for index, row in datos_df.iterrows():
    ano = str(row['Ano'])
    provincia = str(row['Provincia']).zfill(2)  # Asegura que el código de provincia tenga dos dígitos
    if provincia in pib_df.index and ano in pib_df.columns:
        datos_df.at[index, 'PIB per capita'] = pib_df.loc[provincia, ano]

# Guardar el CSV modificado
datos_df.to_csv('datos_actualizado.csv', index=False)

print("La columna 'PIB per capita de Provincia' ha sido rellenada correctamente.")
