import pandas as pd

# 📌 Cargar el CSV con los porcentajes de mujeres
df_mujeres = pd.read_csv('12_mujeres_por_año.csv', sep=';', encoding='latin1', dtype={"Ano": str})

# 🔹 Normalizar los nombres de las columnas
df_mujeres.columns = df_mujeres.columns.str.strip()

# 🔹 Asegurar que 'Provincia' tiene dos caracteres
df_mujeres['Provincia'] = df_mujeres['Provincia'].astype(str).str.zfill(2)

# 🔹 Crear un diccionario con (provincia, año) → porcentaje de mujeres
mujeres_dict = {
    (prov, year): perc for prov, year, perc in zip(df_mujeres['Provincia'], df_mujeres['Ano'], df_mujeres['%mujeres'])
}

# 📌 Cargar el CSV principal asegurando que 'Ano' se lea como string
df_votos = pd.read_csv('11_acceso_a_internet.csv', sep=',', encoding='latin1', dtype={"Ano": str}, low_memory=False)

# 🔹 Normalizar los nombres de las columnas
df_votos.columns = df_votos.columns.str.strip()

# 🔹 Asegurar que 'Provincia' tiene dos caracteres
df_votos['Provincia'] = df_votos['Provincia'].astype(str).str.zfill(2)

# 🔹 Asegurar que 'Ano' es string
df_votos['Ano'] = df_votos['Ano'].astype(str)

# 🔹 Función para obtener el porcentaje de mujeres
def obtener_porcentaje(provincia, año):
    if año == '1996':  # Casos específicos con años faltantes
        return mujeres_dict.get((provincia, '1998'), None)
    if año in ['2019a', '2019b']:  # Casos de 2019a y 2019b → usar datos de 2019
        return mujeres_dict.get((provincia, '2019'), None)
    return mujeres_dict.get((provincia, año), None)

# 🔹 Asignar valores al dataframe principal
df_votos['% de mujeres'] = df_votos.apply(lambda row: obtener_porcentaje(row['Provincia'], row['Ano']), axis=1)

# 📂 Guardar el CSV actualizado
df_votos.to_csv('13_%mujeres.csv', index=False, encoding='latin1')

print("✅ CSV '13_%mujeres.csv' generado con éxito.")
