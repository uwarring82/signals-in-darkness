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
from scipy.signal import lfilter
from scipy.special import i0e, i1e

CONTRAST = 0.9                          # sid_run7 section B's C1 = C2
SSQ = 0.3 ** 2                          # its white modulation variance
MODULATION_POINTS = 41                  # its truncated grid for that modulation, kept for comparison
BLOCK = 1 << 16                         # the simulator's draw block; prefixes agree per whole block
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


def modulated_emissions(x, ph1, ph2, ssq=SSQ, C1=CONTRAST, C2=CONTRAST):
    """The exact Gaussian marginal of the white signal modulation.

    Averaging eps ~ N(0, ssq) gives E[cos(x + eps + ph2)] = exp(-ssq/2) cos(x + ph2), so the
    marginal law is the emission with C2 attenuated by that factor. This is what the simulator
    draws from, so the sampled likelihood ratio estimates the stated Gaussian KL exactly, up to the
    latent grid alone. sid_run7's 41-point truncated sum is a different law by a deterministic
    amount; modulated_emissions_grid keeps it for that comparison (review, 17 Sept 2026)."""
    return emissions(x, ph1, ph2, C1=C1, C2=C2 * math.exp(-ssq / 2))[0]


def modulated_emissions_grid(x, ph1, ph2, ssq=SSQ, points=MODULATION_POINTS, **kw):
    """sid_run7 section B's truncated 41-point average, for the deterministic difference only."""
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
def ratio_interval(per_record_J, J0, t_quantile):
    """The interval for g(J) = sqrt(J/J(0)) - 1 from paired per-record estimates of J(rho).

    J(0) is the deterministic reference, never a second Monte-Carlo estimate. g is monotone, so the
    signed interval maps endpoint to endpoint. A lower bound at or below zero cannot be transformed
    and is reported instead: the caller records UNRESOLVED without forming the ratio."""
    values = np.asarray(per_record_J, dtype=float)
    if len(values) < 2:
        raise ValueError("an interval needs at least two records")
    mean = float(values.mean())
    half = t_quantile * float(values.std(ddof=1)) / math.sqrt(len(values))
    lo, hi = mean - half, mean + half
    if lo <= 0:
        return {"J_mean": mean, "J_lo": lo, "J_hi": hi, "nonpositive": True,
                "signed": None, "records": len(values)}
    g = lambda J: math.sqrt(J / J0) - 1                                    # noqa: E731
    return {"J_mean": mean, "J_lo": lo, "J_hi": hi, "nonpositive": False,
            "signed": (g(lo), g(hi)), "records": len(values)}


def absolute_interval(signed):
    """The absolute-value image of a signed interval. One that spans zero must contain zero."""
    lo, hi = signed
    if lo <= 0 <= hi:
        return (0.0, max(abs(lo), abs(hi)))
    return (min(abs(lo), abs(hi)), max(abs(lo), abs(hi)))


def sizing_allowance_in_ratio_units(relative_J_residuals):
    """A first-order allowance in ratio units, for SIZING ONLY.

    g'(J) J = 1/2 at the reference, so a relative residual in J is about half as large in the ratio.
    Summed, not added in quadrature. This is adequate for choosing N, and it is NOT what classifies
    a verdict: halving can declare a case that the exact propagation leaves open. The review's
    counterexample is in the tests."""
    return 0.5 * math.fsum(abs(float(r)) for r in relative_J_residuals)


def numerical_allowances(relative_numerator, relative_denominator, J_mean, J0):
    """The adopted allowances in absolute rate units, kept separate for numerator and denominator.

    They come from refinement differences and are *adopted allowances*, not certified error bounds.
    Summed, not added in quadrature."""
    return (math.fsum(abs(float(r)) for r in relative_numerator) * J_mean,
            math.fsum(abs(float(r)) for r in relative_denominator) * J0)


def propagated_signed_interval(J_lo, J_hi, J0, e_rho=0.0, e_0=0.0):
    """The allowances propagated through the ratio exactly, before the absolute image is taken:

        lo = sqrt((J_lo - e_rho)/(J0 + e_0)) - 1,   hi = sqrt((J_hi + e_rho)/(J0 - e_0)) - 1.

    Widening the absolute interval by half the relative residual instead is only first order at the
    reference, and can turn a case the exact transformation leaves open into a decision.

    Returns None when a permitted numerator or denominator is not positive; the caller records
    UNRESOLVED rather than transforming."""
    numerator_lo, numerator_hi = J_lo - e_rho, J_hi + e_rho
    denominator_lo, denominator_hi = J0 + e_0, J0 - e_0
    if numerator_lo <= 0 or denominator_hi <= 0:
        return None
    return (math.sqrt(numerator_lo / denominator_lo) - 1, math.sqrt(numerator_hi / denominator_hi) - 1)


def classify(interval, tolerance):
    """BELOW, ABOVE, or UNRESOLVED. Touching the tolerance is UNRESOLVED, not a decision."""
    lo, hi = interval
    if hi < tolerance:
        return "BELOW"
    if lo > tolerance:
        return "ABOVE"
    return "UNRESOLVED"


def verdict(per_record_J, J0, t_quantile, tolerance, numerator_relative=(), denominator_relative=()):
    """The whole rule: the sampling interval, the adopted allowances propagated through the ratio,
    the absolute image, then classification. The verdict must survive the allowance."""
    interval = ratio_interval(per_record_J, J0, t_quantile)
    e_rho, e_0 = numerical_allowances(numerator_relative, denominator_relative, interval["J_mean"], J0)
    result = {**interval, "allowance_numerator": e_rho, "allowance_denominator": e_0}
    if interval["nonpositive"]:
        return {**result, "signed_with_allowance": None, "absolute": None,
                "classification": "UNRESOLVED", "reason": "the lower bound of J(rho) is not positive"}
    signed = propagated_signed_interval(interval["J_lo"], interval["J_hi"], J0, e_rho, e_0)
    if signed is None:
        return {**result, "signed_with_allowance": None, "absolute": None, "classification": "UNRESOLVED",
                "reason": "the allowance admits a nonpositive rate; the ratio is not formed"}
    absolute = absolute_interval(signed)
    return {**result, "signed_with_allowance": signed, "absolute": absolute,
            "classification": classify(absolute, tolerance),
            "classification_before_allowance": classify(absolute_interval(interval["signed"]), tolerance)}


def simulate(chain, ph1, ph2, n, rng, modulated=False, ssq=SSQ, C1=CONTRAST, C2=CONTRAST, block=BLOCK):
    """The AR(1) phase and its outcomes, in the continuum rather than on the filter's grid.

    Draw order: x_0 = standard_normal() * sigma; then, per block of at most BLOCK shots, the phase
    innovations, then the signal modulation, then one uniform per shot. The modulation is drawn
    under both hypotheses and multiplied by zero when unmodulated, so the stream does not depend on
    the hypothesis and records pair across it as well as across rho.

    Two records from one seed therefore agree on every complete block they share, and differ inside
    a partial block; the protocol regenerates at its frozen length rather than relying on prefixes
    of records of different lengths.

    The modulated hypothesis draws eps ~ N(0, ssq) per shot. modulated_emissions is exactly its
    per-shot marginal given x, so the filter's likelihood ratio estimates the stated Gaussian KL."""
    sigma, rho = chain["sigma"], chain["rho"]
    sd = math.sqrt(1 - rho * rho) * sigma
    x = rng.standard_normal() * sigma
    y = np.empty(n, dtype=np.int8)
    phases = np.empty(n)
    for start in range(0, n, block):
        nb = min(block, n - start)
        innovations = rng.standard_normal(nb)
        signal = rng.standard_normal(nb) * math.sqrt(ssq) * (1.0 if modulated else 0.0)
        uniforms = rng.random(nb)
        state, _ = lfilter([1.0], [1.0, -rho], sd * innovations, zi=[rho * x])
        x = state[-1]
        phases[start:start + nb] = state
        c1 = C1 * np.cos(state + ph1)
        c2 = C2 * np.cos(state + signal + ph2)
        probabilities = np.stack([0.25 * (1 + b1 * c1) * (1 + b2 * c2) for b1, b2 in OUTCOMES])
        y[start:start + nb] = (uniforms > np.cumsum(probabilities, axis=0)).sum(axis=0)
    return y, phases
