"""Expediente Tierra: abre un caso, interroga a los sospechosos y dicta un veredicto.

Para correrla:  .venv/bin/streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from expediente import caso, datos, datos_gee, graficas, region, veredicto
from expediente.variables import CATALOGO, POR_CODIGO

st.set_page_config(page_title="Expediente Tierra", page_icon="🔎", layout="wide")

CASOS = [
    {"nombre": "Monterrey, México", "lat": 25.68, "lon": -100.32,
     "pista": "Monterrey vivió una crisis de agua en 2022. ¿Llueve menos que antes? Interroga "
              "a la lluvia y después al agua almacenada en la tierra (GRACE)."},
    {"nombre": "Nueva Delhi, India", "lat": 28.61, "lon": 77.21,
     "pista": "Alrededor de Delhi se riega una de las zonas agrícolas más grandes del mundo. "
              "Interroga al verdor de la vegetación y al agua almacenada: ¿van en la misma "
              "dirección?"},
    {"nombre": "Pekín, China", "lat": 39.90, "lon": 116.40,
     "pista": "Pekín y Delhi crecieron quemando carbón. Interroga en las dos ciudades a las "
              "partículas en el aire: ¿van en la misma dirección?"},
    {"nombre": "Longyearbyen, Svalbard (Ártico)", "lat": 78.22, "lon": 15.65,
     "pista": "El pueblo más al norte del mundo. Se dice que el Ártico se calienta más "
              "rápido que el resto del planeta. Compara su temperatura con la de Monterrey."},
    {"nombre": "Niamey, Níger (Sahel)", "lat": 13.51, "lon": 2.11,
     "pista": "El Sahel sufrió sequías devastadoras en los años ochenta. ¿Se recuperó? Mira en "
              "el mapa el verdor de la vegetación: no toda la región cuenta la misma historia."},
    {"nombre": "Manaos, Brasil (Amazonía)", "lat": -3.10, "lon": -60.02,
     "pista": "En el corazón de la selva más grande del planeta. ¿Está cambiando la lluvia? "
              "Compara lo que dice el modelo (Precipitación) con lo que vio el satélite (GPM)."},
]


# Careos sugeridos: (título, índice del caso A, índice del caso B, variable, pista).
CAREOS = [
    ("Delhi contra Pekín: partículas en el aire", 1, 2, "AOD_55",
     "Dos capitales que crecieron quemando carbón. ¿Su aire va en la misma dirección?"),
    ("Monterrey contra el Ártico: temperatura", 0, 3, "T2M",
     "El planeta se calienta, pero ¿al mismo ritmo en todas partes?"),
    ("Delhi contra el Sahel: agua almacenada", 1, 4, "GRACE_AGUA",
     "Dos regiones secas donde vive muchísima gente. ¿Qué pasa con el agua bajo sus pies?"),
    ("Pekín contra Monterrey: lluvia medida desde satélite", 2, 0, "GPM_LLUVIA",
     "Dos ciudades con escasez de agua. ¿En alguna está cambiando la lluvia?"),
]


def _parametro(nombre: str) -> str:
    """Parámetro de la URL (p. ej. ?caso=2&var=AOD_55), para compartir un caso ya abierto."""
    return st.query_params.get(nombre, "")


@st.cache_data(show_spinner=False)
def cargar_datos(lat: float, lon: float) -> pd.DataFrame:
    """Todas las variables en el punto: MERRA-2 por POWER más los satélites que respondan."""
    tabla = datos.descargar_power(lat, lon, [v.codigo for v in CATALOGO if v.origen == "power"])
    for v in CATALOGO:
        if v.origen == "gee":
            try:
                serie = datos_gee.serie_del_punto(datos_gee.descargar_cubo(lat, lon, v.codigo), lat, lon)
            except datos.ErrorDeDatos:
                continue  # sin sesión de Earth Engine: el caso sigue con las demás variables
            if not serie.empty:
                tabla = tabla.join(serie.rename(v.codigo), how="outer")
    return tabla


@st.cache_data(show_spinner=False)
def cargar_sospechosos(lat: float, lon: float) -> pd.DataFrame:
    return caso.escanear(cargar_datos(lat, lon))


@st.cache_data(show_spinner=False)
def cargar_interrogatorio(lat: float, lon: float, codigo: str) -> caso.Interrogatorio:
    return caso.interrogar(cargar_datos(lat, lon)[codigo], POR_CODIGO[codigo])


@st.cache_data(show_spinner=False)
def cargar_region(lat: float, lon: float, codigo: str, lado: int) -> pd.DataFrame:
    if POR_CODIGO[codigo].origen == "gee":
        return datos_gee.recortar(datos_gee.descargar_cubo(lat, lon, codigo), lat, lon, lado)
    return datos.descargar_region(lat, lon, codigo, lado)


@st.cache_data(show_spinner=False)
def cargar_mapa(lat: float, lon: float, codigo: str, lado: int) -> pd.DataFrame:
    return region.mapa_de_tendencias(cargar_region(lat, lon, codigo, lado), POR_CODIGO[codigo])


@st.cache_data(show_spinner=False)
def cargar_interrogatorio_regional(lat: float, lon: float, codigo: str, lado: int) -> caso.Interrogatorio:
    promedio = region.promedio_regional(cargar_region(lat, lon, codigo, lado))
    return caso.interrogar(promedio, POR_CODIGO[codigo])


@st.cache_data(show_spinner=False)
def buscar(texto: str) -> list[dict]:
    return datos.buscar_lugar(texto)


def elegir_lugar() -> dict | None:
    """Barra lateral: de dónde sale el caso."""
    barra = st.sidebar
    barra.header("Abrir un caso")
    modo = barra.radio("¿Dónde quieres investigar?",
                       ["Casos de demostración", "Buscar un lugar", "Coordenadas"])
    if modo == "Casos de demostración":
        inicial = int(_parametro("caso")) if _parametro("caso").isdigit() else 0
        elegido = barra.selectbox("Caso", CASOS, index=min(inicial, len(CASOS) - 1),
                                  format_func=lambda c: c["nombre"])
        barra.markdown(f"**La pista.** {elegido['pista']}")
        return elegido
    if modo == "Buscar un lugar":
        texto = barra.text_input("Ciudad, región o país", placeholder="Ej. Guadalajara")
        if not texto.strip():
            return None
        try:
            lugares = buscar(texto.strip())
        except datos.ErrorDeDatos as error:
            barra.error(str(error))
            return None
        if not lugares:
            barra.warning("No encontré ese lugar. Prueba con otro nombre.")
            return None
        return barra.selectbox("¿Cuál de estos?", lugares, format_func=lambda l: l["nombre"])
    lat = barra.number_input("Latitud", -90.0, 90.0, 19.43, step=0.5, format="%.2f")
    lon = barra.number_input("Longitud", -180.0, 180.0, -99.13, step=0.5, format="%.2f")
    return {"nombre": f"Punto ({lat:.2f}, {lon:.2f})", "lat": lat, "lon": lon}


def paso_lugar(lugar: dict, tabla_datos: pd.DataFrame) -> None:
    st.subheader("1 · El lugar")
    texto, mapa = st.columns([3, 2])
    satelites = [v.codigo.split("_")[0] for v in CATALOGO if v.origen == "gee" and v.codigo in tabla_datos]
    texto.markdown(
        f"**{lugar['nombre']}**  \n"
        f"Latitud {lugar['lat']:.2f}, longitud {lugar['lon']:.2f}  \n"
        f"Datos mensuales de {tabla_datos.index.min():%Y} a {tabla_datos.index.max():%Y}: "
        f"{sum(v.origen == 'power' for v in CATALOGO)} variables del modelo MERRA-2 de la NASA"
        + (f" y {len(satelites)} de satélite ({', '.join(satelites)})." if satelites else ".")
    )
    if not satelites:
        texto.caption("Los datos de satélite (GPM, MODIS, GRACE) no están disponibles: hace falta "
                      "una sesión de Google Earth Engine en esta computadora.")
    texto.caption("Los datos describen un cuadro de unos 50 km de lado alrededor del punto: "
                  "es el clima de la zona, no el de una calle.")
    mapa.map(pd.DataFrame({"lat": [lugar["lat"]], "lon": [lugar["lon"]]}), zoom=3, height=220)


def paso_sospechosos(sospechosos: pd.DataFrame) -> str | None:
    st.subheader("2 · La rueda de sospechosos")
    validos = sospechosos.dropna(subset=["estandarizada"])
    firmes = int(validos["significativa"].sum())
    st.markdown(
        f"Revisamos **{len(validos)} variables** en este lugar y las ordenamos por la fuerza de "
        f"su tendencia. Para comparar grados con milímetros, cada tendencia se mide contra lo "
        f"que esa variable suele variar de un año a otro. **{firmes}** muestran una tendencia "
        f"significativa en esta primera revisión."
    )
    st.plotly_chart(graficas.sospechosos(sospechosos), theme=None, width="stretch",
                    config={"displayModeBar": False})
    st.caption("Al revisar muchas variables a la vez, alguna parecería culpable por pura "
               "casualidad. Por eso aquí la significancia se exige con una vara más alta "
               "(ajuste de Benjamini-Hochberg).")
    with st.expander("Ver como tabla"):
        vista = sospechosos.assign(tendencia=sospechosos["significativa"].map(
            {True: "significativa", False: "no significativa"}).where(sospechosos["nota"] == "", "—"))
        st.dataframe(
            vista[["nombre", "categoria", "unidad", "anios", "pendiente_decada",
                   "estandarizada", "p_ajustada", "tendencia", "nota"]],
            hide_index=True, width="stretch",
            column_config={
                "nombre": "Variable", "categoria": "Tema", "unidad": "Unidad", "anios": "Años",
                "pendiente_decada": st.column_config.NumberColumn("Cambio por década", format="%.3g"),
                "estandarizada": st.column_config.NumberColumn("En escala común", format="%+.2f"),
                "p_ajustada": st.column_config.NumberColumn("p ajustada", format="%.3f"),
                "tendencia": "Tendencia", "nota": "Nota",
            },
        )
    if validos.empty:
        st.warning("Ninguna variable tiene datos suficientes en este punto.")
        return None
    codigos = list(validos["codigo"])
    rumbo = dict(zip(validos["codigo"], validos["estandarizada"]))
    return st.selectbox(
        "Elige a tu sospechoso",
        codigos,
        index=codigos.index(_parametro("var")) if _parametro("var") in codigos else 0,
        format_func=lambda c: f"{POR_CODIGO[c].nombre} ({'sube' if rumbo[c] > 0 else 'baja'})",
    )


def paso_mapa(lugar: dict, codigo: str) -> int | None:
    """El "dónde": mapa de tendencias de la región. Devuelve el lado del recuadro, o None si falló."""
    v = POR_CODIGO[codigo]
    st.subheader("3 · La escena: ¿dónde cambia?")
    lado = st.radio("Tamaño de la región alrededor del lugar", [4, 8], index=1, horizontal=True,
                    format_func=lambda g: f"{g}° × {g}° (unos {g * 111:,} km de lado)")
    try:
        with st.spinner("Pidiendo la región a la NASA..."):
            mapa = cargar_mapa(lugar["lat"], lugar["lon"], codigo, lado)
    except datos.ErrorDeDatos as error:
        st.warning(f"No se pudo cargar el mapa de la región. {error}")
        return None
    if mapa.empty:
        st.info("Esta variable no se puede medir en ninguna celda de la región.")
        return None
    r = region.resumen(mapa)
    texto = (f"**{v.nombre}** en {r['celdas']} celdas de unos 50 km. Sube de forma significativa "
             f"en **{r['sube']:.0f} %** de la región y baja en **{r['baja']:.0f} %**.")
    if r["sube"] >= 5 and r["baja"] >= 5:
        texto += " **La misma variable va en direcciones opuestas dentro de la misma región.**"
    st.markdown(texto)
    st.plotly_chart(graficas.mapa(mapa, v.unidad, lugar["lat"], lugar["lon"]), theme=None,
                    width="stretch", config={"displayModeBar": False})
    st.caption("Rojo: sube. Azul: baja. El punto marca las celdas donde la tendencia es "
               "significativa después de ajustar por haber revisado todas las celdas a la vez.")
    with st.expander("Ver como tabla"):
        st.dataframe(mapa, hide_index=True, width="stretch", column_config={
            "lat": "Latitud", "lon": "Longitud",
            "pendiente_decada": st.column_config.NumberColumn(f"Cambio por década ({v.unidad})", format="%.3g"),
            "p": st.column_config.NumberColumn("p", format="%.3f"),
            "p_ajustada": st.column_config.NumberColumn("p ajustada", format="%.3f"),
            "significativa": "Significativa"})
    return lado


def paso_interrogatorio(r: caso.Interrogatorio) -> None:
    v = r.variable
    st.subheader("4 · El interrogatorio")
    st.markdown(f"**{v.nombre}** ({v.unidad}). {v.definicion}  \nFuente: {v.fuente}.")
    if v.aviso:
        st.caption(v.aviso)

    con_tendencia, original = st.tabs(["La tendencia", "Los datos tal como llegan"])
    with con_tendencia:
        if r.resolucion == "mensual":
            st.caption("A cada mes se le restó lo normal para ese mes del año. Así desaparece "
                       "el vaivén de las estaciones y queda a la vista el cambio de fondo.")
        else:
            st.caption("Este fenómeno solo ocurre parte del año, así que se analiza el promedio "
                       "de cada año.")
        st.plotly_chart(graficas.tendencia(r), theme=None, width="stretch",
                        config={"displayModeBar": False})
    with original:
        st.caption("Cada punto es el promedio de un mes. El sube y baja regular son las estaciones.")
        st.plotly_chart(graficas.serie_original(r), theme=None, width="stretch",
                        config={"displayModeBar": False})

    st.markdown("**Las cinco pruebas.** Una tendencia que se ve en la gráfica todavía puede ser "
                "casualidad. Solo la que resiste las cinco se considera sólida.")
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
                f"**La trampa de la memoria.** Sin corregirla, Mann-Kendall habría declarado "
                f"esta tendencia significativa ({ingenuo}). Al quitar la memoria de la serie "
                f"deja de serlo ({corregido}): era un espejismo.", icon=":material/warning:")
        else:
            st.caption(f"Efecto de corregir la memoria en Mann-Kendall: sin corregir, {ingenuo}; "
                       f"corregida, {corregido}.")

    st.markdown("**¿Depende de las fechas?** Cada cuadro es la tendencia de un periodo distinto. "
                "Si todo el triángulo es de un solo color, la tendencia no depende de dónde se "
                "empiece a contar. La esquina superior izquierda es el periodo completo.")
    st.plotly_chart(graficas.triangulo(r), theme=None, width="stretch",
                    config={"displayModeBar": False})


def paso_veredicto(r: caso.Interrogatorio, lugar: dict) -> None:
    st.subheader("5 · El veredicto")
    v = veredicto.redactar(r)
    u = r.variable.unidad
    with st.container(border=True):
        st.markdown(f"### {v.titular}")
        a, b, c, d = st.columns(4)
        a.metric("Cambio por década", f"{caso.numero(r.pendiente_decada, signo=True)} {u}")
        b.metric(f"Cambio en {r.anios_de_datos:.0f} años", f"{caso.numero(r.cambio_total, signo=True)} {u}")
        c.metric("Pruebas superadas", f"{r.aprobadas} de {caso.N_PRUEBAS}")
        d.metric("Evidencia", caso.NIVELES_CORTOS[r.nivel])
        st.markdown(f"**Dónde.** {lugar['nombre']}.  \n**Cuánto.** {v.cuanto}  \n**Qué tan seguro.** {v.evidencia}")
        if v.espera:
            st.markdown(f"**Cuánto habría que esperar.** {v.espera}")
        with st.expander("Límites de este expediente"):
            for advertencia in v.advertencias:
                st.markdown(f"- {advertencia}")
    st.download_button(
        "Descargar el expediente",
        veredicto.expediente_markdown(r, lugar["nombre"], lugar["lat"], lugar["lon"]),
        file_name=f"expediente_{r.variable.codigo}_{lugar['lat']:.2f}_{lugar['lon']:.2f}.md",
        mime="text/markdown",
        icon=":material/download:",
    )


def _lugar_del_careo(barra, etiqueta: str, indice: int) -> dict | None:
    """Selector de un lugar para el careo: un caso de demostración o una búsqueda libre."""
    opciones = [c["nombre"] for c in CASOS] + ["Buscar otro lugar..."]
    elegido = barra.selectbox(etiqueta, opciones, index=indice)
    if elegido != opciones[-1]:
        return CASOS[opciones.index(elegido)]
    texto = barra.text_input(f"{etiqueta}: ciudad, región o país", key=f"busqueda_{etiqueta}")
    if not texto.strip():
        return None
    try:
        lugares = buscar(texto.strip())
    except datos.ErrorDeDatos as error:
        barra.error(str(error))
        return None
    if not lugares:
        barra.warning("No encontré ese lugar. Prueba con otro nombre.")
        return None
    return barra.selectbox(f"{etiqueta}: ¿cuál de estos?", lugares, format_func=lambda l: l["nombre"])


def pagina_careo() -> None:
    """Dos lugares, una variable: ¿van en la misma dirección?"""
    barra = st.sidebar
    titulos = [c[0] for c in CAREOS] + ["Armar mi propio careo"]
    inicial = int(_parametro("careo")) if _parametro("careo").isdigit() else 0
    elegido = barra.selectbox("Careo", titulos, index=min(inicial, len(titulos) - 1))
    if elegido != titulos[-1]:
        _, i, j, codigo, pista = CAREOS[titulos.index(elegido)]
        lugar_a, lugar_b = CASOS[i], CASOS[j]
        barra.markdown(f"**La pista.** {pista}")
    else:
        lugar_a = _lugar_del_careo(barra, "Lugar A", 0)
        lugar_b = _lugar_del_careo(barra, "Lugar B", 3)
        if lugar_a is None or lugar_b is None:
            st.info("Elige los dos lugares en la barra lateral.")
            return
        try:
            with st.spinner("Pidiendo los datos a la NASA..."):
                validos = [cargar_sospechosos(l["lat"], l["lon"]).dropna(subset=["estandarizada"])["codigo"]
                           for l in (lugar_a, lugar_b)]
        except datos.ErrorDeDatos as error:
            st.error(f"No se pudieron obtener los datos. {error}")
            return
        comunes = [v.codigo for v in CATALOGO if v.codigo in set(validos[0]) & set(validos[1])]
        if not comunes:
            st.warning("Estos dos lugares no tienen ninguna variable medible en común.")
            return
        codigo = barra.selectbox("Variable", comunes, format_func=lambda c: POR_CODIGO[c].nombre)
    if lugar_a["nombre"] == lugar_b["nombre"]:
        st.info("Elige dos lugares distintos para el careo.")
        return

    v = POR_CODIGO[codigo]
    a_nombre, b_nombre = lugar_a["nombre"], lugar_b["nombre"]
    st.subheader(f"Careo: {v.nombre}")
    st.markdown(f"**{a_nombre}** frente a **{b_nombre}**.  \n{v.definicion} Fuente: {v.fuente}.")
    alcance = st.radio("¿A quién interrogamos en cada lugar?",
                       ["El punto", "El promedio de la región (8° × 8°)"], horizontal=True)
    try:
        with st.spinner("Interrogando a los dos lugares..."):
            if alcance == "El punto":
                a = cargar_interrogatorio(lugar_a["lat"], lugar_a["lon"], codigo)
                b = cargar_interrogatorio(lugar_b["lat"], lugar_b["lon"], codigo)
            else:
                a = cargar_interrogatorio_regional(lugar_a["lat"], lugar_a["lon"], codigo, 8)
                b = cargar_interrogatorio_regional(lugar_b["lat"], lugar_b["lon"], codigo, 8)
    except (caso.CasoImposible, datos.ErrorDeDatos, KeyError) as error:
        st.warning(f"No se puede hacer este careo: en uno de los lugares la variable no se puede medir. {error}")
        return

    with st.container(border=True):
        st.markdown(f"### {veredicto.comparar(a, b, a_nombre, b_nombre)}")
    st.plotly_chart(graficas.careo(a, b, a_nombre, b_nombre), theme=None, width="stretch",
                    config={"displayModeBar": False})
    st.caption("La curva es el promedio de 12 meses, ya sin el vaivén de las estaciones; la recta es "
               "la tendencia. Cada lugar se compara con su propio valor normal, así que las dos "
               "curvas parten de cero aunque un lugar sea mucho más caliente o lluvioso que el otro.")

    mapas = []
    for lugar in (lugar_a, lugar_b):
        try:
            mapas.append(cargar_mapa(lugar["lat"], lugar["lon"], codigo, 8))
        except datos.ErrorDeDatos:
            mapas.append(pd.DataFrame())
    # Los dos mapas comparten la escala de color: el mismo tono significa el mismo cambio.
    tope = max((float(m["pendiente_decada"].abs().max()) for m in mapas if not m.empty), default=None)
    for columna, r, lugar, mapa in zip(st.columns(2), (a, b), (lugar_a, lugar_b), mapas):
        with columna.container(border=True):
            st.markdown(f"**{lugar['nombre']}**")
            izq, der = st.columns(2)
            izq.metric("Cambio por década", f"{caso.numero(r.pendiente_decada, signo=True)} {v.unidad}")
            der.metric("Evidencia", f"{caso.NIVELES_CORTOS[r.nivel]} ({r.aprobadas} de {caso.N_PRUEBAS})")
            st.caption(veredicto.redactar(r).cuanto)
            if not mapa.empty:
                resumen = region.resumen(mapa)
                st.plotly_chart(graficas.mapa(mapa, v.unidad, lugar["lat"], lugar["lon"], tope=tope, alejar=0.4),
                                theme=None, width="stretch", config={"displayModeBar": False},
                                key=f"mapa_{lugar['nombre']}")
                st.caption(f"En la región: sube de forma significativa en {resumen['sube']:.0f} % "
                           f"de las celdas y baja en {resumen['baja']:.0f} %.")
    st.caption("Para ver las cinco pruebas de cada lugar, ábrelo en «Investigar un lugar».")
    metodo()


def metodo() -> None:
    with st.expander("Cómo trabaja el detective (método y validación)"):
        st.markdown(
            """
**Datos.** Series mensuales de dos tipos. Del modelo: [NASA POWER](https://power.larc.nasa.gov/)
reparte variables del reanálisis MERRA-2 para cualquier punto del planeta desde 1981. De
satélite, por Google Earth Engine: lluvia de GPM IMERG (desde 1998), verdor de la vegetación
de MODIS (desde 2000) y agua almacenada de GRACE (desde 2002). Para la
región se pide cada celda de unos 50 km dentro del recuadro y se promedia según su área.

**Cuánto cambia.** La pendiente de una recta ajustada por mínimos cuadrados, con un rango
creíble al 95 % obtenido simulando 2,000 series con el mismo ruido y la misma memoria.

**Las cinco pruebas.**
1. Mann-Kendall con la memoria de la serie corregida (Zhang et al., 2000; Wang y Swail, 2001).
2. Prueba t de la pendiente con tamaño de muestra efectivo (Santer et al., 2000).
3. Intervalo de confianza por simulación: ¿deja fuera al cero?
4. La misma tendencia con promedios anuales (o quitando un año a la vez).
5. La dirección se mantiene en al menos 80 % de los periodos posibles.

**Por qué corregir la memoria.** Probamos al detective con series inventadas que no tienen
ninguna tendencia pero sí memoria, como los datos reales. La prueba de Mann-Kendall sin
corregir acusó falsamente entre 13 % y 63 % de las veces. Las pruebas corregidas se
equivocaron entre 3 % y 8 %, cerca del 5 % que promete un nivel de confianza de 95 %.
El veredicto completo llegó a «evidencia fuerte» o «sólida» en 3 a 5 de cada 100 series
sin tendencia, y en 78 a 98 de cada 100 cuando la tendencia sí existía (300 a 400 series
por escenario; los detalles están en la carpeta `validacion/`).

**Años necesarios para detectar una tendencia.** Fórmula de Weatherhead et al. (1998).
            """
        )


def main() -> None:
    st.title("Expediente Tierra")
    st.markdown("Elige un lugar del planeta. Descubre **qué** está cambiando ahí, **cuánto**, "
                "y si la evidencia aguanta un interrogatorio.")
    modo = st.sidebar.radio("¿Qué quieres hacer?", ["Investigar un lugar", "Careo: comparar dos lugares"],
                            index=1 if _parametro("careo") else 0)
    if modo != "Investigar un lugar":
        pagina_careo()
        return
    lugar = elegir_lugar()
    if lugar is None:
        st.info("Escribe un lugar en la barra lateral para abrir un caso.")
        return

    try:
        with st.spinner("Pidiendo los datos a la NASA..."):
            tabla_datos = cargar_datos(lugar["lat"], lugar["lon"])
            sospechosos = cargar_sospechosos(lugar["lat"], lugar["lon"])
    except datos.ErrorDeDatos as error:
        st.error(f"No se pudieron obtener los datos. {error}")
        return

    paso_lugar(lugar, tabla_datos)
    codigo = paso_sospechosos(sospechosos)
    if codigo is None:
        return
    lado = paso_mapa(lugar, codigo)
    alcance = "El punto"
    if lado is not None:
        alcance = st.radio("¿A quién interrogamos?", ["El punto", "El promedio de toda la región"],
                           horizontal=True)
    try:
        if alcance == "El punto":
            r = cargar_interrogatorio(lugar["lat"], lugar["lon"], codigo)
        else:
            r = cargar_interrogatorio_regional(lugar["lat"], lugar["lon"], codigo, lado)
            lugar = {**lugar, "nombre": f"Región de {lado}° × {lado}° alrededor de {lugar['nombre']}"}
    except caso.CasoImposible as error:
        st.warning(str(error))
        return
    paso_interrogatorio(r)
    paso_veredicto(r, lugar)
    metodo()


main()
