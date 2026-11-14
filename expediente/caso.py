"""El caso: de los datos crudos al veredicto.

`escanear` arma la rueda de sospechosos (qué variables cambian más en un lugar) e
`interrogar` somete una variable a las cinco pruebas y dicta el nivel de evidencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite, log10

import numpy as np
import pandas as pd

from . import estadistica as est
from .variables import CATALOGO, Variable

MIN_ANIOS = 15
MIN_FRACCION_VENTANAS = 0.8
# Si un mismo valor (casi siempre el cero: "no nevó", "no heló") ocupa más de esta parte
# de la serie, las pruebas dejan de ser confiables a esa resolución.
MAX_REPETIDOS = 0.2
N_PRUEBAS = 5

NIVELES = {
    "solida": "Evidencia sólida",
    "fuerte": "Evidencia fuerte",
    "indicios": "Solo indicios",
    "sin": "Sin evidencia suficiente",
}
NIVELES_CORTOS = {"solida": "Sólida", "fuerte": "Fuerte", "indicios": "Indicios", "sin": "Insuficiente"}


class CasoImposible(ValueError):
    """La variable no se puede analizar en este lugar (faltan datos o casi nunca ocurre)."""


def numero(x: float, signo: bool = False, cifras: int = 2) -> str:
    """Número con `cifras` cifras significativas, sin notación científica."""
    if not isfinite(x):
        return "—"
    if x == 0:
        return "0"
    decimales = min(max(cifras - 1 - floor(log10(abs(x))), 0), 8)
    return f"{x:+,.{decimales}f}" if signo else f"{x:,.{decimales}f}"


def valor_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def promedios_anuales(serie: pd.Series) -> pd.Series:
    """Promedio de cada año que tenga sus 12 meses."""
    por_anio = serie.groupby(serie.index.year)
    return por_anio.mean()[por_anio.count() == 12]


def _parte_repetida(serie: pd.Series) -> float:
    """Fracción de la serie que ocupa su valor más frecuente."""
    return float(serie.value_counts().iloc[0] / len(serie)) if len(serie) else 1.0


def _motivo_imposible(anual: pd.Series) -> str:
    if len(anual) < MIN_ANIOS:
        return f"Hay menos de {MIN_ANIOS} años completos de datos aquí"
    if _parte_repetida(anual) > MAX_REPETIDOS:
        return "Casi nunca ocurre o casi nunca cambia en este lugar"
    return ""


@dataclass(frozen=True)
class Prueba:
    nombre: str
    pregunta: str
    aprobada: bool
    resultado: str
    explicacion: str


@dataclass(frozen=True)
class Interrogatorio:
    variable: Variable
    resolucion: str  # "mensual" (anomalías sin ciclo estacional) o "anual" (promedios)
    serie: pd.Series  # mensual, tal como llega
    anomalias: pd.Series  # mensual, sin ciclo estacional
    anual: pd.Series  # promedio por año completo
    t: np.ndarray  # tiempo en años de la serie interrogada
    y: np.ndarray  # serie interrogada: anomalías mensuales o promedios anuales
    regresion: est.Regresion  # la recta: su pendiente (por año) es el "cuánto cambia"
    ic_historias: tuple[float, float]  # rango creíble de esa pendiente
    mk: est.MannKendallSinMemoria
    mk_ingenuo: est.MannKendall
    pendiente_sen: float
    triangulo: pd.DataFrame
    fraccion_ventanas: float
    pruebas: tuple[Prueba, ...]
    anios_necesarios: float

    @property
    def aprobadas(self) -> int:
        return sum(p.aprobada for p in self.pruebas)

    @property
    def nivel(self) -> str:
        if self.aprobadas == N_PRUEBAS:
            return "solida"
        if self.aprobadas == N_PRUEBAS - 1:
            return "fuerte"
        return "indicios" if self.aprobadas >= 2 else "sin"

    @property
    def sube(self) -> bool:
        return self.regresion.pendiente > 0

    @property
    def anios_de_datos(self) -> float:
        return len(self.y) / (12 if self.resolucion == "mensual" else 1)

    @property
    def pendiente_decada(self) -> float:
        return self.regresion.pendiente * 10

    @property
    def ic_decada(self) -> tuple[float, float]:
        return self.ic_historias[0] * 10, self.ic_historias[1] * 10

    @property
    def cambio_total(self) -> float:
        return self.regresion.pendiente * self.anios_de_datos

    @property
    def cambio_relativo(self) -> float | None:
        """Cambio total como porcentaje del promedio, solo donde un porcentaje tiene sentido."""
        promedio = float(self.serie.mean())
        if not self.variable.relativo or promedio <= 0:
            return None
        return 100 * self.cambio_total / promedio


def _mk_confirma(mk: est.MannKendallSinMemoria, signo: float) -> bool:
    return mk.prueba.p < est.ALFA and np.sign(mk.prueba.s) == signo


def _sobrevive_sin_un_anio(anios: np.ndarray, valores: np.ndarray, signo: float) -> tuple[bool, int]:
    """¿La tendencia sigue siendo significativa al quitar cualquier año? Devuelve (sí/no, fallos)."""
    fallos = 0
    for k in range(anios.size):
        mk = est.mann_kendall_sin_memoria(np.delete(anios, k), np.delete(valores, k))
        if not _mk_confirma(mk, signo):
            fallos += 1
    return fallos == 0, fallos


def interrogar(serie_mensual: pd.Series, variable: Variable) -> Interrogatorio:
    """Somete una variable a las cinco pruebas."""
    serie = serie_mensual.loc[str(variable.desde):].dropna()
    anual = promedios_anuales(serie)
    motivo = _motivo_imposible(anual)
    if motivo:
        raise CasoImposible(motivo + ".")

    anomalias, _ = est.quitar_ciclo_estacional(serie)
    anios = anual.index.to_numpy(dtype=float)
    # Fenómenos que solo ocurren parte del año (nieve, heladas) llenan la serie mensual de
    # ceros repetidos; para esos se interroga el promedio anual.
    mensual = _parte_repetida(serie) <= MAX_REPETIDOS
    if mensual:
        t = np.asarray(anomalias.index.year + (anomalias.index.month - 0.5) / 12, dtype=float)
        y = anomalias.to_numpy()
        dato, datos_txt = "mes", "meses"
    else:
        t, y = anios, anual.to_numpy()
        dato, datos_txt = "año", "años"

    regresion = est.regresion_lineal(t, y)
    ic_historias = est.ic_historias_alternativas(t, y)
    mk = est.mann_kendall_sin_memoria(t, y)
    sen = est.pendiente_sen(t, y).pendiente
    signo = np.sign(regresion.pendiente)

    largo_min = max(10, len(anual) // 3)
    triangulo = est.triangulo_de_ventanas(anios, anual.to_numpy(), largo_min)
    fraccion = float((np.sign(triangulo["pendiente"]) == signo).mean()) if signo else 0.0

    if mensual:
        mk_anual = est.mann_kendall_sin_memoria(anios, anual.to_numpy())
        cuarta = Prueba(
            "Promedios anuales",
            "¿La tendencia sigue ahí con un solo dato por año?",
            _mk_confirma(mk_anual, signo),
            f"{valor_p(mk_anual.prueba.p)} con {len(anual)} años",
            "Se repite Mann-Kendall con el promedio de cada año: son menos datos, pero sin "
            "estaciones y casi sin memoria. Una tendencia real debería sobrevivir.",
        )
    else:
        sobrevive, fallos = _sobrevive_sin_un_anio(anios, anual.to_numpy(), signo)
        cuarta = Prueba(
            "Sin un año clave",
            "¿La tendencia sigue ahí si se borra cualquier año?",
            sobrevive,
            "sobrevive al quitar cualquier año" if sobrevive
            else f"deja de ser significativa al quitar {fallos} de {len(anual)} años",
            "Se repite Mann-Kendall quitando un año a la vez. Si la tendencia desaparece "
            "al borrar un solo año, dependía de un año raro y no de un cambio sostenido.",
        )

    u = variable.unidad
    pruebas = (
        Prueba(
            "Mann-Kendall",
            "¿Los valores suben (o bajan) más seguido de lo que explicaría el azar?",
            _mk_confirma(mk, signo),
            f"{valor_p(mk.prueba.p)} · pendiente robusta (Sen): "
            f"{numero(sen * 10, signo=True)} {u} por década",
            f"Compara cada {dato} con todos los posteriores y cuenta cuántas veces el valor "
            f"subió y cuántas bajó. Antes se le quita la «memoria» a la serie (cada {dato} "
            f"se parece al anterior), porque esa memoria hace que la prueba vea tendencias "
            f"donde no las hay. La pendiente de Sen es la mediana de las pendientes entre "
            f"todos los pares de datos: casi no le afectan los valores extremos.",
        ),
        Prueba(
            "Prueba t de la pendiente",
            "¿La inclinación de la recta es distinta de cero?",
            regresion.p < est.ALFA and np.sign(regresion.pendiente) == signo,
            f"{valor_p(regresion.p)} · {regresion.n} {datos_txt} valen como "
            f"{regresion.n_efectivo:.0f} datos independientes",
            f"Ajusta una recta a los datos y pregunta si su inclinación podría ser cero. "
            f"Como los {datos_txt} vecinos se parecen entre sí, no cuentan como datos "
            f"independientes y la prueba los descuenta.",
        ),
        Prueba(
            "Intervalo de confianza",
            "¿El rango de pendientes creíbles deja fuera al cero?",
            (ic_historias[0] > 0 or ic_historias[1] < 0) and np.sign(ic_historias[0]) == signo,
            f"de {numero(ic_historias[0] * 10, signo=True)} a "
            f"{numero(ic_historias[1] * 10, signo=True)} {u} por década",
            "Se simulan 2,000 historias alternativas con el mismo ruido y la misma memoria "
            "que la serie real. Si el 95 % de sus pendientes cae del mismo lado del cero, "
            "la dirección del cambio es confiable.",
        ),
        cuarta,
        Prueba(
            "Cambio de fechas",
            "¿La dirección se mantiene si se cambia el año de inicio o de fin?",
            fraccion >= MIN_FRACCION_VENTANAS,
            f"{100 * fraccion:.0f} % de {len(triangulo)} periodos van en la misma dirección",
            f"Se recalcula la tendencia para todos los periodos posibles de al menos "
            f"{largo_min} años. Si la dirección depende de las fechas elegidas, alguien "
            f"podría «demostrar» lo que quisiera escogiendo dónde empezar a contar. "
            f"Se pide que al menos {100 * MIN_FRACCION_VENTANAS:.0f} % coincida.",
        ),
    )

    ruido = y - (regresion.intercepto + regresion.pendiente * t)
    necesarios = est.anios_para_detectar(regresion.pendiente, float(ruido.std(ddof=1)),
                                         regresion.r1, por_anio=12 if mensual else 1)

    return Interrogatorio(variable, "mensual" if mensual else "anual", serie, anomalias, anual,
                          t, y, regresion, ic_historias, mk, est.mann_kendall(y), sen,
                          triangulo, fraccion, pruebas, necesarios)


def escanear(datos: pd.DataFrame, variables: tuple[Variable, ...] = CATALOGO) -> pd.DataFrame:
    """Rueda de sospechosos: tendencia de cada variable, comparable entre variables.

    Usa promedios anuales. `estandarizada` es la pendiente por década dividida entre la
    variación típica de un año a otro, así que un cambio de temperatura y uno de lluvia
    se pueden poner en la misma escala. Los valores p (Mann-Kendall sin memoria) se
    ajustan con Benjamini-Hochberg porque se examinan muchas variables a la vez.
    """
    filas = []
    for v in variables:
        fila = {"codigo": v.codigo, "nombre": v.nombre, "categoria": v.categoria,
                "unidad": v.unidad, "anios": 0, "pendiente_decada": np.nan,
                "estandarizada": np.nan, "p": np.nan, "nota": ""}
        if v.codigo in datos:
            anual = promedios_anuales(datos[v.codigo].loc[str(v.desde):].dropna())
        else:
            anual = pd.Series(dtype=float)
        fila["anios"] = len(anual)
        fila["nota"] = _motivo_imposible(anual)
        if not fila["nota"]:
            anios, valores = anual.index.to_numpy(dtype=float), anual.to_numpy()
            recta = est.regresion_lineal(anios, valores)
            ruido = valores - (recta.intercepto + recta.pendiente * anios)
            fila["pendiente_decada"] = recta.pendiente * 10
            fila["estandarizada"] = recta.pendiente * 10 / ruido.std(ddof=1)
            fila["p"] = est.mann_kendall_sin_memoria(anios, valores).prueba.p
        filas.append(fila)

    tabla = pd.DataFrame(filas)
    validas = tabla["p"].notna()
    tabla["p_ajustada"] = np.nan
    tabla.loc[validas, "p_ajustada"] = est.benjamini_hochberg(tabla.loc[validas, "p"].to_numpy())
    tabla["significativa"] = tabla["p_ajustada"] < est.ALFA
    orden = tabla["estandarizada"].abs().sort_values(ascending=False, na_position="last").index
    return tabla.loc[orden].reset_index(drop=True)
