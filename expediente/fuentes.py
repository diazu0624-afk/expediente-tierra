"""Las fuentes de datos de la herramienta, todas con la misma cara.

Los datos llegan por tres caminos: la API mensual de NASA POWER, Google Earth Engine y la API
diaria de NASA POWER (de la que salen los índices de extremos). Cada camino es una subclase
de `FuenteDeDatos` y responde a las mismas dos preguntas: las series de un punto y el cubo de
una región. Quien pide los datos no necesita saber de qué fuente vienen: pregunta
`fuente_de(variable)` y usa lo que le entreguen.

Las descargas en sí están en `datos.py`, `datos_gee.py` y `extremos.py`; estas clases solo
deciden a cuál de ellas acudir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

import pandas as pd

from . import datos, datos_gee, extremos
from .datos import ErrorDeDatos
from .idioma import T
from .variables import CATALOGO, Variable


class FuenteDeDatos(ABC):
    """De dónde sale un grupo de variables y cómo se le piden los datos."""

    origen: str  # el valor de `Variable.origen` que esta fuente atiende
    indispensable = False  # True: si esta fuente falla, el análisis del punto no puede seguir

    def variables(self) -> tuple[Variable, ...]:
        """Las variables del catálogo que llegan por esta fuente."""
        return tuple(v for v in CATALOGO if v.origen == self.origen)

    @abstractmethod
    def series_del_punto(self, lat: float, lon: float, variables: Sequence[Variable]) -> pd.DataFrame:
        """Las series de esas variables en un punto. Filas = fechas, columnas = códigos.

        Una variable que no existe en el punto simplemente no aparece entre las columnas.
        """

    def cubo_de_la_region(self, lat: float, lon: float, variable: Variable, lado: int) -> pd.DataFrame:
        """La serie de la variable en cada celda de un recuadro de `lado` grados alrededor del punto.

        Filas = meses, columnas = celdas nombradas "lat,lon". Por omisión una fuente no tiene
        datos por región; las que sí, redefinen este método.
        """
        raise ErrorDeDatos(T("Esta variable solo tiene datos para el punto, no para la región.",
                             "This variable only has data for the point, not for the region."))


class PowerMensual(FuenteDeDatos):
    """Reanálisis MERRA-2 y CERES, mes a mes, por la API de NASA POWER."""

    origen = "power"
    indispensable = True

    def series_del_punto(self, lat: float, lon: float, variables: Sequence[Variable]) -> pd.DataFrame:
        return datos.descargar_power(lat, lon, [v.codigo for v in variables])

    def cubo_de_la_region(self, lat: float, lon: float, variable: Variable, lado: int) -> pd.DataFrame:
        return datos.descargar_region(lat, lon, variable.codigo, lado)


class EarthEngine(FuenteDeDatos):
    """Satélites y modelos (GPM, MODIS, GRACE, OMI, FLDAS, OISST) por Google Earth Engine."""

    origen = "gee"
    PETICIONES_A_LA_VEZ = 6

    def series_del_punto(self, lat: float, lon: float, variables: Sequence[Variable]) -> pd.DataFrame:
        with ThreadPoolExecutor(self.PETICIONES_A_LA_VEZ) as ejecutor:
            series = list(ejecutor.map(lambda v: self._serie(lat, lon, v), variables))
        return pd.concat([s for s in series if s is not None], axis=1) if any(s is not None for s in series) else pd.DataFrame()

    def cubo_de_la_region(self, lat: float, lon: float, variable: Variable, lado: int) -> pd.DataFrame:
        return datos_gee.recortar(datos_gee.descargar_cubo(lat, lon, variable.codigo), lat, lon, lado)

    @staticmethod
    def _serie(lat: float, lon: float, variable: Variable) -> pd.Series | None:
        """La serie de la celda más cercana al punto; None si la variable no existe ahí o no se pudo bajar."""
        try:
            serie = datos_gee.serie_del_punto(datos_gee.descargar_cubo(lat, lon, variable.codigo), lat, lon)
        except ErrorDeDatos:
            return None  # una variable que falla no detiene a las demás
        return None if serie.empty else serie.rename(variable.codigo)


class PowerDiario(FuenteDeDatos):
    """Índices anuales de extremos, calculados con los datos de cada día de NASA POWER."""

    origen = "diario"

    def series_del_punto(self, lat: float, lon: float, variables: Sequence[Variable]) -> pd.DataFrame:
        indices = extremos.tabla_de_extremos(lat, lon)
        return indices[[c for c in indices.columns if c in {v.codigo for v in variables}]]

    def cubo_de_la_region(self, lat: float, lon: float, variable: Variable, lado: int) -> pd.DataFrame:
        raise ErrorDeDatos(T("Los índices de extremos se calculan con datos diarios, que solo existen para el punto.",
                             "Extremes indices are computed from daily data, which only exist for the point."))


# En este orden se unen sus columnas en la tabla de un punto.
FUENTES: tuple[FuenteDeDatos, ...] = (PowerMensual(), EarthEngine(), PowerDiario())
_POR_ORIGEN = {fuente.origen: fuente for fuente in FUENTES}


def fuente_de(variable: Variable) -> FuenteDeDatos:
    """La fuente por la que llegan los datos de una variable."""
    return _POR_ORIGEN[variable.origen]
