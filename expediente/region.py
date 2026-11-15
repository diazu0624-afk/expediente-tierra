"""La región: dónde cambia una variable y cuánto cambia en promedio."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import estadistica as est
from .caso import TODO_EL_ANIO, _motivo_imposible, serie_anual
from .variables import Variable


def _coordenadas(cubo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    pares = np.array([c.split(",") for c in cubo.columns], dtype=float)
    return pares[:, 0], pares[:, 1]


def promedio_regional(cubo: pd.DataFrame) -> pd.Series:
    """Promedio de todas las celdas, mes a mes.

    Cada celda pesa según su área: las celdas cercanas a los polos son más angostas, así
    que pesan menos (coseno de la latitud). Las celdas sin dato no cuentan.
    """
    lats, _ = _coordenadas(cubo)
    pesos = np.cos(np.radians(lats))
    valores = cubo.to_numpy()
    validos = ~np.isnan(valores)
    suma = np.where(validos, valores * pesos, 0.0).sum(axis=1)
    peso_total = (validos * pesos).sum(axis=1)
    return pd.Series(np.where(peso_total > 0, suma / np.where(peso_total > 0, peso_total, 1), np.nan),
                     index=cubo.index).dropna()


def mapa_de_tendencias(cubo: pd.DataFrame, variable: Variable,
                       meses: tuple[int, ...] = TODO_EL_ANIO) -> pd.DataFrame:
    """Tendencia de cada celda de la región, con un valor por año (o por temporada).

    Columnas: lat, lon, anios (tamaño de muestra de la celda), pendiente_decada, p,
    p_ajustada, significativa. Como se prueban
    cientos de celdas a la vez, los valores p se ajustan con Benjamini-Hochberg. Las
    celdas donde la variable no se puede medir (p. ej. humedad del suelo en el mar)
    quedan fuera.
    """
    lats, lons = _coordenadas(cubo)
    filas = []
    for columna, lat, lon in zip(cubo.columns, lats, lons):
        anual = serie_anual(cubo[columna].loc[str(variable.desde):].dropna(), meses)
        if _motivo_imposible(anual):
            continue
        anios, valores = anual.index.to_numpy(dtype=float), anual.to_numpy()
        recta = est.regresion_lineal(anios, valores)
        mk = est.mann_kendall_sin_memoria(anios, valores)
        filas.append((lat, lon, len(anual), recta.pendiente * 10, mk.prueba.p))
    tabla = pd.DataFrame(filas, columns=["lat", "lon", "anios", "pendiente_decada", "p"])
    tabla["p_ajustada"] = est.benjamini_hochberg(tabla["p"].to_numpy()) if len(tabla) else []
    tabla["significativa"] = tabla["p_ajustada"] < est.ALFA
    return tabla


def resumen(mapa: pd.DataFrame) -> dict[str, float]:
    """Porcentaje de celdas que suben o bajan de forma significativa."""
    if mapa.empty:
        return {"sube": 0.0, "baja": 0.0, "celdas": 0, "anios_min": 0, "anios_max": 0}
    firmes = mapa[mapa["significativa"]]
    return {"sube": 100 * float((firmes["pendiente_decada"] > 0).sum()) / len(mapa),
            "baja": 100 * float((firmes["pendiente_decada"] < 0).sum()) / len(mapa),
            "celdas": len(mapa), "anios_min": int(mapa["anios"].min()), "anios_max": int(mapa["anios"].max())}
