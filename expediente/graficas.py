"""Gráficas del expediente (Plotly). Un solo eje por gráfica; el color significa dirección."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import estadistica as est
from .caso import Interrogatorio, numero, valor_p

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TENUE = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"
# Rojo = sube, azul = baja. El tono claro marca lo que no alcanza significancia.
ROJO, ROJO_CLARO = "#e34948", "#f3b3b2"
AZUL, AZUL_CLARO = "#2a78d6", "#9ec5f4"
DIVERGENTE = [[0, "#184f95"], [0.25, "#6da7ec"], [0.5, "#f0efec"], [0.75, "#ee8f8e"], [1, "#b12b2b"]]
FUENTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


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
    fig.update_xaxes(automargin=True, showgrid=False, linecolor=EJE, ticks="outside", tickcolor=EJE,
                     tickfont=dict(color=TENUE), title_font=dict(color=TINTA_2), title_standoff=10)
    fig.update_yaxes(automargin=True, gridcolor=REJILLA, zeroline=False, showline=False,
                     tickfont=dict(color=TENUE), title_font=dict(color=TINTA_2), title_standoff=10)
    return fig


def sospechosos(tabla: pd.DataFrame) -> go.Figure:
    """Barras horizontales: la tendencia de cada variable en una escala común."""
    datos = tabla.dropna(subset=["estandarizada"]).iloc[::-1]  # la más fuerte queda arriba
    fig = go.Figure()
    grupos = [
        ("Sube · significativa", True, True, ROJO),
        ("Sube · no significativa", True, False, ROJO_CLARO),
        ("Baja · significativa", False, True, AZUL),
        ("Baja · no significativa", False, False, AZUL_CLARO),
    ]
    for nombre, sube, significativa, color in grupos:
        g = datos[((datos["estandarizada"] > 0) == sube) & (datos["significativa"] == significativa)]
        detalle = [
            f"{numero(f.pendiente_decada, signo=True)} {f.unidad} por década<br>"
            f"{valor_p(f.p_ajustada)} (ajustado por revisar {len(datos)} variables)"
            for f in g.itertuples()
        ]
        fig.add_bar(
            name=nombre, y=g["nombre"], x=g["estandarizada"], orientation="h", width=0.62,
            marker=dict(color=color, cornerradius=4),
            text=[f"{x:+.2f}" for x in g["estandarizada"]] if significativa else None,
            textposition="outside", textfont=dict(color=TINTA_2, size=12), cliponaxis=False,
            customdata=detalle,
            hovertemplate="<b>%{y}</b><br>%{customdata}<br>En escala común: %{x:+.2f}<extra></extra>",
        )
    tope = float(datos["estandarizada"].abs().max()) * 1.18 if len(datos) else 1.0
    _base(fig, alto=26 * len(datos) + 110)
    fig.update_layout(barmode="overlay", legend_traceorder="normal")
    fig.update_xaxes(
        range=[-tope, tope], zeroline=True, zerolinecolor=EJE, zerolinewidth=1, showline=False,
        title_text="Tendencia por década, medida en variaciones típicas de un año a otro",
    )
    fig.update_yaxes(showgrid=False, categoryorder="array", categoryarray=list(datos["nombre"]),
                     tickfont=dict(color=TINTA_2), ticks="")
    return fig


def serie_original(r: Interrogatorio) -> go.Figure:
    """La serie mensual tal como llega, con su vaivén de estaciones."""
    fig = go.Figure()
    fig.add_scatter(
        x=r.serie.index, y=r.serie, mode="lines", line=dict(color=AZUL, width=1.5),
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
                    name="Rango creíble de la tendencia (95 %)", legendrank=4)
    if mensual:
        fig.add_scatter(x=x, y=r.anomalias, mode="lines", name="Cada mes", legendrank=1,
                        line=dict(color=EJE, width=1),
                        hovertemplate="%{x|%b %Y}: %{y:+.2f} " + u + "<extra></extra>")
        suave = r.anomalias.rolling(12, center=True).mean()
        fig.add_scatter(x=x, y=suave, mode="lines", name="Promedio de 12 meses", legendrank=2,
                        line=dict(color=AZUL, width=2),
                        hovertemplate="12 meses alrededor de %{x|%b %Y}: %{y:+.2f} " + u + "<extra></extra>")
    else:
        fig.add_scatter(x=x, y=r.anual, mode="lines+markers", name="Promedio de cada año", legendrank=2,
                        line=dict(color=AZUL, width=2),
                        marker=dict(size=8, color=AZUL, line=dict(color=SUPERFICIE, width=2)),
                        hovertemplate="%{x}: %{y:.2f} " + u + "<extra></extra>")
    fig.add_scatter(x=x, y=recta, mode="lines", name="Tendencia", legendrank=3,
                    line=dict(color=TINTA, width=2), hoverinfo="skip")

    _base(fig, alto=380)
    fig.update_layout(legend_traceorder="normal")
    if mensual:
        fig.add_hline(y=0, line_color=EJE, line_width=1)
        fig.update_yaxes(title_text=f"Diferencia con lo normal del mes ({u})")
    else:
        fig.update_yaxes(title_text=u)
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
                    name="Periodo con tendencia significativa")
    _base(fig, alto=440)
    fig.update_layout(showlegend=True)
    fig.update_xaxes(title_text="Año en que se empieza a contar", ticks="", showline=False)
    fig.update_yaxes(title_text="Año en que se termina", showgrid=False)
    return fig


def mapa(tabla: pd.DataFrame, unidad: str, lugar_lat: float, lugar_lon: float) -> go.Figure:
    """Mapa de la región: el color de cada celda es su tendencia; el punto marca las significativas."""
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
    tope = float(tabla["pendiente_decada"].abs().max()) or 1.0
    estado = np.where(tabla["significativa"], "significativa", "no significativa")

    fig = go.Figure()
    fig.add_choroplethmap(
        geojson={"type": "FeatureCollection", "features": celdas}, locations=list(range(len(tabla))),
        z=tabla["pendiente_decada"], colorscale=DIVERGENTE, zmin=-tope, zmax=tope,
        marker=dict(opacity=0.78, line=dict(width=0.5, color=SUPERFICIE)), customdata=estado,
        colorbar=dict(title=dict(text=f"{unidad}<br>por década", font=dict(color=TINTA_2)),
                      thickness=12, outlinewidth=0, tickfont=dict(color=TENUE)),
        hovertemplate="%{z:+.3g} " + unidad + " por década<br>%{customdata}<extra></extra>",
    )
    firmes = tabla[tabla["significativa"]]
    fig.add_scattermap(lat=firmes["lat"], lon=firmes["lon"], mode="markers", hoverinfo="skip",
                       marker=dict(size=4, color=TINTA, opacity=0.6),
                       name="Celda con tendencia significativa")
    fig.add_scattermap(lat=[lugar_lat], lon=[lugar_lon], mode="markers", hoverinfo="skip",
                       marker=dict(size=14, color=SUPERFICIE), showlegend=False)
    fig.add_scattermap(lat=[lugar_lat], lon=[lugar_lon], mode="markers", hoverinfo="skip",
                       marker=dict(size=9, color=TINTA), name="El lugar del caso")
    _base(fig, alto=480)
    # Acercamiento para que el recuadro completo quepa a lo alto (el mapa se estira hacia los polos).
    alto_grados = (lats.max() - lats.min() + alto_celda) / np.cos(np.radians(float(lats.mean())))
    fig.update_layout(
        map=dict(style="carto-positron", center=dict(lat=float(lats.mean()), lon=float(lons.mean())),
                 zoom=float(np.log2(360 * 440 / (512 * 1.15 * alto_grados)))),
        margin=dict(l=0, r=0, t=36, b=0),
    )
    return fig
