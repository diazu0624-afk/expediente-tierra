"""Expediente Tierra: abre un caso, interroga a los sospechosos y dicta un veredicto.

Para correrla:  .venv/bin/streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from expediente import caso, datos, graficas, veredicto
from expediente.variables import CATALOGO, POR_CODIGO

st.set_page_config(page_title="Expediente Tierra", page_icon="🔎", layout="wide")

CASOS = [
    {"nombre": "Monterrey, México", "lat": 25.68, "lon": -100.32,
     "pista": "Monterrey vivió una crisis de agua en 2022. ¿Llueve menos que antes, "
              "o el sospechoso es otro?"},
    {"nombre": "Nueva Delhi, India", "lat": 28.61, "lon": 77.21,
     "pista": "Es una de las capitales con el aire más contaminado del mundo. Interroga a "
              "las partículas en el aire."},
    {"nombre": "Pekín, China", "lat": 39.90, "lon": 116.40,
     "pista": "Pekín y Delhi crecieron quemando carbón. Interroga aquí también a las "
              "partículas en el aire: ¿van en la misma dirección que en Delhi?"},
    {"nombre": "Longyearbyen, Svalbard (Ártico)", "lat": 78.22, "lon": 15.65,
     "pista": "El pueblo más al norte del mundo. Se dice que el Ártico se calienta más "
              "rápido que el resto del planeta. Compara su temperatura con la de Monterrey."},
    {"nombre": "Niamey, Níger (Sahel)", "lat": 13.51, "lon": 2.11,
     "pista": "El Sahel sufrió sequías devastadoras en los años ochenta. ¿Qué ha pasado "
              "desde entonces con la humedad del suelo?"},
    {"nombre": "Manaos, Brasil (Amazonía)", "lat": -3.10, "lon": -60.02,
     "pista": "En el corazón de la selva más grande del planeta. ¿Está cambiando la lluvia? "
              "Compárala con lo que pasa en el Sahel."},
]


def _parametro(nombre: str) -> str:
    """Parámetro de la URL (p. ej. ?caso=2&var=AOD_55), para compartir un caso ya abierto."""
    return st.query_params.get(nombre, "")


@st.cache_data(show_spinner=False)
def cargar_datos(lat: float, lon: float) -> pd.DataFrame:
    return datos.descargar_power(lat, lon, [v.codigo for v in CATALOGO])


@st.cache_data(show_spinner=False)
def cargar_sospechosos(lat: float, lon: float) -> pd.DataFrame:
    return caso.escanear(cargar_datos(lat, lon))


@st.cache_data(show_spinner=False)
def cargar_interrogatorio(lat: float, lon: float, codigo: str) -> caso.Interrogatorio:
    return caso.interrogar(cargar_datos(lat, lon)[codigo], POR_CODIGO[codigo])


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
    texto.markdown(
        f"**{lugar['nombre']}**  \n"
        f"Latitud {lugar['lat']:.2f}, longitud {lugar['lon']:.2f}  \n"
        f"Datos mensuales de {tabla_datos.index.min():%Y} a {tabla_datos.index.max():%Y}, "
        f"de la NASA (POWER / MERRA-2)."
    )
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


def paso_interrogatorio(r: caso.Interrogatorio) -> None:
    v = r.variable
    st.subheader("3 · El interrogatorio")
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
                       "de cada año completo.")
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
    st.subheader("4 · El veredicto")
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


def metodo() -> None:
    with st.expander("Cómo trabaja el detective (método y validación)"):
        st.markdown(
            """
**Datos.** Series mensuales de [NASA POWER](https://power.larc.nasa.gov/), que reparte
variables del reanálisis MERRA-2 para cualquier punto del planeta desde 1981.

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
    try:
        r = cargar_interrogatorio(lugar["lat"], lugar["lon"], codigo)
    except caso.CasoImposible as error:
        st.warning(str(error))
        return
    paso_interrogatorio(r)
    paso_veredicto(r, lugar)
    metodo()


main()
