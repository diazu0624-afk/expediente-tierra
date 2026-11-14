import numpy as np
import pandas as pd
import pytest
from scipy import stats

from expediente import estadistica as est


def _ar1(rng, n, phi, sigma=1.0):
    ruido = rng.normal(0, sigma, n)
    x = np.empty(n)
    x[0] = ruido[0] / np.sqrt(1 - phi**2)
    for k in range(1, n):
        x[k] = phi * x[k - 1] + ruido[k]
    return x


def test_quitar_ciclo_estacional_deja_solo_la_senal():
    indice = pd.date_range("1990-01-01", periods=240, freq="MS")
    ciclo = 10 * np.sin(2 * np.pi * (indice.month - 1) / 12)
    tendencia = 0.01 * np.arange(240)
    anomalias, climatologia = est.quitar_ciclo_estacional(pd.Series(ciclo + tendencia, index=indice))
    assert len(climatologia) == 12
    # Sin ciclo: el promedio de cada mes del calendario queda en cero...
    assert np.allclose(anomalias.groupby(anomalias.index.month).mean(), 0, atol=1e-9)
    # ...y la tendencia sobrevive.
    t = np.arange(240) / 12
    assert est.regresion_lineal(t, anomalias.to_numpy()).pendiente == pytest.approx(0.12, rel=0.02)


def test_mann_kendall_coincide_con_pymannkendall():
    mk = pytest.importorskip("pymannkendall")
    rng = np.random.default_rng(1)
    for x in (rng.normal(size=60) + 0.03 * np.arange(60),
              rng.integers(0, 5, size=80).astype(float)):  # con muchos empates
        mio, ref = est.mann_kendall(x), mk.original_test(x)
        assert mio.s == ref.s
        assert mio.var_s == pytest.approx(ref.var_s)
        assert mio.z == pytest.approx(ref.z)
        assert mio.p == pytest.approx(ref.p)
        assert mio.tau == pytest.approx(ref.Tau)


def test_mann_kendall_serie_constante_no_acusa():
    resultado = est.mann_kendall(np.ones(30))
    assert resultado.z == 0 and resultado.p == 1


def test_pendiente_sen_recupera_la_recta_e_ignora_atipicos():
    t = np.arange(50, dtype=float)
    y = 2.0 + 0.5 * t
    y[[5, 30]] += 100  # dos valores disparatados
    sen = est.pendiente_sen(t, y)
    assert sen.pendiente == pytest.approx(0.5, abs=0.01)
    assert sen.ic_bajo <= sen.pendiente <= sen.ic_alto
    assert est._mediana_de_pendientes(t, y) == pytest.approx(sen.pendiente)


def test_regresion_ingenua_coincide_con_scipy():
    rng = np.random.default_rng(2)
    t = np.arange(100, dtype=float)
    y = 0.02 * t + rng.normal(size=100)
    mia, ref = est.regresion_lineal(t, y), stats.linregress(t, y)
    assert mia.pendiente == pytest.approx(ref.slope)
    assert mia.intercepto == pytest.approx(ref.intercept)
    assert mia.p_ingenuo == pytest.approx(ref.pvalue)


def test_la_memoria_reduce_la_muestra_efectiva_y_sube_p():
    rng = np.random.default_rng(3)
    t = np.arange(400, dtype=float)
    y = _ar1(rng, 400, 0.8) + 0.002 * t
    reg = est.regresion_lineal(t, y)
    assert reg.r1 > 0.6
    assert reg.n_efectivo < reg.n / 4
    assert reg.p > reg.p_ingenuo
    assert reg.ic_bajo < reg.pendiente < reg.ic_alto


def test_regresion_con_ajuste_perfecto():
    t = np.arange(20, dtype=float)
    reg = est.regresion_lineal(t, 3 * t + 1)
    assert reg.pendiente == pytest.approx(3) and reg.p == 0


def test_sin_memoria_positiva_no_se_corrige():
    t = np.arange(40, dtype=float)
    y = np.tile([1.0, -1.0], 20) + 0.01 * t  # alterna: memoria negativa
    resultado = est.mann_kendall_sin_memoria(t, y)
    assert not resultado.corregida
    assert resultado.prueba == est.mann_kendall(y)


def test_sin_memoria_estima_la_memoria_y_detecta_la_tendencia():
    rng = np.random.default_rng(4)
    t = np.arange(480, dtype=float) / 12
    y = 0.3 * t + _ar1(rng, 480, 0.6)
    resultado = est.mann_kendall_sin_memoria(t, y)
    assert resultado.corregida
    assert resultado.r1 == pytest.approx(0.6, abs=0.1)
    assert resultado.prueba.p < 0.05 and resultado.prueba.s > 0
    assert resultado.prueba.p > est.mann_kendall(y).p  # corregir siempre resta certeza


def test_sin_memoria_baja_los_falsos_positivos():
    rng = np.random.default_rng(5)
    t = np.arange(200, dtype=float)
    ingenuos = corregidos = 0
    repeticiones = 300
    for _ in range(repeticiones):
        y = _ar1(rng, 200, 0.7)  # sin tendencia
        ingenuos += est.mann_kendall(y).p < 0.05
        corregidos += est.mann_kendall_sin_memoria(t, y).prueba.p < 0.05
    assert ingenuos / repeticiones > 0.25  # la prueba ingenua acusa de más
    assert corregidos / repeticiones < 0.10


def test_memoria_de_residuos_corrige_el_sesgo():
    rng = np.random.default_rng(8)
    t = np.arange(45, dtype=float)
    crudas, corregidas = [], []
    for _ in range(600):
        y = _ar1(rng, 45, 0.4)
        residuos = y - np.polyval(np.polyfit(t, y, 1), t)
        crudas.append(est.autocorrelacion_lag1(residuos))
        corregidas.append(est.memoria_de_residuos(residuos))
    assert np.mean(crudas) < 0.33  # la estimación cruda se queda corta
    assert np.mean(corregidas) == pytest.approx(0.4, abs=0.04)


def test_bootstrap_cubre_la_pendiente_real_y_excluye_el_cero_si_hay_tendencia():
    rng = np.random.default_rng(6)
    t = np.arange(300, dtype=float) / 12
    y = 0.5 * t + _ar1(rng, 300, 0.4)
    bajo, alto = est.ic_historias_alternativas(t, y)
    assert bajo < 0.5 < alto
    assert bajo > 0
    assert est.ic_historias_alternativas(t, y) == (bajo, alto)  # reproducible


def test_triangulo_cuenta_todas_las_ventanas():
    anios = np.arange(1990, 2020)
    valores = 0.1 * (anios - 1990)
    tri = est.triangulo_de_ventanas(anios, valores, largo_min=10)
    n = len(anios) - 10 + 1
    assert len(tri) == n * (n + 1) // 2
    assert (tri["fin"] - tri["inicio"] >= 9).all()
    assert np.allclose(tri["pendiente"], 0.1)
    assert (tri["p"] < 0.05).all()


def test_anios_para_detectar_formula_de_weatherhead():
    # Sin memoria: n* = (3.3·sigma/omega)^(2/3)
    assert est.anios_para_detectar(0.1, 1.0, 0.0) == pytest.approx(33 ** (2 / 3))
    # La memoria y el ruido alargan la espera; una tendencia mayor la acorta.
    base = est.anios_para_detectar(0.1, 1.0, 0.5)
    assert base > est.anios_para_detectar(0.1, 1.0, 0.0)
    assert est.anios_para_detectar(0.1, 2.0, 0.5) > base
    assert est.anios_para_detectar(0.2, 1.0, 0.5) < base
    assert est.anios_para_detectar(0.0, 1.0, 0.5) == float("inf")
    # Con un dato por año el mismo ruido pesa raíz(12) veces más.
    assert est.anios_para_detectar(0.1, 1.0, 0.0, por_anio=1) == pytest.approx((33 * 12**0.5) ** (2 / 3))


def test_anios_para_detectar_da_90_por_ciento_de_deteccion():
    # Simulación: con n* años de datos, ~90 % de las series deben dar positivo.
    rng = np.random.default_rng(7)
    omega, sigma, phi = 0.05, 1.0, 0.3
    anios = est.anios_para_detectar(omega, sigma * 1.0 / np.sqrt(1 - phi**2), phi)
    n = int(round(anios * 12))
    t = np.arange(n) / 12
    detectadas = sum(
        est.regresion_lineal(t, omega * t + _ar1(rng, n, phi, sigma)).p < 0.05
        for _ in range(400)
    )
    assert 0.82 < detectadas / 400 < 0.97


def test_benjamini_hochberg_ejemplo_conocido():
    p = np.array([0.01, 0.04, 0.03, 0.005, 0.5])
    ajustados = est.benjamini_hochberg(p)
    assert ajustados == pytest.approx([0.025, 0.05, 0.05, 0.025, 0.5])
    assert (ajustados >= p).all()
