"""
VALIDACIÓN DE DATOS 
"""
import pandas as pd
import numpy as np

def validar_csv(filepath):
    """
    Valida el archivo CSV de entrada
    """
    print("Validando datos")
    
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado: {filepath}")
        return False
    
    # 1. Verificar columnas obligatorias
    columnas_requeridas = ['date', 'ndvi', 'evi', 'lst', 'tmax', 'tmin', 'soil_humidity']
    
    faltantes = set(columnas_requeridas) - set(df.columns)
    if faltantes:
        print(f"Eror: Faltan columnas: {faltantes}")
        return False
    
    print(f"Todas las columnas presentes")
    
    # 2. Verificar que hay datos
    if len(df) < 100:
        print(f"⚠️  ADVERTENCIA: Solo {len(df)} registros. Se recomienda al menos 100.")
    else:
        print(f"✅ {len(df)} registros encontrados")
    
    # 3. Validar rangos de valores
    validaciones = {
        'ndvi': (-1, 1),
        'evi': (0, 1),
    }
    
    errores = []
    for col, (min_val, max_val) in validaciones.items():
        fuera_rango = df[(df[col] < min_val) | (df[col] > max_val)]
        if len(fuera_rango) > 0:
            errores.append(f"{col}: {len(fuera_rango)} valores fuera de rango [{min_val}, {max_val}]")
    
    # 4. Verificar valores nulos
    nulos = df[columnas_requeridas].isnull().sum()
    if nulos.sum() > 0:
        print("\nValores nulos encontrados:")
        print(nulos[nulos > 0])
        print("\nSe eliminarán automáticamente en el siguiente paso.")
    
    # 5. Estadísticas básicas
    print("\nResumen de datos:")
    print(f"Total registros: {len(df)}")
    try:
        df['date'] = pd.to_datetime(df['date'])
        print(f"Rango fechas: {df['date'].min()} a {df['date'].max()}")
    except:
        print("No se pudo transformar de tipo de dato la columna 'date'")
    
    if errores:
        print("\nADVERTENCIAS:")
        for e in errores:
            print(f"{e}")
    
    print("\nValidación completada")
    return True


if __name__ == "__main__":
    # Ejecutar validación
    archivo = 'data/datos_crudos.csv'
    
    if validar_csv(archivo):
        print(f"\nArchivo listo para procesamiento")
        print(f"Siguiente paso: python src/2_ingenieria_features.py")
    else:
        print(f"\nCorrige los errores antes de continuar")