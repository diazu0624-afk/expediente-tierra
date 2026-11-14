"""¿Siguen calibradas las pruebas con series anuales cortas (GRACE tiene 19 años)?

Compara los falsos positivos de Mann-Kendall sin corregir con los de la versión que
corrige la autocorrelación, en series de 19, 25 y 45 años.

Uso:  .venv/bin/python -m validacion.series_cortas [repeticiones]
"""

from __future__ import annotations

import sys

import numpy as np

from expediente import estadistica as est
from validacion.calibracion import ruido_ar1

if __name__ == "__main__":
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    print(f"{'escenario':26s}{'MK sin corregir':>18s}{'MK corregido':>15s}{'potencia corregido':>21s}")
    for n in (19, 25, 45):
        for phi in (0.0, 0.3, 0.6):
            rng = np.random.default_rng(n * 10 + int(phi * 10))
            t = np.arange(n, dtype=float)
            simple = corregido = potencia = 0
            for _ in range(reps):
                y = ruido_ar1(rng, n, phi)
                simple += est.mann_kendall(y).p < est.ALFA
                corregido += est.mann_kendall_sin_memoria(t, y).prueba.p < est.ALFA
                potencia += est.mann_kendall_sin_memoria(t, y + 0.1 * t).prueba.p < est.ALFA
            print(f"{n} años, memoria {phi:.1f}".ljust(26) + f"{100 * simple / reps:17.1f}%"
                  f"{100 * corregido / reps:14.1f}%{100 * potencia / reps:20.1f}%", flush=True)
