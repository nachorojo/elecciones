import pandas as pd

# Cargar el CSV con los porcentajes de mujeres
df_mujeres = pd.read_csv('poblacion_mujeres.csv', sep=';', encoding='latin1')
df_mujeres.columns = [col.encode('latin1').decode('utf-8').strip() for col in df_mujeres.columns]
if 'Año' not in df_mujeres.columns:
    for col in df_mujeres.columns:
        if 'A' in col and 'o' in col:
            df_mujeres.rename(columns={col: 'Año'}, inplace=True)

df_mujeres['Provincia'] = df_mujeres['Provincias'].str[:2]
df_mujeres['Año'] = df_mujeres['Año'].astype(str)

mujeres_dict = {
    (prov, year): perc for prov, year, perc in zip(df_mujeres['Provincia'], df_mujeres['Año'], df_mujeres['%mujeres'])
}

# Cargar el CSV principal
df_votos = pd.read_csv('acceso_a_internet.csv', sep=',', encoding='latin1')
df_votos.columns = [col.encode('latin1').decode('utf-8').strip() for col in df_votos.columns]
if 'Año' not in df_votos.columns:
    for col in df_votos.columns:
        if 'A' in col and 'o' in col:
            df_votos.rename(columns={col: 'Año'}, inplace=True)

df_votos['Provincia'] = df_votos['Provincia'].astype(str).str.zfill(2)
df_votos['Año'] = df_votos['Año'].astype(str)

def obtener_porcentaje(provincia, año):
    if año == '1996':
        return mujeres_dict.get((provincia, '1998'), None)
    return mujeres_dict.get((provincia, año), None)

df_votos['% de mujeres'] = df_votos.apply(lambda row: obtener_porcentaje(row['Provincia'], row['Año']), axis=1)

# df_votos['% de mujeres'] = df_votos.apply(lambda row: mujeres_dict.get((row['Provincia'], str(int(row['Año']) + 2)), None), axis=1)

df_votos.to_csv('%mujeres.csv', index=False, encoding='latin1')
print("✅ CSV '%mujeres.csv' generado con éxito.")
