# Expediente Tierra

Herramienta para el reto "Be an Earth System Trend Detective!" (NASA Space Apps 2026).
Eliges un lugar del planeta y la app responde qué está cambiando ahí, dónde, cuánto, y
si la tendencia es significativa.

## Correr la app

Necesitas Python 3.10 o más reciente.

En Mac, lo más fácil es hacer doble clic en `abrir.command`: la primera vez instala lo
necesario y después abre la app en el navegador. A mano, en Mac o Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

En Windows:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

Se abre en http://localhost:8501. Los seis casos de demostración funcionan sin cuentas ni
llaves, porque sus datos ya vienen guardados en `cache_power/`.

### Datos de satélite en lugares nuevos (opcional)

Las variables del modelo MERRA-2 salen de la API pública de NASA POWER y funcionan en
cualquier lugar. Las de satélite (lluvia de GPM, vegetación de MODIS, agua de GRACE) salen
de Google Earth Engine; para verlas en un lugar que no sea un caso de demostración hace
falta una cuenta con acceso a un proyecto de Earth Engine:

```bash
SSL_CERT_FILE=$(.venv/bin/python -m certifi) .venv/bin/earthengine authenticate
export EXPEDIENTE_EE_PROYECTO=el-id-de-tu-proyecto   # si no es el del equipo
```

Sin esa sesión la app sigue funcionando; solo avisa que los satélites no están disponibles.

## Cómo está organizada

| Archivo | Qué hace |
|---|---|
| `app.py` | La interfaz (Streamlit): lugar, rueda de sospechosos, interrogatorio, veredicto. |
| `expediente/variables.py` | Catálogo de variables con su definición en lenguaje sencillo. |
| `expediente/datos.py` | Descarga las series mensuales de NASA POWER (punto y región) y busca lugares por nombre. |
| `expediente/datos_gee.py` | Descarga GPM, MODIS y GRACE desde Google Earth Engine. |
| `expediente/region.py` | Mapa de tendencias celda por celda y promedio regional. |
| `expediente/estadistica.py` | Las pruebas: Mann-Kendall, prueba t, intervalos, corrección de memoria. |
| `expediente/caso.py` | Arma la rueda de sospechosos y aplica las cinco pruebas a una variable. |
| `expediente/veredicto.py` | Redacta el veredicto y el expediente descargable. |
| `expediente/graficas.py` | Las gráficas (Plotly). |
| `validacion/` | Simulaciones que miden qué tan seguido se equivocan las pruebas. |
| `tests/` | Pruebas automáticas. |

Los lugares consultados se guardan en `cache_power/`, así que un caso ya abierto funciona
sin internet.

## Verificar

```bash
.venv/bin/pip install pytest pymannkendall
.venv/bin/python -m pytest
.venv/bin/python -m validacion.calibracion   # falsos positivos de cada prueba
.venv/bin/python -m validacion.veredictos    # falsos positivos del veredicto completo
```

## Método en breve

- **Cuánto cambia:** pendiente de mínimos cuadrados sobre la serie sin ciclo estacional,
  con intervalo de confianza por simulación que conserva la memoria de la serie.
- **Si es significativo:** cinco pruebas. Mann-Kendall con preblanqueo iterativo
  (Zhang et al., 2000), prueba t con muestra efectiva (Santer et al., 2000), intervalo de
  confianza, repetición con promedios anuales y estabilidad al cambiar las fechas.
- **Qué variables mirar:** se escanean todas y se ordenan por tendencia estandarizada,
  con ajuste de Benjamini-Hochberg por comparaciones múltiples.
- **Cuánto falta para detectarla:** fórmula de Weatherhead et al. (1998).

No se incluyen nubosidad, radiación solar ni albedo: el producto que reparte POWER
(CERES SYN1deg) tiene saltos artificiales cuando cambian los satélites.
