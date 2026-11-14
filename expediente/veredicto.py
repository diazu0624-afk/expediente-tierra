"""Redacta el veredicto a partir de los números del interrogatorio.

Todo el texto sale de plantillas: ninguna cifra se inventa ni se redondea distinto de
como se calculó.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .caso import NIVELES, N_PRUEBAS, Interrogatorio, numero, valor_p

ADVERTENCIAS_GENERALES = (
    "Los datos describen un cuadro de unos 50 km de lado alrededor del punto, no el punto exacto.",
    "Las variables de MERRA-2 combinan un modelo con observaciones, y los cambios de instrumentos a "
    "lo largo de las décadas pueden dejar huella en algunas series. Las de GPM, MODIS y GRACE son "
    "observaciones de satélite, con registros más cortos.",
    "Una tendencia significativa dice que algo está cambiando, no por qué cambia.",
)


@dataclass(frozen=True)
class Veredicto:
    titular: str
    cuanto: str
    evidencia: str
    espera: str  # vacío si no aplica
    advertencias: tuple[str, ...]


def _titular(r: Interrogatorio) -> str:
    rumbo = "en aumento" if r.sube else "en descenso"
    nombre = r.variable.nombre
    if r.nivel == "solida":
        return f"{nombre}: {rumbo}, con evidencia sólida"
    if r.nivel == "fuerte":
        return f"{nombre}: {rumbo}, con evidencia fuerte"
    if r.nivel == "indicios":
        return f"{nombre}: hay indicios de que va {rumbo}, pero no pruebas"
    return f"{nombre}: sin evidencia suficiente de una tendencia"


def _cuanto(r: Interrogatorio) -> str:
    u = r.variable.unidad
    bajo, alto = r.ic_decada
    rango = f"de {numero(bajo, signo=True)} a {numero(alto, signo=True)}"
    if r.nivel == "sin":
        return (f"La mejor estimación es {numero(r.pendiente_decada, signo=True)} {u} por década, "
                f"pero el rango creíble ({rango}) no permite distinguirla de «sin cambio».")
    texto = (f"Cambia {numero(r.pendiente_decada, signo=True)} {u} por década "
             f"(rango creíble al 95 %: {rango}). En los {r.anios_de_datos:.0f} años analizados "
             f"eso suma {numero(r.cambio_total, signo=True)} {u}")
    if r.cambio_relativo is not None:
        texto += f", cerca de {r.cambio_relativo:+.0f} % de su valor promedio"
    return texto + "."


def _evidencia(r: Interrogatorio) -> str:
    texto = f"Superó {r.aprobadas} de {N_PRUEBAS} pruebas."
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
        return ("Si el cambio real fuera del tamaño estimado, es tan pequeño frente al ruido de "
                "este lugar que harían falta más de 500 años de datos para detectarlo.")
    return (f"Si el cambio real fuera del tamaño estimado, se necesitarían unos "
            f"{r.anios_necesarios:.0f} años de datos para distinguirlo del ruido de este lugar. "
            f"Hay {tenemos:.0f}: faltarían unos {r.anios_necesarios - tenemos:.0f}.")


def redactar(r: Interrogatorio) -> Veredicto:
    advertencias = ((r.variable.aviso,) if r.variable.aviso else ()) + ADVERTENCIAS_GENERALES
    return Veredicto(_titular(r), _cuanto(r), _evidencia(r), _espera(r), advertencias)


def expediente_markdown(r: Interrogatorio, lugar: str, lat: float, lon: float) -> str:
    """El expediente completo como texto, para guardar o compartir."""
    v = redactar(r)
    inicio, fin = r.serie.index.min(), r.serie.index.max()
    lineas = [
        f"# Expediente Tierra: {r.variable.nombre} en {lugar}",
        "",
        f"**Veredicto: {v.titular}** ({NIVELES[r.nivel].lower()})",
        "",
        "## Qué se investigó",
        f"{r.variable.nombre} ({r.variable.unidad}). {r.variable.definicion}",
        f"Fuente: {r.variable.fuente}.",
        "",
        "## Dónde y cuándo",
        f"{lugar} (latitud {lat:.2f}, longitud {lon:.2f}), de {inicio:%m/%Y} a {fin:%m/%Y}.",
        "",
        "## Cuánto cambia",
        v.cuanto,
        "",
        "## Qué tan sólida es la evidencia",
        v.evidencia,
        "",
        "| Prueba | Pregunta | Resultado | ¿Pasa? |",
        "|---|---|---|---|",
    ]
    lineas += [f"| {p.nombre} | {p.pregunta} | {p.resultado} | {'Sí' if p.aprobada else 'No'} |"
               for p in r.pruebas]
    lineas += ["", f"Sin corregir la memoria de la serie, Mann-Kendall daba {valor_p(r.mk_ingenuo.p)}."]
    if v.espera:
        lineas += ["", "## Cuánto habría que esperar", v.espera]
    lineas += ["", "## Límites de este expediente"] + [f"- {a}" for a in v.advertencias]
    return "\n".join(lineas) + "\n"
