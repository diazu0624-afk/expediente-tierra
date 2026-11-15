"""Todas las variables del catálogo en un punto, sin importar de qué fuente vengan."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .datos import ErrorDeDatos
from .fuentes import FUENTES, FuenteDeDatos
from .variables import SOLO_MAR, SOLO_TIERRA

MAR_DE_REFERENCIA = "MAR_SST"
SUELO_DE_REFERENCIA = "GWETROOT"


def _series_de(fuente: FuenteDeDatos, lat: float, lon: float) -> pd.DataFrame | None:
    """Lo que una fuente tiene del punto; None si falló y el análisis puede seguir sin ella."""
    try:
        return fuente.series_del_punto(lat, lon, fuente.variables())
    except ErrorDeDatos:
        if fuente.indispensable:
            raise
        return None


def tabla_del_punto(lat: float, lon: float) -> pd.DataFrame:
    """Series de un punto, de todas las fuentes: reanálisis mensual, satélites y modelos, e
    índices anuales de extremos (un valor por año, fechado el 1 de julio).

    Filas = meses, columnas = códigos de variable. Las variables que no existen en el punto
    (las del océano en tierra firme, por ejemplo) simplemente no aparecen. A cada fuente se le
    pide lo mismo, `series_del_punto`, y todas se consultan a la vez.
    """
    with ThreadPoolExecutor(len(FUENTES)) as ejecutor:
        partes = list(ejecutor.map(lambda fuente: _series_de(fuente, lat, lon), FUENTES))
    tabla = pd.DataFrame()
    for parte in partes:
        if parte is not None and parte.shape[1]:
            tabla = parte if tabla.empty else tabla.join(parte, how="outer")
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
