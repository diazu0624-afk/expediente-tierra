"""Las cinco pruebas de significancia a las que se somete una tendencia.

Cada prueba es una clase que hereda de `PruebaDeSignificancia` y responde a su manera la misma
petición, `evaluar(serie)`: una mira el orden de los datos, otra la pendiente de la recta, otra
su intervalo de confianza, otra si la tendencia sobrevive con menos datos y otra si depende
del periodo elegido. Quien las aplica (`caso.interrogar`) no distingue entre ellas: recorre la
batería y junta los resultados.

Los cálculos numéricos están en `estadistica.py`; aquí se decide qué se le pregunta a la serie,
cuándo se da por superada cada prueba y cómo se explica el resultado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import estadistica as est
from .formato import numero, valor_p
from .idioma import T
from .variables import Variable

# El signo de la tendencia debe mantenerse al menos en esta fracción de los periodos posibles.
MIN_FRACCION_VENTANAS = 0.8


@dataclass(frozen=True)
class SerieAnalizada:
    """La serie que se somete a las pruebas, con lo que ya se calculó de ella.

    La serie "interrogada" (`t`, `y`) son las anomalías mensuales o, si la variable se
    analiza a resolución anual, un valor por año. `anios` y `anual` son siempre un valor por año.
    """

    variable: Variable
    mensual: bool
    t: np.ndarray
    y: np.ndarray
    anios: np.ndarray
    anual: np.ndarray
    regresion: est.Regresion
    ic: tuple[float, float]  # intervalo de confianza del 95 % de la pendiente, por año
    mk: est.MannKendallSinMemoria
    sen: float  # pendiente de Theil-Sen, por año
    triangulo: pd.DataFrame  # tendencia de cada periodo posible
    largo_min: int  # años del periodo más corto del triángulo

    @property
    def signo(self) -> float:
        """El signo de la tendencia: +1 si aumenta, -1 si disminuye."""
        return float(np.sign(self.regresion.pendiente))

    @property
    def fraccion_de_periodos(self) -> float:
        """Fracción de los periodos posibles cuya tendencia tiene el mismo signo que la del periodo completo."""
        return float((np.sign(self.triangulo["pendiente"]) == self.signo).mean()) if self.signo else 0.0

    @property
    def dato(self) -> str:
        """Cómo se llama cada dato de la serie interrogada: "mes" o "año"."""
        return T("mes", "month") if self.mensual else T("año", "year")

    @property
    def datos(self) -> str:
        return T("meses", "months") if self.mensual else T("años", "years")

    def confirma(self, mk: est.MannKendallSinMemoria) -> bool:
        """¿Esa prueba de Mann-Kendall es significativa y va en el mismo sentido que la tendencia?"""
        return bool(mk.prueba.p < est.ALFA and np.sign(mk.prueba.s) == self.signo)


@dataclass(frozen=True)
class ResultadoDePrueba:
    """Lo que dijo una prueba sobre una serie."""

    nombre: str
    pregunta: str
    aprobada: bool
    resultado: str
    explicacion: str


class PruebaDeSignificancia(ABC):
    """Una prueba de significancia: una pregunta que se le hace a la serie y un criterio para superarla.

    Las subclases definen `nombre`, `pregunta` y `evaluar`. El nombre y la pregunta son
    propiedades, no constantes, porque se entregan en el idioma de la sesión.
    """

    @property
    @abstractmethod
    def nombre(self) -> str:
        """El nombre de la prueba, como aparece en la interfaz y en el informe."""

    @property
    @abstractmethod
    def pregunta(self) -> str:
        """La pregunta que la prueba responde, en lenguaje llano."""

    @abstractmethod
    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        """Aplica la prueba a la serie y explica el resultado."""

    def _resultado(self, aprobada: bool, resultado: str, explicacion: str) -> ResultadoDePrueba:
        return ResultadoDePrueba(self.nombre, self.pregunta, bool(aprobada), resultado, explicacion)


class MannKendallConPreblanqueo(PruebaDeSignificancia):
    """¿Los valores suben (o bajan) más seguido de lo que explicaría el azar?"""

    @property
    def nombre(self) -> str:
        return T("Prueba de Mann-Kendall", "Mann-Kendall test")

    @property
    def pregunta(self) -> str:
        return T("¿Los valores aumentan (o disminuyen) con más frecuencia de la que explicaría el azar?",
                 "Do the values increase (or decrease) more often than chance would explain?")

    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        u, dato = serie.variable.unidad, serie.dato
        return self._resultado(
            serie.confirma(serie.mk),
            T(f"{valor_p(serie.mk.prueba.p)} · pendiente de Theil-Sen: "
              f"{numero(serie.sen * 10, signo=True)} {u} por década",
              f"{valor_p(serie.mk.prueba.p)} · Theil-Sen slope: {numero(serie.sen * 10, signo=True)} {u} per decade"),
            T(f"Compara cada {dato} con todos los posteriores y cuenta cuántas veces el valor "
              f"aumentó y cuántas disminuyó. Antes se corrige la autocorrelación de la serie "
              f"(cada {dato} se parece al anterior) mediante preblanqueo, porque sin esa "
              f"corrección la prueba detecta tendencias que no existen. La pendiente de "
              f"Theil-Sen es la mediana de las pendientes entre todos los pares de datos y es "
              f"robusta frente a valores atípicos.",
              f"It compares each {dato} with all later ones and counts how many times the value went up "
              f"and how many it went down. The autocorrelation of the series (each {dato} resembles the "
              f"previous one) is corrected first by prewhitening, because without that correction the "
              f"test detects trends that do not exist. The Theil-Sen slope is the median of the slopes "
              f"between all pairs of data points and is robust to outliers."))


class PruebaTDeLaPendiente(PruebaDeSignificancia):
    """¿La pendiente de la recta es distinta de cero, contando solo los datos independientes?"""

    @property
    def nombre(self) -> str:
        return T("Prueba t de la pendiente", "t-test of the slope")

    @property
    def pregunta(self) -> str:
        return T("¿La pendiente de la regresión lineal es distinta de cero?",
                 "Is the slope of the linear regression different from zero?")

    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        recta, datos = serie.regresion, serie.datos
        return self._resultado(
            recta.p < est.ALFA and np.sign(recta.pendiente) == serie.signo,
            T(f"{valor_p(recta.p)} · tamaño de muestra efectivo: {recta.n_efectivo:.0f} "
              f"de {recta.n} {datos}",
              f"{valor_p(recta.p)} · effective sample size: {recta.n_efectivo:.0f} of {recta.n} {datos}"),
            T(f"Ajusta una recta por mínimos cuadrados y evalúa si su pendiente podría ser cero. "
              f"Como los {datos} consecutivos están correlacionados, no cuentan como datos "
              f"independientes: la prueba usa el tamaño de muestra efectivo.",
              f"It fits a least-squares line and tests whether its slope could be zero. Because "
              f"consecutive {datos} are correlated, they do not count as independent data: the test "
              f"uses the effective sample size."))


class IntervaloDeConfianza(PruebaDeSignificancia):
    """¿El intervalo de confianza de la pendiente deja fuera el cero?"""

    @property
    def nombre(self) -> str:
        return T("Intervalo de confianza del 95 %", "95 % confidence interval")

    @property
    def pregunta(self) -> str:
        return T("¿El intervalo de confianza de la pendiente excluye el cero?",
                 "Does the confidence interval of the slope exclude zero?")

    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        (bajo, alto), u = serie.ic, serie.variable.unidad
        return self._resultado(
            (bajo > 0 or alto < 0) and np.sign(bajo) == serie.signo,
            T(f"de {numero(bajo * 10, signo=True)} a "
              f"{numero(alto * 10, signo=True)} {u} por década",
              f"{numero(bajo * 10, signo=True)} to {numero(alto * 10, signo=True)} {u} per decade"),
            T("Se generan 2,000 series simuladas (bootstrap) con la misma variabilidad y la "
              "misma autocorrelación que la serie real. Si el 95 % de sus pendientes queda del "
              "mismo lado del cero, el signo de la tendencia es confiable.",
              "2,000 simulated series (bootstrap) are generated with the same variability and the same "
              "autocorrelation as the real series. If 95 % of their slopes fall on the same side of zero, "
              "the sign of the trend is reliable."))


class AgregacionAnual(PruebaDeSignificancia):
    """¿La tendencia de los datos mensuales se mantiene con un solo dato por año?"""

    @property
    def nombre(self) -> str:
        return T("Agregación anual", "Annual aggregation")

    @property
    def pregunta(self) -> str:
        return T("¿La tendencia se mantiene con un solo dato por año?", "Does the trend hold with a single value per year?")

    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        mk_anual = est.mann_kendall_sin_memoria(serie.anios, serie.anual)
        anios = len(serie.anual)
        return self._resultado(
            serie.confirma(mk_anual),
            T(f"{valor_p(mk_anual.prueba.p)} con {anios} años", f"{valor_p(mk_anual.prueba.p)} with {anios} years"),
            T("Se repite la prueba de Mann-Kendall sobre los promedios anuales: son menos datos, "
              "pero sin ciclo estacional y casi sin autocorrelación. Una tendencia real debe "
              "mantenerse.",
              "The Mann-Kendall test is repeated on the annual means: fewer data points, but with no "
              "seasonal cycle and almost no autocorrelation. A real trend should hold."))


class SensibilidadAUnAnio(PruebaDeSignificancia):
    """¿La tendencia sigue siendo significativa al quitar cualquier año? (para series de un dato por año)"""

    @property
    def nombre(self) -> str:
        return T("Sensibilidad a un año", "Sensitivity to a single year")

    @property
    def pregunta(self) -> str:
        return T("¿La tendencia se mantiene si se excluye cualquier año?", "Does the trend hold when any one year is left out?")

    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        fallos, anios = self._fallos(serie), len(serie.anual)
        if fallos == 0:
            resultado = T("se mantiene al excluir cualquier año", "it holds when any year is left out")
        elif fallos == anios:
            resultado = T("no es significativa, se excluya el año que se excluya",
                          "it is not significant, whichever year is left out")
        else:
            resultado = T(f"deja de ser significativa al excluir {fallos} de {anios} años",
                          f"it stops being significant when leaving out {fallos} of {anios} years")
        return self._resultado(
            fallos == 0, resultado,
            T("Se repite la prueba de Mann-Kendall excluyendo un año a la vez (validación "
              "dejando uno fuera). Si la tendencia desaparece al excluir un solo año, dependía "
              "de un valor atípico y no de un cambio sostenido.",
              "The Mann-Kendall test is repeated leaving out one year at a time (leave-one-out "
              "validation). If the trend disappears when a single year is removed, it depended on an "
              "outlier and not on a sustained change."))

    @staticmethod
    def _fallos(serie: SerieAnalizada) -> int:
        """En cuántos años, al quitarlos, la tendencia deja de ser significativa."""
        fallos = 0
        for k in range(serie.anios.size):
            mk = est.mann_kendall_sin_memoria(np.delete(serie.anios, k), np.delete(serie.anual, k))
            if not serie.confirma(mk):
                fallos += 1
        return fallos


class SensibilidadAlPeriodo(PruebaDeSignificancia):
    """¿El signo de la tendencia depende de los años inicial y final que se elijan?"""

    @property
    def nombre(self) -> str:
        return T("Sensibilidad al periodo", "Sensitivity to the period")

    @property
    def pregunta(self) -> str:
        return T("¿El signo de la tendencia se mantiene al cambiar el año inicial o final?",
                 "Does the sign of the trend hold when the start or end year changes?")

    def evaluar(self, serie: SerieAnalizada) -> ResultadoDePrueba:
        fraccion, periodos = serie.fraccion_de_periodos, len(serie.triangulo)
        return self._resultado(
            fraccion >= MIN_FRACCION_VENTANAS,
            T(f"{100 * fraccion:.0f} % de {periodos} periodos conservan el signo",
              f"{100 * fraccion:.0f} % of {periodos} periods keep the sign"),
            T(f"Se recalcula la tendencia para todos los periodos posibles de al menos "
              f"{serie.largo_min} años. Si el signo depende de las fechas elegidas, el resultado es "
              f"sensible a la selección del periodo. Se exige que al menos "
              f"{100 * MIN_FRACCION_VENTANAS:.0f} % de los periodos coincida.",
              f"The trend is recomputed for every possible period of at least {serie.largo_min} years. If the "
              f"sign depends on the chosen dates, the result is sensitive to the choice of period. At least "
              f"{100 * MIN_FRACCION_VENTANAS:.0f} % of the periods must agree."))


def bateria(serie: SerieAnalizada) -> tuple[PruebaDeSignificancia, ...]:
    """Las cinco pruebas que le tocan a una serie, en el orden en que se presentan.

    La cuarta cambia con la resolución: a una serie mensual se le pide que la tendencia
    sobreviva con un dato por año; a una que ya es anual, que sobreviva sin cualquiera de sus años.
    """
    cuarta = AgregacionAnual() if serie.mensual else SensibilidadAUnAnio()
    return (MannKendallConPreblanqueo(), PruebaTDeLaPendiente(), IntervaloDeConfianza(), cuarta, SensibilidadAlPeriodo())


N_PRUEBAS = 5
