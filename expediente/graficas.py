"""Gráficas (Plotly). Un solo eje por gráfica; el color significa signo de la tendencia."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import estadistica as est
import textwrap

from .caso import MESES, Interrogatorio, numero, valor_p

FRACCION_LOESS = 0.5  # parte de los datos que entra a cada regresión local de la curva suavizada
from .variables import POR_CODIGO

SUPERFICIE = "#ffffff"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TENUE = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"
# Rojo = sube, azul = baja. El tono claro marca lo que no alcanza significancia.
ROJO, ROJO_CLARO = "#e34948", "#f3b3b2"
AZUL, AZUL_CLARO = "#2a78d6", "#9ec5f4"
DIVERGENTE = [[0, "#184f95"], [0.25, "#6da7ec"], [0.5, "#f0efec"], [0.75, "#ee8f8e"], [1, "#b12b2b"]]
# Identidad de los dos lugares de una comparación (no significan signo).
LUGAR_A, LUGAR_B = "#2a78d6", "#eb6834"
# Tipografía web de la NASA: Public Sans para texto, DM Mono para cifras.
FUENTE = '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif'
FUENTE_CIFRAS = '"DM Mono", ui-monospace, Menlo, monospace'


def _base(fig: go.Figure, alto: int) -> go.Figure:
    fig.update_layout(
        template="none",
        height=alto,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font=dict(family=FUENTE, size=13, color=TINTA_2),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=EJE, font=dict(family=FUENTE, size=13, color=TINTA)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(color=TINTA_2), bgcolor="rgba(0,0,0,0)"),
    )
    cifras = dict(family=FUENTE_CIFRAS, size=11, color=TENUE)
    fig.update_xaxes(automargin=True, showgrid=False, linecolor=EJE, ticks="outside", tickcolor=EJE,
                     tickfont=cifras, title_font=dict(color=TINTA_2, size=12), title_standoff=10)
    fig.update_yaxes(automargin=True, gridcolor=REJILLA, zeroline=False, showline=False,
                     tickfont=cifras, title_font=dict(color=TINTA_2, size=12), title_standoff=10)
    return fig


def exploracion(tabla: pd.DataFrame) -> go.Figure:
    """Barras horizontales: la tendencia estandarizada de cada variable.

    Al pasar el cursor por una barra aparece la definición corta de la variable.
    """
    datos = tabla.dropna(subset=["estandarizada"]).iloc[::-1]  # la más fuerte queda arriba
    # Las variables con registro más corto que el resto lo llevan en la etiqueta: una
    # tendencia de 19 años no se compara de igual a igual con una de 46.
    datos = datos.assign(etiqueta=[f"{f.nombre}  <span style='color:{TENUE}'>n = {f.anios}</span>"
                                   for f in datos.itertuples()])
    fig = go.Figure()
    grupos = [
        ("Positiva · significativa", True, True, ROJO),
        ("Positiva · no significativa", True, False, ROJO_CLARO),
        ("Negativa · significativa", False, True, AZUL),
        ("Negativa · no significativa", False, False, AZUL_CLARO),
    ]
    for nombre, sube, significativa, color in grupos:
        g = datos[((datos["estandarizada"] > 0) == sube) & (datos["significativa"] == significativa)]
        detalle = [
            "<i>" + "<br>".join(textwrap.wrap(POR_CODIGO[f.codigo].definicion, 62)) + "</i><br><br>"
            f"{numero(f.pendiente_decada, signo=True)} {f.unidad} por década<br>"
            f"Tamaño de muestra: n = {f.anios} años<br>"
            f"{valor_p(f.p_ajustada)} (ajustado por comparar {len(datos)} variables)"
            for f in g.itertuples()
        ]
        fig.add_bar(
            name=nombre, y=g["etiqueta"], x=g["estandarizada"], orientation="h", width=0.62,
            marker=dict(color=color, cornerradius=4),
            text=[f"{x:+.2f}" for x in g["estandarizada"]] if significativa else None,
            textposition="outside", textfont=dict(color=TINTA_2, size=11, family=FUENTE_CIFRAS), cliponaxis=False,
            customdata=np.column_stack([g["nombre"], detalle]) if len(g) else None,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Tendencia estandarizada: %{x:+.2f}<extra></extra>",
        )
    tope = float(datos["estandarizada"].abs().max()) * 1.18 if len(datos) else 1.0
    _base(fig, alto=26 * len(datos) + 110)
    fig.update_layout(barmode="overlay", legend_traceorder="normal")
    fig.update_xaxes(
        range=[-tope, tope], zeroline=True, zerolinecolor=EJE, zerolinewidth=1, showline=False,
        title_text="Tendencia estandarizada (desviaciones estándar interanuales por década)",
    )
    fig.update_yaxes(showgrid=False, categoryorder="array", categoryarray=list(datos["etiqueta"]),
                     tickfont=dict(color=TINTA_2, family=FUENTE, size=12.5), ticks="")
    return fig


def serie_original(r: Interrogatorio) -> go.Figure:
    """La serie mensual tal como llega, con su vaivén de estaciones."""
    fig = go.Figure()
    fig.add_scatter(
        x=r.serie.index, y=r.serie, line=dict(color=AZUL, width=1.5),
        # Con solo algunos meses del año, una línea uniría temporadas que no son contiguas.
        mode="markers" if r.por_temporada else "lines", marker=dict(size=5, color=AZUL),
        hovertemplate="%{x|%b %Y}: %{y:.2f} " + r.variable.unidad + "<extra></extra>",
    )
    _base(fig, alto=300)
    fig.update_layout(showlegend=False, margin_t=12)
    fig.update_yaxes(title_text=r.variable.unidad)
    return fig


def _recta_y_rango(r: Interrogatorio) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """La recta de tendencia y el abanico de pendientes creíbles, girando en el centro del periodo."""
    centro = r.t.mean()
    altura = r.regresion.intercepto + r.regresion.pendiente * centro
    recta = altura + r.regresion.pendiente * (r.t - centro)
    bajo, alto = r.ic_historias
    return recta, altura + bajo * (r.t - centro), altura + alto * (r.t - centro)


def tendencia(r: Interrogatorio) -> go.Figure:
    """La serie interrogada con su recta de tendencia y el rango creíble de la pendiente."""
    u = r.variable.unidad
    mensual = r.resolucion == "mensual"
    x = r.anomalias.index if mensual else r.anual.index
    recta, borde_a, borde_b = _recta_y_rango(r)
    fig = go.Figure()

    fig.add_scatter(x=x, y=np.minimum(borde_a, borde_b), mode="lines", line=dict(width=0),
                    hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=x, y=np.maximum(borde_a, borde_b), mode="lines", line=dict(width=0),
                    fill="tonexty", fillcolor="rgba(11,11,11,0.10)", hoverinfo="skip",
                    name="Intervalo de confianza del 95 %", legendrank=4)
    if mensual:
        fig.add_scatter(x=x, y=r.anomalias, mode="lines", name="Anomalía mensual", legendrank=1,
                        line=dict(color=EJE, width=1),
                        hovertemplate="%{x|%b %Y}: %{y:+.2f} " + u + "<extra></extra>")
        suave = r.anomalias.rolling(12, center=True).mean()
        fig.add_scatter(x=x, y=suave, mode="lines", name="Media móvil de 12 meses", legendrank=2,
                        line=dict(color=AZUL, width=2),
                        hovertemplate="12 meses alrededor de %{x|%b %Y}: %{y:+.2f} " + u + "<extra></extra>")
    else:
        fig.add_scatter(x=x, y=r.anual, mode="lines+markers", legendrank=2,
                        name=(f"Promedio de {r.temporada}" if r.por_temporada
                              else "Valor de cada año" if r.variable.anual else "Promedio anual"),
                        line=dict(color=AZUL, width=2),
                        marker=dict(size=8, color=AZUL, line=dict(color=SUPERFICIE, width=2)),
                        hovertemplate="%{x}: %{y:.2f} " + u + "<extra></extra>")
    fig.add_scatter(x=x, y=recta, mode="lines", name="Tendencia lineal", legendrank=3,
                    line=dict(color=TINTA, width=2), hoverinfo="skip")
    fig.add_scatter(x=x, y=est.loess(r.t, r.y, FRACCION_LOESS), mode="lines", legendrank=5,
                    name="Curva suavizada (LOESS)", line=dict(color=TINTA, width=1.6, dash="dot"),
                    hovertemplate="Curva suavizada: %{y:+.2f} " + u + "<extra></extra>")

    _base(fig, alto=380)
    fig.update_layout(legend_traceorder="normal")
    if mensual:
        fig.add_hline(y=0, line_color=EJE, line_width=1)
        fig.update_yaxes(title_text=f"Anomalía respecto a la climatología ({u})")
    else:
        fig.update_yaxes(title_text=f"Promedio de {r.temporada} ({u})" if r.por_temporada else u)
    return fig


def por_mes(tabla: pd.DataFrame, unidad: str) -> go.Figure:
    """Tendencia de cada mes del año por separado, con su intervalo de confianza del 95 %."""
    datos = tabla.dropna(subset=["pendiente_decada"])
    fig = go.Figure()
    grupos = [
        ("Positiva · significativa", True, True, ROJO),
        ("Positiva · no significativa", True, False, ROJO_CLARO),
        ("Negativa · significativa", False, True, AZUL),
        ("Negativa · no significativa", False, False, AZUL_CLARO),
    ]
    for nombre, sube, significativa, color in grupos:
        g = datos[((datos["pendiente_decada"] > 0) == sube) & (datos["significativa"] == significativa)]
        detalle = [f"IC 95 %: de {numero(f.ic_bajo, signo=True)} a {numero(f.ic_alto, signo=True)}<br>"
                   f"{valor_p(f.p_ajustada)} (ajustado por comparar 12 meses)<br>n = {f.n} años"
                   for f in g.itertuples()]
        fig.add_bar(
            name=nombre, x=g["mes"], y=g["pendiente_decada"], width=0.62,
            marker=dict(color=color, cornerradius=4),
            error_y=dict(type="data", symmetric=False, array=g["ic_alto"] - g["pendiente_decada"],
                         arrayminus=g["pendiente_decada"] - g["ic_bajo"], color=TINTA_2, thickness=1.2, width=4),
            customdata=np.column_stack([[MESES[m - 1].capitalize() for m in g["mes"]], detalle]) if len(g) else None,
            hovertemplate="<b>%{customdata[0]}</b>: %{y:+.3g} " + unidad + " por década<br>%{customdata[1]}<extra></extra>",
        )
    _base(fig, alto=340)
    fig.update_layout(barmode="overlay", legend_traceorder="normal")
    fig.add_hline(y=0, line_color=EJE, line_width=1)
    fig.update_xaxes(tickmode="array", tickvals=list(range(1, 13)), range=[0.4, 12.6], ticks="",
                     ticktext=[m[:3] for m in MESES], tickfont=dict(family=FUENTE, size=12.5, color=TINTA_2))
    fig.update_yaxes(title_text=f"Tendencia ({unidad} por década)")
    return fig


def triangulo(r: Interrogatorio) -> go.Figure:
    """Tendencia para cada par (año inicial, año final): ¿depende de las fechas elegidas?"""
    u = r.variable.unidad
    tri = r.triangulo.assign(decada=r.triangulo["pendiente"] * 10)
    z = tri.pivot(index="fin", columns="inicio", values="decada")
    p = tri.pivot(index="fin", columns="inicio", values="p")
    tope = float(np.nanmax(np.abs(z.to_numpy()))) or 1.0
    texto = np.where(p.to_numpy() < est.ALFA, "significativa", "no significativa")

    fig = go.Figure()
    fig.add_heatmap(
        z=z.to_numpy(), x=z.columns, y=z.index, colorscale=DIVERGENTE, zmin=-tope, zmax=tope,
        xgap=1, ygap=1, customdata=texto, hoverongaps=False,
        colorbar=dict(title=dict(text=f"{u}<br>por década", font=dict(color=TINTA_2)),
                      thickness=12, outlinewidth=0, tickfont=dict(color=TENUE)),
        hovertemplate="De %{x} a %{y}: %{z:+.3g} " + u + " por década<br>%{customdata}<extra></extra>",
    )
    firmes = tri[tri["p"] < est.ALFA]
    fig.add_scatter(x=firmes["inicio"], y=firmes["fin"], mode="markers", hoverinfo="skip",
                    marker=dict(size=3, color=TINTA, opacity=0.55),
                    name="Periodo con tendencia significativa (p < 0.05)")
    _base(fig, alto=440)
    fig.update_layout(showlegend=True)
    fig.update_xaxes(title_text="Año inicial del periodo", ticks="", showline=False)
    fig.update_yaxes(title_text="Año final del periodo", showgrid=False)
    return fig


def mapa(tabla: pd.DataFrame, unidad: str, lugar_lat: float, lugar_lon: float,
         tope: float | None = None, alejar: float = 0.0,
         celda: tuple[float, float] | None = None) -> go.Figure:
    """Mapa de la región: el color de cada celda es su tendencia; el punto marca las significativas.

    `tope` fija el extremo de la escala de color (para comparar dos mapas con la misma
    vara) y `alejar` reduce el acercamiento cuando el mapa se dibuja en una columna angosta.
    `celda` (latitud, longitud) rodea con un anillo la celda cuya serie se analiza.
    """
    lats, lons = np.sort(tabla["lat"].unique()), np.sort(tabla["lon"].unique())
    alto_celda = float(np.diff(lats).min()) if lats.size > 1 else 0.5
    ancho_celda = float(np.diff(lons).min()) if lons.size > 1 else 0.625
    celdas = [{
        "type": "Feature", "id": i,
        "geometry": {"type": "Polygon", "coordinates": [[
            [f.lon - ancho_celda / 2, f.lat - alto_celda / 2], [f.lon + ancho_celda / 2, f.lat - alto_celda / 2],
            [f.lon + ancho_celda / 2, f.lat + alto_celda / 2], [f.lon - ancho_celda / 2, f.lat + alto_celda / 2],
            [f.lon - ancho_celda / 2, f.lat - alto_celda / 2]]]},
    } for i, f in enumerate(tabla.itertuples())]
    tope = tope or float(tabla["pendiente_decada"].abs().max()) or 1.0
    estado = np.where(tabla["significativa"], "significativa", "no significativa")
    estado = np.column_stack([estado, tabla["anios"] if "anios" in tabla else np.full(len(tabla), "—")])

    fig = go.Figure()
    fig.add_choroplethmap(
        geojson={"type": "FeatureCollection", "features": celdas}, locations=list(range(len(tabla))),
        z=tabla["pendiente_decada"], colorscale=DIVERGENTE, zmin=-tope, zmax=tope,
        marker=dict(opacity=0.78, line=dict(width=0.5, color=SUPERFICIE)), customdata=estado,
        colorbar=dict(title=dict(text=f"{unidad}<br>por década", font=dict(color=TINTA_2)),
                      thickness=12, outlinewidth=0, tickfont=dict(color=TENUE)),
        hovertemplate="%{z:+.3g} " + unidad + " por década<br>%{customdata[0]}<br>n = %{customdata[1]} años<extra></extra>",
    )
    firmes = tabla[tabla["significativa"]]
    fig.add_scattermap(lat=firmes["lat"], lon=firmes["lon"], mode="markers", hoverinfo="skip",
                       marker=dict(size=4, color=TINTA, opacity=0.6),
                       name="Celda con tendencia significativa")
    fig.add_scattermap(lat=[lugar_lat], lon=[lugar_lon], mode="markers", hoverinfo="skip",
                       marker=dict(size=14, color=SUPERFICIE), showlegend=False)
    fig.add_scattermap(lat=[lugar_lat], lon=[lugar_lon], mode="markers", hoverinfo="skip",
                       marker=dict(size=9, color=TINTA), name="Sitio de estudio")
    if celda is not None:
        for tamano, color, visible in ((22, TINTA, True), (16, SUPERFICIE, False)):
            fig.add_scattermap(lat=[celda[0]], lon=[celda[1]], mode="markers", hoverinfo="skip",
                               marker=dict(size=tamano, color=color, opacity=1 if visible else 0.85),
                               name="Celda analizada", showlegend=visible)
    _base(fig, alto=480)
    # Acercamiento para que el recuadro completo quepa a lo alto (el mapa se estira hacia los polos).
    alto_grados = (lats.max() - lats.min() + alto_celda) / np.cos(np.radians(float(lats.mean())))
    fig.update_layout(
        map=dict(style="carto-positron", center=dict(lat=float(lats.mean()), lon=float(lons.mean())),
                 zoom=float(np.log2(360 * 440 / (512 * 1.15 * alto_grados))) - alejar),
        margin=dict(l=0, r=0, t=36, b=0),
    )
    return fig


def _para_comparar(r: Interrogatorio) -> tuple[pd.Index, pd.Series, np.ndarray]:
    """Fechas, serie suavizada y recta de tendencia, todo como anomalía."""
    if r.resolucion == "mensual":
        return (r.anomalias.index, r.anomalias.rolling(12, center=True).mean(),
                r.regresion.intercepto + r.regresion.pendiente * r.t)
    fechas = pd.to_datetime([f"{anio}-07-01" for anio in r.anual.index])
    normal = float(r.anual.mean())
    return fechas, r.anual - normal, r.regresion.intercepto + r.regresion.pendiente * r.t - normal


def comparacion(a: Interrogatorio, b: Interrogatorio, nombre_a: str, nombre_b: str) -> go.Figure:
    """La misma variable en dos lugares, sobre un mismo eje: curva suavizada y recta de tendencia."""
    u = a.variable.unidad
    fig = go.Figure()
    for r, nombre, color in ((a, nombre_a, LUGAR_A), (b, nombre_b, LUGAR_B)):
        fechas, suave, recta = _para_comparar(r)
        fig.add_scatter(x=fechas, y=suave, mode="lines", name=nombre, legendgroup=nombre,
                        line=dict(color=color, width=1.5), opacity=0.55,
                        hovertemplate=nombre + ", %{x|%b %Y}: %{y:+.3g} " + u + "<extra></extra>")
        fig.add_scatter(x=fechas, y=recta, mode="lines", legendgroup=nombre, showlegend=False,
                        line=dict(color=color, width=2.5), hoverinfo="skip")
        fig.add_annotation(x=fechas[-1], y=float(recta[-1]), xanchor="left", xshift=8, showarrow=False,
                           text=f"{numero(r.pendiente_decada, signo=True)}<br>por década",
                           font=dict(color=TINTA_2, size=11, family=FUENTE_CIFRAS), align="left")
    _base(fig, alto=400)
    fig.add_hline(y=0, line_color=EJE, line_width=1)
    fig.update_layout(margin_r=90, legend_traceorder="normal")
    fig.update_yaxes(title_text=f"Anomalía respecto a la climatología de cada lugar ({u})")
    return fig
