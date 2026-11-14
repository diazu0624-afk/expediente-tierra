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
    assert r.pruebas[3].nombre == "Sin un año clave"
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
    assert r == {"sube": 50.0, "baja": 50.0, "celdas": 4}
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
