"""Shared dimensionless identifiability calculation from sid_run9 (roadmap E).

Extracted for tutorials, with the original grid, arithmetic and optimizer settings.
This module performs no I/O. See notes/2026-09-07-note-16-E-closure.md for why a
best-of-candidates estimate must not be called a certified global infimum.
"""
import math

import numpy as np
from scipy.optimize import minimize
from sid_lib import DB

G = 0.5
TAU_OVER_T2 = np.linspace(0.1, 2.0, 40)
REGIME = {0.4: "principal", 0.5: "principal", 0.9: "servo-context"}
# L-BFGS-B's defaults are absolute-dominated when the objective is ~1e-6: its ftol test
# divides by max(|f|, 1), so with |f| << 1 it stops on an absolute change of ~2e-9, which
# here is a relative change of ~3e-4. Under the reparameterisation from Gamma to
# Gamma/Gamma_hat that premature stop became visible -- the three starts landed on three
# different points spread over 1.1 %, and the infimum came out 6.15e-7 ABOVE res7A. With
# these tolerances the named starts stop prematurely far less often. They do NOT all reach the
# same solution -- see class_b_infimum and the determinism field of the artifact.
#
# They are tightened to the numerical floor and no further. scipy differentiates this
# objective by finite differences, so its gradient carries ~1e-14 absolute noise; asking for
# gtol below that made 46 of 108 starts return ABNORMAL_TERMINATION_IN_LNSRCH while still
# reporting the right minimum, which would have made the recorded convergence status
# worthless. At these values all 108 starts converge cleanly. See note 15.
OPT_OPTIONS = {"ftol": 1e-14, "gtol": 1e-9, "maxiter": 5000, "maxfun": 50000}

# Grid-refinement check, 7 Sept 2026: recomputing every row at GRID_N = 241 changed the
# best-of-candidates value by at most 1.281e-11 relatively (worst row C_0 = 0.5,
# eta_0 = 0.02, tau_c/T2 = 0.2). The scan is converged at 121; the figure depends on which
# candidates are compared, so the method is stated rather than the number alone.
GRID_REFINEMENT_CHECK = {"from": 121, "to": 241, "max_rel_change": 1.281e-11,
                         "worst_row": {"C_0": 0.5, "eta_0": 0.02, "tau_c_over_T2": 0.2},
                         "compared": "best-of-candidates value per row"}

GRID_N = 121


def s2_of(u, v):
    """Stationary Ramsey-phase variance at interrogation u = tau/T2, correlation v = tau_c/T2."""
    return G * G * 2.0 * (v * u - v * v * (1.0 - math.exp(-u / v)))


def pd(contrast):
    """Dark-fringe outcome probability for an effective contrast."""
    return (1.0 - contrast) / 2.0


def dephased_probability(C0, u, gamma=1.0, phase_variance=0.0):
    """Marginal dark probability for exponential baseline and Gaussian phase noise.

    u is tau/T2 and gamma is Gamma/Gamma_hat. Supports scalar or array inputs.
    This is the contrast-scan observation model, not a temporal likelihood.
    """
    return pd(C0 * np.exp(-gamma * np.asarray(u) - np.asarray(phase_variance) / 2))


def class_a_margin(u, phase_variance, eta0):
    """Positive iff the two pointwise dephasing bands are disjoint at u."""
    return phase_variance / 2 - 2 * (eta0 * u)


def _spread(record):
    """Absolute AND relative objective spread across the three NAMED starts.

    Absolute spread alone is misleading: at tau_c/T2 = 0.05 the infimum is of order 1e-9,
    where an absolute spread of 2.4e-9 is a 12 % disagreement. Both are recorded.
    """
    funs = [r["fun"] for r in record if r["kind"] == "named"]
    lo, hi = min(funs), max(funs)
    return hi - lo, ((hi - lo) / lo if lo > 0 else 0.0)


def _grid_beat(record):
    """By how much the deterministic grid route beat the best named start, relatively.

    Positive means the named multi-start missed the minimum and the grid caught it.
    """
    named = min(r["fun"] for r in record if r["kind"] == "named")
    grid = min(r["fun"] for r in record if r["kind"] != "named")
    return (named - grid) / grid if grid > 0 else 0.0


def _obj_grid(C0, s2, weights, gs, g0):
    """Vectorised objective over a mesh of (Gamma_s, Gamma_0)/Gamma_hat, for the grid scan."""
    u = TAU_OVER_T2[None, None, :]
    x = s2[None, None, :]
    w = weights[None, None, :]
    p = (1.0 - C0 * np.exp(-gs[:, None, None] * u - x / 2)) / 2.0
    q = (1.0 - C0 * np.exp(-g0[None, :, None] * u)) / 2.0
    return np.sum(w * (p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))), axis=2)


def class_b_infimum(C0, eta0, s2, weights):
    """Two-parameter infimum over the Markov class: three named starts AND a grid-and-polish.

    The class is chi(tau) = Gamma*tau with |Gamma - Gamma_hat| <= eta0*Gamma_hat. In T2
    units Gamma/Gamma_hat is the free variable, so the bounds are [1-eta0, 1+eta0].

    WHY THE GRID. Agreement between the three named starts does not certify a minimum. At
    C_0 = 0.4, eta_0 = 0.10, tau_c/T2 = 0.05 -- a PRINCIPAL row -- all three starts landed
    within 0.11 % of each other and all three were 9.7 % ABOVE the grid-stable minimum, which
    a deterministic grid scan finds at the g_0 boundary. Low across-start spread was therefore
    an unreliable indicator, and a bare best-of-three would have published the wrong number.
    The grid is deterministic, so this stays reproducible without a seed.

    The value returned is a BEST-OF-CANDIDATES estimate, not a certified global infimum.
    Every candidate is feasible, so its objective is an upper bound on the true infimum;
    a missed lower candidate can only reduce the information retained by this class.
    """
    def obj(v):
        gs, g0 = v
        return sum(wt * DB(pd(C0 * math.exp(-gs * u - x / 2)), pd(C0 * math.exp(-g0 * u)))
                   for wt, u, x in zip(weights, TAU_OVER_T2, s2))

    bounds = [(1.0 - eta0, 1.0 + eta0)] * 2
    named = ([1.0, 1.0], [1.0 - eta0, 1.0 + eta0], [1.0 + eta0, 1.0 - eta0])

    axis = np.linspace(1.0 - eta0, 1.0 + eta0, GRID_N)
    mesh = _obj_grid(C0, s2, weights, axis, axis)
    gi, gj = np.unravel_index(np.argmin(mesh), mesh.shape)
    grid_seed = [float(axis[gi]), float(axis[gj])]

    record = []
    for kind, x0 in [("named", s) for s in named] + [("grid-polish", grid_seed)]:
        r = minimize(obj, x0, bounds=bounds, method="L-BFGS-B", options=OPT_OPTIONS)
        record.append({
            "kind": kind,
            "x0": [float(a) for a in x0],
            "x": [float(a) for a in r.x],
            "fun": float(r.fun),
            "success": bool(r.success),
            "status": int(r.status),
            "nit": int(r.nit),
            "message": str(r.message),
        })
    record.append({"kind": "grid-raw", "x0": grid_seed, "x": grid_seed,
                   "fun": float(mesh[gi, gj]), "success": True, "status": 0, "nit": 0,
                   "message": f"deterministic {GRID_N}x{GRID_N} scan minimum"})
    selected = min(range(len(record)), key=lambda i: record[i]["fun"])
    return record, selected



def information_at(C0, eta0, v):
    """One row of roadmap E, recomputed without reading or writing artifacts.

    Equal allocation over TAU_OVER_T2, information per shot, no cycle-time cost.
    I_B retains the original three starts plus grid-and-polish candidate search.
    """
    w = np.ones_like(TAU_OVER_T2) / len(TAU_OVER_T2)
    chihat = TAU_OVER_T2.copy()
    s2 = np.array([s2_of(u, v) for u in TAU_OVER_T2])
    eta = eta0 * chihat

    I_unc = sum(wt * DB(pd(C0 * math.exp(-ch - x / 2)), pd(C0 * math.exp(-ch)))
                for wt, ch, x in zip(w, chihat, s2))

    # class A decouples per tau; the guard is the exact separation condition
    I_A, passing = 0.0, 0
    for wt, ch, x, e in zip(w, chihat, s2, eta):
        if class_a_margin(ch, x, eta0) > 0:
            I_A += wt * DB(pd(C0 * math.exp(-ch + e - x / 2)), pd(C0 * math.exp(-ch - e)))
            passing += 1

    record, selected = class_b_infimum(C0, eta0, s2, w)
    I_B = max(record[selected]["fun"], 0.0)

    I_ref = max(DB(pd(C0 * math.exp(-ch - x / 2)), pd(C0 * math.exp(-ch)))
                for ch, x in zip(chihat, s2))

    dG_over_Gamma = G * G * v                 # DeltaGamma_phi/Gamma_hat
    return {
        "C_0": C0,
        "regime": REGIME[C0],
        "eta_0": eta0,
        "tau_c_over_T2": v,
        "I_unc": I_unc,
        "I_A": I_A,
        "I_B": I_B,
        "I_ref": I_ref,
        "DeltaGamma_over_Gamma_hat": dG_over_Gamma,
        "DeltaGamma_over_2eta0_Gamma_hat": dG_over_Gamma / (2 * eta0),
        "class_A_points_passing": passing,
        "class_A_points_total": int(len(TAU_OVER_T2)),
        "optimizer": {"starts": record, "selected_index": selected,
                      "selected_fun": record[selected]["fun"],
                      "named_spread_abs": _spread(record)[0],
                      "named_spread_rel": _spread(record)[1],
                      "grid_beat_named": _grid_beat(record),
                      "grid_n": GRID_N,
                      "options": OPT_OPTIONS},
    }
