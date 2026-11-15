import pandas as pd

# Cargar los datos de los CSV
mujeres = pd.read_csv('%mujeres.csv', sep=',', encoding='latin1')
inmigracion = pd.read_csv('inmigracion.csv', sep=';', encoding='latin1')

mujeres.columns = mujeres.columns.str.strip()
inmigracion.columns = inmigracion.columns.str.strip()

mujeres['Provincia'] = mujeres['Provincia'].astype(str).str.zfill(2)
inmigracion['Codigo_Provincia'] = inmigracion['Provincias'].str.extract(r'^(\d{2})')

inmigracion = inmigracion.dropna(subset=['Codigo_Provincia'])
mujeres['Ano'] = mujeres['Ano'].astype(str)
inmigracion['Ano'] = inmigracion['Ano'].astype(str)

inmigracion = inmigracion[(inmigracion['Nacionalidad'].str.strip() == 'TOTAL EXTRANJEROS') & (inmigracion['Sexo'].str.strip() == 'Ambos sexos')]

# Eliminar puntos de los números para convertir correctamente
inmigracion['Total'] = inmigracion['Total'].str.replace('.', '', regex=False).astype(int)

merged = pd.merge(mujeres, inmigracion[['Ano', 'Codigo_Provincia', 'Total']], left_on=['Ano', 'Provincia'], right_on=['Ano', 'Codigo_Provincia'], how='left')

merged['Inmigracion'] = merged['Total']

print("Valores únicos en Inmigracion después de asignar Total:")
print(merged['Inmigracion'].unique())

merged.drop(columns=['Codigo_Provincia', 'Total'], inplace=True)
merged.to_csv('inmigracion_f.csv', index=False, sep=',', encoding='latin1')

print("Archivo inmigracion_f.csv generado con la columna Inmigracion actualizada con el valor Total.")