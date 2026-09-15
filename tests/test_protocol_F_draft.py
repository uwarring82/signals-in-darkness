"""The draft roadmap-F protocol (note 28): reproducible, non-authorising, internally consistent.

These tests check the protocol document and its builder only. No ARMA filter exists yet, and
nothing here simulates a record or evaluates a likelihood.
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
    assert builder.is_draft(DRAFT)
    assert DRAFT["draft_revision"] == 2
    assert "refuse" in DRAFT["status"] and "DRAFT" in DRAFT["execution_stack"]["refusal"]


# --------------------------------------------------------------------------- write path
def _frozen(doc, **changes):
    frozen = json.loads(json.dumps(doc))
    frozen.update(changes)
    return frozen


@pytest.mark.parametrize("changes", [
    {"status": "FROZEN 2026-09-16", "digest": "0123456789abcdef"},
    {"status": "FROZEN 2026-09-16", "digest": None},
    {"digest": "0123456789abcdef"},          # a digest alone makes it frozen
])
def test_builder_refuses_to_overwrite_a_frozen_protocol(tmp_path, changes):
    target = tmp_path / "protocol_F.json"
    target.write_text(json.dumps(_frozen(DRAFT, **changes), indent=2) + "\n")
    before = target.read_bytes()
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(DRAFT, target)
    assert target.read_bytes() == before


def test_builder_refuses_an_unreadable_destination(tmp_path):
    target = tmp_path / "protocol_F.json"
    target.write_text("{not json")
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(DRAFT, target)
    assert target.read_text() == "{not json"


def test_builder_writes_new_drafts_and_replaces_only_drafts(tmp_path):
    fresh = tmp_path / "new" / "protocol_F.json"
    fresh.parent.mkdir()
    builder.write_draft(DRAFT, fresh)
    assert json.loads(fresh.read_text()) == DRAFT
    older = _frozen(DRAFT, draft_revision=1)
    fresh.write_text(json.dumps(older))
    builder.write_draft(DRAFT, fresh)
    assert json.loads(fresh.read_text())["draft_revision"] == 2
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(_frozen(DRAFT, digest="0123456789abcdef"), tmp_path / "other.json")


# --------------------------------------------------------------------------- numerical checks
@pytest.mark.parametrize("W", [1000, 2287, 3460])
def test_nc5_and_nc6_filter_the_same_final_observations(W):
    rec = DRAFT["numerical_checks"]["records_for_NC5_NC6"]
    at = lambda o: o["W_multiple"] * W + o["plus"]  # noqa: E731
    first, last, length = at(rec["estimation_window"]["first"]), at(rec["estimation_window"]["last"]), at(rec["length"])
    assert last == length and last - first + 1 == 50_000
    history = {name: first - at(p["first_observation"]) for name, p in rec["passes"].items()}
    for a, b in DRAFT["numerical_checks"]["NC5_grid"]["compare"].items():
        assert history[a] == history[b] == W                      # grids differ, history does not
        assert rec["passes"][a]["grid"] != rec["passes"][b]["grid"]
    (a, b), = DRAFT["numerical_checks"]["NC6_finite_history"]["compare"].items()
    assert rec["passes"][a]["grid"] == rec["passes"][b]["grid"] == "M241_L7"
    assert (history[a], history[b]) == (W, 2 * W)                 # only the history differs


def test_revision_1_nc6_windows_would_fail_the_same_observation_requirement():
    # r1 compared n = W+1..W+N with n = 2W+1..2W+N from one pass: W observations differ.
    W, N = 1000, 50_000
    r1_a, r1_b = set(range(W + 1, W + N + 1)), set(range(2 * W + 1, 2 * W + N + 1))
    assert len(r1_a ^ r1_b) == 2 * W


# --------------------------------------------------------------------------- stopping
@pytest.mark.parametrize("predicted,remaining,expected", [
    (7200, 28800, 7200),        # r1 would have allowed 9000 s
    (1000, 28800, 1250),
    (5000, 3000, 3000),         # the aggregate budget binds
    (7000, 7100, 7100),
])
def test_stop_time_never_exceeds_any_hard_cap(predicted, remaining, expected):
    assert builder.stop_seconds(predicted, remaining) == expected
    assert builder.stop_seconds(predicted, remaining) <= min(DRAFT["budget"]["point_cap_seconds"], remaining)


def test_budget_caps_and_gate3_deadline_are_explicit():
    b = DRAFT["budget"]
    assert (b["point_cap_seconds"], b["aggregate_cap_seconds"], b["gate3_deadline_seconds"]) == (7200, 28800, 1800)
    assert (b["prediction_margin"], b["stop_margin"]) == (1.10, 1.25)
    assert "first point's measurement" in b["gate3_deadline"]
    assert DRAFT["evaluation"]["hard_stop"] == "budget.stop_rule"


# --------------------------------------------------------------------------- stack
def test_solve_and_installation_share_one_definition_and_channel_policy():
    cmds = DRAFT["execution_stack"]["commands"]
    strip = lambda args, extra: [a for a in args if a not in extra]  # noqa: E731
    assert strip(cmds["solve"], builder.SOLVE_ONLY_FLAGS) == strip(cmds["install"], builder.INSTALL_ONLY_FLAGS)
    for args in (cmds["solve"], cmds["install"]):
        assert args[args.index("--override-channels") + 1:args.index("--override-channels") + 3] == ["-c", "conda-forge"]
        assert args[args.index("--file") + 1] == builder.STACK_SPEC
    assert cmds["environment"] == {"CONDA_SUBDIR": "osx-arm64"}
    specs = [l.strip() for l in (ROOT / builder.STACK_SPEC).read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    assert "libblas=*=*openblas" in specs
    assert {"python=3.12", "numpy=2.4.4", "scipy=1.17.1"} <= set(specs)
    pip = [l.strip() for l in (ROOT / builder.PIP_SPEC).read_text().splitlines() if l.strip() and not l.startswith("#")]
    assert pip == ["cffconvert==2.0.0"]
    assert "--require-hashes" in cmds["pip_install"] and "--no-deps" in cmds["pip_install"]


# --------------------------------------------------------------------------- inputs and arithmetic
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
    assert DRAFT["points"]["E2"]["C"] != 0.300          # not the rejected draft's rounded input


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
            assert flag == (K[i] / K[j] < lo or K[i] / K[j] > hi), (name, pair)
    assert lo < 1.0563 < hi                              # note 27's E6 counterexample
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
    assert (c["t_0975_df15"] / c["z_0975"]) ** 2 == pytest.approx(1.1827, abs=5e-4)
    assert "never recomputed" in DRAFT["shot_rule"]["constants_source"]
    assert DRAFT["pilot"]["variance_bound"].startswith("approximate")


def test_deterministic_numerical_design_checks_pass_at_every_point():
    for name, e in EVIDENCE.items():
        assert abs(e["series_convergence_rel"]["K1"]) <= 1e-6, name
        assert abs(e["series_convergence_rel"]["K4"]) <= 1e-6, name
        for grid, d in e["grids"].items():
            assert d["stationary_residual_within_1e-12"] and d["stationary_min_at_least_-1e-15"], (name, grid)


# --------------------------------------------------------------------------- closure
def test_mandatory_conditional_and_closure_rules_are_explicit():
    points = DRAFT["points"]
    assert points["mandatory"] == ["E3", "E4", "E5"]
    assert points["conditional_pair"] == ["E1", "E2"]
    assert "E6" in points["deferred"]
    closure = DRAFT["closure"]["roadmap_F"]
    assert "K1" in closure and "E3, E4 and E5" in closure and "OPEN" in closure
    assert "R_lo <= 0" in " ".join(DRAFT["verdicts"]["rule"])


def test_closure_wordings_match_their_outcomes():
    c = DRAFT["closure"]
    assert c["wording_while_open"].endswith("F remains open.")
    for key in ("wording_if_failed", "wording_if_validated"):
        assert "remains open" not in c[key].split("finite-window comparator.")[1]
    assert "closed FAILED" in c["wording_if_failed"] and "{failed_tuples}" in c["wording_if_failed"]
    assert "closed VALIDATED" in c["wording_if_validated"] and "{validated_tuples}" in c["wording_if_validated"]
