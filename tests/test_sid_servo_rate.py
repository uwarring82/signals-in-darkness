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
# ------------------------------------------------------------------ ND3 against the production filter
def test_ND3_the_kl_filter_reproduces_a_brute_force_path_sum_at_nonzero_correlation():
    """The brute force must check the filter D runs, not a loop rewritten in the test."""
    chain = sr.latent_chain(0.5, 0.6, 4, 3.0)
    E0 = sr.emissions(chain["x"], PH1, PH2)[0]
    E1 = sr.modulated_emissions(chain["x"], PH1, PH2, ssq=0.25)
    y = [0, 3, 1, 2, 0]

    def brute(E):
        total = 0.0
        for path in itertools.product(range(4), repeat=len(y) + 1):
            w = chain["pi"][path[0]]
            for n, yn in enumerate(y, 1):
                w *= chain["T"][path[n - 1], path[n]] * E[yn][path[n]]
            total += w
        return math.log(total)

    out = sr.kl_rate(y, chain, E1, E0)
    assert float(out["increments"].sum()) == pytest.approx(brute(E1) - brute(E0), rel=1e-12)


def test_ND3_rejects_replacing_correlated_filtering_with_iid_marginalisation():
    """At rho > 0 the stationary-marginal shortcut is a different number; the rho = 0 nesting
    check cannot see this, which is why ND3 runs at nonzero correlation."""
    chain = sr.latent_chain(0.5, 0.6, 4, 3.0)
    E0 = sr.emissions(chain["x"], PH1, PH2)[0]
    E1 = sr.modulated_emissions(chain["x"], PH1, PH2, ssq=0.25)
    y = [0, 3, 1, 2, 0]

    def brute(E):
        total = 0.0
        for path in itertools.product(range(4), repeat=len(y) + 1):
            w = chain["pi"][path[0]]
            for n, yn in enumerate(y, 1):
                w *= chain["T"][path[n - 1], path[n]] * E[yn][path[n]]
            total += w
        return math.log(total)

    def iid_marginalised(E):
        p = E @ chain["pi"]
        return float(np.sum(np.log(p[np.asarray(y)])))

    truth = brute(E1) - brute(E0)
    assert abs(iid_marginalised(E1) - iid_marginalised(E0) - truth) > 1e-6
    assert float(sr.kl_rate(y, chain, E1, E0)["increments"].sum()) == pytest.approx(truth, rel=1e-12)


def test_the_analytic_signal_marginal_differs_from_the_truncated_grid_by_a_deterministic_amount():
    """Finding 1: the simulator draws a continuous Gaussian, so the likelihood must use its exact
    marginal. run7's 41-point truncated sum is a different law, and the gap is reported, not hidden."""
    chain = _chain(0.0)
    x, pi = chain["x"], chain["pi"]
    E0 = sr.emissions(x, 0.0, 0.0)[0]
    analytic = sr.iid_kl(sr.modulated_emissions(x, 0.0, 0.0), E0, pi)
    truncated = sr.iid_kl(sr.modulated_emissions_grid(x, 0.0, 0.0), E0, pi)
    assert truncated != pytest.approx(analytic, rel=1e-5)
    assert abs(truncated / analytic - 1) == pytest.approx(1.2e-3, rel=0.25)


# ------------------------------------------------------------------ intervals, allowance, verdicts
T15 = 2.131449545559323


def test_the_ratio_interval_transforms_endpoint_to_endpoint_and_refuses_a_nonpositive_bound():
    values = [1.0] * 8 + [1.2] * 8
    out = sr.ratio_interval(values, 1.0, T15)
    half = T15 * float(np.std(values, ddof=1)) / 4
    assert out["J_lo"] == pytest.approx(1.1 - half) and out["J_hi"] == pytest.approx(1.1 + half)
    assert out["signed"][0] == pytest.approx(math.sqrt(1.1 - half) - 1)
    assert out["signed"][1] == pytest.approx(math.sqrt(1.1 + half) - 1)
    # two widely separated records: the interval reaches below zero, where the transform has no image
    wide = sr.ratio_interval([0.05, 1.0], 1.0, T15)
    assert wide["J_lo"] < 0 and wide["nonpositive"] and wide["signed"] is None


def test_the_absolute_image_of_an_interval_spanning_zero_contains_zero():
    assert sr.absolute_interval((-0.01, 0.03)) == (0.0, 0.03)
    assert sr.absolute_interval((-0.05, 0.02)) == (0.0, 0.05)
    assert sr.absolute_interval((0.01, 0.03)) == (0.01, 0.03)
    assert sr.absolute_interval((-0.05, -0.02)) == (0.02, 0.05)


def test_the_allowance_is_half_the_relative_residuals_summed():
    assert sr.allowance_in_ratio_units([0.004, 0.002]) == pytest.approx(0.003)
    assert sr.allowance_in_ratio_units([]) == 0.0
    assert sr.widen((0.0, 0.018), 0.003) == pytest.approx((0.0, 0.021))
    assert sr.widen((0.03, 0.05), 0.011) == pytest.approx((0.019, 0.061))


def test_classification_treats_contact_with_the_tolerance_as_unresolved():
    assert sr.classify((0.0, 0.0199), 0.02) == "BELOW"
    assert sr.classify((0.0, 0.02), 0.02) == "UNRESOLVED"        # exact contact from below
    assert sr.classify((0.02, 0.05), 0.02) == "UNRESOLVED"       # exact contact from above
    assert sr.classify((0.0201, 0.05), 0.02) == "ABOVE"
    assert sr.classify((0.001, 0.05), 0.02) == "UNRESOLVED"


def test_the_numerical_allowance_can_turn_a_decided_verdict_into_unresolved():
    """The verdict must survive the widening: passing a convergence threshold is not enough."""
    values = [0.9801, 0.9801, 0.9801, 0.9801] * 4          # sqrt(0.9801) - 1 = -0.01, no spread
    decided = sr.verdict(values, 1.0, T15, [], 0.02)
    assert decided["absolute"] == pytest.approx((0.01, 0.01))
    assert decided["classification"] == "BELOW"
    widened = sr.verdict(values, 1.0, T15, [0.004, 0.002], 0.02)   # allowance 0.003
    assert widened["allowance"] == pytest.approx(0.003)
    assert widened["widened"] == pytest.approx((0.007, 0.013))
    assert widened["classification"] == "BELOW"
    exhausted = sr.verdict(values, 1.0, T15, [0.02], 0.02)         # allowance 0.01
    assert exhausted["widened"] == pytest.approx((0.0, 0.02))
    assert exhausted["classification"] == "UNRESOLVED", "exact contact after widening"
    assert exhausted["classification_before_allowance"] == "BELOW", "and it was decided before"


def test_a_nonpositive_lower_bound_never_forms_the_ratio():
    out = sr.verdict([0.05, 1.0], 1.0, T15, [0.001], 0.02)
    assert out["classification"] == "UNRESOLVED" and out["absolute"] is None
    assert "not positive" in out["reason"]


def test_the_library_does_no_io_and_keeps_the_baseline_separate():
    source = (ROOT / "analysis" / "lib" / "sid_servo_rate.py").read_text()
    tree = ast.parse(source)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "open" not in calls
    imports = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert not any("run7" in name or name == "sid_servo" for name in imports)
    assert "environ" not in source
