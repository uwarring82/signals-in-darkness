"""The frozen roadmap-F protocol (note 28): verifiable, not overwritable, internally consistent.

The committed artifact is checked as a frozen protocol: its digest must verify and its content must
match the builder. Draft and refusal behaviour is tested on a separate draft fixture and on
temporary copies. No ARMA filter exists yet, and nothing here simulates a record or evaluates a
likelihood.
"""
import itertools
import json
import math
from pathlib import Path
import sys

import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_protocol_F as builder  # noqa: E402

PROTOCOL_PATH = ROOT / "analysis" / "protocol_F.json"
PROTOCOL = json.loads(PROTOCOL_PATH.read_text())
EVIDENCE = PROTOCOL["design_evidence"]["points"]


@pytest.fixture(scope="module")
def rebuilt():
    return builder.build()


@pytest.fixture(scope="module")
def draft(rebuilt):
    """The committed content returned to draft form: the builder's draft status and a null digest."""
    doc = builder.unfrozen_view(PROTOCOL)
    doc["status"] = rebuilt["status"]
    doc["digest"] = None
    return doc


def _changed(doc, **changes):
    out = json.loads(json.dumps(doc))
    out.update(changes)
    return out


# --------------------------------------------------------------------------- the committed, frozen artifact
def test_committed_protocol_is_frozen_and_verifies_its_digest():
    assert builder.is_verified_frozen(PROTOCOL) and not builder.is_draft(PROTOCOL)
    assert PROTOCOL["status"] == builder.FREEZE_STATUS and PROTOCOL["frozen"] == builder.FROZEN_WHEN
    assert PROTOCOL["digest"] == builder.digest_of(PROTOCOL) and len(PROTOCOL["digest"]) == 16
    assert PROTOCOL["draft_revision"] == 4
    assert "BEFORE any ARMA likelihood evaluation" in PROTOCOL["frozen"]


def test_committed_protocol_matches_its_builder(rebuilt):
    assert builder.matches_builder(PROTOCOL, rebuilt)


def test_verification_fails_for_tampered_content_even_with_a_recomputed_digest(rebuilt):
    tampered = _changed(PROTOCOL)
    tampered["verdicts"]["delta"] = 0.10
    assert not builder.is_verified_frozen(tampered) and not builder.matches_builder(tampered, rebuilt)
    redigested = _changed(tampered, digest=builder.digest_of(tampered))
    assert builder.is_verified_frozen(redigested)               # the digest alone is satisfied ...
    assert not builder.matches_builder(redigested, rebuilt)     # ... but the content no longer matches
    nudged = _changed(PROTOCOL)
    nudged["design_evidence"]["points"]["E4"]["comparators"]["K1"] *= 1 + 1e-6
    assert not builder.equivalent(builder.unfrozen_view(PROTOCOL), builder.unfrozen_view(nudged))


def test_refreezing_the_committed_content_reproduces_the_committed_protocol(tmp_path, draft):
    target = tmp_path / "protocol_F.json"
    target.write_text(json.dumps(draft, indent=2) + "\n")
    assert builder.freeze_protocol(target) == PROTOCOL["digest"]
    assert json.loads(target.read_text()) == PROTOCOL


def test_the_committed_protocol_cannot_be_overwritten_or_refrozen(tmp_path, draft):
    target = tmp_path / "protocol_F.json"
    target.write_bytes(PROTOCOL_PATH.read_bytes())
    before = target.read_bytes()
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(draft, target)
    with pytest.raises(builder.ProtocolFrozenError):
        builder.freeze_protocol(target)
    assert target.read_bytes() == before


# --------------------------------------------------------------------------- draft fixture and write path
def test_the_draft_fixture_cannot_authorise_any_measurement(draft):
    assert builder.is_draft(draft)
    assert "refuse" in draft["status"] and "DRAFT" in draft["execution_stack"]["refusal"]


@pytest.mark.parametrize("changes", [
    {"status": "FROZEN 2026-09-16", "digest": "0123456789abcdef"},
    {"status": "FROZEN 2026-09-16", "digest": None},
    {"digest": "0123456789abcdef"},          # a digest alone makes it frozen
])
def test_builder_refuses_to_overwrite_a_frozen_protocol(tmp_path, draft, changes):
    target = tmp_path / "protocol_F.json"
    target.write_text(json.dumps(_changed(draft, **changes), indent=2) + "\n")
    before = target.read_bytes()
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(draft, target)
    assert target.read_bytes() == before


def test_builder_refuses_an_unreadable_destination(tmp_path, draft):
    target = tmp_path / "protocol_F.json"
    target.write_text("{not json")
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(draft, target)
    assert target.read_text() == "{not json"


def test_builder_writes_new_drafts_and_replaces_only_drafts(tmp_path, draft):
    fresh = tmp_path / "new" / "protocol_F.json"
    fresh.parent.mkdir()
    builder.write_draft(draft, fresh)
    assert json.loads(fresh.read_text()) == draft
    fresh.write_text(json.dumps(_changed(draft, draft_revision=1)))
    builder.write_draft(draft, fresh)
    assert json.loads(fresh.read_text())["draft_revision"] == draft["draft_revision"]
    with pytest.raises(builder.ProtocolFrozenError):
        builder.write_draft(_changed(draft, digest="0123456789abcdef"), tmp_path / "other.json")


def test_freezing_refuses_a_draft_that_differs_from_its_builder(tmp_path, draft):
    target = tmp_path / "protocol_F.json"
    edited = _changed(draft)
    edited["verdicts"]["delta"] = 0.10
    target.write_text(json.dumps(edited, indent=2) + "\n")
    before = target.read_bytes()
    with pytest.raises(builder.ProtocolFrozenError):
        builder.freeze_protocol(target)
    assert target.read_bytes() == before


@pytest.mark.parametrize("name", ["selections_ladder_C.json", "sensitivity_protocol_C.json", "acceptance_C.json"])
def test_digest_follows_the_freeze_ladder_selections_convention(name):
    # Verified against artifacts frozen with tools/freeze_ladder_selections.py's convention.
    # benchmark_ladder_C, eligibility_C and schedule_class_C do not recompute under it (note 28 §12).
    artifact = json.loads((ROOT / "analysis" / name).read_text())
    assert builder.digest_of(artifact) == artifact["digest"]


# --------------------------------------------------------------------------- numerical checks
@pytest.mark.parametrize("W", [1000, 2287, 3460])
def test_nc5_and_nc6_filter_the_same_final_observations(W):
    rec = PROTOCOL["numerical_checks"]["records_for_NC5_NC6"]
    at = lambda o: o["W_multiple"] * W + o["plus"]  # noqa: E731
    first, last, length = at(rec["estimation_window"]["first"]), at(rec["estimation_window"]["last"]), at(rec["length"])
    assert last == length and last - first + 1 == 50_000
    history = {name: first - at(p["first_observation"]) for name, p in rec["passes"].items()}
    for a, b in PROTOCOL["numerical_checks"]["NC5_grid"]["compare"].items():
        assert history[a] == history[b] == W                      # grids differ, history does not
        assert rec["passes"][a]["grid"] != rec["passes"][b]["grid"]
    (a, b), = PROTOCOL["numerical_checks"]["NC6_finite_history"]["compare"].items()
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
    assert builder.stop_seconds(predicted, remaining) <= min(PROTOCOL["budget"]["point_cap_seconds"], remaining)


def test_budget_caps_and_gate3_deadline_are_explicit():
    b = PROTOCOL["budget"]
    assert (b["point_cap_seconds"], b["aggregate_cap_seconds"], b["gate3_deadline_seconds"]) == (7200, 28800, 1800)
    assert (b["prediction_margin"], b["stop_margin"]) == (1.10, 1.25)
    assert "first point's measurement" in b["gate3_deadline"]
    assert PROTOCOL["evaluation"]["hard_stop"] == "budget.stop_rule"


# --------------------------------------------------------------------------- stack
def _specs(path):
    return [l.strip() for l in (ROOT / path).read_text().splitlines() if l.strip() and not l.startswith("#")]


def test_solve_and_installation_share_one_definition_and_channel_policy():
    cmds = PROTOCOL["execution_stack"]["commands"]
    strip = lambda args, extra: [a for a in args if a not in extra]  # noqa: E731
    assert strip(cmds["solve"], builder.SOLVE_ONLY_FLAGS) == strip(cmds["install"], builder.INSTALL_ONLY_FLAGS)
    for args in (cmds["solve"], cmds["install"]):
        i = args.index("--override-channels")
        assert args[i + 1:i + 3] == ["-c", "conda-forge"]
        assert args[args.index("--file") + 1] == builder.STACK_SPEC
    assert cmds["environment"] == {"CONDA_SUBDIR": "osx-arm64"}
    assert "libblas=*=*openblas" in _specs(builder.STACK_SPEC)
    assert _specs(builder.PIP_SPEC) == ["cffconvert==2.0.0"]
    assert "--require-hashes" in cmds["pip_install"] and "--no-deps" in cmds["pip_install"]


def test_the_exact_python_patch_is_carried_through_the_stack_rules():
    pins = PROTOCOL["execution_stack"]["pins"]
    assert pins == {"python": "3.12.14", "numpy": "2.4.4", "scipy": "1.17.1"}
    specs = _specs(builder.STACK_SPEC)
    assert f"python={pins['python']}" in specs and "python=3.12" not in specs
    assert {f"numpy={pins['numpy']}", f"scipy={pins['scipy']}"} <= set(specs)
    assert any(f"python is not {pins['python']}" in s for s in PROTOCOL["execution_stack"]["stop_conditions"])
    assert f"a python other than {pins['python']}" in PROTOCOL["execution_stack"]["refusal"]


def test_the_reviewed_solve_is_the_recorded_pinned_solve_and_passes_the_stop_conditions():
    solve_path = ROOT / PROTOCOL["execution_stack"]["reviewed_solve"]
    solve = json.loads(solve_path.read_text())
    meta = solve_path.with_suffix(".meta.txt").read_text().splitlines()
    assert solve["success"] is True and solve["dry_run"] is True
    assert meta[2] == "CONDA_SUBDIR=osx-arm64 " + " ".join(PROTOCOL["execution_stack"]["commands"]["solve"])
    assert meta[3].startswith("exit 0 ")
    link = {p["name"]: p for p in solve["actions"]["LINK"]}
    pins = PROTOCOL["execution_stack"]["pins"]
    assert {p["channel"] for p in link.values()} == {"conda-forge"}
    assert {p["platform"] for p in link.values()} <= {"osx-arm64", "noarch"}
    assert "openblas" in link["libblas"]["build_string"]
    assert (link["python"]["version"], link["numpy"]["version"], link["scipy"]["version"]) == \
        (pins["python"], pins["numpy"], pins["scipy"])


# --------------------------------------------------------------------------- inputs and arithmetic
def test_seed_blocks_follow_note_27_and_are_disjoint():
    seeds, flat = PROTOCOL["seeds"], []
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
        p = PROTOCOL["points"][name]
        ix = p["archive_indices"]
        assert grid["C0"][ix["C0_column"]] == p["C0"]
        assert grid["tau_c_over_t_dead"][ix["tau_c_row"]] == p["tau_c_over_t_dead"]
        assert [p["C0"], p["tau_c_over_t_dead"]] in archive["tau_optimised_threshold"]
        tau = taus[ix["tau_index"]]
        assert tau / grid["T2_over_t_dead"] == p["tau_over_T2"]
        assert p["C"] == pytest.approx(p["C0"] * math.exp(-tau / grid["T2_over_t_dead"]), rel=1e-14)
        assert p["u"] == pytest.approx(tau / p["tau_c_over_t_dead"], rel=1e-14)
        assert p["c_over_tau_c"] == pytest.approx((tau + 1) / p["tau_c_over_t_dead"], rel=1e-14)
    assert PROTOCOL["points"]["E2"]["C"] != 0.300          # not the rejected draft's rounded input


def test_ma_root_reproduces_the_filtered_lag_correlations():
    for name, e in EVIDENCE.items():
        F, phi, b = e["F"], e["phi"], e["b"]
        assert abs(b) < 1
        rho1 = (phi * (1 + b * b) + b * (1 + phi * phi)) / (1 + b * b + 2 * b * phi)
        for k in range(1, 6):
            assert rho1 * phi ** (k - 1) == pytest.approx(F * phi ** k, rel=1e-12), (name, k)


def test_forced_incompatibility_follows_the_band_arithmetic():
    lo, hi = PROTOCOL["constants"]["band_lower"], PROTOCOL["constants"]["band_upper"]
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
    c = PROTOCOL["constants"]
    assert c["t_0975_df15"] == pytest.approx(stats.t.ppf(0.975, 15), rel=1e-9)
    assert c["t_0975_df7"] == pytest.approx(stats.t.ppf(0.975, 7), rel=1e-9)
    assert c["chi2_005_df15"] == pytest.approx(stats.chi2.ppf(0.05, 15), rel=1e-9)
    assert c["chi2_005_df144"] == pytest.approx(stats.chi2.ppf(0.05, 144), rel=1e-9)
    assert c["chi2_005_df304"] == pytest.approx(stats.chi2.ppf(0.05, 304), rel=1e-9)
    assert (c["t_0975_df15"] / c["z_0975"]) ** 2 == pytest.approx(1.1827, abs=5e-4)
    assert "never recomputed" in PROTOCOL["shot_rule"]["constants_source"]
    assert PROTOCOL["pilot"]["variance_bound"].startswith("approximate")


def test_deterministic_numerical_design_checks_pass_at_every_point():
    for name, e in EVIDENCE.items():
        assert e["series_convergence_within_1e-6"] == {"K1": True, "K4": True}, name
        for grid, d in e["grids"].items():
            assert d["stationary_residual_within_1e-12"] and d["stationary_min_at_least_-1e-15"], (name, grid)
            assert d["tv_stationary_vs_gaussian_weights_below_1e-6"], (name, grid)


def _floats(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _floats(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _floats(v)
    elif isinstance(obj, float):
        yield obj


def test_design_evidence_records_no_roundoff_level_values():
    # Revision 4 found a total variation of 9.878e-13 on the drafting stack and 9.997e-13 on the
    # execution stack. Quantities at that level are floating-point noise; they are recorded as
    # bounds, never as values that a rebuild must reproduce.
    small = [x for x in _floats(PROTOCOL["design_evidence"]) if x != 0.0 and abs(x) < 1e-9]
    assert not small, small


# --------------------------------------------------------------------------- closure
def test_mandatory_conditional_and_closure_rules_are_explicit():
    points = PROTOCOL["points"]
    assert points["mandatory"] == ["E3", "E4", "E5"]
    assert points["conditional_pair"] == ["E1", "E2"]
    assert "E6" in points["deferred"]
    closure = PROTOCOL["closure"]["roadmap_F"]
    assert "K1" in closure and "E3, E4 and E5" in closure and "OPEN" in closure
    assert "R_lo <= 0" in " ".join(PROTOCOL["verdicts"]["rule"])


@pytest.mark.parametrize("verdicts,status", [
    (("VALIDATED", "VALIDATED", "VALIDATED"), "VALIDATED"),
    (("VALIDATED", "FAILED", "VALIDATED"), "FAILED"),
    (("FAILED", "FAILED", "FAILED"), "FAILED"),
    (("VALIDATED", "UNRESOLVED", "VALIDATED"), "OPEN"),
    (("FAILED", "UNRESOLVED", "FAILED"), "OPEN"),
    (("VALIDATED", "NO_VERDICT", "VALIDATED"), "OPEN"),
    (("NO_VERDICT", "NO_VERDICT", "NO_VERDICT"), "OPEN"),
])
def test_roadmap_F_status_follows_the_closure_rule(verdicts, status):
    assert builder.roadmap_F_status(dict(zip(builder.MANDATORY, verdicts))) == status
    boundary = {"E1": "VALIDATED", "E2": "FAILED"}           # boundary verdicts never change the status
    assert builder.roadmap_F_status({**dict(zip(builder.MANDATORY, verdicts)), **boundary}) == status


def test_status_requires_every_mandatory_verdict_and_known_inputs():
    with pytest.raises(ValueError):
        builder.roadmap_F_status({"E3": "VALIDATED", "E5": "VALIDATED"})
    with pytest.raises(ValueError):
        builder.roadmap_F_status({"E3": "VALIDATED", "E4": "PASSED", "E5": "VALIDATED"})
    with pytest.raises(ValueError):
        builder.roadmap_F_status({"E3": "VALIDATED", "E4": "VALIDATED", "E5": "VALIDATED", "E6": "VALIDATED"})
    with pytest.raises(ValueError):
        builder.roadmap_F_status({"E1": "MAYBE", "E3": "VALIDATED", "E4": "VALIDATED", "E5": "VALIDATED"})


def test_before_evaluation_the_wording_is_note_27_verbatim():
    note27 = " ".join((ROOT / "notes" / "2026-09-15-note-27-C08-fold-erratum-and-F-review.md").read_text().split())
    assert builder.closure_wording() == PROTOCOL["closure"]["wording"]["before_evaluation"]
    assert " ".join(builder.closure_wording().split()) in note27


GLOBAL_C04 = "remains confined to C04"
MANDATORY_SCOPE = "At the mandatory points E3–E5, the exact-r_k comparator (K1) is validated"


def _wording(*verdicts, boundary=None):
    return builder.closure_wording({**dict(zip(builder.MANDATORY, verdicts)), **(boundary or {})}, PROTOCOL["points"])


def test_after_evaluation_no_outcome_confines_all_validation_to_c04():
    for boundary in (None, {"E1": "VALIDATED", "E2": "VALIDATED"}, {"E1": "FAILED", "E2": "UNRESOLVED"}):
        for verdicts in itertools.product(builder.VERDICTS, repeat=3):
            text = _wording(*verdicts, boundary=boundary)
            assert GLOBAL_C04 not in text, (verdicts, boundary)
            assert builder.C04_AND_BOUNDARY in text


def test_boundary_passes_with_mandatory_failures_keep_the_boundary_out_of_the_mandatory_scope():
    text = _wording("FAILED", "FAILED", "FAILED", boundary={"E1": "VALIDATED", "E2": "VALIDATED"})
    assert builder.SCOPE_WITHOUT_MANDATORY_VALIDATION in text and MANDATORY_SCOPE not in text
    assert "C04 supplies the earlier point-sampled validation; results at the conditional boundary points " \
           "E1/E2 are reported separately." in text
    assert "Roadmap F closed FAILED." in text and "VALIDATED at none" in text
    for boundary_point in ("E1", "E2"):
        assert builder.tuple_label(PROTOCOL["points"][boundary_point]) not in text


def test_mixed_failed_closure_keeps_its_mandatory_validations():
    text = _wording("VALIDATED", "FAILED", "VALIDATED")
    e3, e4, e5 = (builder.tuple_label(PROTOCOL["points"][p]) for p in ("E3", "E4", "E5"))
    assert "Roadmap F closed FAILED." in text and MANDATORY_SCOPE in text
    scope = text.split(builder.C04_AND_BOUNDARY)[0]
    assert f"at E3 {e3} and E5 {e5}." in scope and e4 not in scope
    assert f"FAILED at E4 {e4}" in text


def test_mixed_open_campaign_keeps_its_mandatory_validations():
    text = _wording("VALIDATED", "UNRESOLVED", "VALIDATED")
    e4 = builder.tuple_label(PROTOCOL["points"]["E4"])
    assert "Roadmap F remains OPEN." in text and "closed" not in text and MANDATORY_SCOPE in text
    assert f"UNRESOLVED or without a verdict at E4 {e4}" in text and "FAILED at none" in text


def test_without_any_mandatory_validation_the_scope_sentence_says_so():
    for verdicts, status in ((("FAILED", "FAILED", "FAILED"), "closed FAILED"),
                             (("NO_VERDICT", "UNRESOLVED", "FAILED"), "remains OPEN")):
        text = _wording(*verdicts)
        assert builder.SCOPE_WITHOUT_MANDATORY_VALIDATION in text and MANDATORY_SCOPE not in text
        assert f"Roadmap F {status}." in text and "VALIDATED at none" in text


def test_validated_closure_reports_every_mandatory_tuple():
    text = _wording("VALIDATED", "VALIDATED", "VALIDATED")
    assert "Roadmap F closed VALIDATED." in text and MANDATORY_SCOPE in text
    for p in builder.MANDATORY:
        assert builder.tuple_label(PROTOCOL["points"][p]) in text


def test_protocol_records_the_wording_parts_the_builder_uses():
    w = PROTOCOL["closure"]["wording"]
    assert w["scope_with_mandatory_validation"] == builder.SCOPE_WITH_MANDATORY_VALIDATION
    assert w["scope_without_mandatory_validation"] == builder.SCOPE_WITHOUT_MANDATORY_VALIDATION
    assert w["c04_and_boundary"] == builder.C04_AND_BOUNDARY
    assert w["status"] == builder.STATUS_SENTENCE and w["tuple_report"] == builder.TUPLE_REPORT
    assert "E1/E2 verdicts never enter this caveat" in w["assembly"]
