import numpy as np
import pandas as pd
import pytest

from expediente import caso
from expediente.datos import _a_tabla
from expediente.variables import CATALOGO, POR_CODIGO


def _serie(pendiente_anual, ruido=1.0, anios=40, semilla=0, ciclo=8.0):
    rng = np.random.default_rng(semilla)
    indice = pd.date_range("1985-01-01", periods=anios * 12, freq="MS")
    t = np.arange(anios * 12) / 12
    valores = 20 + ciclo * np.sin(2 * np.pi * t) + pendiente_anual * t + rng.normal(0, ruido, t.size)
    return pd.Series(valores, index=indice)


def test_tendencia_clara_pasa_las_cinco_pruebas():
    r = caso.interrogar(_serie(0.05), POR_CODIGO["T2M"])
    assert r.resolucion == "mensual"
    assert [p.aprobada for p in r.pruebas] == [True] * 5
    assert r.nivel == "solida" and r.sube
    assert r.pendiente_decada == pytest.approx(0.5, abs=0.1)
    assert r.ic_decada[0] < 0.5 < r.ic_decada[1]
    assert r.cambio_total == pytest.approx(2.0, abs=0.4)
    assert r.cambio_relativo is None  # un porcentaje de °C no significa nada


def test_puro_ruido_no_es_evidencia():
    r = caso.interrogar(_serie(0.0, semilla=3), POR_CODIGO["PRECTOTCORR"])
    assert r.nivel == "sin"
    assert r.anios_necesarios > r.anios_de_datos


def test_el_ciclo_estacional_no_cuenta_como_tendencia():
    r = caso.interrogar(_serie(0.0, ruido=0.2, ciclo=15, semilla=4), POR_CODIGO["T2M"])
    assert abs(r.anomalias.groupby(r.anomalias.index.month).mean()).max() < 1e-9
    assert r.nivel == "sin"


def test_fenomeno_de_temporada_se_interroga_por_anio():
    # "Heladas": cero ocho meses del año, con una baja sostenida en invierno.
    serie = _serie(-0.08, ruido=0.6, ciclo=0.0, semilla=5) - 14
    serie[~serie.index.month.isin([12, 1, 2, 3])] = 0.0
    r = caso.interrogar(serie.clip(lower=0).round(2), POR_CODIGO["FROST_DAYS"])
    assert r.resolucion == "anual"
    assert r.pruebas[3].nombre == "Sensibilidad a un año"
    assert not r.sube and r.nivel in ("solida", "fuerte")
    assert r.anios_de_datos == 40


def test_variable_que_casi_nunca_ocurre_no_se_puede_interrogar():
    serie = _serie(0.0) * 0
    serie.iloc[[5, 200, 410]] = 1.0
    with pytest.raises(caso.CasoImposible):
        caso.interrogar(serie, POR_CODIGO["SNODP"])
    with pytest.raises(caso.CasoImposible):
        caso.interrogar(_serie(0.05, anios=10), POR_CODIGO["T2M"])


def test_escaner_ordena_por_fuerza_y_descarta_lo_imposible():
    datos = pd.DataFrame({
        "T2M": _serie(0.08, semilla=1),
        "PRECTOTCORR": _serie(0.0, semilla=2),
        "WS10M": _serie(-0.03, semilla=3),
        "SNODP": _serie(0.0) * 0,
    })
    variables = tuple(POR_CODIGO[c] for c in datos.columns)
    tabla = caso.escanear(datos, variables)
    assert tabla.loc[0, "codigo"] == "T2M" and tabla.loc[0, "significativa"]
    assert tabla.loc[0, "estandarizada"] > 0 > tabla.set_index("codigo").loc["WS10M", "estandarizada"]
    nieve = tabla.set_index("codigo").loc["SNODP"]
    assert nieve["nota"] and np.isnan(nieve["estandarizada"]) and not nieve["significativa"]
    assert tabla["codigo"].iloc[-1] == "SNODP"  # lo que no se puede medir va al final
    validas = tabla.dropna(subset=["p"])
    assert (validas["p_ajustada"] >= validas["p"] - 1e-12).all()


def test_numero_y_valor_p():
    assert caso.numero(0.3712, signo=True) == "+0.37"
    assert caso.numero(-0.00067) == "-0.00067"
    assert caso.numero(1234.5) == "1,234"
    assert caso.numero(0) == "0"
    assert caso.valor_p(0.0004) == "p < 0.001"
    assert caso.valor_p(0.0312) == "p = 0.031"


def test_respuesta_de_power_se_convierte_en_tabla_mensual():
    tabla = _a_tabla({"T2M": {"202001": 10.0, "202002": -999.0, "202013": 11.0, "202003": 12.0}})
    assert list(tabla.index.strftime("%Y-%m")) == ["2020-01", "2020-02", "2020-03"]
    assert tabla["T2M"].iloc[0] == 10.0 and np.isnan(tabla["T2M"].iloc[1])


def test_catalogo_sin_codigos_repetidos():
    assert len(POR_CODIGO) == len(CATALOGO)
    assert all(v.definicion.endswith(".") for v in CATALOGO)


def test_region_promedio_y_mapa_con_tendencias_opuestas():
    from expediente import region
    norte = {f"{lat},{lon}": _serie(0.08, semilla=k) for k, (lat, lon) in enumerate([(30.0, -100.0), (30.0, -99.375)])}
    sur = {f"{lat},{lon}": _serie(-0.08, semilla=9 + k) for k, (lat, lon) in enumerate([(20.0, -100.0), (20.0, -99.375)])}
    mar = {"25.0,-100.0": _serie(0.0) * np.nan}
    cubo = pd.DataFrame({**norte, **sur, **mar})
    mapa = region.mapa_de_tendencias(cubo, POR_CODIGO["T2M"])
    assert len(mapa) == 4  # la celda sin datos queda fuera
    assert (mapa[mapa["lat"] == 30.0]["pendiente_decada"] > 0.5).all()
    assert (mapa[mapa["lat"] == 20.0]["pendiente_decada"] < -0.5).all()
    assert mapa["significativa"].all()
    r = region.resumen(mapa)
    assert r == {"sube": 50.0, "baja": 50.0, "celdas": 4, "anios_min": 40, "anios_max": 40}
    # Tendencias opuestas se cancelan en el promedio: por eso hace falta el mapa.
    promedio = region.promedio_regional(cubo)
    assert len(promedio) == 480 and promedio.notna().all()
    assert abs(caso.interrogar(promedio, POR_CODIGO["T2M"]).pendiente_decada) < 0.2


def test_caja_respeta_los_limites_del_planeta():
    from expediente.datos import caja
    assert caja(25.68, -100.32, 8) == (22, 30, -104, -96)
    assert caja(88, 179, 8) == (82, 90, 172, 180)


def test_promedio_anual_no_se_sesga_por_un_mes_faltante():
    serie = _serie(0.0, ruido=0.0)  # solo estaciones: todos los años promedian 20
    completos = caso.promedios_anuales(serie)
    assert np.allclose(completos, 20) and len(completos) == 40
    con_hueco = serie.drop(serie.index[(serie.index.year == 1990) & (serie.index.month == 4)])
    assert caso.promedios_anuales(con_hueco).loc[1990] == pytest.approx(20)  # el promedio simple daría otro valor
    assert con_hueco[con_hueco.index.year == 1990].mean() != pytest.approx(20, abs=0.1)
    # Un año con menos de 9 meses no cuenta.
    medio_anio = serie.drop(serie.index[(serie.index.year == 1991) & (serie.index.month > 6)])
    assert 1991 not in caso.promedios_anuales(medio_anio).index


def test_cubo_de_satelite_recorte_y_punto():
    from expediente import datos_gee
    indice = pd.date_range("2000-01-01", periods=24, freq="MS")
    lats, lons = [29.75, 25.75, 22.25], [-103.75, -100.25, -96.25]
    cubo = pd.DataFrame({f"{la},{lo}": np.full(24, la + lo) for la in lats for lo in lons}, index=indice)
    assert datos_gee.recortar(cubo, 25.68, -100.32, 8).shape[1] == 9
    assert list(datos_gee.recortar(cubo, 25.68, -100.32, 4).columns) == ["25.75,-100.25"]
    assert datos_gee.serie_del_punto(cubo, 25.68, -100.32).iloc[0] == pytest.approx(25.75 - 100.25)
    assert datos_gee.serie_del_punto(cubo.iloc[:, :0], 25.68, -100.32).empty
    assert datos_gee.serie_del_punto(cubo, 27.5, -100.32).empty  # la celda más cercana queda lejos


def test_catalogo_distingue_modelo_y_satelite():
    from expediente.datos_gee import FUENTES
    assert {v.codigo for v in CATALOGO if v.origen == "gee"} == set(FUENTES)


def test_careo_distingue_opuestos_ritmos_y_un_solo_cambio():
    from expediente import veredicto
    t2m = POR_CODIGO["T2M"]
    sube = caso.interrogar(_serie(0.05, semilla=1), t2m)
    sube_rapido = caso.interrogar(_serie(0.15, semilla=2), t2m)
    baja = caso.interrogar(_serie(-0.05, semilla=3), t2m)
    quieto = caso.interrogar(_serie(0.0, semilla=3), t2m)
    assert veredicto.comparar(sube, baja, "A", "B").startswith("Tendencias opuestas: sube en A")
    ritmo = veredicto.comparar(sube, sube_rapido, "A", "B")
    assert ritmo.startswith("Mismo signo") and "pero en B lo hace" in ritmo
    solo = veredicto.comparar(quieto, baja, "A", "B")
    assert solo.startswith("Tendencia en un solo lugar: baja en B") and "en A no hay evidencia" in solo
    assert veredicto.comparar(quieto, quieto, "A", "B").startswith("Ninguno")


def test_cada_variable_tiene_ficha_completa_y_referencias_validas():
    from expediente.variables import METODOS, REFERENCIAS
    for v in CATALOGO:
        assert v.tecnica.endswith(".") and v.producto.endswith(".") and v.resolucion
        assert v.referencias and all(clave in REFERENCIAS for clave in v.referencias), v.codigo
    assert all(clave in REFERENCIAS for clave in METODOS)
    assert all(r.url.startswith("https://") for r in REFERENCIAS.values())


def test_relevancia_practica_y_ficha_tecnica():
    from expediente import veredicto
    grande = caso.interrogar(_serie(0.08, ruido=0.5, semilla=1), POR_CODIGO["T2M"])
    assert grande.cambio_en_variabilidad > 2
    texto = veredicto.relevancia_practica(grande)
    assert "Es un cambio grande" in texto and "no implica que su magnitud sea importante" in texto
    assert veredicto.relevancia_practica(caso.interrogar(_serie(0.0, semilla=3), POR_CODIGO["T2M"])) == ""
    ficha = dict(veredicto.ficha_tecnica(grande))
    assert ficha["Nivel de significancia"].startswith("α = 0.05")
    assert "480 anomalías mensuales" in ficha["Tamaño de muestra"] and "p " in ficha["Valores p"]
    informe = veredicto.informe_markdown(grande, "X", 0.0, 0.0)
    for titulo in ("## Relevancia práctica", "## Ficha técnica", "## Supuestos", "## Limitaciones"):
        assert titulo in informe


def test_aviso_de_registro_corto():
    from expediente import veredicto
    corto = caso.interrogar(_serie(0.08, anios=18, semilla=2), POR_CODIGO["T2M"])
    largo = caso.interrogar(_serie(0.08, anios=40, semilla=2), POR_CODIGO["T2M"])
    assert "usa 18 años" in veredicto.aviso_registro_corto(corto)
    assert veredicto.redactar(corto).registro_corto and "## Registro corto" in veredicto.informe_markdown(corto, "X", 0.0, 0.0)
    assert veredicto.aviso_registro_corto(largo) == "" and veredicto.redactar(largo).registro_corto == ""


def test_informe_html_completo_y_con_texto_externo_escapado():
    from expediente import informe
    r = caso.interrogar(_serie(0.06, semilla=4), POR_CODIGO["T2M"])
    mapa = pd.DataFrame({"lat": [25.0, 25.0, 25.5, 25.5], "lon": [-100.0, -99.375, -100.0, -99.375],
                         "pendiente_decada": [0.4, 0.2, -0.3, 0.1], "p": [0.01, 0.2, 0.01, 0.6],
                         "p_ajustada": [0.02, 0.3, 0.02, 0.6], "significativa": [True, False, True, False]})
    html = informe.informe_html(r, "Sitio <script>alert(1)</script>", 25.2, -99.8, mapa=mapa,
                                region="Recuadro de prueba.", contraste=("Texto de contraste.", "rodell2009"),
                                hipotesis="«Está aumentando». El análisis la respalda.")
    assert html.startswith("<!doctype html>") and html.count("<svg") == 2
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    for parte in ("Informe de análisis de tendencia", "Equipo C15H25N3O", "Resumen", "Variable analizada",
                  "Serie de tiempo", "Pruebas de significancia", "Distribución espacial", "Ficha técnica",
                  "Supuestos del análisis", "Limitaciones", "Contraste con la literatura", "Método",
                  "Referencias", "10.1038/nature08238", "10.1175/JCLI-D-16-0758.1", "Hipótesis inicial"):
        assert parte in html, parte
    sin_extras = informe.informe_html(r, "X", 0.0, 0.0)
    assert "Distribución espacial" not in sin_extras and "Contraste con la literatura" not in sin_extras
    anual = caso.interrogar((_serie(-0.08, ruido=0.6, ciclo=0.0, semilla=5) - 14).clip(lower=0).round(2).where(lambda s: s.index.month.isin([12, 1, 2, 3]), 0.0), POR_CODIGO["FROST_DAYS"])
    assert "Promedio anual" in informe.informe_html(anual, "X", 0.0, 0.0)


def test_recorrido_animado_generado_y_completo():
    from expediente import demo
    html = demo.RUTA.read_text(encoding="utf-8")
    assert html.count('<section class="escena') == 11 and "__DATOS__" not in html and "const AUTO = true;" in html
    datos = {"sitio": "X", "variables": 27, "exploracion": [], "pruebas": []}
    assert '"sitio": "X"' in demo.demo_html(datos) and "const AUTO = false;" in demo.demo_html(datos, reproducir_sola=False)


# ---------- regla tierra/mar ----------

def _tabla_de_sitio(**columnas):
    meses = pd.date_range("2003-01-01", periods=24, freq="MS")
    return pd.DataFrame({k: (np.full(24, np.nan) if v is None else np.full(24, v)) for k, v in columnas.items()}, index=meses)


def test_en_tierra_firme_no_se_muestran_las_variables_del_mar():
    from expediente.sitio import fuera_de_lugar
    from expediente.variables import SOLO_MAR
    # Un río visto por el sensor de color del océano: hay "temperatura del mar" de MODIS, pero no OISST.
    tabla = _tabla_de_sitio(GWETROOT=0.6, MAR_SST_MODIS=30.0)
    assert fuera_de_lugar(tabla) == SOLO_MAR and "MAR_SST_MODIS" in SOLO_MAR


def test_en_mar_abierto_no_se_muestran_las_variables_de_tierra():
    from expediente.sitio import fuera_de_lugar
    from expediente.variables import SOLO_TIERRA
    tabla = _tabla_de_sitio(GWETROOT=None, MAR_SST=26.0, GRACE_AGUA=1.0)
    assert fuera_de_lugar(tabla) == SOLO_TIERRA and "GRACE_AGUA" in SOLO_TIERRA


def test_en_la_costa_se_muestran_las_dos():
    from expediente.sitio import fuera_de_lugar
    assert fuera_de_lugar(_tabla_de_sitio(GWETROOT=0.4, MAR_SST=5.0)) == frozenset()


# ---------- análisis por estación o mes ----------

def _mensual(anios=40, pendiente_verano=0.0, semilla=3):
    """Serie mensual con ciclo estacional; la tendencia, si la hay, ocurre solo de junio a agosto."""
    rng = np.random.default_rng(semilla)
    meses = pd.date_range("1981-01-01", periods=12 * anios, freq="MS")
    valores = 20 + 8 * np.sin(2 * np.pi * (meses.month - 4) / 12) + rng.normal(0, 0.5, meses.size)
    verano = np.isin(meses.month, (6, 7, 8))
    valores = valores + np.where(verano, pendiente_verano * (meses.year - 1981), 0.0)
    return pd.Series(valores, index=meses)


def test_los_meses_se_ordenan_y_se_nombran():
    assert caso.ordenar_meses([2, 12, 1]) == (12, 1, 2)
    assert caso.ordenar_meses([8, 6, 7]) == (6, 7, 8)
    assert caso.ordenar_meses(range(1, 13)) == caso.TODO_EL_ANIO
    assert caso.nombre_de_meses((12, 1, 2)) == "diciembre a febrero"
    assert caso.nombre_de_meses((7,)) == "julio"
    assert caso.nombre_de_meses((1, 7)) == "enero y julio"
    assert caso.nombre_de_meses(caso.TODO_EL_ANIO) == "todo el año"


def test_la_temporada_que_cruza_el_anio_se_asigna_al_anio_en_que_termina():
    meses = pd.date_range("2000-01-01", "2002-12-01", freq="MS")
    serie = pd.Series(np.arange(meses.size, dtype=float), index=meses)
    invierno = caso.serie_de_temporada(serie, (12, 1, 2))
    # 2000 no tiene su diciembre previo y 2003 solo tendría diciembre: quedan 2001 y 2002.
    assert list(invierno.index) == [2001, 2002]
    assert invierno[2001] == pytest.approx(np.mean([11, 12, 13]))  # dic 2000, ene 2001, feb 2001


def test_una_tendencia_solo_de_verano_se_detecta_en_verano_y_no_en_invierno():
    serie = _mensual(pendiente_verano=0.08)
    v = POR_CODIGO["T2M"]
    verano = caso.interrogar(serie, v, (6, 7, 8))
    invierno = caso.interrogar(serie, v, (12, 1, 2))
    assert verano.resolucion == "anual" and verano.por_temporada and verano.temporada == "junio a agosto"
    assert verano.nivel in ("solida", "fuerte") and verano.pendiente_decada == pytest.approx(0.8, abs=0.15)
    assert invierno.nivel in ("sin", "indicios")
    assert "años" in verano.muestra and verano.n == len(verano.anual)


def test_la_tendencia_por_mes_ubica_el_cambio_en_los_meses_correctos():
    tabla = caso.tendencia_por_mes(_mensual(pendiente_verano=0.08), POR_CODIGO["T2M"])
    assert len(tabla) == 12 and set(tabla.loc[tabla["significativa"], "mes"]) == {6, 7, 8}
    assert (tabla["n"] == 40).all()
    assert (tabla["ic_bajo"] <= tabla["pendiente_decada"]).all() and (tabla["pendiente_decada"] <= tabla["ic_alto"]).all()


def test_loess_sigue_una_curva_que_la_recta_no_puede_seguir():
    from expediente import estadistica as est
    x = np.arange(1980, 2026, dtype=float)
    y = np.abs(x - 2003) * 0.1  # baja y luego sube: la recta global es casi plana
    curva = est.loess(x, y, 0.4)
    assert np.abs(curva - y).max() < 0.4 and curva[0] > curva[23] + 1.5 and curva[-1] > curva[23] + 1.5
    # Sobre una recta exacta, la regresión local la reproduce.
    assert np.allclose(est.loess(x, 2 + 0.3 * x, 0.5), 2 + 0.3 * x)


# ---------- índices de extremos con datos diarios ----------

def _diarios(anios=30, calentamiento=0.0):
    from expediente import extremos
    rng = np.random.default_rng(5)
    dias = pd.date_range("1981-01-01", f"{1980 + anios}-12-31", freq="D")
    ciclo = 10 * np.sin(2 * np.pi * (dias.dayofyear - 105) / 365.25)
    maxima = 25 + ciclo + rng.normal(0, 2, dias.size) + calentamiento * (dias.year - 1981)
    lluvia = np.where(rng.random(dias.size) < 0.2, rng.gamma(1.5, 8, dias.size), 0.0)
    return extremos, pd.DataFrame({"T2M_MAX": maxima, "T2M_MIN": maxima - 12, "PRECTOTCORR": lluvia}, index=dias)


def test_racha_mas_larga():
    from expediente.extremos import racha_mas_larga
    assert racha_mas_larga(np.array([1, 1, 0, 1, 1, 1, 0], dtype=bool)) == 3
    assert racha_mas_larga(np.zeros(5, dtype=bool)) == 0


def test_los_indices_de_extremos_se_calculan_como_se_definen():
    extremos, diarios = _diarios()
    diarios = diarios.loc[:"2010-06-30"]  # el último año queda incompleto
    indices = extremos.indices_anuales(diarios)
    assert list(indices.index.year) == list(range(1981, 2010))  # 2010 no cuenta: le faltan días
    de_1990 = diarios.loc["1990"]
    assert indices.loc["1990-07-01", "EXT_TXX"] == pytest.approx(de_1990["T2M_MAX"].max())
    assert indices.loc["1990-07-01", "EXT_RX1"] == pytest.approx(de_1990["PRECTOTCORR"].max())
    assert indices.loc["1990-07-01", "EXT_R10"] == (de_1990["PRECTOTCORR"] >= 10).sum()
    assert indices.loc["1990-07-01", "EXT_DIAS_35"] == (de_1990["T2M_MAX"] > 35).sum()
    # Sin tendencia, cerca del 10 % de los días supera el percentil 90 del periodo base.
    assert indices["EXT_DIAS_CALOR"].mean() == pytest.approx(36.5, abs=4)


def test_un_calentamiento_aumenta_los_dias_de_calor_y_se_detecta():
    extremos, diarios = _diarios(anios=40, calentamiento=0.05)
    indices = extremos.indices_anuales(diarios)
    r = caso.interrogar(indices["EXT_DIAS_CALOR"], POR_CODIGO["EXT_DIAS_CALOR"])
    assert r.resolucion == "anual" and not r.por_temporada and r.sube and r.nivel in ("solida", "fuerte")
    assert r.n == 40 and "años" in r.muestra
    with pytest.raises(caso.CasoImposible):
        caso.interrogar(indices["EXT_DIAS_CALOR"], POR_CODIGO["EXT_DIAS_CALOR"], (6, 7, 8))
