"""Acceso a datos: NASA POWER (series mensuales) y búsqueda de lugares."""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import requests

POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
POWER_REGION_URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"
GEOCODIFICADOR_URL = "https://geocoding-api.open-meteo.com/v1/search"
ANIO_INICIAL = 1981
MAX_PARAMETROS = 20  # límite de la API por petición
SIN_DATO = -999.0
DIR_CACHE = Path(__file__).resolve().parent.parent / "cache_power"


class ErrorDeDatos(RuntimeError):
    """La fuente de datos no respondió o respondió algo inesperado."""


def _a_tabla(parametros: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Convierte la respuesta de POWER ({codigo: {"AAAAMM": valor}}) en una tabla mensual."""
    columnas = {}
    for codigo, valores in parametros.items():
        # La clave "AAAA13" es el promedio anual que calcula POWER; no es un mes.
        meses = {k: v for k, v in valores.items() if not k.endswith("13")}
        indice = pd.to_datetime(list(meses.keys()), format="%Y%m")
        columnas[codigo] = pd.Series(list(meses.values()), index=indice, dtype=float)
    tabla = pd.DataFrame(columnas).sort_index()
    return tabla.replace(SIN_DATO, np.nan)


def _ruta_cache(lat: float, lon: float, codigos: list[str], inicio: int, fin: int) -> Path:
    huella = hashlib.sha1(",".join(sorted(codigos)).encode()).hexdigest()[:10]
    return DIR_CACHE / f"power_{lat:+.2f}_{lon:+.2f}_{inicio}_{fin}_{huella}.csv"


def descargar_power(
    lat: float,
    lon: float,
    codigos: list[str],
    inicio: int = ANIO_INICIAL,
    fin: int | None = None,
    usar_cache: bool = True,
) -> pd.DataFrame:
    """Series mensuales de POWER para un punto. Filas = meses, columnas = códigos.

    Los meses sin dato quedan como NaN. Cada lugar consultado se guarda en disco para que
    los casos ya abiertos funcionen sin internet.
    """
    fin = fin or dt.date.today().year
    lat, lon = round(lat, 2), round(lon, 2)
    ruta = _ruta_cache(lat, lon, codigos, inicio, fin)
    if usar_cache and ruta.exists():
        return pd.read_csv(ruta, index_col=0, parse_dates=True)

    partes = []
    for i in range(0, len(codigos), MAX_PARAMETROS):
        consulta = {
            "parameters": ",".join(codigos[i:i + MAX_PARAMETROS]),
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": inicio,
            "end": fin,
            "format": "JSON",
        }
        try:
            respuesta = requests.get(POWER_URL, params=consulta, timeout=60)
            respuesta.raise_for_status()
            parametros = respuesta.json()["properties"]["parameter"]
        except (requests.RequestException, KeyError, ValueError) as error:
            raise ErrorDeDatos(f"NASA POWER no respondió para ({lat}, {lon}): {error}") from error
        partes.append(_a_tabla(parametros))

    tabla = pd.concat(partes, axis=1)[codigos]
    # El año en curso llega con meses futuros vacíos.
    tabla = tabla.loc[:tabla.dropna(how="all").index.max()]
    if usar_cache:
        DIR_CACHE.mkdir(exist_ok=True)
        tabla.to_csv(ruta)
    return tabla


def caja(lat: float, lon: float, lado: float) -> tuple[float, float, float, float]:
    """Recuadro de `lado` grados centrado en el punto: (lat_min, lat_max, lon_min, lon_max)."""
    medio = lado / 2
    lat_c = min(max(round(lat), -90 + medio), 90 - medio)
    lon_c = min(max(round(lon), -180 + medio), 180 - medio)
    return lat_c - medio, lat_c + medio, lon_c - medio, lon_c + medio


def descargar_region(lat: float, lon: float, codigo: str, lado: float = 8,
                     inicio: int = ANIO_INICIAL, fin: int | None = None) -> pd.DataFrame:
    """Serie mensual de una variable en cada celda de un recuadro.

    Filas = meses; columnas = celdas, nombradas "lat,lon" por su centro. La API regional
    de POWER acepta una variable por petición y recuadros de 2 a 10 grados.
    """
    fin = fin or dt.date.today().year
    lat_min, lat_max, lon_min, lon_max = caja(lat, lon, lado)
    ruta = DIR_CACHE / f"region_{codigo}_{lat_min:+.0f}_{lat_max:+.0f}_{lon_min:+.0f}_{lon_max:+.0f}_{inicio}_{fin}.csv"
    if ruta.exists():
        return pd.read_csv(ruta, index_col=0, parse_dates=True)
    consulta = {"parameters": codigo, "community": "AG", "latitude-min": lat_min,
                "latitude-max": lat_max, "longitude-min": lon_min, "longitude-max": lon_max,
                "start": inicio, "end": fin, "format": "JSON"}
    try:
        respuesta = requests.get(POWER_REGION_URL, params=consulta, timeout=120)
        respuesta.raise_for_status()
        celdas = respuesta.json()["features"]
        columnas = {
            f"{c['geometry']['coordinates'][1]},{c['geometry']['coordinates'][0]}":
                _a_tabla(c["properties"]["parameter"])[codigo]
            for c in celdas
        }
    except (requests.RequestException, KeyError, ValueError, IndexError) as error:
        raise ErrorDeDatos(f"NASA POWER no entregó la región: {error}") from error
    tabla = pd.DataFrame(columnas).sort_index()
    tabla = tabla.loc[:tabla.dropna(how="all").index.max()]
    DIR_CACHE.mkdir(exist_ok=True)
    tabla.to_csv(ruta)
    return tabla


def buscar_lugar(texto: str, maximo: int = 5) -> list[dict]:
    """Busca un lugar por nombre. Devuelve [{"nombre", "lat", "lon"}], el más probable primero."""
    consulta = {"name": texto, "count": maximo, "language": "es", "format": "json"}
    try:
        respuesta = requests.get(GEOCODIFICADOR_URL, params=consulta, timeout=20)
        respuesta.raise_for_status()
        resultados = respuesta.json().get("results", [])
    except (requests.RequestException, ValueError) as error:
        raise ErrorDeDatos(f"No se pudo buscar «{texto}»: {error}") from error
    lugares = []
    for r in resultados:
        partes = [r.get("name"), r.get("admin1"), r.get("country")]
        nombre = ", ".join(dict.fromkeys(p for p in partes if p))
        lugares.append({"nombre": nombre, "lat": r["latitude"], "lon": r["longitude"]})
    return lugares
