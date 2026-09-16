"""Implementation tests for analysis/lib/sid_arma.py against the frozen protocol_F.json (Gate 2).

Synthetic fixtures only: no protocol seed and no likelihood evaluation at a protocol point. The
deterministic design evidence (comparators and parameters) is the one exception, because the
protocol makes its reproduction a contract. Every numerical check is shown to pass on a correct
input and to fail on a wrong one.
"""
import ast
import inspect
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
sys.path.insert(0, str(ROOT / "analysis" / "diagnostics"))
import sid_arma as sa  # noqa: E402
import sid_lib  # noqa: E402

DOC = json.loads((ROOT / "analysis" / "protocol_F.json").read_text())
CONST = DOC["constants"]
SYN = (0.6, 0.8, 0.25, 0.5)            # (C, s, u, c/tau_c), away from every protocol point


class StepClock:
    """A monotonic clock that advances dt on every reading."""

    def __init__(self, dt):
        self.t, self.dt = 0.0, dt

    def __call__(self):
        self.t += self.dt
        return self.t


# ------------------------------------------------------------------------------------------- contracts with the protocol
@pytest.mark.parametrize("name", sorted(DOC["design_evidence"]["points"]))
def test_parameters_and_comparators_reproduce_design_evidence(name):
    p, ev = DOC["points"][name], DOC["design_evidence"]["points"][name]
    par = sa.arma_parameters(p["s"], p["u"], p["c_over_tau_c"])
    for key in ("F", "phi", "b", "v_x", "q"):
        assert math.isclose(par[key], ev[key], rel_tol=1e-12, abs_tol=0.0), key
    assert par["W"] == ev["burn_in_W"]
    K = sa.comparators(p["C"], p["s"], p["u"], p["c_over_tau_c"])
    for key, value in ev["comparators"].items():
        assert math.isclose(K[key], value, rel_tol=1e-12, abs_tol=0.0), key   # implementation_contract
    nc3 = sa.series_convergence_check(p["C"], p["s"], p["u"], p["c_over_tau_c"])
    assert nc3["K1"]["pass"] is ev["series_convergence_within_1e-6"]["K1"]
    assert nc3["K4"]["pass"] is ev["series_convergence_within_1e-6"]["K4"]


def test_comparators_match_the_archived_kernels_read_through_the_ast():
    import review_F_plan
    ref = review_F_plan.comparators(*SYN)
    mine = sa.comparators(*SYN)
    for key in ("K1", "K2", "K3", "K4"):
        assert math.isclose(mine[key], float(ref[key]), rel_tol=1e-12, abs_tol=0.0), key


def test_ma_root_reproduces_the_first_lag_and_vanishes_when_point_sampled():
    for u, c in ((0.1, 0.15), (1.0, 1.05), (0.02, 0.03)):
        F, phi = sa.filter_factor(u), math.exp(-c)
        b = sa.ma_root(F, phi)
        assert abs(b) < 1
        assert math.isclose((phi * (1 + b * b) + b * (1 + phi * phi)) / (1 + b * b + 2 * b * phi), F * phi,
                            rel_tol=1e-12)
    assert sa.ma_root(1.0, 0.9) == 0.0
    assert sa.burn_in(0.15) == 1000 and sa.burn_in(0.05) == 2000 and sa.burn_in(0.028909964236957655) == 3460


# ------------------------------------------------------------------------------------------- the filter
def test_vector_filter_equals_the_literal_pair_state_recursion():
    model = sa.arma_model(*SYN, 9, 5)
    y = np.random.default_rng(7).integers(0, 2, 200).astype(np.int8)
    np.testing.assert_allclose(sa.arma_filter(y, model), sa.arma_filter_pair_state(y, model), rtol=1e-9, atol=1e-13)


def test_filter_is_the_likelihood_of_the_discretised_arma_chain():
    """Brute force over every latent path x_0..x_n on a four-point grid."""
    model = sa.arma_model(*SYN, 4, 3)
    y = [1, 0, 0, 1, 1]
    E = [sa.emission(SYN[0], model["g"], model["params"]["b"], k) for k in (0, 1)]
    total = 0.0
    for path in itertools.product(range(4), repeat=len(y) + 1):
        w = model["pi"][path[0]]
        for k, yk in enumerate(y, 1):
            w *= model["T"][path[k - 1], path[k]] * E[yk][path[k], path[k - 1]]
        total += w
    assert math.isclose(sa.arma_filter(y, model).sum(), math.log(total) - len(y) * math.log(0.5), rel_tol=1e-12)


def test_filter_modes_chunks_burn_in_and_windows_agree():
    model = sa.arma_model(*SYN, 15, 5)
    y = sa.simulate_window_record(*SYN, 1000, np.random.default_rng(5))
    full = sa.arma_filter(y, model)
    np.testing.assert_array_equal(sa.arma_filter(y, model, chunk=7), full)
    np.testing.assert_array_equal(sa.arma_filter(y, model, burn_in=300), full[300:])
    total, count = sa.arma_filter(y, model, burn_in=300, keep=False, chunk=64)
    assert count == 700 and math.isclose(total, math.fsum(full[300:]), rel_tol=1e-12)
    # a pass starting at observation 101, estimated over 401..1000, is the filter run on y[100:]
    tail = sa.arma_filter(y[100:], model)
    assert math.isclose(sa.pass_window_mean(y, model, 101, 401, 1000), math.fsum(tail[300:]) / 600, rel_tol=1e-12)
    with pytest.raises(ValueError):
        sa.arma_filter([0, 1, 2], model)
    with pytest.raises(ValueError):
        sa.arma_filter(y[:10], model, burn_in=11)
    with pytest.raises(ValueError):
        sa.pass_window_mean(y, model, 401, 101, 1000)


# ------------------------------------------------------------------------------------------- NC1 and the committed-code tie
def _nesting_record():
    return sid_lib.simulate(0.4, 0.5, sa.THETA, math.exp(-0.3), 5000, np.random.default_rng(101))


def test_NC1_nesting_passes_for_the_arma_filter_at_u_zero():
    r = sa.nesting_check(_nesting_record(), 0.4, 0.5, 0.3, 41, 5, 1000)
    assert r["b"] == 0.0 and r["NC4"]["pass"]
    assert r["per_increment_within_tolerance"] and r["window_sum_within_tolerance"] and r["pass"]


@pytest.mark.parametrize("defect", ["transition_not_transposed", "nonzero_b", "wrong_phi"])
def test_NC1_nesting_fails_for_a_defective_filter(defect):
    y = _nesting_record()
    model = sa.arma_model(0.4, 0.5, 0.0, 0.3, 41, 5)
    T, g = model["T"], model["g"]
    if defect == "transition_not_transposed":
        model["TE"] = (T * sa.emission(0.4, g, 0.0, 0), T * sa.emission(0.4, g, 0.0, 1))
    elif defect == "nonzero_b":
        model["TE"] = (T.T * sa.emission(0.4, g, 0.3, 0), T.T * sa.emission(0.4, g, 0.3, 1))
    else:
        model = sa.arma_model(0.4, 0.5, 0.0, 0.35, 41, 5)
    assert not sa.nesting_check(y, 0.4, 0.5, 0.3, 41, 5, 1000, arma=model)["pass"]


def test_committed_code_tie_passes_and_other_initialisations_fail_it():
    C, s, c, N, seed = 0.8, 1.0, 0.1, 5000, 202
    tie = sa.committed_code_tie(C, s, c, N, seed)
    assert tie["pass"], tie
    phi = math.exp(-c)
    committed = sid_lib.hmm_rate(C, s, sa.THETA, phi, N=N, seed=seed, M=121)
    assert committed > 1e-3                            # the relative criterion is meaningful here
    y = sid_lib.simulate(C, s, sa.THETA, phi, N, np.random.default_rng(seed))
    model = sa.ar1_model(C, s, phi, 121, 5.0)
    prior = sid_lib.make_hmm(C, s, sa.THETA, phi, 121)[4]
    for kwargs in ({"initial": None, "propagate_first": True}, {"initial": prior, "propagate_first": False}):
        rate = math.fsum(sa.ar1_filter(y, model, **kwargs)) / N
        assert abs(rate - committed) / committed > 1e-12, kwargs


def test_committed_code_tie_uses_hmm_rates_own_accumulation():
    """Gate-2 review regression: a correct filter summed with math.fsum fails the frozen 1e-12
    tolerance at N = 200000, because the two accumulations round differently."""
    C, s, c, N, seed = 0.6, 0.8, 0.5, 200000, 203
    tie = sa.committed_code_tie(C, s, c, N, seed, M=121)
    assert tie["pass"] and tie["accumulation"] == "sid_lib.hmm_rate", tie
    phi = math.exp(-c)
    committed = sid_lib.hmm_rate(C, s, sa.THETA, phi, N=N, seed=seed, M=121)
    y = sid_lib.simulate(C, s, sa.THETA, phi, N, np.random.default_rng(seed))
    prior = sid_lib.make_hmm(C, s, sa.THETA, phi, 121)[4]
    stable = math.fsum(sa.ar1_filter(y, sa.ar1_model(C, s, phi, 121, 5.0), initial=prior,
                                     propagate_first=True)) / N
    assert abs(stable - committed) / abs(committed) > 1e-12          # the summation, not the filter


def test_committed_code_tie_starts_no_committed_work_after_the_deadline(monkeypatch):
    monkeypatch.setattr(sid_lib, "hmm_rate", lambda *a, **k: pytest.fail("ran after the deadline"))
    with pytest.raises(sa.DeadlineReached):
        sa.committed_code_tie(0.8, 1.0, 0.1, 100, 202, deadline=sa.Deadline(0.0, StepClock(1.0)))


def test_committed_code_tie_runs_the_committed_calls_inside_the_guard():
    seen = []

    class Guard:
        def __enter__(self):
            seen.append("enter")

        def __exit__(self, *exc):
            seen.append("exit")
            return False

    assert sa.committed_code_tie(0.8, 1.0, 0.1, 2000, 202, guard=Guard)["pass"]
    assert seen == ["enter", "exit"]


# ------------------------------------------------------------------------------------------- simulator and NC2
def _loop_simulator(C, s, u, c, n, rng, block):
    eu, d = math.exp(-u), c - u
    l11 = math.sqrt(1 - math.exp(-2 * u))
    l21 = (1 - eu) ** 2 / l11
    l22 = math.sqrt(2 * (u - 2 * (1 - eu) + (1 - math.exp(-2 * u)) / 2) - l21 ** 2)
    z, ys, es = rng.standard_normal(), [], []
    for start in range(0, n, block):
        nb = min(block, n - start)
        normals, uniforms = rng.standard_normal((nb, 3)), rng.random(nb)
        for i in range(nb):
            xi1, xi2 = l11 * normals[i, 0], l21 * normals[i, 0] + l22 * normals[i, 1]
            e = s * ((1 - eu) * z + xi2) / math.sqrt(2 * (u - 1 + eu))
            z = math.exp(-d) * (eu * z + xi1) + math.sqrt(1 - math.exp(-2 * d)) * normals[i, 2]
            es.append(e)
            ys.append(int(uniforms[i] < 0.5 * (1 + C * math.cos(sa.THETA + e))))
    return np.array(ys), np.array(es)


def test_simulator_follows_the_frozen_draw_order_across_blocks():
    rng_a, rng_b = np.random.default_rng(11), np.random.default_rng(11)
    y, eps = sa.simulate_window_record(*SYN, 2500, rng_a, return_phase=True, block=1000)
    y_loop, eps_loop = _loop_simulator(*SYN, 2500, rng_b, 1000)
    np.testing.assert_array_equal(y, y_loop)
    np.testing.assert_allclose(eps, eps_loop, rtol=1e-9, atol=1e-12)
    assert rng_a.random() == rng_b.random()            # the same number of draws was consumed
    assert y.dtype == np.int8


def test_simulator_scope_and_independence_from_the_filter_parameters():
    with pytest.raises(ValueError):
        sa.simulate_window_record(0.4, 0.5, 0.0, 0.05, 10, np.random.default_rng(0))
    with pytest.raises(ValueError):
        sa.simulate_window_record(0.4, 0.5, 0.3, 0.2, 10, np.random.default_rng(0))
    names = {n.id for n in ast.walk(ast.parse(inspect.getsource(sa.simulate_window_record)))
             if isinstance(n, ast.Name)}
    assert not names & {"phi", "b", "ma_root", "arma_parameters", "filter_factor"}


def _nc2_stats(transform, n=40000):
    C, s, u, c = 0.6, 0.8, 0.5, 0.6
    out = []
    for r in range(8):
        _, eps = sa.simulate_window_record(C, s, u, c, n, np.random.default_rng(910000 + r), return_phase=True)
        out.append(sa.simulator_statistics(transform(eps, s, c, np.random.default_rng(920000 + r))))
    return out, s, sa.filter_factor(u), math.exp(-c)


def _point_sampled(eps, s, c, rng):
    """An AR(1) phase with the right variance and phi, but lag-one correlation phi instead of F phi."""
    from scipy.signal import lfilter
    phi = math.exp(-c)
    x = lfilter([1.0], [1.0, -phi], s * math.sqrt(1 - phi * phi) * rng.standard_normal(len(eps)),
                zi=[phi * s * rng.standard_normal()])[0]
    return x


@pytest.mark.parametrize("transform, expected", [
    (lambda eps, s, c, rng: eps, True),
    (lambda eps, s, c, rng: 1.1 * eps, False),
    (_point_sampled, False),
])
def test_NC2_simulator_check_passes_for_the_exact_simulator_and_fails_otherwise(transform, expected):
    stats, s, F, phi = _nc2_stats(transform)
    assert sa.simulator_check(stats, s, F, phi)["pass"] is expected


# ------------------------------------------------------------------------------------------- NC3 and NC4
def test_NC3_fails_when_the_series_is_truncated_too_early():
    assert sa.series_convergence_check(*SYN)["pass"]
    assert not sa.series_convergence_check(0.6, 1.5, 0.25, 0.5, coarse=(1, 16))["pass"]


def test_NC4_passes_for_the_eigenvector_and_fails_for_wrong_chains_or_initialisations():
    model = sa.arma_model(*SYN, 61, 7)
    assert model["stationary"]["pass"]
    T, g, vx = model["T"], model["g"], model["params"]["v_x"]
    assert not sa.stationary_distribution(0.9 * T)[1]["pass"]           # not a stochastic matrix
    five = sa.arma_model(*SYN, 61, 5)
    gauss = np.exp(-five["g"] ** 2 / (2 * vx))
    report = sa.stationary_requirements(five["T"], gauss / gauss.sum())
    assert not report["residual_within_1e-12"]                          # Gaussian weights are not stationary
    negative = np.full(5, 0.25)
    negative[0] = -1e-14
    assert not sa.stationary_requirements(np.eye(5), negative)["pass"]
    assert model["pi"].min() >= 0 and math.isclose(model["pi"].sum(), 1.0, rel_tol=1e-15)


# ------------------------------------------------------------------------------------------- NC5/NC6, pilot, shot rule, verdicts
def test_paired_criterion_includes_its_edge_and_fails_beyond_it():
    t7 = CONST["t_0975_df7"]
    assert sa.paired_criterion([1e-7] * 8, 1e-4, t7)["pass"]              # lhs == limit, SE = 0
    assert not sa.paired_criterion([1.01e-7] * 8, 1e-4, t7)["pass"]
    d = [0.0, 2e-8] * 4                                                    # mean 1e-8, SE 3.78e-9
    r = sa.paired_criterion(d, 1e-4, t7)
    assert math.isclose(r["lhs"], 1e-8 + t7 * np.std(d, ddof=1) / math.sqrt(8), rel_tol=1e-12)
    assert r["pass"] and not sa.paired_criterion(d, 1e-5, t7)["pass"]


def test_pilot_bound_arithmetic_stability_and_blindness():
    rng = np.random.default_rng(3)
    summaries = [sa.seed_summary(rng.normal(0.0, 1.0, 2000)) for _ in range(16)]
    bound = sa.pilot_bound(summaries, CONST)
    S2 = np.var([x["mean"] for x in summaries], ddof=1)
    v10 = np.mean([x[10] for x in summaries])
    v20 = np.mean([x[20] for x in summaries])
    assert math.isclose(bound["U_seed"], 15 * S2 / CONST["chi2_005_df15"], rel_tol=1e-12)
    assert math.isclose(bound["U_bm10"], v10 * 144 / CONST["chi2_005_df144"], rel_tol=1e-12)
    assert math.isclose(bound["U_bm20"], v20 * 304 / CONST["chi2_005_df304"], rel_tol=1e-12)
    assert bound["U"] == max(bound["U_seed"], bound["U_bm10"], bound["U_bm20"])
    assert bound["stable"]                                                 # i.i.d. increments: all three agree
    assert not any("mean" in key for key in bound)
    unstable = [{**x, 10: 5 * x[10], 20: 5 * x[20]} for x in summaries]
    assert not sa.pilot_bound(unstable, CONST)["stable"]
    with pytest.raises(ValueError):
        sa.pilot_bound(summaries[:15], CONST)
    with pytest.raises(ValueError):
        sa.seed_summary(np.zeros(2005))


def test_shot_rule_floors_at_the_pilot_length_and_rounds_up_to_thousands():
    t15, kappa, delta = CONST["t_0975_df15"], 0.25, 0.05
    assert sa.per_seed_length(1e-12, 125000, 1e-3, t15, kappa, delta) == 125000
    K1 = 1e-3
    U = 1234567.0 * 16 * (kappa * delta * K1) ** 2 / (t15 * t15 * 125000)
    assert sa.per_seed_length(U, 125000, K1, t15, kappa, delta) == 1235000


def test_verdicts_edges_disjointness_and_nonpositive_intervals():
    d = 0.05
    assert sa.verdict(0.95, 1.0, 1.0, d) == "VALIDATED"                   # edge included
    assert sa.verdict(1.05, 1.0, 1.0, d) == "VALIDATED"
    assert sa.verdict(0.9499, 1.0, 1.0, d) == "FAILED"
    assert sa.verdict(1.2, 0.9, 1.1, d) == "FAILED"                       # Q = [1.09, 1.33]
    assert sa.verdict(1.0, 0.9, 1.1, d) == "UNRESOLVED"                   # Q = [0.91, 1.11] straddles
    assert sa.verdict(1.0, 0.0, 1.1, d) == "UNRESOLVED"
    assert sa.verdict(1.0, -0.1, 1.1, d) == "UNRESOLVED"
    means = [1.0] * 8 + [1.2] * 8
    iv = sa.mean_interval(means, CONST["t_0975_df15"])
    half = CONST["t_0975_df15"] * np.std(means, ddof=1) / 4
    assert math.isclose(iv["R_lo"], 1.1 - half) and math.isclose(iv["R_hi"], 1.1 + half)
    with pytest.raises(ValueError):
        sa.mean_interval(means[:15], CONST["t_0975_df15"])


def test_forced_incompatible_comparators_never_validate_together():
    ev = DOC["design_evidence"]["points"]["E4"]
    K1, K3 = ev["comparators"]["K1"], ev["comparators"]["K3"]
    assert ev["forced_incompatible_pairs"]["K3/K1"]
    for lo, hi in itertools.product(np.linspace(0.3, 1.5, 61) * K1, repeat=2):
        if lo <= hi:
            assert not (sa.verdict(K1, lo, hi, 0.05) == "VALIDATED" == sa.verdict(K3, lo, hi, 0.05))


# ------------------------------------------------------------------------------------------- deadlines and purity
def test_deadline_stops_the_filter_and_the_simulator():
    model = sa.arma_model(*SYN, 15, 5)
    y = np.zeros(5000, dtype=np.int8)
    with pytest.raises(sa.DeadlineReached):
        sa.arma_filter(y, model, deadline=sa.Deadline(2.5, StepClock(1.0)), chunk=100)
    with pytest.raises(sa.DeadlineReached):
        sa.simulate_window_record(*SYN, 5000, np.random.default_rng(0), deadline=sa.Deadline(0.5, StepClock(1.0)))
    with pytest.raises(sa.DeadlineReached):
        sa.ar1_filter(y, sa.ar1_model(0.4, 0.5, 0.9, 15, 5), deadline=sa.Deadline(0.5, StepClock(1.0)))
    assert sa.Deadline(10.0, StepClock(1.0)).remaining() == 9.0        # end = 1 + 10, read at 2
    sa.arma_filter(y[:50], model, deadline=sa.Deadline(1e9))


def test_library_does_no_file_io_and_configures_no_threads():
    source = (ROOT / "analysis" / "lib" / "sid_arma.py").read_text()
    tree = ast.parse(source)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "open" not in calls
    imports = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert imports <= {"math", "time", "nullcontext", "numpy", "lfilter", "sid_lib"}
    assert "environ" not in source
