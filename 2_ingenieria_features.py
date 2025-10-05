"""
INGENIERÍA DE FEATURES - VERSIÓN SIMPLE
========================================
Genera features adicionales para el modelo de ML
"""
import pandas as pd
import numpy as np

def crear_features(df):
    """
    Crea features derivadas de los datos crudos
    """
    print("🔧 Creando features...")
    
    # Asegurar que date sea datetime (formato día/mes/año)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True, format='mixed')
    df = df.sort_values('date').reset_index(drop=True)
    
    # 1. FEATURES TEMPORALES (promedios móviles)
    ventanas = [7, 14]  # 7 y 14 días
    
    for ventana in ventanas:
        # NDVI
        df[f'ndvi_promedio_{ventana}d'] = df['ndvi'].rolling(window=ventana, min_periods=1).mean()
        df[f'ndvi_tendencia_{ventana}d'] = df['ndvi'].diff(ventana)
        
        # Humedad
        df[f'humedad_promedio_{ventana}d'] = df['soil_humidity'].rolling(window=ventana, min_periods=1).mean()
        df[f'humedad_tendencia_{ventana}d'] = df['soil_humidity'].diff(ventana)
        
        # Temperatura
        df[f'lst_max_{ventana}d'] = df['lst'].rolling(window=ventana, min_periods=1).max()
        df[f'tmax_promedio_{ventana}d'] = df['tmax'].rolling(window=ventana, min_periods=1).mean()
    
    # 2. RATIOS E ÍNDICES
    df['evi_ndvi_ratio'] = df['evi'] / (df['ndvi'] + 0.001)  # Evitar división por 0
    df['temp_promedio'] = (df['tmax'] + df['tmin']) / 2
    df['amplitud_termica'] = df['tmax'] - df['tmin']
    
    # 3. INDICADOR DE DÉFICIT (combinado)
    # Normalizar humedad (0-1, donde 0 es malo)
    humedad_norm = df['soil_humidity'] / 35.0
    humedad_norm = humedad_norm.clip(0, 1)
    
    # Normalizar temperatura (0-1, donde 0 es malo, temperaturas altas)
    temp_norm = (df['lst'] - 25) / 20
    temp_norm = temp_norm.clip(0, 1)
    
    # Déficit combinado (0-1, donde 1 es peor)
    df['deficit_combinado'] = (
        (1 - humedad_norm) * 0.5 +  # 50% peso humedad
        temp_norm * 0.3 +             # 30% peso temperatura
        (1 - df['ndvi']) * 0.2        # 20% peso NDVI
    ).clip(0, 1)
    
    # 4. FEATURES DE FECHA
    df['mes'] = df['date'].dt.month
    df['dia_año'] = df['date'].dt.dayofyear
    df['dias_desde_inicio'] = (df['date'] - df['date'].min()).dt.days
    
    # 5. GENERAR ETIQUETAS (TARGET) - Clasificación ajustada a datos reales
    # Basado en percentiles de tus datos para tener distribución equilibrada
    
    # Calcular percentiles para umbrales adaptativos
    p25_humedad = df['soil_humidity'].quantile(0.25)
    p50_humedad = df['soil_humidity'].quantile(0.50)
    p25_ndvi = df['ndvi'].quantile(0.25)
    p50_ndvi = df['ndvi'].quantile(0.50)
    p75_lst = df['lst'].quantile(0.75)
    
    print(f"\n📊 Umbrales calculados:")
    print(f"   Humedad - P25: {p25_humedad:.1f}, P50: {p50_humedad:.1f}")
    print(f"   NDVI - P25: {p25_ndvi:.2f}, P50: {p50_ndvi:.2f}")
    print(f"   LST - P75: {p75_lst:.1f}")
    
    df['estres_nivel'] = 0  # Sin estrés por defecto
    
    # Estrés MODERADO (condiciones intermedias)
    estres_moderado = (
        ((df['soil_humidity'] < p50_humedad) & (df['ndvi'] < p50_ndvi)) |
        ((df['deficit_combinado'] > 0.4) & (df['soil_humidity'] < p50_humedad)) |
        ((df['ndvi_tendencia_7d'] < -0.03) & (df['soil_humidity'] < p50_humedad))
    )
    df.loc[estres_moderado, 'estres_nivel'] = 1
    
    # Estrés SEVERO (condiciones críticas - 25% peor)
    estres_severo = (
        (df['soil_humidity'] < p25_humedad) |
        ((df['ndvi'] < p25_ndvi) & (df['soil_humidity'] < p50_humedad)) |
        ((df['lst'] > p75_lst) & (df['ndvi_tendencia_14d'] < -0.05))
    )
    df.loc[estres_severo, 'estres_nivel'] = 2
    
    # Mapeo a texto
    df['estres_etiqueta'] = df['estres_nivel'].map({
        0: 'sin_estres',
        1: 'estres_moderado',
        2: 'estres_severo'
    })
    
    return df


def procesar_datos(input_file, output_file):
    """
    Pipeline completo de procesamiento
    """
    print("📂 Cargando datos...")
    df = pd.read_csv(input_file)
    
    print(f"✅ {len(df)} registros cargados")
    
    # Eliminar filas con valores nulos
    df = df.dropna()
    print(f"✅ Después de limpiar: {len(df)} registros")
    
    # Crear features
    df = crear_features(df)
    
    # Resumen
    print("\n📊 Distribución de etiquetas:")
    print(df['estres_etiqueta'].value_counts())
    print(f"\nTotal features generados: {len(df.columns)}")
    
    # Guardar
    df.to_csv(output_file, index=False)
    print(f"\n💾 Datos procesados guardados en: {output_file}")
    
    return df


if __name__ == "__main__":
    # Ejecutar procesamiento
    df_procesado = procesar_datos(
        input_file='data/datos_crudos.csv',
        output_file='data/datos_procesados.csv'
    )
    
    print("\n✅ Procesamiento completado")
    print("   Siguiente paso: python src/3_entrenamiento_modelo.py")