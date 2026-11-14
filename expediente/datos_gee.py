"""Acceso a instrumentos de satélite a través de Google Earth Engine.

Cada variable se baja como un "cubo": la serie mensual de cada celda de medio grado
(unos 50 km) dentro de un recuadro, en el mismo formato que `datos.descargar_region`.
Necesita una sesión de Earth Engine en la computadora (`earthengine authenticate`); lo
ya descargado queda en disco y funciona sin ella.
"""

from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd

from .datos import DIR_CACHE, ErrorDeDatos, caja, guardar_en_cache, leer_cache, vigente

PROYECTO = os.environ.get("EXPEDIENTE_EE_PROYECTO", "project-7492083c-8d82-4592-953")
LADO_CUBO = 10  # grados; el cubo siempre se baja de este tamaño y luego se recorta
CELDA = 0.5  # grados
SIN_DATO = -9999.0

# codigo -> (colección de Earth Engine, banda, factor para llegar a la unidad del catálogo)
FUENTES = {
    "GPM_LLUVIA": ("NASA/GPM_L3/IMERG_MONTHLY_V07", "precipitation", 24.0),  # mm/h -> mm/día
    "MODIS_NDVI": ("MODIS/061/MOD13A3", "NDVI", 0.0001),
    "GRACE_AGUA": ("NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI", "lwe_thickness", 1.0),  # cm
}

_sesion_lista = False


def _ee():
    """Devuelve el módulo `ee` con la sesión iniciada, o lanza ErrorDeDatos."""
    global _sesion_lista
    try:
        import ee
        if not _sesion_lista:
            ee.Initialize(project=PROYECTO)
            _sesion_lista = True
        return ee
    except Exception as error:  # sin biblioteca, sin sesión o sin red: mismo resultado
        raise ErrorDeDatos(f"Earth Engine no está disponible: {str(error)[:200]}") from error


def _ruta(codigo: str, lat: float, lon: float) -> "os.PathLike":
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, LADO_CUBO)
    return DIR_CACHE / f"gee_{codigo}_{lat_min:+.0f}_{lat_max:+.0f}_{lon_min:+.0f}_{lon_max:+.0f}.csv"


def descargar_cubo(lat: float, lon: float, codigo: str) -> pd.DataFrame:
    """Serie mensual de un instrumento en cada celda del recuadro de 10° alrededor del punto.

    Filas = meses; columnas = celdas nombradas "lat,lon" por su centro. Earth Engine
    promedia los píxeles originales (de 1 a 50 km según el instrumento) hasta la celda.
    """
    ruta = _ruta(codigo, lat, lon)
    if vigente(ruta):
        return leer_cache(ruta)
    try:
        ee = _ee()
    except ErrorDeDatos:
        if ruta.exists():  # sin sesión de Earth Engine: se usa lo ya descargado
            return leer_cache(ruta)
        raise
    coleccion_id, banda, factor = FUENTES[codigo]
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, LADO_CUBO)
    n = int(LADO_CUBO / CELDA)
    try:
        coleccion = ee.ImageCollection(coleccion_id).select(banda).sort("system:time_start")
        tiempos = coleccion.reduceColumns(ee.Reducer.toList(2), ["system:time_start", "system:time_end"]).get("list").getInfo()
        pila = coleccion.map(lambda imagen: imagen.unmask(SIN_DATO).toFloat()).toBands()
        crudo = ee.data.computePixels({
            "expression": pila,
            "fileFormat": "NPY",
            "grid": {"dimensions": {"width": n, "height": n}, "crsCode": "EPSG:4326",
                     "affineTransform": {"scaleX": CELDA, "shearX": 0, "translateX": lon_min,
                                         "shearY": 0, "scaleY": -CELDA, "translateY": lat_max}},
        })
        # Un campo por mes: el encabezado crece más de lo que numpy acepta por omisión.
        pixeles = np.load(io.BytesIO(crudo), max_header_size=1_000_000)
    except Exception as error:
        if ruta.exists():
            return leer_cache(ruta)
        raise ErrorDeDatos(f"Earth Engine no entregó {codigo}: {str(error)[:200]}") from error

    valores = np.stack([pixeles[nombre] for nombre in pixeles.dtype.names]).astype(float)  # (mes, fila, col)
    valores[valores == SIN_DATO] = np.nan
    # Cada imagen se asigna al mes en que cae la mitad de su periodo (GRACE no mide meses exactos).
    meses = pd.to_datetime([(inicio + fin) / 2 for inicio, fin in tiempos], unit="ms").to_period("M").to_timestamp()
    lats = lat_max - CELDA / 2 - CELDA * np.arange(n)
    lons = lon_min + CELDA / 2 + CELDA * np.arange(n)
    columnas = [f"{la},{lo}" for la in lats for lo in lons]
    tabla = pd.DataFrame(valores.reshape(len(meses), -1) * factor, index=meses, columns=columnas)
    tabla = tabla.groupby(level=0).mean().dropna(how="all", axis=1)
    guardar_en_cache(tabla, ruta, float_format="%.5g")
    return tabla


def recortar(cubo: pd.DataFrame, lat: float, lon: float, lado: float) -> pd.DataFrame:
    """Las celdas del cubo que caen dentro de un recuadro más chico centrado en el mismo punto."""
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, lado)
    pares = np.array([c.split(",") for c in cubo.columns], dtype=float)
    dentro = (pares[:, 0] > lat_min) & (pares[:, 0] < lat_max) & (pares[:, 1] > lon_min) & (pares[:, 1] < lon_max)
    return cubo.loc[:, dentro]


def serie_del_punto(cubo: pd.DataFrame, lat: float, lon: float) -> pd.Series:
    """La serie de la celda más cercana al punto (vacía si el punto no tiene datos)."""
    if cubo.shape[1] == 0:
        return pd.Series(dtype=float)
    pares = np.array([c.split(",") for c in cubo.columns], dtype=float)
    cercana = np.argmin((pares[:, 0] - lat) ** 2 + (pares[:, 1] - lon) ** 2)
    if abs(pares[cercana, 0] - lat) > CELDA or abs(pares[cercana, 1] - lon) > CELDA:
        return pd.Series(dtype=float)
    return cubo.iloc[:, cercana].dropna()
