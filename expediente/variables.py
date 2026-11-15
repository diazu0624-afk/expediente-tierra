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
    "platnick2015": Referencia(
        "Platnick, S., King, M., & Hubanks, P. (2015). MODIS Atmosphere L3 Monthly Product. NASA "
        "MODIS Adaptive Processing System, Goddard Space Flight Center.",
        _doi("10.5067/MODIS/MOD08_M3.061")),
    "mcnally2017": Referencia(
        "McNally, A., Arsenault, K., Kumar, S., et al. (2017). A land data assimilation system "
        "for sub-Saharan Africa food and water security applications. Scientific Data, 4, 170012.",
        _doi("10.1038/sdata.2017.12")),
    "mcnally2018": Referencia(
        "McNally, A., NASA/GSFC/HSL (2018). FLDAS Noah Land Surface Model L4 Global Monthly "
        "0.1 x 0.1 degree (MERRA-2 and CHIRPS). GES DISC.", _doi("10.5067/5NHC22T9375G")),
    "levelt2006": Referencia(
        "Levelt, P. F., van den Oord, G. H. J., Dobber, M. R., et al. (2006). The Ozone "
        "Monitoring Instrument. IEEE Transactions on Geoscience and Remote Sensing, 44(5), "
        "1093–1101.", _doi("10.1109/TGRS.2006.872333")),
    "obpg2022": Referencia(
        "NASA Goddard Space Flight Center, Ocean Ecology Laboratory, Ocean Biology Processing "
        "Group (2022). Moderate-resolution Imaging Spectroradiometer (MODIS) Aqua Ocean Color "
        "Data. NASA OB.DAAC.", _doi("10.5067/AQUA/MODIS/L3M/CHL/2022")),
    "huang2021": Referencia(
        "Huang, B., Liu, C., Banzon, V., et al. (2021). Improvements of the Daily Optimum "
        "Interpolation Sea Surface Temperature (DOISST) Version 2.1. Journal of Climate, 34(8), "
        "2923–2939.", _doi("10.1175/JCLI-D-20-0166.1")),
    "reynolds2008": Referencia(
        "Reynolds, R. W., Banzon, V. F., & NOAA CDR Program (2008). NOAA Optimum Interpolation "
        "1/4 Degree Daily Sea Surface Temperature (OISST) Analysis, Version 2. NOAA National "
        "Centers for Environmental Information.", _doi("10.7289/V5SQ8XB5")),
    "zhang2011": Referencia(
        "Zhang, X., Alexander, L., Hegerl, G. C., Jones, P., Klein Tank, A., Peterson, T. C., "
        "Trewin, B., & Zwiers, F. W. (2011). Indices for monitoring changes in extremes based on "
        "daily temperature and precipitation data. WIREs Climate Change, 2(6), 851-870.",
        _doi("10.1002/wcc.147")),
    "gorelick2017": Referencia(
        "Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). "
        "Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote "
        "Sensing of Environment, 202, 18–27.", _doi("10.1016/j.rse.2017.06.031")),
    # --- Estudios publicados con los que se contrastan los ejemplos ---
    "rodell2009": Referencia(
        "Rodell, M., Velicogna, I., & Famiglietti, J. S. (2009). Satellite-based estimates of "
        "groundwater depletion in India. Nature, 460(7258), 999–1002.", _doi("10.1038/nature08238")),
    "ratnam2021": Referencia(
        "Ratnam, M. V., Prasad, P., Akhil Raj, S. T., Roja Raman, M., & Basha, G. (2021). Changing "
        "patterns in aerosol vertical distribution over South and East Asia. Scientific Reports, "
        "11, 308.", _doi("10.1038/s41598-020-79361-4")),
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
MODIS_AQUA = "MODIS a bordo del satélite Aqua (NASA), vía Google Earth Engine"
OMI = "OMI a bordo del satélite Aura (NASA), vía Google Earth Engine"
FLDAS = "FLDAS (modelo hidrológico de la NASA), vía Google Earth Engine"
OISST = "OISST (análisis de la NOAA con satélites, boyas y barcos), vía Google Earth Engine"

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
    # "power": mensual, por la API de NASA POWER. "gee": mensual, por Google Earth Engine.
    # "diario": índice anual calculado con los datos diarios de NASA POWER (expediente/extremos.py).
    origen: str = "power"
    tipo: str = ""  # vacío: se deduce del origen (ver la propiedad `clase`)

    @property
    def clase(self) -> str:
        """Qué clase de dato es: una observación, o el resultado de un modelo."""
        return self.tipo or {"gee": "Observación satelital", "diario": "Índice anual de extremos"}.get(
            self.origen, "Reanálisis o modelo")

    @property
    def anual(self) -> bool:
        """True si la variable trae un solo valor por año (los índices de extremos)."""
        return self.origen == "diario"

    @property
    def nombre_original(self) -> str:
        return NOMBRES_ORIGINALES[self.codigo]

    @property
    def relevancia(self) -> str:
        return RELEVANCIA[self.codigo]


TEMPERATURA = "Temperatura"
HIDRO = "Hidrología"
HUMEDAD = "Humedad atmosférica"
AIRE = "Atmósfera"
OCEANO = "Océano"
VEGETACION = "Vegetación"
EXTREMOS = "Extremos"
CATEGORIAS = (TEMPERATURA, HIDRO, HUMEDAD, AIRE, OCEANO, VEGETACION, EXTREMOS)

DIARIO = "MERRA-2 (reanálisis de la NASA), datos diarios vía NASA POWER"
_EXT = ("zhang2011", "gelaro2017", "power")
_AVISO_EXT = ("Los extremos de un reanálisis de unos 50 km son más suaves que los de una estación "
              "meteorológica: sirven para evaluar la tendencia, no el valor exacto de un evento.")


def _extremo(codigo: str, nombre: str, unidad: str, definicion: str, tecnica: str, campo: str,
             relativo: bool = False) -> "Variable":
    return Variable(codigo, nombre, unidad, EXTREMOS, definicion, tecnica,
                    f"Calculado por este proyecto con el campo diario {campo} de MERRA-2. Un valor por año; "
                    f"solo cuentan los años con al menos 360 días de datos.",
                    _EXT, fuente=DIARIO, relativo=relativo, aviso=_AVISO_EXT, origen="diario")


# Variables que se evaluaron y NO se incluyen, por no pasar el filtro de calidad
# (validacion/calidad_de_datos.py):
# - Nubosidad, radiación solar y albedo de CERES SYN1deg (vía POWER): saltos artificiales
#   cuando cambian los satélites (2001, 2017-2018, 2022).
# - Temperatura del suelo de MODIS Terra (MOD21C3): escalón en 2020 en 5 de 6 sitios
#   distantes, compatible con la deriva de la órbita de Terra.
# - Vapor de agua de MODIS Terra (MOD08_M3): su tendencia contradice en signo a MERRA-2 en 4
#   de 7 sitios, con un quiebre común en 2008.
# - Temperatura del tope de las nubes (MOD08_M3) y presión del tope de la capa límite
#   (POWER): escala u interpretación dudosas.
# Variables incluidas con recorte:
# - Clorofila de MODIS Aqua: solo hasta 2021 (salto global en 2022-2025 por la deriva de órbita).
# - GRACE: solo sobre tierra. Temperatura del mar y clorofila de MODIS Aqua: solo sobre océano.

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
    Variable("TROPT", "Temperatura de la tropopausa", "°C", AIRE,
             "Qué tan frío está el \"techo\" de la capa de aire donde ocurre el clima, a unos "
             "10 a 17 km de altura.",
             "Temperatura del aire en la tropopausa, el límite entre la troposfera y la "
             "estratosfera. Describe un nivel alto de la atmósfera, no la superficie.",
             "MERRA-2, campo TROPT de la colección tavg1_2d_slv_Nx.", _SLV),
    Variable("SLP", "Presión a nivel del mar", "kPa", AIRE,
             "La presión del aire ajustada como si el lugar estuviera al nivel del mar, para "
             "poder comparar sitios a distinta altitud.",
             "Presión atmosférica reducida al nivel medio del mar.",
             "MERRA-2, campo SLP de la colección tavg1_2d_slv_Nx.", _SLV, relativo=True),
    Variable("AOD_55", "Espesor óptico de aerosoles (modelo)", "AOD", AIRE,
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
    Variable("MODIS_EVI", "Índice de vegetación mejorado EVI (MODIS)", "EVI", VEGETACION,
             "Otra forma de medir qué tan verde está la superficie. Distingue mejor que el NDVI "
             "en selvas y bosques muy densos.",
             "Índice de Vegetación Mejorado: usa las bandas roja, infrarroja cercana y azul para "
             "reducir el efecto de la atmósfera y del suelo, y no se satura con vegetación densa. "
             "Compuesto mensual.",
             "MODIS/Terra MOD13A3 V061, banda EVI; colección MODIS/061/MOD13A3 de Google Earth Engine.",
             ("didan2021", "huete2002", "gorelick2017"), fuente=MODIS,
             resolucion="1 km nativo, muestreado a 0.5° (unos 50 km)", desde=2000,
             relativo=True, origen="gee"),
    Variable("MODIS_AOD", "Espesor óptico de aerosoles (MODIS)", "AOD", AIRE,
             "Qué tanto bloquean la luz el polvo, el humo y la contaminación, medido "
             "directamente por el satélite.",
             "Espesor óptico de aerosoles a 0.55 µm sobre tierra y océano, promedio mensual de "
             "las recuperaciones del instrumento MODIS. Adimensional.",
             "MODIS/Terra MOD08_M3 V061, campo Aerosol_Optical_Depth_Land_Ocean_Mean_Mean; "
             "colección MODIS/061/MOD08_M3 de Google Earth Engine.",
             ("platnick2015", "gorelick2017"), fuente=MODIS, resolucion="1° × 1° (unos 100 km)",
             desde=2000, relativo=True, origen="gee"),
    Variable("MODIS_NUBES", "Nubosidad (MODIS)", "%", AIRE,
             "Qué parte del cielo está cubierta por nubes, vista desde el satélite.",
             "Fracción del área cubierta por nubes según la máscara de nubes de MODIS, promedio "
             "mensual, en porcentaje.",
             "MODIS/Terra MOD08_M3 V061, campo Cloud_Fraction_Mean_Mean; colección "
             "MODIS/061/MOD08_M3 de Google Earth Engine.",
             ("platnick2015", "gorelick2017"), fuente=MODIS, resolucion="1° × 1° (unos 100 km)",
             desde=2000, origen="gee"),
    Variable("OMI_OZONO", "Ozono total en columna (OMI)", "unidades Dobson", AIRE,
             "Cantidad total de ozono sobre el lugar, medida por el instrumento OMI.",
             "Ozono total en columna recuperado por el Ozone Monitoring Instrument a bordo del "
             "satélite Aura. Promedio mensual de las observaciones diarias.",
             "TOMS and OMI Merged Ozone Data v3, banda ozone; colección TOMS/MERGED de Google "
             "Earth Engine. Solo se usa el periodo de OMI, desde 2005.",
             ("levelt2006", "gorelick2017"), fuente=OMI, resolucion="1° × 1° (unos 100 km)",
             desde=2005, relativo=True, origen="gee",
             aviso="La colección mezcla varios instrumentos desde 1978; aquí se analiza solo el "
                   "periodo de OMI para no confundir un cambio de instrumento con una tendencia."),
    Variable("FLDAS_TEMP", "Temperatura del aire (FLDAS)", "°C", TEMPERATURA,
             "Qué tan caliente o frío está el aire cerca del suelo, en una rejilla más fina que la del reanálisis.",
             "Temperatura del aire cerca de la superficie que alimenta al modelo FLDAS: es la de MERRA-2 "
             "llevada a una rejilla de 0.1°. No es una fuente independiente de «Temperatura del aire»; se "
             "incluye porque permite analizar países completos y el mundo.",
             "FLDAS Noah (forzado con MERRA-2 y CHIRPS), campo Tair_f_tavg; colección "
             "NASA/FLDAS/NOAH01/C/GL/M/V001 de Google Earth Engine.",
             ("mcnally2017", "mcnally2018", "gelaro2017", "gorelick2017"), fuente=FLDAS,
             resolucion="0.1° nativo, muestreado a 0.5° (unos 50 km)", desde=1982,
             origen="gee", tipo="Modelo de superficie terrestre"),
    Variable("FLDAS_ESCURRIMIENTO", "Escurrimiento (FLDAS)", "mm/día", HIDRO,
             "El agua de lluvia y deshielo que no se queda en el suelo y corre hacia arroyos, "
             "ríos y acuíferos.",
             "Escurrimiento total simulado: superficial más subterráneo (flujo base). Es una "
             "estimación de un modelo de superficie terrestre, no un caudal medido en un río.",
             "FLDAS Noah (forzado con MERRA-2 y CHIRPS), campos Qs_tavg + Qsb_tavg; colección "
             "NASA/FLDAS/NOAH01/C/GL/M/V001 de Google Earth Engine.",
             ("mcnally2017", "mcnally2018", "gorelick2017"), fuente=FLDAS,
             resolucion="0.1° nativo, muestreado a 0.5° (unos 50 km)", desde=1982,
             relativo=True, origen="gee", tipo="Modelo de superficie terrestre"),
    # --- Océano ---
    Variable("MAR_SST", "Temperatura de la superficie del mar", "°C", OCEANO,
             "Qué tan caliente está el agua en la superficie del mar.",
             "Temperatura de la superficie del mar del análisis OISST, que combina satélites, "
             "boyas y barcos por interpolación óptima. Promedio mensual de los campos diarios.",
             "NOAA OISST v2.1, banda sst; colección NOAA/CDR/OISST/V2_1 de Google Earth Engine.",
             ("huang2021", "reynolds2008", "gorelick2017"), fuente=OISST,
             resolucion="0.25° nativo, muestreado a 0.5° (unos 50 km)", desde=1982, origen="gee",
             tipo="Análisis de observaciones"),
    Variable("MAR_SST_MODIS", "Temperatura de la superficie del mar (MODIS)", "°C", OCEANO,
             "La temperatura del agua en la superficie del mar, medida por el satélite Aqua.",
             "Temperatura de la superficie del mar recuperada en el infrarrojo por MODIS Aqua, "
             "en cielo despejado. Promedio mensual de los campos diarios.",
             "MODIS Aqua L3 SMI, banda sst; colección NASA/OCEANDATA/MODIS-Aqua/L3SMI de Google "
             "Earth Engine.",
             ("obpg2022", "gorelick2017"), fuente=MODIS_AQUA,
             resolucion="4 km nativo, muestreado a 0.5° (unos 50 km)", desde=2003, origen="gee"),
    Variable("MAR_CLOROFILA", "Clorofila del océano (MODIS)", "mg/m³", OCEANO,
             "Cuánta clorofila hay en el agua: indica la cantidad de fitoplancton, las plantas "
             "microscópicas de las que depende la vida marina.",
             "Concentración de clorofila a cerca de la superficie, estimada por el color del "
             "océano. Promedio mensual de los campos diarios.",
             "MODIS Aqua L3 SMI, banda chlor_a; colección NASA/OCEANDATA/MODIS-Aqua/L3SMI de "
             "Google Earth Engine.",
             ("obpg2022", "gorelick2017"), fuente=MODIS_AQUA,
             resolucion="4 km nativo, muestreado a 0.5° (unos 50 km)", desde=2003,
             relativo=True, origen="gee",
             aviso="El registro se analiza de 2003 a 2021. Desde 2022 el satélite Aqua deriva de órbita y "
                   "la clorofila muestra un salto global que no es del océano, así que esos años se "
                   "descartan. Además, su distribución es muy asimétrica: unos pocos florecimientos "
                   "intensos pesan mucho en el promedio."),
    # --- Extremos: índices anuales calculados con datos diarios (definiciones del ETCCDI) ---
    _extremo("EXT_TXX", "Día más caluroso del año", "°C",
             "La temperatura máxima más alta que se registró en el año.",
             "Índice TXx del ETCCDI: máximo anual de la temperatura máxima diaria a 2 m.", "T2M_MAX"),
    _extremo("EXT_TNN", "Noche más fría del año", "°C",
             "La temperatura mínima más baja que se registró en el año.",
             "Índice TNn del ETCCDI: mínimo anual de la temperatura mínima diaria a 2 m.", "T2M_MIN"),
    _extremo("EXT_DIAS_CALOR", "Días de calor extremo para el lugar", "días/año",
             "Cuántos días del año fueron más calurosos que el 90 % de los días de 1981 a 2010 en ese mismo lugar.",
             "Días al año con temperatura máxima superior al percentil 90 de las máximas diarias del periodo "
             "base 1981-2010 del sitio. Variante simplificada del índice TX90p del ETCCDI: el umbral es uno "
             "solo para todo el año, no uno por día del calendario.", "T2M_MAX", relativo=True),
    _extremo("EXT_DIAS_35", "Días con más de 35 °C", "días/año",
             "Cuántos días del año la temperatura máxima superó los 35 °C.",
             "Días al año con temperatura máxima diaria a 2 m superior a 35 °C (umbral fijo).", "T2M_MAX",
             relativo=True),
    _extremo("EXT_NOCHES_20", "Noches tropicales", "días/año",
             "Cuántas noches del año la temperatura no bajó de 20 °C.",
             "Índice TR del ETCCDI: días al año con temperatura mínima diaria superior a 20 °C.", "T2M_MIN",
             relativo=True),
    _extremo("EXT_RX1", "Lluvia máxima en un día", "mm",
             "Cuánto llovió el día más lluvioso del año.",
             "Índice Rx1day del ETCCDI: máximo anual de la precipitación diaria.", "PRECTOTCORR", relativo=True),
    _extremo("EXT_R10", "Días con lluvia fuerte", "días/año",
             "Cuántos días del año llovieron 10 mm o más.",
             "Índice R10mm del ETCCDI: días al año con precipitación diaria de 10 mm o más.", "PRECTOTCORR",
             relativo=True),
    _extremo("EXT_CDD", "Racha seca más larga", "días",
             "El mayor número de días seguidos sin lluvia en el año.",
             "Índice CDD del ETCCDI: máximo de días consecutivos con precipitación inferior a 1 mm. Aquí la "
             "racha se cuenta dentro de cada año calendario.", "PRECTOTCORR", relativo=True),
)

# Nombre con el que el proveedor publica cada variable (para buscarla en su documentación).
NOMBRES_ORIGINALES = {
    "EXT_TXX": "TXx (ETCCDI), from T2M_MAX daily", "EXT_TNN": "TNn (ETCCDI), from T2M_MIN daily",
    "EXT_DIAS_CALOR": "TX90p simplified, from T2M_MAX daily", "EXT_DIAS_35": "Days with TX > 35 °C, from T2M_MAX daily",
    "EXT_NOCHES_20": "TR (ETCCDI), from T2M_MIN daily", "EXT_RX1": "Rx1day (ETCCDI), from PRECTOTCORR daily",
    "EXT_R10": "R10mm (ETCCDI), from PRECTOTCORR daily", "EXT_CDD": "CDD (ETCCDI), from PRECTOTCORR daily",
    "T2M": "Temperature at 2 Meters", "T2M_MAX": "Temperature at 2 Meters Maximum",
    "T2M_MIN": "Temperature at 2 Meters Minimum", "T2M_RANGE": "Temperature at 2 Meters Range",
    "TS": "Earth Skin Temperature", "FROST_DAYS": "Frost Days",
    "CDD18_3": "Cooling Degree Days Above 18.3 C", "HDD18_3": "Heating Degree Days Below 18.3 C",
    "PRECTOTCORR": "Precipitation Corrected", "PRECSNOLAND": "Snow Precipitation Land",
    "SNODP": "Snow Depth", "GWETTOP": "Surface Soil Wetness", "GWETROOT": "Root Zone Soil Wetness",
    "EVLAND": "Evaporation Land", "QV2M": "Specific Humidity at 2 Meters",
    "RH2M": "Relative Humidity at 2 Meters", "T2MDEW": "Dew/Frost Point at 2 Meters",
    "TQV": "Total Column Precipitable Water", "WS10M": "Wind Speed at 10 Meters",
    "WS50M": "Wind Speed at 50 Meters", "PS": "Surface Pressure", "TO3": "Total Column Ozone",
    "TROPPB": "Tropopause Pressure based on blended estimate", "AOD_55": "Aerosol Optical Depth 55",
    "GPM_LLUVIA": "Merged satellite-gauge precipitation estimate (precipitation)",
    "GRACE_AGUA": "Liquid Water Equivalent Thickness (lwe_thickness)",
    "MODIS_NDVI": "Normalized Difference Vegetation Index (NDVI)",
    "MODIS_EVI": "Enhanced Vegetation Index (EVI)",
    "MODIS_AOD": "Aerosol optical thickness at 0.55 microns for both ocean and land",
    "MODIS_NUBES": "Cloud Fraction (Cloud_Fraction_Mean_Mean)",
    "OMI_OZONO": "Total column ozone (ozone)",
    "FLDAS_ESCURRIMIENTO": "Storm surface runoff + Baseflow-groundwater runoff (Qs_tavg, Qsb_tavg)",
    "FLDAS_TEMP": "Near surface air temperature (Tair_f_tavg)",
    "MAR_SST": "Daily sea surface temperature (sst)",
    "MAR_SST_MODIS": "Sea surface temperature (sst)",
    "MAR_CLOROFILA": "Chlorophyll a concentration (chlor_a)",
    "TROPT": "Tropopause Temperature", "SLP": "Sea Level Pressure",
}

# Por qué importa cada variable para el sistema Tierra.
RELEVANCIA = {
    "EXT_TXX": "El calor más intenso del año pone a prueba la salud, la red eléctrica y los cultivos más que el promedio.",
    "EXT_TNN": "El frío más intenso del año determina las heladas dañinas y qué especies y plagas sobreviven al invierno.",
    "EXT_DIAS_CALOR": "Mide las olas de calor con la vara de cada lugar: lo que es extremo en una ciudad templada es normal en el desierto.",
    "EXT_DIAS_35": "Sobre 35 °C aumentan el golpe de calor, las pérdidas agrícolas y la demanda de energía para enfriar.",
    "EXT_NOCHES_20": "Las noches cálidas impiden que el cuerpo y las ciudades se recuperen del calor del día.",
    "EXT_RX1": "Los aguaceros más intensos causan inundaciones repentinas y deslaves; una atmósfera más cálida retiene más vapor.",
    "EXT_R10": "La lluvia fuerte recarga presas y acuíferos, pero también erosiona el suelo y satura el drenaje.",
    "EXT_CDD": "Las rachas secas largas agotan la humedad del suelo y elevan el riesgo de sequía e incendios.",
    "T2M": "Es el indicador básico del calentamiento global y condiciona la salud, la agricultura y la demanda de energía.",
    "T2M_MAX": "Los extremos de calor determinan las olas de calor, el estrés térmico y el riesgo de incendios.",
    "T2M_MIN": "Las mínimas controlan las heladas y el descanso nocturno de personas y cultivos.",
    "T2M_RANGE": "Responde a cambios en la nubosidad, la humedad y el uso del suelo: se reduce cuando las noches se calientan más que los días.",
    "TS": "Gobierna el intercambio de calor entre la superficie y la atmósfera y delata efectos locales como la isla de calor urbana.",
    "FROST_DAYS": "Marca la duración de la temporada de cultivo y la supervivencia de plagas y de cultivos sensibles al frío.",
    "CDD18_3": "Traduce el calentamiento en demanda de electricidad para enfriar edificios.",
    "HDD18_3": "Traduce el clima en demanda de energía para calefacción; disminuye cuando los inviernos se suavizan.",
    "PRECTOTCORR": "Es la entrada principal del ciclo del agua: de ella dependen ríos, acuíferos, cultivos y sequías.",
    "PRECSNOLAND": "La nieve almacena agua en invierno y la libera en primavera; sus cambios alteran el caudal de los ríos.",
    "SNODP": "El manto de nieve refleja la luz solar y es una reserva de agua; su reducción amplifica el calentamiento.",
    "GWETTOP": "Controla cuánta lluvia se infiltra o escurre y cuánta energía del Sol se gasta en evaporar agua.",
    "GWETROOT": "Es el agua disponible para las plantas: su descenso anticipa la sequía agrícola.",
    "EVLAND": "Devuelve agua a la atmósfera y enfría la superficie; enlaza el ciclo del agua con el de la energía.",
    "QV2M": "El aire más caliente puede contener más vapor, lo que intensifica el efecto invernadero y las lluvias extremas.",
    "RH2M": "Influye en el confort térmico, el riesgo de incendios y la formación de nubes y niebla.",
    "T2MDEW": "Mide el contenido real de humedad del aire y es clave para evaluar el estrés por calor húmedo.",
    "TQV": "Es el combustible de la precipitación, y el vapor de agua es el principal gas de efecto invernadero natural.",
    "WS10M": "El viento transporta calor y humedad, impulsa la evaporación y determina el potencial eólico.",
    "WS50M": "Es la referencia para evaluar el recurso eólico a la altura de los aerogeneradores.",
    "PS": "Sus variaciones definen los sistemas de tiempo: altas y bajas presiones, vientos y tormentas.",
    "TO3": "La capa de ozono absorbe la radiación ultravioleta dañina; su recuperación se vigila desde el Protocolo de Montreal.",
    "TROPPB": "La altura de la tropopausa responde al calentamiento de la troposfera y es una de las huellas del cambio climático.",
    "AOD_55": "Los aerosoles afectan la salud, enfrían la superficie al reflejar la luz solar y modifican las nubes.",
    "GPM_LLUVIA": "Es una observación de la precipitación independiente de los modelos, disponible incluso donde no hay pluviómetros.",
    "GRACE_AGUA": "Es la única medición satelital del agua total almacenada en una región, incluida la subterránea.",
    "MODIS_NDVI": "Refleja la cantidad y la salud de la vegetación: responde a sequías, deforestación, riego y cambios de uso del suelo.",
    "MODIS_EVI": "Complementa al NDVI donde este se satura; permite confirmar con un segundo índice si la vegetación cambia.",
    "MODIS_AOD": "Es una observación directa de los aerosoles, que afectan la salud, la luz solar que llega al suelo y las nubes.",
    "MODIS_NUBES": "Las nubes regulan cuánta energía del Sol entra y cuánta sale: son la mayor incertidumbre del clima.",
    "OMI_OZONO": "Es la vigilancia satelital directa de la capa de ozono, que absorbe la radiación ultravioleta dañina.",
    "FLDAS_TEMP": "Es el indicador básico del calentamiento; en rejilla fina permite ver cómo cambia dentro de un país.",
    "FLDAS_ESCURRIMIENTO": "Determina cuánta agua llega a ríos, presas y acuíferos: es la base del abasto de agua y del riesgo de inundación.",
    "MAR_SST": "El océano absorbe la mayor parte del calor que gana el planeta; su temperatura controla huracanes, corales y pesquerías.",
    "MAR_SST_MODIS": "Es una medición satelital independiente de la temperatura del mar, que permite confirmar el análisis de largo plazo.",
    "MAR_CLOROFILA": "El fitoplancton es la base de la cadena alimentaria marina y produce cerca de la mitad del oxígeno del planeta.",
    "TROPT": "La tropopausa es un nivel alto de la atmósfera: su temperatura responde distinto que la superficie al cambio climático.",
    "SLP": "Sus cambios sostenidos revelan desplazamientos de los sistemas de alta y baja presión que organizan el clima.",
}

POR_CODIGO: dict[str, Variable] = {v.codigo: v for v in CATALOGO}

# Variables que solo tienen sentido sobre tierra firme. Sobre mar abierto no se muestran:
# GRACE ahí mide masa del océano, no agua terrestre, y el reanálisis no tiene suelo.
SOLO_TIERRA = frozenset({
    "GWETTOP", "GWETROOT", "EVLAND", "PRECSNOLAND", "SNODP",
    "GRACE_AGUA", "MODIS_NDVI", "MODIS_EVI", "FLDAS_ESCURRIMIENTO", "FLDAS_TEMP",
})
# Las del océano (categoría OCEANO) solo se muestran donde hay mar: los sensores de color
# del océano también "ven" ríos y lagos, pero ahí sus algoritmos no son válidos.
SOLO_MAR = frozenset(v.codigo for v in CATALOGO if v.categoria == OCEANO)

# Pares de variables que miden lo mismo con fuentes independientes. Si las dos coinciden en
# el signo de la tendencia, el resultado no depende de un solo instrumento o modelo.
PAREJAS = {
    "MODIS_AOD": "AOD_55", "AOD_55": "MODIS_AOD",
    "OMI_OZONO": "TO3", "TO3": "OMI_OZONO",
    "GPM_LLUVIA": "PRECTOTCORR", "PRECTOTCORR": "GPM_LLUVIA",
    "MAR_SST_MODIS": "MAR_SST", "MAR_SST": "MAR_SST_MODIS",
    "MODIS_EVI": "MODIS_NDVI", "MODIS_NDVI": "MODIS_EVI",
}
