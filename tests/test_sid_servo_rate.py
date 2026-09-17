"""Synthetic tests for analysis/lib/sid_servo_rate.py (roadmap D1).

Small fixtures only: no design-point check, no pilot, no outcome-bearing computation. Every test
here corresponds to a numerical check named in note 29's D0 r3, and each is written so that it can
fail on the defect it guards.
"""
import ast
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
import sid_servo_rate as sr  # noqa: E402

PH1, PH2 = 0.4, 0.9
KAPPA = 5.0


def _chain(rho, M=121, L=6.0, kappa=KAPPA):
    return sr.latent_chain(sr.sigma_for_kappa(kappa), rho, M, L)


# ------------------------------------------------------------------ model and marginal
def test_the_marginal_matches_the_von_mises_first_circular_moment():
    from scipy.special import i0e, i1e
    for kappa in (1.0, 5.0, 10.0, 30.0):
        sigma = sr.sigma_for_kappa(kappa)
        assert math.exp(-sigma ** 2 / 2) == pytest.approx(float(i1e(kappa) / i0e(kappa)), rel=1e-12)
    assert sr.sigma_for_kappa(math.inf) == 0.0
    with pytest.raises(ValueError):
        sr.sigma_for_kappa(0.0)          # the uniform phase has no finite matching sigma
    assert sr.rho_for_tau(5) == pytest.approx(math.exp(-0.2), rel=1e-15)


def test_the_chain_is_stationary_and_refuses_an_unusable_rho():
    chain = _chain(sr.rho_for_tau(5))
    assert chain["stationary_residual"] < 1e-12
    assert chain["pi"].min() >= 0 and chain["pi"].sum() == pytest.approx(1.0, rel=1e-15)
    for bad in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError):
            sr.latent_chain(0.5, bad, 21, 5.0)


def test_emissions_are_a_probability_law_with_the_stated_derivative():
    chain = _chain(0.0, M=41)
    E, dE = sr.emissions(chain["x"], PH1, PH2)
    assert E.shape == (4, 41) and np.all(E > 0)
    np.testing.assert_allclose(E.sum(axis=0), 1.0, rtol=1e-14)
    assert dE.sum(axis=0) == pytest.approx(np.zeros(41), abs=1e-14)   # a derivative of a constant
    h = 1e-6
    numeric = (sr.emissions(chain["x"], PH1, PH2, eps=h)[0]
               - sr.emissions(chain["x"], PH1, PH2, eps=-h)[0]) / (2 * h)
    np.testing.assert_allclose(dE, numeric, rtol=1e-7, atol=1e-12)


def test_the_modulated_emissions_collapse_to_the_plain_ones_as_the_signal_vanishes():
    chain = _chain(0.0, M=41)
    plain = sr.emissions(chain["x"], PH1, PH2)[0]
    np.testing.assert_allclose(sr.modulated_emissions(chain["x"], PH1, PH2, ssq=1e-12), plain,
                               rtol=1e-6, atol=1e-9)


# ------------------------------------------------------------------ ND3: brute force
def test_the_filter_is_the_likelihood_of_the_discretised_chain():
    """ND3: on a four-point grid and a five-shot record, sum over every latent path."""
    chain = sr.latent_chain(0.5, 0.6, 4, 3.0)
    E, dE = sr.emissions(chain["x"], PH1, PH2)
    y = [0, 3, 1, 2, 0]
    total = 0.0
    for path in itertools.product(range(4), repeat=len(y) + 1):
        w = chain["pi"][path[0]]
        for n, yn in enumerate(y, 1):
            w *= chain["T"][path[n - 1], path[n]] * E[yn][path[n]]
        total += w
    filtered = 0.0
    alpha = chain["pi"].copy()
    for yn in y:
        t = (chain["T"].T @ alpha) * E[yn]
        z = t.sum()
        filtered += math.log(z)
        alpha = t / z
    assert filtered == pytest.approx(math.log(total), rel=1e-12)


# ------------------------------------------------------------------ ND1a and ND4
def test_ND1a_the_fisher_estimator_nests_exactly_at_rho_zero():
    chain = _chain(0.0)
    E, dE = sr.emissions(chain["x"], PH1, PH2)
    y, _ = sr.simulate(chain, PH1, PH2, 1500, np.random.default_rng(3))
    out = sr.fisher_rate(y, chain, E, dE)
    exact = sr.iid_fisher(E, dE, chain["pi"])
    assert out["J"] == pytest.approx(exact, rel=1e-10), "at rho = 0 this nests by construction"
    assert out["max_abs_tangent_sum"] < 1e-12
    assert out["shots"] == 1500


def test_ND4_the_score_matches_finite_differences_and_the_naive_normalisation_does_not():
    chain = _chain(sr.rho_for_tau(5), M=61, L=5.0)
    E, dE = sr.emissions(chain["x"], PH1, PH2)
    y, _ = sr.simulate(chain, PH1, PH2, 200, np.random.default_rng(7))

    def loglik(eps):
        Ee = sr.emissions(chain["x"], PH1, PH2, eps=eps)[0]
        alpha, total = chain["pi"].copy(), 0.0
        for yn in y.tolist():
            t = (chain["T"].T @ alpha) * Ee[yn]
            z = t.sum()
            total += math.log(z)
            alpha = t / z
        return total

    h = 1e-5
    reference = (loglik(h) - loglik(-h)) / (2 * h)
    assert sr.fisher_rate(y, chain, E, dE)["score"] == pytest.approx(reference, rel=1e-7)

    def naive_score():
        """alpha~'/Z with no quotient-rule term: the omission ND4 must reject."""
        alpha, alpha_p, score = chain["pi"].copy(), np.zeros_like(chain["pi"]), 0.0
        for yn in y.tolist():
            Ta, Tap = chain["T"].T @ alpha, chain["T"].T @ alpha_p
            at, apt = Ta * E[yn], Tap * E[yn] + Ta * dE[yn]
            z = at.sum()
            score += apt.sum() / z
            alpha, alpha_p = at / z, apt / z
        return score, alpha_p.sum()

    naive, tangent_sum = naive_score()
    assert abs(naive / reference - 1) > 1e-3, "the naive recursion must not pass as the score"
    assert abs(tangent_sum) > 1e-6, "and it breaks the sum-to-zero invariant"


# ------------------------------------------------------------------ ND1b: the KL nests differently
def test_ND1b_the_kl_increments_are_exact_at_rho_zero_but_its_mean_only_agrees_within_sampling():
    chain = _chain(0.0)
    E0 = sr.emissions(chain["x"], PH1, PH2)[0]
    E1 = sr.modulated_emissions(chain["x"], PH1, PH2)
    y, _ = sr.simulate(chain, PH1, PH2, 4000, np.random.default_rng(11), modulated=True)
    out = sr.kl_rate(y, chain, E1, E0)
    reference = sr.iid_log_likelihood_ratios(y, E1, E0, chain["pi"])
    assert np.max(np.abs(out["increments"] - reference)) < 1e-12      # increment-wise: exact
    analytic = sr.iid_kl(E1, E0, chain["pi"])
    se = float(out["increments"].std(ddof=1) / math.sqrt(out["shots"]))
    assert abs(out["D"] - analytic) < 4 * se, "the sampled average agrees only within sampling error"
    assert se > 0.1 * abs(analytic), "and at this length its standard error is not negligible"


# ------------------------------------------------------------------ ND2 and ND5
def test_ND2_the_rate_is_stable_in_grid_spacing_and_tail_range():
    y, _ = sr.simulate(_chain(sr.rho_for_tau(5)), PH1, PH2, 800, np.random.default_rng(17))
    values = {}
    for M, L in ((121, 6.0), (241, 6.0), (121, 7.0)):
        chain = _chain(sr.rho_for_tau(5), M=M, L=L)
        E, dE = sr.emissions(chain["x"], PH1, PH2)
        values[(M, L)] = sr.fisher_rate(y, chain, E, dE)["J"]
    base = values[(121, 6.0)]
    assert abs(values[(241, 6.0)] / base - 1) < 2e-3, "grid spacing"
    assert abs(values[(121, 7.0)] / base - 1) < 2e-3, "tail range"


def test_ND5_the_simulator_reproduces_its_own_moments():
    chain = _chain(sr.rho_for_tau(5))
    sigma = chain["sigma"]
    _, phases = sr.simulate(chain, PH1, PH2, 60000, np.random.default_rng(5))
    n_eff = len(phases) * (1 - chain["rho"] ** 2) / (1 + chain["rho"] ** 2)
    assert phases.var() == pytest.approx(sigma ** 2, rel=6 / math.sqrt(n_eff))
    assert float(np.corrcoef(phases[:-1], phases[1:])[0, 1]) == pytest.approx(chain["rho"], abs=6 / math.sqrt(n_eff))
    assert float(np.cos(phases).mean()) == pytest.approx(math.exp(-sigma ** 2 / 2), abs=6 / math.sqrt(n_eff))


def test_correlation_raises_the_conditional_information_here():
    """Not a claim about D's outcome: a sanity check that rho enters the estimator at all."""
    y, _ = sr.simulate(_chain(sr.rho_for_tau(5)), PH1, PH2, 1200, np.random.default_rng(23))
    rates = {}
    for rho in (0.0, sr.rho_for_tau(5)):
        chain = _chain(rho)
        E, dE = sr.emissions(chain["x"], PH1, PH2)
        rates[rho] = sr.fisher_rate(y, chain, E, dE)["J"]
    assert rates[0.0] != pytest.approx(rates[sr.rho_for_tau(5)], rel=1e-6)


# ------------------------------------------------------------------ purity
def test_the_library_does_no_io_and_keeps_the_baseline_separate():
    source = (ROOT / "analysis" / "lib" / "sid_servo_rate.py").read_text()
    tree = ast.parse(source)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "open" not in calls
    imports = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert not any("run7" in name or name == "sid_servo" for name in imports)
    assert "environ" not in source
