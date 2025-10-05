"""
ENTRENAMIENTO DE MODELO 
=========================================
Entrena modelo de clasificación de estrés
"""
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

def entrenar_modelo(input_file, output_model):
    """
    Entrena el modelo de clasificación
    """
    print("🌱 Cargando datos procesados...")
    df = pd.read_csv(input_file)
    
    # Seleccionar features (X)
    features = [
        # Features originales
        'ndvi', 'evi', 'lst', 'tmax', 'tmin', 'soil_humidity',
        
        # Features temporales
        'ndvi_promedio_7d', 'ndvi_tendencia_7d',
        'ndvi_promedio_14d', 'ndvi_tendencia_14d',
        'humedad_promedio_7d', 'humedad_tendencia_7d',
        'humedad_promedio_14d', 'humedad_tendencia_14d',
        'lst_max_7d', 'lst_max_14d',
        'tmax_promedio_7d', 'tmax_promedio_14d',
        
        # Features derivados
        'evi_ndvi_ratio', 'temp_promedio', 'amplitud_termica',
        'deficit_combinado',
        
        # Features de fecha
        'mes', 'dia_año', 'dias_desde_inicio'
    ]
    
    # Preparar datos
    df_limpio = df.dropna(subset=features + ['estres_nivel'])
    
    X = df_limpio[features]
    y = df_limpio['estres_nivel']
    
    print(f"\n📊 Datos preparados:")
    print(f"   Muestras: {len(X)}")
    print(f"   Features: {len(features)}")
    print(f"\n   Distribución de clases:")
    print(y.value_counts().sort_index())
    
    # Verificar que hay al menos 2 clases
    clases_unicas = y.nunique()
    if clases_unicas < 2:
        print(f"\n⚠️  ADVERTENCIA: Solo hay {clases_unicas} clase(s) en los datos")
        print("   Los umbrales de estrés son muy estrictos o todos tus datos son similares.")
        print("   Ajustando umbrales para crear más diversidad...")
        return None
    
    # Split train/test (80/20) - solo si hay suficientes datos por clase
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        print("⚠️  No hay suficientes muestras por clase para split estratificado")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    
    print(f"\n   Train: {len(X_train)} | Test: {len(X_test)}")
    
    # Escalar features
    print("\n⚙️  Escalando features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Entrenar modelo
    print("🚀 Entrenando modelo Random Forest...")
    modelo = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    modelo.fit(X_train_scaled, y_train)
    print("✅ Modelo entrenado")
    
    # Evaluar
    print("\n📈 Evaluando modelo...")
    y_pred = modelo.predict(X_test_scaled)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n🎯 Accuracy: {accuracy:.3f}")
    
    print("\n📊 Reporte de clasificación:")
    target_names = ['Sin Estrés', 'Moderado', 'Severo']
    print(classification_report(y_test, y_pred, target_names=target_names, zero_division=0))
    
    # Matriz de confusión
    cm = confusion_matrix(y_test, y_pred)
    
    # Importancia de features
    importancias = pd.DataFrame({
        'feature': features,
        'importancia': modelo.feature_importances_
    }).sort_values('importancia', ascending=False)
    
    print("\n🎯 Top 10 Features más importantes:")
    print(importancias.head(10).to_string(index=False))
    
    # Visualizar resultados
    print("\n📊 Generando gráficos...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Matriz de confusión
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=target_names, yticklabels=target_names,
                ax=axes[0])
    axes[0].set_title('Matriz de Confusión', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Valor Real')
    axes[0].set_xlabel('Predicción')
    
    # Top 10 features
    top10 = importancias.head(10)
    axes[1].barh(range(len(top10)), top10['importancia'])
    axes[1].set_yticks(range(len(top10)))
    axes[1].set_yticklabels(top10['feature'])
    axes[1].set_xlabel('Importancia')
    axes[1].set_title('Top 10 Features', fontsize=14, fontweight='bold')
    axes[1].invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('outputs/resultados_modelo.png', dpi=300, bbox_inches='tight')
    print("✅ Gráficos guardados en: outputs/resultados_modelo.png")
    
    # Guardar modelo
    print(f"\n💾 Guardando modelo...")
    modelo_completo = {
        'modelo': modelo,
        'scaler': scaler,
        'features': features,
        'importancias': importancias
    }
    
    joblib.dump(modelo_completo, output_model)
    print(f"✅ Modelo guardado en: {output_model}")
    
    return modelo_completo


if __name__ == "__main__":
    # Entrenar modelo
    modelo = entrenar_modelo(
        input_file='data/datos_procesados.csv',
        output_model='models/modelo.pkl'
    )
    
    print("\n" + "="*60)
    print("✅ ENTRENAMIENTO COMPLETADO")
    print("="*60)
    print("\n💡 Para usar el modelo:")
    print("   python src/4_api_prediccion.py")