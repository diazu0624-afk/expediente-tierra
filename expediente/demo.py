"""Recorrido animado de la herramienta, con los datos reales de Nueva Delhi.

Genera `static/demo.html`: una animación de pantalla completa (16:9) que muestra el flujo
completo, de empezar un análisis a descargar el informe. Sirve de dos maneras: incrustada
en la página de inicio de la app, o abierta sola en el navegador para grabarla como video.

Uso:  .venv/bin/python -m expediente.demo
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import caso, datos, datos_gee, region
from .variables import CATALOGO, POR_CODIGO

RUTA = Path(__file__).resolve().parent.parent / "static" / "demo.html"
DELHI = ("Nueva Delhi, India", 28.61, 77.21)
PEKIN = ("Pekín, China", 39.90, 116.40)
LADO = 8


def _punto(lat: float, lon: float) -> pd.DataFrame:
    tabla = datos.descargar_power(lat, lon, [v.codigo for v in CATALOGO if v.origen == "power"])
    for v in CATALOGO:
        if v.origen == "gee":
            serie = datos_gee.serie_del_punto(datos_gee.descargar_cubo(lat, lon, v.codigo), lat, lon)
            tabla = tabla.join(serie.rename(v.codigo), how="outer")
    return tabla


def _redondo(valores, cifras: int = 3) -> list:
    return [None if not np.isfinite(x) else round(float(x), cifras) for x in valores]


def _serie(r: caso.Interrogatorio) -> dict:
    """Anomalías, media móvil, recta e intervalo de confianza de un análisis."""
    centro = r.t.mean()
    altura = r.regresion.intercepto + r.regresion.pendiente * centro
    return {
        "t": _redondo(r.t),
        "y": _redondo(r.y),
        "suave": _redondo(pd.Series(r.y).rolling(12, center=True, min_periods=6).mean()),
        "recta": _redondo(altura + r.regresion.pendiente * (r.t - centro)),
        "bajo": _redondo(altura + r.ic_historias[0] * (r.t - centro)),
        "alto": _redondo(altura + r.ic_historias[1] * (r.t - centro)),
        "decada": caso.numero(r.pendiente_decada, signo=True),
    }


def datos_de_demo() -> dict:
    """Todo lo que la animación muestra, calculado con el mismo código que usa la app."""
    nombre, lat, lon = DELHI
    tabla = _punto(lat, lon)
    exploracion = caso.escanear(tabla).dropna(subset=["estandarizada"])
    agua = POR_CODIGO["GRACE_AGUA"]
    r = caso.interrogar(tabla["GRACE_AGUA"], agua)
    mapa = region.mapa_de_tendencias(datos_gee.recortar(datos_gee.descargar_cubo(lat, lon, "GRACE_AGUA"), lat, lon, LADO), agua)
    resumen = region.resumen(mapa)
    aerosoles = POR_CODIGO["AOD_55"]
    a = caso.interrogar(tabla["AOD_55"], aerosoles)
    b = caso.interrogar(_punto(PEKIN[1], PEKIN[2])["AOD_55"], aerosoles)
    return {
        "sitio": nombre,
        "variables": len(CATALOGO),
        "exploracion": [{"nombre": f.nombre, "valor": round(float(f.estandarizada), 2), "firme": bool(f.significativa),
                         "elegida": f.codigo == "GRACE_AGUA"} for f in exploracion.head(9).itertuples()],
        "mapa": {"celdas": [[float(f.lat), float(f.lon), round(float(f.pendiente_decada), 2), bool(f.significativa)]
                            for f in mapa.itertuples()],
                 "sitio": [lat, lon], "baja": round(resumen["baja"]), "sube": round(resumen["sube"]),
                 "total": int(resumen["celdas"]), "lado": LADO, "unidad": agua.unidad},
        "serie": _serie(r),
        "pruebas": [{"nombre": p.nombre, "resultado": p.resultado, "pasa": bool(p.aprobada)} for p in r.pruebas],
        "resultado": {"variable": agua.nombre, "unidad": agua.unidad, "decada": round(r.pendiente_decada),
                      "total": round(r.cambio_total), "anios": round(r.anios_de_datos), "aprobadas": r.aprobadas,
                      "nivel": caso.NIVELES_CORTOS[r.nivel], "etiqueta": caso.NIVELES[r.nivel]},
        "comparacion": {"variable": aerosoles.nombre, "a": {"nombre": DELHI[0], **_serie(a)},
                        "b": {"nombre": PEKIN[0], **_serie(b)}},
    }


def demo_html(datos_demo: dict, reproducir_sola: bool = True) -> str:
    """La animación completa en un solo archivo HTML."""
    # Los números de numpy no son JSON: se convierten a su equivalente de Python.
    como_json = json.dumps(datos_demo, ensure_ascii=False, default=lambda x: x.item())
    return (PLANTILLA.replace("__DATOS__", como_json)
            .replace("__AUTO__", "true" if reproducir_sola else "false"))


PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expediente Tierra: recorrido</title>
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
.datos-cierre { display: flex; gap: 70px; margin-top: 70px; border-top: 3px solid var(--tinta); padding-top: 26px; }
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
.barras { display: grid; grid-template-columns: 560px 1fr; column-gap: 28px; row-gap: 15px; align-items: center; margin-top: 8px; }
.barras .rot { text-align: right; font-size: 25px; white-space: nowrap; }
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
</style></head>
<body>
<div id="marco"><div id="lienzo">
  <div class="marca">Expediente Tierra</div><div class="contador" id="contador"></div>

  <section class="escena portada" data-dur="5" data-nombre="Portada">
    <div class="eyebrow a">NASA Space Apps 2026 · Earth System Trend Detective</div>
    <div class="eyebrow a" style="--d:.15s;color:var(--tinta);margin-top:10px">Equipo C15H25N3O</div>
    <h1 class="a" style="--d:.35s">Expediente<br>Tierra</h1>
    <p class="lead a" style="--d:.75s">Herramienta para detectar tendencias en variables terrestres.</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="El problema">
    <div class="cab a"><span class="n">01</span><h2>Una gráfica que sube no prueba una tendencia</h2></div>
    <p class="lead a" style="--d:.5s">Los datos del clima tienen autocorrelación: cada mes se parece al anterior. La prueba clásica lo ignora y encuentra tendencias donde no las hay.</p>
    <div class="medidor">
      <div class="fila a" style="--d:1.5s"><div><div class="eyebrow">Falsos positivos · prueba clásica</div><div class="v">14–64 %</div></div>
        <div class="pista"><b class="crece" style="width:64%;background:var(--tinta);--d:2s"></b><div class="ideal"><span>lo esperado: 5 %</span></div></div></div>
      <div class="fila a" style="--d:3.6s"><div><div class="eyebrow">Falsos positivos · este método</div><div class="v">3–4 %</div></div>
        <div class="pista"><b class="crece" style="width:4%;background:var(--acento);--d:4.1s"></b><div class="ideal"></div></div></div>
    </div>
    <p class="nota a" style="--d:5.6s">Medido con miles de series sintéticas sin tendencia. Cinco pruebas, todas corregidas por autocorrelación.</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="Empezar un análisis">
    <div class="cab a"><span class="n">02</span><h2>Empezar un análisis</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:40px">Tres preguntas: qué te interesa, dónde, y qué esperas encontrar.</p>
    <div class="tarjeta a" style="--d:.9s">
      <div><div class="campo">Tema de interés</div>
        <div class="opcion"><i></i>Temperatura</div>
        <div class="opcion sel" style="--d:2.2s"><i></i>Precipitación y agua</div>
        <div class="opcion"><i></i>Calidad del aire</div>
        <div class="opcion"><i></i>Vegetación y cultivos</div>
        <div class="opcion"><i></i>Heladas y nieve</div></div>
      <div><div class="campo">Sitio de estudio</div>
        <div class="selector"><span class="a" style="--d:3.6s" id="sitio-demo"></span><span>⌄</span></div>
        <p class="nota a" style="--d:3.9s;margin-top:22px">Cualquier lugar del mundo, por nombre o por coordenadas.</p></div>
      <div><div class="campo">Hipótesis</div>
        <div class="opcion"><i></i>Está aumentando</div>
        <div class="opcion sel" style="--d:5.2s"><i></i>Está disminuyendo</div>
        <div class="opcion"><i></i>No está cambiando</div></div>
    </div>
    <div class="boton pulsa" style="--d:6.2s">Iniciar el análisis</div>
  </section>

  <section class="escena" data-dur="5" data-nombre="Exploración de variables">
    <div class="cab a"><span class="n">03</span><h2>Exploración de variables</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:26px"><span id="n-variables"></span> variables de la NASA, ordenadas por la magnitud de su tendencia.</p>
    <div class="barras" id="barras"></div>
    <p class="nota a" style="--d:6.2s">Cada tendencia se mide contra la variabilidad normal de esa variable, para comparar grados con milímetros. Tono fuerte: significativa.</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="Distribución espacial">
    <div class="cab a"><span class="n">04</span><h2>Distribución espacial</h2></div>
    <div class="dos" style="grid-template-columns: 780px 1fr">
      <div class="a" style="--d:.5s"><svg id="mapa" viewBox="0 0 620 620" width="720" height="720"></svg>
        <div class="leyenda-mapa"><span id="mapa-min"></span><div></div><span id="mapa-max"></span></div></div>
      <div>
        <p class="lead a" style="--d:.9s;margin-bottom:44px">Dónde cambia: la tendencia de cada celda de la región, de 2° a 10° de lado.</p>
        <div class="cifra a" style="--d:3.4s"><div class="eyebrow">Tendencia negativa significativa</div><div class="v"><span data-cuenta id="mapa-baja"></span> %</div><div class="u">de la región pierde agua almacenada.<br>El punto marca las celdas significativas.</div></div>
      </div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="Serie de tiempo">
    <div class="cab a"><span class="n">05</span><h2>Serie de tiempo</h2></div>
    <div class="leyenda a" style="--d:.5s"><span><i style="border-color:#c3c2b7;border-top-width:2px"></i>Anomalía mensual</span><span><i style="border-color:var(--azul)"></i>Media móvil de 12 meses</span><span><i style="border-color:var(--tinta)"></i>Tendencia lineal</span><span><i class="banda"></i>Intervalo de confianza del 95 %</span></div>
    <svg id="serie" viewBox="0 0 1728 640" width="1728" height="640"></svg>
    <p class="nota a" style="--d:6.6s;margin-top:6px">Sin el ciclo de las estaciones queda el cambio de fondo: almacenamiento de agua terrestre medido por los satélites GRACE.</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="Pruebas de significancia">
    <div class="cab a"><span class="n">06</span><h2>Pruebas de significancia</h2></div>
    <p class="lead a" style="--d:.4s;margin-bottom:30px">Una tendencia visible puede ser casualidad. Solo la que supera las cinco es sólida.</p>
    <div id="pruebas"></div>
  </section>

  <section class="escena" data-dur="5" data-nombre="Resultado">
    <div class="cab a"><span class="n">07</span><h2>Resultado</h2></div>
    <div class="eyebrow a" style="--d:.4s" id="res-etiqueta"></div>
    <div class="titular a" style="--d:.55s" id="res-titular"></div>
    <div class="cifras">
      <div class="a" style="--d:1.3s"><div class="eyebrow">Tasa de cambio</div><div class="v"><span data-cuenta id="res-decada"></span></div><div class="u" id="res-u1"></div></div>
      <div class="a" style="--d:1.6s"><div class="eyebrow">Cambio acumulado</div><div class="v"><span data-cuenta id="res-total"></span></div><div class="u" id="res-u2"></div></div>
      <div class="a" style="--d:1.9s"><div class="eyebrow">Pruebas superadas</div><div class="v" id="res-pruebas"></div><div class="u">pruebas de significancia</div></div>
      <div class="a" style="--d:2.2s"><div class="eyebrow">Nivel de evidencia</div><div class="v" id="res-nivel"></div><div class="u">&nbsp;</div></div>
    </div>
    <div class="contraste a" style="--d:4.6s">
      <div><div class="eyebrow">Rodell et al. (2009), Nature</div><div class="v">4.0 ± 1.0</div><p>cm por año de agua subterránea perdida, 2002–2008</p></div>
      <div><div class="eyebrow">Esta herramienta, misma región y periodo</div><div class="v">3.8</div><p>cm por año: dentro del margen del artículo</p></div>
    </div>
  </section>

  <section class="escena" data-dur="5" data-nombre="Comparación de dos lugares">
    <div class="cab a"><span class="n">08</span><h2>Tendencias opuestas</h2></div>
    <div class="leyenda a" style="--d:.5s"><span><i style="border-color:var(--azul)"></i><span id="cmp-a"></span></span><span><i style="border-color:var(--naranja)"></i><span id="cmp-b"></span></span></div>
    <svg id="comparacion" viewBox="0 0 1728 600" width="1728" height="600"></svg>
    <p class="nota a" style="--d:6s;margin-top:6px">La misma variable en dos lugares: el espesor óptico de aerosoles aumenta en Delhi y disminuye en Pekín.</p>
  </section>

  <section class="escena" data-dur="5" data-nombre="Informe">
    <div class="cab a"><span class="n">09</span><h2>Informe descargable</h2></div>
    <div class="dos">
      <div>
        <p class="lead a" style="--d:.4s">Cada análisis se descarga como un informe listo para compartir o imprimir.</p>
        <ul class="lista">
          <li class="a" style="--d:1.2s">Portada, resumen y ficha de la variable</li>
          <li class="a" style="--d:1.5s">Gráficas, pruebas y mapa de tendencias</li>
          <li class="a" style="--d:1.8s">Ficha técnica, supuestos y limitaciones</li>
          <li class="a" style="--d:2.1s">Referencias con enlace DOI</li>
        </ul>
        <div class="boton pulsa" style="--d:3.4s">Descargar el informe</div>
      </div>
      <div class="hojas">
        <div class="hoja" style="left:250px;top:70px;--giro:7deg;--d:1.5s"><div class="l m"></div><div class="l t" style="width:55%"></div><div class="regla"></div><div class="l"></div><div class="l c"></div><div class="l"></div><div class="regla"></div><div class="l c"></div><div class="l"></div><div class="l"></div><div class="l c"></div></div>
        <div class="hoja" style="left:130px;top:40px;--giro:2deg;--d:1.1s"><div class="l m"></div><div class="l t" style="width:48%"></div><svg viewBox="0 0 370 200" width="370" height="200"><polyline points="0,40 40,60 80,50 120,90 160,84 200,120 240,112 280,150 320,146 370,176" fill="none" stroke="#2a78d6" stroke-width="4"/><line x1="0" y1="38" x2="370" y2="178" stroke="#0b0b0b" stroke-width="3"/></svg><div class="regla"></div><div class="l"></div><div class="l c"></div><div class="l"></div></div>
        <div class="hoja" style="left:10px;top:10px;--giro:-4deg;--d:.7s"><div class="l m"></div><div class="l m" style="width:28%;background:var(--tinta)"></div><div class="l t" style="height:34px;margin-top:22px"></div><div class="l t" style="height:34px;width:60%;margin-top:0"></div><div class="l c" style="margin-top:20px"></div><div style="height:150px"></div><div class="regla"></div><div class="l c"></div><div class="l"></div><div class="l c"></div><div class="l"></div></div>
      </div>
    </div>
  </section>

  <section class="escena portada" data-dur="5" data-nombre="Cierre">
    <div class="eyebrow a">NASA Space Apps 2026 · Equipo C15H25N3O</div>
    <h1 class="a" style="--d:.3s;font-size:150px">Expediente Tierra</h1>
    <p class="lead a" style="--d:.7s">Qué cambia, dónde, cuánto, y si el cambio es significativo.</p>
    <div class="datos-cierre">
      <div class="a" style="--d:1.3s"><div class="v" id="fin-variables"></div><div class="eyebrow e">variables</div></div>
      <div class="a" style="--d:1.55s"><div class="v">5</div><div class="eyebrow e">pruebas de significancia</div></div>
      <div class="a" style="--d:1.8s"><div class="v">5</div><div class="eyebrow e">productos de datos de la NASA</div></div>
      <div class="a" style="--d:2.05s"><div class="v">3–4 %</div><div class="eyebrow e">falsos positivos</div></div>
    </div>
  </section>

  <div class="avance"><i id="avance"></i></div>
</div></div>
<div id="controles"><button id="b-antes" aria-label="Escena anterior">Anterior</button><button id="b-pausa" class="principal">Pausa</button><button id="b-despues" aria-label="Escena siguiente">Siguiente</button><div id="tramos" aria-label="Escenas"></div><button id="b-reinicio">Reiniciar</button><span id="rotulo"></span></div>

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

// ---- textos que salen de los datos
$("sitio-demo").textContent = D.sitio;
$("n-variables").textContent = D.variables; $("fin-variables").textContent = D.variables;
$("res-etiqueta").textContent = D.resultado.etiqueta;
$("res-titular").textContent = D.resultado.variable + ": en " + (D.resultado.decada < 0 ? "descenso" : "aumento") + ", con evidencia " + D.resultado.nivel.toLowerCase();
$("res-decada").dataset.valor = D.resultado.decada; $("res-total").dataset.valor = D.resultado.total;
$("res-u1").textContent = D.resultado.unidad + " por década"; $("res-u2").textContent = D.resultado.unidad + " en " + D.resultado.anios + " años";
$("res-pruebas").textContent = D.resultado.aprobadas + "/5"; $("res-nivel").textContent = D.resultado.nivel;
$("mapa-baja").dataset.valor = D.mapa.baja;
$("cmp-a").textContent = D.comparacion.a.nombre + " · " + menos(D.comparacion.a.decada) + " por década";
$("cmp-b").textContent = D.comparacion.b.nombre + " · " + menos(D.comparacion.b.decada) + " por década";

// ---- exploración: barras desde el centro
(function () {
  const tope = Math.max(...D.exploracion.map(v => Math.abs(v.valor))) * 1.12;
  D.exploracion.forEach((v, k) => {
    const d = (1.1 + k * .32).toFixed(2), ancho = Math.abs(v.valor) / tope * 50, positiva = v.valor > 0;
    const tono = positiva ? (v.firme ? "#e34948" : "#f3b3b2") : (v.firme ? "#2a78d6" : "#9ec5f4");
    const fila = document.createElement("div"); fila.style.display = "contents"; if (v.elegida) fila.className = "elegida";
    fila.innerHTML = `<div class="rot a" style="--d:${d}s">${v.nombre}</div><div class="eje">` +
      `<b class="crece" style="--d:${d}s;--origen:${positiva ? "left" : "right"};background:${tono};width:${ancho}%;${positiva ? "left:50%" : "right:50%"}"></b>` +
      (ancho > 30
        ? `<span class="a" style="--d:${(+d + .5).toFixed(2)}s;color:#fff;${positiva ? `right:calc(50% - ${ancho}% + 14px)` : `left:calc(50% - ${ancho}% + 14px)`}">${menos((v.valor > 0 ? "+" : "") + v.valor.toFixed(2))}</span></div>`
        : `<span class="a" style="--d:${(+d + .5).toFixed(2)}s;${positiva ? `left:calc(50% + ${ancho}% + 12px)` : `right:calc(50% + ${ancho}% + 12px)`}">${menos((v.valor > 0 ? "+" : "") + v.valor.toFixed(2))}</span></div>`);
    $("barras").appendChild(fila);
  });
})();

// ---- mapa por celda
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
  $("mapa-min").textContent = menos((-tope).toFixed(0)); $("mapa-max").textContent = "+" + tope.toFixed(0) + " " + D.mapa.unidad + "/década";
})();

// ---- gráficas de líneas
function marcas(min, max, cuantas) {
  const bruto = (max - min) / cuantas, base = Math.pow(10, Math.floor(Math.log10(bruto)));
  const paso = [1, 2, 5, 10].map(m => m * base).find(p => p >= bruto), out = [];
  for (let k = Math.ceil(min / paso); k <= Math.floor(max / paso); k++) out.push(k * paso);
  return out;
}
function lienzo(svg, series, alto) {
  const izq = 86, der = 200, arriba = 18, abajo = 44, ancho = 1728;
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
  return { px, py, camino, ancho, der };
}
(function () {
  const s = D.serie, svg = $("serie"), g = lienzo(svg, [s], 640);
  const banda = s.t.map((a, k) => g.px(a).toFixed(1) + "," + g.py(Math.max(s.alto[k], s.bajo[k])).toFixed(1)).join(" ") + " " +
                [...s.t].reverse().map((a, k) => { const i = s.t.length - 1 - k; return g.px(a).toFixed(1) + "," + g.py(Math.min(s.alto[i], s.bajo[i])).toFixed(1); }).join(" ");
  el("polygon", { points: banda, fill: "#0b0b0b", "fill-opacity": .11, class: "funde", style: "--d:4.2s" }, svg);
  el("path", { d: g.camino(s.t, s.y), fill: "none", stroke: "#c3c2b7", "stroke-width": 2, pathLength: 1, class: "traza", style: "--d:.9s;--t:2.2s" }, svg);
  el("path", { d: g.camino(s.t, s.suave), fill: "none", stroke: "#2a78d6", "stroke-width": 5, "stroke-linejoin": "round", pathLength: 1, class: "traza", style: "--d:1.9s;--t:2.4s" }, svg);
  el("path", { d: g.camino(s.t, s.recta), fill: "none", stroke: "#0b0b0b", "stroke-width": 5, pathLength: 1, class: "traza", style: "--d:4.2s;--t:1.3s" }, svg);
  const fin = s.t.length - 1, r = el("text", { x: g.px(s.t[fin]) + 18, y: g.py(s.recta[fin]) + 4, class: "rotulo funde", style: "--d:5.4s" }, svg);
  r.textContent = menos(s.decada); const r2 = el("text", { x: g.px(s.t[fin]) + 18, y: g.py(s.recta[fin]) + 32, class: "funde", style: "--d:5.4s" }, svg); r2.textContent = "cm por década";
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

// ---- pruebas
D.pruebas.forEach((p, k) => {
  const d = (1.1 + k * 1.05).toFixed(2), fila = document.createElement("div"); fila.className = "prueba a"; fila.style.setProperty("--d", d + "s");
  const marca = p.pasa ? `<svg width="22" height="22" viewBox="0 0 22 22"><path d="M4 11.5l4.5 4.5L18 6.5" fill="none" stroke="#0a6b2d" stroke-width="2.6" pathLength="1" class="traza" style="--d:${(+d + .55).toFixed(2)}s;--t:.5s"/></svg>` : "";
  fila.innerHTML = `<div class="estado ${p.pasa ? "" : "no"}">${marca}${p.pasa ? "Pasa" : "No pasa"}</div><div><div class="nom">${p.nombre}</div><div class="res">${p.resultado}</div></div>`;
  $("pruebas").appendChild(fila);
});

// ---- línea de tiempo
const K = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--k")) || 1;
const escenas = [...document.querySelectorAll(".escena")], duraciones = escenas.map(e => +e.dataset.dur * 1000), total = duraciones.reduce((a, b) => a + b, 0);
const inicios = duraciones.map((_, i) => duraciones.slice(0, i).reduce((a, b) => a + b, 0));
let actual = -1, transcurrido = 0, anterior = null, pausado = !AUTO, terminado = false;

// Una barra por escena: muestra el avance y sirve para saltar a cualquiera.
const tramos = escenas.map((e, i) => { const b = document.createElement("button"); b.title = e.dataset.nombre; b.setAttribute("aria-label", "Ir a: " + e.dataset.nombre);
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
  $("rotulo").textContent = (i + 1) + " de " + escenas.length + " · " + escenas[i].dataset.nombre;
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
function estado() { $("b-pausa").textContent = terminado ? "Ver de nuevo" : pausado ? "Reproducir" : "Pausa"; }
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
    RUTA.parent.mkdir(exist_ok=True)
    RUTA.write_text(demo_html(datos_de_demo()), encoding="utf-8")
    print(f"Animación escrita en {RUTA} ({RUTA.stat().st_size / 1024:.0f} KB)")
