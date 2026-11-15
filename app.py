"""Expediente Tierra: detección de tendencias en variables del sistema Tierra.

Para correrla:  .venv/bin/streamlit run app.py
"""

from __future__ import annotations

import datetime as dt
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as componentes

from expediente import caso, datos, datos_gee, graficas, idioma, informe, laboratorio, region, sitio as sitios, veredicto
from expediente.fuentes import fuente_de
from expediente.idioma import T, tr
from expediente.variables import (CATALOGO, CATEGORIAS, METODOS, PAREJAS, POR_CODIGO, REFERENCIAS, SOLO_MAR, Variable,
                                  independencia)

RAIZ = Path(__file__).parent
st.set_page_config(page_title="Expediente Tierra", page_icon=str(RAIZ / "static" / "favicon.png"),
                   layout="wide")

# Idioma de la sesión. Streamlit vuelve a ejecutar este archivo completo en cada interacción, así
# que basta fijarlo aquí para que todos los textos de abajo, incluidas las constantes, salgan en
# el idioma elegido. El selector se dibuja al final, junto con la navegación.
if "idioma" not in st.session_state:
    st.session_state["idioma"] = "en" if st.query_params.get("lang", "es").lower().startswith("en") else "es"
idioma.fijar(st.session_state["idioma"])

EJEMPLOS = [
    {"nombre": T("Monterrey, México", "Monterrey, Mexico"), "lat": 25.68, "lon": -100.32,
     "pregunta": T("Monterrey vivió una crisis de agua en 2022. ¿Disminuyó la precipitación? "
                   "Compara la precipitación con el almacenamiento de agua terrestre (GRACE).",
                   "Monterrey went through a water crisis in 2022. Did precipitation decrease? "
                   "Compare precipitation with terrestrial water storage (GRACE).")},
    {"nombre": T("Nueva Delhi, India", "New Delhi, India"), "lat": 28.61, "lon": 77.21,
     "pregunta": T("Alrededor de Delhi se riega una de las zonas agrícolas más grandes del mundo. "
                   "¿El índice de vegetación y el almacenamiento de agua tienen la misma tendencia?",
                   "One of the largest farming areas in the world is irrigated around Delhi. "
                   "Do the vegetation index and water storage have the same trend?")},
    {"nombre": T("Pekín, China", "Beijing, China"), "lat": 39.90, "lon": 116.40,
     "pregunta": T("Pekín y Delhi crecieron quemando carbón. ¿El espesor óptico de aerosoles "
                   "tiene la misma tendencia en las dos ciudades?",
                   "Beijing and Delhi grew by burning coal. Does aerosol optical depth have the "
                   "same trend in the two cities?")},
    {"nombre": T("Longyearbyen, Svalbard (Ártico)", "Longyearbyen, Svalbard (Arctic)"), "lat": 78.22, "lon": 15.65,
     "pregunta": T("Es el poblado más septentrional del mundo. ¿El Ártico se calienta más "
                   "rápido que latitudes medias como la de Monterrey?",
                   "It is the northernmost town in the world. Is the Arctic warming faster than "
                   "mid-latitudes such as Monterrey's?")},
    {"nombre": T("Niamey, Níger (Sahel)", "Niamey, Niger (Sahel)"), "lat": 13.51, "lon": 2.11,
     "pregunta": T("El Sahel sufrió sequías severas en los años ochenta. ¿Se recuperó? El mapa "
                   "del índice de vegetación muestra tendencias distintas dentro de la región.",
                   "The Sahel suffered severe droughts in the 1980s. Did it recover? The map of the "
                   "vegetation index shows different trends within the region.")},
    {"nombre": T("Manaos, Brasil (Amazonía)", "Manaus, Brazil (Amazon)"), "lat": -3.10, "lon": -60.02,
     "pregunta": T("En el centro de la selva más grande del planeta. ¿Está cambiando la "
                   "precipitación? Compara el reanálisis con la observación del satélite GPM.",
                   "At the centre of the largest rainforest on the planet. Is precipitation "
                   "changing? Compare the reanalysis with the GPM satellite observation.")},
    {"nombre": T("Golfo de México (océano)", "Gulf of Mexico (ocean)"), "lat": 25.0, "lon": -90.0,
     "pregunta": T("El Golfo de México alimenta a los huracanes que llegan a México y Estados "
                   "Unidos. ¿Se está calentando el mar? ¿Cambia la clorofila, base de su vida marina?",
                   "The Gulf of Mexico feeds the hurricanes that reach Mexico and the United States. "
                   "Is the sea warming? Is chlorophyll, the base of its marine life, changing?")},
]

# Comparaciones sugeridas: (título, índice del ejemplo A, índice del B, variable, pregunta).
COMPARACIONES = [
    (T("Delhi y Pekín: espesor óptico de aerosoles", "Delhi and Beijing: aerosol optical depth"), 1, 2, "AOD_55",
     T("Dos capitales que crecieron quemando carbón. ¿Su carga de aerosoles tiene la misma tendencia?",
       "Two capitals that grew by burning coal. Does their aerosol load have the same trend?")),
    (T("Monterrey y el Ártico: temperatura del aire", "Monterrey and the Arctic: air temperature"), 0, 3, "T2M",
     T("El planeta se calienta, pero ¿con la misma tasa en todas las latitudes?",
       "The planet is warming, but at the same rate at all latitudes?")),
    (T("Delhi y el Sahel: almacenamiento de agua terrestre", "Delhi and the Sahel: terrestrial water storage"), 1, 4, "GRACE_AGUA",
     T("Dos regiones semiáridas densamente pobladas. ¿Cómo cambia su reserva de agua?",
       "Two densely populated semi-arid regions. How is their water reserve changing?")),
    (T("Pekín y Monterrey: precipitación (satélite GPM)", "Beijing and Monterrey: precipitation (GPM satellite)"), 2, 0, "GPM_LLUVIA",
     T("Dos ciudades con estrés hídrico. ¿En alguna está cambiando la precipitación?",
       "Two water-stressed cities. Is precipitation changing in either of them?")),
]

# Contraste de los ejemplos con estudios publicados: (sitio, variable) -> (texto, referencia).
# Sin referencia significa que se buscó y no se encontró un estudio comparable.
_AEROSOLES = T("Ratnam et al. (2021), con el instrumento MODIS del satélite Terra (2001–2018), encontraron un "
               "aumento significativo de 0.1 AOD por década sobre India y una disminución de 0.1 AOD por "
               "década sobre el este de China. El signo coincide con este análisis. Las magnitudes no son "
               "directamente comparables: aquí se analiza un punto, otro periodo y un producto distinto.",
               "Ratnam et al. (2021), with the MODIS instrument on the Terra satellite (2001–2018), found a "
               "significant increase of 0.1 AOD per decade over India and a decrease of 0.1 AOD per decade over "
               "eastern China. The sign agrees with this analysis. The magnitudes are not directly comparable: "
               "here a point, another period and a different product are analysed.")
CONTRASTES = {
    (EJEMPLOS[1]["nombre"], "GRACE_AGUA"): (T(
        "Rodell, Velicogna y Famiglietti (2009) estimaron con GRACE una pérdida de agua subterránea de "
        "4.0 ± 1.0 cm por año (unos 40 cm por década) entre 2002 y 2008 en Rajastán, Punyab y Haryana, "
        "región que incluye Delhi. Con los datos de esta herramienta, el promedio regional (recuadro de "
        "8°) da −3.8 cm por año en ese mismo periodo: dentro del margen del artículo. Las cifras no son "
        "idénticas en definición: el artículo aísla el agua subterránea y aquí se mide el almacenamiento "
        "total de agua.",
        "Rodell, Velicogna and Famiglietti (2009) estimated with GRACE a groundwater loss of 4.0 ± 1.0 cm "
        "per year (about 40 cm per decade) between 2002 and 2008 in Rajasthan, Punjab and Haryana, a region "
        "that includes Delhi. With the data of this tool, the regional mean (8° box) gives −3.8 cm per year "
        "over that same period: within the margin of the paper. The figures are not identical by definition: "
        "the paper isolates groundwater and here total water storage is measured."), "rodell2009"),
    (EJEMPLOS[1]["nombre"], "AOD_55"): (_AEROSOLES, "ratnam2021"),
    (EJEMPLOS[2]["nombre"], "AOD_55"): (_AEROSOLES, "ratnam2021"),
    (EJEMPLOS[0]["nombre"], "GRACE_AGUA"): (T(
        "No se encontró un estudio publicado que mida con GRACE esta tendencia para Monterrey o Nuevo "
        "León. El resultado no está contrastado con la literatura y debe tomarse como exploratorio.",
        "No published study was found that measures this trend with GRACE for Monterrey or Nuevo León. The "
        "result is not checked against the literature and should be taken as exploratory."), None),
}


def contraste_con_literatura(nombre_del_sitio: str, codigo: str) -> None:
    """Muestra, para los sitios de ejemplo, qué dicen los estudios publicados sobre el mismo fenómeno."""
    contraste = CONTRASTES.get((nombre_del_sitio, codigo))
    if contraste is None:
        return
    texto, clave = contraste
    cita = f" [{REFERENCIAS[clave].cita}]({REFERENCIAS[clave].url})" if clave else ""
    st.markdown(f"**{T('Contraste con la literatura', 'Comparison with the literature')}.** {texto}{cita}")


# Inicio guiado: tema de interés -> variable que se analiza primero (la primera de la lista
# que se pueda medir en el sitio). La lista vacía deja la de mayor tendencia.
TEMAS = {
    T("Temperatura", "Temperature"): ["T2M"],
    T("Calor y lluvia extremos", "Heat and rainfall extremes"): ["EXT_DIAS_CALOR", "EXT_TXX", "EXT_RX1", "EXT_CDD"],
    T("Precipitación y agua", "Precipitation and water"): ["GRACE_AGUA", "GPM_LLUVIA", "PRECTOTCORR"],
    T("Calidad del aire", "Air quality"): ["AOD_55"],
    T("Vegetación y cultivos", "Vegetation and crops"): ["MODIS_NDVI", "GWETROOT"],
    T("Océano", "Ocean"): ["MAR_SST", "MAR_CLOROFILA", "TS"],
    T("Heladas y nieve", "Frost and snow"): ["FROST_DAYS", "SNODP", "T2M_MIN"],
    T("La variable con mayor tendencia", "The variable with the largest trend"): [],
}
HIPOTESIS = [T("Está aumentando", "It is increasing"), T("Está disminuyendo", "It is decreasing"),
             T("No está cambiando", "It is not changing")]

# Resultados de la simulación de validación (validacion/calibracion.py y validacion/veredictos.py).
VALIDACION = {
    "series": T("1,500 a 2,000", "1,500 to 2,000"),
    "clasica": "14–64 %", "clasica_baja": "14 %", "clasica_media": "33 %", "clasica_alta": "64 %",
    "metodo": "3–4 %",
    "potencia": "79–98 %", "potencia_baja": "98 %", "potencia_media": "79 %",
}
PAGINAS: dict[str, object] = {}  # se llena al final, cuando ya existen las funciones de página

ESTILOS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@500;600;700;800&family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');
:root { --tinta:#0b0b0b; --tinta2:#52514e; --tenue:#898781; --filete:#d9d8d2; }
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, [data-baseweb] {
  font-family: 'Public Sans', system-ui, -apple-system, 'Segoe UI', sans-serif; }
h1, h2, h3, h4 { font-family: 'Inter', system-ui, sans-serif !important; letter-spacing: -0.02em; }
code, .et-mono { font-family: 'DM Mono', ui-monospace, Menlo, monospace; }
.block-container { max-width: 1180px; padding-top: 4.5rem; padding-bottom: 5rem; }
.et-eyebrow { font-family: 'DM Mono', monospace; font-size: .72rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--tinta2); }
.et-equipo { color: var(--tinta); margin-top: .3rem; }
.et-nota { font-size: .97rem; line-height: 1.55; color: var(--tinta); max-width: 60rem; }
.et-titulo { font-family: 'Inter', sans-serif; font-weight: 800; color: var(--tinta);
  font-size: clamp(2.2rem, 5vw, 3.7rem); line-height: 1.02; letter-spacing: -0.035em; margin: .4rem 0 .7rem; }
.et-lead { font-size: 1.16rem; line-height: 1.5; max-width: 46rem; color: var(--tinta); margin: 0; }
.et-sec { border-top: 2px solid var(--tinta); padding-top: .7rem; margin-top: 2.4rem;
  display: flex; gap: 1rem; align-items: baseline; }
.et-sec .n { font-family: 'DM Mono', monospace; font-size: .8rem; color: var(--tinta2); }
.et-sec h2 { font-weight: 700; font-size: 1.5rem; margin: 0; padding: 0; color: var(--tinta); }
.et-resultado { font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.65rem;
  line-height: 1.18; letter-spacing: -0.02em; color: var(--tinta); margin: .2rem 0 .4rem; }
.et-paso .n { font-family: 'DM Mono', monospace; font-size: .75rem; color: var(--tinta2); }
.et-paso .t { font-family: 'Inter', sans-serif; font-weight: 700; font-size: 1.05rem; margin: .15rem 0 .3rem; }
.et-paso p { font-size: .95rem; line-height: 1.45; color: var(--tinta2); margin: 0; }
.et-paso { border-top: 1px solid var(--tinta); padding-top: .6rem; }
.et-cifra { border-top: 1px solid var(--tinta); padding-top: .55rem; }
.et-cifra .v { font-family: 'DM Mono', monospace; font-weight: 500; font-size: 2.1rem; line-height: 1.1;
  letter-spacing: -0.04em; color: var(--tinta); margin-top: .25rem; white-space: nowrap; }
.et-cifra .u { font-size: .9rem; color: var(--tinta2); margin-top: .15rem; }
.et-cifra .d { font-size: .85rem; line-height: 1.4; color: var(--tinta2); margin-top: .45rem; }
[data-testid="stCaptionContainer"] p { color: var(--tinta2); }
/* Selector de idioma: fijo en la barra superior, a la derecha de la navegación. */
.st-key-idioma { position: fixed; top: .62rem; right: 1.1rem; z-index: 999999; width: auto !important; }
.st-key-idioma button { min-height: 1.9rem; padding: .1rem .7rem; font-family: 'DM Mono', monospace; font-size: .8rem; }
</style>
"""


def encabezado(eyebrow: str, titulo: str, lead: str = "", equipo: str = "") -> None:
    # Los nombres de lugar vienen de un buscador externo: se escapan antes de insertarlos.
    parrafo = f'<p class="et-lead">{escape(lead)}</p>' if lead else ""
    autoria = f'<div class="et-eyebrow et-equipo">{escape(equipo)}</div>' if equipo else ""
    st.html(f'<div class="et-eyebrow">{escape(eyebrow)}</div>{autoria}'
            f'<div class="et-titulo">{escape(titulo)}</div>{parrafo}')


def seccion(numero: int | None, titulo: str) -> None:
    marca = f'<span class="n">{numero:02d}</span>' if numero is not None else ""
    st.html(f'<div class="et-sec">{marca}<h2>{titulo}</h2></div>')


def cifra(donde, etiqueta: str, valor: str, unidad: str = "", detalle: str = "") -> None:
    """Un dato destacado: etiqueta, cifra en tipografía monoespaciada, unidad y nota opcional."""
    extra = (f'<div class="u">{unidad}</div>' if unidad else "") + (f'<div class="d">{detalle}</div>' if detalle else "")
    donde.html(f'<div class="et-cifra"><div class="et-eyebrow">{etiqueta}</div>'
               f'<div class="v">{valor}</div>{extra}</div>')


def _parametro(nombre: str) -> str:
    """Parámetro de la URL (p. ej. /analisis?caso=2&var=AOD_55), para enlazar un análisis."""
    return st.query_params.get(nombre, "")


# ------------------------------------------------------------------ datos (con caché)

@st.cache_data(show_spinner=False)
def cargar_datos(lat: float, lon: float) -> pd.DataFrame:
    """Todas las variables en el punto: reanálisis por POWER más lo que responda Earth Engine."""
    return sitios.tabla_del_punto(lat, lon)


_CON_TEXTO: dict[str, object] = {}


@st.cache_data(show_spinner=False)
def _resultado_con_texto(nombre: str, lengua: str, *args):
    return _CON_TEXTO[nombre](*args)


def por_idioma(funcion):
    """Caché para resultados que llevan texto (nombres de pruebas, notas): el idioma entra en la clave."""
    _CON_TEXTO[funcion.__name__] = funcion

    def envoltura(*args):
        return _resultado_con_texto(funcion.__name__, idioma.actual(), *args)
    return envoltura


Periodo = tuple[int, int]  # (año inicial, año final), ambos incluidos
Meses = tuple[int, ...]  # meses del año que entran al análisis; los 12 = todo el año


def _recortar(tabla: pd.DataFrame, periodo: Periodo) -> pd.DataFrame:
    return tabla.loc[str(periodo[0]):str(periodo[1])]


@por_idioma
def cargar_exploracion(lat: float, lon: float, periodo: Periodo, meses: Meses = caso.TODO_EL_ANIO) -> pd.DataFrame:
    return caso.escanear(_recortar(cargar_datos(lat, lon), periodo), meses=meses)


@por_idioma
def cargar_analisis(lat: float, lon: float, codigo: str, periodo: Periodo,
                    meses: Meses = caso.TODO_EL_ANIO) -> caso.Interrogatorio:
    return caso.interrogar(_recortar(cargar_datos(lat, lon), periodo)[codigo], POR_CODIGO[codigo], meses)


@st.cache_data(show_spinner=False)
def cargar_region(lat: float, lon: float, codigo: str, lado: int) -> pd.DataFrame:
    variable = POR_CODIGO[codigo]
    return fuente_de(variable).cubo_de_la_region(lat, lon, variable, lado)


@st.cache_data(show_spinner=False)
def cargar_mapa(lat: float, lon: float, codigo: str, lado: int, periodo: Periodo,
                meses: Meses = caso.TODO_EL_ANIO) -> pd.DataFrame:
    return region.mapa_de_tendencias(_recortar(cargar_region(lat, lon, codigo, lado), periodo), POR_CODIGO[codigo], meses)


@por_idioma
def cargar_analisis_celda(lat: float, lon: float, codigo: str, lado: int, periodo: Periodo,
                          celda: str, meses: Meses = caso.TODO_EL_ANIO) -> caso.Interrogatorio:
    cubo = _recortar(cargar_region(lat, lon, codigo, lado), periodo)
    return caso.interrogar(cubo[celda], POR_CODIGO[codigo], meses)


@por_idioma
def cargar_analisis_regional(lat: float, lon: float, codigo: str, lado: int, periodo: Periodo,
                             meses: Meses = caso.TODO_EL_ANIO) -> caso.Interrogatorio:
    promedio = region.promedio_regional(_recortar(cargar_region(lat, lon, codigo, lado), periodo))
    return caso.interrogar(promedio, POR_CODIGO[codigo], meses)


Territorio = tuple[str, float, float, float, float] | None  # (país, lat_min, lat_max, lon_min, lon_max); None = mundo


@st.cache_data(show_spinner=False)
def cargar_pais(lat: float, lon: float) -> Territorio:
    pais = datos_gee.buscar_pais(lat, lon)
    return pais.nombre, pais.lat_min, pais.lat_max, pais.lon_min, pais.lon_max


@st.cache_data(show_spinner=False, max_entries=6)
def cargar_cubo_territorio(territorio: Territorio, codigo: str) -> pd.DataFrame:
    if territorio is None:
        return datos_gee.descargar_cubo_del_mundo(codigo)
    return datos_gee.descargar_cubo_del_pais(datos_gee.Pais(*territorio), codigo)


@st.cache_data(show_spinner=False)
def cargar_mapa_territorio(territorio: Territorio, codigo: str, periodo: Periodo, meses: Meses) -> pd.DataFrame:
    return region.mapa_de_tendencias(_recortar(cargar_cubo_territorio(territorio, codigo), periodo), POR_CODIGO[codigo], meses)


@por_idioma
def cargar_analisis_territorio(territorio: Territorio, codigo: str, periodo: Periodo, meses: Meses) -> caso.Interrogatorio:
    promedio = region.promedio_regional(_recortar(cargar_cubo_territorio(territorio, codigo), periodo))
    return caso.interrogar(promedio, POR_CODIGO[codigo], meses)


def elegir_periodo() -> Periodo | None:
    """Barra lateral: años inicial y final del análisis. None si el periodo es demasiado corto."""
    primero, ultimo = datos.ANIO_INICIAL, dt.date.today().year
    desde = int(_parametro("desde")) if _parametro("desde").isdigit() else primero
    hasta = int(_parametro("hasta")) if _parametro("hasta").isdigit() else ultimo
    barra = st.sidebar
    barra.markdown(f"**{T('Periodo de análisis', 'Analysis period')}**")
    periodo = barra.slider(T("Periodo de análisis", "Analysis period"), primero, ultimo,
                           (min(max(desde, primero), ultimo), min(max(hasta, primero), ultimo)),
                           label_visibility="collapsed")
    barra.caption(T("La tendencia depende del periodo elegido. Un periodo corto puede reflejar la "
                  "variabilidad natural de una década y no un cambio de fondo. Las variables de "
                  "satélite empiezan después de 1981 y usan los años disponibles dentro del periodo.",
                    "The trend depends on the chosen period. A short period may reflect the natural variability "
                    "of a decade and not an underlying change. Satellite variables start after 1981 and use the "
                    "years available within the period."))
    if periodo[1] - periodo[0] + 1 < caso.MIN_ANIOS:
        barra.warning(T(f"Elige al menos {caso.MIN_ANIOS} años: con menos no se puede evaluar una tendencia.",
                        f"Choose at least {caso.MIN_ANIOS} years: with fewer a trend cannot be assessed."))
        return None
    return periodo


OPCIONES_DE_MESES: dict[str, Meses | None] = {
    T("Todo el año", "The whole year"): caso.TODO_EL_ANIO,
    T("Diciembre a febrero", "December to February"): caso.TEMPORADAS["DEF"],
    T("Marzo a mayo", "March to May"): caso.TEMPORADAS["MAM"],
    T("Junio a agosto", "June to August"): caso.TEMPORADAS["JJA"],
    T("Septiembre a noviembre", "September to November"): caso.TEMPORADAS["SON"],
    T("Elegir los meses", "Choose the months"): None,
}


def elegir_meses() -> Meses:
    """Barra lateral: qué meses del año entran al análisis (todo el año, una estación o meses sueltos)."""
    barra = st.sidebar
    barra.markdown(f"**{T('Meses del año', 'Months of the year')}**")
    pedidos = caso.ordenar_meses(m for m in _parametro("meses").split(",") if m.strip().isdigit() and 1 <= int(m) <= 12)
    nombres = list(OPCIONES_DE_MESES)
    inicial = next((k for k, (_, meses) in enumerate(OPCIONES_DE_MESES.items()) if meses == pedidos), len(nombres) - 1)
    # La opción se guarda por posición para que no se pierda al cambiar de idioma.
    posicion = barra.selectbox(T("Meses del año", "Months of the year"), range(len(nombres)), index=inicial,
                               format_func=lambda k: nombres[k], label_visibility="collapsed")
    meses = OPCIONES_DE_MESES[nombres[posicion]]
    if meses is None:
        elegidos = barra.multiselect(T("Meses", "Months"), caso.TODO_EL_ANIO, default=pedidos if len(pedidos) < 12 else (6, 7, 8, 9),
                                     format_func=lambda m: caso.MESES[m - 1].capitalize(), label_visibility="collapsed")
        meses = caso.ordenar_meses(elegidos)
    barra.caption(T("Una tendencia puede concentrarse en una parte del año: la temporada de lluvias, el "
                  "invierno, un mes. Al elegir una estación o unos meses, el análisis usa un dato por "
                  "año: el promedio de esos meses.",
                    "A trend may be concentrated in one part of the year: the rainy season, the winter, one "
                    "month. When a season or some months are chosen, the analysis uses one value per year: the "
                    "mean of those months."))
    return meses


@por_idioma
def buscar(texto: str) -> list[dict]:
    return datos.buscar_lugar(texto, idioma=idioma.actual())


def _buscar_sitio(donde, etiqueta: str, clave: str) -> dict | None:
    """Campo de búsqueda por nombre y lista de coincidencias."""
    texto = donde.text_input(etiqueta, placeholder=T("Ej. Guadalajara", "E.g. Guadalajara"), key=f"texto_{clave}")
    if not texto.strip():
        return None
    try:
        lugares = buscar(texto.strip())
    except datos.ErrorDeDatos as error:
        donde.error(str(error))
        return None
    if not lugares:
        donde.warning(T("No se encontró ese lugar. Prueba con otro nombre.", "That place was not found. Try another name."))
        return None
    return donde.selectbox(T("Coincidencias", "Matches"), lugares, format_func=lambda l: l["nombre"], key=f"lista_{clave}")


def plotly(figura, clave: str | None = None) -> None:
    st.plotly_chart(figura, theme=None, width="stretch", config={"displayModeBar": False}, key=clave)


# ------------------------------------------------------------------ fichas de variables

def _tipo(v: Variable) -> str:
    return v.clase


def ficha_variable(v: Variable) -> None:
    """Definición completa de una variable: corta, técnica, producto de datos y referencias."""
    st.markdown(f"#### {v.nombre}")
    st.markdown(f"`{v.codigo}` · {tr(v.categoria)} · {_tipo(v)}")
    st.markdown(f"**{T('En pocas palabras', 'In a few words')}.** {v.definicion}")
    st.markdown(f"**{T('Definición técnica', 'Technical definition')}.** {v.tecnica}")
    st.markdown(f"**{T('Relevancia para el sistema Tierra', 'Relevance to the Earth system')}.** {v.relevancia}")
    periodo = (T(f"Desde {v.desde}, un valor por año", f"Since {v.desde}, one value per year") if v.anual
               else T(f"Desde {v.desde}, datos mensuales", f"Since {v.desde}, monthly data"))
    st.markdown(
        f"| {T('Característica', 'Feature')} | {T('Detalle', 'Detail')} |\n|---|---|\n"
        f"| {T('Nombre original', 'Original name')} | {v.nombre_original} |\n"
        f"| {T('Unidad', 'Unit')} | {v.unidad} |\n"
        f"| {T('Producto de datos', 'Data product')} | {v.producto} |\n"
        f"| {T('Acceso', 'Access')} | {v.fuente} |\n"
        f"| {T('Resolución espacial', 'Spatial resolution')} | {v.resolucion} |\n"
        f"| {T('Periodo analizado', 'Period analysed')} | {periodo} |"
    )
    if v.aviso:
        st.markdown(f"**{T('Advertencia', 'Caveat')}.** {v.aviso}")
    st.markdown(f"**{T('Referencias', 'References')}**")
    for clave in v.referencias:
        referencia = REFERENCIAS[clave]
        st.markdown(f"- {referencia.cita} [{referencia.url}]({referencia.url})")


def definicion_emergente(donde, v: Variable) -> None:
    """Definición corta de la variable, con enlace a su ficha completa."""
    with donde.popover(T("Definición de la variable", "Definition of the variable")):
        st.markdown(f"**{v.nombre}**  \n`{v.codigo}` · {v.unidad}")
        st.write(v.definicion)
        st.caption(f"{T('Fuente', 'Source')}: {v.fuente}.")
        st.page_link(PAGINAS["variables"], label=T("Definición completa y referencias", "Full definition and references"),
                     icon=":material/arrow_forward:", query_params={"var": v.codigo})


# ------------------------------------------------------------------ página: inicio

def pagina_inicio() -> None:
    encabezado(
        "NASA Space Apps 2026 · Earth System Trend Detective",
        "Expediente Tierra",
        T("Herramienta para detectar tendencias en variables terrestres.",
          "A tool to detect trends in Earth system variables."),
        equipo=T("Equipo C15H25N3O", "Team C15H25N3O"),
    )

    recorrido = RAIZ / "static" / T("demo.html", "demo_en.html")
    if recorrido.exists():
        seccion(1, T("Recorrido de la herramienta", "Tour of the tool"))
        st.caption(T("La herramienta en 75 segundos, con datos reales: de empezar un análisis a descargar el informe, "
                     "con el análisis por meses, los extremos, los países y el laboratorio. Se puede pausar, "
                     "retroceder, avanzar o saltar a cualquier escena.",
                     "The tool in 75 seconds, with real data: from starting an analysis to downloading the report, "
                     "including the analysis by month, the extremes, the countries and the laboratory. It can be "
                     "paused, rewound, advanced or jumped to any scene."))
        # La misma animación se reproduce sola cuando se abre el archivo directamente (para grabarla).
        componentes.html(recorrido.read_text(encoding="utf-8").replace("const AUTO = true;", "const AUTO = false;"),
                         height=660)

    seccion(2, T("Empezar un análisis", "Start an analysis"))
    with st.container(border=True):
        uno, dos, tres = st.columns(3)
        temas = list(TEMAS)
        # Tema, sitio e hipótesis se guardan por posición: así no se pierden al cambiar de idioma.
        tema = uno.radio(T("Tema de interés", "Topic of interest"), range(len(temas)), format_func=lambda k: temas[k])
        with dos:
            opciones = [e["nombre"] for e in EJEMPLOS] + [T("Otro lugar", "Another place")]
            elegido = st.selectbox(T("Sitio de estudio", "Study site"), range(len(opciones)), format_func=lambda k: opciones[k])
            ejemplo = elegido if elegido < len(EJEMPLOS) else None
            sitio = EJEMPLOS[ejemplo] if ejemplo is not None else _buscar_sitio(st, T("Ciudad, región o país", "City, region or country"), "inicio")
        with tres:
            hipotesis = st.radio(T("Hipótesis: ¿qué esperas encontrar?", "Hypothesis: what do you expect to find?"),
                                 range(len(HIPOTESIS)), format_func=lambda k: HIPOTESIS[k])
            st.caption(T("Plantear la hipótesis antes de ver los datos evita ajustar la "
                         "interpretación al resultado. Al final se contrasta con el análisis.",
                         "Stating the hypothesis before seeing the data avoids fitting the interpretation "
                         "to the result. At the end it is checked against the analysis."))
        if st.button(T("Iniciar el análisis", "Start the analysis"), type="primary", disabled=sitio is None):
            st.session_state["guiado"] = {"sitio": sitio, "ejemplo": ejemplo, "tema": tema, "hipotesis": hipotesis}
            st.switch_page(PAGINAS["analisis"])

    seccion(3, T("Método", "Method"))
    pasos = [
        (T("Exploración de variables", "Exploration of variables"),
         T("Se calcula la tendencia de todas las variables del sitio y se ordenan por su magnitud estandarizada.",
           "The trend of every variable at the site is computed and they are ranked by standardised magnitude.")),
        (T("Distribución espacial", "Spatial distribution"),
         T("Un mapa muestra dónde la tendencia es positiva, dónde es negativa y dónde es significativa.",
           "A map shows where the trend is positive, where it is negative and where it is significant.")),
        (T("Serie de tiempo", "Time series"),
         T("Se elimina el ciclo estacional y se aplican cinco pruebas de significancia a la tendencia.",
           "The seasonal cycle is removed and five significance tests are applied to the trend.")),
        (T("Resultado", "Result"),
         T("Tasa de cambio con su intervalo de confianza del 95 % y nivel de evidencia.",
           "Rate of change with its 95 % confidence interval and level of evidence.")),
    ]
    for k, (columna, (titulo, texto)) in enumerate(zip(st.columns(4), pasos), start=1):
        columna.html(f'<div class="et-paso"><div class="n">{T("PASO", "STEP")} {k}</div>'
                     f'<div class="t">{titulo}</div><p>{texto}</p></div>')

    seccion(4, T("Validación del método", "Validation of the method"))
    st.html(T(
        '<p class="et-nota"><b>Cómo se obtuvieron estas cifras.</b> Se generaron series sintéticas de 45 años '
        "de datos mensuales que, por construcción, no tienen ninguna tendencia, pero sí autocorrelación "
        "(cada mes se parece al anterior), como las series climáticas reales. Cualquier tendencia "
        "«significativa» detectada en ellas es, por definición, un falso positivo. Con un nivel de "
        "significancia de α = 0.05, una prueba bien calibrada debe equivocarse cerca de 5 % de las veces.</p>",
        '<p class="et-nota"><b>How these figures were obtained.</b> Synthetic series of 45 years of monthly '
        "data were generated which, by construction, have no trend at all but do have autocorrelation (each "
        "month resembles the previous one), like real climate series. Any “significant” trend detected in "
        "them is, by definition, a false positive. With a significance level of α = 0.05, a well-calibrated "
        "test should be wrong about 5 % of the time.</p>"))
    a, b, c = st.columns(3)
    cifra(a, T("Falsos positivos · prueba clásica", "False positives · classic test"), VALIDACION["clasica"], "",
          T("La prueba de Mann-Kendall estándar supone que los datos son independientes. Aplicada a "
            f"esas series, declaró una tendencia falsa en {VALIDACION['clasica_baja']} de los casos con "
            f"autocorrelación baja (0.3), {VALIDACION['clasica_media']} con autocorrelación media (0.6) y "
            f"{VALIDACION['clasica_alta']} con autocorrelación alta (0.9).",
            "The standard Mann-Kendall test assumes that the data are independent. Applied to those series, "
            f"it declared a false trend in {VALIDACION['clasica_baja']} of the cases with low autocorrelation "
            f"(0.3), {VALIDACION['clasica_media']} with medium autocorrelation (0.6) and "
            f"{VALIDACION['clasica_alta']} with high autocorrelation (0.9)."))
    cifra(b, T("Falsos positivos · este método", "False positives · this method"), VALIDACION["metodo"], "",
          T("Dos medidas reducen el error. Primero, cada prueba corrige la autocorrelación antes de "
            "evaluar la tendencia. Segundo, la evidencia solo se califica como «fuerte» o «sólida» si "
            "coinciden al menos cuatro de las cinco pruebas. Con las mismas series, el método completo "
            "dio un falso positivo en esa proporción de casos.",
            "Two measures reduce the error. First, each test corrects for autocorrelation before assessing "
            "the trend. Second, the evidence is only rated “strong” or “solid” if at least four of the five "
            "tests agree. With the same series, the full method gave a false positive in that share of cases."))
    cifra(c, T("Potencia estadística", "Statistical power"), VALIDACION["potencia"], "",
          T("Corregir no debe volver ciega a la prueba. Al añadir a las series una tendencia real y "
            f"modesta (0.2 desviaciones estándar por década), el método la detectó en {VALIDACION['potencia_baja']} "
            f"de los casos con autocorrelación baja y en {VALIDACION['potencia_media']} con autocorrelación media.",
            "Correcting must not make the test blind. When a real, modest trend (0.2 standard deviations per "
            f"decade) was added to the series, the method detected it in {VALIDACION['potencia_baja']} of the "
            f"cases with low autocorrelation and in {VALIDACION['potencia_media']} with medium autocorrelation."))
    st.caption(T(f"Simulación de Monte Carlo con {VALIDACION['series']} series por escenario. El código "
                 "está en la carpeta validacion/ del repositorio.",
                 f"Monte Carlo simulation with {VALIDACION['series']} series per scenario. The code is in the "
                 "validacion/ folder of the repository."))
    st.page_link(PAGINAS["laboratorio"], icon=":material/arrow_forward:",
                 label=T("Repetir la simulación en vivo en el laboratorio", "Repeat the simulation live in the laboratory"))

    seccion(5, T("Datos", "Data"))
    satelite = sum(v.origen == "gee" for v in CATALOGO)
    a, b, c = st.columns(3)
    extremos = sum(v.origen == "diario" for v in CATALOGO)
    cifra(a, "Variables", f"{len(CATALOGO)}",
          T(f"tierra, atmósfera y océano; {extremos} son índices de extremos con datos diarios",
            f"land, atmosphere and ocean; {extremos} are extremes indices from daily data"))
    cifra(b, T("De reanálisis", "From reanalysis"), f"{sum(v.origen == 'power' for v in CATALOGO)}",
          T("MERRA-2 y CERES, vía NASA POWER", "MERRA-2 and CERES, via NASA POWER"))
    cifra(c, T("De satélites y modelos", "From satellites and models"), f"{satelite}",
          T("GPM, MODIS, GRACE, OMI, FLDAS y OISST, vía Earth Engine", "GPM, MODIS, GRACE, OMI, FLDAS and OISST, via Earth Engine"))
    st.page_link(PAGINAS["variables"], icon=":material/arrow_forward:",
                 label=T("Definiciones y referencias de las variables", "Definitions and references of the variables"))

    seccion(6, T("Países y mundo", "Countries and world"))
    st.markdown(T("El mismo análisis para un país completo o para todo el planeta: mapa de la tendencia "
                  "recortado a la frontera y serie del promedio nacional o global, con las cinco pruebas.",
                  "The same analysis for a whole country or for the entire planet: a trend map clipped to the "
                  "border and the series of the national or global mean, with the five tests."))
    st.page_link(PAGINAS["territorio"], label=T("Analizar un país o el mundo", "Analyse a country or the world"),
                 icon=":material/arrow_forward:")

    seccion(7, T("Comparación de dos lugares", "Comparison of two places"))
    st.markdown(T("Un mismo proceso puede producir tendencias opuestas en regiones distintas. La "
                  "comparación coloca la misma variable de dos lugares sobre un mismo eje.",
                  "The same process can produce opposite trends in different regions. The comparison puts the "
                  "same variable from two places on the same axis."))
    st.page_link(PAGINAS["comparacion"], label=T("Ir a la comparación", "Go to the comparison"), icon=":material/arrow_forward:")


# ------------------------------------------------------------------ página: variables

def _referencia(clave: str) -> None:
    st.markdown(f"- {REFERENCIAS[clave].cita} [{REFERENCIAS[clave].url}]({REFERENCIAS[clave].url})")


def pagina_variables() -> None:
    satelite = sum(v.origen == "gee" for v in CATALOGO)
    de_power, de_extremos = sum(v.origen == "power" for v in CATALOGO), sum(v.origen == "diario" for v in CATALOGO)
    encabezado(
        T("Catálogo", "Catalogue"),
        "Variables",
        T(f"{len(CATALOGO)} variables de tierra, atmósfera y océano: {de_power} "
          f"mensuales de reanálisis vía NASA POWER, {satelite} de satélites y modelos vía Google Earth Engine y "
          f"{de_extremos} índices anuales de extremos calculados con datos diarios. Cada una "
          f"con su definición, el producto de datos del que proviene y sus referencias.",
          f"{len(CATALOGO)} variables of land, atmosphere and ocean: {de_power} monthly from reanalysis via NASA "
          f"POWER, {satelite} from satellites and models via Google Earth Engine and {de_extremos} annual extremes "
          f"indices computed from daily data. Each with its definition, the data product it comes from and its "
          f"references."),
    )

    consultada = POR_CODIGO.get(_parametro("var"))
    if consultada:
        seccion(None, T("Variable consultada", "Variable looked up"))
        with st.container(border=True):
            ficha_variable(consultada)
        st.page_link(PAGINAS["analisis"], label=T("Volver al análisis", "Back to the analysis"), icon=":material/arrow_back:")

    seccion(1, T("Resumen", "Summary"))
    desde = T("Desde", "Since")
    st.dataframe(
        pd.DataFrame([{"Variable": v.nombre, T("Código", "Code"): v.codigo, T("Unidad", "Unit"): v.unidad,
                       T("Tema", "Topic"): tr(v.categoria), T("Tipo", "Type"): _tipo(v), desde: v.desde,
                       T("Resolución espacial", "Spatial resolution"): v.resolucion} for v in CATALOGO]),
        hide_index=True, width="stretch", height=36 * len(CATALOGO) + 40,
        column_config={desde: st.column_config.NumberColumn(format="%d")},
    )

    for numero, categoria in enumerate(CATEGORIAS, start=2):
        seccion(numero, tr(categoria))
        for v in (v for v in CATALOGO if v.categoria == categoria):
            with st.expander(f"{v.nombre} · {v.codigo}", expanded=False):
                ficha_variable(v)

    seccion(len(CATEGORIAS) + 2, T("Referencias", "References"))
    st.markdown(f"**{T('Datos', 'Data')}**")
    usadas = list(dict.fromkeys(clave for v in CATALOGO for clave in v.referencias))
    for clave in sorted(usadas, key=lambda c: REFERENCIAS[c].cita):
        _referencia(clave)
    st.markdown(f"**{T('Estudios con los que se contrastan los ejemplos', 'Studies against which the examples are compared')}**")
    for clave in ("ratnam2021", "rodell2009"):
        _referencia(clave)
    st.markdown(f"**{T('Métodos estadísticos', 'Statistical methods')}**")
    for clave in sorted(METODOS, key=lambda c: REFERENCIAS[c].cita):
        _referencia(clave)
    st.markdown(T(
        "**Filtro de calidad.** Cada variable se evaluó en siete sitios antes de incluirla: "
        "cobertura del registro, saltos que coinciden en el mismo año en lugares distantes (señal de "
        "un cambio de instrumento y no del clima) y acuerdo con otra fuente independiente. No pasaron "
        "y quedaron fuera: nubosidad, radiación solar y albedo de CERES SYN1deg (saltos al cambiar de "
        "satélite); temperatura del suelo de MODIS Terra (escalón en 2020 en 5 de 6 sitios, compatible "
        "con la deriva de su órbita); y vapor de agua de MODIS Terra (contradice en signo al reanálisis "
        "en 4 de 7 sitios). Se incluyen con recorte: la clorofila de MODIS Aqua, solo hasta 2021 (desde "
        "2022 el satélite deriva de órbita y el promedio global salta sin causa oceánica); GRACE, solo "
        "sobre tierra firme; y los productos de color del océano, solo donde hay mar.",
        "**Quality filter.** Each variable was assessed at seven sites before being included: record "
        "coverage, jumps that coincide in the same year at distant places (a sign of an instrument change "
        "and not of climate) and agreement with another independent source. These did not pass and were left "
        "out: cloud cover, solar radiation and albedo from CERES SYN1deg (jumps when satellites change); land "
        "surface temperature from MODIS Terra (a step in 2020 at 5 of 6 sites, consistent with its orbit "
        "drift); and water vapour from MODIS Terra (it contradicts the reanalysis in sign at 4 of 7 sites). "
        "These are included with trimming: MODIS Aqua chlorophyll, only until 2021 (since 2022 the satellite "
        "has been drifting in orbit and the global mean jumps with no oceanic cause); GRACE, only over land; "
        "and ocean-colour products, only where there is sea."))


# ------------------------------------------------------------------ página: análisis de un lugar

def elegir_sitio() -> dict | None:
    """Barra lateral: sitio de estudio."""
    barra = st.sidebar
    barra.markdown(f"**{T('Sitio de estudio', 'Study site')}**")
    modos = {"ejemplos": T("Ejemplos", "Examples"), "buscar": T("Buscar un lugar", "Search for a place"),
             "coordenadas": T("Coordenadas", "Coordinates")}
    modo = barra.radio(T("Origen", "Source"), list(modos), format_func=modos.get, label_visibility="collapsed")
    if modo == "ejemplos":
        inicial = int(_parametro("caso")) if _parametro("caso").isdigit() else 0
        elegido = EJEMPLOS[barra.selectbox(T("Ejemplo", "Example"), range(len(EJEMPLOS)), index=min(inicial, len(EJEMPLOS) - 1),
                                           format_func=lambda k: EJEMPLOS[k]["nombre"])]
        barra.markdown(f"**{T('Pregunta de investigación', 'Research question')}.** {elegido['pregunta']}")
        return elegido
    if modo == "buscar":
        lugar = _buscar_sitio(barra, T("Ciudad, región o país", "City, region or country"), "analisis")
        if lugar and lugar.get("es_pais"):
            barra.caption(T(f"{lugar['nombre']} es un país. Aquí se analiza el punto de su centro; para el país "
                            f"completo, con su mapa y su promedio nacional:",
                            f"{lugar['nombre']} is a country. Here the point at its centre is analysed; for the "
                            f"whole country, with its map and its national mean:"))
            barra.page_link(PAGINAS["territorio"], icon=":material/arrow_forward:", query_params={"pais": lugar["nombre"]},
                            label=T(f"Analizar {lugar['nombre']} como país", f"Analyse {lugar['nombre']} as a country"))
        return lugar
    lat = barra.number_input(T("Latitud", "Latitude"), -90.0, 90.0, 19.43, step=0.5, format="%.2f")
    lon = barra.number_input(T("Longitud", "Longitude"), -180.0, 180.0, -99.13, step=0.5, format="%.2f")
    return {"nombre": T(f"Punto ({lat:.2f}, {lon:.2f})", f"Point ({lat:.2f}, {lon:.2f})"), "lat": lat, "lon": lon}


def paso_sitio(sitio: dict, tabla_datos: pd.DataFrame) -> None:
    seccion(1, T("Sitio de estudio", "Study site"))
    satelites = [v for v in CATALOGO if v.origen == "gee" and v.codigo in tabla_datos]
    de_power = sum(v.origen == "power" and v.codigo in tabla_datos for v in CATALOGO)
    de_extremos = sum(v.origen == "diario" and v.codigo in tabla_datos for v in CATALOGO)
    inicio, fin = tabla_datos.index.min(), tabla_datos.index.max()
    texto, mapa = st.columns([3, 2])
    texto.markdown(
        T(f"Latitud {sitio['lat']:.2f}, longitud {sitio['lon']:.2f}  \n"
          f"Datos mensuales de {inicio:%Y} a {fin:%Y}: {de_power} variables de reanálisis vía NASA POWER"
          + (f", {len(satelites)} de satélites y modelos vía Google Earth Engine" if satelites else "")
          + f" y {de_extremos} índices de extremos calculados con los datos diarios.",
          f"Latitude {sitio['lat']:.2f}, longitude {sitio['lon']:.2f}  \n"
          f"Monthly data from {inicio:%Y} to {fin:%Y}: {de_power} reanalysis variables via NASA POWER"
          + (f", {len(satelites)} from satellites and models via Google Earth Engine" if satelites else "")
          + f" and {de_extremos} extremes indices computed from daily data.")
    )
    if not satelites:
        texto.caption(T("Las variables que llegan por Google Earth Engine (GPM, MODIS, GRACE, OMI, océano) "
                        "no están disponibles: hace falta una sesión de Earth Engine en esta computadora.",
                        "The variables that come through Google Earth Engine (GPM, MODIS, GRACE, OMI, ocean) are "
                        "not available: an Earth Engine session is needed on this computer."))
    fecha = datos.fecha_de_datos(sitio["lat"], sitio["lon"], [v.codigo for v in CATALOGO if v.origen == "power"])
    texto.caption(T("Cada dato representa un área alrededor del punto, no un sitio puntual: unos 50 km "
                    "de lado en la mayoría de las variables, 100 km en aerosoles y 300 km en GRACE.",
                    "Each value represents an area around the point, not a single spot: about 50 km across for "
                    "most variables, 100 km for aerosols and 300 km for GRACE.")
                  + (T(f" Datos descargados de la fuente el {fecha:%d/%m/%Y}.",
                       f" Data downloaded from the source on {fecha:%d/%m/%Y}.") if fecha else ""))
    mapa.map(pd.DataFrame({"lat": [sitio["lat"]], "lon": [sitio["lon"]]}), zoom=3, height=220)


def _significativa(valor: bool) -> str:
    return T("significativa", "significant") if valor else T("no significativa", "not significant")


def _columnas_del_mapa(v: Variable) -> dict:
    """Encabezados de la tabla de tendencias por celda."""
    return {"lat": T("Latitud", "Latitude"), "lon": T("Longitud", "Longitude"), "anios": T("n (años)", "n (years)"),
            "pendiente_decada": st.column_config.NumberColumn(
                T(f"Cambio por década ({v.unidad})", f"Change per decade ({v.unidad})"), format="%.3g"),
            "p": st.column_config.NumberColumn("p", format="%.3f"),
            "p_ajustada": st.column_config.NumberColumn(T("p ajustada", "adjusted p"), format="%.3f"),
            "significativa": T("Significativa", "Significant")}


def paso_exploracion(exploracion: pd.DataFrame, preferidas: tuple[str, ...] = (),
                     meses: Meses = caso.TODO_EL_ANIO) -> str | None:
    seccion(2, T("Exploración de variables", "Exploration of variables"))
    validas = exploracion.dropna(subset=["estandarizada"])
    firmes = int(validas["significativa"].sum())
    temporada = (T(f", solo con los meses de {caso.nombre_de_meses(meses)}", f", using only {caso.nombre_de_meses(meses)}")
                 if len(meses) < 12 else "")
    st.markdown(T(
        f"Se calculó la tendencia de **{len(validas)} variables** en este sitio{temporada}. Para comparar "
        f"variables con unidades distintas, cada tendencia se divide entre la variabilidad "
        f"interanual de esa variable. **{firmes}** tienen una tendencia significativa en esta "
        f"primera revisión. Pasa el cursor sobre una barra para ver la definición de la variable.",
        f"The trend of **{len(validas)} variables** was computed at this site{temporada}. To compare variables "
        f"with different units, each trend is divided by the interannual variability of that variable. "
        f"**{firmes}** have a significant trend in this first screening. Hover over a bar to see the "
        f"definition of the variable."))
    clasicas = int((validas["p_clasica"] < 0.05).sum())
    with st.container(border=True):
        a, b, c = st.columns(3)
        cifra(a, T("Variables analizadas", "Variables analysed"), f"{len(validas)}", "",
              T("con datos suficientes en este sitio", "with enough data at this site"))
        cifra(b, T("Con la prueba clásica", "With the classic test"), f"{clasicas}", "",
              T("parecerían tener tendencia: Mann-Kendall sobre los datos mensuales, sin corregir la "
                "autocorrelación ni el número de comparaciones",
                "would appear to have a trend: Mann-Kendall on the monthly data, with no correction for "
                "autocorrelation or for the number of comparisons"))
        cifra(c, T("Con este método", "With this method"), f"{firmes}", "",
              T("tienen tendencia significativa: autocorrelación corregida y valores p ajustados por "
                "comparaciones múltiples",
                "have a significant trend: autocorrelation corrected and p-values adjusted for multiple "
                "comparisons"))
        if clasicas > firmes:
            st.caption(T(f"{clasicas - firmes} de las {clasicas} tendencias que señalaría la prueba clásica no "
                         f"sobreviven a las correcciones. En el laboratorio se puede comprobar con series sin "
                         f"tendencia cuántas de esas señales son falsas.",
                         f"{clasicas - firmes} of the {clasicas} trends the classic test would flag do not survive "
                         f"the corrections. In the laboratory you can check, with trend-free series, how many of "
                         f"those signals are false."))
    plotly(graficas.exploracion(exploracion))
    st.caption(T("Junto a cada variable está su tamaño de muestra (n, en años con datos completos): una "
                 "tendencia de 19 años no pesa lo mismo que una de 45. Al evaluar muchas variables a la vez "
                 "aumenta la probabilidad de falsos positivos; por eso los valores p se ajustan con el "
                 "procedimiento de Benjamini-Hochberg.",
                 "Next to each variable is its sample size (n, in years with complete data): a 19-year trend "
                 "does not carry the same weight as a 45-year one. Assessing many variables at once raises the "
                 "probability of false positives; that is why p-values are adjusted with the Benjamini-Hochberg "
                 "procedure."))
    with st.expander(T("Ver como tabla", "View as a table")):
        vista = exploracion.assign(
            tendencia=exploracion["significativa"].map(_significativa).where(exploracion["nota"] == "", "—"),
            definicion=exploracion["codigo"].map(lambda c: POR_CODIGO[c].definicion),
        )
        st.dataframe(
            vista[["nombre", "definicion", "unidad", "anios", "pendiente_decada",
                   "estandarizada", "p_ajustada", "tendencia", "nota"]],
            hide_index=True, width="stretch",
            column_config={
                "nombre": "Variable",
                "definicion": st.column_config.TextColumn(T("Definición", "Definition"), width="large"),
                "unidad": T("Unidad", "Unit"), "anios": T("n (años)", "n (years)"),
                "pendiente_decada": st.column_config.NumberColumn(T("Cambio por década", "Change per decade"), format="%.3g"),
                "estandarizada": st.column_config.NumberColumn(T("Tendencia estandarizada", "Standardised trend"), format="%+.2f"),
                "p_ajustada": st.column_config.NumberColumn(T("p ajustada", "adjusted p"), format="%.3f"),
                "tendencia": T("Tendencia", "Trend"), "nota": T("Nota", "Note"),
            },
        )
    if validas.empty:
        st.warning(T("Ninguna variable tiene datos suficientes en este punto.", "No variable has enough data at this point."))
        return None
    codigos = list(validas["codigo"])
    signo = dict(zip(validas["codigo"], validas["estandarizada"]))
    inicial = next((c for c in (*preferidas, _parametro("var")) if c in codigos), codigos[0])
    selector, definicion = st.columns([5, 2], vertical_alignment="bottom")
    codigo = selector.selectbox(
        T("Variable a analizar", "Variable to analyse"),
        codigos,
        index=codigos.index(inicial),
        key=f"variable_{inicial}_{len(codigos)}",
        format_func=lambda c: f"{POR_CODIGO[c].nombre} ({T('positiva', 'positive') if signo[c] > 0 else T('negativa', 'negative')})",
    )
    definicion_emergente(definicion, POR_CODIGO[codigo])
    return codigo


ALCANCES = ("punto", "region", "celda")  # qué serie se analiza tras ver el mapa


def paso_mapa(sitio: dict, codigo: str, periodo: Periodo,
              meses: Meses = caso.TODO_EL_ANIO) -> tuple[int, str, str | None] | None:
    """Distribución espacial de la tendencia.

    Devuelve (lado del recuadro, alcance, celda elegida) o None si no hay mapa. El alcance es
    uno de ALCANCES.
    """
    v = POR_CODIGO[codigo]
    seccion(3, T("Distribución espacial de la tendencia", "Spatial distribution of the trend"))
    if v.anual:
        st.info(T("Los índices de extremos se calculan con los datos diarios del punto. La NASA no entrega datos "
                  "diarios por región, así que esta variable no tiene mapa: el análisis corresponde al sitio de estudio.",
                  "Extremes indices are computed from the daily data of the point. NASA does not deliver daily "
                  "data by region, so this variable has no map: the analysis refers to the study site."))
        return None
    lado = st.slider(T("Tamaño de la región: lado del recuadro alrededor del sitio, en grados",
                       "Size of the region: side of the box around the site, in degrees"), 2, 10, 8, step=2,
                     help=T("Un grado equivale a unos 111 km. La NASA entrega recuadros de 2° a 10°.",
                            "One degree is about 111 km. NASA delivers boxes of 2° to 10°."))
    try:
        with st.spinner(T("Descargando los datos de la región...", "Downloading the data of the region...")):
            mapa = cargar_mapa(sitio["lat"], sitio["lon"], codigo, lado, periodo, meses)
    except datos.ErrorDeDatos as error:
        st.warning(T(f"No se pudo cargar el mapa de la región. {error}", f"The map of the region could not be loaded. {error}"))
        return None
    if mapa.empty:
        st.info(T("Esta variable no se puede medir en ninguna celda de la región.",
                  "This variable cannot be measured in any cell of the region."))
        return None
    lat_min, lat_max, lon_min, lon_max = datos.caja(sitio["lat"], sitio["lon"], lado)
    r = region.resumen(mapa)
    texto = T(f"**{v.nombre}** en {r['celdas']} celdas con datos. La tendencia es positiva y significativa "
              f"en **{r['sube']:.0f} %** de la región, y negativa y significativa en **{r['baja']:.0f} %**.",
              f"**{v.nombre}** in {r['celdas']} cells with data. The trend is positive and significant in "
              f"**{r['sube']:.0f} %** of the region, and negative and significant in **{r['baja']:.0f} %**.")
    if r["sube"] >= 5 and r["baja"] >= 5:
        texto += T(" **La misma variable presenta tendencias opuestas dentro de la región.**",
                   " **The same variable shows opposite trends within the region.**")
    st.markdown(texto)
    anios = (T(f"{r['anios_min']} años", f"{r['anios_min']} years") if r["anios_min"] == r["anios_max"]
             else T(f"entre {r['anios_min']} y {r['anios_max']} años", f"between {r['anios_min']} and {r['anios_max']} years"))
    de_meses = T(f" de {caso.nombre_de_meses(meses)}", f" for {caso.nombre_de_meses(meses)}") if len(meses) < 12 else ""
    st.caption(T(f"Recuadro de {lado}° × {lado}° (unos {lado * 111:,} km de lado): latitud {lat_min:g}° a {lat_max:g}°, "
                 f"longitud {lon_min:g}° a {lon_max:g}°. Resolución espacial de esta variable: {v.resolucion}. "
                 f"Tamaño de muestra: {r['celdas']} celdas, cada una con {anios} de datos{de_meses}.",
                 f"Box of {lado}° × {lado}° (about {lado * 111:,} km across): latitude {lat_min:g}° to {lat_max:g}°, "
                 f"longitude {lon_min:g}° to {lon_max:g}°. Spatial resolution of this variable: {v.resolucion}. "
                 f"Sample size: {r['celdas']} cells, each with {anios} of data{de_meses}."))

    nombres = {"punto": T("El punto", "The point"), "region": T("El promedio de la región", "The mean of the region"),
               "celda": T("Una celda del mapa", "One cell of the map")}
    alcance = st.radio(T("Serie que se analiza", "Series to analyse"), ALCANCES, format_func=nombres.get, horizontal=True)
    celda = None
    if alcance == "celda":
        orden = mapa.reindex(mapa["pendiente_decada"].abs().sort_values(ascending=False).index)
        etiquetas = {f"{f.lat},{f.lon}": f"{f.lat:.2f}°, {f.lon:.2f}° · {caso.numero(f.pendiente_decada, signo=True)} "
                                         f"{v.unidad} {T('por década', 'per decade')} · {_significativa(f.significativa)}"
                     for f in orden.itertuples()}
        celda = st.selectbox(T("Celda (ordenadas de mayor a menor tendencia)", "Cell (ordered from largest to smallest trend)"),
                             list(etiquetas), format_func=etiquetas.get)
    marca = tuple(float(x) for x in celda.split(",")) if celda else None
    plotly(graficas.mapa(mapa, v.unidad, sitio["lat"], sitio["lon"], celda=marca))
    st.caption(T("Rojo: tendencia positiva. Azul: negativa. El punto marca las celdas con tendencia "
                 "significativa tras el ajuste de Benjamini-Hochberg por comparaciones múltiples. Las zonas "
                 "sin color dentro del recuadro no tienen datos de esta variable (por ejemplo, variables "
                 "de suelo sobre el mar).",
                 "Red: positive trend. Blue: negative. The dot marks the cells with a significant trend after "
                 "the Benjamini-Hochberg adjustment for multiple comparisons. Uncoloured areas inside the box "
                 "have no data for this variable (for example, soil variables over the sea)."))
    with st.expander(T("Ver como tabla", "View as a table")):
        st.dataframe(mapa, hide_index=True, width="stretch", column_config=_columnas_del_mapa(v))
    return lado, alcance, celda


def _tendencia_por_mes(r: caso.Interrogatorio) -> None:
    """¿En qué meses del año ocurre el cambio? Una tendencia por cada mes del calendario."""
    u = r.variable.unidad
    tabla = caso.tendencia_por_mes(r.serie, r.variable)
    validas = tabla.dropna(subset=["pendiente_decada"])
    if validas.empty:
        st.info(T("No hay suficientes años de datos para analizar cada mes por separado.",
                  "There are not enough years of data to analyse each month separately."))
        return
    firmes = validas[validas["significativa"]]
    mayor = validas.loc[validas["pendiente_decada"].abs().idxmax()]
    if firmes.empty:
        resumen = T("Ningún mes tiene, por sí solo, una tendencia significativa.",
                    "No month has, on its own, a significant trend.")
    elif len(firmes) == len(validas):
        resumen = T(f"La tendencia es significativa en los {len(validas)} meses analizados.",
                    f"The trend is significant in all {len(validas)} months analysed.")
    else:
        resumen = T(f"La tendencia es significativa en {len(firmes)} de {len(validas)} meses: {', '.join(firmes['nombre'])}.",
                    f"The trend is significant in {len(firmes)} of {len(validas)} months: {', '.join(firmes['nombre'])}.")
    fuera = tabla[tabla["pendiente_decada"].isna()]["nombre"]
    sin_analizar = (T(f" No se analiza {', '.join(fuera)}: faltan años de datos o el valor casi nunca cambia en ese mes.",
                      f" Not analysed: {', '.join(fuera)} (too few years of data, or the value almost never changes "
                      f"in that month).") if len(fuera) else "")
    tasa = caso.numero(mayor["pendiente_decada"], signo=True)
    st.markdown(T(f"{resumen} El mayor cambio ocurre en **{mayor['nombre']}**: {tasa} {u} por década.{sin_analizar}",
                  f"{resumen} The largest change occurs in **{mayor['nombre']}**: {tasa} {u} per decade.{sin_analizar}"))
    plotly(graficas.por_mes(tabla, u))
    n_min, n_max = int(validas["n"].min()), int(validas["n"].max())
    st.caption(T(f"Cada barra es la tendencia de un mes del calendario, calculada con un dato por año "
                 f"(n = {n_min} a {n_max} años). La línea vertical es el intervalo de "
                 f"confianza del 95 %. La significancia (Mann-Kendall con preblanqueo) se ajustó con "
                 f"Benjamini-Hochberg por tratarse de 12 pruebas. Para analizar a fondo una temporada, elígela "
                 f"en «Meses del año», en la barra lateral.",
                 f"Each bar is the trend of one calendar month, computed with one value per year (n = {n_min} to "
                 f"{n_max} years). The vertical line is the 95 % confidence interval. Significance (Mann-Kendall "
                 f"with prewhitening) was adjusted with Benjamini-Hochberg because there are 12 tests. To analyse "
                 f"a season in depth, choose it under “Months of the year” in the sidebar."))
    with st.expander(T("Ver como tabla", "View as a table")):
        st.dataframe(tabla[["nombre", "n", "pendiente_decada", "ic_bajo", "ic_alto", "p_ajustada", "significativa"]],
                     hide_index=True, width="stretch", column_config={
            "nombre": T("Mes", "Month"), "n": T("n (años)", "n (years)"),
            "pendiente_decada": st.column_config.NumberColumn(T(f"Cambio por década ({u})", f"Change per decade ({u})"), format="%+.3g"),
            "ic_bajo": st.column_config.NumberColumn(T("IC 95 %, inferior", "95 % CI, lower"), format="%+.3g"),
            "ic_alto": st.column_config.NumberColumn(T("IC 95 %, superior", "95 % CI, upper"), format="%+.3g"),
            "p_ajustada": st.column_config.NumberColumn(T("p ajustada", "adjusted p"), format="%.3f"),
            "significativa": T("Significativa", "Significant")})


def paso_serie(r: caso.Interrogatorio, numero: int = 4) -> None:
    v = r.variable
    seccion(numero, T("Serie de tiempo y pruebas de significancia", "Time series and significance tests"))
    texto, definicion = st.columns([5, 2], vertical_alignment="center")
    texto.markdown(f"**{v.nombre}** ({v.unidad}). {v.definicion}  \n{T('Fuente', 'Source')}: {v.fuente}.")
    definicion_emergente(definicion, v)
    if v.aviso:
        st.caption(v.aviso)

    st.markdown(T(f"**Tamaño de muestra.** {r.muestra}. Tamaño efectivo tras descontar la "
                  f"autocorrelación: {r.regresion.n_efectivo:.0f}.",
                  f"**Sample size.** {r.muestra}. Effective size after discounting autocorrelation: "
                  f"{r.regresion.n_efectivo:.0f}."))
    original_txt = T("Serie original", "Original series")
    if v.anual:
        (con_tendencia,) = st.tabs([T("Valores anuales y tendencia", "Annual values and trend")])
        mensual = original = None
    elif r.por_temporada:
        con_tendencia, original = st.tabs([T(f"Tendencia de {r.temporada}", f"{r.temporada} trend"), original_txt])
        mensual = None
    else:
        con_tendencia, mensual, original = st.tabs([T("Anomalías y tendencia", "Anomalies and trend"),
                                                    T("Tendencia por mes del año", "Trend by month of the year"), original_txt])
    with con_tendencia:
        if r.resolucion == "mensual":
            st.caption(T("A cada mes se le restó su climatología (el promedio de ese mes del año). "
                         "Así se elimina el ciclo estacional y queda la variación de fondo.",
                         "Each month had its climatology (the mean of that month of the year) subtracted. "
                         "This removes the seasonal cycle and leaves the underlying variation."))
        elif v.anual:
            st.caption(T("Un valor por año, calculado con los datos de cada día. Solo cuentan los años con al "
                         "menos 360 días de datos, por eso el año en curso no aparece.",
                         "One value per year, computed from the data of every day. Only years with at least 360 "
                         "days of data count, which is why the current year does not appear."))
        elif r.por_temporada:
            st.caption(T(f"Un dato por año: el promedio de {r.temporada}. Solo cuentan los años que tienen "
                         f"todos esos meses.",
                         f"One value per year: the {r.temporada} mean. Only years that have all those months count."))
        else:
            st.caption(T("Esta variable solo toma valores parte del año, así que se analizan los promedios anuales.",
                         "This variable only takes values part of the year, so the annual means are analysed."))
        plotly(graficas.tendencia(r))
        st.caption(T(f"La curva punteada es una regresión local (LOESS, con el {100 * graficas.FRACCION_LOESS:.0f} % "
                     f"de los datos más cercanos a cada punto): muestra la forma del cambio sin suponer que es "
                     f"una recta. Donde se separa de la tendencia lineal, el cambio no fue constante. Es "
                     f"descriptiva y no cuenta entre las pruebas.",
                     f"The dotted curve is a local regression (LOESS, with the {100 * graficas.FRACCION_LOESS:.0f} % of "
                     f"the data closest to each point): it shows the shape of the change without assuming it is a "
                     f"straight line. Where it departs from the linear trend, the change was not steady. It is "
                     f"descriptive and does not count among the tests."))
    if mensual is not None:
        with mensual:
            _tendencia_por_mes(r)
    if original is not None:
        with original:
            st.caption(T("Promedios mensuales tal como se reciben. La oscilación regular es el ciclo estacional.",
                         "Monthly means as received. The regular oscillation is the seasonal cycle.")
                       if not r.por_temporada else
                       T(f"Valores mensuales de {r.temporada}, tal como se reciben.", f"Monthly values for {r.temporada}, as received."))
            plotly(graficas.serie_original(r))

    st.markdown(T("**Pruebas de significancia.** Una tendencia visible en la gráfica puede deberse al "
                  "azar. Cada prueba da un valor p: la probabilidad de observar una tendencia al menos "
                  "tan marcada como esta si en realidad no hubiera ninguna. Cuanto más pequeño, menos "
                  "creíble es que sea casualidad. Una prueba se supera si p es menor que el nivel de "
                  "significancia α = 0.05, y la tendencia se considera sólida solo si supera las cinco.",
                  "**Significance tests.** A trend visible in the chart may be due to chance. Each test gives a "
                  "p-value: the probability of observing a trend at least as marked as this one if there were "
                  "actually none. The smaller it is, the less believable it is that it is a coincidence. A test is "
                  "passed if p is below the significance level α = 0.05, and the trend is considered solid only if "
                  "it passes all five."))
    for prueba in r.pruebas:
        with st.container(border=True):
            estado, detalle, ayuda = st.columns([1, 7, 2], vertical_alignment="center")
            if prueba.aprobada:
                estado.badge(T("Pasa", "Pass"), icon=":material/check:", color="green")
            else:
                estado.badge(T("No pasa", "Fail"), icon=":material/close:", color="gray")
            detalle.markdown(f"**{prueba.nombre}.** {prueba.pregunta}  \n{prueba.resultado}")
            with ayuda.popover(T("¿Cómo funciona?", "How does it work?")):
                st.write(prueba.explicacion)

    if r.mk.corregida:
        ingenuo, corregido = caso.valor_p(r.mk_ingenuo.p), caso.valor_p(r.mk.prueba.p)
        if r.mk_ingenuo.p < 0.05 <= r.mk.prueba.p:
            st.warning(T(
                f"**Efecto de la autocorrelación.** Sin corregirla, la prueba de Mann-Kendall "
                f"habría declarado significativa esta tendencia ({ingenuo}). Con la corrección "
                f"deja de serlo ({corregido}): era un falso positivo.",
                f"**Effect of autocorrelation.** Without correcting for it, the Mann-Kendall test would have "
                f"declared this trend significant ({ingenuo}). With the correction it no longer is "
                f"({corregido}): it was a false positive."), icon=":material/warning:")
        else:
            st.caption(T(f"Efecto de corregir la autocorrelación en Mann-Kendall: sin corregir, {ingenuo}; corregida, {corregido}.",
                         f"Effect of correcting for autocorrelation in Mann-Kendall: uncorrected, {ingenuo}; corrected, {corregido}."))

    st.markdown(T("**Sensibilidad al periodo.** Cada celda es la tendencia de un periodo distinto. "
                  "Si todo el triángulo tiene el mismo color, el signo de la tendencia no depende de "
                  "los años elegidos. La esquina superior izquierda es el periodo completo.",
                  "**Sensitivity to the period.** Each cell is the trend of a different period. If the whole "
                  "triangle has the same colour, the sign of the trend does not depend on the years chosen. The "
                  "top-left corner is the full period."))
    plotly(graficas.triangulo(r))
    cambio = veredicto.cambio_de_comportamiento(r)
    if cambio:
        st.markdown(f"**{T('Cambio de comportamiento', 'Change in behaviour')}.** {cambio}")
        st.caption(T("Regresión en dos tramos sobre los promedios anuales: se busca el año que mejor "
                     "divide la serie en dos rectas. Es un análisis exploratorio; no cuenta entre las "
                     "cinco pruebas.",
                     "Two-segment regression on the annual means: the year that best splits the series into two "
                     "lines is sought. It is an exploratory analysis; it does not count among the five tests."))


def _contraste_de_hipotesis(r: caso.Interrogatorio, hipotesis: str) -> str:
    """Compara la hipótesis planteada antes de ver los datos con el resultado del análisis."""
    firme = r.nivel in ("solida", "fuerte")
    real = HIPOTESIS[2] if not firme else HIPOTESIS[0] if r.sube else HIPOTESIS[1]
    if hipotesis == real:
        return T(f"«{hipotesis}». El análisis la respalda.", f"“{hipotesis}”. The analysis supports it.")
    dice = T("no hay evidencia suficiente de un cambio", "there is insufficient evidence of a change") if not firme else real.lower()
    return T(f"«{hipotesis}». El análisis no la respalda: {dice}.", f"“{hipotesis}”. The analysis does not support it: {dice}.")


def paso_resultado(r: caso.Interrogatorio, sitio: dict, hipotesis: str | None = None,
                   mapa: pd.DataFrame | None = None, region_txt: str = "",
                   contraste: tuple[str, str | None] | None = None, numero: int = 5) -> None:
    seccion(numero, T("Resultado", "Result"))
    v = veredicto.redactar(r)
    u = r.variable.unidad
    with st.container(border=True):
        st.html(f'<div class="et-eyebrow">{escape(caso.NIVELES[r.nivel])}</div>'
                f'<div class="et-resultado">{escape(v.titular)}</div>')
        a, b, c, d = st.columns(4)
        cifra(a, T("Tasa de cambio", "Rate of change"), caso.numero(r.pendiente_decada, signo=True),
              T(f"{u} por década", f"{u} per decade"))
        cifra(b, T("Cambio acumulado", "Accumulated change"), caso.numero(r.cambio_total, signo=True),
              T(f"{u} en {r.anios_de_datos:.0f} años", f"{u} in {r.anios_de_datos:.0f} years"))
        cifra(c, T("Pruebas superadas", "Tests passed"), f"{r.aprobadas}/{caso.N_PRUEBAS}",
              T("pruebas de significancia", "significance tests"))
        cifra(d, T("Nivel de evidencia", "Level of evidence"), caso.NIVELES_CORTOS[r.nivel], "")
        solo = T(f"; solo {r.temporada}", f"; {r.temporada} only") if r.por_temporada else ""
        st.markdown(f"**{T('Sitio', 'Site')}.** {sitio['nombre']}.  \n"
                    f"**{T('Tamaño de muestra', 'Sample size')}.** {r.muestra}{solo}.  \n"
                    f"**{T('Tasa de cambio', 'Rate of change')}.** {v.cuanto}  \n"
                    f"**{T('Significancia', 'Significance')}.** {v.evidencia}")
        if v.espera:
            st.markdown(f"**{T('Años de datos necesarios', 'Years of data needed')}.** {v.espera}")
        if v.relevancia:
            st.markdown(f"**{T('Relevancia práctica', 'Practical relevance')}.** {v.relevancia}")
        if v.no_lineal:
            st.warning(f"**{T('Tendencia no lineal', 'Non-linear trend')}.** {v.no_lineal}", icon=":material/warning:")
        if v.registro_corto:
            st.warning(f"**{T('Registro corto', 'Short record')}.** {v.registro_corto}", icon=":material/warning:")
        if hipotesis:
            st.markdown(f"**{T('Hipótesis inicial', 'Initial hypothesis')}.** {_contraste_de_hipotesis(r, hipotesis)}")
        ficha, salvedades = st.columns(2)
        ficha.markdown(f"**{T('Ficha técnica', 'Technical sheet')}**\n\n| {T('Característica', 'Feature')} | "
                       f"{T('Detalle', 'Detail')} |\n|---|---|\n" + "\n".join(
            f"| {nombre} | {detalle} |" for nombre, detalle in veredicto.ficha_tecnica(r)))
        salvedades.markdown(f"**{T('Supuestos del análisis', 'Assumptions of the analysis')}**\n\n"
                            + "\n".join(f"- {x}" for x in veredicto.SUPUESTOS))
        salvedades.markdown(f"**{T('Limitaciones', 'Limitations')}**\n\n" + "\n".join(f"- {x}" for x in v.advertencias))
    st.download_button(
        T("Descargar el informe", "Download the report"),
        informe.informe_html(
            r, sitio["nombre"], sitio["lat"], sitio["lon"], mapa=mapa, region=region_txt, contraste=contraste,
            hipotesis=_contraste_de_hipotesis(r, hipotesis) if hipotesis else "",
            fecha_datos=(datos.fecha_de_datos(sitio["lat"], sitio["lon"], [x.codigo for x in CATALOGO if x.origen == "power"])
                         if sitio["lat"] is not None else dt.date.today()),
        ),
        file_name=f"{T('informe', 'report')}_{r.variable.codigo}_"
                  + (f"{sitio['lat']:.2f}_{sitio['lon']:.2f}" if sitio["lat"] is not None
                     else "".join(ch if ch.isalnum() else "_" for ch in sitio["nombre"]))
                  + ("_" + "-".join(str(m) for m in r.meses) if r.por_temporada else "") + ".html",
        mime="text/html",
        icon=":material/download:",
        help=T("Archivo HTML: se abre en cualquier navegador y se puede imprimir o guardar como PDF.",
               "HTML file: it opens in any browser and can be printed or saved as PDF."),
    )


def _fila_de_fuente(r: caso.Interrogatorio) -> str:
    bajo, alto = r.ic_decada
    return (f"| {r.variable.nombre} | {r.variable.fuente} | {caso.numero(r.pendiente_decada, signo=True)} "
            f"{r.variable.unidad} | {caso.numero(bajo, signo=True)} {T('a', 'to')} {caso.numero(alto, signo=True)} | "
            f"{caso.NIVELES_CORTOS[r.nivel]} ({r.aprobadas}/{caso.N_PRUEBAS}) | {r.n} |")


def contraste_entre_fuentes(sitio: dict, codigo: str, periodo: Periodo, meses: Meses, validas: list[str]) -> None:
    """La misma magnitud medida por otra fuente, sobre el periodo que comparten."""
    if codigo not in PAREJAS or PAREJAS[codigo][0] not in validas:
        return
    otra = PAREJAS[codigo][0]
    comun = (max(periodo[0], POR_CODIGO[codigo].desde, POR_CODIGO[otra].desde), periodo[1])
    try:
        a = cargar_analisis(sitio["lat"], sitio["lon"], codigo, comun, meses)
        b = cargar_analisis(sitio["lat"], sitio["lon"], otra, comun, meses)
    except (caso.CasoImposible, KeyError):
        return
    firme_a, firme_b = a.nivel in ("solida", "fuerte"), b.nivel in ("solida", "fuerte")
    if firme_a and firme_b and a.sube == b.sube:
        conclusion = T("Las dos fuentes coinciden: mismo signo y evidencia firme en ambas.",
                       "The two sources agree: same sign and firm evidence in both.")
    elif firme_a and firme_b:
        conclusion = T("Las dos fuentes se contradicen: cada una da una tendencia firme de signo opuesto. El "
                       "resultado depende de la fuente y debe tomarse con cautela.",
                       "The two sources contradict each other: each gives a firm trend of opposite sign. The "
                       "result depends on the source and should be taken with caution.")
    elif a.sube == b.sube and (firme_a or firme_b):
        conclusion = T("Las dos fuentes coinciden en el signo, pero solo una alcanza evidencia firme.",
                       "The two sources agree in sign, but only one reaches firm evidence.")
    elif firme_a or firme_b:
        conclusion = T("Las fuentes no coinciden: una da una tendencia firme y la otra apunta en sentido "
                       "contrario sin evidencia suficiente. El resultado debe tomarse con cautela.",
                       "The sources do not agree: one gives a firm trend and the other points the opposite way "
                       "without sufficient evidence. The result should be taken with caution.")
    else:
        conclusion = T("Ninguna de las dos fuentes muestra evidencia firme de una tendencia en el periodo que comparten.",
                       "Neither source shows firm evidence of a trend over the period they share.")
    st.markdown(f"**{T('Otra fuente de la misma magnitud', 'Another source of the same quantity')}.** {conclusion}")
    st.markdown(T("| Variable | Fuente | Cambio por década | IC del 95 % | Evidencia | n |",
                  "| Variable | Source | Change per decade | 95 % CI | Evidence | n |")
                + "\n|---|---|---|---|---|---|\n" + _fila_de_fuente(a) + "\n" + _fila_de_fuente(b))
    st.caption(T(f"Las dos series se analizaron sobre el periodo que comparten, de {comun[0]} a {comun[1]}, con las "
                 f"mismas cinco pruebas. {independencia(codigo)}",
                 f"The two series were analysed over the period they share, {comun[0]} to {comun[1]}, with the "
                 f"same five tests. {independencia(codigo)}"))


def relacion_con_otra_variable(sitio: dict, codigo: str, periodo: Periodo, meses: Meses, validas: list[str]) -> None:
    """Correlación entre la variable analizada y otra del mismo sitio."""
    otras = [c for c in validas if c != codigo]
    if not otras:
        return
    st.markdown(T("**Relación con otra variable.** ¿Hay otra variable de este sitio que varíe junto con esta?",
                  "**Relationship with another variable.** Is there another variable at this site that varies "
                  "together with this one?"))
    pedida = _parametro("con")
    otra = st.selectbox(T("Variable con la que se relaciona", "Variable to relate it to"), [""] + otras,
                        index=otras.index(pedida) + 1 if pedida in otras else 0,
                        format_func=lambda c: POR_CODIGO[c].nombre if c else T("Elegir una variable", "Choose a variable"),
                        label_visibility="collapsed", key=f"relacion_{codigo}")
    if not otra:
        return
    try:
        a = cargar_analisis(sitio["lat"], sitio["lon"], codigo, periodo, meses)
        b = cargar_analisis(sitio["lat"], sitio["lon"], otra, periodo, meses)
        rel = caso.relacionar(a, b)
    except (caso.CasoImposible, KeyError) as error:
        st.warning(T(f"No se pueden relacionar estas dos variables. {error}", f"These two variables cannot be related. {error}"))
        return
    c = rel.correlacion
    fuerza = (T("débil", "weak") if abs(c.r) < 0.3 else T("moderada", "moderate") if abs(c.r) < 0.6 else T("fuerte", "strong"))
    sentido = (T("varían en el mismo sentido", "they vary in the same direction") if c.r > 0
               else T("varían en sentido contrario", "they vary in opposite directions"))
    if c.p < 0.05:
        lectura = T(f"La correlación es {fuerza} y significativa: cuando una se aparta de lo normal, la otra "
                    f"tiende a hacerlo también ({sentido}).",
                    f"The correlation is {fuerza} and significant: when one departs from normal, the other tends "
                    f"to do so too ({sentido}).")
    else:
        lectura = T("La correlación no es significativa: no hay evidencia de que varíen juntas.",
                    "The correlation is not significant: there is no evidence that they vary together.")
    dato = (T("meses", "months") if rel.resolucion == "mensual" else T("años", "years"))
    uno, dos, tres = st.columns(3)
    cifra(uno, T("Correlación", "Correlation"), f"{c.r:+.2f}", T("r de Pearson, sin tendencias", "Pearson's r, detrended"))
    cifra(dos, T("Valor p", "p-value"), caso.valor_p(c.p).replace("p = ", "").replace("p ", ""),
          T("con tamaño de muestra efectivo", "with effective sample size"))
    cifra(tres, T("Tamaño de muestra", "Sample size"), f"{c.n}",
          T(f"{dato} en común; efectivo: {c.n_efectivo:.0f}", f"{dato} in common; effective: {c.n_efectivo:.0f}"))
    st.markdown(lectura)
    plotly(graficas.relacion(rel.fechas, rel.a, rel.b, a.variable.nombre, b.variable.nombre, rel.resolucion == "mensual"))
    movil = T(" (la curva es la media móvil de 12 meses)", " (the curve is the 12-month moving average)") if rel.resolucion == "mensual" else ""
    st.caption(T("A cada serie se le quitó su ciclo estacional y su tendencia lineal, y se dividió entre su "
                 f"desviación estándar para ponerlas en la misma escala{movil}. Sin quitar la tendencia, dos "
                 "variables que solo comparten un cambio de fondo parecerían relacionadas. El valor p descuenta "
                 "la autocorrelación de las dos series (Bretherton et al., 1999). Una correlación no demuestra "
                 "que una variable cause a la otra.",
                 "Each series had its seasonal cycle and its linear trend removed, and was divided by its "
                 f"standard deviation to put them on the same scale{movil}. Without removing the trend, two "
                 "variables that only share an underlying change would look related. The p-value discounts the "
                 "autocorrelation of both series (Bretherton et al., 1999). A correlation does not prove that "
                 "one variable causes the other."))


METODO_ES = """
**Datos.** Series mensuales de dos tipos. De reanálisis: [NASA POWER](https://power.larc.nasa.gov/)
distribuye variables de MERRA-2 para cualquier punto del planeta desde 1981. De satélite, por
Google Earth Engine: precipitación de GPM IMERG (desde 1998), vegetación, aerosoles y nubosidad
de MODIS (desde 2000), almacenamiento de agua de GRACE (desde 2002), ozono de OMI (desde 2005),
clorofila y temperatura del mar de MODIS Aqua (desde 2003), temperatura del mar de OISST (desde
1982) y escurrimiento del modelo FLDAS (desde 1982). Para la región se usa
cada celda de unos 50 km dentro del recuadro y se promedia ponderando por área.

**Tasa de cambio.** Pendiente de una regresión lineal por mínimos cuadrados sobre las
anomalías, con intervalo de confianza del 95 % por bootstrap de 2,000 series que conservan la
variabilidad y la autocorrelación de la serie.

**Pruebas de significancia.**
1. Mann-Kendall con preblanqueo iterativo para corregir la autocorrelación (Zhang et al., 2000; Wang y Swail, 2001).
2. Prueba t de la pendiente con tamaño de muestra efectivo (Santer et al., 2000).
3. Intervalo de confianza del 95 % por bootstrap: ¿excluye el cero?
4. Persistencia de la tendencia con promedios anuales (o excluyendo un año a la vez).
5. Sensibilidad al periodo: el signo se mantiene en al menos 80 % de los periodos posibles.

**Validación.** Las pruebas se aplicaron a series sintéticas sin tendencia y con
autocorrelación. La prueba de Mann-Kendall sin corregir dio falsos positivos entre 14 % y
64 % de las veces. Las pruebas corregidas, entre 4 % y 7 %, cerca del 5 % nominal. El
resultado completo alcanzó evidencia «fuerte» o «sólida» en 3 a 4 de cada 100 series sin
tendencia, y en 79 a 98 de cada 100 cuando la tendencia existía (1,500 a 2,000 series por
escenario; el código está en la carpeta `validacion/`).

**Análisis por estación o por mes.** Al elegir una parte del año, la serie se reduce a un dato
por año (el promedio de esos meses; solo cuentan los años que los tienen todos) y se aplican las
mismas cinco pruebas a resolución anual, la misma ruta validada con series de 19 a 45 años. La
pestaña «Tendencia por mes del año» repite el cálculo para cada mes del calendario y ajusta los
12 valores p con Benjamini-Hochberg.

**Extremos.** Ocho índices anuales con las definiciones del ETCCDI (Zhang et al., 2011),
calculados con la temperatura máxima, la mínima y la precipitación de cada día (MERRA-2, vía
NASA POWER). Solo cuentan los años con al menos 360 días de datos. Se analizan con las mismas
cinco pruebas a resolución anual y solo para el punto.

**Países y mundo.** La frontera de cada país viene del catálogo LSIB 2017 del Departamento de
Estado de EE. UU. (en Earth Engine). Entran las celdas cuyo centro cae dentro de la frontera; la
serie nacional o global es su promedio ponderado por área (coseno de la latitud), y a esa serie
se le aplican las mismas cinco pruebas. El tamaño de la celda se ajusta para no pasar de 6,000
celdas: 0.25° a 1° en un país, 3° en el mundo (de 60° S a 84° N). Solo están disponibles las
variables que llegan por Earth Engine.

**Otra fuente y relación entre variables.** Cuando existe otra fuente de la misma magnitud
(satélite y reanálisis, o dos sensores), las dos se analizan sobre el periodo que comparten y se
informa si coinciden. La relación entre dos variables es la correlación de Pearson de sus
anomalías sin tendencia; su valor p usa el tamaño de muestra efectivo de Bretherton et al. (1999).

**Curva suavizada.** Regresión local LOESS (Cleveland, 1979) con la mitad de los datos más
cercanos a cada punto. Describe la forma del cambio sin suponer una recta; no entra a las pruebas.

**Tamaños de muestra.** Cada resultado indica su n: meses o años que entran a las pruebas, años
por variable en la exploración y años por celda en el mapa. El tamaño efectivo descuenta la
autocorrelación: n(1 − r₁)/(1 + r₁).

**Años de datos necesarios para detectar una tendencia.** Fórmula de Weatherhead et al. (1998).

**Cambio de comportamiento.** Regresión lineal en dos tramos sobre los promedios anuales, con
búsqueda del año de quiebre. Señala una inversión solo si los dos tramos son significativos
(α = 0.025 cada uno) y de signo opuesto. En simulación, señaló inversiones falsas en menos de
3 de cada 100 series.

**Criterios propios del equipo.** Las pruebas y sus correcciones provienen de la literatura
citada. Son decisiones de diseño de este proyecto, no estándares: la escala de evidencia (sólida
= 5 pruebas, fuerte = 4, débil = 2 o 3), el umbral de 80 % en la sensibilidad al periodo, el
mínimo de 15 años de datos, y los cortes de relevancia práctica (menos de 1, de 1 a 2 y más de
2 desviaciones estándar interanuales). Su efecto conjunto se midió en la validación.
"""

METODO_EN = """
**Data.** Monthly series of two kinds. From reanalysis: [NASA POWER](https://power.larc.nasa.gov/)
distributes MERRA-2 variables for any point on the planet since 1981. From satellites, through
Google Earth Engine: GPM IMERG precipitation (since 1998), MODIS vegetation, aerosols and cloud
cover (since 2000), GRACE water storage (since 2002), OMI ozone (since 2005), MODIS Aqua
chlorophyll and sea temperature (since 2003), OISST sea temperature (since 1982) and runoff from
the FLDAS model (since 1982). For the region, every cell of about 50 km inside the box is used and
they are averaged weighting by area.

**Rate of change.** Slope of a least-squares linear regression on the anomalies, with a 95 %
confidence interval from a bootstrap of 2,000 series that preserve the variability and the
autocorrelation of the series.

**Significance tests.**
1. Mann-Kendall with iterative prewhitening to correct for autocorrelation (Zhang et al., 2000; Wang and Swail, 2001).
2. t-test of the slope with effective sample size (Santer et al., 2000).
3. 95 % bootstrap confidence interval: does it exclude zero?
4. Persistence of the trend with annual means (or leaving out one year at a time).
5. Sensitivity to the period: the sign holds in at least 80 % of the possible periods.

**Validation.** The tests were applied to synthetic series with no trend and with
autocorrelation. The uncorrected Mann-Kendall test gave false positives between 14 % and 64 % of
the time. The corrected tests, between 4 % and 7 %, close to the nominal 5 %. The full result
reached “strong” or “solid” evidence in 3 to 4 of every 100 trend-free series, and in 79 to 98 of
every 100 when the trend existed (1,500 to 2,000 series per scenario; the code is in the
`validacion/` folder).

**Analysis by season or by month.** When part of the year is chosen, the series is reduced to one
value per year (the mean of those months; only years that have all of them count) and the same
five tests are applied at annual resolution, the same path validated with series of 19 to 45
years. The “Trend by month of the year” tab repeats the calculation for each calendar month and
adjusts the 12 p-values with Benjamini-Hochberg.

**Extremes.** Eight annual indices with the ETCCDI definitions (Zhang et al., 2011), computed
from the maximum temperature, the minimum temperature and the precipitation of each day (MERRA-2,
via NASA POWER). Only years with at least 360 days of data count. They are analysed with the same
five tests at annual resolution and only for the point.

**Countries and world.** The border of each country comes from the LSIB 2017 catalogue of the US
Department of State (in Earth Engine). Cells whose centre falls inside the border are included;
the national or global series is their area-weighted mean (cosine of latitude), and the same five
tests are applied to that series. The cell size is adjusted so as not to exceed 6,000 cells:
0.25° to 1° for a country, 3° for the world (60° S to 84° N). Only the variables that come through
Earth Engine are available.

**Another source and relationship between variables.** When another source of the same quantity
exists (satellite and reanalysis, or two sensors), both are analysed over the period they share
and it is reported whether they agree. The relationship between two variables is the Pearson
correlation of their detrended anomalies; its p-value uses the effective sample size of
Bretherton et al. (1999).

**Smoothed curve.** LOESS local regression (Cleveland, 1979) with the half of the data closest to
each point. It describes the shape of the change without assuming a straight line; it does not
enter the tests.

**Sample sizes.** Every result states its n: months or years entering the tests, years per
variable in the exploration and years per cell in the map. The effective size discounts
autocorrelation: n(1 − r₁)/(1 + r₁).

**Years of data needed to detect a trend.** Formula of Weatherhead et al. (1998).

**Change in behaviour.** Two-segment linear regression on the annual means, searching for the
break year. It flags a reversal only if both segments are significant (α = 0.025 each) and of
opposite sign. In simulation, it flagged false reversals in fewer than 3 of every 100 series.

**The team's own criteria.** The tests and their corrections come from the cited literature.
These are design decisions of this project, not standards: the evidence scale (solid = 5 tests,
strong = 4, weak = 2 or 3), the 80 % threshold in the sensitivity to the period, the minimum of
15 years of data, and the cut-offs for practical relevance (less than 1, 1 to 2 and more than 2
interannual standard deviations). Their joint effect was measured in the validation.
"""


def metodo() -> None:
    with st.expander(T("Método y validación", "Method and validation")):
        st.markdown(T(METODO_ES, METODO_EN))
        st.page_link(PAGINAS["variables"], label=T("Referencias completas", "Full references"), icon=":material/arrow_forward:")


def pagina_analisis() -> None:
    guiado = st.session_state.get("guiado")
    eyebrow = T("Análisis de un lugar", "Analysis of a place")
    if guiado:
        # El inicio guiado guarda posiciones (ejemplo, tema, hipótesis) para no depender del idioma.
        sitio = EJEMPLOS[guiado["ejemplo"]] if guiado.get("ejemplo") is not None else guiado["sitio"]
        tema = list(TEMAS)[guiado["tema"]]
        st.sidebar.markdown(f"**{T('Sitio de estudio', 'Study site')}**  \n{sitio['nombre']}  \n"
                            f"{T('Tema de interés', 'Topic of interest')}: {tema.lower()}.")
        if st.sidebar.button(T("Cambiar de sitio", "Change site")):
            del st.session_state["guiado"]
            st.rerun()
    else:
        sitio = elegir_sitio()
    if sitio is None:
        encabezado(eyebrow, T("Elige un sitio de estudio", "Choose a study site"))
        st.info(T("Escribe un lugar en la barra lateral para empezar.", "Type a place in the sidebar to begin."))
        return

    periodo = elegir_periodo()
    meses = elegir_meses()
    encabezado(eyebrow, sitio["nombre"])
    if periodo is None:
        st.info(T(f"El periodo elegido es demasiado corto. Amplíalo a {caso.MIN_ANIOS} años o más en la barra lateral.",
                  f"The chosen period is too short. Extend it to {caso.MIN_ANIOS} years or more in the sidebar."))
        return
    try:
        with st.spinner(T("Descargando los datos...", "Downloading the data...")):
            tabla_datos = _recortar(cargar_datos(sitio["lat"], sitio["lon"]), periodo)
            exploracion = cargar_exploracion(sitio["lat"], sitio["lon"], periodo, meses)
    except datos.ErrorDeDatos as error:
        st.error(T(f"No se pudieron obtener los datos. {error}", f"The data could not be obtained. {error}"))
        return

    paso_sitio(sitio, tabla_datos)
    preferidas = tuple(TEMAS[tema]) if guiado else ()
    codigo = paso_exploracion(exploracion, preferidas, meses)
    if codigo is None:
        return
    # La hipótesis se planteó sobre la primera variable del tema; si se cambia de variable ya no aplica.
    validas = list(exploracion.dropna(subset=["estandarizada"])["codigo"])
    planteada = next((c for c in preferidas if c in validas), validas[0]) if guiado else None
    hipotesis = HIPOTESIS[guiado["hipotesis"]] if guiado and codigo == planteada else None

    ejemplo, punto = sitio["nombre"], sitio  # `sitio` cambia si se analiza la región o una celda
    espacial = paso_mapa(sitio, codigo, periodo, meses)
    lado, alcance, celda = espacial if espacial else (None, "punto", None)
    try:
        if alcance == "punto":
            r = cargar_analisis(sitio["lat"], sitio["lon"], codigo, periodo, meses)
        elif alcance == "region":
            r = cargar_analisis_regional(sitio["lat"], sitio["lon"], codigo, lado, periodo, meses)
            sitio = {**sitio, "nombre": T(f"Región de {lado}° × {lado}° alrededor de {sitio['nombre']}",
                                          f"Region of {lado}° × {lado}° around {sitio['nombre']}")}
        else:
            r = cargar_analisis_celda(sitio["lat"], sitio["lon"], codigo, lado, periodo, celda, meses)
            lat_celda, lon_celda = (float(x) for x in celda.split(","))
            sitio = {"nombre": T(f"Celda en {lat_celda:.2f}°, {lon_celda:.2f}°, cerca de {sitio['nombre']}",
                                 f"Cell at {lat_celda:.2f}°, {lon_celda:.2f}°, near {sitio['nombre']}"),
                     "lat": lat_celda, "lon": lon_celda}
    except caso.CasoImposible as error:
        st.warning(str(error))
        return
    paso_serie(r)
    mapa, region_txt = None, ""
    if lado is not None:
        mapa = cargar_mapa(punto["lat"], punto["lon"], codigo, lado, periodo, meses)
        lat_min, lat_max, lon_min, lon_max = datos.caja(punto["lat"], punto["lon"], lado)
        region_txt = T(f"Recuadro de {lado}° × {lado}° alrededor de {punto['nombre']}: latitud {lat_min:g}° a "
                       f"{lat_max:g}°, longitud {lon_min:g}° a {lon_max:g}°.",
                       f"Box of {lado}° × {lado}° around {punto['nombre']}: latitude {lat_min:g}° to "
                       f"{lat_max:g}°, longitude {lon_min:g}° to {lon_max:g}°.")
    paso_resultado(r, sitio, hipotesis, mapa, region_txt, CONTRASTES.get((ejemplo, codigo)))
    contraste_con_literatura(ejemplo, codigo)
    seccion(6, T("Contraste con otras variables", "Comparison with other variables"))
    if alcance != "punto":
        st.caption(T("El contraste se hace con las series del punto de estudio, no con las de la región o la celda.",
                     "The comparison uses the series of the study point, not those of the region or the cell."))
    contraste_entre_fuentes(punto, codigo, periodo, meses, validas)
    relacion_con_otra_variable(punto, codigo, periodo, meses, validas)
    metodo()


# ------------------------------------------------------------------ página: país o mundo

def _elegir_pais(barra) -> tuple[str, Territorio] | None:
    """Campo para escribir un país. Devuelve (nombre, territorio) o None si aún no hay uno válido."""
    eyebrow = T("País o mundo", "Country or world")
    texto = barra.text_input(T("País", "Country"), value=_parametro("pais"), placeholder=T("Ej. México", "E.g. Mexico"))
    if not texto.strip():
        encabezado(eyebrow, T("Escribe un país", "Type a country"))
        st.info(T("Escribe el nombre de un país en la barra lateral.", "Type the name of a country in the sidebar."))
        return None
    try:
        paises = [l for l in buscar(texto.strip()) if l.get("es_pais")]
    except datos.ErrorDeDatos as error:
        st.error(str(error))
        return None
    if not paises:
        encabezado(eyebrow, T("País no encontrado", "Country not found"))
        st.warning(T(f"No se encontró un país llamado «{texto.strip()}». Para una ciudad o una región, usa "
                     f"«Análisis de un lugar».",
                     f"No country called “{texto.strip()}” was found. For a city or a region, use “Analysis of "
                     f"a place”."))
        return None
    lugar = paises[0] if len(paises) == 1 else barra.selectbox(T("Coincidencias", "Matches"), paises, format_func=lambda l: l["nombre"])
    try:
        with st.spinner(T("Buscando la frontera del país...", "Looking up the country's border...")):
            return lugar["nombre"], cargar_pais(lugar["lat"], lugar["lon"])
    except datos.ErrorDeDatos as error:
        encabezado(eyebrow, lugar["nombre"])
        st.error(T(f"No se pudo obtener la frontera. {error}", f"The border could not be obtained. {error}"))
        return None


def pagina_territorio() -> None:
    barra = st.sidebar
    barra.markdown(f"**{T('Territorio', 'Territory')}**")
    modos = {"mundo": T("Mundo", "World"), "pais": T("País", "Country")}
    modo = barra.radio(T("Territorio", "Territory"), list(modos), index=1 if _parametro("pais") else 0,
                       format_func=modos.get, horizontal=True, label_visibility="collapsed")
    nombre, territorio = modos["mundo"], None
    if modo == "pais":
        elegido = _elegir_pais(barra)
        if elegido is None:
            return
        nombre, territorio = elegido
    # En un país solo se ofrecen variables de tierra; en el mundo, todas las que llegan por Earth Engine.
    codigos = [v.codigo for v in CATALOGO if v.origen == "gee" and not (territorio and v.codigo in SOLO_MAR)]
    pedida = _parametro("var")
    inicial = pedida if pedida in codigos else "FLDAS_TEMP" if territorio else "MAR_SST"
    barra.markdown("**Variable**")
    codigo = barra.selectbox("Variable", codigos, index=codigos.index(inicial), label_visibility="collapsed",
                             format_func=lambda c: POR_CODIGO[c].nombre)
    periodo = elegir_periodo()
    meses = elegir_meses()
    v = POR_CODIGO[codigo]
    encabezado(T("Análisis de un país", "Analysis of a country") if territorio else T("Análisis global", "Global analysis"),
               nombre, v.nombre)
    if periodo is None:
        st.info(T(f"El periodo elegido es demasiado corto. Amplíalo a {caso.MIN_ANIOS} años o más en la barra lateral.",
                  f"The chosen period is too short. Extend it to {caso.MIN_ANIOS} years or more in the sidebar."))
        return
    try:
        with st.spinner(T("Descargando los datos de Earth Engine y calculando la tendencia de cada celda...",
                          "Downloading the data from Earth Engine and computing the trend of each cell...")):
            mapa = cargar_mapa_territorio(territorio, codigo, periodo, meses)
            r = cargar_analisis_territorio(territorio, codigo, periodo, meses)
    except datos.ErrorDeDatos as error:
        st.error(T(f"No se pudieron obtener los datos. {error}", f"The data could not be obtained. {error}"))
        return
    except caso.CasoImposible as error:
        st.warning(T(f"Esta variable no se puede analizar en {nombre}. {error}", f"This variable cannot be analysed in {nombre}. {error}"))
        return
    if mapa.empty:
        st.warning(T(f"Esta variable no tiene datos suficientes en {nombre}.", f"This variable does not have enough data in {nombre}."))
        return

    seccion(1, T("Territorio y variable", "Territory and variable"))
    texto, definicion = st.columns([5, 2], vertical_alignment="center")
    texto.markdown(f"**{v.nombre}** ({v.unidad}). {v.definicion}  \n{T('Fuente', 'Source')}: {v.fuente}.")
    definicion_emergente(definicion, v)
    caja_del_territorio = territorio[1:] if territorio else datos_gee.MUNDO
    celda = datos_gee.celda_para(codigo, *caja_del_territorio)
    resumen = region.resumen(mapa)
    anios = (T(f"{resumen['anios_min']} años", f"{resumen['anios_min']} years") if resumen["anios_min"] == resumen["anios_max"]
             else T(f"entre {resumen['anios_min']} y {resumen['anios_max']} años",
                    f"between {resumen['anios_min']} and {resumen['anios_max']} years"))
    de_meses = T(f" de {caso.nombre_de_meses(meses)}", f" for {caso.nombre_de_meses(meses)}") if len(meses) < 12 else ""
    if territorio:
        alcance = T("Entran las celdas cuyo centro cae dentro de la frontera (catálogo LSIB 2017 del Departamento de "
                    "Estado de EE. UU.). El promedio nacional pondera cada celda por su área.",
                    "Cells whose centre falls inside the border are included (LSIB 2017 catalogue of the US "
                    "Department of State). The national mean weights each cell by its area.")
    else:
        alcance = T("Entran todas las celdas con datos entre 60° S y 84° N. El promedio global pondera cada celda por su área.",
                    "All cells with data between 60° S and 84° N are included. The global mean weights each cell by its area.")
    st.caption(T(f"Tamaño de muestra: {resumen['celdas']:,} celdas de {celda:g}° (unos {celda * 111:,.0f} km de lado), "
                 f"cada una con {anios} de datos{de_meses}. {alcance}",
                 f"Sample size: {resumen['celdas']:,} cells of {celda:g}° (about {celda * 111:,.0f} km across), each "
                 f"with {anios} of data{de_meses}. {alcance}"))

    seccion(2, T("Distribución espacial de la tendencia", "Spatial distribution of the trend"))
    texto = T(f"La tendencia es positiva y significativa en **{resumen['sube']:.0f} %** de las celdas, y negativa "
              f"y significativa en **{resumen['baja']:.0f} %**.",
              f"The trend is positive and significant in **{resumen['sube']:.0f} %** of the cells, and negative "
              f"and significant in **{resumen['baja']:.0f} %**.")
    if resumen["sube"] >= 5 and resumen["baja"] >= 5:
        donde = (T("el país", "the country") if territorio else T("el planeta", "the planet"))
        texto += T(f" **La misma variable presenta tendencias opuestas dentro de {donde}.**",
                   f" **The same variable shows opposite trends within {donde}.**")
    st.markdown(texto)
    plotly(graficas.mapa(mapa, v.unidad))
    st.caption(T("Rojo: tendencia positiva. Azul: negativa. El punto marca las celdas con tendencia significativa "
                 "tras el ajuste de Benjamini-Hochberg por comparaciones múltiples. Las zonas sin color no tienen "
                 "datos de esta variable.",
                 "Red: positive trend. Blue: negative. The dot marks the cells with a significant trend after the "
                 "Benjamini-Hochberg adjustment for multiple comparisons. Uncoloured areas have no data for this "
                 "variable."))
    with st.expander(T("Ver como tabla", "View as a table")):
        st.dataframe(mapa, hide_index=True, width="stretch", column_config=_columnas_del_mapa(v))

    paso_serie(r, numero=3)
    promedio = (T("promedio nacional", "national mean") if territorio else T("promedio global", "global mean"))
    paso_resultado(r, {"nombre": T(f"{nombre} ({promedio} de {resumen['celdas']:,} celdas)",
                                   f"{nombre} ({promedio} of {resumen['celdas']:,} cells)"), "lat": None, "lon": None},
                   mapa=mapa, numero=4,
                   region_txt=T(f"{nombre}: {resumen['celdas']:,} celdas de {celda:g}° con datos.",
                                f"{nombre}: {resumen['celdas']:,} cells of {celda:g}° with data."))
    metodo()


# ------------------------------------------------------------------ página: laboratorio

@st.cache_data(show_spinner=False)
def cargar_simulacion(anios: int, phi: float, series: int, pendiente: float, semilla: int) -> laboratorio.Simulacion:
    return laboratorio.simular(anios, phi, series, pendiente, semilla)


TENDENCIAS_DE_LABORATORIO = {
    T("Ninguna: se miden los falsos positivos", "None: false positives are measured"): 0.0,
    T("Modesta (0.2 desviaciones estándar por década): se mide la potencia",
      "Modest (0.2 standard deviations per decade): power is measured"): 0.2,
    T("Marcada (0.5 desviaciones estándar por década): se mide la potencia",
      "Marked (0.5 standard deviations per decade): power is measured"): 0.5,
}


def pagina_laboratorio() -> None:
    encabezado(T("Laboratorio", "Laboratory"),
               T("¿Cuántas tendencias inventa cada prueba?", "How many trends does each test invent?"),
               T("Aquí se fabrican series que no tienen ninguna tendencia y se les aplican las pruebas. Todo lo "
                 "que una prueba «detecte» en ellas es un error.",
                 "Here series with no trend at all are manufactured and the tests are applied to them. Anything "
                 "a test “detects” in them is an error."))
    seccion(1, T("Experimento", "Experiment"))
    st.markdown(T(
        "Las series del clima tienen autocorrelación: un mes cálido suele ir seguido de otro mes cálido. Eso "
        "produce rachas largas que a simple vista, y para una prueba que suponga datos independientes, parecen "
        "tendencias. Elige las condiciones y compara cuántas series declara «con tendencia significativa» cada "
        "prueba. Con α = 0.05, una prueba bien calibrada debe equivocarse en unas 5 de cada 100.",
        "Climate series are autocorrelated: a warm month is usually followed by another warm month. That "
        "produces long runs which, to the naked eye and to a test that assumes independent data, look like "
        "trends. Choose the conditions and compare how many series each test declares “to have a significant "
        "trend”. With α = 0.05, a well-calibrated test should be wrong in about 5 out of 100."))
    a, b, c = st.columns(3)
    phi = a.slider(T("Autocorrelación entre un mes y el siguiente", "Autocorrelation between one month and the next"),
                   0.0, 0.9, 0.6, step=0.1,
                   help=T("0: cada mes es independiente del anterior. 0.9: cada mes se parece mucho al anterior. "
                          "En los datos reales de esta herramienta va de 0.1 a 0.9 según la variable.",
                          "0: each month is independent of the previous one. 0.9: each month closely resembles "
                          "the previous one. In the real data of this tool it ranges from 0.1 to 0.9 depending "
                          "on the variable."))
    anios = b.slider(T("Años de datos mensuales", "Years of monthly data"), 15, 45, 30, step=5)
    series = c.select_slider(T("Series simuladas", "Simulated series"), [100, 200, 300, 500, 1000], value=300)
    izq, der = st.columns([3, 1], vertical_alignment="bottom")
    opciones = list(TENDENCIAS_DE_LABORATORIO)
    tendencia = izq.selectbox(T("Tendencia real que se añade a las series", "Real trend added to the series"),
                              range(len(opciones)), format_func=lambda k: opciones[k])
    if der.button(T("Generar otras series", "Generate other series"), icon=":material/refresh:", width="stretch"):
        st.session_state["semilla_laboratorio"] = st.session_state.get("semilla_laboratorio", 0) + 1
    pendiente = TENDENCIAS_DE_LABORATORIO[opciones[tendencia]]
    with st.spinner(T(f"Simulando {series} series...", f"Simulating {series} series...")):
        sim = cargar_simulacion(anios, phi, series, pendiente, st.session_state.get("semilla_laboratorio", 0))

    seccion(2, T("Resultado", "Result"))
    if pendiente == 0:
        veces = sim.clasica / max(sim.corregida, 100 / series)
        cierre = T(f", unas {veces:.0f} veces menos.", f", about {veces:.0f} times fewer.") if veces >= 1.5 else "."
        st.markdown(T(
            f"Ninguna de las {series} series tiene tendencia. La prueba de Mann-Kendall clásica declaró una "
            f"tendencia significativa en **{sim.clasica:.0f} %** de ellas; con el preblanqueo que usa esta "
            f"herramienta, en **{sim.corregida:.0f} %**{cierre}",
            f"None of the {series} series has a trend. The classic Mann-Kendall test declared a significant "
            f"trend in **{sim.clasica:.0f} %** of them; with the prewhitening this tool uses, in "
            f"**{sim.corregida:.0f} %**{cierre}"))
    else:
        st.markdown(T(
            f"Las {series} series tienen una tendencia real. La prueba corregida la detectó en "
            f"**{sim.corregida:.0f} %** de ellas y la clásica en **{sim.clasica:.0f} %**. La clásica detecta "
            f"más, pero a costa de sus falsos positivos: no distingue una tendencia real de una racha.",
            f"All {series} series have a real trend. The corrected test detected it in **{sim.corregida:.0f} %** "
            f"of them and the classic one in **{sim.clasica:.0f} %**. The classic test detects more, but at the "
            f"cost of its false positives: it cannot tell a real trend from a run."))
    plotly(graficas.laboratorio(sim.clasica, sim.corregida, sim.prueba_t, pendiente > 0))
    margen = 196 * (0.05 * 0.95 / series) ** 0.5
    st.caption(T(f"Con {series} series, una prueba calibrada al 5 % daría entre {max(5 - margen, 0):.0f} % y "
                 f"{5 + margen:.0f} % por azar. La validación completa del método, con 1,500 a 2,000 series por "
                 f"escenario y las cinco pruebas juntas, está en la carpeta validacion/ del repositorio.",
                 f"With {series} series, a test calibrated at 5 % would give between {max(5 - margen, 0):.0f} % and "
                 f"{5 + margen:.0f} % by chance. The full validation of the method, with 1,500 to 2,000 series per "
                 f"scenario and the five tests together, is in the validacion/ folder of the repository."))

    if pendiente == 0 and sim.ejemplo is not None:
        seccion(3, T("Una serie que engaña a la prueba clásica", "A series that fools the classic test"))
        st.markdown(T(
            f"Esta serie salió del experimento: no tiene tendencia, solo rachas. La prueba clásica la declara "
            f"significativa ({caso.valor_p(sim.ejemplo.p_clasica)}); con la corrección de la autocorrelación "
            f"deja de serlo ({caso.valor_p(sim.ejemplo.p_corregida)}).",
            f"This series came out of the experiment: it has no trend, only runs. The classic test declares it "
            f"significant ({caso.valor_p(sim.ejemplo.p_clasica)}); with the correction for autocorrelation it "
            f"no longer is ({caso.valor_p(sim.ejemplo.p_corregida)})."))
        plotly(graficas.serie_simulada(sim.ejemplo.t, sim.ejemplo.y))
        st.caption(T("Con datos reales ocurre lo mismo. En «Análisis de un lugar», la exploración de variables "
                     "muestra cuántas tendencias señalaría la prueba clásica en ese sitio y cuántas sobreviven a "
                     "las correcciones.",
                     "The same happens with real data. In “Analysis of a place”, the exploration of variables "
                     "shows how many trends the classic test would flag at that site and how many survive the "
                     "corrections."))
    metodo()


# ------------------------------------------------------------------ página: comparación

def _sitio_a_comparar(barra, etiqueta: str, indice: int) -> dict | None:
    opciones = [e["nombre"] for e in EJEMPLOS] + [T("Otro lugar", "Another place")]
    elegido = barra.selectbox(etiqueta, range(len(opciones)), index=indice, format_func=lambda k: opciones[k])
    if elegido < len(EJEMPLOS):
        return EJEMPLOS[elegido]
    return _buscar_sitio(barra, T(f"{etiqueta}: ciudad, región o país", f"{etiqueta}: city, region or country"), etiqueta)


def pagina_comparacion() -> None:
    barra = st.sidebar
    eyebrow = T("Comparación de dos lugares", "Comparison of two places")
    barra.markdown(f"**{T('Comparación', 'Comparison')}**")
    titulos = [c[0] for c in COMPARACIONES] + [T("Definir mi propia comparación", "Define my own comparison")]
    inicial = int(_parametro("comp")) if _parametro("comp").isdigit() else 0
    elegida = barra.selectbox(T("Comparación", "Comparison"), range(len(titulos)), index=min(inicial, len(titulos) - 1),
                              format_func=lambda k: titulos[k], label_visibility="collapsed")
    propia = elegida == len(titulos) - 1
    if not propia:
        _, i, j, codigo, pregunta = COMPARACIONES[elegida]
        sitio_a, sitio_b = EJEMPLOS[i], EJEMPLOS[j]
        barra.markdown(f"**{T('Pregunta de investigación', 'Research question')}.** {pregunta}")
    else:
        sitio_a = _sitio_a_comparar(barra, T("Lugar A", "Place A"), 0)
        sitio_b = _sitio_a_comparar(barra, T("Lugar B", "Place B"), 3)
    periodo = elegir_periodo()
    meses = elegir_meses()
    if propia:
        if sitio_a is None or sitio_b is None:
            encabezado(eyebrow, T("Elige dos lugares", "Choose two places"))
            st.info(T("Elige los dos lugares en la barra lateral.", "Choose the two places in the sidebar."))
            return
        try:
            with st.spinner(T("Descargando los datos...", "Downloading the data...")):
                todo = periodo or (datos.ANIO_INICIAL, dt.date.today().year)
                validas = [cargar_exploracion(s["lat"], s["lon"], todo, meses).dropna(subset=["estandarizada"])["codigo"]
                           for s in (sitio_a, sitio_b)]
        except datos.ErrorDeDatos as error:
            st.error(T(f"No se pudieron obtener los datos. {error}", f"The data could not be obtained. {error}"))
            return
        comunes = [v.codigo for v in CATALOGO if v.codigo in set(validas[0]) & set(validas[1])]
        if not comunes:
            st.warning(T("Estos dos lugares no tienen ninguna variable medible en común.",
                         "These two places have no measurable variable in common."))
            return
        codigo = barra.selectbox("Variable", comunes, format_func=lambda c: POR_CODIGO[c].nombre)
    if sitio_a["nombre"] == sitio_b["nombre"]:
        st.info(T("Elige dos lugares distintos para comparar.", "Choose two different places to compare."))
        return
    if periodo is None:
        encabezado(eyebrow, T("Periodo demasiado corto", "Period too short"))
        st.info(T(f"Amplía el periodo a {caso.MIN_ANIOS} años o más en la barra lateral.",
                  f"Extend the period to {caso.MIN_ANIOS} years or more in the sidebar."))
        return

    v = POR_CODIGO[codigo]
    nombre_a, nombre_b = sitio_a["nombre"], sitio_b["nombre"]
    solo = T(f"; solo {caso.nombre_de_meses(meses)}", f"; {caso.nombre_de_meses(meses)} only") if len(meses) < 12 else ""
    encabezado(eyebrow, v.nombre, T(f"{nombre_a} y {nombre_b}, de {periodo[0]} a {periodo[1]}{solo}.",
                                    f"{nombre_a} and {nombre_b}, {periodo[0]} to {periodo[1]}{solo}."))
    texto, definicion = st.columns([5, 2], vertical_alignment="center")
    texto.markdown(f"{v.definicion}  \n{T('Fuente', 'Source')}: {v.fuente}.")
    definicion_emergente(definicion, v)
    alcances = {"punto": T("El punto", "The point"),
                "region": T("El promedio de la región (8° × 8°)", "The mean of the region (8° × 8°)")}
    alcance = st.radio(T("Serie que se analiza en cada lugar", "Series analysed at each place"), list(alcances),
                       format_func=alcances.get, horizontal=True)
    try:
        with st.spinner(T("Analizando los dos lugares...", "Analysing the two places...")):
            if alcance == "punto":
                a = cargar_analisis(sitio_a["lat"], sitio_a["lon"], codigo, periodo, meses)
                b = cargar_analisis(sitio_b["lat"], sitio_b["lon"], codigo, periodo, meses)
            else:
                a = cargar_analisis_regional(sitio_a["lat"], sitio_a["lon"], codigo, 8, periodo, meses)
                b = cargar_analisis_regional(sitio_b["lat"], sitio_b["lon"], codigo, 8, periodo, meses)
    except (caso.CasoImposible, datos.ErrorDeDatos, KeyError) as error:
        st.warning(T(f"No se puede hacer esta comparación: en uno de los lugares la variable no se puede medir. {error}",
                     f"This comparison cannot be made: at one of the places the variable cannot be measured. {error}"))
        return

    seccion(1, T("Resultado", "Result"))
    with st.container(border=True):
        st.html(f'<div class="et-resultado">{escape(veredicto.comparar(a, b, nombre_a, nombre_b))}</div>')

    contraste_con_literatura(nombre_a, codigo)
    if CONTRASTES.get((nombre_b, codigo)) != CONTRASTES.get((nombre_a, codigo)):
        contraste_con_literatura(nombre_b, codigo)

    seccion(2, T("Series de tiempo", "Time series"))
    plotly(graficas.comparacion(a, b, nombre_a, nombre_b))
    curva = (T(f"el promedio de {caso.nombre_de_meses(meses)} de cada año", f"the {caso.nombre_de_meses(meses)} mean of each year")
             if len(meses) < 12 else
             T("la media móvil de 12 meses de las anomalías (sin ciclo estacional)",
               "the 12-month moving average of the anomalies (no seasonal cycle)"))
    st.caption(T(f"La curva es {curva}; la recta es la tendencia lineal. Cada lugar se compara con su propio "
                 f"promedio, por eso las dos series se centran en cero aunque sus valores absolutos sean "
                 f"distintos. Tamaño de muestra: {nombre_a}, {a.muestra}; {nombre_b}, {b.muestra}.",
                 f"The curve is {curva}; the straight line is the linear trend. Each place is compared with its "
                 f"own mean, which is why both series are centred on zero even though their absolute values "
                 f"differ. Sample size: {nombre_a}, {a.muestra}; {nombre_b}, {b.muestra}."))

    seccion(3, T("Distribución espacial", "Spatial distribution"))
    mapas = []
    for sitio in (sitio_a, sitio_b):
        try:
            mapas.append(cargar_mapa(sitio["lat"], sitio["lon"], codigo, 8, periodo, meses))
        except datos.ErrorDeDatos:
            mapas.append(pd.DataFrame())
    # Los dos mapas comparten la escala de color: el mismo tono significa el mismo cambio.
    tope = max((float(m["pendiente_decada"].abs().max()) for m in mapas if not m.empty), default=None)
    for columna, r, sitio, mapa in zip(st.columns(2), (a, b), (sitio_a, sitio_b), mapas):
        with columna.container(border=True):
            st.markdown(f"**{sitio['nombre']}**")
            izq, der = st.columns(2)
            cifra(izq, T("Tasa de cambio", "Rate of change"), caso.numero(r.pendiente_decada, signo=True),
                  T(f"{v.unidad} por década", f"{v.unidad} per decade"))
            cifra(der, T("Nivel de evidencia", "Level of evidence"), caso.NIVELES_CORTOS[r.nivel],
                  T(f"{r.aprobadas} de {caso.N_PRUEBAS} pruebas superadas", f"{r.aprobadas} of {caso.N_PRUEBAS} tests passed"))
            st.caption(T(f"{veredicto.redactar(r).cuanto} Tamaño de muestra: {r.muestra}.",
                         f"{veredicto.redactar(r).cuanto} Sample size: {r.muestra}."))
            if not mapa.empty:
                resumen = region.resumen(mapa)
                plotly(graficas.mapa(mapa, v.unidad, sitio["lat"], sitio["lon"], tope=tope, alejar=0.4),
                       clave=f"mapa_{sitio['lat']}_{sitio['lon']}")
                st.caption(T(f"En la región ({resumen['celdas']} celdas): tendencia positiva significativa en "
                             f"{resumen['sube']:.0f} % de las celdas y negativa en {resumen['baja']:.0f} %.",
                             f"In the region ({resumen['celdas']} cells): significant positive trend in "
                             f"{resumen['sube']:.0f} % of the cells and negative in {resumen['baja']:.0f} %."))
    st.caption(T("Las cinco pruebas de significancia de cada lugar están en «Análisis de un lugar».",
                 "The five significance tests of each place are in “Analysis of a place”."))
    metodo()


# ------------------------------------------------------------------ navegación e idioma

st.html(ESTILOS)
# Selector de idioma, arriba a la derecha de todas las páginas. Su valor vive en la sesión con la
# clave "idioma"; al cambiarlo, la app se vuelve a ejecutar y el idioma se fija al principio.
st.segmented_control(T("Idioma", "Language"), list(idioma.IDIOMAS), key="idioma", format_func=str.upper,
                     label_visibility="collapsed")
if st.session_state.get("idioma") not in idioma.IDIOMAS:  # se pulsó la opción activa y quedó sin selección
    st.session_state["idioma"] = idioma.actual()
    st.rerun()

PAGINAS.update({
    "inicio": st.Page(pagina_inicio, title=T("Inicio", "Home"), url_path="inicio", default=True),
    "variables": st.Page(pagina_variables, title="Variables", url_path="variables"),
    "analisis": st.Page(pagina_analisis, title=T("Análisis de un lugar", "Analysis of a place"), url_path="analisis"),
    "territorio": st.Page(pagina_territorio, title=T("País o mundo", "Country or world"), url_path="territorio"),
    "comparacion": st.Page(pagina_comparacion, title=T("Comparación de dos lugares", "Comparison of two places"), url_path="comparacion"),
    "laboratorio": st.Page(pagina_laboratorio, title=T("Laboratorio", "Laboratory"), url_path="laboratorio"),
})
st.navigation(list(PAGINAS.values()), position="top").run()
