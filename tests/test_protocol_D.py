"""Contract tests for analysis/protocol_D.json and tools/build_protocol_D.py (roadmap D1).

The specification is prepared for review, not frozen. These tests check that the committed draft is
exactly what its builder produces, that the freezing machinery refuses what it should, and that the
inputs the review required to be bound really are bound: the frozen offsets are recomputed and must
still be maximisers, the stored J(0) and quantiles are recomputed, and the classification rule is
exercised through its reference implementation rather than read as prose.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
import build_protocol_D as bd  # noqa: E402
import sid_servo_rate as sr  # noqa: E402

PATH = ROOT / "analysis" / "protocol_D.json"
DOC = json.loads(PATH.read_text())
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
           "NUMEXPR_NUM_THREADS")


def _offset_grid(n=13):
    return [(float(a), float(b)) for a in np.linspace(0, math.pi, n) for b in np.linspace(0, math.pi, n)]


# ------------------------------------------------------------------ the draft and its machinery
def test_the_committed_draft_is_what_the_builder_produces():
    assert bd.matches_builder(DOC)
    assert bd.is_draft(DOC) and DOC["digest"] is None and not bd.is_verified_frozen(DOC)
    assert DOC["note"] == "notes/2026-09-16-note-29-D-plan-draft.md"


def test_the_builder_writes_drafts_and_refuses_frozen_files(tmp_path):
    target = tmp_path / "protocol_D.json"
    bd.write_draft(bd.build(), target)
    assert bd.is_draft(json.loads(target.read_text()))
    digest = bd.freeze_protocol(target, "2026-09-18")
    frozen = json.loads(target.read_text())
    assert bd.is_verified_frozen(frozen) and frozen["digest"] == digest and bd.matches_builder(frozen)
    before = target.read_bytes()
    with pytest.raises(bd.ProtocolFrozenError):
        bd.write_draft(bd.build(), target)
    with pytest.raises(bd.ProtocolFrozenError):
        bd.freeze_protocol(target, "2026-09-19")
    assert target.read_bytes() == before


def test_a_tampered_frozen_document_does_not_verify(tmp_path):
    target = tmp_path / "protocol_D.json"
    bd.write_draft(bd.build(), target)
    bd.freeze_protocol(target, "2026-09-18")
    doc = json.loads(target.read_text())
    doc["classification"]["tolerance"] = 0.05
    assert not bd.is_verified_frozen(doc) and not bd.matches_builder(doc)


# ------------------------------------------------------------------ frozen inputs, recomputed
def test_the_design_points_declare_their_order_and_disjoint_seeds():
    points = DOC["design_points"]
    assert [p["role"] for p in points.values()] == ["primary", "sensitivity"]
    assert points["K5"]["kappa"] == 5.0 and points["K5"]["seed_block"] == 0
    assert points["K10"]["kappa"] == 10.0 and points["K10"]["seed_block"] == 1
    for point in points.values():
        assert point["rho"] == pytest.approx(math.exp(-0.2), rel=1e-12) and point["control_rho"] == 0.0
    seeds = [s for p in points.values() for block in p["seeds"].values() for s in block]
    assert len(seeds) == len(set(seeds))
    assert len(points["K5"]["seeds"]["pilot"]) == DOC["records"]["pilot"]["replicates"]
    assert len(points["K5"]["seeds"]["evaluation"]) == DOC["records"]["evaluation"]["replicates"]
    assert len(points["K5"]["seeds"]["checks"]) == DOC["records"]["checks"]["replicates"]


def test_the_marginal_is_matched_to_the_von_mises_moment():
    from scipy.special import i0e, i1e
    for point in DOC["design_points"].values():
        kappa, sigma = point["kappa"], point["sigma"]
        assert math.exp(-sigma ** 2 / 2) == pytest.approx(float(i1e(kappa) / i0e(kappa)), rel=1e-12)


@pytest.mark.parametrize("name", ["K5", "K10"])
def test_the_frozen_offsets_are_still_maximisers_and_the_variance_optimum_is_degenerate(name):
    """Freezing an index must not fossilise a wrong choice: recompute and check it is a maximiser,
    and confirm the fourfold degeneracy that made a run-time argmax unsafe."""
    point = DOC["design_points"][name]
    grid = DOC["grids"]["base"]
    chain = sr.latent_chain(point["sigma"], 0.0, grid["M"], grid["L"])
    x, pi = chain["x"], chain["pi"]
    full = _offset_grid()
    slope = np.array([sr.iid_fisher(*sr.emissions(x, a, b), pi) for a, b in full])
    i_slope = point["offsets"]["slope"]["index"]
    assert slope[i_slope] >= slope.max() * (1 - bd.TIE_RELATIVE)
    assert list(full[i_slope]) == pytest.approx(point["offsets"]["slope"]["values"], rel=1e-15)
    assert point["J0_reference"] == pytest.approx(slope[i_slope], rel=1e-9)

    thinned = full[::bd.VARIANCE_STRIDE]
    kl = np.array([sr.iid_kl(sr.modulated_emissions(x, a, b), sr.emissions(x, a, b)[0], pi) for a, b in thinned])
    i_var = point["offsets"]["variance"]["index"]
    assert kl[i_var] >= kl.max() * (1 - bd.TIE_RELATIVE)
    assert list(thinned[i_var]) == pytest.approx(point["offsets"]["variance"]["values"], rel=1e-15)
    assert point["kl0_reference"] == pytest.approx(kl[i_var], rel=1e-9)
    near = int(np.sum(kl >= kl.max() * (1 - bd.TIE_RELATIVE)))
    assert near == 4, "the variance optimum is fourfold degenerate; a run-time argmax picks by roundoff"
    assert "degenerate" in DOC["model"]["offsets"] and f"{bd.TIE_RELATIVE:g}" in DOC["model"]["tie_rule"]


@pytest.mark.parametrize("name", ["K5", "K10"])
def test_the_recorded_signal_law_difference_is_the_measured_one(name):
    point = DOC["design_points"][name]
    grid = DOC["grids"]["base"]
    chain = sr.latent_chain(point["sigma"], 0.0, grid["M"], grid["L"])
    x, pi = chain["x"], chain["pi"]
    a, b = point["offsets"]["variance"]["values"]
    plain = sr.emissions(x, a, b)[0]
    analytic = sr.iid_kl(sr.modulated_emissions(x, a, b), plain, pi)
    truncated = sr.iid_kl(sr.modulated_emissions_grid(x, a, b), plain, pi)
    assert point["signal_law_relative_difference"] == pytest.approx(abs(truncated / analytic - 1), rel=2e-2)
    assert "exact marginal" in DOC["model"]["signal"] and "exp(-0.045)" in DOC["model"]["signal"]
    assert DOC["numerical_checks"]["ND8_signal_law"]["reported_not_gating"] is True


def test_the_constants_are_this_stack_s_quantiles():
    from scipy.stats import chi2, t
    c = DOC["constants"]
    assert c["t_0975_df15"] == pytest.approx(float(t.ppf(0.975, 15)), rel=1e-9)
    assert c["t_0975_df7"] == pytest.approx(float(t.ppf(0.975, 7)), rel=1e-9)
    assert c["chi2_005_df7"] == pytest.approx(float(chi2.ppf(0.05, 7)), rel=1e-9)
    assert c["chi2_005_df15"] == pytest.approx(float(chi2.ppf(0.05, 15)), rel=1e-9)
    assert "never recomputed" in bd.__doc__ or "scipy" in c["source"]


# ------------------------------------------------------------------ the checks and the allowance
def test_the_two_nesting_checks_are_distinguished():
    checks = DOC["numerical_checks"]
    fisher, kl = checks["ND1a_fisher_nesting"], checks["ND1b_kl_nesting"]
    assert "exact by construction" in fisher["sampling"] and fisher["tolerance_relative"] == 1e-10
    assert kl["mean_tolerance_standard_errors"] >= 1 and kl["increment_tolerance_absolute"] == 1e-12
    assert "does not nest exactly" in kl["sampling"]
    assert "frozen before the checks run" in checks["failure"]


def test_the_grid_and_burn_in_checks_are_fully_specified():
    checks = DOC["numerical_checks"]
    grid = checks["ND2_grid"]
    assert grid["base"] == DOC["grids"]["base"] and grid["refinements"] == DOC["grids"]["refinements"]
    assert grid["channels"] == ["fisher", "kl"], "the KL channel's interval reports numerical accuracy too"
    assert grid["records"] == DOC["records"]["checks"] and grid["enters_allowance"] is True
    burn_in = checks["ND7_burn_in"]
    assert "SAME final estimation window" in burn_in["requirement"]
    assert "both KL filters" in burn_in["requirement"] and burn_in["enters_allowance"] is True
    assert "2W + retained" in burn_in["window"]
    assert "rho > 0" in checks["ND3_brute_force"]["requirement"]
    assert "i.i.d. marginalisation is rejected" in checks["ND3_brute_force"]["requirement"]


def test_the_allowance_is_adopted_propagated_and_kept_off_the_sizing_approximation():
    allowance = DOC["allowance"]
    assert len(allowance["inputs"]) == 3 and any("J(0)" in item for item in allowance["inputs"])
    assert "not certified error bounds" in allowance["nature"]
    assert "absolute rate units" in allowance["units"]
    assert "not added in quadrature" in allowance["combination"] and "separate" in allowance["combination"]
    assert "sqrt((J_lo - e_rho)/(J0 + e_0))" in allowance["application"]
    assert "first order" in allowance["application"]
    assert "never in classification" in allowance["sizing_only"]
    assert "UNRESOLVED" in allowance["nonpositive"]
    assert "UNRESOLVED_NUMERICAL" in allowance["exhaustion"] and "0.005" in allowance["exhaustion"]
    entering = [k for k, v in DOC["numerical_checks"].items() if isinstance(v, dict) and v.get("enters_allowance")]
    assert sorted(entering) == ["ND2_grid", "ND7_burn_in"]


def test_the_score_and_simulator_checks_bind_their_acceptance_choices():
    nd4 = DOC["numerical_checks"]["ND4_score"]
    assert nd4["finite_difference_step"] == 1e-5
    assert nd4["fixture"]["grid"] == {"M": 61, "L": 5.0} and nd4["fixture"]["seed"] == 7
    assert nd4["fixture"]["observations"] == 200 and nd4["fixture"]["offsets"] == [0.4, 0.9]
    assert "1e-12" in nd4["near_zero"] and nd4["rejection_relative"] == 1e-3
    nd5 = DOC["numerical_checks"]["ND5_simulator"]
    assert len(nd5["statistics"]) == 3
    assert "N_eff = N (1 - rho^2)/(1 + rho^2)" in nd5["effective_sample_size"]
    assert set(nd5["standard_errors"]) == {"variance", "lag_one", "circular_moment"}
    assert "N_eff" in nd5["standard_errors"]["variance"]
    assert "every check record" in nd5["aggregation"] and "sqrt(replicates)" in nd5["aggregation"]


def test_the_runtime_stop_and_what_the_prediction_charges_are_frozen():
    execution = DOC["execution"]
    stop = execution["runtime_stop"]
    assert "minimum of the applicable ceiling" in stop and "remaining aggregate" in stop
    assert "setup, simulation and filtering" in stop
    assert "INCOMPLETE" in stop and "never completed by shortening records" in stop
    prediction = execution["cost_prediction"]
    assert "warm-ups included" in prediction and "x 4" in prediction
    assert "one filter per hypothesis" in prediction and str(bd.PREDICTION_MARGIN) in prediction
    assert bd.PROPAGATIONS_PER_SHOT == 4


def test_the_classification_rule_runs_through_its_reference_implementation():
    """The protocol's own tolerance and allowance must be able to turn a decision into UNRESOLVED."""
    tolerance = DOC["classification"]["tolerance"]
    assert tolerance == 0.02 and DOC["classification"]["kappa_D"] == 0.25
    assert "UNRESOLVED_NUMERICAL" in DOC["classification"]["states"]
    assert any("touches it" in clause for clause in DOC["classification"]["rule"])
    assert DOC["uncertainty"]["reference_implementation"] == "analysis/lib/sid_servo_rate.py verdict()"
    t15 = DOC["constants"]["t_0975_df15"]
    values = [0.9801] * DOC["records"]["evaluation"]["replicates"]
    decided = sr.verdict(values, 1.0, t15, tolerance)
    widened = sr.verdict(values, 1.0, t15, tolerance, numerator_relative=[0.041])
    assert decided["classification"] == "BELOW"
    assert widened["classification"] == "UNRESOLVED" and widened["classification_before_allowance"] == "BELOW"
    # the review's counterexample: the first-order form would decide it, the exact one does not
    counterexample = sr.verdict([1.02096 ** 2] * 16, 1.0, t15, tolerance, denominator_relative=[0.0019])
    assert counterexample["classification"] == "UNRESOLVED"
    assert counterexample["classification_before_allowance"] == "ABOVE"
    assert sr.sizing_allowance_in_ratio_units([0.0019]) < DOC["classification"]["kappa_D"] * tolerance


# ------------------------------------------------------------------ sizing, execution, budget
def test_the_sizing_rule_is_an_algorithm_not_a_target():
    rule = DOC["sizing_rule"]
    for key in ("pilot_statistic", "conservative_bound", "extrapolation", "reference", "half_width",
                "requirement", "solve", "rounding", "replicates", "refusals", "predicted_versus_guaranteed"):
        assert key in rule, key
    assert "chi2_005_df7" in rule["conservative_bound"] and "1/N" in rule["extrapolation"]
    assert "J(0)" in rule["reference"] and "no measured interval centre" in rule["reference"]
    assert "multiple of 10000" in rule["rounding"]
    assert "fixed at 16" in rule["replicates"]
    assert any("UNRESOLVED_NUMERICAL" in r for r in rule["refusals"])
    assert any("NOT_ATTEMPTED" in r for r in rule["refusals"])
    assert any("no top-ups" in r for r in rule["refusals"])
    assert "realised interval decides" in rule["predicted_versus_guaranteed"]
    assert "no mean" in rule["pilot_statistic"]


def test_the_execution_rules_are_bound_by_the_protocol():
    execution = DOC["execution"]
    assert "sid-f" in execution["stack"] and "conda-osx-arm64.lock" in execution["stack"]
    assert execution["pins"] == {"python": "3.12.14", "numpy": "2.4.4", "scipy": "1.17.1"}
    assert set(execution["threads"]) == set(THREADS) and set(execution["threads"].values()) == {"1"}
    for key in ("deadline_accounting", "admission", "interruption", "provenance", "refusal"):
        assert key in execution and len(execution[key]) > 40
    assert "counts once" in execution["deadline_accounting"]
    assert "NO_VERDICT" in execution["interruption"] and "shortened" in execution["interruption"]
    assert "digest" in execution["refusal"] and "dirty tree" in execution["refusal"]


def test_the_accepted_planning_numbers_are_the_ones_stored():
    assert DOC["records"]["evaluation"] == {"retained": 200000, "warm_up": 2000, "replicates": 16}
    assert DOC["records"]["pilot"] == {"retained": 50000, "warm_up": 2000, "replicates": 8}
    assert DOC["grids"]["base"] == {"M": 241, "L": 6.0}
    budget = DOC["budget"]
    assert budget["check_ceiling_seconds"] == 1800 and budget["pilot_ceiling_seconds"] == 900
    assert budget["point_ceiling_seconds"] == 3600 and budget["aggregate_ceiling_seconds"] == 14400
    assert budget["threads"] == 1 and "2.097152e11" in budget["cost_note"]
    assert "neither" in budget["ceilings_are_not_authorisation"]
    assert set(DOC["outputs"]) == {"checks", "pilot", "evaluation"}
    assert all(v.startswith("analysis/reproduction/res15_D_") for v in DOC["outputs"].values())


def test_the_rng_and_stream_allocation_are_specified():
    rng = DOC["rng"]
    assert "PCG64" in rng["generator"] and "seed_block" in rng["streams"]
    assert str(bd.BLOCK) in rng["draw_order"] and "uniform" in rng["draw_order"]
    assert "does not depend on the hypothesis" in rng["hypothesis_independence"]
    assert "never relies on a prefix" in rng["prefixes"]


def test_the_model_records_why_the_state_is_unwrapped():
    model = DOC["model"]
    assert "unwrapped" in model["latent_state"] and "2 pi rho" in model["latent_state"]
    assert "left eigenvector" in model["initialisation"]
    assert "common random numbers" in model["records"]
