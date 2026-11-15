"""Recorrido animado de la herramienta, con datos reales.

Genera `static/demo.html` (español) y `static/demo_en.html` (inglés): una animación de pantalla
completa (16:9) que muestra el flujo completo, de empezar un análisis a descargar el informe,
con las funciones de la herramienta. Sirve de dos maneras: incrustada en la página de inicio de
la app, o abierta sola en el navegador para grabarla como video.

Los textos de la plantilla van en los dos idiomas con la forma ⟦español¦english⟧.

Uso:  .venv/bin/python -m expediente.demo
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import caso, datos_gee, estadistica as est, idioma, laboratorio, region, veredicto
from .idioma import T
from .sitio import tabla_del_punto
from .variables import CATALOGO, POR_CODIGO

ESTATICOS = Path(__file__).resolve().parent.parent / "static"
RUTAS = {"es": ESTATICOS / "demo.html", "en": ESTATICOS / "demo_en.html"}
DELHI = (28.61, 77.21)
PEKIN = (39.90, 116.40)
LADO = 8
FRACCION_LOESS = 0.5  # la misma de graficas.FRACCION_LOESS
# El recuadro de México tal como lo entrega datos_gee.buscar_pais: así la animación se puede
# regenerar con los datos guardados, sin sesión de Earth Engine.
MEXICO = datos_gee.Pais("Mexico", 14.534685594615368, 32.71878297063941, -118.36763759064785, -86.72663880218043)
MESES_DE_QUEMA = (10, 11)


def _redondo(valores, cifras: int = 3) -> list:
    return [None if not np.isfinite(x) else round(float(x), cifras) for x in valores]


def _serie(r: caso.Interrogatorio) -> dict:
    """La serie analizada, su media móvil, la recta, el intervalo de confianza y la curva LOESS."""
    centro = r.t.mean()
    altura = r.regresion.intercepto + r.regresion.pendiente * centro
    return {
        "t": _redondo(r.t),
        "y": _redondo(r.y),
        "suave": _redondo(pd.Series(r.y).rolling(12, center=True, min_periods=6).mean()),
        "recta": _redondo(altura + r.regresion.pendiente * (r.t - centro)),
        "bajo": _redondo(altura + r.ic_historias[0] * (r.t - centro)),
        "alto": _redondo(altura + r.ic_historias[1] * (r.t - centro)),
        "loess": _redondo(est.loess(r.t, r.y, FRACCION_LOESS)),
        "decada": caso.numero(r.pendiente_decada, signo=True),
    }


def _celdas(mapa: pd.DataFrame) -> list:
    return [[float(f.lat), float(f.lon), round(float(f.pendiente_decada), 2), int(f.significativa)] for f in mapa.itertuples()]


def _territorio(cubo: pd.DataFrame, codigo: str, nombre: str, celda: float) -> dict:
    """Mapa de tendencias y promedio de un país o del mundo."""
    variable = POR_CODIGO[codigo]
    mapa = region.mapa_de_tendencias(cubo, variable)
    r = caso.interrogar(region.promedio_regional(cubo), variable)
    return {"nombre": nombre, "variable": variable.nombre, "celdas": _celdas(mapa), "celda": celda,
            "decada": caso.numero(r.pendiente_decada, signo=True), "unidad": variable.unidad,
            "sube": round(region.resumen(mapa)["sube"]), "total": len(mapa), "nivel": caso.NIVELES[r.nivel]}


def datos_de_demo() -> dict:
    """Todo lo que la animación muestra, calculado con el mismo código que usa la app y en el
    idioma de la sesión."""
    delhi, pekin = T("Nueva Delhi, India", "New Delhi, India"), T("Pekín, China", "Beijing, China")
    lat, lon = DELHI
    tabla = tabla_del_punto(lat, lon)
    exploracion = caso.escanear(tabla).dropna(subset=["estandarizada"])
    agua = POR_CODIGO["GRACE_AGUA"]
    r = caso.interrogar(tabla["GRACE_AGUA"], agua)
    mapa = region.mapa_de_tendencias(datos_gee.recortar(datos_gee.descargar_cubo(lat, lon, "GRACE_AGUA"), lat, lon, LADO), agua)
    resumen = region.resumen(mapa)
    aerosoles = POR_CODIGO["AOD_55"]
    a = caso.interrogar(tabla["AOD_55"], aerosoles)
    b = caso.interrogar(tabla_del_punto(*PEKIN)["AOD_55"], aerosoles)

    # ¿En qué meses? Aerosoles medidos por MODIS: todo el año frente a octubre y noviembre.
    satelite = POR_CODIGO["MODIS_AOD"]
    por_mes = caso.tendencia_por_mes(tabla["MODIS_AOD"], satelite)
    anual, temporada = caso.interrogar(tabla["MODIS_AOD"], satelite), caso.interrogar(tabla["MODIS_AOD"], satelite, MESES_DE_QUEMA)
    # Extremos: noches tropicales, con los datos de cada día.
    noches = POR_CODIGO["EXT_NOCHES_20"]
    n = caso.interrogar(tabla["EXT_NOCHES_20"], noches)
    # Laboratorio: 300 series sin tendencia con autocorrelación de 0.6.
    sim = laboratorio.simular(anios=30, phi=0.6, series=300, semilla=0)
    ejemplo = sim.ejemplo
    recta = np.polyval(np.polyfit(ejemplo.t, ejemplo.y, 1), ejemplo.t)

    return {
        "sitio": delhi,
        "variables": len(CATALOGO),
        "exploracion": {
            "barras": [{"nombre": f.nombre, "valor": round(float(f.estandarizada), 2), "firme": bool(f.significativa),
                        "elegida": f.codigo == "GRACE_AGUA"} for f in exploracion.head(10).itertuples()],
            "validas": len(exploracion), "clasicas": int((exploracion["p_clasica"] < est.ALFA).sum()),
            "firmes": int(exploracion["significativa"].sum())},
        "mapa": {"celdas": _celdas(mapa), "sitio": [lat, lon], "baja": round(resumen["baja"]), "sube": round(resumen["sube"]),
                 "total": int(resumen["celdas"]), "lado": LADO, "unidad": agua.unidad},
        "serie": _serie(r),
        "pruebas": [{"nombre": p.nombre, "resultado": p.resultado, "pasa": bool(p.aprobada)} for p in r.pruebas],
        "resultado": {"titular": veredicto.redactar(r).titular, "unidad": agua.unidad, "decada": round(r.pendiente_decada),
                      "total": round(r.cambio_total), "anios": round(r.anios_de_datos), "aprobadas": r.aprobadas,
                      "nivel": caso.NIVELES_CORTOS[r.nivel], "etiqueta": caso.NIVELES[r.nivel]},
        "meses": {"variable": satelite.nombre, "unidad": satelite.unidad,
                  "barras": [{"mes": f.nombre[:3], "valor": None if pd.isna(f.pendiente_decada) else round(float(f.pendiente_decada), 3),
                              "bajo": None if pd.isna(f.ic_bajo) else round(float(f.ic_bajo), 3),
                              "alto": None if pd.isna(f.ic_alto) else round(float(f.ic_alto), 3),
                              "firme": bool(f.significativa)} for f in por_mes.itertuples()],
                  "anual": {"decada": caso.numero(anual.pendiente_decada, signo=True), "nivel": caso.NIVELES[anual.nivel]},
                  "temporada": {"nombre": temporada.temporada, "decada": caso.numero(temporada.pendiente_decada, signo=True),
                                "nivel": caso.NIVELES[temporada.nivel]}},
        "extremos": {"variable": noches.nombre, "definicion": noches.definicion, "unidad": noches.unidad,
                     "serie": _serie(n), "nivel": caso.NIVELES[n.nivel], "elegido": noches.nombre,
                     "indices": [v.nombre for v in CATALOGO if v.anual]},
        "territorios": {
            "pais": _territorio(datos_gee.descargar_cubo_del_pais(MEXICO, "FLDAS_TEMP"), "FLDAS_TEMP", T("México", "Mexico"),
                                datos_gee.celda_para("FLDAS_TEMP", MEXICO.lat_min, MEXICO.lat_max, MEXICO.lon_min, MEXICO.lon_max)),
            "mundo": _territorio(datos_gee.descargar_cubo_del_mundo("MAR_SST"), "MAR_SST", T("Mundo", "World"),
                                 datos_gee.celda_para("MAR_SST", *datos_gee.MUNDO))},
        "comparacion": {"variable": aerosoles.nombre, "a": {"nombre": delhi, **_serie(a)}, "b": {"nombre": pekin, **_serie(b)}},
        "laboratorio": {"series": sim.series, "clasica": round(sim.clasica), "corregida": round(sim.corregida),
                        "p_clasica": caso.valor_p(ejemplo.p_clasica), "p_corregida": caso.valor_p(ejemplo.p_corregida),
                        "serie": {"t": _redondo(ejemplo.t), "y": _redondo(ejemplo.y), "recta": _redondo(recta),
                                  "suave": _redondo(pd.Series(ejemplo.y).rolling(12, center=True, min_periods=6).mean())}},
    }


def demo_html(datos_demo: dict, reproducir_sola: bool = True) -> str:
    """La animación completa en un solo archivo HTML, en el idioma de la sesión."""
    # Los números de numpy no son JSON: se convierten a su equivalente de Python.
    como_json = json.dumps(datos_demo, ensure_ascii=False, default=lambda x: x.item())
    grupo = 2 if idioma.en_ingles() else 1
    plantilla = re.sub(r"⟦(.*?)¦(.*?)⟧", lambda m: m.group(grupo), PLANTILLA, flags=re.S)
    return (plantilla.replace("__DATOS__", como_json).replace("__IDIOMA__", idioma.actual())
            .replace("__AUTO__", "true" if reproducir_sola else "false"))


def escribir() -> None:
    """Genera la animación en los dos idiomas."""
    ESTATICOS.mkdir(exist_ok=True)
    antes = idioma.actual()
    try:
        for lengua, ruta in RUTAS.items():
            idioma.fijar(lengua)
            ruta.write_text(demo_html(datos_de_demo()), encoding="utf-8")
            print(f"Animación escrita en {ruta} ({ruta.stat().st_size / 1024:.0f} KB)")
    finally:
        idioma.fijar(antes)


PLANTILLA = r"""<!doctype html>
<html lang="__IDIOMA__"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expediente Tierra: ⟦recorrido¦tour⟧</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@600;700;800&family=Public+Sans:wght@400;500;600&display=swap');
:root { --k:.5; /* factor que comprime todos los retrasos de las animaciones */ --tinta:#0b0b0b; --tinta2:#52514e; --tenue:#898781; --filete:#d9d8d2; --fondo:#ffffff; --plano:#f4f4f2;
  --acento:#0b3d91; --azul:#2a78d6; --rojo:#e34948; --naranja:#eb6834; --suave:cubic-bezier(.16,1,.3,1); --transito:cubic-bezier(.65,0,.35,1); }
* { box-sizing: border-box; margin: 0; }
html, body { height: 100%; background: var(--fondo); overflow: hidden; }
body { font-family: 'Public Sans', system-ui, -apple-system, 'Segoe UI', sans-serif; color: var(--tinta); }
#marco { position: fixed; inset: 0; display: grid; place-items: center; background: var(--fondo); }
#lienzo { width: 1920px; height: 1080px; position: absolute; left: 0; top: 0; transform-origin: 0 0; background: var(--fondo); overflow: hidden; }
.mono { font-family: 'DM Mono', ui-monospace, Menlo, monospace; }
.eyebrow { font: 400 22px/1.3 'DM Mono', monospace; letter-spacing: .1em; text-transform: uppercase; color: var(--tinta2); }
h1, h2 { font-family: 'Inter', system-ui, sans-serif; font-weight: 800; letter-spacing: -0.035em; }
h2 { font-size: 78px; line-height: 1.02; }
p.lead { font-size: 34px; line-height: 1.38; color: var(--tinta2); max-width: 1180px; }

/* marco fijo: marca, contador y avance */
.marca { position: absolute; left: 96px; top: 54px; font: 700 26px 'Inter', sans-serif; letter-spacing: -0.02em; z-index: 5; }
.contador { position: absolute; right: 96px; top: 58px; font: 400 20px 'DM Mono', monospace; letter-spacing: .08em; color: var(--tinta2); z-index: 5; }
.avance { position: absolute; left: 0; bottom: 0; height: 6px; width: 100%; background: var(--plano); z-index: 5; }
.avance i { display: block; height: 100%; width: 0; background: var(--tinta); }

/* escenas */
.escena { position: absolute; inset: 0; padding: 150px 96px 80px; opacity: 0; pointer-events: none; transform: translateY(46px);
  transition: opacity .85s var(--transito), transform .85s var(--transito); will-change: opacity, transform; }
.escena.activa { opacity: 1; transform: none; }
.escena.saliente { opacity: 0; transform: translateY(-46px); }
.atras .escena { transform: translateY(-46px); } .atras .escena.activa { transform: none; } .atras .escena.saliente { transform: translateY(46px); }
.escena .cab { border-top: 3px solid var(--tinta); padding-top: 22px; display: flex; gap: 26px; align-items: baseline; margin-bottom: 30px; }
.escena .cab .n { font: 400 24px 'DM Mono', monospace; color: var(--tinta2); }
.escena .cab h2 { font-size: 62px; }
.dos { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: start; }

/* animaciones: solo corren en la escena activa; --d es el retraso */
.escena .a { opacity: 0; }
.escena.activa .a { animation: sube .8s var(--suave) both; animation-delay: calc(var(--d, 0s) * var(--k) + .3s); }
.escena.activa .crece { animation: crece .8s var(--suave) both; animation-delay: calc(var(--d, 0s) * var(--k) + .3s); transform-origin: var(--origen, left) center; }
.escena.activa .traza { stroke-dasharray: 1; stroke-dashoffset: 1; animation: traza calc(var(--t, 2.2s) * var(--k)) cubic-bezier(.4,0,.2,1) both; animation-delay: calc(var(--d, 0s) * var(--k) + .3s); }
.escena.activa .funde { animation: funde .7s ease both; animation-delay: calc(var(--d, 0s) * var(--k) + .3s); }
.escena .crece { transform: scaleX(0); } .escena .funde { opacity: 0; }
@keyframes sube { from { opacity: 0; transform: translateY(26px); } to { opacity: 1; transform: none; } }
@keyframes crece { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes traza { to { stroke-dashoffset: 0; } }
@keyframes funde { from { opacity: 0; } to { opacity: 1; } }
@keyframes marca { 0%,100% { transform: scale(1); } 50% { transform: scale(.96); } }

/* 1 y 11: portada y cierre */
.portada { display: flex; flex-direction: column; justify-content: center; padding-top: 80px; }
.portada h1 { font-size: 190px; line-height: .96; margin: 26px 0 34px; }
.portada .lead { font-size: 42px; color: var(--tinta); }
.datos-cierre { display: flex; gap: 58px; margin-top: 70px; border-top: 3px solid var(--tinta); padding-top: 26px; }
.datos-cierre .v { font: 500 76px/1 'DM Mono', monospace; letter-spacing: -0.04em; }
.datos-cierre .e { margin-top: 12px; }

/* 2: el problema */
.medidor { margin-top: 44px; }
.medidor .fila { display: grid; grid-template-columns: 430px 1fr; gap: 40px; align-items: center; margin-bottom: 44px; }
.medidor .v { font: 500 96px/1 'DM Mono', monospace; letter-spacing: -0.05em; white-space: nowrap; }
.medidor .pista { height: 34px; background: var(--plano); position: relative; }
.medidor .pista b { position: absolute; left: 0; top: 0; bottom: 0; display: block; }
.medidor .pista .ideal { position: absolute; top: -12px; bottom: -12px; left: 7.8%; width: 2px; background: var(--tinta); }
.medidor .pista .ideal span { position: absolute; top: -34px; left: -6px; white-space: nowrap; font: 400 18px 'DM Mono', monospace; color: var(--tinta2); }

/* 3: empezar un análisis */
.tarjeta { border: 1.5px solid var(--filete); padding: 44px 48px; display: grid; grid-template-columns: 1.15fr 1fr 1fr; gap: 56px; }
.tarjeta .campo { font: 500 26px 'Public Sans', sans-serif; margin-bottom: 20px; }
.opcion { display: flex; align-items: center; gap: 16px; font-size: 27px; padding: 8px 0; color: var(--tinta); }
.opcion i { width: 24px; height: 24px; border-radius: 50%; border: 2px solid var(--tenue); display: grid; place-items: center; flex: none; }
.opcion i::after { content: ""; width: 12px; height: 12px; border-radius: 50%; background: var(--acento); transform: scale(0); }
.escena.activa .opcion.sel i { animation: borde .01s linear both; animation-delay: calc(var(--d) * var(--k) + .3s); }
.escena.activa .opcion.sel i::after { animation: punto .45s var(--suave) both; animation-delay: calc(var(--d) * var(--k) + .3s); }
@keyframes borde { to { border-color: var(--acento); } }
@keyframes punto { to { transform: scale(1); } }
.selector { border: 1.5px solid var(--filete); background: var(--plano); padding: 16px 20px; font-size: 27px; display: flex; justify-content: space-between; }
.boton { display: inline-block; margin-top: 40px; background: var(--acento); color: #fff; font: 600 28px 'Public Sans', sans-serif; padding: 20px 34px; }
.escena.activa .boton.pulsa { animation: sube .8s var(--suave) both, marca .45s ease 1; animation-delay: calc(var(--d) * var(--k) + .3s), calc(var(--d) * var(--k) + 1.2s); }

/* 4: exploración */
.barras { display: grid; grid-template-columns: 500px 1fr; column-gap: 26px; row-gap: 15px; align-items: center; margin-top: 8px; }
.barras .rot { text-align: right; font-size: 23px; white-space: nowrap; }
.barras .eje { height: 34px; position: relative; }
.barras .eje::before { content: ""; position: absolute; left: 50%; top: -9px; bottom: -9px; width: 1.5px; background: var(--filete); }
.barras .eje b { position: absolute; top: 3px; bottom: 3px; display: block; }
.barras .eje span { position: absolute; top: 3px; font: 400 21px/28px 'DM Mono', monospace; color: var(--tinta2); }
.barras .elegida .rot { font-weight: 600; }
.nota { font-size: 24px; line-height: 1.45; color: var(--tinta2); margin-top: 30px; max-width: 1500px; }

/* 5: mapa */
.leyenda-mapa { display: flex; align-items: center; gap: 16px; font: 400 20px 'DM Mono', monospace; color: var(--tinta2); margin-top: 18px; width: 720px; }
.leyenda-mapa div { flex: 1; height: 14px; background: linear-gradient(to right, rgb(24,79,149), rgb(109,167,236), rgb(240,239,236), rgb(238,143,142), rgb(177,43,43)); }
.cifra { border-top: 2px solid var(--tinta); padding-top: 18px; margin-bottom: 44px; }
.cifra .v { font: 500 112px/1 'DM Mono', monospace; letter-spacing: -0.05em; margin: 14px 0 10px; }
.cifra .u { font-size: 26px; color: var(--tinta2); line-height: 1.4; }

/* 6 y 9: gráficas */
.leyenda { display: flex; gap: 40px; font-size: 23px; color: var(--tinta2); margin-bottom: 10px; }
.leyenda i { display: inline-block; width: 40px; border-top: 4px solid; vertical-align: middle; margin-right: 12px; }
.leyenda i.banda { height: 18px; border: 0; background: rgba(11,11,11,.11); }
svg text { font-family: 'DM Mono', monospace; font-size: 19px; fill: var(--tenue); }
svg text.rotulo { font-size: 23px; fill: var(--tinta); }

/* 7: pruebas */
.prueba { display: grid; grid-template-columns: 150px 1fr; gap: 30px; align-items: center; border: 1.5px solid var(--filete); padding: 19px 30px; margin-bottom: 14px; }
.prueba .estado { font: 500 22px 'Public Sans', sans-serif; color: #0a6b2d; background: #e6f4ea; padding: 7px 14px; display: inline-flex; align-items: center; gap: 9px; justify-self: start; }
.prueba .estado.no { color: var(--tinta2); background: var(--plano); }
.prueba .nom { font: 600 28px 'Public Sans', sans-serif; }
.prueba .res { font-size: 24px; color: var(--tinta2); margin-top: 3px; }

/* 8: resultado */
.titular { font: 700 58px/1.12 'Inter', sans-serif; letter-spacing: -0.025em; margin: 12px 0 36px; max-width: 1500px; }
.cifras { display: grid; grid-template-columns: repeat(4, 1fr); gap: 34px; }
.cifras > div { border-top: 2px solid var(--tinta); padding-top: 16px; }
.cifras .v { font: 500 92px/1.05 'DM Mono', monospace; letter-spacing: -0.05em; margin-top: 10px; white-space: nowrap; }
.cifras .u { font-size: 23px; color: var(--tinta2); margin-top: 6px; }
.contraste { margin-top: 44px; background: var(--plano); border-left: 6px solid var(--tinta); padding: 26px 34px; display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
.contraste .v { font: 500 54px/1.1 'DM Mono', monospace; letter-spacing: -0.04em; margin-top: 8px; }
.contraste p { font-size: 23px; color: var(--tinta2); margin-top: 6px; }

/* 10: informe */
.hojas { position: relative; height: 700px; }
.hoja { position: absolute; width: 440px; height: 570px; background: #fff; border: 1.5px solid var(--filete); box-shadow: 0 30px 60px rgba(11,11,11,.13); padding: 38px 34px; }
.hoja .l { height: 9px; background: var(--filete); margin-bottom: 13px; }
.hoja .l.t { height: 22px; background: var(--tinta); width: 82%; margin: 14px 0 22px; }
.hoja .l.c { width: 60%; } .hoja .l.m { width: 38%; height: 7px; }
.hoja .regla { border-top: 2.5px solid var(--tinta); margin: 22px 0 16px; }
.escena.activa .hoja { animation: hoja 1s var(--suave) both; animation-delay: calc(var(--d) * var(--k) + .3s); }
@keyframes hoja { from { opacity: 0; transform: translateY(90px) rotate(0deg); } to { opacity: 1; transform: translateY(0) rotate(var(--giro, 0deg)); } }
.lista { list-style: none; padding: 0; margin-top: 34px; }
.lista li { font-size: 31px; padding: 15px 0; border-top: 1.5px solid var(--filete); }

/* controles: barra fija bajo el lienzo; con ?grabar=1 no existe */
#controles { position: fixed; left: 0; right: 0; bottom: 0; height: 56px; display: flex; gap: 8px; align-items: center; padding: 0 16px; background: var(--tinta); z-index: 20; }
#controles button { font: 500 14px 'Public Sans', system-ui, sans-serif; color: #fff; background: transparent; border: 1px solid rgba(255,255,255,.35); padding: 7px 14px; cursor: pointer; white-space: nowrap; }
#controles button:hover, #controles button:focus-visible { background: rgba(255,255,255,.16); outline: none; }
#controles button.principal { background: #fff; color: var(--tinta); border-color: #fff; min-width: 104px; }
#tramos { flex: 1; display: flex; gap: 4px; height: 56px; align-items: center; margin: 0 8px; }
#tramos button { flex: 1; height: 26px; padding: 0; border: 0; background: transparent; position: relative; }
#tramos button::before { content: ""; position: absolute; left: 0; right: 0; top: 10px; height: 6px; background: rgba(255,255,255,.28); }
#tramos button i { position: absolute; left: 0; top: 10px; height: 6px; width: 0; background: #fff; }
#tramos button:hover::before { background: rgba(255,255,255,.5); }
#rotulo { font: 400 12px 'DM Mono', monospace; color: rgba(255,255,255,.8); min-width: 250px; text-align: right; }
@media (prefers-reduced-motion: reduce) { .escena.activa .a, .escena.activa .crece, .escena.activa .funde, .escena.activa .traza, .escena.activa .hoja { animation-duration: .01s !important; animation-delay: 0s !important; } }

/* escenas nuevas: cifras medianas, barras verticales, índices y mapas de territorio */
.cifra.media { margin-bottom: 34px; } .cifra.media .v { font-size: 96px; } .cifra.media .u { font-size: 24px; }
.escena .alza { transform: scaleY(0); transform-box: fill-box; transform-origin: var(--origen, 50% 100%); }
.escena.activa .alza { animation: alza .7s var(--suave) both; animation-delay: calc(var(--d, 0s) * var(--k) + .3s); }
@keyframes alza { from { transform: scaleY(0); } to { transform: scaleY(1); } }
.indices { list-style: none; padding: 0; margin-top: 26px; }
.indices li { font-size: 25px; padding: 10px 0 10px 18px; border-top: 1.5px solid var(--filete); color: var(--tinta2); }
.indices li.elegido { color: var(--tinta); font-weight: 600; border-left: 6px solid var(--azul); padding-left: 12px; }
.pie-mapa { display: flex; gap: 26px; align-items: center; border-top: 2px solid var(--tinta); padding-top: 14px; margin-top: 14px; }
.pie-mapa .v { font: 500 66px/1 'DM Mono', monospace; letter-spacing: -0.05em; white-space: nowrap; }
.pie-mapa .u { font-size: 22px; line-height: 1.4; color: var(--tinta2); }
@media (prefers-reduced-motion: reduce) { .escena.activa .alza { animation-duration: .01s !important; animation-delay: 0s !important; } }
</style></head>
<body>
<div id="marco"><div id="lienzo">
  <div class="marca">Expediente Tierra</div><div class="contador" id="contador"></div>

  <section class="escena portada" data-dur="5" data-nombre="⟦Portada¦Cover⟧">
    <div class="eyebrow a">NASA Space Apps 2026 · Earth System Trend Detective</div>
    <div class="eyebrow a" style="--d:.15s;color:var(--tinta);margin-top:10px">⟦Equipo¦Team⟧ C15H25N3O</div>
    <h1 class="a" style="--d:.35s">Expediente<br>Tierra</h1>
    <p class="lead a" style="--d:.75s">⟦Herramienta para detectar tendencias en variables terrestres.¦A tool to detect trends in Earth system variables.⟧</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦El problema¦The problem⟧">
    <div class="cab a"><span class="n">01</span><h2>⟦Una gráfica que sube no prueba una tendencia¦A rising chart does not prove a trend⟧</h2></div>
    <p class="lead a" style="--d:.5s">⟦Los datos del clima tienen autocorrelación: cada mes se parece al anterior. La prueba clásica lo ignora y encuentra tendencias donde no las hay.¦Climate data are autocorrelated: each month resembles the previous one. The classic test ignores this and finds trends where there are none.⟧</p>
    <div class="medidor">
      <div class="fila a" style="--d:1.5s"><div><div class="eyebrow">⟦Falsos positivos · prueba clásica¦False positives · classic test⟧</div><div class="v">14–64 %</div></div>
        <div class="pista"><b class="crece" style="width:64%;background:var(--tinta);--d:2s"></b><div class="ideal"><span>⟦lo esperado: 5 %¦expected: 5 %⟧</span></div></div></div>
      <div class="fila a" style="--d:3.6s"><div><div class="eyebrow">⟦Falsos positivos · este método¦False positives · this method⟧</div><div class="v">3–4 %</div></div>
        <div class="pista"><b class="crece" style="width:4%;background:var(--acento);--d:4.1s"></b><div class="ideal"></div></div></div>
    </div>
    <p class="nota a" style="--d:5.6s">⟦Medido con miles de series sintéticas sin tendencia. Cinco pruebas, todas corregidas por autocorrelación.¦Measured with thousands of synthetic trend-free series. Five tests, all corrected for autocorrelation.⟧</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Empezar un análisis¦Start an analysis⟧">
    <div class="cab a"><span class="n">02</span><h2>⟦Empezar un análisis¦Start an analysis⟧</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:40px">⟦Tres preguntas: qué te interesa, dónde, y qué esperas encontrar.¦Three questions: what interests you, where, and what you expect to find.⟧</p>
    <div class="tarjeta a" style="--d:.9s">
      <div><div class="campo">⟦Tema de interés¦Topic of interest⟧</div>
        <div class="opcion"><i></i>⟦Temperatura¦Temperature⟧</div>
        <div class="opcion"><i></i>⟦Calor y lluvia extremos¦Heat and rainfall extremes⟧</div>
        <div class="opcion sel" style="--d:2.2s"><i></i>⟦Precipitación y agua¦Precipitation and water⟧</div>
        <div class="opcion"><i></i>⟦Calidad del aire¦Air quality⟧</div>
        <div class="opcion"><i></i>⟦Vegetación y cultivos¦Vegetation and crops⟧</div>
        <div class="opcion"><i></i>⟦Océano¦Ocean⟧</div></div>
      <div><div class="campo">⟦Sitio de estudio¦Study site⟧</div>
        <div class="selector"><span class="a" style="--d:3.6s" id="sitio-demo"></span><span>⌄</span></div>
        <p class="nota a" style="--d:3.9s;margin-top:22px">⟦Cualquier lugar del mundo, por nombre o por coordenadas. También un país completo o el planeta entero.¦Any place in the world, by name or by coordinates. Also a whole country or the entire planet.⟧</p></div>
      <div><div class="campo">⟦Hipótesis¦Hypothesis⟧</div>
        <div class="opcion"><i></i>⟦Está aumentando¦It is increasing⟧</div>
        <div class="opcion sel" style="--d:5.2s"><i></i>⟦Está disminuyendo¦It is decreasing⟧</div>
        <div class="opcion"><i></i>⟦No está cambiando¦It is not changing⟧</div></div>
    </div>
    <div class="boton pulsa" style="--d:6.2s">⟦Iniciar el análisis¦Start the analysis⟧</div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Exploración de variables¦Exploration of variables⟧">
    <div class="cab a"><span class="n">03</span><h2>⟦Exploración de variables¦Exploration of variables⟧</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:26px"><span id="n-validas"></span> ⟦variables con datos en este sitio, ordenadas por la magnitud de su tendencia.¦variables with data at this site, ranked by the size of their trend.⟧</p>
    <div class="dos" style="grid-template-columns: 1130px 1fr; gap: 64px">
      <div class="barras" id="barras"></div>
      <div>
        <div class="cifra media a" style="--d:4.4s"><div class="eyebrow">⟦Con la prueba clásica¦With the classic test⟧</div><div class="v" style="color:var(--tenue)" id="exp-clasicas"></div><div class="u">⟦parecerían tener tendencia¦would appear to have a trend⟧</div></div>
        <div class="cifra media a" style="--d:5.6s"><div class="eyebrow">⟦Con este método¦With this method⟧</div><div class="v" id="exp-firmes"></div><div class="u">⟦sobreviven a las correcciones por autocorrelación y por comparaciones múltiples¦survive the corrections for autocorrelation and for multiple comparisons⟧</div></div>
      </div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Distribución espacial¦Spatial distribution⟧">
    <div class="cab a"><span class="n">04</span><h2>⟦Distribución espacial¦Spatial distribution⟧</h2></div>
    <div class="dos" style="grid-template-columns: 780px 1fr">
      <div class="a" style="--d:.5s"><svg id="mapa" viewBox="0 0 620 620" width="720" height="720"></svg>
        <div class="leyenda-mapa"><span id="mapa-min"></span><div></div><span id="mapa-max"></span></div></div>
      <div>
        <p class="lead a" style="--d:.9s;margin-bottom:44px">⟦Dónde cambia: la tendencia de cada celda de la región, de 2° a 10° de lado.¦Where it changes: the trend of every cell in the region, 2° to 10° across.⟧</p>
        <div class="cifra a" style="--d:3.4s"><div class="eyebrow">⟦Tendencia negativa significativa¦Significant negative trend⟧</div><div class="v"><span data-cuenta id="mapa-baja"></span> %</div><div class="u">⟦de la región pierde agua almacenada.<br>El punto marca las celdas significativas.¦of the region is losing stored water.<br>The dot marks the significant cells.⟧</div></div>
      </div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Serie de tiempo¦Time series⟧">
    <div class="cab a"><span class="n">05</span><h2>⟦Serie de tiempo¦Time series⟧</h2></div>
    <div class="leyenda a" style="--d:.5s;gap:30px"><span><i style="border-color:#c3c2b7;border-top-width:2px"></i>⟦Anomalía mensual¦Monthly anomaly⟧</span><span><i style="border-color:var(--azul)"></i>⟦Media móvil de 12 meses¦12-month moving average⟧</span><span><i style="border-color:var(--tinta)"></i>⟦Tendencia lineal¦Linear trend⟧</span><span><i class="banda"></i>⟦Intervalo de confianza del 95 %¦95 % confidence interval⟧</span><span><i style="border-color:var(--tinta);border-top-style:dotted"></i>⟦Curva suavizada (LOESS)¦Smoothed curve (LOESS)⟧</span></div>
    <svg id="serie" viewBox="0 0 1728 640" width="1728" height="640"></svg>
    <p class="nota a" style="--d:6.6s;margin-top:6px">⟦Sin el ciclo de las estaciones queda el cambio de fondo: almacenamiento de agua terrestre medido por los satélites GRACE.¦Without the seasonal cycle the underlying change remains: terrestrial water storage measured by the GRACE satellites.⟧</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Pruebas de significancia¦Significance tests⟧">
    <div class="cab a"><span class="n">06</span><h2>⟦Pruebas de significancia¦Significance tests⟧</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:30px">⟦Una tendencia visible puede ser casualidad. Solo la que supera las cinco es sólida.¦A visible trend may be chance. Only one that passes all five is solid.⟧</p>
    <div id="pruebas"></div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Resultado¦Result⟧">
    <div class="cab a"><span class="n">07</span><h2>⟦Resultado¦Result⟧</h2></div>
    <div class="eyebrow a" style="--d:.4s" id="res-etiqueta"></div>
    <div class="titular a" style="--d:.55s" id="res-titular"></div>
    <div class="cifras">
      <div class="a" style="--d:1.3s"><div class="eyebrow">⟦Tasa de cambio¦Rate of change⟧</div><div class="v"><span data-cuenta id="res-decada"></span></div><div class="u" id="res-u1"></div></div>
      <div class="a" style="--d:1.6s"><div class="eyebrow">⟦Cambio acumulado¦Accumulated change⟧</div><div class="v"><span data-cuenta id="res-total"></span></div><div class="u" id="res-u2"></div></div>
      <div class="a" style="--d:1.9s"><div class="eyebrow">⟦Pruebas superadas¦Tests passed⟧</div><div class="v" id="res-pruebas"></div><div class="u">⟦pruebas de significancia¦significance tests⟧</div></div>
      <div class="a" style="--d:2.2s"><div class="eyebrow">⟦Nivel de evidencia¦Level of evidence⟧</div><div class="v" id="res-nivel"></div><div class="u">&nbsp;</div></div>
    </div>
    <div class="contraste a" style="--d:4.6s">
      <div><div class="eyebrow">Rodell et al. (2009), Nature</div><div class="v">4.0 ± 1.0</div><p>⟦cm por año de agua subterránea perdida, 2002–2008¦cm per year of groundwater lost, 2002–2008⟧</p></div>
      <div><div class="eyebrow">⟦Esta herramienta, misma región y periodo¦This tool, same region and period⟧</div><div class="v">3.8</div><p>⟦cm por año: dentro del margen del artículo¦cm per year: within the margin of the paper⟧</p></div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Meses del año¦Months of the year⟧">
    <div class="cab a"><span class="n">08</span><h2>⟦¿En qué meses cambia?¦In which months does it change?⟧</h2></div>
    <div class="dos" style="grid-template-columns: 1060px 1fr; gap: 70px">
      <div><div class="eyebrow a" style="--d:.4s" id="mes-titulo"></div>
        <svg id="meses" viewBox="0 0 1060 600" width="1060" height="600"></svg></div>
      <div>
        <p class="lead a" style="--d:.6s;margin-bottom:34px">⟦Una tendencia puede concentrarse en una parte del año. Cada mes se analiza por separado.¦A trend may be concentrated in one part of the year. Each month is analysed separately.⟧</p>
        <div class="cifra media a" style="--d:3.8s"><div class="eyebrow">⟦Todo el año¦The whole year⟧</div><div class="v" style="color:var(--tenue)" id="mes-anual"></div><div class="u" id="mes-anual-u"></div></div>
        <div class="cifra media a" style="--d:5s"><div class="eyebrow" id="mes-temporada-n"></div><div class="v" id="mes-temporada"></div><div class="u" id="mes-temporada-u"></div></div>
      </div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Extremos¦Extremes⟧">
    <div class="cab a"><span class="n">09</span><h2>⟦Extremos, con los datos de cada día¦Extremes, from the data of every day⟧</h2></div>
    <div class="dos" style="grid-template-columns: 1120px 1fr; gap: 60px">
      <div><div class="eyebrow a" style="--d:.4s" id="ext-titulo"></div>
        <svg id="extremos" viewBox="0 0 1120 540" width="1120" height="540"></svg>
        <p class="nota a" style="--d:5.8s;margin-top:8px" id="ext-def"></p></div>
      <div>
        <p class="lead a" style="--d:.6s;font-size:30px">⟦Un promedio mensual esconde los días extremos. Ocho índices anuales los cuentan.¦A monthly mean hides extreme days. Eight annual indices count them.⟧</p>
        <ul class="indices" id="ext-indices"></ul>
      </div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦País o mundo¦Country or world⟧">
    <div class="cab a"><span class="n">10</span><h2>⟦Un país completo, o el planeta¦A whole country, or the planet⟧</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:22px;max-width:1500px">⟦El mismo análisis con el mapa recortado a la frontera y el promedio de todo el territorio.¦The same analysis with the map clipped to the border and the mean of the whole territory.⟧</p>
    <div class="dos" style="gap:64px">
      <div><div class="eyebrow a" style="--d:.7s" id="ter-pais-n"></div><svg id="ter-pais" viewBox="0 0 832 430" width="832" height="430" style="margin-top:10px"></svg>
        <div class="pie-mapa a" style="--d:3.8s"><span class="v" id="ter-pais-v"></span><span class="u" id="ter-pais-u"></span></div></div>
      <div><div class="eyebrow a" style="--d:.9s" id="ter-mundo-n"></div><svg id="ter-mundo" viewBox="0 0 832 430" width="832" height="430" style="margin-top:10px"></svg>
        <div class="pie-mapa a" style="--d:4.6s"><span class="v" id="ter-mundo-v"></span><span class="u" id="ter-mundo-u"></span></div></div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Comparación de dos lugares¦Comparison of two places⟧">
    <div class="cab a"><span class="n">11</span><h2>⟦Tendencias opuestas¦Opposite trends⟧</h2></div>
    <div class="leyenda a" style="--d:.5s"><span><i style="border-color:var(--azul)"></i><span id="cmp-a"></span></span><span><i style="border-color:var(--naranja)"></i><span id="cmp-b"></span></span></div>
    <svg id="comparacion" viewBox="0 0 1728 600" width="1728" height="600"></svg>
    <p class="nota a" style="--d:6s;margin-top:6px">⟦La misma variable en dos lugares: el espesor óptico de aerosoles aumenta en Delhi y disminuye en Pekín.¦The same variable in two places: aerosol optical depth increases in Delhi and decreases in Beijing.⟧</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Laboratorio¦Laboratory⟧">
    <div class="cab a"><span class="n">12</span><h2>⟦Laboratorio de falsos positivos¦False-positive laboratory⟧</h2></div>
    <div class="dos" style="grid-template-columns: 1040px 1fr; gap: 70px">
      <div><div class="eyebrow a" style="--d:.4s">⟦Una serie fabricada sin tendencia¦A series manufactured with no trend⟧</div>
        <svg id="lab" viewBox="0 0 1040 520" width="1040" height="520"></svg>
        <p class="nota a" style="--d:6s;margin-top:8px">⟦La simulación se repite en vivo dentro de la herramienta, con la autocorrelación y los años que se elijan.¦The simulation can be repeated live inside the tool, with any autocorrelation and number of years.⟧</p></div>
      <div>
        <div class="cifra media a" style="--d:3.2s"><div class="eyebrow">⟦Prueba clásica¦Classic test⟧</div><div class="v" style="color:var(--rojo)" id="lab-clasica"></div><div class="u" id="lab-clasica-u"></div></div>
        <div class="cifra media a" style="--d:4.6s"><div class="eyebrow">⟦Con la corrección¦With the correction⟧</div><div class="v" id="lab-corregida"></div><div class="u" id="lab-corregida-u"></div></div>
      </div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="⟦Informe¦Report⟧">
    <div class="cab a"><span class="n">13</span><h2>⟦Informe descargable¦Downloadable report⟧</h2></div>
    <div class="dos">
      <div>
        <p class="lead a" style="--d:.4s">⟦Cada análisis se descarga como un informe listo para compartir o imprimir.¦Every analysis can be downloaded as a report ready to share or print.⟧</p>
        <ul class="lista">
          <li class="a" style="--d:1.2s">⟦Portada, resumen y ficha de la variable¦Cover, summary and variable sheet⟧</li>
          <li class="a" style="--d:1.5s">⟦Gráficas, pruebas y mapa de tendencias¦Charts, tests and trend map⟧</li>
          <li class="a" style="--d:1.8s">⟦Ficha técnica, supuestos y limitaciones¦Technical sheet, assumptions and limitations⟧</li>
          <li class="a" style="--d:2.1s">⟦Referencias con enlace DOI¦References with DOI links⟧</li>
          <li class="a" style="--d:2.4s">⟦En español y en inglés, igual que la herramienta¦In Spanish and in English, like the tool itself⟧</li>
        </ul>
        <div class="boton pulsa" style="--d:3.6s">⟦Descargar el informe¦Download the report⟧</div>
      </div>
      <div class="hojas">
        <div class="hoja" style="left:250px;top:70px;--giro:7deg;--d:1.5s"><div class="l m"></div><div class="l t" style="width:55%"></div><div class="regla"></div><div class="l"></div><div class="l c"></div><div class="l"></div><div class="regla"></div><div class="l c"></div><div class="l"></div><div class="l"></div><div class="l c"></div></div>
        <div class="hoja" style="left:130px;top:40px;--giro:2deg;--d:1.1s"><div class="l m"></div><div class="l t" style="width:48%"></div><svg viewBox="0 0 370 200" width="370" height="200"><polyline points="0,40 40,60 80,50 120,90 160,84 200,120 240,112 280,150 320,146 370,176" fill="none" stroke="#2a78d6" stroke-width="4"/><line x1="0" y1="38" x2="370" y2="178" stroke="#0b0b0b" stroke-width="3"/></svg><div class="regla"></div><div class="l"></div><div class="l c"></div><div class="l"></div></div>
        <div class="hoja" style="left:10px;top:10px;--giro:-4deg;--d:.7s"><div class="l m"></div><div class="l m" style="width:28%;background:var(--tinta)"></div><div class="l t" style="height:34px;margin-top:22px"></div><div class="l t" style="height:34px;width:60%;margin-top:0"></div><div class="l c" style="margin-top:20px"></div><div style="height:150px"></div><div class="regla"></div><div class="l c"></div><div class="l"></div><div class="l c"></div><div class="l"></div></div>
      </div>
    </div>
  </section>

  <section class="escena portada" data-dur="5" data-nombre="⟦Cierre¦Closing⟧">
    <div class="eyebrow a">NASA Space Apps 2026 · ⟦Equipo¦Team⟧ C15H25N3O</div>
    <h1 class="a" style="--d:.3s;font-size:150px">Expediente Tierra</h1>
    <p class="lead a" style="--d:.7s">⟦Qué cambia, dónde, cuánto, en qué meses, y si el cambio es significativo.¦What is changing, where, by how much, in which months, and whether the change is significant.⟧</p>
    <div class="datos-cierre">
      <div class="a" style="--d:1.3s"><div class="v" id="fin-variables"></div><div class="eyebrow e">variables</div></div>
      <div class="a" style="--d:1.5s"><div class="v">5</div><div class="eyebrow e">⟦pruebas de significancia¦significance tests⟧</div></div>
      <div class="a" style="--d:1.7s"><div class="v">8</div><div class="eyebrow e">⟦productos de datos¦data products⟧</div></div>
      <div class="a" style="--d:1.9s"><div class="v">2</div><div class="eyebrow e">⟦idiomas¦languages⟧</div></div>
      <div class="a" style="--d:2.1s"><div class="v">3–4 %</div><div class="eyebrow e">⟦falsos positivos¦false positives⟧</div></div>
    </div>
  </section>

  <div class="avance"><i id="avance"></i></div>
</div></div>
<div id="controles"><button id="b-antes" aria-label="⟦Escena anterior¦Previous scene⟧">⟦Anterior¦Previous⟧</button><button id="b-pausa" class="principal">⟦Pausa¦Pause⟧</button><button id="b-despues" aria-label="⟦Escena siguiente¦Next scene⟧">⟦Siguiente¦Next⟧</button><div id="tramos" aria-label="⟦Escenas¦Scenes⟧"></div><button id="b-reinicio">⟦Reiniciar¦Restart⟧</button><span id="rotulo"></span></div>

<script>
const D = __DATOS__;
const AUTO = __AUTO__;
const NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);
const el = (tag, attrs = {}, padre) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (padre) padre.appendChild(n); return n; };
const ESCALA = [[0, [24, 79, 149]], [.25, [109, 167, 236]], [.5, [240, 239, 236]], [.75, [238, 143, 142]], [1, [177, 43, 43]]];
function color(valor, tope) {
  const x = Math.min(Math.max((valor / tope + 1) / 2, 0), 1);
  for (let i = 0; i < ESCALA.length - 1; i++) { const [x0, c0] = ESCALA[i], [x1, c1] = ESCALA[i + 1];
    if (x <= x1) { const f = (x - x0) / (x1 - x0); return "rgb(" + c0.map((a, k) => Math.round(a + f * (c1[k] - a))).join(",") + ")"; } }
  return "rgb(177,43,43)";
}
const menos = (s) => String(s).replace("-", "−");
const POR_DECADA = "⟦por década¦per decade⟧";
const tono = (positiva, firme) => positiva ? (firme ? "#e34948" : "#f3b3b2") : (firme ? "#2a78d6" : "#9ec5f4");

// ---- textos que salen de los datos
$("sitio-demo").textContent = D.sitio;
$("n-validas").textContent = D.exploracion.validas; $("fin-variables").textContent = D.variables;
$("exp-clasicas").textContent = D.exploracion.clasicas; $("exp-firmes").textContent = D.exploracion.firmes;
$("res-etiqueta").textContent = D.resultado.etiqueta;
$("res-titular").textContent = D.resultado.titular;
$("res-decada").dataset.valor = D.resultado.decada; $("res-total").dataset.valor = D.resultado.total;
$("res-u1").textContent = D.resultado.unidad + " " + POR_DECADA; $("res-u2").textContent = D.resultado.unidad + "⟦ en ¦ in ⟧" + D.resultado.anios + "⟦ años¦ years⟧";
$("res-pruebas").textContent = D.resultado.aprobadas + "/5"; $("res-nivel").textContent = D.resultado.nivel;
$("mapa-baja").dataset.valor = D.mapa.baja;
$("cmp-a").textContent = D.comparacion.a.nombre + " · " + menos(D.comparacion.a.decada) + " " + POR_DECADA;
$("cmp-b").textContent = D.comparacion.b.nombre + " · " + menos(D.comparacion.b.decada) + " " + POR_DECADA;
$("mes-titulo").textContent = D.meses.variable + " · " + D.sitio;
$("mes-anual").textContent = menos(D.meses.anual.decada); $("mes-anual-u").textContent = D.meses.unidad + " " + POR_DECADA + " · " + D.meses.anual.nivel.toLowerCase();
$("mes-temporada-n").textContent = "⟦Solo ¦Only ⟧" + D.meses.temporada.nombre;
$("mes-temporada").textContent = menos(D.meses.temporada.decada); $("mes-temporada-u").textContent = D.meses.unidad + " " + POR_DECADA + " · " + D.meses.temporada.nivel.toLowerCase();
$("ext-titulo").textContent = D.extremos.variable + " · " + D.sitio;
$("ext-def").textContent = D.extremos.definicion + " " + D.extremos.nivel + ".";
D.extremos.indices.forEach((nombre, k) => { const li = document.createElement("li"); li.className = "a" + (nombre === D.extremos.elegido ? " elegido" : "");
  li.style.setProperty("--d", (1.4 + k * .28).toFixed(2) + "s"); li.textContent = nombre; $("ext-indices").appendChild(li); });
for (const clave of ["pais", "mundo"]) { const t = D.territorios[clave];
  $("ter-" + clave + "-n").textContent = t.nombre + " · " + t.variable;
  $("ter-" + clave + "-v").textContent = menos(t.decada) + " " + t.unidad;
  $("ter-" + clave + "-u").innerHTML = POR_DECADA + " · " + t.nivel.toLowerCase() + "<br>⟦aumento significativo en ¦significant increase in ⟧" + t.sube + " %⟦ de ¦ of ⟧" + t.total.toLocaleString("en-US") + "⟦ celdas¦ cells⟧"; }
$("lab-clasica").textContent = D.laboratorio.clasica + " %"; $("lab-corregida").textContent = D.laboratorio.corregida + " %";
$("lab-clasica-u").textContent = "⟦de ¦of ⟧" + D.laboratorio.series + "⟦ series sin tendencia, declaradas «significativas». A esta le da ¦ trend-free series, declared “significant”. For this one it gives ⟧" + D.laboratorio.p_clasica + ".";
$("lab-corregida-u").textContent = "⟦cerca del 5 % que corresponde. A esta serie le da ¦close to the 5 % it should be. For this series it gives ⟧" + D.laboratorio.p_corregida + "⟦: no es significativa.¦: not significant.⟧";

// ---- exploración: barras desde el centro; la que se sale de la escala se corta en el borde
(function () {
  const filas = D.exploracion.barras, orden = filas.map(v => Math.abs(v.valor)).sort((a, b) => b - a);
  const tope = (orden.length > 2 && orden[0] > 2.2 * orden[1] ? orden[1] : orden[0]) * 1.12;
  filas.forEach((v, k) => {
    const d = (1.1 + k * .32).toFixed(2), ancho = Math.min(Math.abs(v.valor) / tope * 50, 50), positiva = v.valor > 0;
    const fila = document.createElement("div"); fila.style.display = "contents"; if (v.elegida) fila.className = "elegida";
    const cifra = menos((v.valor > 0 ? "+" : "") + v.valor.toFixed(2));
    fila.innerHTML = `<div class="rot a" style="--d:${d}s">${v.nombre}</div><div class="eje">` +
      `<b class="crece" style="--d:${d}s;--origen:${positiva ? "left" : "right"};background:${tono(positiva, v.firme)};width:${ancho}%;${positiva ? "left:50%" : "right:50%"}"></b>` +
      (ancho > 30
        ? `<span class="a" style="--d:${(+d + .5).toFixed(2)}s;color:#fff;${positiva ? `right:calc(50% - ${ancho}% + 14px)` : `left:calc(50% - ${ancho}% + 14px)`}">${cifra}</span></div>`
        : `<span class="a" style="--d:${(+d + .5).toFixed(2)}s;${positiva ? `left:calc(50% + ${ancho}% + 12px)` : `right:calc(50% + ${ancho}% + 12px)`}">${cifra}</span></div>`);
    $("barras").appendChild(fila);
  });
})();

// ---- mapa por celda de la región
(function () {
  const c = D.mapa.celdas, svg = $("mapa");
  const lats = [...new Set(c.map(x => x[0]))].sort((a, b) => a - b), lons = [...new Set(c.map(x => x[1]))].sort((a, b) => a - b);
  const dLat = lats[1] - lats[0], dLon = lons[1] - lons[0], lat1 = lats[lats.length - 1] + dLat / 2, lon0 = lons[0] - dLon / 2;
  const w = 620 / lons.length, h = 620 / lats.length, tope = Math.max(...c.map(x => Math.abs(x[2])));
  const cx = (lon) => (lon - lon0) / dLon * w, cy = (lat) => (lat1 - lat) / dLat * h;
  el("rect", { x: 0, y: 0, width: 620, height: 620, fill: "#f4f4f2" }, svg);
  for (const [lat, lon, valor, firme] of c) {
    const x = cx(lon) - w / 2, y = cy(lat) - h / 2, dist = Math.hypot(lat - D.mapa.sitio[0], lon - D.mapa.sitio[1]);
    const g = el("g", { class: "funde", style: `--d:${(1 + dist * .24).toFixed(2)}s` }, svg);
    el("rect", { x: x + 1, y: y + 1, width: w - 2, height: h - 2, fill: color(valor, tope) }, g);
    if (firme) el("circle", { cx: x + w / 2, cy: y + h / 2, r: 3.2, fill: "#0b0b0b", "fill-opacity": .6 }, g);
  }
  const m = el("g", { class: "funde", style: "--d:.9s" }, svg);
  el("circle", { cx: cx(D.mapa.sitio[1]), cy: cy(D.mapa.sitio[0]), r: 12, fill: "#fff" }, m);
  el("circle", { cx: cx(D.mapa.sitio[1]), cy: cy(D.mapa.sitio[0]), r: 7.5, fill: "#0b0b0b" }, m);
  $("mapa-min").textContent = menos((-tope).toFixed(0)); $("mapa-max").textContent = "+" + tope.toFixed(0) + " " + D.mapa.unidad + "⟦/década¦/decade⟧";
})();

// ---- mapas de un país y del mundo: las celdas aparecen de oeste a este
function mapaDeCeldas(svg, territorio, ancho, alto, radio) {
  const c = territorio.celdas, d = territorio.celda, lats = c.map(x => x[0]), lons = c.map(x => x[1]);
  const lat0 = Math.min(...lats) - d / 2, lat1 = Math.max(...lats) + d / 2, lon0 = Math.min(...lons) - d / 2, lon1 = Math.max(...lons) + d / 2;
  // Un grado de longitud mide menos que uno de latitud lejos del ecuador.
  const estrecha = Math.cos((lat0 + lat1) / 2 * Math.PI / 180), k = Math.min(ancho / ((lon1 - lon0) * estrecha), alto / (lat1 - lat0));
  const ox = (ancho - (lon1 - lon0) * estrecha * k) / 2, oy = (alto - (lat1 - lat0) * k) / 2, w = d * estrecha * k, h = d * k;
  const tope = Math.max(...c.map(x => Math.abs(x[2]))), N = 48;
  el("rect", { x: 0, y: 0, width: ancho, height: alto, fill: "#f4f4f2" }, svg);
  const franjas = Array.from({ length: N }, (_, i) => el("g", { class: "funde", style: `--d:${(1 + i * .07).toFixed(2)}s` }, svg));
  for (const [lat, lon, valor, firme] of c) {
    const x = ox + (lon - d / 2 - lon0) * estrecha * k, y = oy + (lat1 - lat - d / 2) * k;
    const g = franjas[Math.min(N - 1, Math.floor((lon - lon0) / (lon1 - lon0) * N))];
    el("rect", { x: (x + .35).toFixed(1), y: (y + .35).toFixed(1), width: (w - .7).toFixed(1), height: (h - .7).toFixed(1), fill: color(valor, tope) }, g);
    if (firme) el("circle", { cx: (x + w / 2).toFixed(1), cy: (y + h / 2).toFixed(1), r: radio, fill: "#0b0b0b", "fill-opacity": .5 }, g);
  }
}
mapaDeCeldas($("ter-pais"), D.territorios.pais, 832, 430, 1.9);
mapaDeCeldas($("ter-mundo"), D.territorios.mundo, 832, 430, 1.1);

// ---- gráficas de líneas
function marcas(min, max, cuantas) {
  const bruto = (max - min) / cuantas, base = Math.pow(10, Math.floor(Math.log10(bruto)));
  const paso = [1, 2, 5, 10].map(m => m * base).find(p => p >= bruto), out = [];
  for (let k = Math.ceil(min / paso); k <= Math.floor(max / paso); k++) out.push(k * paso);
  return out;
}
function lienzo(svg, series, alto, ancho = 1728, der = 200) {
  const izq = 86, arriba = 18, abajo = 44;
  const ts = series.flatMap(s => s.t), ys = series.flatMap(s => [...s.y, ...s.alto, ...s.bajo]).filter(v => v !== null);
  let yMin = Math.min(...ys), yMax = Math.max(...ys); const m = .06 * (yMax - yMin); yMin -= m; yMax += m;
  const tMin = Math.min(...ts), tMax = Math.max(...ts);
  const px = (t) => izq + (t - tMin) / (tMax - tMin) * (ancho - izq - der), py = (v) => arriba + (yMax - v) / (yMax - yMin) * (alto - arriba - abajo);
  for (const v of marcas(yMin, yMax, 5)) { el("line", { x1: izq, x2: ancho - der, y1: py(v), y2: py(v), stroke: v === 0 ? "#c3c2b7" : "#e1e0d9", "stroke-width": 1.5, class: "funde", style: "--d:.6s" }, svg);
    const t = el("text", { x: izq - 14, y: py(v) + 7, "text-anchor": "end", class: "funde", style: "--d:.6s" }, svg); t.textContent = menos(+v.toFixed(3)); }
  for (const a of marcas(tMin, tMax, 6)) { const t = el("text", { x: px(a), y: alto - 12, "text-anchor": "middle", class: "funde", style: "--d:.6s" }, svg); t.textContent = a; }
  el("line", { x1: izq, x2: ancho - der, y1: alto - abajo, y2: alto - abajo, stroke: "#c3c2b7", "stroke-width": 1.5, class: "funde", style: "--d:.6s" }, svg);
  const pasos = ts.slice(1).map((a, k) => a - ts[k]).filter(x => x > 0).sort((a, b) => a - b), paso = pasos[Math.floor(pasos.length / 2)] || 1;
  // Un tramo nuevo empieza tras un dato faltante o tras un hueco largo, para no unir sus extremos.
  const camino = (t, v) => { let d = "", abierto = false; t.forEach((a, k) => { if (v[k] === null) { abierto = false; return; }
    if (k > 0 && a - t[k - 1] > 3.5 * paso) abierto = false; d += (abierto ? "L" : "M") + px(a).toFixed(1) + "," + py(v[k]).toFixed(1); abierto = true; }); return d; };
  const banda = (s) => s.t.map((a, k) => px(a).toFixed(1) + "," + py(Math.max(s.alto[k], s.bajo[k])).toFixed(1)).join(" ") + " " +
    [...s.t].reverse().map((a, k) => { const i = s.t.length - 1 - k; return px(a).toFixed(1) + "," + py(Math.min(s.alto[i], s.bajo[i])).toFixed(1); }).join(" ");
  return { px, py, camino, banda, ancho, der };
}
(function () {
  const s = D.serie, svg = $("serie"), g = lienzo(svg, [s], 640);
  el("polygon", { points: g.banda(s), fill: "#0b0b0b", "fill-opacity": .11, class: "funde", style: "--d:4.2s" }, svg);
  el("path", { d: g.camino(s.t, s.y), fill: "none", stroke: "#c3c2b7", "stroke-width": 2, pathLength: 1, class: "traza", style: "--d:.9s;--t:2.2s" }, svg);
  el("path", { d: g.camino(s.t, s.suave), fill: "none", stroke: "#2a78d6", "stroke-width": 5, "stroke-linejoin": "round", pathLength: 1, class: "traza", style: "--d:1.9s;--t:2.4s" }, svg);
  el("path", { d: g.camino(s.t, s.recta), fill: "none", stroke: "#0b0b0b", "stroke-width": 5, pathLength: 1, class: "traza", style: "--d:4.2s;--t:1.3s" }, svg);
  el("path", { d: g.camino(s.t, s.loess), fill: "none", stroke: "#0b0b0b", "stroke-width": 4, "stroke-dasharray": "2 10", "stroke-linecap": "round", class: "funde", style: "--d:5.6s" }, svg);
  const fin = s.t.length - 1, r = el("text", { x: g.px(s.t[fin]) + 18, y: g.py(s.recta[fin]) + 4, class: "rotulo funde", style: "--d:5.4s" }, svg);
  r.textContent = menos(s.decada); const r2 = el("text", { x: g.px(s.t[fin]) + 18, y: g.py(s.recta[fin]) + 32, class: "funde", style: "--d:5.4s" }, svg); r2.textContent = "⟦cm por década¦cm per decade⟧";
})();
(function () {
  const c = D.comparacion, svg = $("comparacion"), tonos = ["#2a78d6", "#eb6834"];
  const g = lienzo(svg, [c.a, c.b].map(s => ({ t: s.t, y: s.suave.filter(v => v !== null), alto: s.recta, bajo: s.recta })), 600);
  [c.a, c.b].forEach((s, k) => {
    el("path", { d: g.camino(s.t, s.suave), fill: "none", stroke: tonos[k], "stroke-width": 3, "stroke-opacity": .55, "stroke-linejoin": "round", pathLength: 1, class: "traza", style: `--d:${1 + k * .5}s;--t:2.6s` }, svg);
    el("path", { d: g.camino(s.t, s.recta), fill: "none", stroke: tonos[k], "stroke-width": 6, pathLength: 1, class: "traza", style: `--d:${3.6 + k * .4}s;--t:1.3s` }, svg);
    const fin = s.t.length - 1, r = el("text", { x: g.px(s.t[fin]) + 18, y: g.py(s.recta[fin]) + 8, class: "rotulo funde", style: `--d:${4.9 + k * .4}s` }, svg); r.textContent = menos(s.decada);
  });
})();

// ---- extremos: un valor por año, con su tendencia
(function () {
  const s = D.extremos.serie, svg = $("extremos"), g = lienzo(svg, [s], 540, 1120, 235);
  el("polygon", { points: g.banda(s), fill: "#0b0b0b", "fill-opacity": .11, class: "funde", style: "--d:3.8s" }, svg);
  el("path", { d: g.camino(s.t, s.y), fill: "none", stroke: "#2a78d6", "stroke-width": 3.5, "stroke-linejoin": "round", pathLength: 1, class: "traza", style: "--d:.9s;--t:2.6s" }, svg);
  s.t.forEach((a, k) => el("circle", { cx: g.px(a), cy: g.py(s.y[k]), r: 6, fill: "#2a78d6", stroke: "#fff", "stroke-width": 2.5, class: "funde", style: `--d:${(1 + k * .055).toFixed(2)}s` }, svg));
  el("path", { d: g.camino(s.t, s.recta), fill: "none", stroke: "#0b0b0b", "stroke-width": 5, pathLength: 1, class: "traza", style: "--d:3.8s;--t:1.3s" }, svg);
  const fin = s.t.length - 1, r = el("text", { x: g.px(s.t[fin]) + 16, y: g.py(s.recta[fin]) + 4, class: "rotulo funde", style: "--d:5s" }, svg);
  r.textContent = menos(s.decada); const r2 = el("text", { x: g.px(s.t[fin]) + 16, y: g.py(s.recta[fin]) + 32, class: "funde", style: "--d:5s" }, svg); r2.textContent = "⟦días por década¦days per decade⟧";
})();

// ---- laboratorio: la serie sin tendencia que engaña a la prueba clásica
(function () {
  const s = D.laboratorio.serie, svg = $("lab"), g = lienzo(svg, [{ t: s.t, y: s.y, alto: s.recta, bajo: s.recta }], 520, 1040, 30);
  el("path", { d: g.camino(s.t, s.y), fill: "none", stroke: "#c3c2b7", "stroke-width": 2, pathLength: 1, class: "traza", style: "--d:.8s;--t:2s" }, svg);
  el("path", { d: g.camino(s.t, s.suave), fill: "none", stroke: "#2a78d6", "stroke-width": 5, "stroke-linejoin": "round", pathLength: 1, class: "traza", style: "--d:1.6s;--t:2.2s" }, svg);
  el("path", { d: g.camino(s.t, s.recta), fill: "none", stroke: "#e34948", "stroke-width": 5, pathLength: 1, class: "traza", style: "--d:3.2s;--t:1.2s" }, svg);
})();

// ---- tendencia de cada mes del año, con su intervalo de confianza
(function () {
  const b = D.meses.barras, svg = $("meses"), ancho = 1060, alto = 600, izq = 96, der = 16, arriba = 22, abajo = 56;
  const vs = b.flatMap(x => x.valor === null ? [0] : [x.valor, x.bajo, x.alto, 0]);
  let yMin = Math.min(...vs), yMax = Math.max(...vs); const m = .07 * (yMax - yMin); yMin -= m; yMax += m;
  const py = (v) => arriba + (yMax - v) / (yMax - yMin) * (alto - arriba - abajo), paso = (ancho - izq - der) / 12;
  for (const v of marcas(yMin, yMax, 5)) { el("line", { x1: izq, x2: ancho - der, y1: py(v), y2: py(v), stroke: "#e1e0d9", "stroke-width": 1.5, class: "funde", style: "--d:.6s" }, svg);
    const t = el("text", { x: izq - 14, y: py(v) + 7, "text-anchor": "end", class: "funde", style: "--d:.6s" }, svg); t.textContent = menos((v > 0 ? "+" : "") + +v.toFixed(3)); }
  b.forEach((x, k) => {
    const cx = izq + paso * (k + .5), d = 1 + k * .2;
    const t = el("text", { x: cx, y: alto - 16, "text-anchor": "middle", class: "rotulo funde", style: "--d:.6s" }, svg); t.textContent = x.mes;
    if (x.valor === null) return;
    const y0 = py(0), y1 = py(x.valor), positiva = x.valor > 0;
    el("rect", { x: cx - paso * .31, y: Math.min(y0, y1), width: paso * .62, height: Math.max(Math.abs(y1 - y0), 1), rx: 4, fill: tono(positiva, x.firme),
                 class: "alza", style: `--d:${d.toFixed(2)}s;--origen:${positiva ? "50% 100%" : "50% 0%"}` }, svg);
    const bigote = el("g", { class: "funde", style: `--d:${(d + .9).toFixed(2)}s` }, svg);
    el("line", { x1: cx, x2: cx, y1: py(x.bajo), y2: py(x.alto), stroke: "#52514e", "stroke-width": 2 }, bigote);
    for (const v of [x.bajo, x.alto]) el("line", { x1: cx - 7, x2: cx + 7, y1: py(v), y2: py(v), stroke: "#52514e", "stroke-width": 2 }, bigote);
  });
  el("line", { x1: izq, x2: ancho - der, y1: py(0), y2: py(0), stroke: "#898781", "stroke-width": 1.5, class: "funde", style: "--d:.6s" }, svg);
})();

// ---- pruebas
D.pruebas.forEach((p, k) => {
  const d = (1.1 + k * 1.05).toFixed(2), fila = document.createElement("div"); fila.className = "prueba a"; fila.style.setProperty("--d", d + "s");
  const marca = p.pasa ? `<svg width="22" height="22" viewBox="0 0 22 22"><path d="M4 11.5l4.5 4.5L18 6.5" fill="none" stroke="#0a6b2d" stroke-width="2.6" pathLength="1" class="traza" style="--d:${(+d + .55).toFixed(2)}s;--t:.5s"/></svg>` : "";
  fila.innerHTML = `<div class="estado ${p.pasa ? "" : "no"}">${marca}${p.pasa ? "⟦Pasa¦Pass⟧" : "⟦No pasa¦Fail⟧"}</div><div><div class="nom"></div><div class="res"></div></div>`;
  fila.querySelector(".nom").textContent = p.nombre; fila.querySelector(".res").textContent = p.resultado;
  $("pruebas").appendChild(fila);
});

// ---- línea de tiempo
const K = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--k")) || 1;
const escenas = [...document.querySelectorAll(".escena")], duraciones = escenas.map(e => +e.dataset.dur * 1000), total = duraciones.reduce((a, b) => a + b, 0);
const inicios = duraciones.map((_, i) => duraciones.slice(0, i).reduce((a, b) => a + b, 0));
let actual = -1, transcurrido = 0, anterior = null, pausado = !AUTO, terminado = false;

// Una barra por escena: muestra el avance y sirve para saltar a cualquiera.
const tramos = escenas.map((e, i) => { const b = document.createElement("button"); b.title = e.dataset.nombre; b.setAttribute("aria-label", "⟦Ir a: ¦Go to: ⟧" + e.dataset.nombre);
  b.innerHTML = "<i></i>"; b.onclick = () => irA(i); $("tramos").appendChild(b); return b.firstChild; });

function contar(escena) {
  escena.querySelectorAll("[data-cuenta]").forEach(n => {
    const meta = +n.dataset.valor, retraso = (parseFloat(getComputedStyle(n.closest(".a")).getPropertyValue("--d")) || 0) * 1000 * K + 300, inicio = performance.now() + retraso;
    n.textContent = "0";
    const paso = (ahora) => { if (!escena.classList.contains("activa")) return; const f = Math.min(Math.max((ahora - inicio) / 1000, 0), 1), s = 1 - Math.pow(1 - f, 3);
      n.textContent = menos((meta > 0 && n.id !== "mapa-baja" ? "+" : "") + Math.round(meta * s)); if (f < 1) requestAnimationFrame(paso); };
    requestAnimationFrame(paso);
  });
}
function mostrar(i) {
  if (i === actual) return;
  const previa = escenas[actual];
  $("lienzo").classList.toggle("atras", actual > i);  // al retroceder, el movimiento se invierte
  escenas.forEach(e => e.classList.remove("saliente"));
  if (previa) { previa.classList.remove("activa"); previa.classList.add("saliente"); setTimeout(() => previa.classList.remove("saliente"), 900); }
  actual = i;
  void escenas[i].offsetWidth;  // reinicia las animaciones de la escena aunque ya se haya visto
  escenas[i].classList.add("activa");
  $("contador").textContent = String(i + 1).padStart(2, "0") + " / " + String(escenas.length).padStart(2, "0");
  $("rotulo").textContent = (i + 1) + "⟦ de ¦ of ⟧" + escenas.length + " · " + escenas[i].dataset.nombre;
  contar(escenas[i]);
}
function irA(i) { i = Math.min(Math.max(i, 0), escenas.length - 1); transcurrido = inicios[i]; terminado = false; mostrar(i); pintar(); estado(); }
function pintar() {
  $("avance").style.width = (100 * transcurrido / total) + "%";
  tramos.forEach((t, i) => { t.style.width = (100 * Math.min(Math.max((transcurrido - inicios[i]) / duraciones[i], 0), 1)) + "%"; });
}
function cuadro(ahora) {
  if (anterior !== null && !pausado && !terminado) transcurrido += ahora - anterior;
  anterior = ahora;
  if (transcurrido >= total) { transcurrido = total; terminado = true; pausado = true; estado(); }
  let i = escenas.length - 1; while (i > 0 && transcurrido < inicios[i]) i--;
  mostrar(i); pintar();
  requestAnimationFrame(cuadro);
}
// Pausar detiene el paso de una escena a la siguiente; la escena en pantalla termina de dibujarse.
function estado() { $("b-pausa").textContent = terminado ? "⟦Ver de nuevo¦Watch again⟧" : pausado ? "⟦Reproducir¦Play⟧" : "⟦Pausa¦Pause⟧"; }
function alternar() { if (terminado) { irA(0); pausado = false; } else pausado = !pausado; estado(); }
$("b-pausa").onclick = alternar;
$("b-reinicio").onclick = () => { irA(0); pausado = false; estado(); };
$("b-antes").onclick = () => irA(actual - 1);
$("b-despues").onclick = () => irA(actual + 1);
document.addEventListener("keydown", (e) => { if (e.code === "Space") { e.preventDefault(); alternar(); } if (e.code === "ArrowRight") irA(actual + 1); if (e.code === "ArrowLeft") irA(actual - 1); if (e.code === "Home") irA(0); });

// ---- escala: el lienzo de 1920 × 1080 se ajusta al espacio que deja la barra de controles
const parametros = new URLSearchParams(location.search), grabando = parametros.has("grabar");
if (grabando) $("controles").style.display = "none";
function ajustar() { const alto = innerHeight - (grabando ? 0 : 56), k = Math.min(innerWidth / 1920, alto / 1080), l = $("lienzo");
  l.style.transform = `translate(${(innerWidth - 1920 * k) / 2}px, ${(alto - 1080 * k) / 2}px) scale(${k})`; }
addEventListener("resize", ajustar); ajustar();

if (parametros.has("escena")) irA(+parametros.get("escena") - 1); else mostrar(0);
estado();
(document.fonts ? document.fonts.ready : Promise.resolve()).then(() => setTimeout(() => requestAnimationFrame(cuadro), AUTO ? 700 : 0));
</script>
</body></html>
"""


if __name__ == "__main__":
    escribir()
