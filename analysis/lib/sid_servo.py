"""The four-outcome servo likelihood, extracted from analysis/runs/sid_run7.py section B.

Roadmap D (note 29) needs this law under a correlated oscillator phase, and the existing baseline
lives only inside a run script with no test over it. This module is the extraction, arithmetic for
arithmetic, so that D's correlated work and the published baseline share one implementation.

sid_run7.py and its artifact analysis/outputs/res7B_servo.json are unchanged; the tests hold this
module to that artifact.

Two details of run7 that are easy to lose and are preserved here:
  * the two channels search different offset grids -- the slope channel maximises over the full
    13 x 13 grid, the variance channel over grid[::3];
  * kappa -> infinity is a known limiting case with its own closed form, carried by an explicit
    sentinel string rather than a null (see analysis/outputs/SCHEMA.md).

The oscillator phase here is redrawn independently each shot, which is the assumption roadmap D
exists to test. Nothing in this module models a correlated phase.
"""
import math

import numpy as np
from scipy.optimize import brentq

from sid_lib import I_ext_exact

KAPPA_INF = "positive-infinity"
KAPPAS = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, math.inf)
CONTRAST = 0.9                      # run7's C1 = C2
SSQ = 0.3 ** 2                      # run7's white modulation variance for the variance channel
PHASE = np.linspace(-math.pi, math.pi, 4001)[:-1]
OUTCOMES = [(b1, b2) for b1 in (-1, 1) for b2 in (-1, 1)]


def offset_grid(n=13):
    """run7's phase-offset search grid."""
    return [(a, b) for a in np.linspace(0, math.pi, n) for b in np.linspace(0, math.pi, n)]


def slope_offsets(n=13):
    return offset_grid(n)


def variance_offsets(n=13):
    """The variance channel searches every third offset. Run7 does; so does D."""
    return offset_grid(n)[::3]


def von_mises_weights(kappa, mu=0.0, phase=PHASE):
    """Normalised von Mises weights on the phase grid; None marks the perfect-oscillator limit."""
    if kappa == math.inf:
        return None
    q = np.exp(kappa * np.cos(phase - mu))
    return q / q.sum()


def four_outcome(eps, kappa, ph1, ph2, C1=CONTRAST, C2=CONTRAST, phase=PHASE):
    """P(B1, B2) marginalised over the oscillator phase, which is independent between shots."""
    q = von_mises_weights(kappa, phase=phase)
    if q is None:
        c1, c2 = C1 * math.cos(ph1), C2 * math.cos(eps + ph2)
        return {(b1, b2): 0.25 * (1 + b1 * c1) * (1 + b2 * c2) for b1, b2 in OUTCOMES}
    c1, c2 = C1 * np.cos(phase + ph1), C2 * np.cos(phase + eps + ph2)
    return {(b1, b2): float(np.sum(q * 0.25 * (1 + b1 * c1) * (1 + b2 * c2))) for b1, b2 in OUTCOMES}


def parity(P):
    return {+1: P[(1, 1)] + P[(-1, -1)], -1: P[(1, -1)] + P[(-1, 1)]}


def kl(P, Q):
    return sum(P[k] * math.log(P[k] / Q[k]) for k in P if P[k] > 0)


def fisher(kappa, ph1, ph2, full=True, d=1e-4, **kw):
    """Fisher information in eps at eps = 0, by central difference, as run7 computes it."""
    Pp, Pm = four_outcome(d, kappa, ph1, ph2, **kw), four_outcome(-d, kappa, ph1, ph2, **kw)
    P0 = four_outcome(0.0, kappa, ph1, ph2, **kw)
    if not full:
        Pp, Pm, P0 = parity(Pp), parity(Pm), parity(P0)
    return sum(((Pp[k] - Pm[k]) / (2 * d)) ** 2 / P0[k] for k in P0)


def var_channel(kappa, ph1, ph2, ssq=SSQ, full=True, **kw):
    """KL of a white Gaussian phase modulation of variance ssq against none (extremum-type channel)."""
    xs = np.linspace(-4, 4, 41) * math.sqrt(ssq)
    wts = np.exp(-xs ** 2 / (2 * ssq))
    wts /= wts.sum()
    P1 = {k: 0.0 for k in OUTCOMES}
    for x, wt in zip(xs, wts):
        P = four_outcome(float(x), kappa, ph1, ph2, **kw)
        for k in OUTCOMES:
            P1[k] += wt * P[k]
    P0 = four_outcome(0.0, kappa, ph1, ph2, **kw)
    if not full:
        P1, P0 = parity(P1), parity(P0)
    return kl(P1, P0)


def ceff_from_kl(value, ssq=SSQ):
    """The equivalent binary-link contrast: invert I_ext_exact(C, sqrt(ssq)) = value."""
    f = lambda c: I_ext_exact(c, math.sqrt(ssq)) - value        # noqa: E731
    return brentq(f, 1e-4, 0.999999) if f(0.999999) > 0 else 1.0


def servo_row(kappa, ssq=SSQ, n=13, **kw):
    """One row of res7B_servo.json: kappa, slope C_eff (parity, full), variance C_eff (parity, full)."""
    slope, variance = slope_offsets(n), variance_offsets(n)
    fi_par = max(fisher(kappa, a, b, False, **kw) for a, b in slope)
    fi_full = max(fisher(kappa, a, b, True, **kw) for a, b in slope)
    kv_par = max(var_channel(kappa, a, b, ssq, False, **kw) for a, b in variance)
    kv_full = max(var_channel(kappa, a, b, ssq, True, **kw) for a, b in variance)
    label = KAPPA_INF if math.isinf(kappa) else kappa
    return (label, math.sqrt(fi_par), math.sqrt(fi_full), ceff_from_kl(kv_par, ssq),
            ceff_from_kl(kv_full, ssq))
