"""Cómo se escriben los números en los textos de la herramienta."""

from __future__ import annotations

from math import floor, isfinite, log10


def numero(x: float, signo: bool = False, cifras: int = 2) -> str:
    """Número con `cifras` cifras significativas, sin notación científica."""
    if not isfinite(x):
        return "—"
    if x == 0:
        return "0"
    decimales = min(max(cifras - 1 - floor(log10(abs(x))), 0), 8)
    return f"{x:+,.{decimales}f}" if signo else f"{x:,.{decimales}f}"


def valor_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
