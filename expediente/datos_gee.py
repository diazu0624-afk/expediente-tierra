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

from .datos import CACHE, ErrorDeDatos, caja

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
    hasta: int | None = None  # último año confiable; lo posterior se descarta


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
    "FLDAS_TEMP": Fuente("NASA/FLDAS/NOAH01/C/GL/M/V001", ("Tair_f_tavg",), desfase=-273.15),  # K -> °C
    # FLDAS: escurrimiento superficial + subterráneo (kg/m²/s -> mm/día)
    "FLDAS_ESCURRIMIENTO": Fuente("NASA/FLDAS/NOAH01/C/GL/M/V001", ("Qs_tavg", "Qsb_tavg"), factor=86400.0),
    # Productos diarios
    "OMI_OZONO": Fuente("TOMS/MERGED", ("ozone",), celda=1.0, diaria=True),  # unidades Dobson
    # Clorofila: se corta en 2021. Desde 2022 el satélite Aqua deriva de órbita y el promedio global
    # salta de 0.31 a 0.40 mg/m³ en tres años, sin que hasta 2021 hubiera tendencia alguna.
    "MAR_CLOROFILA": Fuente(_OCEANO, ("chlor_a",), diaria=True, hasta=2021),  # mg/m³
    "MAR_SST_MODIS": Fuente(_OCEANO, ("sst",), diaria=True),  # °C
    "MAR_SST": Fuente("NOAA/CDR/OISST/V2_1", ("sst",), factor=0.01, diaria=True),  # °C
}

@dataclass(frozen=True)
class Rejilla:
    """Rejilla regular de celdas en latitud y longitud sobre la que se muestrea una imagen."""

    lat_max: float
    lon_min: float
    celda: float
    ancho: int  # celdas de oeste a este
    alto: int  # celdas de norte a sur

    @property
    def lats(self) -> np.ndarray:
        return self.lat_max - self.celda / 2 - self.celda * np.arange(self.alto)

    @property
    def lons(self) -> np.ndarray:
        return self.lon_min + self.celda / 2 + self.celda * np.arange(self.ancho)

    @property
    def columnas(self) -> list[str]:
        """Nombre "lat,lon" de cada celda, en el orden en que llegan los píxeles (por filas)."""
        return [f"{lat},{lon}" for lat in self.lats for lon in self.lons]


def rejilla_del_recuadro(lat_min: float, lat_max: float, lon_min: float, lon_max: float, celda: float) -> Rejilla:
    """La rejilla de celdas de tamaño `celda` que cubre un recuadro, alineada a múltiplos de la celda."""
    norte = np.ceil(lat_max / celda) * celda
    oeste = np.floor(lon_min / celda) * celda
    alto = int(round((norte - np.floor(lat_min / celda) * celda) / celda))
    ancho = int(round((np.ceil(lon_max / celda) * celda - oeste) / celda))
    return Rejilla(float(norte), float(oeste), celda, max(ancho, 1), max(alto, 1))


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
    return CACHE.ruta(f"gee_{codigo}_{lat_min:+.0f}_{lat_max:+.0f}_{lon_min:+.0f}_{lon_max:+.0f}.csv")


def _pixeles(ee, imagen, rejilla: Rejilla) -> np.ndarray:
    """Valores de una imagen de varias bandas sobre la rejilla: (banda, fila, columna)."""
    crudo = ee.data.computePixels({
        "expression": imagen,
        "fileFormat": "NPY",
        "grid": {"dimensions": {"width": rejilla.ancho, "height": rejilla.alto}, "crsCode": "EPSG:4326",
                 "affineTransform": {"scaleX": rejilla.celda, "shearX": 0, "translateX": rejilla.lon_min,
                                     "shearY": 0, "scaleY": -rejilla.celda, "translateY": rejilla.lat_max}},
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


def _cubo_mensual(ee, fuente: Fuente, rejilla: Rejilla) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Colecciones que ya traen una imagen por mes: todas las bandas en una sola petición."""
    coleccion = ee.ImageCollection(fuente.coleccion).select(list(fuente.bandas)).sort("system:time_start")
    tiempos = coleccion.reduceColumns(ee.Reducer.toList(2), ["system:time_start", "system:time_end"]).get("list").getInfo()
    valores = _pixeles(ee, coleccion.map(lambda imagen: _banda(ee, imagen, fuente)).toBands(), rejilla)
    # Cada imagen se asigna al mes en que cae la mitad de su periodo (GRACE no mide meses exactos).
    meses = pd.to_datetime([(inicio + fin) / 2 for inicio, fin in tiempos], unit="ms").to_period("M").to_timestamp()
    return meses, valores


def _cubo_desde_diarios(ee, fuente: Fuente, rejilla: Rejilla) -> tuple[pd.DatetimeIndex, np.ndarray]:
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
        return _pixeles(ee, pila, rejilla)

    tandas = [list(range(k, min(k + MESES_POR_PETICION, len(meses)))) for k in range(0, len(meses), MESES_POR_PETICION)]
    with ThreadPoolExecutor(HILOS) as ejecutor:
        partes = list(ejecutor.map(tanda, tandas))
    return meses, np.concatenate(partes)


FRONTERAS = "USDOS/LSIB_SIMPLE/2017"  # fronteras internacionales del Departamento de Estado de EE. UU.
# Productos que traen valores fuera de su dominio y hay que recortar:
# GRACE mide masa también sobre el océano, y ahí no es agua terrestre.
SOLO_SOBRE_TIERRA = frozenset({"GRACE_AGUA"})
# El sensor de color del océano también "ve" lagos y ríos, donde sus algoritmos no son válidos.
SOLO_SOBRE_MAR = frozenset({"MAR_SST_MODIS", "MAR_CLOROFILA"})


def _dominio(ee, codigo: str, rejilla: Rejilla) -> np.ndarray | None:
    """Qué celdas de la rejilla pertenecen al dominio de la variable (None: todas)."""
    if codigo in SOLO_SOBRE_TIERRA:  # celdas cuyo centro cae dentro de algún país
        dentro = ee.Image.constant(1).clip(ee.FeatureCollection(FRONTERAS)).unmask(0)
    elif codigo in SOLO_SOBRE_MAR:  # celdas que el análisis OISST considera océano en más de la mitad
        dentro = ee.Image(ee.ImageCollection("NOAA/CDR/OISST/V2_1").first()).select("sst").mask().gt(0.5)
    else:
        return None
    return _pixeles(ee, dentro.rename("dentro").toFloat(), rejilla)[0].reshape(-1) > 0.5


def _extraer(ee, codigo: str, rejilla: Rejilla) -> pd.DataFrame:
    """Serie mensual de cada celda de la rejilla, ya en la unidad del catálogo."""
    fuente = FUENTES[codigo]
    extraer = _cubo_desde_diarios if fuente.diaria else _cubo_mensual
    meses, valores = extraer(ee, fuente, rejilla)
    valores[valores == SIN_DATO] = np.nan
    tabla = pd.DataFrame(valores.reshape(len(meses), -1) * fuente.factor + fuente.desfase,
                         index=meses, columns=rejilla.columnas)
    dominio = _dominio(ee, codigo, rejilla)
    if dominio is not None:
        tabla = tabla.loc[:, dominio]
    return tabla.groupby(level=0).mean().dropna(how="all", axis=1).dropna(how="all", axis=0)


def _con_cache(ruta, codigo: str, descargar) -> pd.DataFrame:
    """El cubo de una variable, del disco o recién bajado, sin los años que no son confiables."""
    tabla = _leer_o_bajar(ruta, codigo, descargar)
    hasta = FUENTES[codigo].hasta
    return tabla if hasta is None else tabla.loc[:str(hasta)]


def _leer_o_bajar(ruta, codigo: str, descargar) -> pd.DataFrame:
    """Lee el cubo del disco si está vigente; si no, lo baja. Sin Earth Engine, usa lo que haya."""
    if CACHE.vigente(ruta):
        return CACHE.leer(ruta)
    try:
        ee = _ee()
    except ErrorDeDatos:
        if ruta.exists():  # sin sesión de Earth Engine: se usa lo ya descargado
            return CACHE.leer(ruta)
        raise
    try:
        tabla = descargar(ee)
    except Exception as error:
        if ruta.exists():
            return CACHE.leer(ruta)
        raise ErrorDeDatos(f"Earth Engine no entregó {codigo}: {str(error)[:200]}") from error
    CACHE.guardar(tabla, ruta, float_format="%.5g")
    return tabla


def descargar_cubo(lat: float, lon: float, codigo: str) -> pd.DataFrame:
    """Serie mensual de una variable en cada celda del recuadro de 10° alrededor del punto.

    Filas = meses; columnas = celdas nombradas "lat,lon" por su centro. Earth Engine
    promedia los píxeles originales (de 1 a 100 km según el producto) hasta la celda.
    """
    fuente = FUENTES[codigo]
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, LADO_CUBO)
    n = int(round(LADO_CUBO / fuente.celda))
    rejilla = Rejilla(lat_max, lon_min, fuente.celda, n, n)
    return _con_cache(_ruta(codigo, lat, lon), codigo, lambda ee: _extraer(ee, codigo, rejilla))


# ------------------------------------------------------------------ países y mundo

MAX_CELDAS = 6000  # tope de celdas de un mapa: equilibrio entre detalle y tiempo de cálculo
CELDAS_POSIBLES = (0.25, 0.5, 1.0, 2.0, 3.0, 4.0)
MUNDO = (-60.0, 84.0, -180.0, 180.0)  # lat_min, lat_max, lon_min, lon_max; sin la Antártida


@dataclass(frozen=True)
class Pais:
    nombre: str  # como lo escribe el catálogo de fronteras (en inglés)
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


def buscar_pais(lat: float, lon: float) -> Pais:
    """El país que contiene un punto, con el recuadro que lo encierra."""
    ee = _ee()
    try:
        fronteras = ee.FeatureCollection(FRONTERAS)
        nombres = fronteras.filterBounds(ee.Geometry.Point([lon, lat])).aggregate_array("country_na").getInfo()
        if not nombres:
            raise ErrorDeDatos("Ese punto no cae dentro de ningún país del catálogo de fronteras.")
        esquinas = _geometria(ee, nombres[0]).bounds().coordinates().getInfo()[0]
    except ErrorDeDatos:
        raise
    except Exception as error:
        raise ErrorDeDatos(f"Earth Engine no entregó la frontera: {str(error)[:200]}") from error
    lons, lats = [e[0] for e in esquinas], [e[1] for e in esquinas]
    return Pais(nombres[0], max(min(lats), -90.0), min(max(lats), 90.0), max(min(lons), -180.0), min(max(lons), 180.0))


def _geometria(ee, nombre_del_pais: str):
    return ee.FeatureCollection(FRONTERAS).filter(ee.Filter.eq("country_na", nombre_del_pais)).geometry()


def celda_para(codigo: str, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> float:
    """La celda más fina que mantiene el mapa por debajo de MAX_CELDAS, sin bajar de la del producto."""
    minima = FUENTES[codigo].celda if FUENTES[codigo].celda > 0.5 or codigo == "GRACE_AGUA" else 0.25
    for celda in CELDAS_POSIBLES:
        if celda >= minima and (lat_max - lat_min) * (lon_max - lon_min) / celda ** 2 <= MAX_CELDAS:
            return celda
    return CELDAS_POSIBLES[-1]


def descargar_cubo_del_pais(pais: Pais, codigo: str) -> pd.DataFrame:
    """Serie mensual de una variable en cada celda cuyo centro cae dentro del país."""
    celda = celda_para(codigo, pais.lat_min, pais.lat_max, pais.lon_min, pais.lon_max)
    rejilla = rejilla_del_recuadro(pais.lat_min, pais.lat_max, pais.lon_min, pais.lon_max, celda)

    def descargar(ee) -> pd.DataFrame:
        dentro = ee.Image.constant(1).clip(_geometria(ee, pais.nombre)).unmask(0).rename("dentro").toFloat()
        mascara = _pixeles(ee, dentro, rejilla)[0].reshape(-1) > 0.5
        tabla = _extraer(ee, codigo, rejilla)
        return tabla[[c for c, esta in zip(rejilla.columnas, mascara) if esta and c in tabla.columns]]

    nombre = "".join(ch if ch.isalnum() else "_" for ch in pais.nombre)
    return _con_cache(CACHE.ruta(f"pais_{codigo}_{nombre}_{celda:g}.csv.gz"), codigo, descargar)


def descargar_cubo_del_mundo(codigo: str) -> pd.DataFrame:
    """Serie mensual de una variable en cada celda del planeta (de 60° S a 84° N)."""
    celda = celda_para(codigo, *MUNDO)
    rejilla = rejilla_del_recuadro(*MUNDO, celda)
    return _con_cache(CACHE.ruta(f"mundo_{codigo}_{celda:g}.csv.gz"), codigo, lambda ee: _extraer(ee, codigo, rejilla))


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
