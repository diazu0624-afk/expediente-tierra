"""Expediente Tierra: detección de tendencias en variables del sistema Tierra.

Para correrla:  .venv/bin/streamlit run app.py
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

from expediente import caso, datos, datos_gee, graficas, region, veredicto
from expediente.variables import CATALOGO, CATEGORIAS, METODOS, POR_CODIGO, REFERENCIAS, Variable

RAIZ = Path(__file__).parent
st.set_page_config(page_title="Expediente Tierra", page_icon=str(RAIZ / "static" / "favicon.png"),
                   layout="wide")

EJEMPLOS = [
    {"nombre": "Monterrey, México", "lat": 25.68, "lon": -100.32,
     "pregunta": "Monterrey vivió una crisis de agua en 2022. ¿Disminuyó la precipitación? "
                 "Compara la precipitación con el almacenamiento de agua terrestre (GRACE)."},
    {"nombre": "Nueva Delhi, India", "lat": 28.61, "lon": 77.21,
     "pregunta": "Alrededor de Delhi se riega una de las zonas agrícolas más grandes del mundo. "
                 "¿El índice de vegetación y el almacenamiento de agua tienen la misma tendencia?"},
    {"nombre": "Pekín, China", "lat": 39.90, "lon": 116.40,
     "pregunta": "Pekín y Delhi crecieron quemando carbón. ¿El espesor óptico de aerosoles "
                 "tiene la misma tendencia en las dos ciudades?"},
    {"nombre": "Longyearbyen, Svalbard (Ártico)", "lat": 78.22, "lon": 15.65,
     "pregunta": "Es el poblado más septentrional del mundo. ¿El Ártico se calienta más "
                 "rápido que latitudes medias como la de Monterrey?"},
    {"nombre": "Niamey, Níger (Sahel)", "lat": 13.51, "lon": 2.11,
     "pregunta": "El Sahel sufrió sequías severas en los años ochenta. ¿Se recuperó? El mapa "
                 "del índice de vegetación muestra tendencias distintas dentro de la región."},
    {"nombre": "Manaos, Brasil (Amazonía)", "lat": -3.10, "lon": -60.02,
     "pregunta": "En el centro de la selva más grande del planeta. ¿Está cambiando la "
                 "precipitación? Compara el reanálisis con la observación del satélite GPM."},
]

# Comparaciones sugeridas: (título, índice del ejemplo A, índice del B, variable, pregunta).
COMPARACIONES = [
    ("Delhi y Pekín: espesor óptico de aerosoles", 1, 2, "AOD_55",
     "Dos capitales que crecieron quemando carbón. ¿Su carga de aerosoles tiene la misma tendencia?"),
    ("Monterrey y el Ártico: temperatura del aire", 0, 3, "T2M",
     "El planeta se calienta, pero ¿con la misma tasa en todas las latitudes?"),
    ("Delhi y el Sahel: almacenamiento de agua terrestre", 1, 4, "GRACE_AGUA",
     "Dos regiones semiáridas densamente pobladas. ¿Cómo cambia su reserva de agua?"),
    ("Pekín y Monterrey: precipitación (satélite GPM)", 2, 0, "GPM_LLUVIA",
     "Dos ciudades con estrés hídrico. ¿En alguna está cambiando la precipitación?"),
]

# Inicio guiado: tema de interés -> variable que se analiza primero (la primera de la lista
# que se pueda medir en el sitio). La lista vacía deja la de mayor tendencia.
TEMAS = {
    "Temperatura": ["T2M"],
    "Precipitación y agua": ["GRACE_AGUA", "GPM_LLUVIA", "PRECTOTCORR"],
    "Calidad del aire": ["AOD_55"],
    "Vegetación y cultivos": ["MODIS_NDVI", "GWETROOT"],
    "Heladas y nieve": ["FROST_DAYS", "SNODP", "T2M_MIN"],
    "La variable con mayor tendencia": [],
}
HIPOTESIS = ["Está aumentando", "Está disminuyendo", "No está cambiando"]

# Resultados de la simulación de validación (validacion/calibracion.py y validacion/veredictos.py).
VALIDACION = {
    "series": "1,500 a 2,000",
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
</style>
"""


def encabezado(eyebrow: str, titulo: str, lead: str = "", equipo: str = "") -> None:
    parrafo = f'<p class="et-lead">{lead}</p>' if lead else ""
    autoria = f'<div class="et-eyebrow et-equipo">{equipo}</div>' if equipo else ""
    st.html(f'<div class="et-eyebrow">{eyebrow}</div>{autoria}<div class="et-titulo">{titulo}</div>{parrafo}')


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
    """Todas las variables en el punto: reanálisis por POWER más los satélites que respondan."""
    tabla = datos.descargar_power(lat, lon, [v.codigo for v in CATALOGO if v.origen == "power"])
    for v in CATALOGO:
        if v.origen == "gee":
            try:
                serie = datos_gee.serie_del_punto(datos_gee.descargar_cubo(lat, lon, v.codigo), lat, lon)
            except datos.ErrorDeDatos:
                continue  # sin sesión de Earth Engine: el análisis sigue con las demás variables
            if not serie.empty:
                tabla = tabla.join(serie.rename(v.codigo), how="outer")
    return tabla


Periodo = tuple[int, int]  # (año inicial, año final), ambos incluidos


def _recortar(tabla: pd.DataFrame, periodo: Periodo) -> pd.DataFrame:
    return tabla.loc[str(periodo[0]):str(periodo[1])]


@st.cache_data(show_spinner=False)
def cargar_exploracion(lat: float, lon: float, periodo: Periodo) -> pd.DataFrame:
    return caso.escanear(_recortar(cargar_datos(lat, lon), periodo))


@st.cache_data(show_spinner=False)
def cargar_analisis(lat: float, lon: float, codigo: str, periodo: Periodo) -> caso.Interrogatorio:
    return caso.interrogar(_recortar(cargar_datos(lat, lon), periodo)[codigo], POR_CODIGO[codigo])


@st.cache_data(show_spinner=False)
def cargar_region(lat: float, lon: float, codigo: str, lado: int) -> pd.DataFrame:
    if POR_CODIGO[codigo].origen == "gee":
        return datos_gee.recortar(datos_gee.descargar_cubo(lat, lon, codigo), lat, lon, lado)
    return datos.descargar_region(lat, lon, codigo, lado)


@st.cache_data(show_spinner=False)
def cargar_mapa(lat: float, lon: float, codigo: str, lado: int, periodo: Periodo) -> pd.DataFrame:
    return region.mapa_de_tendencias(_recortar(cargar_region(lat, lon, codigo, lado), periodo), POR_CODIGO[codigo])


@st.cache_data(show_spinner=False)
def cargar_analisis_regional(lat: float, lon: float, codigo: str, lado: int, periodo: Periodo) -> caso.Interrogatorio:
    promedio = region.promedio_regional(_recortar(cargar_region(lat, lon, codigo, lado), periodo))
    return caso.interrogar(promedio, POR_CODIGO[codigo])


def elegir_periodo() -> Periodo | None:
    """Barra lateral: años inicial y final del análisis. None si el periodo es demasiado corto."""
    primero, ultimo = datos.ANIO_INICIAL, dt.date.today().year
    desde = int(_parametro("desde")) if _parametro("desde").isdigit() else primero
    hasta = int(_parametro("hasta")) if _parametro("hasta").isdigit() else ultimo
    barra = st.sidebar
    barra.markdown("**Periodo de análisis**")
    periodo = barra.slider("Periodo de análisis", primero, ultimo,
                           (min(max(desde, primero), ultimo), min(max(hasta, primero), ultimo)),
                           label_visibility="collapsed")
    barra.caption("La tendencia depende del periodo elegido. Un periodo corto puede reflejar la "
                  "variabilidad natural de una década y no un cambio de fondo. Las variables de "
                  "satélite empiezan después de 1981 y usan los años disponibles dentro del periodo.")
    if periodo[1] - periodo[0] + 1 < caso.MIN_ANIOS:
        barra.warning(f"Elige al menos {caso.MIN_ANIOS} años: con menos no se puede evaluar una tendencia.")
        return None
    return periodo


@st.cache_data(show_spinner=False)
def buscar(texto: str) -> list[dict]:
    return datos.buscar_lugar(texto)


def _buscar_sitio(donde, etiqueta: str, clave: str) -> dict | None:
    """Campo de búsqueda por nombre y lista de coincidencias."""
    texto = donde.text_input(etiqueta, placeholder="Ej. Guadalajara", key=f"texto_{clave}")
    if not texto.strip():
        return None
    try:
        lugares = buscar(texto.strip())
    except datos.ErrorDeDatos as error:
        donde.error(str(error))
        return None
    if not lugares:
        donde.warning("No se encontró ese lugar. Prueba con otro nombre.")
        return None
    return donde.selectbox("Coincidencias", lugares, format_func=lambda l: l["nombre"], key=f"lista_{clave}")


def plotly(figura, clave: str | None = None) -> None:
    st.plotly_chart(figura, theme=None, width="stretch", config={"displayModeBar": False}, key=clave)


# ------------------------------------------------------------------ fichas de variables

def _tipo(v: Variable) -> str:
    return "Observación satelital" if v.origen == "gee" else "Reanálisis o modelo"


def ficha_variable(v: Variable) -> None:
    """Definición completa de una variable: corta, técnica, producto de datos y referencias."""
    st.markdown(f"#### {v.nombre}")
    st.markdown(f"`{v.codigo}` · {v.categoria} · {_tipo(v)}")
    st.markdown(f"**En pocas palabras.** {v.definicion}")
    st.markdown(f"**Definición técnica.** {v.tecnica}")
    st.markdown(
        f"| Característica | Detalle |\n|---|---|\n"
        f"| Unidad | {v.unidad} |\n"
        f"| Producto de datos | {v.producto} |\n"
        f"| Acceso | {v.fuente} |\n"
        f"| Resolución espacial | {v.resolucion} |\n"
        f"| Periodo analizado | Desde {v.desde}, datos mensuales |"
    )
    if v.aviso:
        st.markdown(f"**Advertencia.** {v.aviso}")
    st.markdown("**Referencias**")
    for clave in v.referencias:
        referencia = REFERENCIAS[clave]
        st.markdown(f"- {referencia.cita} [{referencia.url}]({referencia.url})")


def definicion_emergente(donde, v: Variable) -> None:
    """Definición corta de la variable, con enlace a su ficha completa."""
    with donde.popover("Definición de la variable"):
        st.markdown(f"**{v.nombre}**  \n`{v.codigo}` · {v.unidad}")
        st.write(v.definicion)
        st.caption(f"Fuente: {v.fuente}.")
        st.page_link(PAGINAS["variables"], label="Definición completa y referencias",
                     icon=":material/arrow_forward:", query_params={"var": v.codigo})


# ------------------------------------------------------------------ página: inicio

def pagina_inicio() -> None:
    encabezado(
        "NASA Space Apps 2026 · Earth System Trend Detective",
        "Expediente Tierra",
        "Herramienta para detectar tendencias en variables terrestres.",
        equipo="Equipo C15H25N3O",
    )

    seccion(1, "Empezar un análisis")
    with st.container(border=True):
        uno, dos, tres = st.columns(3)
        tema = uno.radio("Tema de interés", list(TEMAS))
        with dos:
            opciones = [e["nombre"] for e in EJEMPLOS] + ["Otro lugar"]
            elegido = st.selectbox("Sitio de estudio", opciones)
            sitio = EJEMPLOS[opciones.index(elegido)] if elegido != opciones[-1] else None
            if sitio is None:
                sitio = _buscar_sitio(st, "Ciudad, región o país", "inicio")
        with tres:
            hipotesis = st.radio("Hipótesis: ¿qué esperas encontrar?", HIPOTESIS)
            st.caption("Plantear la hipótesis antes de ver los datos evita ajustar la "
                       "interpretación al resultado. Al final se contrasta con el análisis.")
        if st.button("Iniciar el análisis", type="primary", disabled=sitio is None):
            st.session_state["guiado"] = {"sitio": sitio, "tema": tema, "hipotesis": hipotesis}
            st.switch_page(PAGINAS["analisis"])

    seccion(2, "Método")
    pasos = [
        ("Exploración de variables", "Se calcula la tendencia de todas las variables del sitio "
         "y se ordenan por su magnitud estandarizada."),
        ("Distribución espacial", "Un mapa muestra dónde la tendencia es positiva, dónde es "
         "negativa y dónde es significativa."),
        ("Serie de tiempo", "Se elimina el ciclo estacional y se aplican cinco pruebas de "
         "significancia a la tendencia."),
        ("Resultado", "Tasa de cambio con su intervalo de confianza del 95 % y nivel de "
         "evidencia."),
    ]
    for k, (columna, (titulo, texto)) in enumerate(zip(st.columns(4), pasos), start=1):
        columna.html(f'<div class="et-paso"><div class="n">PASO {k}</div>'
                     f'<div class="t">{titulo}</div><p>{texto}</p></div>')

    seccion(3, "Validación del método")
    st.html(
        '<p class="et-nota"><b>Cómo se obtuvieron estas cifras.</b> Se generaron series sintéticas de 45 años '
        "de datos mensuales que, por construcción, no tienen ninguna tendencia, pero sí autocorrelación "
        "(cada mes se parece al anterior), como las series climáticas reales. Cualquier tendencia "
        "«significativa» detectada en ellas es, por definición, un falso positivo. Con un nivel de "
        "significancia de α = 0.05, una prueba bien calibrada debe equivocarse cerca de 5 % de las veces.</p>"
    )
    a, b, c = st.columns(3)
    cifra(a, "Falsos positivos · prueba clásica", VALIDACION["clasica"], "",
          "La prueba de Mann-Kendall estándar supone que los datos son independientes. Aplicada a "
          f"esas series, declaró una tendencia falsa en {VALIDACION['clasica_baja']} de los casos con "
          f"autocorrelación baja (0.3), {VALIDACION['clasica_media']} con autocorrelación media (0.6) y "
          f"{VALIDACION['clasica_alta']} con autocorrelación alta (0.9).")
    cifra(b, "Falsos positivos · este método", VALIDACION["metodo"], "",
          "Dos medidas reducen el error. Primero, cada prueba corrige la autocorrelación antes de "
          "evaluar la tendencia. Segundo, la evidencia solo se califica como «fuerte» o «sólida» si "
          "coinciden al menos cuatro de las cinco pruebas. Con las mismas series, el método completo "
          "dio un falso positivo en esa proporción de casos.")
    cifra(c, "Potencia estadística", VALIDACION["potencia"], "",
          "Corregir no debe volver ciega a la prueba. Al añadir a las series una tendencia real y "
          f"modesta (0.2 desviaciones estándar por década), el método la detectó en {VALIDACION['potencia_baja']} "
          f"de los casos con autocorrelación baja y en {VALIDACION['potencia_media']} con autocorrelación media.")
    st.caption(f"Simulación de Monte Carlo con {VALIDACION['series']} series por escenario. El código "
               "está en la carpeta validacion/ del repositorio.")

    seccion(4, "Datos")
    satelite = sum(v.origen == "gee" for v in CATALOGO)
    a, b, c = st.columns(3)
    cifra(a, "Variables", f"{len(CATALOGO)}", "series mensuales, de 1981 a la fecha")
    cifra(b, "De reanálisis", f"{len(CATALOGO) - satelite}", "MERRA-2 y CERES, vía NASA POWER")
    cifra(c, "De satélite", f"{satelite}", "GPM, MODIS y GRACE, vía Google Earth Engine")
    st.page_link(PAGINAS["variables"], label="Definiciones y referencias de las variables",
                 icon=":material/arrow_forward:")

    seccion(5, "Comparación de dos lugares")
    st.markdown("Un mismo proceso puede producir tendencias opuestas en regiones distintas. La "
                "comparación coloca la misma variable de dos lugares sobre un mismo eje.")
    st.page_link(PAGINAS["comparacion"], label="Ir a la comparación", icon=":material/arrow_forward:")


# ------------------------------------------------------------------ página: variables

def pagina_variables() -> None:
    satelite = sum(v.origen == "gee" for v in CATALOGO)
    encabezado(
        "Catálogo",
        "Variables",
        f"{len(CATALOGO)} variables mensuales: {len(CATALOGO) - satelite} de reanálisis y "
        f"modelos de la NASA y {satelite} de observación satelital. Cada una con su definición, "
        f"el producto de datos del que proviene y sus referencias.",
    )

    consultada = POR_CODIGO.get(_parametro("var"))
    if consultada:
        seccion(None, "Variable consultada")
        with st.container(border=True):
            ficha_variable(consultada)
        st.page_link(PAGINAS["analisis"], label="Volver al análisis", icon=":material/arrow_back:")

    seccion(1, "Resumen")
    st.dataframe(
        pd.DataFrame([{"Variable": v.nombre, "Código": v.codigo, "Unidad": v.unidad,
                       "Tema": v.categoria, "Tipo": _tipo(v), "Desde": v.desde,
                       "Resolución espacial": v.resolucion} for v in CATALOGO]),
        hide_index=True, width="stretch", height=36 * len(CATALOGO) + 40,
        column_config={"Desde": st.column_config.NumberColumn(format="%d")},
    )

    for numero, categoria in enumerate(CATEGORIAS, start=2):
        seccion(numero, categoria)
        for v in (v for v in CATALOGO if v.categoria == categoria):
            with st.expander(f"{v.nombre} · {v.codigo}", expanded=False):
                ficha_variable(v)

    seccion(len(CATEGORIAS) + 2, "Referencias")
    st.markdown("**Datos**")
    usadas = list(dict.fromkeys(clave for v in CATALOGO for clave in v.referencias))
    for clave in sorted(usadas, key=lambda c: REFERENCIAS[c].cita):
        st.markdown(f"- {REFERENCIAS[clave].cita} [{REFERENCIAS[clave].url}]({REFERENCIAS[clave].url})")
    st.markdown("**Métodos estadísticos**")
    for clave in sorted(METODOS, key=lambda c: REFERENCIAS[c].cita):
        st.markdown(f"- {REFERENCIAS[clave].cita} [{REFERENCIAS[clave].url}]({REFERENCIAS[clave].url})")
    st.caption("No se incluyen nubosidad, radiación solar ni albedo: el producto CERES SYN1deg "
               "presenta discontinuidades en esos campos cuando cambian los satélites que lo alimentan.")


# ------------------------------------------------------------------ página: análisis de un lugar

def elegir_sitio() -> dict | None:
    """Barra lateral: sitio de estudio."""
    barra = st.sidebar
    barra.markdown("**Sitio de estudio**")
    modo = barra.radio("Origen", ["Ejemplos", "Buscar un lugar", "Coordenadas"], label_visibility="collapsed")
    if modo == "Ejemplos":
        inicial = int(_parametro("caso")) if _parametro("caso").isdigit() else 0
        elegido = barra.selectbox("Ejemplo", EJEMPLOS, index=min(inicial, len(EJEMPLOS) - 1),
                                  format_func=lambda e: e["nombre"])
        barra.markdown(f"**Pregunta de investigación.** {elegido['pregunta']}")
        return elegido
    if modo == "Buscar un lugar":
        return _buscar_sitio(barra, "Ciudad, región o país", "analisis")
    lat = barra.number_input("Latitud", -90.0, 90.0, 19.43, step=0.5, format="%.2f")
    lon = barra.number_input("Longitud", -180.0, 180.0, -99.13, step=0.5, format="%.2f")
    return {"nombre": f"Punto ({lat:.2f}, {lon:.2f})", "lat": lat, "lon": lon}


def paso_sitio(sitio: dict, tabla_datos: pd.DataFrame) -> None:
    seccion(1, "Sitio de estudio")
    satelites = [v.codigo.split("_")[0] for v in CATALOGO if v.origen == "gee" and v.codigo in tabla_datos]
    texto, mapa = st.columns([3, 2])
    texto.markdown(
        f"Latitud {sitio['lat']:.2f}, longitud {sitio['lon']:.2f}  \n"
        f"Datos mensuales de {tabla_datos.index.min():%Y} a {tabla_datos.index.max():%Y}: "
        f"{sum(v.origen == 'power' for v in CATALOGO)} variables de reanálisis de la NASA"
        + (f" y {len(satelites)} de satélite ({', '.join(satelites)})." if satelites else ".")
    )
    if not satelites:
        texto.caption("Las variables de satélite (GPM, MODIS, GRACE) no están disponibles: hace "
                      "falta una sesión de Google Earth Engine en esta computadora.")
    texto.caption("Cada dato representa una celda de unos 50 km de lado alrededor del punto: "
                  "describe el clima de la zona, no el de un sitio puntual.")
    mapa.map(pd.DataFrame({"lat": [sitio["lat"]], "lon": [sitio["lon"]]}), zoom=3, height=220)


def paso_exploracion(exploracion: pd.DataFrame, preferidas: tuple[str, ...] = ()) -> str | None:
    seccion(2, "Exploración de variables")
    validas = exploracion.dropna(subset=["estandarizada"])
    firmes = int(validas["significativa"].sum())
    st.markdown(
        f"Se calculó la tendencia de **{len(validas)} variables** en este sitio. Para comparar "
        f"variables con unidades distintas, cada tendencia se divide entre la variabilidad "
        f"interanual de esa variable. **{firmes}** tienen una tendencia significativa en esta "
        f"primera revisión. Pasa el cursor sobre una barra para ver la definición de la variable."
    )
    plotly(graficas.exploracion(exploracion))
    st.caption("Al evaluar muchas variables a la vez aumenta la probabilidad de falsos positivos. "
               "Por eso los valores p se ajustan con el procedimiento de Benjamini-Hochberg.")
    with st.expander("Ver como tabla"):
        vista = exploracion.assign(
            tendencia=exploracion["significativa"].map({True: "significativa", False: "no significativa"})
            .where(exploracion["nota"] == "", "—"),
            definicion=exploracion["codigo"].map(lambda c: POR_CODIGO[c].definicion),
        )
        st.dataframe(
            vista[["nombre", "definicion", "unidad", "anios", "pendiente_decada",
                   "estandarizada", "p_ajustada", "tendencia", "nota"]],
            hide_index=True, width="stretch",
            column_config={
                "nombre": "Variable", "definicion": st.column_config.TextColumn("Definición", width="large"),
                "unidad": "Unidad", "anios": "Años",
                "pendiente_decada": st.column_config.NumberColumn("Cambio por década", format="%.3g"),
                "estandarizada": st.column_config.NumberColumn("Tendencia estandarizada", format="%+.2f"),
                "p_ajustada": st.column_config.NumberColumn("p ajustada", format="%.3f"),
                "tendencia": "Tendencia", "nota": "Nota",
            },
        )
    if validas.empty:
        st.warning("Ninguna variable tiene datos suficientes en este punto.")
        return None
    codigos = list(validas["codigo"])
    signo = dict(zip(validas["codigo"], validas["estandarizada"]))
    inicial = next((c for c in (*preferidas, _parametro("var")) if c in codigos), codigos[0])
    selector, definicion = st.columns([5, 2], vertical_alignment="bottom")
    codigo = selector.selectbox(
        "Variable a analizar",
        codigos,
        index=codigos.index(inicial),
        key=f"variable_{inicial}_{len(codigos)}",
        format_func=lambda c: f"{POR_CODIGO[c].nombre} ({'positiva' if signo[c] > 0 else 'negativa'})",
    )
    definicion_emergente(definicion, POR_CODIGO[codigo])
    return codigo


def paso_mapa(sitio: dict, codigo: str, periodo: Periodo) -> int | None:
    """Distribución espacial de la tendencia. Devuelve el lado del recuadro, o None si falló."""
    v = POR_CODIGO[codigo]
    seccion(3, "Distribución espacial de la tendencia")
    lado = st.radio("Tamaño de la región alrededor del sitio", [4, 8], index=1, horizontal=True,
                    format_func=lambda g: f"{g}° × {g}° (unos {g * 111:,} km de lado)")
    try:
        with st.spinner("Descargando los datos de la región..."):
            mapa = cargar_mapa(sitio["lat"], sitio["lon"], codigo, lado, periodo)
    except datos.ErrorDeDatos as error:
        st.warning(f"No se pudo cargar el mapa de la región. {error}")
        return None
    if mapa.empty:
        st.info("Esta variable no se puede medir en ninguna celda de la región.")
        return None
    r = region.resumen(mapa)
    texto = (f"**{v.nombre}** en {r['celdas']} celdas. La tendencia es positiva y significativa "
             f"en **{r['sube']:.0f} %** de la región, y negativa y significativa en **{r['baja']:.0f} %**.")
    if r["sube"] >= 5 and r["baja"] >= 5:
        texto += " **La misma variable presenta tendencias opuestas dentro de la región.**"
    st.markdown(texto)
    plotly(graficas.mapa(mapa, v.unidad, sitio["lat"], sitio["lon"]))
    st.caption("Rojo: tendencia positiva. Azul: negativa. El punto marca las celdas con tendencia "
               "significativa tras el ajuste de Benjamini-Hochberg por comparaciones múltiples.")
    with st.expander("Ver como tabla"):
        st.dataframe(mapa, hide_index=True, width="stretch", column_config={
            "lat": "Latitud", "lon": "Longitud",
            "pendiente_decada": st.column_config.NumberColumn(f"Cambio por década ({v.unidad})", format="%.3g"),
            "p": st.column_config.NumberColumn("p", format="%.3f"),
            "p_ajustada": st.column_config.NumberColumn("p ajustada", format="%.3f"),
            "significativa": "Significativa"})
    return lado


def paso_serie(r: caso.Interrogatorio) -> None:
    v = r.variable
    seccion(4, "Serie de tiempo y pruebas de significancia")
    texto, definicion = st.columns([5, 2], vertical_alignment="center")
    texto.markdown(f"**{v.nombre}** ({v.unidad}). {v.definicion}  \nFuente: {v.fuente}.")
    definicion_emergente(definicion, v)
    if v.aviso:
        st.caption(v.aviso)

    con_tendencia, original = st.tabs(["Anomalías y tendencia", "Serie original"])
    with con_tendencia:
        if r.resolucion == "mensual":
            st.caption("A cada mes se le restó su climatología (el promedio de ese mes del año). "
                       "Así se elimina el ciclo estacional y queda la variación de fondo.")
        else:
            st.caption("Esta variable solo toma valores parte del año, así que se analizan los "
                       "promedios anuales.")
        plotly(graficas.tendencia(r))
    with original:
        st.caption("Promedios mensuales tal como se reciben. La oscilación regular es el ciclo estacional.")
        plotly(graficas.serie_original(r))

    st.markdown("**Pruebas de significancia.** Una tendencia visible en la gráfica puede deberse al "
                "azar. Cada prueba se evalúa con un nivel de significancia α = 0.05, y la tendencia "
                "se considera sólida solo si supera las cinco.")
    for prueba in r.pruebas:
        with st.container(border=True):
            estado, detalle, ayuda = st.columns([1, 7, 2], vertical_alignment="center")
            if prueba.aprobada:
                estado.badge("Pasa", icon=":material/check:", color="green")
            else:
                estado.badge("No pasa", icon=":material/close:", color="gray")
            detalle.markdown(f"**{prueba.nombre}.** {prueba.pregunta}  \n{prueba.resultado}")
            with ayuda.popover("¿Cómo funciona?"):
                st.write(prueba.explicacion)

    if r.mk.corregida:
        ingenuo, corregido = caso.valor_p(r.mk_ingenuo.p), caso.valor_p(r.mk.prueba.p)
        if r.mk_ingenuo.p < 0.05 <= r.mk.prueba.p:
            st.warning(
                f"**Efecto de la autocorrelación.** Sin corregirla, la prueba de Mann-Kendall "
                f"habría declarado significativa esta tendencia ({ingenuo}). Con la corrección "
                f"deja de serlo ({corregido}): era un falso positivo.", icon=":material/warning:")
        else:
            st.caption(f"Efecto de corregir la autocorrelación en Mann-Kendall: sin corregir, "
                       f"{ingenuo}; corregida, {corregido}.")

    st.markdown("**Sensibilidad al periodo.** Cada celda es la tendencia de un periodo distinto. "
                "Si todo el triángulo tiene el mismo color, el signo de la tendencia no depende de "
                "los años elegidos. La esquina superior izquierda es el periodo completo.")
    plotly(graficas.triangulo(r))


def _contraste_de_hipotesis(r: caso.Interrogatorio, hipotesis: str) -> str:
    """Compara la hipótesis planteada antes de ver los datos con el resultado del análisis."""
    firme = r.nivel in ("solida", "fuerte")
    real = HIPOTESIS[2] if not firme else HIPOTESIS[0] if r.sube else HIPOTESIS[1]
    if hipotesis == real:
        return f"**Hipótesis inicial: «{hipotesis.lower()}».** El análisis la respalda."
    dice = "no hay evidencia suficiente de un cambio" if not firme else real.lower()
    return f"**Hipótesis inicial: «{hipotesis.lower()}».** El análisis no la respalda: {dice}."


def paso_resultado(r: caso.Interrogatorio, sitio: dict, hipotesis: str | None = None) -> None:
    seccion(5, "Resultado")
    v = veredicto.redactar(r)
    u = r.variable.unidad
    with st.container(border=True):
        st.html(f'<div class="et-eyebrow">{caso.NIVELES[r.nivel]}</div>'
                f'<div class="et-resultado">{v.titular}</div>')
        a, b, c, d = st.columns(4)
        cifra(a, "Tasa de cambio", caso.numero(r.pendiente_decada, signo=True), f"{u} por década")
        cifra(b, "Cambio acumulado", caso.numero(r.cambio_total, signo=True), f"{u} en {r.anios_de_datos:.0f} años")
        cifra(c, "Pruebas superadas", f"{r.aprobadas}/{caso.N_PRUEBAS}", "pruebas de significancia")
        cifra(d, "Nivel de evidencia", caso.NIVELES_CORTOS[r.nivel], "")
        st.markdown(f"**Sitio.** {sitio['nombre']}.  \n**Tasa de cambio.** {v.cuanto}  \n"
                    f"**Significancia.** {v.evidencia}")
        if v.espera:
            st.markdown(f"**Años de datos necesarios.** {v.espera}")
        if v.relevancia:
            st.markdown(f"**Relevancia práctica.** {v.relevancia}")
        if v.registro_corto:
            st.warning(f"**Registro corto.** {v.registro_corto}", icon=":material/warning:")
        if hipotesis:
            st.markdown(_contraste_de_hipotesis(r, hipotesis))
        ficha, salvedades = st.columns(2)
        ficha.markdown("**Ficha técnica**\n\n| Característica | Detalle |\n|---|---|\n" + "\n".join(
            f"| {nombre} | {detalle} |" for nombre, detalle in veredicto.ficha_tecnica(r)))
        salvedades.markdown("**Supuestos del análisis**\n\n" + "\n".join(f"- {x}" for x in veredicto.SUPUESTOS))
        salvedades.markdown("**Limitaciones**\n\n" + "\n".join(f"- {x}" for x in v.advertencias))
    st.download_button(
        "Descargar el informe",
        veredicto.informe_markdown(r, sitio["nombre"], sitio["lat"], sitio["lon"]),
        file_name=f"informe_{r.variable.codigo}_{sitio['lat']:.2f}_{sitio['lon']:.2f}.md",
        mime="text/markdown",
        icon=":material/download:",
    )


def metodo() -> None:
    with st.expander("Método y validación"):
        st.markdown(
            """
**Datos.** Series mensuales de dos tipos. De reanálisis: [NASA POWER](https://power.larc.nasa.gov/)
distribuye variables de MERRA-2 para cualquier punto del planeta desde 1981. De satélite, por
Google Earth Engine: precipitación de GPM IMERG (desde 1998), índice de vegetación de MODIS
(desde 2000) y almacenamiento de agua terrestre de GRACE (desde 2002). Para la región se usa
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

**Años de datos necesarios para detectar una tendencia.** Fórmula de Weatherhead et al. (1998).
            """
        )
        st.page_link(PAGINAS["variables"], label="Referencias completas", icon=":material/arrow_forward:")


def pagina_analisis() -> None:
    guiado = st.session_state.get("guiado")
    if guiado:
        sitio = guiado["sitio"]
        st.sidebar.markdown(f"**Sitio de estudio**  \n{sitio['nombre']}  \nTema de interés: "
                            f"{guiado['tema'].lower()}.")
        if st.sidebar.button("Cambiar de sitio"):
            del st.session_state["guiado"]
            st.rerun()
    else:
        sitio = elegir_sitio()
    if sitio is None:
        encabezado("Análisis de un lugar", "Elige un sitio de estudio")
        st.info("Escribe un lugar en la barra lateral para empezar.")
        return

    periodo = elegir_periodo()
    encabezado("Análisis de un lugar", sitio["nombre"])
    if periodo is None:
        st.info(f"El periodo elegido es demasiado corto. Amplíalo a {caso.MIN_ANIOS} años o más en la barra lateral.")
        return
    try:
        with st.spinner("Descargando los datos..."):
            tabla_datos = _recortar(cargar_datos(sitio["lat"], sitio["lon"]), periodo)
            exploracion = cargar_exploracion(sitio["lat"], sitio["lon"], periodo)
    except datos.ErrorDeDatos as error:
        st.error(f"No se pudieron obtener los datos. {error}")
        return

    paso_sitio(sitio, tabla_datos)
    preferidas = tuple(TEMAS[guiado["tema"]]) if guiado else ()
    codigo = paso_exploracion(exploracion, preferidas)
    if codigo is None:
        return
    # La hipótesis se planteó sobre la primera variable del tema; si se cambia de variable ya no aplica.
    validas = list(exploracion.dropna(subset=["estandarizada"])["codigo"])
    planteada = next((c for c in preferidas if c in validas), validas[0]) if guiado else None
    hipotesis = guiado["hipotesis"] if guiado and codigo == planteada else None

    lado = paso_mapa(sitio, codigo, periodo)
    alcance = "El punto"
    if lado is not None:
        alcance = st.radio("Serie que se analiza", ["El punto", "El promedio de la región"], horizontal=True)
    try:
        if alcance == "El punto":
            r = cargar_analisis(sitio["lat"], sitio["lon"], codigo, periodo)
        else:
            r = cargar_analisis_regional(sitio["lat"], sitio["lon"], codigo, lado, periodo)
            sitio = {**sitio, "nombre": f"Región de {lado}° × {lado}° alrededor de {sitio['nombre']}"}
    except caso.CasoImposible as error:
        st.warning(str(error))
        return
    paso_serie(r)
    paso_resultado(r, sitio, hipotesis)
    metodo()


# ------------------------------------------------------------------ página: comparación

def _sitio_a_comparar(barra, etiqueta: str, indice: int) -> dict | None:
    opciones = [e["nombre"] for e in EJEMPLOS] + ["Otro lugar"]
    elegido = barra.selectbox(etiqueta, opciones, index=indice)
    if elegido != opciones[-1]:
        return EJEMPLOS[opciones.index(elegido)]
    return _buscar_sitio(barra, f"{etiqueta}: ciudad, región o país", etiqueta)


def pagina_comparacion() -> None:
    barra = st.sidebar
    barra.markdown("**Comparación**")
    titulos = [c[0] for c in COMPARACIONES] + ["Definir mi propia comparación"]
    inicial = int(_parametro("comp")) if _parametro("comp").isdigit() else 0
    elegida = barra.selectbox("Comparación", titulos, index=min(inicial, len(titulos) - 1),
                              label_visibility="collapsed")
    if elegida != titulos[-1]:
        _, i, j, codigo, pregunta = COMPARACIONES[titulos.index(elegida)]
        sitio_a, sitio_b = EJEMPLOS[i], EJEMPLOS[j]
        barra.markdown(f"**Pregunta de investigación.** {pregunta}")
    else:
        sitio_a = _sitio_a_comparar(barra, "Lugar A", 0)
        sitio_b = _sitio_a_comparar(barra, "Lugar B", 3)
    periodo = elegir_periodo()
    if elegida == titulos[-1]:
        if sitio_a is None or sitio_b is None:
            encabezado("Comparación de dos lugares", "Elige dos lugares")
            st.info("Elige los dos lugares en la barra lateral.")
            return
        try:
            with st.spinner("Descargando los datos..."):
                validas = [cargar_exploracion(s["lat"], s["lon"], periodo or (datos.ANIO_INICIAL, dt.date.today().year)).dropna(subset=["estandarizada"])["codigo"]
                           for s in (sitio_a, sitio_b)]
        except datos.ErrorDeDatos as error:
            st.error(f"No se pudieron obtener los datos. {error}")
            return
        comunes = [v.codigo for v in CATALOGO if v.codigo in set(validas[0]) & set(validas[1])]
        if not comunes:
            st.warning("Estos dos lugares no tienen ninguna variable medible en común.")
            return
        codigo = barra.selectbox("Variable", comunes, format_func=lambda c: POR_CODIGO[c].nombre)
    if sitio_a["nombre"] == sitio_b["nombre"]:
        st.info("Elige dos lugares distintos para comparar.")
        return
    if periodo is None:
        encabezado("Comparación de dos lugares", "Periodo demasiado corto")
        st.info(f"Amplía el periodo a {caso.MIN_ANIOS} años o más en la barra lateral.")
        return

    v = POR_CODIGO[codigo]
    nombre_a, nombre_b = sitio_a["nombre"], sitio_b["nombre"]
    encabezado("Comparación de dos lugares", v.nombre, f"{nombre_a} y {nombre_b}, de {periodo[0]} a {periodo[1]}.")
    texto, definicion = st.columns([5, 2], vertical_alignment="center")
    texto.markdown(f"{v.definicion}  \nFuente: {v.fuente}.")
    definicion_emergente(definicion, v)
    alcance = st.radio("Serie que se analiza en cada lugar",
                       ["El punto", "El promedio de la región (8° × 8°)"], horizontal=True)
    try:
        with st.spinner("Analizando los dos lugares..."):
            if alcance == "El punto":
                a = cargar_analisis(sitio_a["lat"], sitio_a["lon"], codigo, periodo)
                b = cargar_analisis(sitio_b["lat"], sitio_b["lon"], codigo, periodo)
            else:
                a = cargar_analisis_regional(sitio_a["lat"], sitio_a["lon"], codigo, 8, periodo)
                b = cargar_analisis_regional(sitio_b["lat"], sitio_b["lon"], codigo, 8, periodo)
    except (caso.CasoImposible, datos.ErrorDeDatos, KeyError) as error:
        st.warning(f"No se puede hacer esta comparación: en uno de los lugares la variable no "
                   f"se puede medir. {error}")
        return

    seccion(1, "Resultado")
    with st.container(border=True):
        st.html(f'<div class="et-resultado">{veredicto.comparar(a, b, nombre_a, nombre_b)}</div>')

    seccion(2, "Series de tiempo")
    plotly(graficas.comparacion(a, b, nombre_a, nombre_b))
    st.caption("La curva es la media móvil de 12 meses de las anomalías (sin ciclo estacional); la "
               "recta es la tendencia lineal. Cada lugar se compara con su propia climatología, por "
               "eso las dos series se centran en cero aunque sus valores absolutos sean distintos.")

    seccion(3, "Distribución espacial")
    mapas = []
    for sitio in (sitio_a, sitio_b):
        try:
            mapas.append(cargar_mapa(sitio["lat"], sitio["lon"], codigo, 8, periodo))
        except datos.ErrorDeDatos:
            mapas.append(pd.DataFrame())
    # Los dos mapas comparten la escala de color: el mismo tono significa el mismo cambio.
    tope = max((float(m["pendiente_decada"].abs().max()) for m in mapas if not m.empty), default=None)
    for columna, r, sitio, mapa in zip(st.columns(2), (a, b), (sitio_a, sitio_b), mapas):
        with columna.container(border=True):
            st.markdown(f"**{sitio['nombre']}**")
            izq, der = st.columns(2)
            cifra(izq, "Tasa de cambio", caso.numero(r.pendiente_decada, signo=True), f"{v.unidad} por década")
            cifra(der, "Nivel de evidencia", caso.NIVELES_CORTOS[r.nivel],
                  f"{r.aprobadas} de {caso.N_PRUEBAS} pruebas superadas")
            st.caption(veredicto.redactar(r).cuanto)
            if not mapa.empty:
                resumen = region.resumen(mapa)
                plotly(graficas.mapa(mapa, v.unidad, sitio["lat"], sitio["lon"], tope=tope, alejar=0.4),
                       clave=f"mapa_{sitio['nombre']}")
                st.caption(f"En la región: tendencia positiva significativa en {resumen['sube']:.0f} % "
                           f"de las celdas y negativa en {resumen['baja']:.0f} %.")
    st.caption("Las cinco pruebas de significancia de cada lugar están en «Análisis de un lugar».")
    metodo()


# ------------------------------------------------------------------ navegación

st.html(ESTILOS)
PAGINAS.update({
    "inicio": st.Page(pagina_inicio, title="Inicio", url_path="inicio", default=True),
    "variables": st.Page(pagina_variables, title="Variables", url_path="variables"),
    "analisis": st.Page(pagina_analisis, title="Análisis de un lugar", url_path="analisis"),
    "comparacion": st.Page(pagina_comparacion, title="Comparación de dos lugares", url_path="comparacion"),
})
st.navigation(list(PAGINAS.values()), position="top").run()
