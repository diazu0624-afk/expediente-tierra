"""¿Qué tan seguido acusa el detective a un inocente?

Genera series sintéticas con memoria (ruido AR(1)) y sin tendencia, y cuenta cuántas
veces cada prueba declara una tendencia "significativa" (falsos positivos; lo ideal es
5 %). Después repite con una tendencia real para medir cuántas detecta (potencia).

Uso:  .venv/bin/python -m validacion.calibracion [repeticiones]
"""

from __future__ import annotations

import sys

import numpy as np

from expediente import estadistica as est


def ruido_ar1(rng: np.random.Generator, n: int, phi: float) -> np.ndarray:
    """Ruido AR(1) con desviación estándar 1."""
    e = rng.normal(0, np.sqrt(1 - phi**2), n)
    x = np.empty(n)
    x[0] = rng.normal()
    for k in range(1, n):
        x[k] = phi * x[k - 1] + e[k]
    return x


def tasas(n: int, paso: float, phi: float, pendiente: float, repeticiones: int, semilla: int) -> dict:
    rng = np.random.default_rng(semilla)
    t = np.arange(n) * paso
    cuenta = dict.fromkeys(["MK ingenuo", "MK sin memoria", "t (n efectivo)", "IC bootstrap"], 0)
    for k in range(repeticiones):
        y = pendiente * t + ruido_ar1(rng, n, phi)
        cuenta["MK ingenuo"] += est.mann_kendall(y).p < est.ALFA
        cuenta["MK sin memoria"] += est.mann_kendall_sin_memoria(t, y).prueba.p < est.ALFA
        cuenta["t (n efectivo)"] += est.regresion_lineal(t, y).p < est.ALFA
        bajo, alto = est.ic_historias_alternativas(t, y, repeticiones=1000, semilla=k)
        cuenta["IC bootstrap"] += not (bajo <= 0 <= alto)
    return {nombre: 100 * c / repeticiones for nombre, c in cuenta.items()}


def imprimir(titulo: str, escenarios: list[tuple], repeticiones: int) -> None:
    print(f"\n{titulo}")
    encabezado = None
    for etiqueta, n, paso, phi, pendiente in escenarios:
        fila = tasas(n, paso, phi, pendiente, repeticiones, semilla=int(phi * 100) + n)
        if encabezado is None:
            encabezado = list(fila)
            print(f"{'escenario':34s}" + "".join(f"{c:>17s}" for c in encabezado))
        print(f"{etiqueta:34s}" + "".join(f"{fila[c]:16.1f}%" for c in encabezado))


if __name__ == "__main__":
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    mensual = [(f"mensual 45 años, memoria {phi}", 540, 1 / 12, phi, 0.0) for phi in (0.0, 0.3, 0.6, 0.9)]
    anual = [(f"anual 45 años, memoria {phi}", 45, 1.0, phi, 0.0) for phi in (0.0, 0.2, 0.4)]
    imprimir("FALSOS POSITIVOS (sin tendencia; ideal 5 %)", mensual + anual, reps)
    # Tendencia real de 0.2 desviaciones estándar por década.
    con_tendencia = [(f"mensual 45 años, memoria {phi}", 540, 1 / 12, phi, 0.02) for phi in (0.3, 0.6, 0.9)]
    con_tendencia += [("anual 45 años, memoria 0.2", 45, 1.0, 0.2, 0.02)]
    imprimir("POTENCIA (tendencia real de 0.2 sigma por década)", con_tendencia, reps)
