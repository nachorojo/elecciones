import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Cargar datos
df = pd.read_csv("22_FINAL_DB.csv")

# Mostrar primeras filas
print("Primeras filas del dataset:")
print(df.head(), "\n")

# Información general
print("Información general:")
print(df.info(), "\n")

# Estadísticas descriptivas
print("Estadísticas descriptivas:")
print(df.describe(include='all'), "\n")

# Verificar valores nulos
print("Valores nulos por columna:")
print(df.isnull().sum(), "\n")

# Eliminar columnas con más del 50% de nulos
df = df.dropna(axis=1, thresh=0.5 * len(df))

# Rellenar nulos numéricos con la media
df.fillna(df.mean(numeric_only=True), inplace=True)

# Columnas numéricas
numericas = df.select_dtypes(include='number').columns

# Boxplots para outliers
print("Generando boxplots...")
for col in numericas:
    plt.figure()
    sns.boxplot(x=df[col])
    plt.title(f'Boxplot de {col}')
    plt.savefig(f'boxplot_{col}.png')
    plt.close()

# Histogramas de distribución
print("Generando histogramas...")
for col in numericas:
    plt.figure()
    sns.histplot(df[col], kde=True)
    plt.title(f'Distribución de {col}')
    plt.savefig(f'distribucion_{col}.png')
    plt.close()

# Matriz de correlación
print("Generando mapa de calor de correlación...")
plt.figure(figsize=(12, 8))
sns.heatmap(df[numericas].corr(), annot=True, cmap='coolwarm')
plt.title("Matriz de correlación")
plt.savefig("correlacion_heatmap.png")
plt.close()

# Ejemplo: PIB per capita vs Votos Derecha
if 'PIB per capita' in df.columns and 'Votos Derecha' in df.columns:
    plt.figure()
    sns.scatterplot(x='PIB per capita', y='Votos Derecha', data=df)
    plt.title('PIB per cápita vs Votos Derecha')
    plt.savefig('pib_vs_votos_derecha.png')
    plt.close()

# Ejemplo: Tasa de Pobreza por Candidatura Ganadora
if 'Tasa de Pobreza' in df.columns and 'Candidatura Ganadora' in df.columns:
    plt.figure()
    sns.boxplot(x='Candidatura Ganadora', y='Tasa de Pobreza', data=df)
    plt.xticks(rotation=45)
    plt.title('Tasa de Pobreza por Candidatura Ganadora')
    plt.savefig('pobreza_vs_candidatura.png')
    plt.close()

print("Análisis exploratorio completado. Gráficas guardadas como archivos PNG.")
