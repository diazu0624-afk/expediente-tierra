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

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
TODO_EL_ANIO = tuple(range(1, 13))
# Estaciones meteorológicas, nombradas por sus meses para que sirvan en los dos hemisferios.
TEMPORADAS: dict[str, tuple[int, ...]] = {
    "DEF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11),
}


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
        return "todo el año"
    nombres = [MESES[m - 1] for m in meses]
    if len(meses) == 1:
        return nombres[0]
    seguidos = all((b - a) % 12 == 1 for a, b in zip(meses, meses[1:]))
    if seguidos:
        return f"{nombres[0]} a {nombres[-1]}" if len(meses) > 2 else f"{nombres[0]} y {nombres[1]}"
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


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


SOLO_ANUAL = "Es un índice anual: no se calcula por temporada"


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
        periodo = f"de {self.anual.index.min()} a {self.anual.index.max()}"
        if self.resolucion == "mensual":
            return f"n = {self.n} meses ({len(self.anual)} años completos), {periodo}"
        return f"n = {self.n} años, {periodo}"

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


def interrogar(serie_mensual: pd.Series, variable: Variable,
               meses: tuple[int, ...] = TODO_EL_ANIO) -> Interrogatorio:
    """Somete una variable a las cinco pruebas.

    Con `meses` se analiza solo una parte del año (una estación o un mes): la serie se
    reduce a un valor por año y se interroga a esa resolución.
    """
    serie = serie_mensual.loc[str(variable.desde):].dropna()
    por_temporada = len(meses) < 12
    if por_temporada and variable.anual:
        raise CasoImposible(SOLO_ANUAL + ". Elige «Todo el año» en la barra lateral.")
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
            else "no es significativa, se excluya el año que se excluya" if fallos == len(anual)
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
                "estandarizada": np.nan, "p": np.nan, "nota": ""}
        if v.codigo in datos:
            anual = serie_anual(datos[v.codigo].loc[str(v.desde):].dropna(), meses, v.anual)
        else:
            anual = pd.Series(dtype=float)
        fila["anios"] = len(anual)
        fila["nota"] = SOLO_ANUAL if v.anual and len(meses) < 12 else _motivo_imposible(anual)
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
