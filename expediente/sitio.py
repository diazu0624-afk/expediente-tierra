"""Todas las variables del catálogo en un punto, sin importar de qué fuente vengan."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import datos, datos_gee
from .variables import CATALOGO, SOLO_MAR, SOLO_TIERRA

MAR_DE_REFERENCIA = "MAR_SST"
SUELO_DE_REFERENCIA = "GWETROOT"


def _serie_de_satelite(lat: float, lon: float, codigo: str) -> pd.Series | None:
    try:
        serie = datos_gee.serie_del_punto(datos_gee.descargar_cubo(lat, lon, codigo), lat, lon)
    except datos.ErrorDeDatos:
        return None  # sin sesión de Earth Engine: el análisis sigue con las demás variables
    return None if serie.empty else serie.rename(codigo)


def tabla_del_punto(lat: float, lon: float) -> pd.DataFrame:
    """Series mensuales de un punto: reanálisis por NASA POWER más lo que responda Earth Engine.

    Filas = meses, columnas = códigos de variable. Las variables que no existen en el punto
    (las del océano en tierra firme, por ejemplo) simplemente no aparecen.
    """
    tabla = datos.descargar_power(lat, lon, [v.codigo for v in CATALOGO if v.origen == "power"])
    codigos = [v.codigo for v in CATALOGO if v.origen == "gee"]
    with ThreadPoolExecutor(6) as ejecutor:
        series = list(ejecutor.map(lambda codigo: _serie_de_satelite(lat, lon, codigo), codigos))
    for serie in series:
        if serie is not None:
            tabla = tabla.join(serie, how="outer")
    return tabla.drop(columns=[c for c in tabla.columns if c in fuera_de_lugar(tabla)])


def fuera_de_lugar(tabla: pd.DataFrame) -> frozenset[str]:
    """Variables que el punto no puede tener: las del mar en tierra firme y las de tierra en mar abierto.

    Hay mar cerca si el análisis OISST (que trae máscara de océano) tiene datos en el punto.
    Es mar abierto si, además, el reanálisis no tiene suelo ahí (humedad de raíces sin datos).
    """
    hay_mar = MAR_DE_REFERENCIA in tabla and tabla[MAR_DE_REFERENCIA].notna().any()
    sin_suelo = SUELO_DE_REFERENCIA in tabla and not tabla[SUELO_DE_REFERENCIA].notna().any()
    if not hay_mar:
        return SOLO_MAR
    return SOLO_TIERRA if sin_suelo else frozenset()
