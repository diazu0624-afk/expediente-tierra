"""Informe descargable en HTML: portada, resultado, gráficas, ficha técnica y referencias.

Es un solo archivo sin dependencias de JavaScript: las gráficas van dibujadas en SVG
dentro del propio documento, así que se abre en cualquier navegador y se imprime o se
guarda como PDF tal cual.
"""

from __future__ import annotations

import datetime as dt
from html import escape
from math import ceil, cos, floor, log10, radians

import numpy as np
import pandas as pd

from . import estadistica as est
from . import veredicto
from .caso import NIVELES, NIVELES_CORTOS, N_PRUEBAS, Interrogatorio, numero, valor_p
from .variables import METODOS, REFERENCIAS

TINTA, TINTA_2, TENUE, REJILLA, EJE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
AZUL = "#2a78d6"
# Escala divergente: azul (baja) – gris (sin cambio) – rojo (sube).
ESCALA = [(0.0, (24, 79, 149)), (0.25, (109, 167, 236)), (0.5, (240, 239, 236)),
          (0.75, (238, 143, 142)), (1.0, (177, 43, 43))]


def _color(valor: float, tope: float) -> str:
    """Color de la escala divergente para un valor entre -tope y +tope."""
    x = min(max((valor / tope + 1) / 2, 0.0), 1.0) if tope else 0.5
    for (x0, c0), (x1, c1) in zip(ESCALA, ESCALA[1:]):
        if x <= x1:
            f = (x - x0) / (x1 - x0)
            return "#" + "".join(f"{round(a + f * (b - a)):02x}" for a, b in zip(c0, c1))
    return "#b12b2b"


def _marcas(minimo: float, maximo: float, cuantas: int = 5) -> list[float]:
    """Marcas "redondas" para un eje (1, 2 o 5 por una potencia de diez)."""
    if maximo <= minimo:
        return [minimo]
    bruto = (maximo - minimo) / cuantas
    base = 10 ** floor(log10(bruto))
    paso = next(m * base for m in (1, 2, 5, 10) if m * base >= bruto)
    return [k * paso for k in range(ceil(minimo / paso), floor(maximo / paso) + 1)]


def _texto_de_marca(valor: float, paso: float) -> str:
    decimales = max(0, -floor(log10(paso))) if paso < 1 else 0
    return f"{valor:.{decimales}f}".replace("-", "−")


def _svg_serie(r: Interrogatorio) -> str:
    """Serie analizada con su recta de tendencia y el intervalo de confianza de la pendiente."""
    ancho, alto, izq, der, arriba, abajo = 720, 300, 56, 14, 12, 30
    t, y = r.t, r.y
    centro = t.mean()
    altura = r.regresion.intercepto + r.regresion.pendiente * centro
    recta = altura + r.regresion.pendiente * (t - centro)
    borde_a = altura + r.ic_historias[0] * (t - centro)
    borde_b = altura + r.ic_historias[1] * (t - centro)
    y_min, y_max = float(min(y.min(), borde_a.min(), borde_b.min())), float(max(y.max(), borde_a.max(), borde_b.max()))
    margen = 0.05 * (y_max - y_min or 1)
    y_min, y_max = y_min - margen, y_max + margen
    t_min, t_max = float(t.min()), float(t.max())

    def px(tiempo: float) -> float:
        return izq + (tiempo - t_min) / (t_max - t_min or 1) * (ancho - izq - der)

    def py(valor: float) -> float:
        return arriba + (y_max - valor) / (y_max - y_min) * (alto - arriba - abajo)

    def trazo(tiempos, valores) -> str:
        return " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in zip(tiempos, valores) if np.isfinite(b))

    partes = [f'<svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="Serie de tiempo con tendencia" '
              f'xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto">']
    marcas_y = _marcas(y_min, y_max)
    paso_y = marcas_y[1] - marcas_y[0] if len(marcas_y) > 1 else 1
    for m in marcas_y:
        partes.append(f'<line x1="{izq}" x2="{ancho - der}" y1="{py(m):.1f}" y2="{py(m):.1f}" stroke="{REJILLA}"/>')
        partes.append(f'<text x="{izq - 8}" y="{py(m) + 4:.1f}" text-anchor="end" class="eje">{_texto_de_marca(m, paso_y)}</text>')
    for anio in _marcas(t_min, t_max, 8):
        partes.append(f'<line x1="{px(anio):.1f}" x2="{px(anio):.1f}" y1="{alto - abajo}" y2="{alto - abajo + 4}" stroke="{EJE}"/>')
        partes.append(f'<text x="{px(anio):.1f}" y="{alto - abajo + 18}" text-anchor="middle" class="eje">{anio:.0f}</text>')
    partes.append(f'<line x1="{izq}" x2="{ancho - der}" y1="{alto - abajo}" y2="{alto - abajo}" stroke="{EJE}"/>')
    if r.resolucion == "mensual" and y_min < 0 < y_max:
        partes.append(f'<line x1="{izq}" x2="{ancho - der}" y1="{py(0):.1f}" y2="{py(0):.1f}" stroke="{EJE}"/>')
    banda = trazo(t, np.maximum(borde_a, borde_b)) + " " + trazo(t[::-1], np.minimum(borde_a, borde_b)[::-1])
    partes.append(f'<polygon points="{banda}" fill="{TINTA}" fill-opacity="0.10"/>')
    # Las líneas se cortan en los huecos largos (más de tres datos faltantes seguidos), para no
    # unir sus dos extremos; un mes suelto que falta no interrumpe la línea.
    pasos = np.diff(t)
    cortes = np.flatnonzero(pasos > 3.5 * np.median(pasos)) + 1
    tramos = np.split(np.arange(t.size), cortes)

    def linea(valores: np.ndarray, color: str, grosor: float) -> None:
        for indices in tramos:
            visibles = [k for k in indices if np.isfinite(valores[k])]
            if len(visibles) > 1:
                partes.append(f'<polyline points="{trazo(t[visibles], valores[visibles])}" fill="none" '
                              f'stroke="{color}" stroke-width="{grosor}" stroke-linejoin="round"/>')

    if r.resolucion == "mensual":
        linea(y, EJE, 1)
        linea(pd.Series(y).rolling(12, center=True, min_periods=6).mean().to_numpy(), AZUL, 2)
    else:
        linea(y, AZUL, 2)
        partes += [f'<circle cx="{px(a):.1f}" cy="{py(b):.1f}" r="4" fill="{AZUL}" stroke="#fff" stroke-width="2"/>' for a, b in zip(t, y)]
    partes.append(f'<polyline points="{trazo(t, recta)}" fill="none" stroke="{TINTA}" stroke-width="2"/>')
    return "".join(partes) + "</svg>"


def _svg_mapa(mapa: pd.DataFrame, lat_sitio: float, lon_sitio: float) -> str:
    """Mapa de tendencia por celda: color = tasa de cambio; punto = tendencia significativa."""
    lats, lons = np.sort(mapa["lat"].unique()), np.sort(mapa["lon"].unique())
    d_lat = float(np.diff(lats).min()) if lats.size > 1 else 0.5
    d_lon = float(np.diff(lons).min()) if lons.size > 1 else 0.625
    lat0, lat1 = lats.min() - d_lat / 2, lats.max() + d_lat / 2
    lon0, lon1 = lons.min() - d_lon / 2, lons.max() + d_lon / 2
    izq, arriba, abajo, der = 44, 8, 26, 8
    ancho_util = 380
    # Un grado de longitud mide menos que uno de latitud lejos del ecuador.
    escala = ancho_util / ((lon1 - lon0) * cos(radians(float(lats.mean()))))
    alto_util = (lat1 - lat0) * escala
    ancho, alto = izq + ancho_util + der, arriba + alto_util + abajo
    tope = float(mapa["pendiente_decada"].abs().max()) or 1.0

    def px(lon: float) -> float:
        return izq + (lon - lon0) / (lon1 - lon0) * ancho_util

    def py(lat: float) -> float:
        return arriba + (lat1 - lat) * escala

    partes = [f'<svg viewBox="0 0 {ancho:.0f} {alto:.0f}" role="img" aria-label="Mapa de tendencias por celda" '
              f'xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto">',
              f'<rect x="{izq}" y="{arriba}" width="{ancho_util}" height="{alto_util:.1f}" fill="#f4f4f2"/>']
    w, h = d_lon / (lon1 - lon0) * ancho_util, d_lat * escala
    for f in mapa.itertuples():
        partes.append(f'<rect x="{px(f.lon - d_lon / 2) + 0.5:.1f}" y="{py(f.lat + d_lat / 2) + 0.5:.1f}" '
                      f'width="{w - 1:.1f}" height="{h - 1:.1f}" fill="{_color(f.pendiente_decada, tope)}"/>')
        if f.significativa:
            partes.append(f'<circle cx="{px(f.lon):.1f}" cy="{py(f.lat):.1f}" r="{max(min(w, h) / 9, 1.1):.1f}" fill="{TINTA}" fill-opacity="0.6"/>')
    if lon0 <= lon_sitio <= lon1 and lat0 <= lat_sitio <= lat1:
        partes.append(f'<circle cx="{px(lon_sitio):.1f}" cy="{py(lat_sitio):.1f}" r="6" fill="#fff"/>'
                      f'<circle cx="{px(lon_sitio):.1f}" cy="{py(lat_sitio):.1f}" r="4" fill="{TINTA}"/>')
    for lat in (lat0, lat1):
        partes.append(f'<text x="{izq - 6}" y="{py(lat) + (10 if lat == lat1 else 0):.1f}" text-anchor="end" class="eje">{lat:g}°</text>')
    for lon, ancla in ((lon0, "start"), (lon1, "end")):
        partes.append(f'<text x="{px(lon):.1f}" y="{arriba + alto_util + 16:.1f}" text-anchor="{ancla}" class="eje">{lon:g}°</text>')
    return "".join(partes) + "</svg>"


def _escala_de_color(tope: float, unidad: str) -> str:
    degradado = ", ".join(f"rgb{c} {100 * x:.0f}%" for x, c in ESCALA)
    return (f'<div class="escala"><span>{escape(numero(-tope, signo=True))}</span>'
            f'<div style="background:linear-gradient(to right, {degradado})"></div>'
            f'<span>{escape(numero(tope, signo=True))}</span></div>'
            f'<p class="nota">Tasa de cambio en {escape(unidad)} por década. Azul: disminuye. Rojo: aumenta. '
            f'El punto oscuro marca las celdas con tendencia significativa; el círculo, el sitio de estudio.</p>')


def _tabla(filas: list[tuple[str, str]], encabezado: tuple[str, str] | None = None) -> str:
    cabeza = f"<thead><tr><th>{escape(encabezado[0])}</th><th>{escape(encabezado[1])}</th></tr></thead>" if encabezado else ""
    cuerpo = "".join(f"<tr><th>{escape(a)}</th><td>{escape(b)}</td></tr>" for a, b in filas)
    return f"<table>{cabeza}<tbody>{cuerpo}</tbody></table>"


def _referencia(clave: str) -> str:
    referencia = REFERENCIAS[clave]
    return f'<li>{escape(referencia.cita)} <a href="{escape(referencia.url)}">{escape(referencia.url)}</a></li>'


ESTILO = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@600;700;800&family=Public+Sans:wght@400;600;700&display=swap');
:root { --tinta:#0b0b0b; --tinta2:#52514e; --filete:#d9d8d2; }
* { box-sizing: border-box; }
@page { size: letter; margin: 20mm 18mm; }
body { margin: 0; color: var(--tinta); background: #fff; font: 400 10.5pt/1.5 'Public Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }
main { max-width: 46rem; margin: 0 auto; padding: 0 1.25rem 3rem; }
h1, h2, h3 { font-family: 'Inter', system-ui, sans-serif; letter-spacing: -0.02em; margin: 0; }
.mono, .etiqueta, .eje, th.n { font-family: 'DM Mono', ui-monospace, Menlo, monospace; }
.etiqueta { font-size: 7.5pt; letter-spacing: .1em; text-transform: uppercase; color: var(--tinta2); }
.portada { min-height: 100vh; display: flex; flex-direction: column; justify-content: space-between; padding: 3rem 0 2.5rem;
  page-break-after: always; break-after: page; }
.portada h1 { font-weight: 800; font-size: 34pt; line-height: 1.04; letter-spacing: -0.035em; margin: .6rem 0 .8rem; }
.portada .sub { font-size: 14pt; line-height: 1.35; max-width: 34rem; }
.portada dl { display: grid; grid-template-columns: 11rem 1fr; gap: .45rem 1rem; margin: 0; padding-top: 1rem; border-top: 2px solid var(--tinta); }
.portada dt { font: 400 7.5pt/1.6 'DM Mono', monospace; letter-spacing: .1em; text-transform: uppercase; color: var(--tinta2); padding-top: .15rem; }
.portada dd { margin: 0; }
section { margin-top: 2rem; }
section > h2 { font-weight: 700; font-size: 15pt; border-top: 2px solid var(--tinta); padding-top: .6rem; margin-bottom: .8rem;
  display: flex; gap: .8rem; align-items: baseline; break-after: avoid; }
section > h2 .n { font: 400 8pt 'DM Mono', monospace; color: var(--tinta2); letter-spacing: 0; }
h3 { font-weight: 700; font-size: 11pt; margin: 1.1rem 0 .35rem; break-after: avoid; }
p { margin: 0 0 .6rem; }
.titular { font: 700 17pt/1.2 'Inter', sans-serif; letter-spacing: -0.02em; margin: .25rem 0 1rem; }
.cifras { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 0 0 1.1rem; break-inside: avoid; }
.cifras > div { border-top: 1px solid var(--tinta); padding-top: .45rem; }
.cifras .v { font: 500 19pt/1.15 'DM Mono', monospace; letter-spacing: -0.04em; margin-top: .2rem; white-space: nowrap; }
.cifras .u { font-size: 8.5pt; color: var(--tinta2); }
table { width: 100%; border-collapse: collapse; margin: .3rem 0 .9rem; font-size: 9.5pt; break-inside: avoid; }
th, td { text-align: left; vertical-align: top; padding: .38rem .6rem .38rem 0; border-bottom: 1px solid var(--filete); }
thead th { font: 400 7.5pt 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; color: var(--tinta2); border-bottom: 1px solid var(--tinta); }
tbody th { font-weight: 600; width: 13rem; }
td.estado { white-space: nowrap; font-weight: 600; }
.aviso { border-left: 3px solid var(--tinta); padding: .5rem .8rem; margin: .8rem 0; background: #f4f4f2; break-inside: avoid; }
figure { margin: .6rem 0 1rem; break-inside: avoid; }
figcaption, .nota { font-size: 8.5pt; line-height: 1.45; color: var(--tinta2); margin-top: .4rem; }
.leyenda { display: flex; flex-wrap: wrap; gap: .3rem 1.1rem; font-size: 8.5pt; color: var(--tinta2); margin-bottom: .3rem; }
.leyenda i { display: inline-block; width: 18px; height: 0; border-top: 2px solid; vertical-align: middle; margin-right: .35rem; }
.leyenda i.banda { height: 9px; border: 0; background: rgba(11,11,11,.10); }
.eje { font-size: 9px; fill: #898781; }
.mapa { max-width: 26rem; }
.escala { display: flex; align-items: center; gap: .5rem; max-width: 26rem; font: 400 8pt 'DM Mono', monospace; color: var(--tinta2); }
.escala div { flex: 1; height: 9px; }
ul, ol { margin: .2rem 0 .8rem; padding-left: 1.2rem; }
li { margin-bottom: .3rem; }
ol.referencias { font-size: 8.8pt; line-height: 1.45; }
ol.referencias li { break-inside: avoid; }
a { color: #0b3d91; word-break: break-all; }
footer { margin-top: 2.5rem; padding-top: .6rem; border-top: 1px solid var(--filete); font-size: 8pt; color: var(--tinta2); }
@media print { main { max-width: none; padding: 0; } .portada { min-height: 0; height: 235mm; padding: 0; } a { color: var(--tinta); } }
"""


def informe_html(
    r: Interrogatorio,
    sitio: str,
    lat: float,
    lon: float,
    mapa: pd.DataFrame | None = None,
    region: str = "",
    contraste: tuple[str, str | None] | None = None,
    hipotesis: str = "",
    fecha_datos: dt.date | None = None,
) -> str:
    """Informe completo de un análisis, listo para abrir en el navegador o imprimir.

    `mapa` es la tabla de tendencias por celda (opcional) y `region` la descripción de su
    recuadro; `contraste` es (texto, clave de referencia) con lo que dice la literatura.
    """
    v = r.variable
    res = veredicto.redactar(r)
    inicio, fin = r.serie.index.min(), r.serie.index.max()
    hoy = dt.date.today()
    numero_de_seccion = iter(range(1, 20))

    def seccion(titulo: str) -> str:
        return f'<section><h2><span class="n">{next(numero_de_seccion):02d}</span>{escape(titulo)}</h2>'

    cuerpo = [
        '<div class="portada"><div>',
        '<div class="etiqueta">NASA Space Apps 2026 · Earth System Trend Detective</div>',
        '<div class="etiqueta" style="color:var(--tinta);margin-top:.3rem">Equipo C15H25N3O · Expediente Tierra</div>',
        '<h1>Informe de análisis de tendencia</h1>',
        f'<p class="sub">{escape(v.nombre)} en {escape(sitio)}</p></div>',
        '<dl>',
        f'<dt>Variable</dt><dd>{escape(v.nombre)} ({escape(v.unidad)})</dd>',
        f'<dt>Sitio de estudio</dt><dd>{escape(sitio)}<br>Latitud {lat:.2f}°, longitud {lon:.2f}°</dd>',
        f'<dt>Periodo analizado</dt><dd>{inicio:%m/%Y} a {fin:%m/%Y} ({r.anios_de_datos:.0f} años de datos mensuales)</dd>',
        f'<dt>Fuente de datos</dt><dd>{escape(v.fuente)}</dd>',
        f'<dt>Resultado</dt><dd><strong>{escape(res.titular)}</strong></dd>',
        f'<dt>Fecha del informe</dt><dd>{hoy:%d/%m/%Y}'
        + (f" · datos descargados el {fecha_datos:%d/%m/%Y}" if fecha_datos else "") + '</dd>',
        '</dl></div>',
    ]

    # ---- Resumen
    u = v.unidad
    cuerpo += [
        seccion("Resumen"),
        f'<div class="etiqueta">{escape(NIVELES[r.nivel])}</div><p class="titular">{escape(res.titular)}</p>',
        '<div class="cifras">',
        f'<div><div class="etiqueta">Tasa de cambio</div><div class="v">{escape(numero(r.pendiente_decada, signo=True))}</div><div class="u">{escape(u)} por década</div></div>',
        f'<div><div class="etiqueta">Cambio acumulado</div><div class="v">{escape(numero(r.cambio_total, signo=True))}</div><div class="u">{escape(u)} en {r.anios_de_datos:.0f} años</div></div>',
        f'<div><div class="etiqueta">Pruebas superadas</div><div class="v">{r.aprobadas}/{N_PRUEBAS}</div><div class="u">pruebas de significancia</div></div>',
        f'<div><div class="etiqueta">Nivel de evidencia</div><div class="v">{escape(NIVELES_CORTOS[r.nivel])}</div><div class="u">&nbsp;</div></div>',
        '</div>',
        f'<p><strong>Tasa de cambio.</strong> {escape(res.cuanto)}</p>',
        f'<p><strong>Significancia estadística.</strong> {escape(res.evidencia)}</p>',
    ]
    if res.relevancia:
        cuerpo.append(f'<p><strong>Relevancia práctica.</strong> {escape(res.relevancia)}</p>')
    if res.espera:
        cuerpo.append(f'<p><strong>Años de datos necesarios.</strong> {escape(res.espera)}</p>')
    if hipotesis:
        cuerpo.append(f'<p><strong>Hipótesis inicial.</strong> {escape(hipotesis)}</p>')
    if res.no_lineal:
        cuerpo.append(f'<div class="aviso"><strong>Tendencia no lineal.</strong> {escape(res.no_lineal)}</div>')
    if res.registro_corto:
        cuerpo.append(f'<div class="aviso"><strong>Registro corto.</strong> {escape(res.registro_corto)}</div>')
    cuerpo.append("</section>")

    # ---- Variable
    cuerpo += [
        seccion("Variable analizada"),
        f'<p><strong>En pocas palabras.</strong> {escape(v.definicion)}</p>',
        f'<p><strong>Definición técnica.</strong> {escape(v.tecnica)}</p>',
        f'<p><strong>Relevancia para el sistema Tierra.</strong> {escape(v.relevancia)}</p>',
        _tabla([("Nombre original", v.nombre_original), ("Código", v.codigo), ("Unidad", v.unidad),
                ("Producto de datos", v.producto), ("Acceso", v.fuente), ("Resolución espacial", v.resolucion)]),
    ]
    if v.aviso:
        cuerpo.append(f'<p><strong>Advertencia sobre los datos.</strong> {escape(v.aviso)}</p>')
    cuerpo.append("</section>")

    # ---- Serie de tiempo
    if r.resolucion == "mensual":
        leyenda = (f'<span><i style="border-color:{EJE};border-top-width:1px"></i>Anomalía mensual</span>'
                   f'<span><i style="border-color:{AZUL}"></i>Media móvil de 12 meses</span>')
        pie = (f"Anomalías de la variable «{escape(v.nombre)}», en {escape(u)}: a cada mes se le restó su climatología "
               f"(el promedio de ese mes del año) para eliminar el ciclo estacional.")
    else:
        leyenda = f'<span><i style="border-color:{AZUL}"></i>Promedio anual</span>'
        pie = (f"Promedios anuales de la variable «{escape(v.nombre)}», en {escape(u)}. Esta variable solo toma valores "
               f"parte del año, por lo que se analiza por año.")
    cuerpo += [
        seccion("Serie de tiempo"),
        f'<figure><div class="leyenda">{leyenda}<span><i style="border-color:{TINTA}"></i>Tendencia lineal</span>'
        f'<span><i class="banda"></i>Intervalo de confianza del 95 %</span></div>',
        _svg_serie(r),
        f'<figcaption>{pie} La recta es la regresión lineal por mínimos cuadrados y la banda, el intervalo de '
        f'confianza del 95 % de su pendiente.</figcaption></figure>',
    ]
    cambio = veredicto.cambio_de_comportamiento(r)
    if cambio:
        cuerpo.append(f'<p><strong>Cambio de comportamiento.</strong> {escape(cambio)}</p>')
    cuerpo.append("</section>")

    # ---- Pruebas
    filas = "".join(
        f'<tr><th>{escape(p.nombre)}</th><td>{escape(p.pregunta)}<br><span style="color:var(--tinta2)">{escape(p.resultado)}</span></td>'
        f'<td class="estado">{"Pasa" if p.aprobada else "No pasa"}</td></tr>' for p in r.pruebas)
    cuerpo += [
        seccion("Pruebas de significancia"),
        f'<p>Cada prueba da un valor p: la probabilidad de observar una tendencia al menos tan marcada como esta si en '
        f'realidad no hubiera ninguna. Una prueba se supera si p es menor que el nivel de significancia α = {est.ALFA}.</p>',
        f'<table><thead><tr><th>Prueba</th><th>Pregunta y resultado</th><th>Estado</th></tr></thead><tbody>{filas}</tbody></table>',
        f'<p class="nota">Sin corregir la autocorrelación, la prueba de Mann-Kendall daba {escape(valor_p(r.mk_ingenuo.p))}; '
        f'corregida, {escape(valor_p(r.mk.prueba.p))}.</p></section>',
    ]

    # ---- Distribución espacial
    if mapa is not None and not mapa.empty:
        firmes = mapa[mapa["significativa"]]
        sube = 100 * (firmes["pendiente_decada"] > 0).sum() / len(mapa)
        baja = 100 * (firmes["pendiente_decada"] < 0).sum() / len(mapa)
        cuerpo += [
            seccion("Distribución espacial"),
            f'<p>{escape(region)} La tendencia es positiva y significativa en {sube:.0f} % de las {len(mapa)} celdas con '
            f'datos, y negativa y significativa en {baja:.0f} %.</p>',
            f'<figure><div class="mapa">{_svg_mapa(mapa, lat, lon)}</div>',
            _escala_de_color(float(mapa["pendiente_decada"].abs().max()) or 1.0, u),
            '<figcaption>Tendencia de cada celda calculada con sus promedios anuales. La significancia se ajustó con '
            'el procedimiento de Benjamini-Hochberg por comparaciones múltiples. Las zonas sin color no tienen '
            'datos de esta variable.</figcaption></figure></section>',
        ]

    # ---- Ficha técnica
    cuerpo += [
        seccion("Ficha técnica"),
        _tabla(veredicto.ficha_tecnica(r), ("Característica", "Detalle")),
        "<h3>Supuestos del análisis</h3><ul>" + "".join(f"<li>{escape(x)}</li>" for x in veredicto.SUPUESTOS) + "</ul>",
        "<h3>Limitaciones</h3><ul>" + "".join(f"<li>{escape(x)}</li>" for x in res.advertencias) + "</ul></section>",
    ]

    # ---- Contraste con la literatura
    claves = list(v.referencias)
    if contraste:
        texto, clave = contraste
        cuerpo += [seccion("Contraste con la literatura"), f"<p>{escape(texto)}</p></section>"]
        if clave:
            claves.append(clave)

    # ---- Método
    cuerpo += [
        seccion("Método"),
        "<p>La serie mensual se descarga de la fuente indicada y se le resta la climatología de cada mes para eliminar "
        "el ciclo estacional. La tasa de cambio es la pendiente de una regresión lineal por mínimos cuadrados; su "
        "intervalo de confianza del 95 % se obtiene por bootstrap de 2,000 series que conservan la variabilidad y la "
        "autocorrelación de la serie original.</p>"
        "<p>La significancia se evalúa con cinco pruebas: Mann-Kendall con preblanqueo iterativo (Zhang et al., 2000; "
        "Wang y Swail, 2001), prueba t de la pendiente con tamaño de muestra efectivo (Santer et al., 2000), intervalo "
        "de confianza por bootstrap, persistencia con promedios anuales y sensibilidad al periodo. El nivel de "
        "evidencia es sólido con cinco pruebas superadas, fuerte con cuatro, débil con dos o tres e insuficiente con "
        "menos. Esta escala es un criterio del equipo; en una simulación con series sin tendencia produjo evidencia "
        "fuerte o sólida en 3 a 4 de cada 100 casos.</p></section>",
    ]

    # ---- Referencias
    cuerpo += [
        seccion("Referencias"),
        "<h3>Datos</h3><ol class='referencias'>" + "".join(_referencia(c) for c in claves) + "</ol>",
        "<h3>Métodos estadísticos</h3><ol class='referencias'>" + "".join(_referencia(c) for c in METODOS) + "</ol></section>",
        f'<footer>Informe generado el {hoy:%d/%m/%Y} con Expediente Tierra, herramienta del equipo C15H25N3O para el '
        f'NASA Space Apps Challenge 2026. Los datos pertenecen a sus fuentes originales; este informe no es un '
        f'producto oficial de la NASA.</footer>',
    ]

    titulo = f"Informe de tendencia: {v.nombre} en {sitio}"
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escape(titulo)}</title><style>{ESTILO}</style></head><body><main>'
            + "".join(cuerpo) + "</main></body></html>")
