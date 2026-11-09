"""Animação: as mesmas transformações geométricas, agora em função do tempo t.

Para um objeto com matriz local M, a matriz animada é

    M(t) = T(osc(t)) · M · R(ω·t) · S(p(t), p(t))

    osc(t) = (ax, ay) · sin(2π·f·t)      oscilação nos eixos do pai
    ω                                      velocidade angular (°/s)
    p(t)   = 1 + a·sin(2π·f·t)            pulsação da escala

A rotação e a pulsação atuam nos eixos locais do objeto (à direita de M),
por isso um objeto roda sobre o seu próprio centro; num grupo, os filhos
orbitam em torno do pivô do grupo (ver o exemplo "Sistema solar").
"""

from __future__ import annotations

import colorsys
import math

from .matrix import Mat3
from .shapes import Animation


def animated_matrix(local: Mat3, anim: Animation, t: float) -> Mat3:
    m = local
    if anim.rotate:
        m = m @ Mat3.rotation(anim.rotate * t)
    if anim.pulse:
        s = 1.0 + anim.pulse * math.sin(2.0 * math.pi * anim.pulse_freq * t)
        m = m @ Mat3.scaling(s, s)
    if anim.osc_x or anim.osc_y:
        ph = math.sin(2.0 * math.pi * anim.osc_freq * t)
        m = Mat3.translation(anim.osc_x * ph, anim.osc_y * ph) @ m
    return m


def animated_color(rgba, anim: Animation, t: float):
    """Roda a matiz (modelo HLS) — 'alteração dinâmica de cores'."""
    if not anim.hue:
        return rgba
    r, g, b, a = rgba
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + anim.hue * t / 360.0) % 1.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r, g, b, a)
