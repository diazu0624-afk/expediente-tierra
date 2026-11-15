"""Del dato crudo al resultado.

`escanear` ordena las variables de un sitio por la magnitud de su tendencia e
`interrogar` aplica las cinco pruebas de significancia a una variable y asigna el nivel
de evidencia.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import estadistica as est
from .formato import numero, valor_p  # noqa: F401  (otros módulos los toman de aquí)
from .idioma import Dicc, T, Tupla
from .pruebas import MIN_FRACCION_VENTANAS, N_PRUEBAS, ResultadoDePrueba, SerieAnalizada, bateria  # noqa: F401
from .variables import CATALOGO, Variable

MIN_ANIOS = 15
MIN_MESES = 9  # meses con dato para que un año cuente
# Si un mismo valor (casi siempre el cero: "no nevó", "no heló") ocupa más de esta parte
# de la serie, las pruebas dejan de ser confiables a esa resolución.
MAX_REPETIDOS = 0.2

NIVELES = Dicc({
    "solida": ("Evidencia sólida", "Solid evidence"),
    "fuerte": ("Evidencia fuerte", "Strong evidence"),
    "indicios": ("Evidencia débil", "Weak evidence"),
    "sin": ("Sin evidencia suficiente", "Insufficient evidence"),
})
NIVELES_CORTOS = Dicc({"solida": ("Sólida", "Solid"), "fuerte": ("Fuerte", "Strong"), "indicios": ("Débil", "Weak"),
                       "sin": ("Insuficiente", "Insufficient")})

MESES = Tupla(("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
               "octubre", "noviembre", "diciembre"),
              ("January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"))
TODO_EL_ANIO = tuple(range(1, 13))
# Estaciones meteorológicas, nombradas por sus meses para que sirvan en los dos hemisferios.
TEMPORADAS: dict[str, tuple[int, ...]] = {
    "DEF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11),
}


class CasoImposible(ValueError):
    """La variable no se puede analizar en este lugar (faltan datos o casi nunca ocurre)."""


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


def ordenar_meses(meses) -> tuple[int, ...]:
    """Los meses elegidos en orden cronológico; una temporada que cruza el fin de año empieza
    después de su hueco más largo (diciembre, enero y febrero -> 12, 1, 2)."""
    unicos = sorted({int(m) for m in meses if 1 <= int(m) <= 12})
    if not unicos or len(unicos) == 12:
        return TODO_EL_ANIO
    huecos = [(unicos[(k + 1) % len(unicos)] - m - 1) % 12 for k, m in enumerate(unicos)]
    inicio = (int(np.argmax(huecos)) + 1) % len(unicos)
    return tuple(unicos[inicio:] + unicos[:inicio])


def nombre_de_meses(meses: tuple[int, ...]) -> str:
    """Cómo se nombra una selección de meses: "todo el año", "julio", "junio a agosto"."""
    if len(meses) == 12:
        return T("todo el año", "the whole year")
    nombres = [MESES[m - 1] for m in meses]
    if len(meses) == 1:
        return nombres[0]
    seguidos = all((b - a) % 12 == 1 for a, b in zip(meses, meses[1:]))
    y = T(" y ", " and ")
    if seguidos:
        return f"{nombres[0]}{T(' a ', ' to ')}{nombres[-1]}" if len(meses) > 2 else f"{nombres[0]}{y}{nombres[1]}"
    return ", ".join(nombres[:-1]) + y + nombres[-1]


def serie_de_temporada(serie: pd.Series, meses: tuple[int, ...]) -> pd.Series:
    """Un valor por año: el promedio de los meses elegidos. El año solo cuenta si los tiene todos.

    Una temporada que cruza el fin de año (diciembre a febrero) se asigna al año en que
    termina: diciembre de 2019 cuenta para la temporada de 2020.
    """
    serie = serie.dropna()
    serie = serie[serie.index.month.isin(meses)]
    if serie.empty:
        return pd.Series(dtype=float)
    cruza = [m for k, m in enumerate(meses) if any(posterior < m for posterior in meses[k + 1:])]
    anio = serie.index.year + np.isin(serie.index.month, cruza).astype(int)
    por_anio = serie.groupby(anio)
    return por_anio.mean()[por_anio.count() == len(meses)]


def serie_anual(serie: pd.Series, meses: tuple[int, ...] = TODO_EL_ANIO, ya_es_anual: bool = False) -> pd.Series:
    """Un valor por año, de todo el año o solo de los meses elegidos.

    `ya_es_anual` es para los índices de extremos, que traen un solo valor por año.
    """
    if ya_es_anual:
        serie = serie.dropna()
        return serie.groupby(serie.index.year).mean()
    return promedios_anuales(serie) if len(meses) == 12 else serie_de_temporada(serie, meses)


def _solo_anual() -> str:
    return T("Es un índice anual: no se calcula por temporada", "It is an annual index: it is not computed by season")


def _parte_repetida(serie: pd.Series) -> float:
    """Fracción de la serie que ocupa su valor más frecuente."""
    return float(serie.value_counts().iloc[0] / len(serie)) if len(serie) else 1.0


def _motivo_imposible(anual: pd.Series) -> str:
    if len(anual) < MIN_ANIOS:
        return T(f"Hay menos de {MIN_ANIOS} años de datos aquí", f"There are fewer than {MIN_ANIOS} years of data here")
    if _parte_repetida(anual) > MAX_REPETIDOS:
        return T("Casi nunca ocurre o casi nunca cambia en este lugar",
                 "It almost never occurs or almost never changes at this location")
    return ""


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
    pruebas: tuple[ResultadoDePrueba, ...]
    anios_necesarios: float
    cambio: est.PuntoDeCambio | None  # regresión en dos tramos sobre los promedios anuales
    meses: tuple[int, ...] = TODO_EL_ANIO  # meses del año que entran al análisis

    @property
    def por_temporada(self) -> bool:
        return len(self.meses) < 12

    @property
    def temporada(self) -> str:
        return nombre_de_meses(self.meses)

    @property
    def n(self) -> int:
        """Tamaño de muestra: datos que entran a las pruebas."""
        return len(self.y)

    @property
    def muestra(self) -> str:
        """El tamaño de muestra en palabras, para mostrarlo junto a cada resultado."""
        inicio, fin = self.anual.index.min(), self.anual.index.max()
        periodo = T(f"de {inicio} a {fin}", f"{inicio} to {fin}")
        if self.resolucion == "mensual":
            return T(f"n = {self.n} meses ({len(self.anual)} años completos), {periodo}",
                     f"n = {self.n} months ({len(self.anual)} complete years), {periodo}")
        return T(f"n = {self.n} años, {periodo}", f"n = {self.n} years, {periodo}")

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


def interrogar(serie_mensual: pd.Series, variable: Variable,
               meses: tuple[int, ...] = TODO_EL_ANIO) -> Interrogatorio:
    """Somete una variable a las cinco pruebas.

    Con `meses` se analiza solo una parte del año (una estación o un mes): la serie se
    reduce a un valor por año y se interroga a esa resolución.
    """
    serie = serie_mensual.loc[str(variable.desde):].dropna()
    por_temporada = len(meses) < 12
    if por_temporada and variable.anual:
        raise CasoImposible(_solo_anual() + T(". Elige «Todo el año» en la barra lateral.",
                                              ". Choose “The whole year” in the sidebar."))
    if por_temporada:
        serie = serie[serie.index.month.isin(meses)]
    anual = serie_anual(serie, meses, variable.anual)
    motivo = _motivo_imposible(anual)
    if motivo:
        raise CasoImposible(motivo + ".")

    anomalias, _ = est.quitar_ciclo_estacional(serie)
    anios = anual.index.to_numpy(dtype=float)
    # Fenómenos que solo ocurren parte del año (nieve, heladas) llenan la serie mensual de
    # ceros repetidos; para esos se interroga el promedio anual.
    mensual = not por_temporada and not variable.anual and _parte_repetida(serie) <= MAX_REPETIDOS
    if mensual:
        t = np.asarray(anomalias.index.year + (anomalias.index.month - 0.5) / 12, dtype=float)
        y = anomalias.to_numpy()
    else:
        t, y = anios, anual.to_numpy()

    regresion = est.regresion_lineal(t, y)
    ic_historias = est.ic_historias_alternativas(t, y)
    mk = est.mann_kendall_sin_memoria(t, y)
    sen = est.pendiente_sen(t, y).pendiente
    largo_min = max(10, len(anual) // 3)
    triangulo = est.triangulo_de_ventanas(anios, anual.to_numpy(), largo_min)

    # Las cinco pruebas: cada una es un objeto que sabe evaluarse sobre la serie (ver pruebas.py).
    analizada = SerieAnalizada(variable, mensual, t, y, anios, anual.to_numpy(), regresion, ic_historias, mk, sen,
                               triangulo, largo_min)
    pruebas = tuple(prueba.evaluar(analizada) for prueba in bateria(analizada))
    fraccion = analizada.fraccion_de_periodos

    ruido = y - (regresion.intercepto + regresion.pendiente * t)
    necesarios = est.anios_para_detectar(regresion.pendiente, float(ruido.std(ddof=1)),
                                         regresion.r1, por_anio=12 if mensual else 1)

    return Interrogatorio(variable, "mensual" if mensual else "anual", serie, anomalias, anual,
                          t, y, regresion, ic_historias, mk, est.mann_kendall(y), sen,
                          triangulo, fraccion, pruebas, necesarios,
                          est.punto_de_cambio(anios, anual.to_numpy()), tuple(meses))


def tendencia_por_mes(serie_mensual: pd.Series, variable: Variable) -> pd.DataFrame:
    """¿En qué meses del año ocurre el cambio? La tendencia de cada mes del calendario por separado.

    Cada mes se analiza con un dato por año (todos los eneros, todos los febreros...).
    Columnas: mes, nombre, n, pendiente_decada, ic_bajo, ic_alto (IC del 95 % de la pendiente,
    con tamaño de muestra efectivo), p (Mann-Kendall sin memoria), p_ajustada
    (Benjamini-Hochberg, porque son 12 pruebas) y significativa.
    """
    serie = serie_mensual.loc[str(variable.desde):].dropna()
    filas = []
    for mes in TODO_EL_ANIO:
        anual = serie_de_temporada(serie, (mes,))
        fila = {"mes": mes, "nombre": MESES[mes - 1], "n": len(anual), "pendiente_decada": np.nan,
                "ic_bajo": np.nan, "ic_alto": np.nan, "p": np.nan}
        if not _motivo_imposible(anual):
            anios, valores = anual.index.to_numpy(dtype=float), anual.to_numpy()
            recta = est.regresion_lineal(anios, valores)
            fila.update(pendiente_decada=recta.pendiente * 10, ic_bajo=recta.ic_bajo * 10,
                        ic_alto=recta.ic_alto * 10, p=est.mann_kendall_sin_memoria(anios, valores).prueba.p)
        filas.append(fila)
    tabla = pd.DataFrame(filas)
    validas = tabla["p"].notna()
    tabla["p_ajustada"] = np.nan
    if validas.any():
        tabla.loc[validas, "p_ajustada"] = est.benjamini_hochberg(tabla.loc[validas, "p"].to_numpy())
    tabla["significativa"] = tabla["p_ajustada"] < est.ALFA
    return tabla


def _p_clasica(serie: pd.Series, anual: np.ndarray, variable: Variable, meses: tuple[int, ...]) -> float:
    """Valor p de la prueba de Mann-Kendall tal como suele aplicarse: sobre los datos mensuales sin
    ciclo estacional, sin corregir la autocorrelación. Sirve solo de referencia."""
    if variable.anual or len(meses) < 12 or _parte_repetida(serie) > MAX_REPETIDOS:
        return float(est.mann_kendall(anual).p)
    return float(est.mann_kendall(est.quitar_ciclo_estacional(serie)[0].to_numpy()).p)


@dataclass(frozen=True)
class Relacion:
    """Cómo varían juntas dos variables de un mismo lugar."""

    correlacion: est.Correlacion
    resolucion: str  # "mensual" o "anual"
    fechas: pd.Index
    a: np.ndarray  # anomalías de la primera variable, sin tendencia y estandarizadas
    b: np.ndarray


def relacionar(a: Interrogatorio, b: Interrogatorio) -> Relacion:
    """Correlación entre las anomalías de dos análisis, sobre las fechas que comparten.

    Si las dos se analizaron con datos mensuales se usan sus anomalías mensuales; si alguna
    es anual, los valores anuales de las dos.
    """
    if a.resolucion == b.resolucion == "mensual":
        juntas = pd.concat([a.anomalias.rename("a"), b.anomalias.rename("b")], axis=1).dropna()
        t = np.asarray(juntas.index.year + (juntas.index.month - 0.5) / 12, dtype=float)
        resolucion = "mensual"
    else:
        juntas = pd.concat([a.anual.rename("a"), b.anual.rename("b")], axis=1).dropna()
        t = juntas.index.to_numpy(dtype=float)
        resolucion = "anual"
    if len(juntas) < MIN_ANIOS:
        raise CasoImposible(T("Las dos variables comparten muy pocos datos para relacionarlas.",
                              "The two variables share too few data points to relate them."))
    def estandar(x: np.ndarray) -> np.ndarray:
        sin_tendencia = x - np.polyval(np.polyfit(t, x, 1), t)
        return sin_tendencia / (sin_tendencia.std(ddof=1) or 1.0)

    return Relacion(est.correlacion(juntas["a"].to_numpy(), juntas["b"].to_numpy(), t), resolucion,
                    juntas.index, estandar(juntas["a"].to_numpy()), estandar(juntas["b"].to_numpy()))


def escanear(datos: pd.DataFrame, variables: tuple[Variable, ...] = CATALOGO,
             meses: tuple[int, ...] = TODO_EL_ANIO) -> pd.DataFrame:
    """Exploración de variables: tendencia de cada una, en una escala comparable.

    Usa un valor por año (de todo el año o de los `meses` elegidos). `estandarizada` es la pendiente por década dividida entre la
    variación típica de un año a otro, así que un cambio de temperatura y uno de lluvia
    se pueden poner en la misma escala. Los valores p (Mann-Kendall sin memoria) se
    ajustan con Benjamini-Hochberg porque se examinan muchas variables a la vez.
    """
    filas = []
    for v in variables:
        fila = {"codigo": v.codigo, "nombre": v.nombre, "categoria": v.categoria,
                "unidad": v.unidad, "anios": 0, "pendiente_decada": np.nan,
                "estandarizada": np.nan, "p": np.nan, "p_clasica": np.nan, "nota": ""}
        if v.codigo in datos:
            anual = serie_anual(datos[v.codigo].loc[str(v.desde):].dropna(), meses, v.anual)
        else:
            anual = pd.Series(dtype=float)
        fila["anios"] = len(anual)
        fila["nota"] = _solo_anual() if v.anual and len(meses) < 12 else _motivo_imposible(anual)
        if not fila["nota"]:
            anios, valores = anual.index.to_numpy(dtype=float), anual.to_numpy()
            recta = est.regresion_lineal(anios, valores)
            ruido = valores - (recta.intercepto + recta.pendiente * anios)
            fila["pendiente_decada"] = recta.pendiente * 10
            fila["estandarizada"] = recta.pendiente * 10 / ruido.std(ddof=1)
            fila["p"] = est.mann_kendall_sin_memoria(anios, valores).prueba.p
            fila["p_clasica"] = _p_clasica(datos[v.codigo].loc[str(v.desde):].dropna(), valores, v, meses)
        filas.append(fila)

    tabla = pd.DataFrame(filas)
    validas = tabla["p"].notna()
    tabla["p_ajustada"] = np.nan
    tabla.loc[validas, "p_ajustada"] = est.benjamini_hochberg(tabla.loc[validas, "p"].to_numpy())
    tabla["significativa"] = tabla["p_ajustada"] < est.ALFA
    orden = tabla["estandarizada"].abs().sort_values(ascending=False, na_position="last").index
    return tabla.loc[orden].reset_index(drop=True)
