import pandas as pd

# 📌 Cargar los datos de los CSV
mujeres = pd.read_csv('13_%mujeres.csv', sep=',', encoding='latin1', dtype={"Ano": str})
inmigracion = pd.read_csv('../ine/inmigracion.csv', sep=';', encoding='latin1', dtype={"Ano": str})

# 🔹 Limpiar nombres de columnas
mujeres.columns = mujeres.columns.str.strip()
inmigracion.columns = inmigracion.columns.str.strip()

# 🔹 Asegurar que 'Provincia' tiene dos caracteres
mujeres['Provincia'] = mujeres['Provincia'].astype(str).str.zfill(2)
inmigracion['Codigo_Provincia'] = inmigracion['Provincias'].str[:2]  # Extraer los 2 primeros caracteres

# 🔹 Filtrar solo registros de 'TOTAL EXTRANJEROS' y 'Ambos sexos'
inmigracion = inmigracion[
    (inmigracion['Nacionalidad'].str.strip() == 'TOTAL EXTRANJEROS') &
    (inmigracion['Sexo'].str.strip() == 'Ambos sexos')
]

# 🔹 Limpiar 'Total' eliminando separadores de miles y convirtiéndolo a número
inmigracion['Total'] = pd.to_numeric(inmigracion['Total'].str.replace('.', '', regex=False), errors='coerce')

# 🔹 Crear un diccionario de inmigración {(año, provincia) → total}
inmigracion_dict = {
    (row['Ano'], row['Codigo_Provincia']): row['Total']
    for _, row in inmigracion.iterrows()
}

# 🔹 Función para asignar valores de inmigración
def asignar_inmigracion(row):
    anio = row['Ano']
    prov = row['Provincia']

    # Si el año es 2019a o 2019b, usar los datos de 2019
    if anio in ["2019a", "2019b"]:
        return inmigracion_dict.get(("2019", prov), None)
    
    return inmigracion_dict.get((anio, prov), None)

# 🔹 Asignar valores de inmigración
mujeres['Inmigracion'] = mujeres.apply(asignar_inmigracion, axis=1)

# 📂 Guardar el CSV actualizado
mujeres.to_csv('14_inmigracion.csv', index=False, sep=',', encoding='latin1')

print("✅ Archivo '14_inmigracion.csv' generado correctamente con los valores de inmigración actualizados.")
