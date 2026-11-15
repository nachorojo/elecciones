import pandas as pd

# Leer el CSV original, especificando el delimitador y manejando errores de codificación
df = pd.read_csv('mujeres_y_total.csv', sep=';', encoding='latin1')

# Filtrar solo las filas con 'TOTAL EDADES' y 'TOTAL'
df = df[(df['Edad (grupos quinquenales)'] == 'TOTAL EDADES') & (df['Espanoles/Extranjeros'] == 'TOTAL')]

# Convertir la columna 'Total' a numérico para evitar errores
df['Total'] = pd.to_numeric(df['Total'], errors='coerce')

# Crear un DataFrame pivotado con las columnas necesarias
pivot = df.pivot_table(index=['Provincias', 'Edad (grupos quinquenales)', 'Espanoles/Extranjeros', 'Ano'],
                       columns='Sexo', values='Total', aggfunc='sum').reset_index()

# Verificar si hay valores de 'Ambos sexos' igual a 0 para evitar divisiones por cero
pivot = pivot[pivot['Ambos sexos'] != 0]

# Calcular el porcentaje de mujeres
pivot['%mujeres'] = (pivot['Mujeres'] / pivot['Ambos sexos']) * 100

# Seleccionar las columnas requeridas
final_df = pivot[['Provincias', 'Edad (grupos quinquenales)', 'Espanoles/Extranjeros', 'Ano', '%mujeres']]

# Guardar el resultado en un nuevo CSV
final_df.to_csv('poblacion_mujeres.csv', sep=';', index=False, encoding='latin1')

print("CSV generado con éxito como 'poblacion_mujeres.csv'")