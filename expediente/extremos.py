"""Índices anuales de extremos, calculados con los datos diarios de NASA POWER.

Un promedio mensual esconde los días extremos: el mes puede ser "normal" y haber tenido
una ola de calor o un aguacero. Estos índices siguen las definiciones del grupo de expertos
ETCCDI (Zhang et al., 2011) y resumen cada año en un número: cuántos días de calor hubo,
cuánto llovió el día más lluvioso, cuánto duró la racha seca más larga.

Solo se calculan para el punto: la API regional de POWER no entrega datos diarios.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import requests

from .datos import ANIO_INICIAL, CACHE, SIN_DATO, ErrorDeDatos

POWER_DIARIO_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETROS = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR")
MIN_DIAS = 360  # días con dato para que un año cuente
PERIODO_BASE = (1981, 2010)  # referencia del umbral local de calor extremo
PERCENTIL_CALOR = 90
DIA_HUMEDO = 1.0  # mm; con menos, el día cuenta como seco (definición del ETCCDI)
LLUVIA_FUERTE = 10.0  # mm
CALOR = 35.0  # °C
NOCHE_TROPICAL = 20.0  # °C


def descargar_diarios(lat: float, lon: float, inicio: int = ANIO_INICIAL, fin: int | None = None) -> pd.DataFrame:
    """Temperatura máxima, mínima y precipitación de cada día en un punto."""
    fin = fin or dt.date.today().year
    lat, lon = round(lat, 2), round(lon, 2)
    ruta = CACHE.ruta(f"diario_{lat:+.2f}_{lon:+.2f}_{inicio}_{fin}.csv")
    if CACHE.vigente(ruta):
        return CACHE.leer(ruta)
    consulta = {"parameters": ",".join(PARAMETROS), "community": "AG", "latitude": lat, "longitude": lon,
                "start": f"{inicio}0101", "end": f"{fin}1231", "format": "JSON"}
    try:
        respuesta = requests.get(POWER_DIARIO_URL, params=consulta, timeout=90)
        respuesta.raise_for_status()
        parametros = respuesta.json()["properties"]["parameter"]
        tabla = pd.DataFrame({codigo: pd.Series(parametros[codigo], dtype=float) for codigo in PARAMETROS})
        tabla.index = pd.to_datetime(tabla.index, format="%Y%m%d")
    except (requests.RequestException, KeyError, ValueError) as error:
        if ruta.exists():  # sin conexión: mejor datos viejos que ninguno
            return CACHE.leer(ruta)
        raise ErrorDeDatos(f"NASA POWER no entregó los datos diarios de ({lat}, {lon}): {error}") from error
    tabla = tabla.sort_index().replace(SIN_DATO, np.nan).dropna(how="all")
    CACHE.guardar(tabla, ruta, float_format="%.4g")
    return tabla


def racha_mas_larga(condicion: np.ndarray) -> int:
    """Longitud de la racha más larga de días seguidos que cumplen la condición."""
    mayor = actual = 0
    for cumple in condicion:
        actual = actual + 1 if cumple else 0
        mayor = max(mayor, actual)
    return mayor


def indices_anuales(diarios: pd.DataFrame) -> pd.DataFrame:
    """Un valor por año de cada índice. Solo cuentan los años con al menos MIN_DIAS días de datos.

    Cada año se fecha el 1 de julio para que la tabla se pueda unir con las series mensuales.
    """
    maxima, minima, lluvia = (diarios[c] for c in PARAMETROS)
    base = maxima.loc[str(PERIODO_BASE[0]):str(PERIODO_BASE[1])].dropna()
    umbral_local = float(np.percentile(base, PERCENTIL_CALOR)) if len(base) > 3650 else np.nan

    filas = {}
    for anio, del_anio in diarios.groupby(diarios.index.year):
        if del_anio.notna().all(axis=1).sum() < MIN_DIAS:
            continue  # año incompleto (el año en curso, por ejemplo): sus conteos no son comparables
        tx, tn, pr = del_anio["T2M_MAX"], del_anio["T2M_MIN"], del_anio["PRECTOTCORR"]
        filas[pd.Timestamp(anio, 7, 1)] = {
            "EXT_TXX": tx.max(),
            "EXT_TNN": tn.min(),
            "EXT_DIAS_35": float((tx > CALOR).sum()),
            "EXT_DIAS_CALOR": float((tx > umbral_local).sum()) if np.isfinite(umbral_local) else np.nan,
            "EXT_NOCHES_20": float((tn > NOCHE_TROPICAL).sum()),
            "EXT_RX1": pr.max(),
            "EXT_R10": float((pr >= LLUVIA_FUERTE).sum()),
            "EXT_CDD": float(racha_mas_larga((pr.fillna(0) < DIA_HUMEDO).to_numpy())),
        }
    return pd.DataFrame.from_dict(filas, orient="index").sort_index()


def tabla_de_extremos(lat: float, lon: float) -> pd.DataFrame:
    """Los índices anuales de extremos de un punto."""
    return indices_anuales(descargar_diarios(lat, lon))
