from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import joblib
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import requests

app = FastAPI(title="API Predicción con Coordenadas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar modelo
print("🌱 Cargando modelo...")
modelo_completo = joblib.load('models/modelo.pkl')
modelo = modelo_completo['modelo']
scaler = modelo_completo['scaler']
features_requeridos = modelo_completo['features']
print("✅ Modelo cargado")

# Modelos de entrada/salida
class Coordenadas(BaseModel):
    latitud: float
    longitud: float
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None

class Diagnostico(BaseModel):
    diagnostico: str
    probabilidad: float
    ndvi: float
    evi: float
    lst: float
    humedad: float
    tmax: float
    tmin: float

# Función para obtener datos reales desde NASA POWER
def obtener_datos_satelitales(lat: float, lon: float, fecha: str):
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    fecha_inicio = fecha_obj.strftime('%Y%m%d')
    fecha_fin = (fecha_obj + timedelta(days=1)).strftime('%Y%m%d')

    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"parameters=T2M_MAX,T2M_MIN,ALLSKY_SFC_LW_DWN,RH2M&"
        f"start={fecha_inicio}&end={fecha_fin}&latitude={lat}&longitude={lon}&format=JSON"
    )

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Error al consultar NASA POWER")

    data = response.json()
    dia = list(data['properties']['parameter']['T2M_MAX'].keys())[0]

    tmax = data['properties']['parameter']['T2M_MAX'][dia]
    tmin = data['properties']['parameter']['T2M_MIN'][dia]
    lst = data['properties']['parameter']['ALLSKY_SFC_LW_DWN'][dia] / 10
    humedad_relativa = data['properties']['parameter']['RH2M'][dia]

    ndvi = max(0.3, min(0.85, 0.6 + (lat % 10) * 0.02 - 0.2))
    evi = max(0.2, min(0.7, ndvi * 0.85))
    soil_humidity = max(5, min(35, humedad_relativa / 3))

    return {
        'date': fecha_obj.strftime('%d/%m/%Y'),
        'ndvi': round(ndvi, 3),
        'evi': round(evi, 3),
        'lst': round(lst, 1),
        'tmax': round(tmax, 1),
        'tmin': round(tmin, 1),
        'soil_humidity': round(soil_humidity, 1)
    }

# Función para calcular features
def calcular_features(datos):
    return {
        'ndvi': datos['ndvi'],
        'evi': datos['evi'],
        'lst': datos['lst'],
        'tmax': datos['tmax'],
        'tmin': datos['tmin'],
        'soil_humidity': datos['soil_humidity'],
        'evi_ndvi_ratio': datos['evi'] / (datos['ndvi'] + 0.001),
        'temp_promedio': (datos['tmax'] + datos['tmin']) / 2,
        'amplitud_termica': datos['tmax'] - datos['tmin'],
        'deficit_combinado': (
            (1 - datos['soil_humidity'] / 35) * 0.5 +
            ((datos['lst'] - 25) / 20) * 0.3 +
            (1 - datos['ndvi']) * 0.2
        ),
        'mes': datetime.strptime(datos['date'], '%d/%m/%Y').month,
        'dia_año': datetime.strptime(datos['date'], '%d/%m/%Y').dayofyear,
        'dias_desde_inicio': 0,
        'ndvi_promedio_7d': datos['ndvi'],
        'ndvi_tendencia_7d': 0,
        'ndvi_promedio_14d': datos['ndvi'],
        'ndvi_tendencia_14d': 0,
        'humedad_promedio_7d': datos['soil_humidity'],
        'humedad_tendencia_7d': 0,
        'humedad_promedio_14d': datos['soil_humidity'],
        'humedad_tendencia_14d': 0,
        'lst_max_7d': datos['lst'],
        'lst_max_14d': datos['lst'],
        'tmax_promedio_7d': datos['tmax'],
        'tmax_promedio_14d': datos['tmax']
    }

# Endpoint principal
@app.post("/analizar", response_model=Diagnostico)
def analizar_campo(coords: Coordenadas):
    try:
        fecha = coords.fecha_fin or datetime.now().strftime('%Y-%m-%d')
        datos = obtener_datos_satelitales(coords.latitud, coords.longitud, fecha)
        features = calcular_features(datos)

        X = pd.DataFrame([features])[features_requeridos]
        X_scaled = scaler.transform(X)

        pred = modelo.predict(X_scaled)[0]
        prob = modelo.predict_proba(X_scaled)[0][pred]

        etiquetas = {0: 'sin_estres', 1: 'estres_moderado', 2: 'estres_severo'}

        return Diagnostico(
            diagnostico=etiquetas[pred],
            probabilidad=round(prob * 100, 1),
            ndvi=datos['ndvi'],
            evi=datos['evi'],
            lst=datos['lst'],
            humedad=datos['soil_humidity'],
            tmax=datos['tmax'],
            tmin=datos['tmin']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def inicio():
    return {"mensaje": "API de Predicción con Coordenadas", "estado": "activo"}

@app.get("/salud")
def salud():
    return {"estado": "OK", "modelo_cargado": True, "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)