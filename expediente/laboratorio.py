"""Laboratorio de falsos positivos: ¿cuántas tendencias inventa cada prueba?

Fabrica series que por construcción no tienen tendencia (o tienen una conocida) y sí
autocorrelación, como las series reales del clima, y cuenta cuántas veces cada prueba
declara una tendencia significativa. Es la misma simulación de `validacion/calibracion.py`,
en pequeño, para verla en vivo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import estadistica as est


def ruido_ar1(rng: np.random.Generator, n: int, phi: float) -> np.ndarray:
    """Ruido autorregresivo de primer orden, AR(1), con desviación estándar 1."""
    e = rng.normal(0, np.sqrt(1 - phi ** 2), n)
    x = np.empty(n)
    x[0] = rng.normal()
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


@dataclass(frozen=True)
class Ejemplo:
    """Una serie simulada, con el valor p que le da cada prueba."""

    t: np.ndarray
    y: np.ndarray
    p_clasica: float
    p_corregida: float


@dataclass(frozen=True)
class Simulacion:
    series: int
    clasica: float  # % de series que la prueba de Mann-Kendall clásica declara significativas
    corregida: float  # % con Mann-Kendall tras el preblanqueo
    prueba_t: float  # % con la prueba t de la pendiente y tamaño de muestra efectivo
    ejemplo: Ejemplo | None  # una serie que la clásica declara significativa y la corregida no


def simular(anios: int, phi: float, series: int, pendiente_por_decada: float = 0.0, semilla: int = 0) -> Simulacion:
    """Aplica las pruebas a `series` series mensuales simuladas de `anios` años.

    `phi` es la autocorrelación entre un mes y el siguiente. `pendiente_por_decada` es la
    tendencia real que se les añade, en desviaciones estándar por década (0 = ninguna: todo
    lo que se detecte es un falso positivo).
    """
    rng = np.random.default_rng(semilla)
    n = 12 * anios
    t = np.arange(n) / 12
    cuenta = {"clasica": 0, "corregida": 0, "t": 0}
    ejemplo = None
    for _ in range(series):
        y = pendiente_por_decada / 10 * t + ruido_ar1(rng, n, phi)
        p_clasica = est.mann_kendall(y).p
        p_corregida = est.mann_kendall_sin_memoria(t, y).prueba.p
        cuenta["clasica"] += p_clasica < est.ALFA
        cuenta["corregida"] += p_corregida < est.ALFA
        cuenta["t"] += est.regresion_lineal(t, y).p < est.ALFA
        if p_clasica < est.ALFA <= p_corregida and (ejemplo is None or p_clasica < ejemplo.p_clasica):
            ejemplo = Ejemplo(t, y, float(p_clasica), float(p_corregida))
    return Simulacion(series, 100 * cuenta["clasica"] / series, 100 * cuenta["corregida"] / series,
                      100 * cuenta["t"] / series, ejemplo)
