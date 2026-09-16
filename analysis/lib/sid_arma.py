"""Roadmap F reference computations for the frozen protocol analysis/protocol_F.json.

Frozen digest b7c09ce90f33c37b. Design and review history: notes/2026-09-15-note-28-F-protocol-draft.md.
The driver is analysis/runs/sid_run13.py.

A pure library: no file I/O, no global state, no thread configuration. The driver owns seeds,
deadlines, refusals and artifacts.

Protocol section                          implementation
  reference_filter.parameters             filter_factor, ma_root, arma_parameters, burn_in
  reference_filter.grid .. emission       grid, transition, emission, arma_model
  reference_filter.stationary_init        stationary_distribution, stationary_requirements (NC4)
  reference_filter.first_step, recursion  arma_filter; arma_filter_pair_state (the literal form)
  reference_filter.ar1_nesting_reference  ar1_model, ar1_filter, nesting_check (NC1)
  reference_filter.committed_code_tie     committed_code_tie
  simulator                               simulate_window_record, simulator_statistics, simulator_check (NC2)
  comparators, NC3_series                 comparators, series_rate, geometric_rate, series_convergence_check
  NC5_grid, NC6_finite_history            pass_window_mean, paired_criterion
  pilot                                   seed_summary, pilot_bound
  shot_rule, evaluation, verdicts         per_seed_length, mean_interval, verdict

Choices the protocol leaves open, recorded for review:
  1. Filter form. The protocol states the pair-state recursion over alpha(i', i). Its next step
     uses only beta(i') = sum_i alpha(i', i), so arma_filter carries beta and applies
     TE_y = T.T * E_y, with TE_y[i', i] = T[i, i'] E_y(i', i). The first step,
     alpha~_m(i, j) = pi(j) T[j, i] E(i, j), is the same product applied to beta = pi.
     arma_filter_pair_state is the literal recursion; the tests hold the two together and hold
     both to a brute-force sum over latent paths.
  2. Simulator columns. Within a block, columns 0 and 1 of standard_normal((block, 3)) feed the
     lower Cholesky factor of the window covariance, and column 2 is the dead-time normal. The
     start-of-window frequency obeys z <- e^{-d} (e^{-u} z + xi_1) + sqrt(1 - e^{-2d}) xi_3,
     evaluated with scipy.signal.lfilter; a test holds it to a plain per-shot loop.
  3. NC1 sums. The per-increment tolerance applies to every increment. The summed tolerance
     applies to the estimator's window n = W+1..N, since the reference shares the estimator.
  4. NC2 statistics use the sample mean: the variance with ddof = 1, and the lag-k
     autocorrelation sum_n e_n e_{n+k} / sum_n e_n^2 of the centred phase.
  5. Band edges. "Inside [1 - delta, 1 + delta]" includes the edges; "disjoint" excludes them.
  6. Tie arithmetic. committed_code_tie reproduces sid_lib.hmm_rate's own accumulation: log Z summed
     into a running float and the null summed by numpy. Estimators keep math.fsum over the
     increments, which is the better summation but a different rounding: at N = 200000 the two
     differ by about 1e-12 relative, enough to fail the frozen tie tolerance on a correct filter
     (Gate-2 review).
"""
import math
import time
from contextlib import nullcontext

import numpy as np
from scipy.signal import lfilter

THETA = math.pi / 2
LOG_HALF = math.log(0.5)
STATIONARY_RESIDUAL_MAX = 1e-12
STATIONARY_MIN = -1e-15
REPLICATES = 16
CHUNK = 16384


# ------------------------------------------------------------------------------------------- deadlines
class DeadlineReached(RuntimeError):
    """A step reached its enforced wall-clock limit. The protocol records it INCOMPLETE."""


class Deadline:
    """An absolute limit on a monotonic clock, checked between chunks of work."""

    def __init__(self, seconds, clock=time.monotonic):
        self.clock = clock
        self.end = clock() + seconds

    def remaining(self):
        return self.end - self.clock()

    def check(self):
        if self.clock() >= self.end:
            raise DeadlineReached("deadline reached")


def _check(deadline):
    if deadline is not None:
        deadline.check()


# ------------------------------------------------------------------------------------------- parameters
def filter_factor(u):
    """F(u) = (cosh u - 1)/(u - 1 + e^{-u}); 1 in the point-sampling limit u = 0."""
    return (math.cosh(u) - 1) / (u - 1 + math.exp(-u)) if u else 1.0


def ma_root(F, phi):
    """MA coefficient b, |b| < 1, of eps_n = x_n + b x_{n-1} whose lag-one correlation is F phi."""
    A = phi * (1 - F)
    B = 1 + phi * phi - 2 * F * phi * phi
    if A == 0.0:
        return 0.0
    disc = B * B - 4 * A * A
    if disc < 0:
        raise ValueError("finite-window spectrum is negative at omega = pi")
    b = min(((-B + math.sqrt(disc)) / (2 * A), (-B - math.sqrt(disc)) / (2 * A)), key=abs)
    rho1 = (phi * (1 + b * b) + b * (1 + phi * phi)) / (1 + b * b + 2 * b * phi)
    if not math.isclose(rho1, F * phi, rel_tol=1e-12, abs_tol=0.0):
        raise AssertionError("MA root does not reproduce rho_1 = F phi")
    return b


def burn_in(c_over_tau_c):
    return max(1000, math.ceil(100 / c_over_tau_c))


def arma_parameters(s, u, c_over_tau_c):
    F, phi = filter_factor(u), math.exp(-c_over_tau_c)
    b = ma_root(F, phi)
    v_x = s * s / (1 + b * b + 2 * b * phi)
    return {"F": F, "phi": phi, "b": b, "v_x": v_x, "q": v_x * (1 - phi * phi), "W": burn_in(c_over_tau_c)}


# ------------------------------------------------------------------------------------------- latent chain
def grid(v_x, M, L):
    half = L * math.sqrt(v_x)
    return np.linspace(-half, half, M)


def transition(g, phi, q):
    """T[i, i'] proportional to exp(-(g_i' - phi g_i)^2 / (2 q)); every row normalised to 1."""
    T = np.exp(-(g[None, :] - phi * g[:, None]) ** 2 / (2 * q))
    return T / T.sum(axis=1, keepdims=True)


def emission(C, g, b, y):
    """E_y[i', i] = (1 + (2y - 1) C cos(theta + g_i' + b g_i))/2."""
    p1 = 0.5 * (1 + C * np.cos(THETA + g[:, None] + b * g[None, :]))
    return p1 if y else 1 - p1


def stationary_requirements(T, pi):
    """NC4: sum |pi T - pi| <= 1e-12 and min(pi) >= -1e-15."""
    residual = float(np.abs(pi @ T - pi).sum())
    minimum = float(np.min(pi))
    ok_res, ok_min = residual <= STATIONARY_RESIDUAL_MAX, minimum >= STATIONARY_MIN
    return {"residual": residual, "minimum": minimum, "residual_within_1e-12": bool(ok_res),
            "min_at_least_-1e-15": bool(ok_min), "pass": bool(ok_res and ok_min)}


def stationary_distribution(T):
    """Left eigenvector of T for the eigenvalue nearest 1 (eig of T transpose, real part, sum 1).

    The requirements are evaluated on that vector. Entries in [-1e-15, 0) are then set to 0 and
    pi is renormalised; entries below -1e-15 stay, and the requirement has failed."""
    w, V = np.linalg.eig(T.T)
    pi = np.real(V[:, int(np.argmin(np.abs(w - 1)))])
    pi = pi / pi.sum()
    report = stationary_requirements(T, pi)
    pi = np.where((pi < 0) & (pi >= STATIONARY_MIN), 0.0, pi)
    return pi / pi.sum(), report


def arma_model(C, s, u, c_over_tau_c, M, L):
    par = arma_parameters(s, u, c_over_tau_c)
    g = grid(par["v_x"], M, L)
    T = transition(g, par["phi"], par["q"])
    pi, report = stationary_distribution(T)
    TE = (T.T * emission(C, g, par["b"], 0), T.T * emission(C, g, par["b"], 1))
    return {"C": C, "grid": f"M{M}_L{L}", "params": par, "g": g, "T": T, "TE": TE, "pi": pi,
            "stationary": report}


# ------------------------------------------------------------------------------------------- filters
def _binary(y):
    ys = np.asarray(y)
    if ys.size and (ys.min() < 0 or ys.max() > 1):
        raise ValueError("observations must be 0 or 1")
    return ys


def arma_filter(y, model, burn_in=0, keep=True, deadline=None, chunk=CHUNK):
    """One ARMA(1,1) pass whose first observation is y[0], started from pi.

    keep=True returns the log increments l_n for y[burn_in:]; keep=False returns
    (sum of those increments, their count) without storing them.
    """
    ys = _binary(y)
    n = len(ys)
    if not 0 <= burn_in <= n:
        raise ValueError("burn-in outside the record")
    TE = model["TE"]
    beta = model["pi"].copy()
    v = np.empty_like(beta)
    buf = np.empty(max(1, min(chunk, n)))
    out = np.empty(n - burn_in) if keep else None
    parts = []
    log, dot, divide = math.log, np.dot, np.divide
    for start in range(0, n, chunk):
        _check(deadline)
        block = ys[start:start + chunk].tolist()
        for j, yk in enumerate(block):
            dot(TE[yk], beta, out=v)
            z = v.sum()
            divide(v, z, out=beta)
            buf[j] = log(z)
        lo = max(burn_in - start, 0)
        if lo < len(block):
            inc = buf[lo:len(block)] - LOG_HALF
            if keep:
                out[start + lo - burn_in:start + len(block) - burn_in] = inc
            else:
                parts.append(math.fsum(inc))
    _check(deadline)
    return out if keep else (math.fsum(parts), n - burn_in)


def arma_filter_pair_state(y, model):
    """The protocol's literal pair-state recursion over alpha(i', i). Slow; for small grids."""
    T, g, C, b, pi = model["T"], model["g"], model["C"], model["params"]["b"], model["pi"]
    E = (emission(C, g, b, 0), emission(C, g, b, 1))
    out, alpha = [], None
    for yk in _binary(y).tolist():
        if alpha is None:
            tilde = pi[None, :] * T.T * E[yk]              # pi(j) T[j, i] E(i, j)
        else:
            beta = alpha.sum(axis=1)                        # beta(i) = sum_j alpha_{n-1}(i, j)
            tilde = T.T * beta[None, :] * E[yk]             # T[i, i'] beta(i) E(i', i)
        z = tilde.sum()
        alpha = tilde / z
        out.append(math.log(z) - LOG_HALF)
    return np.array(out)


def pass_window_mean(y, model, first_observation, window_first, window_last, deadline=None):
    """Mean increment over observations window_first..window_last (1-based) of a pass that starts
    from pi at first_observation and runs through the observations before the window as burn-in."""
    if not 1 <= first_observation <= window_first <= window_last <= len(y):
        raise ValueError("pass or window outside the record")
    total, count = arma_filter(y[first_observation - 1:window_last], model,
                               burn_in=window_first - first_observation, keep=False, deadline=deadline)
    return total / count


def ar1_model(C, s, phi, M, L):
    """The AR(1) nesting reference on the same grid convention with b = 0, so v_x = s^2."""
    g = grid(s * s, M, L)
    T = transition(g, phi, s * s * (1 - phi * phi))
    pi, report = stationary_distribution(T)
    e1 = 0.5 * (1 + C * np.cos(THETA + g))
    return {"grid": f"M{M}_L{L}", "g": g, "T": T, "E": (1 - e1, e1), "pi": pi, "stationary": report}


def ar1_filter(y, model, initial=None, propagate_first=False, deadline=None, log_evidence=False):
    """alpha~_1(i) = w(i) E_{y1}(i), with w = pi unless given; alpha~_n(i') = sum_i alpha_{n-1}(i) T[i, i'] E_{yn}(i').

    propagate_first applies T before the first emission as well, as sid_lib.hmm_rate does.
    log_evidence returns sum_n log Z_n accumulated in hmm_rate's own order and arithmetic, for the
    committed-code tie only; otherwise the increments l_n = log Z_n - log(1/2) are returned, and
    every estimator sums those with math.fsum."""
    T, E = model["T"], model["E"]
    alpha = (model["pi"] if initial is None else np.asarray(initial, dtype=float)).copy()
    ys = _binary(y).tolist()
    out = None if log_evidence else np.empty(len(ys))
    total = 0.0
    for k, yk in enumerate(ys):
        if k % CHUNK == 0:
            _check(deadline)
        if k or propagate_first:
            alpha = alpha @ T
        alpha = alpha * E[yk]
        z = alpha.sum()
        alpha /= z
        if log_evidence:
            total += math.log(z)                     # hmm_rate's running accumulation, bit for bit
        else:
            out[k] = math.log(z) - LOG_HALF
    _check(deadline)
    return total if log_evidence else out


def nesting_check(y, C, s, c_over_tau_c, M, L, W, arma=None, deadline=None):
    """NC1 on one grid: the ARMA filter at u = 0 (F = 1, b = 0) against the AR(1) reference.

    Also reports NC4 for the grid; the two models share T and therefore pi."""
    phi = math.exp(-c_over_tau_c)
    arma = arma_model(C, s, 0.0, c_over_tau_c, M, L) if arma is None else arma
    reference = ar1_model(C, s, phi, M, L)
    la = arma_filter(y, arma, deadline=deadline)
    lr = ar1_filter(y, reference, deadline=deadline)
    d = la - lr
    per_increment = bool(np.all(np.abs(d) <= 1e-12 + 1e-9 * np.abs(lr)))
    sum_d, sum_abs = math.fsum(d[W:]), math.fsum(np.abs(lr[W:]))
    window_sum = bool(abs(sum_d) <= 1e-9 * sum_abs)
    return {"grid": f"M{M}_L{L}", "b": arma["params"]["b"],
            "max_abs_increment_difference": float(np.max(np.abs(d))),
            "window_abs_sum_difference_over_sum_abs": abs(sum_d) / sum_abs,
            "per_increment_within_tolerance": per_increment, "window_sum_within_tolerance": window_sum,
            "NC4": arma["stationary"], "pass": per_increment and window_sum}


def committed_code_tie(C, s, c_over_tau_c, N, seed, M=121, deadline=None, guard=None):
    """The AR(1) reference, started from make_hmm's Gaussian-weight prior with one propagation by T
    before the first emission and W = 0, against sid_lib.hmm_rate on hmm_rate's own record.

    The comparison uses hmm_rate's own accumulation, so that the tie tests the filter and not the
    summation: stable summation of the same increments differs by about 1e-12 relative at
    N = 200000 and would fail the frozen tolerance on a correct filter.

    guard wraps the committed calls, which are uninterruptible loops; the driver passes one that
    raises DeadlineReached from a timer. Nothing starts once the deadline has passed."""
    import sid_lib
    _check(deadline)
    phi = math.exp(-c_over_tau_c)
    with (guard or nullcontext)():
        committed = float(sid_lib.hmm_rate(C, s, THETA, phi, N=N, seed=seed, M=M))
        y = sid_lib.simulate(C, s, THETA, phi, N, np.random.default_rng(seed))
        prior = sid_lib.make_hmm(C, s, THETA, phi, M)[4]
    ll1 = ar1_filter(y, ar1_model(C, s, phi, M, 5.0), initial=prior, propagate_first=True,
                     deadline=deadline, log_evidence=True)
    p0 = sid_lib.ramsey_probability(C, THETA)
    ll0 = float(np.sum(y * np.log(p0) + (1 - y) * np.log(1 - p0)))
    rel = abs((ll1 - ll0) / N - committed) / abs(committed)
    return {"N": N, "seed": seed, "M": M, "L": 5.0, "accumulation": "sid_lib.hmm_rate",
            "relative_difference": rel, "pass": bool(rel <= 1e-12)}


# ------------------------------------------------------------------------------------------- simulator
def simulate_window_record(C, s, u, c_over_tau_c, n, rng, return_phase=False, deadline=None, block=2 ** 20):
    """Exact OU window simulator in units of tau_c. Uses neither phi nor b.

    Draw order: z_0 = standard_normal(); then per block of at most 2^20 shots
    standard_normal((block, 3)) followed by random(block). Returns y as int8, and eps if asked."""
    if not u > 0:
        raise ValueError("the window simulator covers u > 0 only")
    d = c_over_tau_c - u
    if d < 0:
        raise ValueError("c/tau_c must be at least u")
    eu, e2u = math.exp(-u), math.exp(-2 * u)
    l11 = math.sqrt(1 - e2u)
    l21 = (1 - eu) ** 2 / l11
    l22 = math.sqrt(2 * (u - 2 * (1 - eu) + (1 - e2u) / 2) - l21 * l21)
    scale = s / math.sqrt(2 * (u - 1 + eu))
    ed, sd_dead = math.exp(-d), math.sqrt(1 - math.exp(-2 * d))
    a = ed * eu
    y = np.empty(n, dtype=np.int8)
    eps = np.empty(n) if return_phase else None
    z = rng.standard_normal()
    for start in range(0, n, block):
        _check(deadline)
        nb = min(block, n - start)
        normals = rng.standard_normal((nb, 3))
        uniforms = rng.random(nb)
        xi2 = l21 * normals[:, 0] + l22 * normals[:, 1]
        following, _ = lfilter([1.0], [1.0, -a], ed * l11 * normals[:, 0] + sd_dead * normals[:, 2], zi=[a * z])
        z_start = np.concatenate(([z], following[:-1]))
        z = following[-1]
        e = scale * ((1 - eu) * z_start + xi2)
        y[start:start + nb] = uniforms < 0.5 * (1 + C * np.cos(THETA + e))
        if return_phase:
            eps[start:start + nb] = e
    _check(deadline)
    return (y, eps) if return_phase else y


def simulator_statistics(eps, max_lag=5):
    e = eps - eps.mean()
    den = float(np.dot(e, e))
    return {"variance": float(np.var(eps, ddof=1)),
            "acf": [float(np.dot(e[:-k], e[k:]) / den) for k in range(1, max_lag + 1)]}


def simulator_check(per_seed, s, F, phi, n_se=5.0):
    """NC2: every statistic's mean over seeds lies within n_se across-seed standard errors of its exact value."""
    rows = [("variance", s * s, [p["variance"] for p in per_seed])]
    rows += [(f"acf_lag_{k}", F * phi ** k, [p["acf"][k - 1] for p in per_seed]) for k in range(1, 6)]
    out = []
    for name, exact, values in rows:
        mean = float(np.mean(values))
        se = float(np.std(values, ddof=1) / math.sqrt(len(values)))
        out.append({"statistic": name, "exact": exact, "mean_over_seeds": mean, "standard_error": se,
                    "pass": bool(abs(mean - exact) <= n_se * se)})
    return {"statistics": out, "pass": all(r["pass"] for r in out)}


# ------------------------------------------------------------------------------------------- comparators
def series_rate(C, s, A, phi, terms=6, nf=1024):
    """Sinh-series Gaussian spectral rate with r_k = C^2 exp(-s^2) sinh(s^2 A phi^k), as run4's kernel."""
    w = np.pi * (np.arange(nf) + 0.5) / nf
    x, pref = s * s * A, C * C * math.exp(-s * s)
    d = np.zeros_like(w)
    for m in range(terms):
        rho = pref * x ** (2 * m + 1) / math.factorial(2 * m + 1)
        am = phi ** (2 * m + 1)
        d += 2 * rho * (am * np.cos(w) - am * am) / (1 - 2 * am * np.cos(w) + am * am)
    return float(0.5 * np.mean(d - np.log1p(d)))


def geometric_rate(rho, a):
    """Closed form for r_k = rho a^k (k >= 1), as sid_lib.gp_rate_geom."""
    alpha = 1 + a * a - 2 * rho * a * a
    beta = 2 * a * (rho - 1)
    if abs(beta) < 1e-14:
        return 0.0
    b = (-alpha + math.sqrt(alpha * alpha - beta * beta)) / beta
    return -0.5 * math.log(alpha / (1 + b * b))


def comparators(C, s, u, c_over_tau_c):
    F, phi = filter_factor(u), math.exp(-c_over_tau_c)
    r1 = C * C * math.exp(-s * s) * math.sinh(s * s * F * phi)
    return {"K1": series_rate(C, s, F, phi), "K2": geometric_rate(r1 / phi, phi),
            "K3": geometric_rate(r1 / (phi * F), phi), "K4": series_rate(C, s, 1.0, phi)}


def series_convergence_check(C, s, u, c_over_tau_c, tol=1e-6, coarse=(6, 1024), fine=(12, 4096)):
    """NC3: K1 and K4 change by at most tol relative from (6 terms, 1024) to (12 terms, 4096)."""
    F, phi = filter_factor(u), math.exp(-c_over_tau_c)
    out = {}
    for key, A in (("K1", F), ("K4", 1.0)):
        change = series_rate(C, s, A, phi, *fine) / series_rate(C, s, A, phi, *coarse) - 1
        out[key] = {"relative_change": change, "pass": bool(abs(change) <= tol)}
    out["pass"] = out["K1"]["pass"] and out["K4"]["pass"]
    return out


# ------------------------------------------------------------------------------------------- criteria and rules
def paired_criterion(differences, K1, t_quantile, fraction=0.001):
    """NC5/NC6: |mean paired difference| + t x its standard error <= fraction x K1."""
    d = np.asarray(differences, dtype=float)
    mean = float(d.mean())
    se = float(d.std(ddof=1) / math.sqrt(len(d)))
    lhs = abs(mean) + t_quantile * se
    return {"mean_paired_difference": mean, "standard_error": se, "lhs": lhs, "limit": fraction * K1,
            "pass": bool(lhs <= fraction * K1)}


def seed_summary(increments, batches=(10, 20)):
    """A seed's mean and its var(batch means, ddof=1)/B terms. The mean serves S^2 only and is never recorded."""
    inc = np.asarray(increments, dtype=float)
    out = {"mean": float(inc.mean())}
    for B in batches:
        if len(inc) % B:
            raise ValueError("batches must be equal")
        out[B] = float(np.var(inc.reshape(B, -1).mean(axis=1), ddof=1) / B)
    return out


def pilot_bound(summaries, constants, stability_factor=4.0):
    """Approximate conservative planning bound U and the stability rule, from 16 seed summaries.

    Returns S^2, vbar_10, vbar_20 and the bounds; no per-seed mean and no average of them."""
    if len(summaries) != REPLICATES:
        raise ValueError("the pilot has 16 replicates")
    S2 = float(np.var([x["mean"] for x in summaries], ddof=1))
    vbar = {B: float(np.mean([x[B] for x in summaries])) for B in (10, 20)}
    chi2 = {15: constants["chi2_005_df15"], 144: constants["chi2_005_df144"], 304: constants["chi2_005_df304"]}
    U_seed = 15 * S2 / chi2[15]
    U_bm = {B: vbar[B] * (REPLICATES * (B - 1)) / chi2[REPLICATES * (B - 1)] for B in (10, 20)}
    raw = (S2, vbar[10], vbar[20])
    return {"S2": S2, "vbar_10": vbar[10], "vbar_20": vbar[20], "U_seed": U_seed, "U_bm10": U_bm[10],
            "U_bm20": U_bm[20], "U": max(U_seed, U_bm[10], U_bm[20]),
            "stable": bool(max(raw) <= stability_factor * min(raw))}


def per_seed_length(U, n_p, K1, t_quantile, kappa, delta):
    """n_e = max(n_p, 1000 ceil(t^2 U n_p / (16 (kappa delta K1)^2) / 1000))."""
    raw = t_quantile * t_quantile * U * n_p / (REPLICATES * (kappa * delta * K1) ** 2)
    return max(n_p, 1000 * math.ceil(raw / 1000))


def mean_interval(seed_means, t_quantile):
    """R_bar +/- t s_R / sqrt(16)."""
    m = np.asarray(seed_means, dtype=float)
    if len(m) != REPLICATES:
        raise ValueError("the evaluation has 16 replicates")
    R_bar, s_R = float(m.mean()), float(m.std(ddof=1))
    half = t_quantile * s_R / math.sqrt(REPLICATES)
    return {"R_bar": R_bar, "s_R": s_R, "R_lo": R_bar - half, "R_hi": R_bar + half}


def verdict(K, R_lo, R_hi, delta):
    """UNRESOLVED if R_lo <= 0; otherwise Q = [K/R_hi, K/R_lo] against [1 - delta, 1 + delta]."""
    if R_lo <= 0:
        return "UNRESOLVED"
    q_lo, q_hi = K / R_hi, K / R_lo
    if 1 - delta <= q_lo and q_hi <= 1 + delta:
        return "VALIDATED"
    if q_hi < 1 - delta or q_lo > 1 + delta:
        return "FAILED"
    return "UNRESOLVED"
