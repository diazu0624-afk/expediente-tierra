"""Acceso a instrumentos de satélite y modelos a través de Google Earth Engine.

Cada variable se baja como un "cubo": la serie mensual de cada celda dentro de un
recuadro, en el mismo formato que `datos.descargar_region`. Necesita una sesión de Earth
Engine en la computadora (`earthengine authenticate`); lo ya descargado queda en disco y
funciona sin ella.
"""

from __future__ import annotations

import io
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .datos import DIR_CACHE, ErrorDeDatos, caja, guardar_en_cache, leer_cache, vigente

PROYECTO = os.environ.get("EXPEDIENTE_EE_PROYECTO", "project-7492083c-8d82-4592-953")
LADO_CUBO = 10  # grados; el cubo siempre se baja de este tamaño y luego se recorta
SIN_DATO = -9999.0
MESES_POR_PETICION = 24  # para los productos diarios, que Earth Engine promedia mes a mes
HILOS = 6


@dataclass(frozen=True)
class Fuente:
    """De dónde sale una variable y cómo llevarla a la unidad del catálogo.

    valor = (suma de `bandas`) × `factor` + `desfase`.
    """

    coleccion: str
    bandas: tuple[str, ...]
    factor: float = 1.0
    desfase: float = 0.0
    celda: float = 0.5  # grados; no menor que la resolución real del producto
    diaria: bool = False  # True: la colección trae varias imágenes por mes y hay que promediarlas


_MODIS_ATM = "MODIS/061/MOD08_M3"
_OCEANO = "NASA/OCEANDATA/MODIS-Aqua/L3SMI"

FUENTES: dict[str, Fuente] = {
    "GPM_LLUVIA": Fuente("NASA/GPM_L3/IMERG_MONTHLY_V07", ("precipitation",), factor=24.0),  # mm/h -> mm/día
    "MODIS_NDVI": Fuente("MODIS/061/MOD13A3", ("NDVI",), factor=0.0001),
    "MODIS_EVI": Fuente("MODIS/061/MOD13A3", ("EVI",), factor=0.0001),
    "GRACE_AGUA": Fuente("NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI", ("lwe_thickness",)),  # cm
    # MODIS Terra, producto mensual de atmósfera en rejilla de 1°
    "MODIS_AOD": Fuente(_MODIS_ATM, ("Aerosol_Optical_Depth_Land_Ocean_Mean_Mean",), factor=0.001, celda=1.0),
    "MODIS_NUBES": Fuente(_MODIS_ATM, ("Cloud_Fraction_Mean_Mean",), factor=0.01, celda=1.0),  # a %
    # FLDAS: escurrimiento superficial + subterráneo (kg/m²/s -> mm/día)
    "FLDAS_ESCURRIMIENTO": Fuente("NASA/FLDAS/NOAH01/C/GL/M/V001", ("Qs_tavg", "Qsb_tavg"), factor=86400.0),
    # Productos diarios
    "OMI_OZONO": Fuente("TOMS/MERGED", ("ozone",), celda=1.0, diaria=True),  # unidades Dobson
    "MAR_CLOROFILA": Fuente(_OCEANO, ("chlor_a",), diaria=True),  # mg/m³
    "MAR_SST_MODIS": Fuente(_OCEANO, ("sst",), diaria=True),  # °C
    "MAR_SST": Fuente("NOAA/CDR/OISST/V2_1", ("sst",), factor=0.01, diaria=True),  # °C
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


def _pixeles(ee, imagen, lat_max: float, lon_min: float, celda: float) -> np.ndarray:
    """Valores de una imagen de varias bandas sobre la rejilla del cubo: (banda, fila, columna)."""
    n = int(round(LADO_CUBO / celda))
    crudo = ee.data.computePixels({
        "expression": imagen,
        "fileFormat": "NPY",
        "grid": {"dimensions": {"width": n, "height": n}, "crsCode": "EPSG:4326",
                 "affineTransform": {"scaleX": celda, "shearX": 0, "translateX": lon_min,
                                     "shearY": 0, "scaleY": -celda, "translateY": lat_max}},
    })
    # Un campo por mes: el encabezado crece más de lo que numpy acepta por omisión.
    pixeles = np.load(io.BytesIO(crudo), max_header_size=1_000_000)
    return np.stack([pixeles[nombre] for nombre in pixeles.dtype.names]).astype(float)


def _banda(ee, imagen, fuente: Fuente):
    """Una sola banda con la suma de las bandas de la fuente y los huecos marcados con SIN_DATO."""
    suma = imagen.select(fuente.bandas[0])
    for otra in fuente.bandas[1:]:
        suma = suma.add(imagen.select(otra))
    return suma.rename("v").unmask(SIN_DATO).toFloat()


def _cubo_mensual(ee, fuente: Fuente, lat_max: float, lon_min: float) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Colecciones que ya traen una imagen por mes: todas las bandas en una sola petición."""
    coleccion = ee.ImageCollection(fuente.coleccion).select(list(fuente.bandas)).sort("system:time_start")
    tiempos = coleccion.reduceColumns(ee.Reducer.toList(2), ["system:time_start", "system:time_end"]).get("list").getInfo()
    valores = _pixeles(ee, coleccion.map(lambda imagen: _banda(ee, imagen, fuente)).toBands(), lat_max, lon_min, fuente.celda)
    # Cada imagen se asigna al mes en que cae la mitad de su periodo (GRACE no mide meses exactos).
    meses = pd.to_datetime([(inicio + fin) / 2 for inicio, fin in tiempos], unit="ms").to_period("M").to_timestamp()
    return meses, valores


def _cubo_desde_diarios(ee, fuente: Fuente, lat_max: float, lon_min: float) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Colecciones diarias: Earth Engine promedia cada mes y se piden por tandas en paralelo."""
    coleccion = ee.ImageCollection(fuente.coleccion).select(list(fuente.bandas))
    limites = coleccion.reduceColumns(ee.Reducer.minMax(), ["system:time_start"]).getInfo()
    meses = pd.period_range(pd.to_datetime(limites["min"], unit="ms"), pd.to_datetime(limites["max"], unit="ms"), freq="M").to_timestamp()
    vacia = ee.Image.constant(0).rename("v").updateMask(0).toFloat()  # para que un mes sin imágenes no rompa la pila

    def promedio(mes: pd.Timestamp):
        del_mes = coleccion.filterDate(mes.strftime("%Y-%m-%d"), (mes + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d"))
        suma = del_mes.map(lambda imagen: imagen.select(fuente.bandas[0]).rename("v").toFloat())
        return ee.ImageCollection(suma.merge(ee.ImageCollection([vacia]))).mean().unmask(SIN_DATO).toFloat()

    def tanda(indices: list[int]) -> np.ndarray:
        pila = ee.ImageCollection.fromImages([promedio(meses[k]) for k in indices]).toBands()
        return _pixeles(ee, pila, lat_max, lon_min, fuente.celda)

    tandas = [list(range(k, min(k + MESES_POR_PETICION, len(meses)))) for k in range(0, len(meses), MESES_POR_PETICION)]
    with ThreadPoolExecutor(HILOS) as ejecutor:
        partes = list(ejecutor.map(tanda, tandas))
    return meses, np.concatenate(partes)


def descargar_cubo(lat: float, lon: float, codigo: str) -> pd.DataFrame:
    """Serie mensual de una variable en cada celda del recuadro de 10° alrededor del punto.

    Filas = meses; columnas = celdas nombradas "lat,lon" por su centro. Earth Engine
    promedia los píxeles originales (de 1 a 100 km según el producto) hasta la celda.
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
    fuente = FUENTES[codigo]
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, LADO_CUBO)
    try:
        extraer = _cubo_desde_diarios if fuente.diaria else _cubo_mensual
        meses, valores = extraer(ee, fuente, lat_max, lon_min)
    except Exception as error:
        if ruta.exists():
            return leer_cache(ruta)
        raise ErrorDeDatos(f"Earth Engine no entregó {codigo}: {str(error)[:200]}") from error

    n = valores.shape[1]
    valores[valores == SIN_DATO] = np.nan
    lats = lat_max - fuente.celda / 2 - fuente.celda * np.arange(n)
    lons = lon_min + fuente.celda / 2 + fuente.celda * np.arange(n)
    columnas = [f"{la},{lo}" for la in lats for lo in lons]
    tabla = pd.DataFrame(valores.reshape(len(meses), -1) * fuente.factor + fuente.desfase, index=meses, columns=columnas)
    tabla = tabla.groupby(level=0).mean().dropna(how="all", axis=1).dropna(how="all", axis=0)
    guardar_en_cache(tabla, ruta, float_format="%.5g")
    return tabla


def _coordenadas(cubo: pd.DataFrame) -> np.ndarray:
    return np.array([c.split(",") for c in cubo.columns], dtype=float).reshape(-1, 2)


def recortar(cubo: pd.DataFrame, lat: float, lon: float, lado: float) -> pd.DataFrame:
    """Las celdas del cubo que caen dentro de un recuadro más chico centrado en el mismo punto."""
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, lado)
    pares = _coordenadas(cubo)
    dentro = (pares[:, 0] > lat_min) & (pares[:, 0] < lat_max) & (pares[:, 1] > lon_min) & (pares[:, 1] < lon_max)
    return cubo.loc[:, dentro]


def serie_del_punto(cubo: pd.DataFrame, lat: float, lon: float) -> pd.Series:
    """La serie de la celda más cercana al punto (vacía si el punto no tiene datos)."""
    if cubo.shape[1] == 0:
        return pd.Series(dtype=float)
    pares = _coordenadas(cubo)
    cercana = np.argmin((pares[:, 0] - lat) ** 2 + (pares[:, 1] - lon) ** 2)
    # Tolerancia: una celda de 1°, la más gruesa de las fuentes.
    if abs(pares[cercana, 0] - lat) > 1.0 or abs(pares[cercana, 1] - lon) > 1.0:
        return pd.Series(dtype=float)
    return cubo.iloc[:, cercana].dropna()
