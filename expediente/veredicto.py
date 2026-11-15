"""Redacta el resultado a partir de los números del análisis.

Todo el texto sale de plantillas: ninguna cifra se inventa ni se redondea distinto de
como se calculó.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from . import estadistica as est
from .caso import NIVELES, N_PRUEBAS, Interrogatorio, numero, valor_p

ADVERTENCIAS_GENERALES = (
    "Las variables de MERRA-2 combinan un modelo con observaciones, y los cambios de instrumentos a "
    "lo largo de las décadas pueden dejar huella en algunas series. Las de GPM, MODIS y GRACE son "
    "observaciones de satélite, con registros más cortos.",
    "Una tendencia significativa dice que algo está cambiando, no por qué cambia.",
)

SUPUESTOS = (
    "La tendencia se describe con una recta. Un cambio que se acelera, se frena o se invierte "
    "queda mal representado; la prueba de sensibilidad al periodo ayuda a detectarlo.",
    "La autocorrelación de la serie se modela como un proceso autorregresivo de primer orden, AR(1).",
    "La serie es homogénea: se supone que el instrumento y el método de medición no cambiaron "
    "durante el periodo.",
)


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
    rumbo = "en aumento" if r.sube else "en descenso"
    nombre = r.variable.nombre + (f", {r.temporada}" if r.por_temporada else "")
    if r.nivel == "solida":
        return f"{nombre}: {rumbo}, con evidencia sólida"
    if r.nivel == "fuerte":
        return f"{nombre}: {rumbo}, con evidencia fuerte"
    if r.nivel == "indicios":
        return f"{nombre}: posiblemente {rumbo}, con evidencia débil"
    return f"{nombre}: sin evidencia suficiente de una tendencia"


def _cuanto(r: Interrogatorio) -> str:
    u = r.variable.unidad
    bajo, alto = r.ic_decada
    rango = f"de {numero(bajo, signo=True)} a {numero(alto, signo=True)}"
    if r.nivel == "sin":
        return (f"La mejor estimación es {numero(r.pendiente_decada, signo=True)} {u} por década, "
                f"pero el intervalo de confianza del 95 % ({rango}) incluye el cero o no supera las pruebas: "
                f"no se distingue de la ausencia de cambio.")
    texto = (f"Cambia {numero(r.pendiente_decada, signo=True)} {u} por década "
             f"(intervalo de confianza del 95 %: {rango}). En los {r.anios_de_datos:.0f} años analizados "
             f"eso suma {numero(r.cambio_total, signo=True)} {u}")
    if r.cambio_relativo is not None:
        texto += f", cerca de {r.cambio_relativo:+.0f} % de su valor promedio"
    return texto + "."


def _evidencia(r: Interrogatorio) -> str:
    texto = f"Superó {r.aprobadas} de {N_PRUEBAS} pruebas de significancia."
    falladas = [p.nombre for p in r.pruebas if not p.aprobada]
    if falladas and r.aprobadas:
        texto += " No superó: " + ", ".join(falladas) + "."
    return texto


def _espera(r: Interrogatorio) -> str:
    """Cuántos años más de datos harían falta, solo cuando la evidencia aún no convence."""
    if r.nivel in ("solida", "fuerte") or not isfinite(r.anios_necesarios):
        return ""
    tenemos = r.anios_de_datos
    if r.anios_necesarios <= tenemos:
        return (f"Con {tenemos:.0f} años ya habría datos de sobra para detectar un cambio constante "
                f"de este tamaño. Que no supere las pruebas sugiere que el cambio no ha sido constante.")
    if r.anios_necesarios > 500:
        return ("Si el cambio real fuera del tamaño estimado, es tan pequeño frente a la variabilidad natural de "
                "este lugar que harían falta más de 500 años de datos para detectarlo.")
    return (f"Si el cambio real fuera del tamaño estimado, se necesitarían unos "
            f"{r.anios_necesarios:.0f} años de datos para distinguirlo de la variabilidad natural de este lugar. "
            f"Hay {tenemos:.0f}: faltarían unos {r.anios_necesarios - tenemos:.0f}.")


def relevancia_practica(r: Interrogatorio) -> str:
    """Tamaño del cambio frente a la variabilidad natural: significativo no es lo mismo que importante."""
    veces = r.cambio_en_variabilidad
    if veces is None or r.nivel == "sin":
        return ""
    veces = abs(veces)
    if veces < 1:
        tamano = ("Es un cambio pequeño frente a la variabilidad natural: un año típico se aparta "
                  "de lo normal más que eso.")
    elif veces < 2:
        tamano = "Es un cambio comparable a la variabilidad natural de un año a otro."
    else:
        tamano = "Es un cambio grande: supera con claridad la variabilidad natural de un año a otro."
    return (f"El cambio acumulado equivale a {veces:.1f} veces la desviación estándar interanual "
            f"(lo que la variable suele variar de un año a otro). {tamano} Que una tendencia sea "
            f"estadísticamente significativa no implica que su magnitud sea importante: eso depende "
            f"de su efecto en el sistema que se estudia.")


ANIOS_CLIMA = 30  # periodo estándar de la Organización Meteorológica Mundial para describir el clima


def aviso_registro_corto(r: Interrogatorio) -> str:
    """Advierte cuando el registro es más corto que el periodo estándar para describir el clima."""
    if r.anios_de_datos >= ANIOS_CLIMA:
        return ""
    return (f"El análisis usa {r.anios_de_datos:.0f} años de datos. La Organización Meteorológica "
            f"Mundial usa periodos de {ANIOS_CLIMA} años para describir el clima; en un registro más "
            f"corto, una tendencia puede reflejar la variabilidad natural de una o dos décadas y no "
            f"un cambio de fondo. El resultado describe lo ocurrido en este periodo, no "
            f"necesariamente una tendencia climática.")


def cambio_de_comportamiento(r: Interrogatorio) -> str:
    """Describe la regresión en dos tramos: ¿la tendencia se mantuvo, cambió de ritmo o se invirtió?"""
    c = r.cambio
    if c is None:
        return ""
    u = r.variable.unidad
    antes, despues = numero(c.antes.pendiente * 10, signo=True), numero(c.despues.pendiente * 10, signo=True)
    tramos = f"{antes} {u} por década hasta {c.anio} y {despues} después"
    if c.cambia_de_signo:
        return (f"La tendencia se invirtió alrededor de {c.anio}: {tramos}. Una sola recta no describe "
                f"bien esta serie; la tasa de cambio global promedia dos comportamientos opuestos.")
    if c.mejora < 0.25:
        return (f"Dividir la serie en dos tramos apenas mejora el ajuste ({100 * c.mejora:.0f} % menos "
                f"error): una sola recta la describe razonablemente.")
    return (f"El mayor cambio de comportamiento ocurre alrededor de {c.anio}: {tramos}. La tendencia "
            f"no se invirtió, pero su ritmo no fue constante.")


def aviso_no_lineal(r: Interrogatorio) -> str:
    return cambio_de_comportamiento(r) if r.cambio is not None and r.cambio.cambia_de_signo else ""


def ficha_tecnica(r: Interrogatorio) -> list[tuple[str, str]]:
    """Diseño del análisis, en el formato que se pide al reportar significancia estadística."""
    inicio, fin = r.serie.index.min(), r.serie.index.max()
    datos = ("anomalías mensuales" if r.resolucion == "mensual"
             else f"promedios de {r.temporada} (uno por año)" if r.por_temporada else "promedios anuales")
    return [
        ("Periodo", f"{inicio:%m/%Y} a {fin:%m/%Y}"),
        ("Meses analizados", r.temporada.capitalize()),
        ("Tamaño de muestra", f"{r.regresion.n} {datos}; tamaño efectivo de {r.regresion.n_efectivo:.0f} "
                              f"tras descontar la autocorrelación (r₁ = {max(r.regresion.r1, 0):.2f})"),
        ("Tasa de cambio", "Pendiente de una regresión lineal por mínimos cuadrados"),
        ("Coeficiente de determinación R²", f"{r.regresion.r2:.2f}: la recta explica {100 * r.regresion.r2:.0f} % de la "
                                            f"variación de los datos; el resto es variabilidad alrededor de la tendencia"),
        ("Intervalo de confianza", "95 %, por bootstrap de 2,000 series con autocorrelación AR(1)"),
        ("Nivel de significancia", f"α = {est.ALFA}, pruebas bilaterales"),
        ("Valores p", f"Mann-Kendall con preblanqueo: {valor_p(r.mk.prueba.p)}. Prueba t con muestra "
                      f"efectiva: {valor_p(r.regresion.p)}. Mann-Kendall sin corregir, como "
                      f"referencia: {valor_p(r.mk_ingenuo.p)}"),
        ("Nivel de evidencia", f"{NIVELES[r.nivel]}: {r.aprobadas} de {N_PRUEBAS} pruebas. Sólida = 5, "
                               f"fuerte = 4, débil = 2 o 3, insuficiente = 0 o 1"),
    ]


def redactar(r: Interrogatorio) -> Veredicto:
    resolucion = (f"Cada dato representa un área, no un sitio puntual. Resolución espacial de esta "
                  f"variable: {r.variable.resolucion}.")
    advertencias = ((r.variable.aviso,) if r.variable.aviso else ()) + (resolucion,) + ADVERTENCIAS_GENERALES
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
    rumbo = lambda r: "sube" if r.sube else "baja"
    ritmo = lambda r: f"{numero(r.pendiente_decada, signo=True)} {u} por década"
    if firme_a and firme_b and a.sube != b.sube:
        return (f"Tendencias opuestas: {rumbo(a)} en {nombre_a} ({ritmo(a)}) y {rumbo(b)} en "
                f"{nombre_b} ({ritmo(b)}), con evidencia firme en los dos.")
    if firme_a and firme_b:
        rapido, lento = (a, b) if abs(a.pendiente_decada) >= abs(b.pendiente_decada) else (b, a)
        nombre_rapido = nombre_a if rapido is a else nombre_b
        veces = abs(rapido.pendiente_decada) / abs(lento.pendiente_decada)
        return (f"Mismo signo, distinta tasa: {rumbo(a)} en los dos lugares, pero en "
                f"{nombre_rapido} lo hace {veces:.1f} veces más rápido ({ritmo(a)} en {nombre_a}, "
                f"{ritmo(b)} en {nombre_b}).")
    if firme_a or firme_b:
        firme, nombre_firme, nombre_otro = (a, nombre_a, nombre_b) if firme_a else (b, nombre_b, nombre_a)
        return (f"Tendencia en un solo lugar: {rumbo(firme)} en {nombre_firme} ({ritmo(firme)}), mientras "
                f"que en {nombre_otro} no hay evidencia suficiente de una tendencia.")
    return "Ninguno de los dos lugares muestra evidencia firme de una tendencia."
