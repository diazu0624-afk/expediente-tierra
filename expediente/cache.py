"""Caché en disco de las tablas descargadas.

Cada tabla se guarda como CSV y, junto a ella, la fecha en que se bajó de su fuente. Con eso
la herramienta funciona sin conexión con los lugares ya consultados y sabe cuándo conviene
volver a descargar.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path

import pandas as pd


class CacheEnDisco:
    """Una carpeta de tablas descargadas y el registro de cuándo se bajó cada una.

    El estado (la carpeta, el índice de fechas, el plazo de vigencia) es privado: el resto
    del programa solo pregunta si un archivo sigue vigente, lo lee o lo guarda.
    """

    def __init__(self, carpeta: Path, dias_de_vigencia: int):
        self._carpeta = carpeta
        self._indice = carpeta / "descargas.json"  # nombre de archivo -> fecha de descarga
        self._dias_de_vigencia = dias_de_vigencia
        self._candado = threading.Lock()  # varias descargas en paralelo escriben el mismo índice

    def ruta(self, nombre: str) -> Path:
        """Dónde vive (o vivirá) el archivo con ese nombre."""
        return self._carpeta / nombre

    def fecha_de_descarga(self, ruta: Path) -> dt.date | None:
        """Cuándo se bajó de la fuente un archivo de la caché (None si no hay registro)."""
        fecha = self._fechas().get(ruta.name)
        return dt.date.fromisoformat(fecha) if fecha else None

    def vigente(self, ruta: Path) -> bool:
        """El archivo existe y se descargó dentro del plazo de vigencia."""
        fecha = self.fecha_de_descarga(ruta)
        return ruta.exists() and fecha is not None and (dt.date.today() - fecha).days <= self._dias_de_vigencia

    def leer(self, ruta: Path) -> pd.DataFrame:
        return pd.read_csv(ruta, index_col=0, parse_dates=True)

    def guardar(self, tabla: pd.DataFrame, ruta: Path, **formato) -> None:
        """Escribe la tabla y anota la fecha de hoy como su fecha de descarga."""
        self._carpeta.mkdir(exist_ok=True)
        tabla.to_csv(ruta, **formato)
        with self._candado:
            fechas = self._fechas()
            fechas[ruta.name] = dt.date.today().isoformat()
            self._indice.write_text(json.dumps(fechas, indent=0, sort_keys=True))

    def _fechas(self) -> dict[str, str]:
        try:
            return json.loads(self._indice.read_text())
        except (OSError, ValueError):
            return {}
