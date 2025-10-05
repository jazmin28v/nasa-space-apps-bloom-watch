"""
API DE PREDICCIÓN 
===================================
API para recibir datos y devolver predicciones en tiempo real
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import numpy as np
from datetime import datetime

app = FastAPI(title="API Predicción de Estrés")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar modelo al iniciar
print("🌱 Cargando modelo...")
modelo_completo = joblib.load('models/modelo.pkl')
modelo = modelo_completo['modelo']
scaler = modelo_completo['scaler']
features_requeridos = modelo_completo['features']
print("✅ Modelo cargado")


# Estructura de datos de entrada
class DatosEntrada(BaseModel):
    date: str
    ndvi: float
    evi: float
    lst: float
    tmax: float
    tmin: float
    soil_humidity: float


# Estructura de respuesta
class Prediccion(BaseModel):
    fecha: str
    prediccion: str
    probabilidad_sin_estres: float
    probabilidad_moderado: float
    probabilidad_severo: float
    nivel_alerta: str
    recomendacion: str
    metricas: dict


def calcular_features(datos: DatosEntrada) -> dict:
    """
    Calcula todos los features necesarios para el modelo
    """
    # Features básicos
    features_dict = {
        'ndvi': datos.ndvi,
        'evi': datos.evi,
        'lst': datos.lst,
        'tmax': datos.tmax,
        'tmin': datos.tmin,
        'soil_humidity': datos.soil_humidity,
        
        # Features derivados
        'evi_ndvi_ratio': datos.evi / (datos.ndvi + 0.001),
        'temp_promedio': (datos.tmax + datos.tmin) / 2,
        'amplitud_termica': datos.tmax - datos.tmin,
        
        # Déficit combinado
        'deficit_combinado': (
            (1 - datos.soil_humidity / 35) * 0.5 +
            ((datos.lst - 25) / 20) * 0.3 +
            (1 - datos.ndvi) * 0.2
        ),
        
        # Features de fecha
        'mes': pd.to_datetime(datos.date, dayfirst=True).month,
        'dia_año': pd.to_datetime(datos.date, dayfirst=True).dayofyear,
        'dias_desde_inicio': 0  # No aplica en predicción individual
    }
    
    # Features temporales (para predicción individual, usar valores actuales como aproximación)
    for ventana in [7, 14]:
        features_dict[f'ndvi_promedio_{ventana}d'] = datos.ndvi
        features_dict[f'ndvi_tendencia_{ventana}d'] = 0  # Sin historial
        features_dict[f'humedad_promedio_{ventana}d'] = datos.soil_humidity
        features_dict[f'humedad_tendencia_{ventana}d'] = 0
        features_dict[f'lst_max_{ventana}d'] = datos.lst
        features_dict[f'tmax_promedio_{ventana}d'] = datos.tmax
    
    return features_dict


def generar_recomendacion(prediccion: str, probs: dict, datos: DatosEntrada) -> str:
    """
    Genera recomendación basada en la predicción
    """
    if prediccion == "estres_severo":
        return "🚨 Aplicar riego inmediato: 25-30mm | Horario óptimo: 5-7am o 6-8pm"
    
    elif prediccion == "estres_moderado":
        dias = 3 if probs['severo'] > 0.3 else 5
        return f"⚠️ Programar riego en {dias} días | Monitorear cada 2 días"
    
    else:
        return "✅ Condiciones óptimas | Monitoreo rutinario semanal"


# Endpoints
@app.get("/")
def inicio():
    return {
        "mensaje": "API de Predicción de Estrés en Cultivos",
        "version": "1.0",
        "estado": "activo"
    }


@app.post("/predecir", response_model=Prediccion)
def predecir(datos: DatosEntrada):
    """
    Recibe datos actuales y devuelve predicción
    """
    try:
        # 1. Calcular features
        features_dict = calcular_features(datos)
        
        # 2. Crear DataFrame con el orden correcto
        X = pd.DataFrame([features_dict])[features_requeridos]
        
        # 3. Escalar
        X_scaled = scaler.transform(X)
        
        # 4. Predecir
        prediccion_num = modelo.predict(X_scaled)[0]
        probabilidades = modelo.predict_proba(X_scaled)[0]
        
        # 5. Mapear predicción
        mapa = {0: "sin_estres", 1: "estres_moderado", 2: "estres_severo"}
        prediccion_texto = mapa[prediccion_num]
        
        # 6. Nivel de alerta
        nivel_alerta = {
            "sin_estres": "✅ ÓPTIMO",
            "estres_moderado": "⚠️ ALERTA HÍDRICA",
            "estres_severo": "🚨 CRÍTICO"
        }[prediccion_texto]
        
        # 7. Probabilidades
        probs = {
            'sin_estres': float(probabilidades[0]),
            'moderado': float(probabilidades[1]),
            'severo': float(probabilidades[2])
        }
        
        # 8. Recomendación
        recomendacion = generar_recomendacion(prediccion_texto, probs, datos)
        
        # 9. Métricas adicionales
        metricas = {
            'ndvi': datos.ndvi,
            'soil_humidity': datos.soil_humidity,
            'lst': datos.lst,
            'deficit_combinado': float(features_dict['deficit_combinado']),
            'estado_humedad': 'crítico' if datos.soil_humidity < 12 else ('bajo' if datos.soil_humidity < 18 else 'adecuado'),
            'estado_ndvi': 'bajo' if datos.ndvi < 0.5 else ('moderado' if datos.ndvi < 0.65 else 'óptimo')
        }
        
        # 10. Construir respuesta
        respuesta = Prediccion(
            fecha=datos.date,
            prediccion=prediccion_texto,
            probabilidad_sin_estres=probs['sin_estres'],
            probabilidad_moderado=probs['moderado'],
            probabilidad_severo=probs['severo'],
            nivel_alerta=nivel_alerta,
            recomendacion=recomendacion,
            metricas=metricas
        )
        
        return respuesta
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/salud")
def salud():
    """Verifica que la API esté funcionando"""
    return {
        "estado": "OK",
        "modelo_cargado": True,
        "features_requeridos": len(features_requeridos),
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Iniciando API...")
    print("📍 Documentación: http://localhost:8000/docs")
    print("📍 Pruebas: http://localhost:8000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)