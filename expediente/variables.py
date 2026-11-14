"""Catálogo de variables: los "sospechosos" que el detective puede investigar.

Todas vienen de la API NASA POWER en resolución mensual. Las definiciones están
escritas para alguien de preparatoria: sin jerga y con una imagen concreta.
"""

from __future__ import annotations

from dataclasses import dataclass

MERRA2 = "MERRA-2 (reanálisis de la NASA), vía NASA POWER"
GPM = "GPM IMERG (satélites de la NASA y JAXA), vía Google Earth Engine"
MODIS = "MODIS a bordo del satélite Terra (NASA), vía Google Earth Engine"
GRACE = "GRACE y GRACE-FO (satélites de la NASA y Alemania), vía Google Earth Engine"


@dataclass(frozen=True)
class Variable:
    codigo: str
    nombre: str
    unidad: str
    categoria: str
    definicion: str
    fuente: str = MERRA2
    desde: int = 1981
    # True si tiene sentido hablar de "cambió un X %" (no aplica a °C: 20 °C no es "el doble" de 10 °C).
    relativo: bool = False
    aviso: str = ""
    # "power": modelo MERRA-2 por la API de NASA POWER. "gee": instrumento de satélite por Earth Engine.
    origen: str = "power"


TEMPERATURA = "Temperatura"
AGUA = "Agua y humedad"
AIRE = "Aire y viento"
VEGETACION = "Vegetación"

# No se incluyen nubosidad, radiación solar ni albedo: POWER los toma de CERES SYN1deg, que
# tiene saltos artificiales cuando cambian los satélites (2001, 2017-2018, 2022). Un
# detective de tendencias no puede usar un testigo que cambia su versión.

CATALOGO: tuple[Variable, ...] = (
    # --- Temperatura ---
    Variable("T2M", "Temperatura del aire", "°C", TEMPERATURA,
             "Qué tan caliente está el aire a 2 metros del suelo, la altura a la que vivimos."),
    Variable("T2M_MAX", "Temperatura máxima del mes", "°C", TEMPERATURA,
             "El momento más caluroso de cada mes: la temperatura más alta que se alcanzó."),
    Variable("T2M_MIN", "Temperatura mínima del mes", "°C", TEMPERATURA,
             "El momento más frío de cada mes: la temperatura más baja que se alcanzó."),
    Variable("T2M_RANGE", "Diferencia entre el día y la noche", "°C", TEMPERATURA,
             "Cuántos grados cambia la temperatura entre la parte más cálida y la más fría "
             "de un día típico."),
    Variable("TS", "Temperatura de la superficie", "°C", TEMPERATURA,
             "La temperatura de la \"piel\" del planeta: el suelo, el pavimento o el agua, no el aire."),
    Variable("FROST_DAYS", "Días con helada", "días/mes", TEMPERATURA,
             "Cuántos días del mes la temperatura bajó de 0 °C."),
    Variable("CDD18_3", "Necesidad de enfriar (grados-día)", "grados-día/mes", TEMPERATURA,
             "Suma cuánto calor \"sobra\" por encima de 18.3 °C. Entre más alto, más se "
             "necesita aire acondicionado.", relativo=True),
    Variable("HDD18_3", "Necesidad de calentar (grados-día)", "grados-día/mes", TEMPERATURA,
             "Suma cuánto frío hay por debajo de 18.3 °C. Entre más alto, más se necesita "
             "calefacción.", relativo=True),
    # --- Agua y humedad ---
    Variable("PRECTOTCORR", "Precipitación", "mm/día", AGUA,
             "Lluvia y nieve que caen en promedio cada día.", relativo=True),
    Variable("PRECSNOLAND", "Nevadas", "mm/día", AGUA,
             "La parte de la precipitación que cae en forma de nieve.", relativo=True),
    Variable("SNODP", "Profundidad de la nieve", "cm", AGUA,
             "Grosor de la capa de nieve acumulada sobre el suelo.", relativo=True),
    Variable("GWETTOP", "Humedad del suelo en la superficie", "fracción (0–1)", AGUA,
             "Qué tan mojados están los primeros 5 cm del suelo: 0 es totalmente seco y 1 "
             "es empapado.", relativo=True),
    Variable("GWETROOT", "Humedad del suelo en las raíces", "fracción (0–1)", AGUA,
             "Qué tan mojado está el primer metro del suelo, de donde beben las plantas: "
             "0 es totalmente seco y 1 es empapado.", relativo=True),
    Variable("EVLAND", "Evaporación", "mm/día", AGUA,
             "Agua que pasa del suelo y de las plantas al aire.", relativo=True),
    Variable("QV2M", "Vapor de agua en el aire", "g/kg", AGUA,
             "Cuántos gramos de agua invisible (vapor) hay en cada kilogramo de aire.",
             relativo=True),
    Variable("RH2M", "Humedad relativa", "%", AGUA,
             "Qué tan cerca está el aire de saturarse de vapor: con 100 % se forma niebla o rocío."),
    Variable("T2MDEW", "Punto de rocío", "°C", AGUA,
             "La temperatura a la que el aire tendría que enfriarse para formar rocío. "
             "Sube cuando el aire trae más humedad."),
    Variable("TQV", "Vapor de agua en toda la atmósfera", "kg/m²", AGUA,
             "Toda el agua en forma de vapor que hay sobre el lugar, desde el suelo hasta "
             "el espacio.", relativo=True),
    # --- Aire y viento ---
    Variable("WS10M", "Viento a 10 m", "m/s", AIRE,
             "Rapidez promedio del viento a 10 metros de altura.", relativo=True),
    Variable("WS50M", "Viento a 50 m", "m/s", AIRE,
             "Rapidez promedio del viento a 50 metros, la altura de un aerogenerador pequeño.",
             relativo=True),
    Variable("PS", "Presión del aire", "kPa", AIRE,
             "El peso del aire sobre el lugar.", relativo=True),
    Variable("TO3", "Ozono", "unidades Dobson", AIRE,
             "Cantidad total de ozono sobre el lugar. La capa de ozono nos protege de los "
             "rayos ultravioleta.", relativo=True),
    Variable("TROPPB", "Presión en el techo del clima (tropopausa)", "kPa", AIRE,
             "La tropopausa es el \"techo\" de la capa de aire donde ocurre el clima. Si su "
             "presión baja, ese techo está subiendo.", relativo=True),
    Variable("AOD_55", "Partículas en el aire (aerosoles)", "AOD", AIRE,
             "Qué tanto bloquean la luz el polvo, el humo y la contaminación. Se mide con "
             "un índice llamado AOD: cerca de 0 el aire es muy limpio; arriba de 0.4 ya se "
             "ve turbio.", desde=2001, relativo=True),
    # --- Instrumentos de satélite (observaciones directas, no un modelo) ---
    Variable("GPM_LLUVIA", "Lluvia medida desde satélite (GPM)", "mm/día", AGUA,
             "Lluvia y nieve observadas por una constelación de satélites con radares y "
             "sensores de microondas, afinadas con pluviómetros en tierra.",
             fuente=GPM, desde=1998, relativo=True, origen="gee"),
    Variable("GRACE_AGUA", "Agua almacenada en la tierra (GRACE)", "cm de agua", AGUA,
             "Toda el agua guardada en el lugar: acuíferos, suelo, ríos y nieve. Dos satélites "
             "gemelos la «pesan» midiendo cómo cambia la gravedad. Se expresa en centímetros "
             "de agua de más o de menos respecto al promedio de 2004 a 2009.",
             fuente=GRACE, desde=2002, origen="gee",
             aviso="GRACE ve manchas de unos 300 km: no distingue una ciudad de sus alrededores. "
                   "Faltan los datos de mediados de 2017 a mediados de 2018, entre una misión "
                   "y la siguiente."),
    Variable("MODIS_NDVI", "Verdor de la vegetación (MODIS)", "NDVI", VEGETACION,
             "Qué tan verde y frondosa se ve la superficie desde el satélite. Se mide con un "
             "índice llamado NDVI: cerca de 0 es suelo desnudo; cerca de 1, selva densa.",
             fuente=MODIS, desde=2000, relativo=True, origen="gee"),
)

POR_CODIGO: dict[str, Variable] = {v.codigo: v for v in CATALOGO}
