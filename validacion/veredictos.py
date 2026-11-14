"""¿Qué tan seguido el veredicto completo se equivoca?

Arma series mensuales sintéticas (estaciones + ruido con memoria), les aplica las cinco
pruebas y cuenta cuántas alcanzan cada nivel de evidencia. Sin tendencia, cualquier
"evidencia fuerte" o "sólida" es una acusación falsa.

Uso:  .venv/bin/python -m validacion.veredictos [repeticiones]
"""

from __future__ import annotations

import sys
from collections import Counter

import numpy as np
import pandas as pd

from expediente import caso
from expediente.variables import POR_CODIGO
from validacion.calibracion import ruido_ar1

ANIOS = 45


def serie_sintetica(rng: np.random.Generator, phi: float, pendiente_anual: float) -> pd.Series:
    n = ANIOS * 12
    t = np.arange(n) / 12
    indice = pd.date_range("1981-01-01", periods=n, freq="MS")
    return pd.Series(8 * np.sin(2 * np.pi * t) + pendiente_anual * t + ruido_ar1(rng, n, phi), index=indice)


def niveles(phi: float, pendiente_anual: float, repeticiones: int) -> Counter:
    rng = np.random.default_rng(int(phi * 100) + int(pendiente_anual * 1e4))
    cuenta = Counter()
    for _ in range(repeticiones):
        cuenta[caso.interrogar(serie_sintetica(rng, phi, pendiente_anual), POR_CODIGO["T2M"]).nivel] += 1
    return cuenta


if __name__ == "__main__":
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    print(f"{'escenario':44s}" + "".join(f"{caso.NIVELES[k]:>26s}" for k in caso.NIVELES))
    for etiqueta, phi, pendiente in [
        ("sin tendencia, memoria 0.3", 0.3, 0.0),
        ("sin tendencia, memoria 0.6", 0.6, 0.0),
        ("sin tendencia, memoria 0.9", 0.9, 0.0),
        ("tendencia 0.2 sigma/década, memoria 0.3", 0.3, 0.02),
        ("tendencia 0.2 sigma/década, memoria 0.6", 0.6, 0.02),
    ]:
        cuenta = niveles(phi, pendiente, reps)
        print(f"{etiqueta:44s}" + "".join(f"{100 * cuenta[k] / reps:25.1f}%" for k in caso.NIVELES), flush=True)
