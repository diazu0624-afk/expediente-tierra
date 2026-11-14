"""Del dato crudo al resultado.

`escanear` ordena las variables de un sitio por la magnitud de su tendencia e
`interrogar` aplica las cinco pruebas de significancia a una variable y asigna el nivel
de evidencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite, log10

import numpy as np
import pandas as pd

from . import estadistica as est
from .variables import CATALOGO, Variable

MIN_ANIOS = 15
MIN_MESES = 9  # meses con dato para que un año cuente
MIN_FRACCION_VENTANAS = 0.8
# Si un mismo valor (casi siempre el cero: "no nevó", "no heló") ocupa más de esta parte
# de la serie, las pruebas dejan de ser confiables a esa resolución.
MAX_REPETIDOS = 0.2
N_PRUEBAS = 5

NIVELES = {
    "solida": "Evidencia sólida",
    "fuerte": "Evidencia fuerte",
    "indicios": "Evidencia débil",
    "sin": "Sin evidencia suficiente",
}
NIVELES_CORTOS = {"solida": "Sólida", "fuerte": "Fuerte", "indicios": "Débil", "sin": "Insuficiente"}


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
    """Promedio de cada año que tenga al menos MIN_MESES meses con dato.

    Para que un mes faltante no sesgue el promedio (no es lo mismo perder un enero que un
    julio), se promedian las anomalías y se suma el promedio normal del año. Con los 12
    meses presentes da exactamente el promedio simple.
    """
    serie = serie.dropna()
    if serie.empty:
        return pd.Series(dtype=float)
    anomalias, climatologia = est.quitar_ciclo_estacional(serie)
    por_anio = anomalias.groupby(anomalias.index.year)
    return (por_anio.mean() + climatologia.mean())[por_anio.count() >= MIN_MESES]


def _parte_repetida(serie: pd.Series) -> float:
    """Fracción de la serie que ocupa su valor más frecuente."""
    return float(serie.value_counts().iloc[0] / len(serie)) if len(serie) else 1.0


def _motivo_imposible(anual: pd.Series) -> str:
    if len(anual) < MIN_ANIOS:
        return f"Hay menos de {MIN_ANIOS} años de datos aquí"
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
    cambio: est.PuntoDeCambio | None  # regresión en dos tramos sobre los promedios anuales

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

    @property
    def cambio_en_variabilidad(self) -> float | None:
        """Cambio total medido en desviaciones estándar interanuales (su tamaño práctico).

        La desviación estándar interanual es lo que el promedio anual suele apartarse de su
        propia tendencia de un año a otro.
        """
        anios = self.anual.index.to_numpy(dtype=float)
        valores = self.anual.to_numpy()
        residuos = valores - np.polyval(np.polyfit(anios, valores, 1), anios)
        sigma = float(residuos.std(ddof=1))
        return self.cambio_total / sigma if sigma > 0 else None


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
            "Agregación anual",
            "¿La tendencia se mantiene con un solo dato por año?",
            _mk_confirma(mk_anual, signo),
            f"{valor_p(mk_anual.prueba.p)} con {len(anual)} años",
            "Se repite la prueba de Mann-Kendall sobre los promedios anuales: son menos datos, "
            "pero sin ciclo estacional y casi sin autocorrelación. Una tendencia real debe "
            "mantenerse.",
        )
    else:
        sobrevive, fallos = _sobrevive_sin_un_anio(anios, anual.to_numpy(), signo)
        cuarta = Prueba(
            "Sensibilidad a un año",
            "¿La tendencia se mantiene si se excluye cualquier año?",
            sobrevive,
            "se mantiene al excluir cualquier año" if sobrevive
            else f"deja de ser significativa al excluir {fallos} de {len(anual)} años",
            "Se repite la prueba de Mann-Kendall excluyendo un año a la vez (validación "
            "dejando uno fuera). Si la tendencia desaparece al excluir un solo año, dependía "
            "de un valor atípico y no de un cambio sostenido.",
        )

    u = variable.unidad
    pruebas = (
        Prueba(
            "Prueba de Mann-Kendall",
            "¿Los valores aumentan (o disminuyen) con más frecuencia de la que explicaría el azar?",
            _mk_confirma(mk, signo),
            f"{valor_p(mk.prueba.p)} · pendiente de Theil-Sen: "
            f"{numero(sen * 10, signo=True)} {u} por década",
            f"Compara cada {dato} con todos los posteriores y cuenta cuántas veces el valor "
            f"aumentó y cuántas disminuyó. Antes se corrige la autocorrelación de la serie "
            f"(cada {dato} se parece al anterior) mediante preblanqueo, porque sin esa "
            f"corrección la prueba detecta tendencias que no existen. La pendiente de "
            f"Theil-Sen es la mediana de las pendientes entre todos los pares de datos y es "
            f"robusta frente a valores atípicos.",
        ),
        Prueba(
            "Prueba t de la pendiente",
            "¿La pendiente de la regresión lineal es distinta de cero?",
            regresion.p < est.ALFA and np.sign(regresion.pendiente) == signo,
            f"{valor_p(regresion.p)} · tamaño de muestra efectivo: {regresion.n_efectivo:.0f} "
            f"de {regresion.n} {datos_txt}",
            f"Ajusta una recta por mínimos cuadrados y evalúa si su pendiente podría ser cero. "
            f"Como los {datos_txt} consecutivos están correlacionados, no cuentan como datos "
            f"independientes: la prueba usa el tamaño de muestra efectivo.",
        ),
        Prueba(
            "Intervalo de confianza del 95 %",
            "¿El intervalo de confianza de la pendiente excluye el cero?",
            (ic_historias[0] > 0 or ic_historias[1] < 0) and np.sign(ic_historias[0]) == signo,
            f"de {numero(ic_historias[0] * 10, signo=True)} a "
            f"{numero(ic_historias[1] * 10, signo=True)} {u} por década",
            "Se generan 2,000 series simuladas (bootstrap) con la misma variabilidad y la "
            "misma autocorrelación que la serie real. Si el 95 % de sus pendientes queda del "
            "mismo lado del cero, el signo de la tendencia es confiable.",
        ),
        cuarta,
        Prueba(
            "Sensibilidad al periodo",
            "¿El signo de la tendencia se mantiene al cambiar el año inicial o final?",
            fraccion >= MIN_FRACCION_VENTANAS,
            f"{100 * fraccion:.0f} % de {len(triangulo)} periodos conservan el signo",
            f"Se recalcula la tendencia para todos los periodos posibles de al menos "
            f"{largo_min} años. Si el signo depende de las fechas elegidas, el resultado es "
            f"sensible a la selección del periodo. Se exige que al menos "
            f"{100 * MIN_FRACCION_VENTANAS:.0f} % de los periodos coincida.",
        ),
    )

    ruido = y - (regresion.intercepto + regresion.pendiente * t)
    necesarios = est.anios_para_detectar(regresion.pendiente, float(ruido.std(ddof=1)),
                                         regresion.r1, por_anio=12 if mensual else 1)

    return Interrogatorio(variable, "mensual" if mensual else "anual", serie, anomalias, anual,
                          t, y, regresion, ic_historias, mk, est.mann_kendall(y), sen,
                          triangulo, fraccion, pruebas, necesarios,
                          est.punto_de_cambio(anios, anual.to_numpy()))


def escanear(datos: pd.DataFrame, variables: tuple[Variable, ...] = CATALOGO) -> pd.DataFrame:
    """Exploración de variables: tendencia de cada una, en una escala comparable.

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
