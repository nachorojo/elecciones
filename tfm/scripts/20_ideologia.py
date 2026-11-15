import pandas as pd

# Cargar los CSVs
periodos_df = pd.read_csv('../ine/autonomas_gobierno.csv')
partidos_df = pd.read_csv('../csv/02_partidos_clasificados.csv')

# Crear un diccionario para mapear partidos a su clasificacion ideologica
clasificacion_dict = partidos_df.set_index('Siglas')['Clasificacion'].to_dict()

# Agregar la clasificacion al DataFrame de periodos
periodos_df['Clasificacion'] = periodos_df['Partido'].map(clasificacion_dict)

# Rellenar partidos no encontrados con un valor predeterminado
periodos_df['Clasificacion'].fillna('Desconocido', inplace=True)

# Crear la nueva columna combinando Clasificacion y Partido
periodos_df['Partido'] = periodos_df['Clasificacion'] + ' (' + periodos_df['Partido'] + ')'

# Eliminar la columna Clasificacion temporal
periodos_df.drop(columns=['Clasificacion'], inplace=True)

# Guardar el nuevo CSV
periodos_df.to_csv('periodos_con_ideologia.csv', index=False)

print("CSV generado correctamente como 'periodos_con_ideologia.csv'")
