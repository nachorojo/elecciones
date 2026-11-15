import pandas as pd
import unidecode

# Cargar el CSV original
df = pd.read_csv('../ine/mujeres_y_total.csv', sep=';', encoding='latin1')

# Limpiar nombres de columnas
df.columns = df.columns.str.strip()

# Normalizar valores clave eliminando espacios y caracteres especiales
df['Edad (grupos quinquenales)'] = df['Edad (grupos quinquenales)'].str.strip()
df['Espanoles/Extranjeros'] = df['Espanoles/Extranjeros'].str.strip()
df['Sexo'] = df['Sexo'].str.strip()
df['Provincias'] = df['Provincias'].str.strip().apply(lambda x: unidecode.unidecode(str(x)))

# Extraer código de provincia correctamente
df['Provincia'] = df['Provincias'].str.extract(r'(^\d{2})', expand=False).str.zfill(2)

# Filtrar solo 'TOTAL EDADES' y 'TOTAL' en columnas clave
df = df[(df['Edad (grupos quinquenales)'] == 'TOTAL EDADES') & (df['Espanoles/Extranjeros'] == 'TOTAL')]

# 🔹 Solución: Limpiar los valores en 'Total'
df['Total'] = df['Total'].astype(str).str.replace('.', '', regex=False)  # Eliminar separadores de miles
df['Total'] = df['Total'].str.replace(',', '.', regex=False)  # Reemplazar ',' por '.' para decimales
df['Total'] = pd.to_numeric(df['Total'], errors='coerce')  # Convertir a float

# 🔍 Verificar valores nulos en 'Total' después de la conversión
print("⚠️ Filas con 'Total' nulo después de la limpieza:")
print(df[df['Total'].isna()].head())

# Asegurar que todas las provincias tengan datos de "Ambos sexos" y "Mujeres"
prov_sexos = df.groupby(['Provincia', 'Sexo'])['Total'].count().unstack()
provincias_faltantes = list(prov_sexos[prov_sexos.isna().any(axis=1)].index)

print(f"⚠️ Provincias sin datos de 'Ambos sexos' o 'Mujeres': {provincias_faltantes}")

# Crear un DataFrame pivotado con las columnas necesarias
pivot = df.pivot_table(index=['Provincia', 'Ano'], columns='Sexo', values='Total', aggfunc='sum').reset_index()

# Asegurar que 'Ambos sexos' no sea 0 para evitar divisiones por cero
pivot = pivot[pivot['Ambos sexos'] > 0]

# Calcular el porcentaje de mujeres
pivot['%mujeres'] = (pivot['Mujeres'] / pivot['Ambos sexos']) * 100

# Seleccionar columnas requeridas
final_df = pivot[['Provincia', 'Ano', '%mujeres']]

# Verificar provincias después de la pivotación
provincias_faltantes_post = set(df['Provincia'].unique()) - set(final_df['Provincia'].unique())
print(f"⚠️ Provincias faltantes en el resultado final: {provincias_faltantes_post}")

# Guardar el resultado en un nuevo CSV
final_df.to_csv('12_mujeres_por_año.csv', sep=';', index=False, encoding='latin1')

print("✅ CSV generado con éxito como '12_mujeres_por_año.csv'")
