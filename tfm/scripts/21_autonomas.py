import pandas as pd

# 📌 Mapeo de códigos de comunidad a nombres oficiales
mapa_comunidades = {
    "1": "Andalucía",
    "2": "Aragón",
    "3": "Asturias",
    "4": "Cantabria",
    "5": "Castilla-La Mancha",
    "6": "Castilla y León",
    "7": "Cataluña",
    "8": "Extremadura",
    "9": "Galicia",
    "10": "Comunidad de Madrid",
    "11": "Región de Murcia",
    "12": "Navarra",
    "13": "La Rioja",
    "14": "País Vasco",
    "15": "Ceuta",
    "16": "Melilla",
    "17": "Comunidad Valenciana",
    "18": "Canarias",
    "19": "Islas Baleares"
}

# 📌 Cargar el CSV con los gobiernos autonómicos
gobiernos_df = pd.read_csv('21_periodos_con_ideologia.csv', sep=',', dtype=str)

# 📌 Asegurar que las columnas "Inicio" y "Fin" sean numéricas, manejando 'en el cargo'
gobiernos_df['Inicio'] = pd.to_numeric(gobiernos_df['Inicio'], errors='coerce')
gobiernos_df['Fin'] = pd.to_numeric(gobiernos_df['Fin'], errors='coerce').fillna(2024)  # Si es "en el cargo", asumir 2024

# 📌 Cargar el CSV principal
datos_df = pd.read_csv('20_gobierno_actual.csv', sep=',', dtype=str)

# 📌 Convertir 'Ano' a numérico, normalizando 2019a y 2019b
datos_df['Ano'] = datos_df['Ano'].replace({'2019a': '2019', '2019b': '2019'})
datos_df['Ano'] = pd.to_numeric(datos_df['Ano'], errors='coerce')

# 📌 Reemplazar los códigos de comunidad por sus nombres
datos_df['Comunidad_Nombre'] = datos_df['Comunidad'].map(mapa_comunidades)

# 📌 Crear un diccionario (comunidad, año) -> partido gobernante
gobierno_dict = {}

for _, row in gobiernos_df.iterrows():
    autonomia = row['Autonomía'].strip()  # Asegurar que los nombres sean comparables
    partido = row['Partido']
    
    for año in range(int(row['Inicio']), int(row['Fin']) + 1):
        gobierno_dict[(autonomia, año)] = partido

# 📌 Función para asignar el gobierno correcto
def obtener_gobierno(row):
    comunidad = row['Comunidad_Nombre']
    año = row['Ano']
    return gobierno_dict.get((comunidad, año), None)

# 📌 Asignar valores de Gobierno Actual de Comunidad
datos_df['Gobierno Actual de Comunidad'] = datos_df.apply(obtener_gobierno, axis=1)

# 📌 Verificar si hay valores no asignados
provincias_faltantes = datos_df[datos_df['Gobierno Actual de Comunidad'].isna()][['Comunidad', 'Ano']]
if not provincias_faltantes.empty:
    print("⚠️ Algunas comunidades no tienen gobierno asignado:")
    print(provincias_faltantes.drop_duplicates())

# 📌 Guardar el CSV modificado
datos_df.to_csv('22_FINAL_DB.csv', index=False)

print("✅ La columna 'Gobierno Actual de Comunidad' ha sido rellenada correctamente en '22_FINAL_DB.csv'.")
