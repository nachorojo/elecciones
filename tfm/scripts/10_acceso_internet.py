import pandas as pd

# Cargar los CSVs asegurando que 'Ano' se lea como string
df_main = pd.read_csv('10_habitantes.csv', dtype={"Ano": str}, low_memory=False)
df_internet = pd.read_csv('../ine/viviendas_con_internet.csv', sep=';', encoding='latin1')

# Diccionario de códigos de comunidad a nombres
comunidades = {
    "01": "Andalucia", "02": "Aragon", "03": "Asturias", "04": "Islas Baleares",
    "05": "Canarias", "06": "Cantabria", "07": "Castilla-La Mancha", "08": "Castilla y Leon",
    "09": "Catalunia", "10": "Extremadura", "11": "Galicia", "12": "Comunidad de Madrid",
    "13": "Navarra", "14": "Pais Vasco", "15": "Region de Murcia", "16": "La Rioja",
    "17": "Comunidad Valenciana", "18": "Ceuta", "19": "Melilla"
}

# Asegurar que 'Ano' sea string en df_internet
df_internet['Ano'] = df_internet['Ano'].astype(str)

# Convertir 'Total' a número reemplazando ',' por '.'
df_internet['Total'] = pd.to_numeric(df_internet['Total'].str.replace(',', '.'), errors='coerce')

# Crear un diccionario de acceso a Internet {(año, comunidad) → porcentaje}
internet_mapping = {
    (row['Ano'], row['Comunidades y Ciudades Autonomas']): row['Total']
    for _, row in df_internet.iterrows()
}

# Función para asignar el acceso a Internet
def map_internet(row):
    anio = row['Ano']
    comunidad_codigo = str(row['Comunidad']).zfill(2)

    # Obtener el nombre de la comunidad
    comunidad_nombre = comunidades.get(comunidad_codigo, None)
    if comunidad_nombre is None:
        print(f"⚠️ Comunidad no encontrada para código: {comunidad_codigo}")
        return None

    # Si el año es 2019a o 2019b, usar los datos de 2019
    if anio in ["2019a", "2019b"]:
        return internet_mapping.get(("2019", comunidad_nombre), None)

    return internet_mapping.get((anio, comunidad_nombre), None)

# Asignar valores al dataframe principal
df_main['Acceso a Internet'] = df_main.apply(map_internet, axis=1)

# Guardar el nuevo CSV
df_main.to_csv('11_acceso_a_internet.csv', index=False)

print("✅ CSV actualizado guardado como '11_acceso_a_internet.csv'")
