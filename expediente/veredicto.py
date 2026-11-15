"""Redacta el resultado a partir de los números del análisis.

Todo el texto sale de plantillas: ninguna cifra se inventa ni se redondea distinto de
como se calculó.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from . import estadistica as est
from .caso import NIVELES, N_PRUEBAS, Interrogatorio, numero, valor_p
from .idioma import T, Tupla

ADVERTENCIAS_GENERALES = Tupla((
    "Las variables de MERRA-2 combinan un modelo con observaciones, y los cambios de instrumentos a "
    "lo largo de las décadas pueden dejar huella en algunas series. Las de GPM, MODIS y GRACE son "
    "observaciones de satélite, con registros más cortos.",
    "Una tendencia significativa dice que algo está cambiando, no por qué cambia.",
), (
    "MERRA-2 variables combine a model with observations, and changes of instruments over the "
    "decades can leave a mark on some series. GPM, MODIS and GRACE variables are satellite "
    "observations, with shorter records.",
    "A significant trend says that something is changing, not why it is changing.",
))

SUPUESTOS = Tupla((
    "La tendencia se describe con una recta. Un cambio que se acelera, se frena o se invierte "
    "queda mal representado; la prueba de sensibilidad al periodo ayuda a detectarlo.",
    "La autocorrelación de la serie se modela como un proceso autorregresivo de primer orden, AR(1).",
    "La serie es homogénea: se supone que el instrumento y el método de medición no cambiaron "
    "durante el periodo.",
), (
    "The trend is described with a straight line. A change that speeds up, slows down or reverses "
    "is poorly represented; the period-sensitivity test helps to detect it.",
    "The autocorrelation of the series is modelled as a first-order autoregressive process, AR(1).",
    "The series is homogeneous: the instrument and the measurement method are assumed not to have "
    "changed during the period.",
))


@dataclass(frozen=True)
class Veredicto:
    titular: str
    cuanto: str
    evidencia: str
    espera: str  # vacío si no aplica
    relevancia: str  # vacío si no hay tendencia que calificar
    no_lineal: str  # vacío si una recta describe razonablemente la serie
    registro_corto: str  # vacío si el registro alcanza el estándar climatológico
    advertencias: tuple[str, ...]


def _titular(r: Interrogatorio) -> str:
    rumbo = T("en aumento", "increasing") if r.sube else T("en descenso", "decreasing")
    nombre = r.variable.nombre + (f", {r.temporada}" if r.por_temporada else "")
    if r.nivel == "solida":
        return T(f"{nombre}: {rumbo}, con evidencia sólida", f"{nombre}: {rumbo}, with solid evidence")
    if r.nivel == "fuerte":
        return T(f"{nombre}: {rumbo}, con evidencia fuerte", f"{nombre}: {rumbo}, with strong evidence")
    if r.nivel == "indicios":
        return T(f"{nombre}: posiblemente {rumbo}, con evidencia débil", f"{nombre}: possibly {rumbo}, with weak evidence")
    return T(f"{nombre}: sin evidencia suficiente de una tendencia", f"{nombre}: insufficient evidence of a trend")


def _cuanto(r: Interrogatorio) -> str:
    u = r.variable.unidad
    bajo, alto = r.ic_decada
    rango = T(f"de {numero(bajo, signo=True)} a {numero(alto, signo=True)}",
              f"{numero(bajo, signo=True)} to {numero(alto, signo=True)}")
    tasa = numero(r.pendiente_decada, signo=True)
    if r.nivel == "sin":
        return T(f"La mejor estimación es {tasa} {u} por década, "
                 f"pero el intervalo de confianza del 95 % ({rango}) incluye el cero o no supera las pruebas: "
                 f"no se distingue de la ausencia de cambio.",
                 f"The best estimate is {tasa} {u} per decade, but the 95 % confidence interval ({rango}) "
                 f"includes zero or does not pass the tests: it cannot be told apart from no change.")
    texto = T(f"Cambia {tasa} {u} por década "
              f"(intervalo de confianza del 95 %: {rango}). En los {r.anios_de_datos:.0f} años analizados "
              f"eso suma {numero(r.cambio_total, signo=True)} {u}",
              f"It changes by {tasa} {u} per decade (95 % confidence interval: {rango}). Over the "
              f"{r.anios_de_datos:.0f} years analysed that adds up to {numero(r.cambio_total, signo=True)} {u}")
    if r.cambio_relativo is not None:
        texto += T(f", cerca de {r.cambio_relativo:+.0f} % de su valor promedio",
                   f", about {r.cambio_relativo:+.0f} % of its mean value")
    return texto + "."


def _evidencia(r: Interrogatorio) -> str:
    texto = T(f"Superó {r.aprobadas} de {N_PRUEBAS} pruebas de significancia.",
              f"It passed {r.aprobadas} of {N_PRUEBAS} significance tests.")
    falladas = [p.nombre for p in r.pruebas if not p.aprobada]
    if falladas and r.aprobadas:
        texto += T(" No superó: ", " It did not pass: ") + ", ".join(falladas) + "."
    return texto


def _espera(r: Interrogatorio) -> str:
    """Cuántos años más de datos harían falta, solo cuando la evidencia aún no convence."""
    if r.nivel in ("solida", "fuerte") or not isfinite(r.anios_necesarios):
        return ""
    tenemos = r.anios_de_datos
    if r.anios_necesarios <= tenemos:
        return T(f"Con {tenemos:.0f} años ya habría datos de sobra para detectar un cambio constante "
                 f"de este tamaño. Que no supere las pruebas sugiere que el cambio no ha sido constante.",
                 f"With {tenemos:.0f} years there would already be more than enough data to detect a steady "
                 f"change of this size. Not passing the tests suggests that the change has not been steady.")
    if r.anios_necesarios > 500:
        return T("Si el cambio real fuera del tamaño estimado, es tan pequeño frente a la variabilidad natural de "
                 "este lugar que harían falta más de 500 años de datos para detectarlo.",
                 "If the real change were of the estimated size, it is so small compared with the natural "
                 "variability of this place that more than 500 years of data would be needed to detect it.")
    return T(f"Si el cambio real fuera del tamaño estimado, se necesitarían unos "
             f"{r.anios_necesarios:.0f} años de datos para distinguirlo de la variabilidad natural de este lugar. "
             f"Hay {tenemos:.0f}: faltarían unos {r.anios_necesarios - tenemos:.0f}.",
             f"If the real change were of the estimated size, about {r.anios_necesarios:.0f} years of data "
             f"would be needed to tell it apart from the natural variability of this place. There are "
             f"{tenemos:.0f}: about {r.anios_necesarios - tenemos:.0f} more would be needed.")


def relevancia_practica(r: Interrogatorio) -> str:
    """Tamaño del cambio frente a la variabilidad natural: significativo no es lo mismo que importante."""
    veces = r.cambio_en_variabilidad
    if veces is None or r.nivel == "sin":
        return ""
    veces = abs(veces)
    if veces < 1:
        tamano = T("Es un cambio pequeño frente a la variabilidad natural: un año típico se aparta "
                   "de lo normal más que eso.",
                   "It is a small change compared with natural variability: a typical year departs from "
                   "normal by more than that.")
    elif veces < 2:
        tamano = T("Es un cambio comparable a la variabilidad natural de un año a otro.",
                   "It is a change comparable to the natural variability from one year to the next.")
    else:
        tamano = T("Es un cambio grande: supera con claridad la variabilidad natural de un año a otro.",
                   "It is a large change: it clearly exceeds the natural variability from one year to the next.")
    return T(f"El cambio acumulado equivale a {veces:.1f} veces la desviación estándar interanual "
             f"(lo que la variable suele variar de un año a otro). {tamano} Que una tendencia sea "
             f"estadísticamente significativa no implica que su magnitud sea importante: eso depende "
             f"de su efecto en el sistema que se estudia.",
             f"The accumulated change equals {veces:.1f} times the interannual standard deviation (how much "
             f"the variable usually varies from one year to the next). {tamano} A trend being statistically "
             f"significant does not mean that its size matters: that depends on its effect on the system "
             f"under study.")


ANIOS_CLIMA = 30  # periodo estándar de la Organización Meteorológica Mundial para describir el clima


def aviso_registro_corto(r: Interrogatorio) -> str:
    """Advierte cuando el registro es más corto que el periodo estándar para describir el clima."""
    if r.anios_de_datos >= ANIOS_CLIMA:
        return ""
    return T(f"El análisis usa {r.anios_de_datos:.0f} años de datos. La Organización Meteorológica "
             f"Mundial usa periodos de {ANIOS_CLIMA} años para describir el clima; en un registro más "
             f"corto, una tendencia puede reflejar la variabilidad natural de una o dos décadas y no "
             f"un cambio de fondo. El resultado describe lo ocurrido en este periodo, no "
             f"necesariamente una tendencia climática.",
             f"The analysis uses {r.anios_de_datos:.0f} years of data. The World Meteorological Organization "
             f"uses {ANIOS_CLIMA}-year periods to describe climate; in a shorter record, a trend may reflect "
             f"the natural variability of one or two decades and not an underlying change. The result "
             f"describes what happened in this period, not necessarily a climate trend.")


def cambio_de_comportamiento(r: Interrogatorio) -> str:
    """Describe la regresión en dos tramos: ¿la tendencia se mantuvo, cambió de ritmo o se invirtió?"""
    c = r.cambio
    if c is None:
        return ""
    u = r.variable.unidad
    antes, despues = numero(c.antes.pendiente * 10, signo=True), numero(c.despues.pendiente * 10, signo=True)
    tramos = T(f"{antes} {u} por década hasta {c.anio} y {despues} después",
               f"{antes} {u} per decade until {c.anio} and {despues} afterwards")
    if c.cambia_de_signo:
        return T(f"La tendencia se invirtió alrededor de {c.anio}: {tramos}. Una sola recta no describe "
                 f"bien esta serie; la tasa de cambio global promedia dos comportamientos opuestos.",
                 f"The trend reversed around {c.anio}: {tramos}. A single line does not describe this "
                 f"series well; the overall rate of change averages two opposite behaviours.")
    if c.mejora < 0.25:
        return T(f"Dividir la serie en dos tramos apenas mejora el ajuste ({100 * c.mejora:.0f} % menos "
                 f"error): una sola recta la describe razonablemente.",
                 f"Splitting the series into two segments barely improves the fit ({100 * c.mejora:.0f} % "
                 f"less error): a single line describes it reasonably well.")
    return T(f"El mayor cambio de comportamiento ocurre alrededor de {c.anio}: {tramos}. La tendencia "
             f"no se invirtió, pero su ritmo no fue constante.",
             f"The largest change in behaviour occurs around {c.anio}: {tramos}. The trend did not "
             f"reverse, but its pace was not constant.")


def aviso_no_lineal(r: Interrogatorio) -> str:
    return cambio_de_comportamiento(r) if r.cambio is not None and r.cambio.cambia_de_signo else ""


def ficha_tecnica(r: Interrogatorio) -> list[tuple[str, str]]:
    """Diseño del análisis, en el formato que se pide al reportar significancia estadística."""
    inicio, fin = r.serie.index.min(), r.serie.index.max()
    datos = (T("anomalías mensuales", "monthly anomalies") if r.resolucion == "mensual"
             else T(f"promedios de {r.temporada} (uno por año)", f"{r.temporada} means (one per year)") if r.por_temporada
             else T("valores anuales del índice", "annual values of the index") if r.variable.anual
             else T("promedios anuales", "annual means"))
    formato = "%Y" if r.variable.anual else "%m/%Y"
    r1 = max(r.regresion.r1, 0)
    return [
        (T("Periodo", "Period"), T(f"{inicio:{formato}} a {fin:{formato}}", f"{inicio:{formato}} to {fin:{formato}}")),
        (T("Meses analizados", "Months analysed"), r.temporada.capitalize()),
        (T("Tamaño de muestra", "Sample size"),
         T(f"{r.regresion.n} {datos}; tamaño efectivo de {r.regresion.n_efectivo:.0f} "
           f"tras descontar la autocorrelación (r₁ = {r1:.2f})",
           f"{r.regresion.n} {datos}; effective size of {r.regresion.n_efectivo:.0f} "
           f"after discounting autocorrelation (r₁ = {r1:.2f})")),
        (T("Tasa de cambio", "Rate of change"),
         T("Pendiente de una regresión lineal por mínimos cuadrados", "Slope of a least-squares linear regression")),
        (T("Coeficiente de determinación R²", "Coefficient of determination R²"),
         T(f"{r.regresion.r2:.2f}: la recta explica {100 * r.regresion.r2:.0f} % de la "
           f"variación de los datos; el resto es variabilidad alrededor de la tendencia",
           f"{r.regresion.r2:.2f}: the line explains {100 * r.regresion.r2:.0f} % of the variation in "
           f"the data; the rest is variability around the trend")),
        (T("Intervalo de confianza", "Confidence interval"),
         T("95 %, por bootstrap de 2,000 series con autocorrelación AR(1)",
           "95 %, by bootstrap of 2,000 series with AR(1) autocorrelation")),
        (T("Nivel de significancia", "Significance level"),
         T(f"α = {est.ALFA}, pruebas bilaterales", f"α = {est.ALFA}, two-sided tests")),
        (T("Valores p", "p-values"),
         T(f"Mann-Kendall con preblanqueo: {valor_p(r.mk.prueba.p)}. Prueba t con muestra "
           f"efectiva: {valor_p(r.regresion.p)}. Mann-Kendall sin corregir, como "
           f"referencia: {valor_p(r.mk_ingenuo.p)}",
           f"Mann-Kendall with prewhitening: {valor_p(r.mk.prueba.p)}. t-test with effective sample: "
           f"{valor_p(r.regresion.p)}. Uncorrected Mann-Kendall, for reference: {valor_p(r.mk_ingenuo.p)}")),
        (T("Nivel de evidencia", "Level of evidence"),
         T(f"{NIVELES[r.nivel]}: {r.aprobadas} de {N_PRUEBAS} pruebas. Sólida = 5, "
           f"fuerte = 4, débil = 2 o 3, insuficiente = 0 o 1",
           f"{NIVELES[r.nivel]}: {r.aprobadas} of {N_PRUEBAS} tests. Solid = 5, strong = 4, "
           f"weak = 2 or 3, insufficient = 0 or 1")),
    ]


def redactar(r: Interrogatorio) -> Veredicto:
    resolucion = T(f"Cada dato representa un área, no un sitio puntual. Resolución espacial de esta "
                   f"variable: {r.variable.resolucion}.",
                   f"Each value represents an area, not a single point. Spatial resolution of this "
                   f"variable: {r.variable.resolucion}.")
    advertencias = ((r.variable.aviso,) if r.variable.aviso else ()) + (resolucion,) + tuple(ADVERTENCIAS_GENERALES)
    return Veredicto(_titular(r), _cuanto(r), _evidencia(r), _espera(r), relevancia_practica(r),
                     aviso_no_lineal(r), aviso_registro_corto(r), advertencias)


def informe_markdown(r: Interrogatorio, lugar: str, lat: float, lon: float) -> str:
    """El informe completo como texto, para guardar o compartir."""
    v = redactar(r)
    inicio, fin = r.serie.index.min(), r.serie.index.max()
    lineas = [
        f"# Informe de tendencia: {r.variable.nombre} en {lugar}",
        "",
        f"**Resultado: {v.titular}** ({NIVELES[r.nivel].lower()})",
        "",
        "## Variable",
        f"{r.variable.nombre} ({r.variable.unidad}). {r.variable.definicion}",
        f"Fuente: {r.variable.fuente}.",
        "",
        "## Sitio y periodo",
        f"{lugar} (latitud {lat:.2f}, longitud {lon:.2f}), de {inicio:%m/%Y} a {fin:%m/%Y}.",
        "",
        "## Tasa de cambio",
        v.cuanto,
        "",
        "## Significancia estadística",
        v.evidencia,
        "",
        "| Prueba | Pregunta | Resultado | ¿Pasa? |",
        "|---|---|---|---|",
    ]
    lineas += [f"| {p.nombre} | {p.pregunta} | {p.resultado} | {'Sí' if p.aprobada else 'No'} |"
               for p in r.pruebas]
    lineas += ["", f"Sin corregir la autocorrelación, la prueba de Mann-Kendall daba {valor_p(r.mk_ingenuo.p)}."]
    if v.espera:
        lineas += ["", "## Años de datos necesarios para detectarla", v.espera]
    if v.relevancia:
        lineas += ["", "## Relevancia práctica", v.relevancia]
    if cambio_de_comportamiento(r):
        lineas += ["", "## Cambio de comportamiento", cambio_de_comportamiento(r)]
    if v.registro_corto:
        lineas += ["", "## Registro corto", v.registro_corto]
    lineas += ["", "## Ficha técnica", "", "| Característica | Detalle |", "|---|---|"]
    lineas += [f"| {nombre} | {detalle} |" for nombre, detalle in ficha_tecnica(r)]
    lineas += ["", "## Supuestos"] + [f"- {supuesto}" for supuesto in SUPUESTOS]
    lineas += ["", "## Limitaciones"] + [f"- {a}" for a in v.advertencias]
    return "\n".join(lineas) + "\n"


def comparar(a: Interrogatorio, b: Interrogatorio, nombre_a: str, nombre_b: str) -> str:
    """Resultado de la comparación: ¿la variable tiene el mismo signo de tendencia en los dos lugares?"""
    u = a.variable.unidad
    firme_a, firme_b = a.nivel in ("solida", "fuerte"), b.nivel in ("solida", "fuerte")
    rumbo = lambda r: T("sube", "it rises") if r.sube else T("baja", "it falls")
    ritmo = lambda r: T(f"{numero(r.pendiente_decada, signo=True)} {u} por década",
                        f"{numero(r.pendiente_decada, signo=True)} {u} per decade")
    if firme_a and firme_b and a.sube != b.sube:
        return T(f"Tendencias opuestas: {rumbo(a)} en {nombre_a} ({ritmo(a)}) y {rumbo(b)} en "
                 f"{nombre_b} ({ritmo(b)}), con evidencia firme en los dos.",
                 f"Opposite trends: {rumbo(a)} in {nombre_a} ({ritmo(a)}) and {rumbo(b)} in "
                 f"{nombre_b} ({ritmo(b)}), with firm evidence in both.")
    if firme_a and firme_b:
        rapido, lento = (a, b) if abs(a.pendiente_decada) >= abs(b.pendiente_decada) else (b, a)
        nombre_rapido = nombre_a if rapido is a else nombre_b
        veces = abs(rapido.pendiente_decada) / abs(lento.pendiente_decada)
        return T(f"Mismo signo, distinta tasa: {rumbo(a)} en los dos lugares, pero en "
                 f"{nombre_rapido} lo hace {veces:.1f} veces más rápido ({ritmo(a)} en {nombre_a}, "
                 f"{ritmo(b)} en {nombre_b}).",
                 f"Same sign, different rate: {rumbo(a)} in both places, but in {nombre_rapido} it does so "
                 f"{veces:.1f} times faster ({ritmo(a)} in {nombre_a}, {ritmo(b)} in {nombre_b}).")
    if firme_a or firme_b:
        firme, nombre_firme, nombre_otro = (a, nombre_a, nombre_b) if firme_a else (b, nombre_b, nombre_a)
        return T(f"Tendencia en un solo lugar: {rumbo(firme)} en {nombre_firme} ({ritmo(firme)}), mientras "
                 f"que en {nombre_otro} no hay evidencia suficiente de una tendencia.",
                 f"Trend in only one place: {rumbo(firme)} in {nombre_firme} ({ritmo(firme)}), while in "
                 f"{nombre_otro} there is insufficient evidence of a trend.")
    return T("Ninguno de los dos lugares muestra evidencia firme de una tendencia.",
             "Neither of the two places shows firm evidence of a trend.")
