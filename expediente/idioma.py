"""Idioma de la interfaz: español (por omisión) o inglés.

Cada texto que ve el usuario se escribe en los dos idiomas, uno junto al otro:

    T("Tasa de cambio", "Rate of change")

`T` devuelve el que corresponde al idioma de la sesión. El idioma vive en una variable de
contexto: cada sesión de la app fija el suyo al empezar a dibujar la página.
"""

from __future__ import annotations

from contextvars import ContextVar

_idioma: ContextVar[str] = ContextVar("idioma", default="es")

IDIOMAS = {"es": "Español", "en": "English"}


def fijar(codigo: str) -> None:
    _idioma.set("en" if codigo == "en" else "es")


def actual() -> str:
    return _idioma.get()


def en_ingles() -> bool:
    return _idioma.get() == "en"


def T(es: str, en: str) -> str:
    """El texto en el idioma de la sesión."""
    return en if _idioma.get() == "en" else es


# Textos cortos que se repiten como datos (unidades, temas, fuentes): se traducen por tabla.
_FRASES: dict[str, str] = {}


def registrar(frases: dict[str, str]) -> None:
    _FRASES.update(frases)


def tr(texto: str) -> str:
    """Traduce un texto corto registrado (una unidad, un tema...); si no lo está, lo deja igual."""
    return _FRASES.get(texto, texto) if _idioma.get() == "en" else texto


class Tupla:
    """Tupla de textos en los dos idiomas; se comporta como la del idioma de la sesión."""

    def __init__(self, es: tuple[str, ...], en: tuple[str, ...]):
        self._es, self._en = tuple(es), tuple(en)

    def _actual(self) -> tuple[str, ...]:
        return self._en if _idioma.get() == "en" else self._es

    def __getitem__(self, indice):
        return self._actual()[indice]

    def __iter__(self):
        return iter(self._actual())

    def __len__(self) -> int:
        return len(self._es)


class Dicc(dict):
    """Diccionario clave -> (español, inglés); al consultarlo entrega el texto del idioma de la sesión."""

    def __getitem__(self, clave):
        es, en = super().__getitem__(clave)
        return en if _idioma.get() == "en" else es
