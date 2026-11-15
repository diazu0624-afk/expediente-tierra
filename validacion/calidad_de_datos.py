"""Filtro de calidad de las variables: cobertura, saltos artificiales y acuerdo entre fuentes.

Para cada variable y sitio calcula:
- cobertura: porcentaje de meses con dato dentro de su propio registro;
- salto: el mayor escalón entre los dos tramos de la regresión por tramos, medido en
  desviaciones estándar de la variación interanual, y el año en que ocurre. Si sitios muy
  distantes saltan en el mismo año, el salto es del instrumento y no del clima;
- acuerdo: correlación de las anomalías mensuales con otra fuente que mide lo mismo.

Uso:  .venv/bin/python -m validacion.calidad_de_datos
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from expediente import caso, estadistica as est
from expediente.sitio import tabla_del_punto
from expediente.variables import CATALOGO

SITIOS = [("Monterrey", 25.68, -100.32), ("Nueva Delhi", 28.61, 77.21), ("Pekín", 39.90, 116.40),
          ("Svalbard", 78.22, 15.65), ("Niamey", 13.51, 2.11), ("Manaos", -3.10, -60.02),
          ("Golfo de México", 25.0, -90.0)]
# Variable -> otra fuente independiente que mide (casi) lo mismo.
PAREJAS = {"MODIS_AOD": "AOD_55", "OMI_OZONO": "TO3", "MODIS_EVI": "MODIS_NDVI", "MAR_SST": "TS",
           "MAR_SST_MODIS": "MAR_SST", "GPM_LLUVIA": "PRECTOTCORR", "FLDAS_ESCURRIMIENTO": "PRECTOTCORR"}


def salto(anual) -> tuple[int, float]:
    """Año y tamaño (en desviaciones estándar) del mayor escalón entre dos tramos."""
    anios, valores = anual.index.to_numpy(dtype=float), anual.to_numpy()
    cambio = est.punto_de_cambio(anios, valores)
    if cambio is None:
        return 0, 0.0
    antes = cambio.antes.intercepto + cambio.antes.pendiente * cambio.anio
    despues = cambio.despues.intercepto + cambio.despues.pendiente * (cambio.anio + 1)
    residuos = valores - np.polyval(np.polyfit(anios, valores, 1), anios)
    return cambio.anio, float(abs(despues - antes) / (residuos.std(ddof=1) or 1))


if __name__ == "__main__":
    tablas = {nombre: tabla_del_punto(lat, lon) for nombre, lat, lon in SITIOS}
    print(f"{'variable':22s}{'sitios':>7s}{'años':>6s}{'cobertura':>11s}{'salto máx':>11s}  {'años del salto (sitios)':34s}{'acuerdo con otra fuente'}")
    for v in CATALOGO:
        coberturas, saltos, anios_salto, correlaciones, signos, largos = [], [], [], [], [], []
        for nombre, tabla in tablas.items():
            if v.codigo not in tabla:
                continue
            serie = tabla[v.codigo].loc[str(v.desde):].dropna()
            anual = caso.promedios_anuales(serie)
            if len(anual) < caso.MIN_ANIOS:
                continue
            meses = (serie.index[-1].year - serie.index[0].year) * 12 + serie.index[-1].month - serie.index[0].month + 1
            coberturas.append(100 * len(serie) / meses); largos.append(len(anual))
            anio, tamano = salto(anual); saltos.append(tamano); anios_salto.append(anio)
            pareja = PAREJAS.get(v.codigo)
            if pareja and pareja in tabla:
                a, _ = est.quitar_ciclo_estacional(serie)
                b, _ = est.quitar_ciclo_estacional(tabla[pareja].dropna())
                junto = a.to_frame("a").join(b.rename("b"), how="inner").dropna()
                if len(junto) > 60:
                    correlaciones.append(float(junto.corr().iloc[0, 1]))
                    t = np.arange(len(junto))
                    signos.append(np.sign(np.polyfit(t, junto["a"], 1)[0]) == np.sign(np.polyfit(t, junto["b"], 1)[0]))
        if not coberturas:
            print(f"{v.codigo:22s}{'0':>7s}   sin sitios con datos suficientes"); continue
        repetidos = ", ".join(f"{a} ({n})" for a, n in Counter(anios_salto).most_common(3))
        acuerdo = (f"{PAREJAS[v.codigo]}: r = {np.median(correlaciones):.2f}, mismo signo en {sum(signos)}/{len(signos)}"
                   if correlaciones else "")
        print(f"{v.codigo:22s}{len(coberturas):7d}{int(np.median(largos)):6d}{np.median(coberturas):10.0f}%{max(saltos):10.1f}σ  {repetidos:34s}{acuerdo}")
