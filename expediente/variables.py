"""Catálogo de variables y de referencias bibliográficas.

Cada variable tiene dos definiciones: una corta, para alguien de preparatoria, y una
técnica, con el producto de datos del que sale y sus referencias. Las definiciones
técnicas de las variables de NASA POWER siguen la ficha oficial de cada parámetro
(https://power.larc.nasa.gov/api/system/manager/parameters/<CODIGO>).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Referencia:
    cita: str
    url: str


def _doi(doi: str) -> str:
    return f"https://doi.org/{doi}"


REFERENCIAS: dict[str, Referencia] = {
    # --- Reanálisis MERRA-2 ---
    "gelaro2017": Referencia(
        "Gelaro, R., McCarty, W., Suárez, M. J., et al. (2017). The Modern-Era Retrospective "
        "Analysis for Research and Applications, Version 2 (MERRA-2). Journal of Climate, "
        "30(14), 5419–5454.", _doi("10.1175/JCLI-D-16-0758.1")),
    "gmao_slv": Referencia(
        "Global Modeling and Assimilation Office (2015). MERRA-2 tavg1_2d_slv_Nx: 2d, 1-Hourly, "
        "Time-Averaged, Single-Level, Assimilation, Single-Level Diagnostics V5.12.4. Goddard "
        "Earth Sciences Data and Information Services Center (GES DISC).",
        _doi("10.5067/VJAFPLI1CSIV")),
    "gmao_lnd": Referencia(
        "Global Modeling and Assimilation Office (2015). MERRA-2 tavg1_2d_lnd_Nx: 2d, 1-Hourly, "
        "Time-Averaged, Single-Level, Assimilation, Land Surface Diagnostics V5.12.4. GES DISC.",
        _doi("10.5067/RKPHT8KC1Y1T")),
    "gmao_flx": Referencia(
        "Global Modeling and Assimilation Office (2015). MERRA-2 tavg1_2d_flx_Nx: 2d, 1-Hourly, "
        "Time-Averaged, Single-Level, Assimilation, Surface Flux Diagnostics V5.12.4. GES DISC.",
        _doi("10.5067/7MCPBJ41Y0K6")),
    "reichle2017a": Referencia(
        "Reichle, R. H., Liu, Q., Koster, R. D., Draper, C. S., Mahanama, S. P. P., & Partyka, "
        "G. S. (2017). Land surface precipitation in MERRA-2. Journal of Climate, 30(5), "
        "1643–1664.", _doi("10.1175/JCLI-D-16-0570.1")),
    "reichle2017b": Referencia(
        "Reichle, R. H., Draper, C. S., Liu, Q., et al. (2017). Assessment of MERRA-2 land "
        "surface hydrology estimates. Journal of Climate, 30(8), 2937–2960.",
        _doi("10.1175/JCLI-D-16-0720.1")),
    "wargan2017": Referencia(
        "Wargan, K., Labow, G., Frith, S., Pawson, S., Livesey, N., & Partyka, G. (2017). "
        "Evaluation of the ozone fields in NASA's MERRA-2 reanalysis. Journal of Climate, "
        "30(8), 2961–2988.", _doi("10.1175/JCLI-D-16-0699.1")),
    "power": Referencia(
        "NASA Langley Research Center. Prediction Of Worldwide Energy Resources (POWER) "
        "Project: Data Methodology. Consultado en noviembre de 2026.",
        "https://power.larc.nasa.gov/docs/methodology/"),
    # --- CERES SYN1deg (aerosoles) ---
    "rutan2015": Referencia(
        "Rutan, D. A., Kato, S., Doelling, D. R., et al. (2015). CERES synoptic product: "
        "Methodology and validation of surface radiant flux. Journal of Atmospheric and "
        "Oceanic Technology, 32(6), 1121–1143.", _doi("10.1175/JTECH-D-14-00165.1")),
    "collins2001": Referencia(
        "Collins, W. D., Rasch, P. J., Eaton, B. E., Khattatov, B. V., Lamarque, J.-F., & "
        "Zender, C. S. (2001). Simulating aerosols using a chemical transport model with "
        "assimilation of satellite aerosol retrievals: Methodology for INDOEX. Journal of "
        "Geophysical Research: Atmospheres, 106(D7), 7313–7336.", _doi("10.1029/2000JD900507")),
    # --- Instrumentos de satélite ---
    "huffman2023": Referencia(
        "Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., & Tan, J. (2023). GPM "
        "IMERG Final Precipitation L3 1 month 0.1 degree x 0.1 degree V07. GES DISC.",
        _doi("10.5067/GPM/IMERG/3B-MONTH/07")),
    "huffman2020": Referencia(
        "Huffman, G. J., Bolvin, D. T., Braithwaite, D., et al. (2020). Integrated "
        "Multi-satellite Retrievals for the Global Precipitation Measurement (GPM) mission "
        "(IMERG). En Satellite Precipitation Measurement (pp. 343–353). Springer.",
        _doi("10.1007/978-3-030-24568-9_19")),
    "didan2021": Referencia(
        "Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061. "
        "NASA EOSDIS Land Processes DAAC.", _doi("10.5067/MODIS/MOD13A3.061")),
    "huete2002": Referencia(
        "Huete, A., Didan, K., Miura, T., Rodriguez, E. P., Gao, X., & Ferreira, L. G. (2002). "
        "Overview of the radiometric and biophysical performance of the MODIS vegetation "
        "indices. Remote Sensing of Environment, 83(1–2), 195–213.",
        _doi("10.1016/S0034-4257(02)00096-2")),
    "watkins2015": Referencia(
        "Watkins, M. M., Wiese, D. N., Yuan, D.-N., Boening, C., & Landerer, F. W. (2015). "
        "Improved methods for observing Earth's time variable mass distribution with GRACE "
        "using spherical cap mascons. Journal of Geophysical Research: Solid Earth, 120(4), "
        "2648–2671.", _doi("10.1002/2014JB011547")),
    "wiese2016": Referencia(
        "Wiese, D. N., Landerer, F. W., & Watkins, M. M. (2016). Quantifying and reducing "
        "leakage errors in the JPL RL05M GRACE mascon solution. Water Resources Research, "
        "52(9), 7490–7502.", _doi("10.1002/2016WR019344")),
    "wiese2023": Referencia(
        "Wiese, D. N., et al. (2023). JPL GRACE and GRACE-FO Mascon Ocean, Ice, and Hydrology "
        "Equivalent Water Height CRI Filtered, Release 06.3 Version 04. NASA PO.DAAC.",
        _doi("10.5067/TEMSC-3JC634")),
    "gorelick2017": Referencia(
        "Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). "
        "Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote "
        "Sensing of Environment, 202, 18–27.", _doi("10.1016/j.rse.2017.06.031")),
    # --- Métodos estadísticos ---
    "mann1945": Referencia(
        "Mann, H. B. (1945). Nonparametric tests against trend. Econometrica, 13(3), 245–259.",
        _doi("10.2307/1907187")),
    "sen1968": Referencia(
        "Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. "
        "Journal of the American Statistical Association, 63(324), 1379–1389.",
        _doi("10.1080/01621459.1968.10480934")),
    "zhang2000": Referencia(
        "Zhang, X., Vincent, L. A., Hogg, W. D., & Niitsoo, A. (2000). Temperature and "
        "precipitation trends in Canada during the 20th century. Atmosphere-Ocean, 38(3), "
        "395–429.", _doi("10.1080/07055900.2000.9649654")),
    "wang2001": Referencia(
        "Wang, X. L., & Swail, V. R. (2001). Changes of extreme wave heights in Northern "
        "Hemisphere oceans and related atmospheric circulation regimes. Journal of Climate, "
        "14(10), 2204–2221.",
        "https://doi.org/10.1175/1520-0442%282001%29014%3C2204%3ACOEWHI%3E2.0.CO%3B2"),
    "santer2000": Referencia(
        "Santer, B. D., Wigley, T. M. L., Boyle, J. S., et al. (2000). Statistical significance "
        "of trends and trend differences in layer-average atmospheric temperature time "
        "series. Journal of Geophysical Research: Atmospheres, 105(D6), 7337–7356.",
        _doi("10.1029/1999JD901105")),
    "weatherhead1998": Referencia(
        "Weatherhead, E. C., Reinsel, G. C., Tiao, G. C., et al. (1998). Factors affecting the "
        "detection of trends: Statistical considerations and applications to environmental "
        "data. Journal of Geophysical Research: Atmospheres, 103(D14), 17149–17161.",
        _doi("10.1029/98JD00995")),
    "benjamini1995": Referencia(
        "Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A "
        "practical and powerful approach to multiple testing. Journal of the Royal "
        "Statistical Society: Series B, 57(1), 289–300.",
        _doi("10.1111/j.2517-6161.1995.tb02031.x")),
}

METODOS = ("mann1945", "sen1968", "zhang2000", "wang2001", "santer2000", "weatherhead1998",
           "benjamini1995")

MERRA2 = "MERRA-2 (reanálisis de la NASA), vía NASA POWER"
SYN1DEG = "CERES SYN1deg (NASA), vía NASA POWER"
GPM = "GPM IMERG (satélites de la NASA y JAXA), vía Google Earth Engine"
MODIS = "MODIS a bordo del satélite Terra (NASA), vía Google Earth Engine"
GRACE = "GRACE y GRACE-FO (satélites de la NASA y Alemania), vía Google Earth Engine"

RES_MERRA2 = "0.5° de latitud × 0.625° de longitud (unos 50 km)"
_SLV = ("gelaro2017", "gmao_slv", "power")
_LND = ("gelaro2017", "reichle2017b", "gmao_lnd", "power")


@dataclass(frozen=True)
class Variable:
    codigo: str
    nombre: str
    unidad: str
    categoria: str
    definicion: str  # corta, en lenguaje sencillo
    tecnica: str  # definición técnica
    producto: str  # de qué producto de datos y de qué campo sale
    referencias: tuple[str, ...]
    fuente: str = MERRA2
    resolucion: str = RES_MERRA2
    desde: int = 1981
    # True si tiene sentido hablar de "cambió un X %" (no aplica a °C: 20 °C no es "el doble" de 10 °C).
    relativo: bool = False
    aviso: str = ""
    # "power": NASA POWER (reanálisis). "gee": instrumento de satélite por Earth Engine.
    origen: str = "power"


TEMPERATURA = "Temperatura"
HIDRO = "Hidrología"
HUMEDAD = "Humedad atmosférica"
AIRE = "Aire y viento"
VEGETACION = "Vegetación"
CATEGORIAS = (TEMPERATURA, HIDRO, HUMEDAD, AIRE, VEGETACION)

# No se incluyen nubosidad, radiación solar ni albedo: POWER los toma de CERES SYN1deg, que
# tiene saltos artificiales cuando cambian los satélites (2001, 2017-2018, 2022).

CATALOGO: tuple[Variable, ...] = (
    # --- Temperatura ---
    Variable("T2M", "Temperatura del aire", "°C", TEMPERATURA,
             "Qué tan caliente está el aire a 2 metros del suelo, la altura a la que vivimos.",
             "Temperatura media del aire (bulbo seco) a 2 m sobre la superficie. Promedio "
             "mensual de los valores horarios.",
             "MERRA-2, campo T2M de la colección de superficie tavg1_2d_slv_Nx.", _SLV),
    Variable("T2M_MAX", "Temperatura máxima del mes", "°C", TEMPERATURA,
             "El momento más caluroso de cada mes: la temperatura más alta que se alcanzó.",
             "Máximo de la temperatura horaria del aire a 2 m dentro del mes.",
             "Calculada por NASA POWER a partir del campo T2M horario de MERRA-2.", _SLV),
    Variable("T2M_MIN", "Temperatura mínima del mes", "°C", TEMPERATURA,
             "El momento más frío de cada mes: la temperatura más baja que se alcanzó.",
             "Mínimo de la temperatura horaria del aire a 2 m dentro del mes.",
             "Calculada por NASA POWER a partir del campo T2M horario de MERRA-2.", _SLV),
    Variable("T2M_RANGE", "Amplitud térmica diaria", "°C", TEMPERATURA,
             "Cuántos grados cambia la temperatura entre la parte más cálida y la más fría "
             "de un día típico.",
             "Diferencia entre la temperatura horaria máxima y mínima del aire a 2 m en cada "
             "día, promediada sobre el mes (amplitud térmica diurna).",
             "Calculada por NASA POWER a partir del campo T2M horario de MERRA-2.", _SLV),
    Variable("TS", "Temperatura de la superficie", "°C", TEMPERATURA,
             "La temperatura de la \"piel\" del planeta: el suelo, el pavimento o el agua, no el aire.",
             "Temperatura radiativa media de la superficie terrestre (skin temperature).",
             "MERRA-2, campo TS de la colección tavg1_2d_slv_Nx.", _SLV),
    Variable("FROST_DAYS", "Días con helada", "días/mes", TEMPERATURA,
             "Cuántos días del mes hubo helada: el aire se enfrió hasta formar escarcha.",
             "Número de días del mes en que la temperatura a 2 m desciende hasta el punto de "
             "rocío y ambos quedan por debajo de 0 °C.",
             "Calculada por NASA POWER a partir de los campos T2M y T2MDEW de MERRA-2.", _SLV),
    Variable("CDD18_3", "Grados-día de refrigeración", "grados-día/mes", TEMPERATURA,
             "Suma cuánto calor \"sobra\" por encima de 18.3 °C. Entre más alto, más se "
             "necesita aire acondicionado.",
             "Acumulación mensual de los grados en que la temperatura media diaria supera el "
             "umbral de 18.3 °C (65 °F). Indicador estándar de demanda de enfriamiento.",
             "Calculada por NASA POWER a partir de la temperatura a 2 m de MERRA-2.", _SLV,
             relativo=True),
    Variable("HDD18_3", "Grados-día de calefacción", "grados-día/mes", TEMPERATURA,
             "Suma cuánto frío hay por debajo de 18.3 °C. Entre más alto, más se necesita "
             "calefacción.",
             "Acumulación mensual de los grados en que la temperatura media diaria queda por "
             "debajo del umbral de 18.3 °C (65 °F). Indicador estándar de demanda de calefacción.",
             "Calculada por NASA POWER a partir de la temperatura a 2 m de MERRA-2.", _SLV,
             relativo=True),
    # --- Hidrología y humedad atmosférica ---
    Variable("PRECTOTCORR", "Precipitación (reanálisis)", "mm/día", HIDRO,
             "Lluvia y nieve que caen en promedio cada día, según el modelo de la NASA.",
             "Precipitación total media en superficie del reanálisis MERRA-2, corregida de "
             "sesgo con observaciones de pluviómetros y satélites.",
             "MERRA-2, campo PRECTOTCORR de la colección de flujos tavg1_2d_flx_Nx.",
             ("gelaro2017", "reichle2017a", "gmao_flx", "power"), relativo=True),
    Variable("PRECSNOLAND", "Nevadas", "mm/día", HIDRO,
             "La parte de la precipitación que cae en forma de nieve.",
             "Precipitación en forma de nieve sobre tierra, en equivalente de agua líquida.",
             "MERRA-2, campo PRECSNOLAND de la colección de superficie terrestre tavg1_2d_lnd_Nx.",
             _LND, relativo=True),
    Variable("SNODP", "Profundidad de la nieve", "cm", HIDRO,
             "Grosor de la capa de nieve acumulada sobre el suelo.",
             "Espesor del manto de nieve sobre tierra.",
             "MERRA-2, campo SNODP de la colección tavg1_2d_lnd_Nx.", _LND, relativo=True),
    Variable("GWETTOP", "Humedad del suelo superficial", "fracción (0–1)", HIDRO,
             "Qué tan mojados están los primeros 5 cm del suelo: 0 es totalmente seco y 1 "
             "es empapado.",
             "Grado de saturación de agua en los 5 cm superiores del suelo: 0 corresponde a "
             "suelo completamente seco y 1 a suelo saturado.",
             "MERRA-2, campo GWETTOP de la colección tavg1_2d_lnd_Nx.", _LND, relativo=True),
    Variable("GWETROOT", "Humedad del suelo en la zona de raíces", "fracción (0–1)", HIDRO,
             "Qué tan mojado está el primer metro del suelo, de donde beben las plantas: "
             "0 es totalmente seco y 1 es empapado.",
             "Grado de saturación de agua en la zona radicular, aproximadamente el primer "
             "metro de suelo: 0 corresponde a suelo completamente seco y 1 a suelo saturado.",
             "MERRA-2, campo GWETROOT de la colección tavg1_2d_lnd_Nx.", _LND, relativo=True),
    Variable("EVLAND", "Evaporación", "mm/día", HIDRO,
             "Agua que pasa del suelo y de las plantas al aire.",
             "Flujo de evaporación desde la superficie terrestre (suelo, vegetación y nieve).",
             "MERRA-2, campo EVLAND de la colección tavg1_2d_lnd_Nx.", _LND, relativo=True),
    Variable("QV2M", "Humedad específica", "g/kg", HUMEDAD,
             "Cuántos gramos de agua invisible (vapor) hay en cada kilogramo de aire.",
             "Razón entre la masa de vapor de agua y la masa total de aire a 2 m.",
             "MERRA-2, campo QV2M de la colección tavg1_2d_slv_Nx.", _SLV, relativo=True),
    Variable("RH2M", "Humedad relativa", "%", HUMEDAD,
             "Qué tan cerca está el aire de saturarse de vapor: con 100 % se forma niebla o rocío.",
             "Razón entre la presión de vapor y la presión de vapor de saturación respecto a "
             "una superficie plana de agua pura, a 2 m, en porcentaje.",
             "Calculada por NASA POWER a partir de temperatura, humedad y presión de MERRA-2.", _SLV),
    Variable("T2MDEW", "Punto de rocío", "°C", HUMEDAD,
             "La temperatura a la que el aire tendría que enfriarse para formar rocío. "
             "Sube cuando el aire trae más humedad.",
             "Temperatura de punto de rocío o de escarcha a 2 m sobre la superficie.",
             "MERRA-2, campo T2MDEW de la colección tavg1_2d_slv_Nx.", _SLV),
    Variable("TQV", "Agua precipitable total", "kg/m²", HUMEDAD,
             "Toda el agua en forma de vapor que hay sobre el lugar, desde el suelo hasta "
             "el espacio.",
             "Vapor de agua total contenido en una columna vertical de sección unitaria, "
             "desde la superficie hasta el tope de la atmósfera.",
             "MERRA-2, campo TQV de la colección tavg1_2d_slv_Nx.", _SLV, relativo=True),
    # --- Aire y viento ---
    Variable("WS10M", "Velocidad del viento a 10 m", "m/s", AIRE,
             "Rapidez promedio del viento a 10 metros de altura.",
             "Velocidad media del viento a 10 m sobre la superficie.",
             "Calculada por NASA POWER a partir de las componentes U10M y V10M de MERRA-2.",
             _SLV, relativo=True),
    Variable("WS50M", "Velocidad del viento a 50 m", "m/s", AIRE,
             "Rapidez promedio del viento a 50 metros, la altura de un aerogenerador pequeño.",
             "Velocidad media del viento a 50 m sobre la superficie.",
             "Calculada por NASA POWER a partir de las componentes U50M y V50M de MERRA-2.",
             _SLV, relativo=True),
    Variable("PS", "Presión atmosférica en superficie", "kPa", AIRE,
             "El peso del aire sobre el lugar.",
             "Presión atmosférica media al nivel de la superficie terrestre.",
             "MERRA-2, campo PS de la colección tavg1_2d_slv_Nx.", _SLV, relativo=True),
    Variable("TO3", "Ozono total en columna", "unidades Dobson", AIRE,
             "Cantidad total de ozono sobre el lugar. La capa de ozono nos protege de los "
             "rayos ultravioleta.",
             "Cantidad total de ozono en una columna vertical desde la superficie hasta el "
             "tope de la atmósfera.",
             "MERRA-2, campo TO3 de la colección tavg1_2d_slv_Nx.",
             ("gelaro2017", "wargan2017", "gmao_slv", "power"), relativo=True),
    Variable("TROPPB", "Presión de la tropopausa", "kPa", AIRE,
             "La tropopausa es el \"techo\" de la capa de aire donde ocurre el clima. Si su "
             "presión baja, ese techo está subiendo.",
             "Presión en la tropopausa según la estimación combinada (blended) de MERRA-2. "
             "Un descenso de presión indica una tropopausa más alta.",
             "MERRA-2, campo TROPPB de la colección tavg1_2d_slv_Nx.", _SLV, relativo=True),
    Variable("AOD_55", "Espesor óptico de aerosoles", "AOD", AIRE,
             "Qué tanto bloquean la luz el polvo, el humo y la contaminación. Se mide con "
             "un índice llamado AOD: cerca de 0 el aire es muy limpio; arriba de 0.4 ya se "
             "ve turbio.",
             "Espesor óptico de aerosoles a 0.55 µm en la vertical: mide cuánta radiación "
             "retiran de un haz incidente las partículas suspendidas. Adimensional.",
             "CERES SYN1deg, cuyo campo de aerosoles proviene del modelo de transporte MATCH "
             "con asimilación de observaciones de MODIS.",
             ("rutan2015", "collins2001", "power"), fuente=SYN1DEG,
             resolucion="1° × 1° (unos 100 km)", desde=2001, relativo=True,
             aviso="Es un campo de un modelo que asimila observaciones de satélite, no una "
                   "medición directa. El producto SYN1deg puede tener discontinuidades cuando "
                   "cambian los satélites que lo alimentan."),
    # --- Instrumentos de satélite (observaciones, no un modelo) ---
    Variable("GPM_LLUVIA", "Precipitación (satélite GPM)", "mm/día", HIDRO,
             "Lluvia y nieve observadas por una constelación de satélites con radares y "
             "sensores de microondas, afinadas con pluviómetros en tierra.",
             "Precipitación media mensual del algoritmo IMERG (Final Run), que combina los "
             "sensores de microondas e infrarrojos de la constelación GPM y se calibra con "
             "pluviómetros. Convertida de mm/h a mm/día.",
             "GPM IMERG Final V07 mensual (3IMERGM), banda precipitation; colección "
             "NASA/GPM_L3/IMERG_MONTHLY_V07 de Google Earth Engine.",
             ("huffman2023", "huffman2020", "gorelick2017"), fuente=GPM,
             resolucion="0.1° nativo, muestreado a 0.5° (unos 50 km)", desde=1998,
             relativo=True, origen="gee"),
    Variable("GRACE_AGUA", "Almacenamiento de agua terrestre (GRACE)", "cm de agua", HIDRO,
             "Toda el agua guardada en el lugar: acuíferos, suelo, ríos y nieve. Dos satélites "
             "gemelos la «pesan» midiendo cómo cambia la gravedad. Se expresa en centímetros "
             "de agua de más o de menos respecto al promedio de 2004 a 2009.",
             "Anomalía del almacenamiento total de agua terrestre, en espesor equivalente de "
             "agua líquida respecto a la media de 2004–2009, estimada a partir de las "
             "variaciones del campo gravitatorio (solución de mascons del JPL con filtro CRI).",
             "JPL GRACE/GRACE-FO Mascon RL06.3 v04 CRI, banda lwe_thickness; colección "
             "NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI de Google Earth Engine.",
             ("watkins2015", "wiese2016", "wiese2023", "gorelick2017"), fuente=GRACE,
             resolucion="mascons de 3° (unos 300 km), en rejilla de 0.5°", desde=2002,
             origen="gee",
             aviso="La resolución real es de unos 300 km: no distingue una ciudad de sus "
                   "alrededores. Faltan los datos de mediados de 2017 a mediados de 2018, "
                   "entre la misión GRACE y GRACE-FO."),
    Variable("MODIS_NDVI", "Índice de vegetación NDVI (MODIS)", "NDVI", VEGETACION,
             "Qué tan verde y frondosa se ve la superficie desde el satélite. Se mide con un "
             "índice llamado NDVI: cerca de 0 es suelo desnudo; cerca de 1, selva densa.",
             "Índice de Vegetación de Diferencia Normalizada: (NIR − rojo) / (NIR + rojo), "
             "calculado con las reflectancias de superficie de MODIS. Compuesto mensual.",
             "MODIS/Terra MOD13A3 V061, banda NDVI; colección MODIS/061/MOD13A3 de Google "
             "Earth Engine.",
             ("didan2021", "huete2002", "gorelick2017"), fuente=MODIS,
             resolucion="1 km nativo, muestreado a 0.5° (unos 50 km)", desde=2000,
             relativo=True, origen="gee"),
)

POR_CODIGO: dict[str, Variable] = {v.codigo: v for v in CATALOGO}
