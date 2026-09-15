"""The draft roadmap-F protocol (note 28): reproducible, non-authorising, internally consistent.

These tests check the protocol document only. No ARMA filter exists yet, and nothing here
simulates a record or evaluates a likelihood.
"""
import json
import math
from pathlib import Path
import sys

import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_protocol_F as builder  # noqa: E402

DRAFT = json.loads((ROOT / "analysis" / "protocol_F.json").read_text())
EVIDENCE = DRAFT["design_evidence"]["points"]


def test_committed_draft_is_reproduced_by_its_builder():
    assert builder.equivalent(DRAFT, builder.build()), "analysis/protocol_F.json differs from a rebuild"


def test_equivalence_helper_can_fail():
    changed = json.loads(json.dumps(DRAFT))
    changed["design_evidence"]["points"]["E4"]["comparators"]["K1"] *= 1 + 1e-6
    assert not builder.equivalent(DRAFT, changed)


def test_draft_cannot_authorise_any_measurement():
    assert DRAFT["status"].startswith("DRAFT")
    assert DRAFT["digest"] is None
    assert "refuse" in DRAFT["status"] and "DRAFT" in DRAFT["execution_stack"]["refusal"]


def test_seed_blocks_follow_note_27_and_are_disjoint():
    seeds, flat = DRAFT["seeds"], []
    for phase, base in (("pilot", 13000), ("evaluation", 14000), ("numerical_checks", 15000)):
        for p, name in enumerate(("E1", "E2", "E3", "E4", "E5")):
            assert seeds[phase][name] == [base + 20 * p + r for r in range(16)]
            flat += seeds[phase][name]
    flat += seeds["nesting_N0"]
    assert len(flat) == len(set(flat)) == 5 * 16 * 3 + 1


def test_boundary_points_are_the_archived_grid_values():
    archive = json.loads((ROOT / "analysis" / "outputs" / "res3_comparator.json").read_text())
    grid = archive["tau_optimised_grid"]
    taus = builder.run3_taus(grid["T2_over_t_dead"])
    for name in ("E1", "E2"):
        p = DRAFT["points"][name]
        ix = p["archive_indices"]
        assert grid["C0"][ix["C0_column"]] == p["C0"]
        assert grid["tau_c_over_t_dead"][ix["tau_c_row"]] == p["tau_c_over_t_dead"]
        assert [p["C0"], p["tau_c_over_t_dead"]] in archive["tau_optimised_threshold"]
        tau = taus[ix["tau_index"]]
        assert tau / grid["T2_over_t_dead"] == p["tau_over_T2"]
        assert p["C"] == pytest.approx(p["C0"] * math.exp(-tau / grid["T2_over_t_dead"]), rel=1e-14)
        assert p["u"] == pytest.approx(tau / p["tau_c_over_t_dead"], rel=1e-14)
        assert p["c_over_tau_c"] == pytest.approx((tau + 1) / p["tau_c_over_t_dead"], rel=1e-14)
    # the rounded inputs of the rejected draft are not what is frozen
    assert DRAFT["points"]["E2"]["C"] != 0.300


def test_ma_root_reproduces_the_filtered_lag_correlations():
    for name, e in EVIDENCE.items():
        F, phi, b = e["F"], e["phi"], e["b"]
        assert abs(b) < 1
        rho1 = (phi * (1 + b * b) + b * (1 + phi * phi)) / (1 + b * b + 2 * b * phi)
        for k in range(1, 6):
            assert rho1 * phi ** (k - 1) == pytest.approx(F * phi ** k, rel=1e-12), (name, k)


def test_forced_incompatibility_follows_the_band_arithmetic():
    lo, hi = DRAFT["constants"]["band_lower"], DRAFT["constants"]["band_upper"]
    for name, e in EVIDENCE.items():
        K = e["comparators"]
        for pair, flag in e["forced_incompatible_pairs"].items():
            i, j = pair.split("/")
            ratio = K[i] / K[j]
            assert flag == (ratio < lo or ratio > hi), (name, pair)
    # note 27's counterexample: a 5.6 % gap does not force either comparator to fail
    assert lo < 1.0563 < hi
    assert EVIDENCE["E4"]["forced_incompatible_pairs"]["K3/K1"] is True
    assert EVIDENCE["E5"]["forced_incompatible_pairs"]["K3/K1"] is True
    assert EVIDENCE["E3"]["forced_incompatible_pairs"]["K3/K1"] is False


def test_sizing_constants_match_their_definitions():
    # SciPy 1.10 and 1.17 differ by 2.5e-10 relative in t(0.975, 7). The tolerance is the
    # builder's cross-stack one; the driver reads these constants and never recomputes them.
    c = DRAFT["constants"]
    assert c["t_0975_df15"] == pytest.approx(stats.t.ppf(0.975, 15), rel=1e-9)
    assert c["t_0975_df7"] == pytest.approx(stats.t.ppf(0.975, 7), rel=1e-9)
    assert c["chi2_005_df15"] == pytest.approx(stats.chi2.ppf(0.05, 15), rel=1e-9)
    assert c["chi2_005_df144"] == pytest.approx(stats.chi2.ppf(0.05, 144), rel=1e-9)
    assert c["chi2_005_df304"] == pytest.approx(stats.chi2.ppf(0.05, 304), rel=1e-9)
    assert "never recomputed" in DRAFT["shot_rule"]["constants_source"]
    assert (c["t_0975_df15"] / c["z_0975"]) ** 2 == pytest.approx(1.1827, abs=5e-4)


def test_deterministic_numerical_design_checks_pass_at_every_point():
    for name, e in EVIDENCE.items():
        assert abs(e["series_convergence_rel"]["K1"]) <= 1e-6, name
        assert abs(e["series_convergence_rel"]["K4"]) <= 1e-6, name
        for grid, d in e["grids"].items():
            assert d["stationary_residual_within_1e-12"] and d["stationary_min_at_least_-1e-15"], (name, grid)


def test_mandatory_conditional_and_closure_rules_are_explicit():
    points = DRAFT["points"]
    assert points["mandatory"] == ["E3", "E4", "E5"]
    assert points["conditional_pair"] == ["E1", "E2"]
    assert "E6" in points["deferred"]
    closure = DRAFT["closure"]["roadmap_F"]
    assert "K1" in closure and "E3, E4 and E5" in closure and "OPEN" in closure
    assert "R_lo <= 0" in " ".join(DRAFT["verdicts"]["rule"])
    assert DRAFT["closure"]["wording_while_open_or_failed"] == builder.CORRECTED_C08_CAVEAT
