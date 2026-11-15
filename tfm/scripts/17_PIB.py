import pandas as pd

# 📌 Cargar el CSV con PIB per cápita
pib_df = pd.read_csv('../ine/PIB.csv', sep=',', dtype=str)

# 📌 Asegurar que la columna 'Provincia' es string con dos dígitos
pib_df['Provincia'] = pib_df['Provincia'].astype(str).str.zfill(2)

# 📌 Convertir las columnas de PIB al formato numérico eliminando comas de miles
for col in pib_df.columns[1:]:  # Omitir la columna 'Provincia'
    pib_df[col] = pib_df[col].str.replace(',', '').astype(float)

# 📌 Configurar índice en provincia para acceso más rápido
pib_df.set_index('Provincia', inplace=True)

# 📌 Cargar el CSV que debe ser modificado
datos_df = pd.read_csv('17_criminalidad.csv', dtype={'Ano': str})

# 📌 Asegurar que 'Provincia' es string con dos dígitos
datos_df['Provincia'] = datos_df['Provincia'].astype(str).str.zfill(2)

# 📌 Función para obtener el PIB per cápita correcto
def obtener_pib(row):
    provincia = row['Provincia']
    año = row['Ano']

    # Si el año es 2019a o 2019b, usar el PIB de 2019
    if año in ['2019a', '2019b']:
        return pib_df.loc[provincia, '2019'] if provincia in pib_df.index else None

    # Si el año está en las columnas del PIB, asignarlo
    if provincia in pib_df.index and año in pib_df.columns:
        return pib_df.loc[provincia, año]

    return None

# 📌 Asignar valores de PIB per cápita
datos_df['PIB per capita'] = datos_df.apply(obtener_pib, axis=1)

# 📌 Verificar filas sin PIB asignado
filas_sin_pib = datos_df[datos_df['PIB per capita'].isna()]
if not filas_sin_pib.empty:
    print("⚠️ Provincias sin PIB asignado (mostrando 50 ejemplos):")
    print(filas_sin_pib[['Provincia', 'Ano']].head(50))  

# 📌 Guardar el CSV modificado
datos_df.to_csv('18_PIB.csv', index=False)

print("✅ La columna 'PIB per capita' ha sido rellenada correctamente en '18_PIB.csv'.")
