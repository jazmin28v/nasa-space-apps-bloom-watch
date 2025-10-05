# -*- coding: utf-8 -*-
# JAZ + ChatGPT — NDVI (S2), LST (MODIS c/ QC), Tmax/Tmin (ERA5-Land), Lluvia (CHIRPS, interpolada), Humedad (ERA5-Land)
import ee, pandas as pd, numpy as np, matplotlib.pyplot as plt, time
from scipy.signal import savgol_filter
from datetime import datetime
from pathlib import Path
import os

# ===================== 0) Inicialización =====================
PROJECT = "earthengine-jaz"

def init_ee(project: str):
    try:
        ee.Initialize(project=project)
        print(f"proyecto inicializado: {project}")
    except Exception:
        print("autenticación requerida")
        ee.Authenticate()
        ee.Initialize(project=project)
        print(f"listo: {project}")

init_ee(PROJECT)

# ===================== 1) Parámetros =====================
# Polígono de trabajo (ajústalo si lo necesitas)
coor = [[
    [-99.68750, 20.32944],
    [-99.68750, 20.32944],
    [-99.68417, 20.33250],
    [-99.68417, 20.33250],
    [-99.68444, 20.32889],
    [-99.68750, 20.32944],
]]
AREA = ee.Geometry.Polygon(coor)

INICIO = '2023-10-01'
FIN    = '2025-10-02'

# Carpeta de salida (ajústala a tu preferencia)
OUT_DIR = r"C:\Users\jaz_v\OneDrive\Documentos\HCKATHON"
Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

# ===================== 2) Utilidades =====================
def fc_to_df_batched(fc: ee.FeatureCollection, fields, batch_size=400, pause=0.2) -> pd.DataFrame:
    """Descarga una FeatureCollection en lotes."""
    n = int(fc.size().getInfo() or 0)
    rows = []
    for i in range(0, n, batch_size):
        sub = ee.FeatureCollection(fc.toList(batch_size, i)).getInfo()
        for f in sub.get('features', []):
            p = f.get('properties', {}) or {}
            rows.append({k: p.get(k, None) for k in fields})
        time.sleep(pause)
    df = pd.DataFrame(rows)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in set(fields) - {'date'}:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna(subset=['date']).sort_values('date').reset_index(drop=True)

def suavizar_sg(df: pd.DataFrame, ycol='NDVI', ventana=11, poli=3) -> pd.DataFrame:
    y = df[ycol].values.astype(float)
    n = len(y)
    if n < poli + 2:
        return df.assign(ndvisuave=y)
    if ventana > n:
        ventana = n if n % 2 == 1 else n-1
    if ventana < poli + 2:
        ventana = poli + 2 if (poli + 2) % 2 == 1 else poli + 3
    ysuave = savgol_filter(y, ventana, poli, mode='interp')
    return df.assign(ndvisuave=ysuave)

# ===================== 3) NDVI (Sentinel-2 SR) =====================
def mask_s2_sr(img):
    qa = img.select('QA60')
    cloudBit  = 1 << 10
    cirrusBit = 1 << 11
    cloud_mask = qa.bitwiseAnd(cloudBit).eq(0).And(qa.bitwiseAnd(cirrusBit).eq(0))
    return img.updateMask(cloud_mask)

def add_indices(img):
    ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return img.addBands(ndvi)

s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(AREA)
      .filterDate(INICIO, FIN)
      .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 50))
      .map(mask_s2_sr)
      .map(add_indices))

def img_to_feature_ndvi(img):
    ndvi_mean = img.select('NDVI').reduceRegion(
        ee.Reducer.mean(), AREA, 10, maxPixels=1e13
    ).get('NDVI')
    return ee.Feature(None, {
        'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
        'NDVI': ndvi_mean
    })

fc_ndvi = ee.FeatureCollection(s2.map(img_to_feature_ndvi)).filter(ee.Filter.notNull(['NDVI']))
ndvi_df = fc_to_df_batched(fc_ndvi, fields=('date','NDVI'), batch_size=400, pause=0.2)
# Diario + suavizado
ndvi_day = (ndvi_df.groupby('date', as_index=False)['NDVI'].mean()
            .set_index('date')
            .resample('D').mean()
            .interpolate('time')
            .clip(lower=0, upper=1)
            .reset_index())
ndvi_day = suavizar_sg(ndvi_day, 'NDVI', ventana=11, poli=3)

# ===================== 4) LST (MODIS con QC — °C) =====================
AREA_LST = AREA.buffer(600)

def modis_lst_clean(ic_id, inicio, fin, geom):
    ic = (ee.ImageCollection(ic_id)
          .filterDate(inicio, fin)
          .filterBounds(geom)
          .map(lambda img: img.addBands(img.select('QC_Day').rename('QC'))))
    def to_celsius_masked(img):
        lst = img.select('LST_Day_1km')
        qc  = img.select('QC')
        good_qc = qc.bitwiseAnd(3).lte(1)  # 0 good, 1 average
        valid   = lst.gt(0).And(good_qc)
        lst_c = lst.multiply(0.02).subtract(273.15).updateMask(valid).rename('LST')
        return lst_c.copyProperties(img, ['system:time_start'])
    return ic.map(to_celsius_masked)

lst_terra = modis_lst_clean('MODIS/061/MOD11A2', INICIO, FIN, AREA_LST)
lst_aqua  = modis_lst_clean('MODIS/061/MYD11A2', INICIO, FIN, AREA_LST)
lst_all   = lst_terra.merge(lst_aqua)

def img_to_feature_lst(img):
    meanlst = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=AREA_LST,
        scale=1000,
        bestEffort=True,
        maxPixels=1e13
    ).get('LST')
    return ee.Feature(None, {
        'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
        'LST': meanlst
    })

fc_lst = ee.FeatureCollection(lst_all.map(img_to_feature_lst)).filter(ee.Filter.notNull(['LST']))
lst_df = fc_to_df_batched(fc_lst, fields=('date','LST'), batch_size=300, pause=0.25)

# ===================== 5) Lluvia (CHIRPS, mm/día) + Interpolación =====================
AREA_PPT = AREA.buffer(1500)
chirps = (ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
          .filterDate(INICIO, FIN)
          .filterBounds(AREA_PPT)
          .select('precipitation'))

def img_to_feature_ppt(img):
    ppt = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=AREA_PPT,
        scale=5000,
        bestEffort=True,
        maxPixels=1e13
    ).get('precipitation')
    return ee.Feature(None, {
        'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
        'precip_mm': ee.Number(ppt).max(0)
    })

fc_ppt = ee.FeatureCollection(chirps.map(img_to_feature_ppt)).filter(ee.Filter.notNull(['precip_mm']))
ppt_df = fc_to_df_batched(fc_ppt, fields=('date','precip_mm'), batch_size=400, pause=0.2)

# ---- Interpolación inteligente de precipitación ----
# ---- Interpolación inteligente de precipitación ----
all_days = pd.date_range(start=INICIO, end=FIN, freq='D')
ppt_full = pd.DataFrame({'date': all_days}).merge(ppt_df, on='date', how='left')
ppt_full['precip_mm'] = pd.to_numeric(ppt_full['precip_mm'], errors='coerce')

# Detecta rachas de ceros y reemplaza SOLO rachas cortas por NaN para interpolar
is_zero = ppt_full['precip_mm'].fillna(0).eq(0)
grp = (is_zero != is_zero.shift()).cumsum()
run_len = is_zero.groupby(grp).transform('size')
K = 2  # máximo de días 0 seguidos a tratar como hueco (ajusta 1–3)
mask_short_zero = is_zero & (run_len <= K)
ppt_full.loc[mask_short_zero, 'precip_mm'] = np.nan

# >>> clave: usar DatetimeIndex para method='time'
ppt_full = ppt_full.sort_values('date').set_index('date')

ppt_full['precip_mm_interp'] = (
    ppt_full['precip_mm']
    .interpolate(method='time', limit_direction='both')
    .clip(lower=0)
)

# Suavizado centrado 3 días (funciona igual con DatetimeIndex)
ppt_full['precip_mm_roll3'] = (
    ppt_full['precip_mm_interp'].rolling(3, min_periods=1, center=True).mean()
)

# Volver a columna 'date' para los merges posteriores
ppt_full = ppt_full.reset_index()

# Reemplaza ppt_df para el resto del flujo
ppt_df = ppt_full[['date', 'precip_mm', 'precip_mm_interp', 'precip_mm_roll3']]


# ===================== 6) Humedad de suelo (ERA5-Land) =====================
AREA_SM = AREA.buffer(1000)
era_sm = (ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
          .filterDate(INICIO, FIN)
          .filterBounds(AREA_SM)
          .select('volumetric_soil_water_layer_1'))

def img_to_feature_sm(img):
    sm = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=AREA_SM,
        scale=11132,
        bestEffort=True,
        maxPixels=1e13
    ).get('volumetric_soil_water_layer_1')
    return ee.Feature(None, {
        'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
        'sm_vwc': sm
    })

fc_sm = ee.FeatureCollection(era_sm.map(img_to_feature_sm)).filter(ee.Filter.notNull(['sm_vwc']))
sm_df = fc_to_df_batched(fc_sm, fields=('date','sm_vwc'), batch_size=400, pause=0.2)
sm_df['sm_pct'] = sm_df['sm_vwc'] * 100.0
sm_df['water_mm_0_7cm'] = sm_df['sm_vwc'] * 70.0

# ===================== 7) Temperatura aire Tmax/Tmin (ERA5-Land, °C) =====================
AREA_T2M = AREA.buffer(1000)
era_t2m = (ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
           .filterDate(INICIO, FIN)
           .filterBounds(AREA_T2M)
           .select(['temperature_2m_max', 'temperature_2m_min']))

def img_to_feature_t2m(img):
    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=AREA_T2M,
        scale=11132,
        bestEffort=True,
        maxPixels=1e13
    )
    tmax_c = ee.Number(stats.get('temperature_2m_max')).subtract(273.15)
    tmin_c = ee.Number(stats.get('temperature_2m_min')).subtract(273.15)
    return ee.Feature(None, {
        'date': ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'),
        'tmax_c': tmax_c,
        'tmin_c': tmin_c
    })

fc_t2m = ee.FeatureCollection(era_t2m.map(img_to_feature_t2m)) \
           .filter(ee.Filter.And(
               ee.Filter.notNull(['tmax_c']),
               ee.Filter.notNull(['tmin_c'])
           ))
t2m_df = fc_to_df_batched(fc_t2m, fields=('date','tmax_c','tmin_c'), batch_size=400, pause=0.2)

# ===================== 8) Merges =====================
# Orden temporal
ndvi_day = ndvi_day.sort_values('date')
lst_df   = lst_df.sort_values('date')
ppt_df   = ppt_df.sort_values('date')
sm_df    = sm_df.sort_values('date')
t2m_df   = t2m_df.sort_values('date')

# Base: NDVI diario (con ndvisuave)
master = ndvi_day.copy()  # date, NDVI, ndvisuave

# LST (MODIS 8-días): merge_asof ±4 días
master = pd.merge_asof(
    master, lst_df[['date','LST']].dropna(subset=['date']).sort_values('date'),
    on='date', direction='nearest', tolerance=pd.Timedelta('4D')
)

# Precipitación (cruda + interp + roll3): merge exacto
master = master.merge(
    ppt_df[['date','precip_mm','precip_mm_interp','precip_mm_roll3']],
    on='date', how='left'
)

# Humedad de suelo ERA5-Land (diaria): merge exacto
master = master.merge(
    sm_df[['date','sm_vwc','sm_pct','water_mm_0_7cm']],
    on='date', how='left'
)

# Tmax/Tmin aire ERA5-Land (diario): merge exacto
master = master.merge(
    t2m_df[['date','tmax_c','tmin_c']],
    on='date', how='left'
)

# ===================== 9) Limpieza y exporte =====================
# LST=0 a NaN, NDVI en [0,1]
if 'LST' in master.columns:
    master.loc[master['LST'].fillna(0).eq(0), 'LST'] = pd.NA
for c in ['NDVI', 'ndvisuave']:
    if c in master.columns:
        master[c] = master[c].clip(lower=0, upper=1)

# Rango físico razonable (opcional)
master.loc[(master['LST'] > 80)   | (master['LST'] < -50),   'LST']    = pd.NA
master.loc[(master['tmax_c'] > 60)| (master['tmax_c'] < -50),'tmax_c'] = pd.NA
master.loc[(master['tmin_c'] > 60)| (master['tmin_c'] < -60),'tmin_c'] = pd.NA

# Reordenar columnas
cols_order = [
    'date', 'NDVI', 'ndvisuave', 'LST',
    'tmax_c', 'tmin_c',
    'precip_mm', 'precip_mm_interp', 'precip_mm_roll3',
    'sm_vwc', 'sm_pct', 'water_mm_0_7cm'
]
master = master.reindex(columns=cols_order)

# Guardar CSV con timestamp
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
file_name = f"datos_ndi.csv".replace(':','-')
out_all = os.path.join(OUT_DIR, file_name)
master.to_csv(out_all, index=False, date_format="%Y-%m-%d")
print("✅ CSV guardado:", out_all)

# (Opcional) Vista rápida
#print(master.head(10))
