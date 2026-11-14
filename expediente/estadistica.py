"""Motor estadístico: las pruebas con las que se interroga a una tendencia.

Las funciones reciben arreglos de numpy ordenados en el tiempo, sin NaN y con paso
uniforme (un valor por mes o por año), salvo que se indique lo contrario.

Referencias:
- Mann (1945), Kendall (1975): prueba de tendencia monótona.
- Sen (1968): pendiente robusta (mediana de pendientes entre pares).
- Zhang et al. (2000), Wang y Swail (2001): Mann-Kendall con preblanqueo iterativo.
- Santer et al. (2000): prueba t con tamaño de muestra efectivo.
- Weatherhead et al. (1998): años de datos necesarios para detectar una tendencia.
- Benjamini y Hochberg (1995): control de descubrimientos falsos.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf, sqrt

import numpy as np
import pandas as pd
from scipy import signal, stats

ALFA = 0.05


def quitar_ciclo_estacional(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Separa una serie mensual en (anomalías, climatología).

    La climatología es el promedio de cada mes del calendario (todos los eneros, todos
    los febreros...). La anomalía es cuánto se aparta cada mes de su promedio.
    """
    climatologia = serie.groupby(serie.index.month).mean()
    anomalias = serie - climatologia.reindex(serie.index.month).to_numpy()
    return anomalias, climatologia


def autocorrelacion_lag1(x: np.ndarray) -> float:
    """Qué tanto se parece cada valor al anterior (la "memoria" de la serie), entre -1 y 1."""
    x = np.asarray(x, dtype=float)
    if x.size < 3:
        return 0.0
    d = x - x.mean()
    denominador = float(np.dot(d, d))
    if denominador == 0:
        return 0.0
    return float(np.dot(d[:-1], d[1:]) / denominador)


def memoria_de_residuos(residuos: np.ndarray) -> float:
    """Autocorrelación lag 1 de los residuos de una recta, corregida por sesgo.

    Tras quitar una recta, la autocorrelación muestral subestima la real en
    (2 + 4·phi)/n; aquí se despeja phi. Importa en series cortas (anuales).
    """
    n = np.asarray(residuos).size
    if n < 6:
        return 0.0
    return min((n * autocorrelacion_lag1(residuos) + 2) / (n - 4), 0.98)


@dataclass(frozen=True)
class MannKendall:
    s: float
    var_s: float
    z: float
    p: float
    tau: float
    n: int


def mann_kendall(x: np.ndarray) -> MannKendall:
    """Prueba de Mann-Kendall: ¿los valores tienden a subir (o bajar) con el tiempo?

    Compara cada par de valores y cuenta cuántas veces el posterior es mayor menos
    cuántas es menor (S). Incluye la corrección por empates y la de continuidad.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 3:
        return MannKendall(0.0, 0.0, 0.0, 1.0, 0.0, n)
    i, j = np.triu_indices(n, k=1)
    s = float(np.sign(x[j] - x[i]).sum())
    _, cuentas = np.unique(x, return_counts=True)
    empates = float((cuentas * (cuentas - 1) * (2 * cuentas + 5)).sum())
    var_s = (n * (n - 1) * (2 * n + 5) - empates) / 18
    if var_s <= 0 or s == 0:
        z = 0.0
    else:
        z = (s - np.sign(s)) / sqrt(var_s)
    p = float(2 * stats.norm.sf(abs(z)))
    return MannKendall(s, var_s, z, p, s / (n * (n - 1) / 2), n)


@dataclass(frozen=True)
class PendienteSen:
    pendiente: float
    intercepto: float
    ic_bajo: float
    ic_alto: float


def pendiente_sen(t: np.ndarray, y: np.ndarray) -> PendienteSen:
    """Pendiente de Theil-Sen (mediana de las pendientes entre todos los pares) e IC al 95 %."""
    pendiente, intercepto, bajo, alto = stats.theilslopes(y, t, alpha=1 - ALFA)
    return PendienteSen(float(pendiente), float(intercepto), float(bajo), float(alto))


def _mediana_de_pendientes(t: np.ndarray, y: np.ndarray) -> float:
    i, j = np.triu_indices(t.size, k=1)
    return float(np.median((y[j] - y[i]) / (t[j] - t[i])))


@dataclass(frozen=True)
class MannKendallSinMemoria:
    prueba: MannKendall
    r1: float
    corregida: bool


def mann_kendall_sin_memoria(t: np.ndarray, y: np.ndarray, max_iter: int = 30) -> MannKendallSinMemoria:
    """Mann-Kendall con preblanqueo iterativo (Zhang et al., 2000; Wang y Swail, 2001).

    Una serie con memoria (cada mes se parece al anterior) hace que Mann-Kendall vea
    tendencias donde no las hay. El remedio es probar la serie "sin memoria"

        w[k] = (y[k] - r1·y[k-1]) / (1 - r1)

    que conserva la pendiente y deja el ruido del tamaño que de verdad estorba. Como r1
    y la pendiente dependen una de la otra, se estiman por turnos hasta que se
    estabilizan. Solo se corrige la memoria positiva, que es la que infla los falsos
    positivos.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    pendiente = _mediana_de_pendientes(t, y)
    r1 = memoria_de_residuos(y - pendiente * t)
    if r1 <= 0:
        return MannKendallSinMemoria(mann_kendall(y), r1, False)
    for _ in range(max_iter):
        w = (y[1:] - r1 * y[:-1]) / (1 - r1)
        nueva_pendiente = _mediana_de_pendientes(t[1:], w)
        nuevo_r1 = min(max(memoria_de_residuos(y - nueva_pendiente * t), 1e-6), 0.98)
        estable = (abs(nuevo_r1 - r1) < 1e-4
                   and abs(nueva_pendiente - pendiente) <= 1e-4 * abs(pendiente) + 1e-12)
        pendiente, r1 = nueva_pendiente, nuevo_r1
        if estable:
            break
    w = (y[1:] - r1 * y[:-1]) / (1 - r1)
    return MannKendallSinMemoria(mann_kendall(w), r1, True)


@dataclass(frozen=True)
class Regresion:
    pendiente: float
    intercepto: float
    p_ingenuo: float
    r1: float
    n: int
    n_efectivo: float
    p: float
    ic_bajo: float
    ic_alto: float


def regresion_lineal(t: np.ndarray, y: np.ndarray) -> Regresion:
    """Recta de mínimos cuadrados y prueba t de su pendiente (Santer et al., 2000).

    `p_ingenuo` supone que cada dato es independiente. `p` descuenta la memoria de la
    serie: n datos que se parecen entre sí valen como n_efectivo = n(1-r1)/(1+r1) datos
    independientes.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    n = t.size
    tc = t - t.mean()
    sxx = float(np.dot(tc, tc))
    pendiente = float(np.dot(tc, y - y.mean()) / sxx)
    intercepto = float(y.mean() - pendiente * t.mean())
    residuos = y - (intercepto + pendiente * t)
    sse = float(np.dot(residuos, residuos))
    r1 = memoria_de_residuos(residuos)
    n_ef = max(n * (1 - r1) / (1 + r1), 3.0) if r1 > 0 else float(n)

    if sse == 0:  # ajuste perfecto: no hay incertidumbre que estimar
        p = 0.0 if pendiente != 0 else 1.0
        return Regresion(pendiente, intercepto, p, r1, n, n_ef, p, pendiente, pendiente)

    def _p_y_error(grados: float) -> tuple[float, float]:
        error = sqrt(sse / grados / sxx)
        return float(2 * stats.t.sf(abs(pendiente / error), grados)), error

    p_ingenuo, _ = _p_y_error(n - 2)
    p, error = _p_y_error(n_ef - 2)
    margen = float(stats.t.ppf(1 - ALFA / 2, n_ef - 2)) * error
    return Regresion(pendiente, intercepto, p_ingenuo, r1, n, n_ef, p,
                     pendiente - margen, pendiente + margen)


def ic_historias_alternativas(
    t: np.ndarray, y: np.ndarray, repeticiones: int = 2000, semilla: int = 0
) -> tuple[float, float]:
    """Intervalo de confianza al 95 % de la pendiente por bootstrap con memoria (AR(1)).

    Se fabrican miles de "historias alternativas": la misma recta más un ruido nuevo,
    armado barajando los sobresaltos de la serie real y devolviéndoles su memoria. El
    intervalo es el rango donde cae el 95 % de las pendientes de esas historias.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    n = t.size
    tc = t - t.mean()
    sxx = float(np.dot(tc, tc))
    pendiente = float(np.dot(tc, y - y.mean()) / sxx)
    residuos = (y - y.mean()) - pendiente * tc
    phi = max(memoria_de_residuos(residuos), 0.0)
    sobresaltos = residuos[1:] - phi * residuos[:-1]
    sobresaltos = sobresaltos - sobresaltos.mean()
    rng = np.random.default_rng(semilla)
    calentamiento = 100  # pasos descartados para que el arranque no influya
    sorteo = rng.choice(sobresaltos, size=(repeticiones, n + calentamiento))
    ruido = signal.lfilter([1.0], [1.0, -phi], sorteo, axis=1)[:, calentamiento:]
    pendientes = pendiente + ruido @ tc / sxx
    bajo, alto = np.quantile(pendientes, [ALFA / 2, 1 - ALFA / 2])
    return float(bajo), float(alto)


def triangulo_de_ventanas(anios: np.ndarray, valores: np.ndarray, largo_min: int) -> pd.DataFrame:
    """Tendencia para cada combinación posible de año inicial y año final.

    Sirve para descubrir si una tendencia depende de dónde se empieza o se termina de
    contar. Columnas: inicio, fin, pendiente (por año, mínimos cuadrados) y p (Mann-Kendall).
    """
    anios = np.asarray(anios, dtype=float)
    valores = np.asarray(valores, dtype=float)
    filas = []
    for i in range(anios.size):
        for j in range(i + largo_min - 1, anios.size):
            t, y = anios[i:j + 1], valores[i:j + 1]
            tc = t - t.mean()
            pendiente = float(np.dot(tc, y) / np.dot(tc, tc))
            filas.append((int(anios[i]), int(anios[j]), pendiente, mann_kendall(y).p))
    return pd.DataFrame(filas, columns=["inicio", "fin", "pendiente", "p"])


def anios_para_detectar(
    pendiente_anual: float, sigma_ruido: float, phi: float, por_anio: int = 12
) -> float:
    """Años de datos necesarios para detectar una tendencia (Weatherhead et al., 1998).

    Detectar = distinguirla del ruido con 95 % de confianza y 90 % de probabilidad.
    `sigma_ruido` y `phi` son la desviación estándar y la autocorrelación (lag 1) de la
    serie sin tendencia; `por_anio` es cuántos datos hay por año (12 mensual, 1 anual).
    La fórmula original es para datos mensuales; el factor raíz(12/por_anio) la
    generaliza a otras resoluciones.
    """
    if pendiente_anual == 0:
        return inf
    if sigma_ruido == 0:
        return 0.0
    phi = min(max(phi, 0.0), 0.99)
    ruido = sigma_ruido * sqrt(12 / por_anio) * sqrt((1 + phi) / (1 - phi))
    return (3.3 * ruido / abs(pendiente_anual)) ** (2 / 3)


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """Valores p ajustados para controlar la tasa de descubrimientos falsos.

    Si se interroga a 30 sospechosos, uno o dos parecerán culpables por pura casualidad;
    este ajuste lo compensa.
    """
    p = np.asarray(p, dtype=float)
    m = p.size
    orden = np.argsort(p)
    ajustados = p[orden] * m / np.arange(1, m + 1)
    ajustados = np.minimum.accumulate(ajustados[::-1])[::-1]
    resultado = np.empty(m)
    resultado[orden] = np.minimum(ajustados, 1.0)
    return resultado
