"""Information rates for the four-outcome servo law under a correlated oscillator phase (roadmap D1).

Implements the accepted D0 specification, notes/2026-09-16-note-29-D-plan-draft.md r3. A pure
library: no file I/O, no global state. analysis/lib/sid_servo.py stays the independent-phase
baseline and is not modified here.

Three points the specification turns on, and this module implements literally:

  1. The latent state is the UNWRAPPED Gaussian AR(1) variable on a truncated real grid. The
     wrapped phase is not a Markov lumping of it: x and x + 2 pi share a phase, but their next-step
     means differ by 2 pi rho, which is not equivalent modulo 2 pi. The emissions are periodic and
     are evaluated directly at the grid points, so no wrapping step is needed anywhere.

  2. The normalised tangent carries its quotient-rule term. With u_n = Z'_n / Z_n,

         alpha'_n = alpha~'_n / Z_n - alpha_n u_n,   and   sum_i alpha'_{n,i} = 0

     at every step. Dividing alpha~'_n by Z_n alone gives a different score, which ND4 rejects.

  3. The Fisher estimator is the conditional-information average along the filtered history,

         J_hat = (1/N) sum_n sum_y [d_eps p_eps(y | Y_<n)]^2 / p_eps(y | Y_<n) |_{eps=0},

     not S_N^2/N, whose per-record variance does not shrink with N. The total score is returned
     alongside, for derivative checks only.

At rho = 0 the Fisher estimator reduces exactly to the single-shot information under the same
discretised marginal, which iid_fisher computes directly; the sampled KL average does not nest
exactly and is checked against iid_log_likelihood_ratios and iid_kl within sampling uncertainty.
"""
import math

import numpy as np
from scipy.special import i0e, i1e

CONTRAST = 0.9                          # sid_run7 section B's C1 = C2
SSQ = 0.3 ** 2                          # its white modulation variance
MODULATION_POINTS = 41                  # its Gauss grid for that modulation
OUTCOMES = [(b1, b2) for b1 in (-1, 1) for b2 in (-1, 1)]


# ------------------------------------------------------------------------------ marginal and chain
def sigma_for_kappa(kappa):
    """The Gaussian whose stationary first circular moment matches a von Mises at this kappa:
    exp(-sigma^2/2) = I1(kappa)/I0(kappa). Matching this moment does not make the two laws equal;
    ND6 measures what is left."""
    if kappa == math.inf:
        return 0.0
    if kappa <= 0:
        raise ValueError("kappa must be positive; kappa = 0 is the uniform phase, sigma is infinite")
    ratio = float(i1e(kappa) / i0e(kappa))          # scaled Bessels: the ratio is the unscaled one
    return math.sqrt(-2 * math.log(ratio))


def rho_for_tau(tau_shots):
    """AR(1) coefficient for a correlation time in shots."""
    return math.exp(-1.0 / tau_shots)


def latent_chain(sigma, rho, M, L):
    """The truncated real grid, its row-normalised transition and the chain's own stationary vector.

    Initialisation is the discretised chain's stationary distribution, not the continuous N(0, s^2):
    the two differ at the grid's resolution, and the filter is a chain, not the continuum."""
    if not 0 <= rho < 1:
        raise ValueError("rho must lie in [0, 1)")
    x = np.linspace(-L * sigma, L * sigma, M)
    q = (1 - rho * rho) * sigma * sigma
    T = np.exp(-(x[None, :] - rho * x[:, None]) ** 2 / (2 * q))
    T /= T.sum(axis=1, keepdims=True)
    w, V = np.linalg.eig(T.T)
    pi = np.real(V[:, int(np.argmin(np.abs(w - 1)))])
    pi = pi / pi.sum()
    residual = float(np.abs(pi @ T - pi).sum())
    return {"x": x, "T": T, "pi": pi, "sigma": sigma, "rho": rho, "M": M, "L": L,
            "stationary_residual": residual}


# ------------------------------------------------------------------------------ emissions
def emissions(x, ph1, ph2, eps=0.0, C1=CONTRAST, C2=CONTRAST):
    """The four-outcome law on the grid and its eps-derivative, as (4, M) arrays.

    P(b1, b2 | x, eps) = (1 + b1 C1 cos(x + ph1)) (1 + b2 C2 cos(x + eps + ph2)) / 4."""
    first = 1 + np.array([[b1] for b1, _ in OUTCOMES]) * (C1 * np.cos(x + ph1))[None, :]
    second_arg = x + eps + ph2
    second = 1 + np.array([[b2] for _, b2 in OUTCOMES]) * (C2 * np.cos(second_arg))[None, :]
    d_second = -np.array([[b2] for _, b2 in OUTCOMES]) * (C2 * np.sin(second_arg))[None, :]
    return 0.25 * first * second, 0.25 * first * d_second


def modulated_emissions(x, ph1, ph2, ssq=SSQ, points=MODULATION_POINTS, **kw):
    """Emissions marginalised over the white Gaussian signal modulation, on run7's own grid."""
    xs = np.linspace(-4, 4, points) * math.sqrt(ssq)
    weights = np.exp(-xs ** 2 / (2 * ssq))
    weights /= weights.sum()
    total = np.zeros((len(OUTCOMES), len(x)))
    for value, weight in zip(xs, weights):
        total += weight * emissions(x, ph1, ph2, eps=float(value), **kw)[0]
    return total


# ------------------------------------------------------------------------------ i.i.d. references
def iid_fisher(E, dE, pi):
    """The single-shot Fisher information under a given phase distribution: the rho = 0 limit of
    the conditional-information estimator, computed directly and deterministically."""
    p, dp = E @ pi, dE @ pi
    return float(np.sum(dp * dp / p))


def iid_kl(E1, E0, pi):
    """The single-shot KL of the modulated law against the unmodulated one."""
    p1, p0 = E1 @ pi, E0 @ pi
    return float(np.sum(p1 * np.log(p1 / p0)))


def iid_log_likelihood_ratios(y, E1, E0, pi):
    """Per-shot log ratios an i.i.d. record would give; ND1b compares the filter's increments here."""
    p1, p0 = E1 @ pi, E0 @ pi
    return np.log(p1[np.asarray(y)] / p0[np.asarray(y)])


# ------------------------------------------------------------------------------ rates
def fisher_rate(y, chain, E, dE, burn_in=0):
    """Conditional-information average along the filtered history, with the tangent recursion.

    Returns J (the estimator), the total score S_N (for derivative checks only), the final tangent
    sum, which must be 0, and the number of shots averaged."""
    T, alpha = chain["T"], chain["pi"].copy()
    alpha_p = np.zeros_like(alpha)
    ys = np.asarray(y)
    if burn_in >= len(ys):
        raise ValueError("burn-in leaves no shots to average")
    information, score, counted = 0.0, 0.0, 0
    worst_tangent_sum = 0.0
    for n, yn in enumerate(ys.tolist()):
        Ta, Tap = T.T @ alpha, T.T @ alpha_p
        p, dp = E @ Ta, dE @ Ta + E @ Tap            # the predictive law and its eps-derivative
        if n >= burn_in:
            information += float(np.sum(dp * dp / p))
            counted += 1
        at = Ta * E[yn]
        apt = Tap * E[yn] + Ta * dE[yn]
        z = at.sum()
        u = apt.sum() / z
        score += u
        alpha = at / z
        alpha_p = apt / z - alpha * u                # the quotient-rule term, not optional
        worst_tangent_sum = max(worst_tangent_sum, abs(float(alpha_p.sum())))
    return {"J": information / counted, "score": score, "shots": counted,
            "max_abs_tangent_sum": worst_tangent_sum}


def kl_rate(y, chain, E1, E0, burn_in=0):
    """The KL rate from two filters run on the same record, one per hypothesis.

    Returns the rate and the per-shot increments log(Z1_n / Z0_n), which ND1b checks against the
    i.i.d. log-likelihood ratios at rho = 0."""
    T = chain["T"]
    a1, a0 = chain["pi"].copy(), chain["pi"].copy()
    ys = np.asarray(y)
    increments = np.empty(len(ys))
    for n, yn in enumerate(ys.tolist()):
        t1, t0 = (T.T @ a1) * E1[yn], (T.T @ a0) * E0[yn]
        z1, z0 = t1.sum(), t0.sum()
        increments[n] = math.log(z1) - math.log(z0)
        a1, a0 = t1 / z1, t0 / z0
    kept = increments[burn_in:]
    return {"D": float(kept.mean()), "increments": increments, "shots": len(kept)}


# ------------------------------------------------------------------------------ simulator
def simulate(chain, ph1, ph2, n, rng, modulated=False, ssq=SSQ, C1=CONTRAST, C2=CONTRAST):
    """The AR(1) phase and its outcomes, in the continuum rather than on the filter's grid.

    Draw order per shot: the phase innovation, then the signal modulation when modulated, then one
    uniform for the outcome. The phase starts from its stationary law."""
    sigma, rho = chain["sigma"], chain["rho"]
    x = rng.standard_normal() * sigma
    innovations = rng.standard_normal(n)
    signal = rng.standard_normal(n) * math.sqrt(ssq) if modulated else np.zeros(n)
    uniforms = rng.random(n)
    sd = math.sqrt(1 - rho * rho) * sigma
    y = np.empty(n, dtype=np.int8)
    phases = np.empty(n)
    for k in range(n):
        x = rho * x + sd * innovations[k]
        phases[k] = x
        c1 = C1 * math.cos(x + ph1)
        c2 = C2 * math.cos(x + signal[k] + ph2)
        probabilities = [0.25 * (1 + b1 * c1) * (1 + b2 * c2) for b1, b2 in OUTCOMES]
        y[k] = int(np.searchsorted(np.cumsum(probabilities), uniforms[k], side="right"))
    return y, phases
