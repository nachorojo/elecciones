import pandas as pd

csv_votos = '07_edad_media.csv'  
csv_educacion = '../ine/educ019.csv'  

codigo_a_provincia = {
    "01": "Alava", "02": "Albacete", "03": "Alicante/Alacant", "04": "Almeria", "05": "Avila",
    "06": "Badajoz", "07": "Balears,Illes", "08": "Barcelona", "09": "Burgos", "10": "Caceres",
    "11": "Cadiz", "12": "Castellon/Castello", "13": "Ciudad Real", "14": "Cordoba", "15": "A Corunia",
    "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Guipuzcoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaen", "24": "Leon", "25": "Lleida",
    "26": "Rioja, La", "27": "Lugo", "28": "Madrid, Comunidad de", "29": "Malaga", "30": "Murcia, Region de",
    "31": "Navarra, Comunidad Foral", "32": "Ourense", "33": "Asturias, Ppado de", "34": "Palencia", "35": "Las Palmas",
    "36": "Pontevedra", "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
    "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona", "44": "Teruel",
    "45": "Toledo", "46": "Valencia/Valencia", "47": "Valladolid", "48": "Vizcaya", "49": "Zamora",
    "50": "Zaragoza", "51": "Ceuta", "52": "Melilla"
}

votos_df = pd.read_csv(csv_votos, dtype={"Ano": str}, low_memory=False)
educacion_df = pd.read_csv(csv_educacion, sep=';', encoding='latin1')

# Limpiar y convertir datos
educacion_df['anios'] = educacion_df['anios'].astype(str)
educacion_df['Total'] = pd.to_numeric(educacion_df['Total'].str.replace(',', '.'), errors='coerce')

# Crear un diccionario de escolarización
esc_dict = {}
for _, row in educacion_df.iterrows():
    clave = (row['anios'], row['Comunidad Autonoma y Provincia'])
    esc_dict[clave] = 100 - row['Total']

# Asignar los valores de escolarización
def asignar_escolarizacion(row):
    anio = row['Ano']
    prov = codigo_a_provincia.get(str(row['Provincia']).zfill(2), None)
    if prov is not None:
        # Si el año es 2019a o 2019b, usar los datos de 2029
        return esc_dict.get(("2019", prov), None) if anio in ["2019a", "2019b"] else esc_dict.get((anio, prov), None)
    return None

votos_df['Escolarizacion'] = votos_df.apply(asignar_escolarizacion, axis=1)

# Guardar el CSV actualizado
votos_df.to_csv('08_escolarizacion.csv', index=False)

print("✅ CSV actualizado guardado como '08_escolarizacion.csv'")
