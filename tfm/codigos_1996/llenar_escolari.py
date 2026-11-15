import pandas as pd

# Cargar los CSVs
csv_votos = 'edad_media.csv'  # CSV original a completar
csv_educacion = 'educ019.csv'  # CSV de escolarización

# Diccionario de códigos a provincias
codigo_a_provincia = {
    "01": "Álava", "02": "Albacete", "03": "Alicante/Alacant", "04": "Almería", "05": "Ávila",
    "06": "Badajoz", "07": "Balears,Illes", "08": "Barcelona", "09": "Burgos", "10": "Cáceres",
    "11": "Cádiz", "12": "Castellón/Castelló", "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña",
    "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Guipúzcoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León", "25": "Lleida",
    "26": "Rioja, La", "27": "Lugo", "28": "Madrid, Comunidad de", "29": "Málaga", "30": "Murcia, Región de",
    "31": "Navarra, Comunidad Foral", "32": "Ourense", "33": "Asturias, Ppado de", "34": "Palencia", "35": "Las Palmas",
    "36": "Pontevedra", "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
    "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona", "44": "Teruel",
    "45": "Toledo", "46": "Valencia/València", "47": "Valladolid", "48": "Vizcaya", "49": "Zamora",
    "50": "Zaragoza", "51": "Ceuta", "52": "Melilla"
}

# Cargar los datos
votos_df = pd.read_csv(csv_votos)
educacion_df = pd.read_csv(csv_educacion, sep=';', encoding='latin1')

# Limpiar y convertir datos
educacion_df['años'] = educacion_df['años'].astype(int)
educacion_df['Total'] = pd.to_numeric(educacion_df['Total'].str.replace(',', '.'), errors='coerce')


# Crear un diccionario de escolarización
esc_dict = {}
for _, row in educacion_df.iterrows():
    clave = (row['años'], row['Comunidad Autónoma y Provincia'])
    esc_dict[clave] = 100 - row['Total']

# Asignar los valores de escolarización
def asignar_escolarizacion(row):
    anio = row['Año']
    prov = codigo_a_provincia.get(str(row['Provincia']).zfill(2), None)
    if prov is not None:
        return esc_dict.get((anio, prov), None)
    return None

votos_df['Escolarizacion'] = votos_df.apply(asignar_escolarizacion, axis=1)

# Guardar el CSV actualizado
votos_df.to_csv('escolarizacion_bueno.csv', index=False)

print("CSV actualizado guardado como 'escolarizacion_bueno.csv'")