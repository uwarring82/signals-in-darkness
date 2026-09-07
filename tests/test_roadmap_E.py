"""Contract tests for roadmap E (analysis/runs/sid_run9.py, res9_identifiability_T2.json).

E's requirements were stated as six conditions. Each is asserted here against the published
artifact, so a later edit that quietly violates one fails rather than drifts.
"""
import json
import math
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "analysis", "lib"))
ART = json.load(open(os.path.join(ROOT, "analysis", "outputs", "res9_identifiability_T2.json"),
                    encoding="utf-8"))
ROWS = ART["rows"]


def test_E_does_not_import_sid_policies():
    """Requirement 1: E must be independent of roadmap G's operating-point refactor."""
    src = open(os.path.join(ROOT, "analysis", "runs", "sid_run9.py"), encoding="utf-8").read()
    body = src.split('"""', 2)[-1]          # the module docstring may discuss the independence
    assert "sid_policies" not in body, "E has acquired a dependency on the stack G will refactor"


def test_res7A_is_untouched_by_E():
    """Requirement 2: E writes a new artifact and leaves the historical one alone."""
    assert os.path.exists(os.path.join(ROOT, "analysis", "outputs", "res7A_identifiability.json"))
    assert "res7A_identifiability.json" in ART["supersedes"]
    src = open(os.path.join(ROOT, "analysis", "runs", "sid_run9.py"), encoding="utf-8").read()
    assert 'ARTIFACT = "res9_identifiability_T2.json"' in src
    # the only res7A access is a read for regression
    assert "load_reference" in src and "write_json" in src
    assert 'write_json(os.path.join' not in src, "E must write only through sid_repro.reproduction_path"


def test_every_axis_is_dimensionless_in_T2_and_no_dead_time_survives():
    """Requirement 3: units of T2 throughout, and td removed rather than documented."""
    for row in ROWS:
        assert "tau_c_over_T2" in row and "DeltaGamma_over_Gamma_hat" in row
        for banned in ("tau_c", "T2", "td", "t_dead"):
            assert banned not in row or banned == "tau_c_over_T2"
    src9 = open(os.path.join(ROOT, "analysis", "runs", "sid_run9.py"), encoding="utf-8").read()
    body9 = src9.split('"""', 2)[-1]
    assert "td" not in body9.replace("stdout", "").replace("stderr", ""), "td is back in E"
    src7 = open(os.path.join(ROOT, "analysis", "runs", "sid_run7.py"), encoding="utf-8").read()
    assert "T2, td = " not in src7, "sid_run7 still assigns the unused dead time"
    assert "PER SHOT" in ART["units"].upper()


def test_grid_and_regime_labels_are_in_the_output_itself():
    """Requirement 4: all three contrasts and all three eta_0, labelled in the artifact."""
    assert sorted({r["C_0"] for r in ROWS}) == [0.4, 0.5, 0.9]
    assert sorted({r["eta_0"] for r in ROWS}) == [0.02, 0.05, 0.10]
    assert sorted({r["tau_c_over_T2"] for r in ROWS}) == [0.05, 0.2, 1.0, 5.0]
    assert len(ROWS) == 36
    for row in ROWS:
        assert row["regime"] == ("principal" if row["C_0"] in (0.4, 0.5) else "servo-context")
    assert ART["regimes"]["principal"] == [0.4, 0.5]
    assert ART["regimes"]["servo-context"] == [0.9]
    assert "may" in ART["regimes"]["note"] and "NOT" in ART["regimes"]["note"]


def test_every_candidate_is_recorded_with_its_status():
    """Requirement 5, extended: three named starts plus the deterministic grid route."""
    for row in ROWS:
        opt = row["optimizer"]
        kinds = [s["kind"] for s in opt["starts"]]
        assert kinds.count("named") == 3
        assert "grid-polish" in kinds and "grid-raw" in kinds
        for st in opt["starts"]:
            for field in ("kind", "x0", "x", "fun", "success", "status", "nit", "message"):
                assert field in st, f"candidate is missing {field}"
            assert st["success"], f"a candidate did not converge at C_0={row['C_0']}"
        assert opt["selected_fun"] == min(s["fun"] for s in opt["starts"])
        assert row["I_B"] == pytest.approx(max(opt["selected_fun"], 0.0), rel=1e-15)


def test_spread_is_recorded_relatively_and_the_claim_matches_it():
    """Absolute spread alone is misleading where I_B is of order 1e-9: a 2.4e-9 absolute
    spread is a 12 % disagreement. Both are stored, and the artifact must not claim
    start-independence it does not have."""
    for row in ROWS:
        opt = row["optimizer"]
        assert "named_spread_abs" in opt and "named_spread_rel" in opt
        assert opt["options"]["ftol"] <= 1e-13
    worst_rel = max(r["optimizer"]["named_spread_rel"] for r in ROWS)
    assert worst_rel > 0.01, (
        "named starts now agree everywhere; if that is real, the determinism wording may be "
        "strengthened -- but only deliberately")
    det = ART["determinism"]
    assert "BEST-OF-CANDIDATES" in det.upper()
    assert "not a certified global infimum" in det
    assert "start-independent" not in det.lower().replace("not start-independent", "")


def test_low_named_spread_does_not_certify_a_minimum():
    """The reason the grid exists. On five rows the deterministic grid beat every named start,
    and on those rows the named starts agreed to between 0.003 % and 0.115 %."""
    beat = [r for r in ROWS if r["optimizer"]["grid_beat_named"] > 1e-6]
    assert beat, "the grid never beats the named starts; re-check that it is actually running"
    for row in beat:
        assert row["optimizer"]["grid_beat_named"] > row["optimizer"]["named_spread_rel"], (
            "on a row where the grid wins, the named starts' own spread understates the error")
    worst = max(beat, key=lambda r: r["optimizer"]["grid_beat_named"])
    assert worst["regime"] == "principal", "the worst grid win has moved off the principal rows"
    assert worst["optimizer"]["grid_beat_named"] > 0.05


def test_the_24_overlapping_rows_regress_against_res7A():
    """Requirement 6, with the direction preserved: a lower infimum is the reference being
    under-converged, not this run failing."""
    reg = ART["regression_vs_res7A"]
    assert reg["compared"] == 24 and reg["expected"] == 24
    assert reg["tolerance"] == 6e-8
    assert reg["breaches"] == [], f"E is worse than res7A somewhere: {reg['breaches']}"
    assert reg["review_required"] == [], (
        f"rows need human review before E closes: {reg['review_required']}")
    for u in reg["reference_under_converged"]:
        assert u["mine"] < u["res7A"], "an under-convergence entry is not actually lower"
        assert u["all_candidates_below_reference"], (
            "a row was accepted as under-converged reference without every candidate agreeing")
        assert u["allowlist_reason"], "a row was accepted without an allowlist entry"
        assert u["regime"] == "servo-context", (
            "res7A under-convergence has reached a principal-regime row; C26's principal "
            "numbers must be rechecked before this is relaxed")


def test_a_lower_infimum_is_never_accepted_automatically():
    """The gate must require BOTH an allowlist entry and unanimous candidates."""
    src = open(os.path.join(ROOT, "analysis", "runs", "sid_run9.py"), encoding="utf-8").read()
    assert "UNDER_CONVERGED_ALLOWLIST" in src
    assert "if allowed and all_below:" in src, "the two conditions are not both enforced"
    assert "review_required" in src


def test_C13_is_withdrawn_and_C26_supersedes_it():
    """The false exact-zero formulation and its supported replacement are separate claims,
    following the C01/C21 precedent, rather than one statement rewritten in place."""
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    c13 = txt.split("- id: C13")[1].split("- id:")[0]
    assert "status: withdrawn" in c13
    assert "res7A_identifiability.json" in c13, "C13 must keep pointing at its own output"
    assert "sid_run7.py" in c13 and "sid_run9.py" not in c13.split("errata:")[1].split("\n")[1:][0]
    assert "zero retained information" in c13, "C13's historical statement was not preserved"

    c26 = txt.split("- id: C26")[1].split("- id:")[0]
    assert "supersedes: C13" in c26
    assert "status: result" in c26
    assert "Delta Gamma_phi / Gamma_hat > 2 eta0" in c26, "C26 is not stated dimensionlessly"
    assert "res9_identifiability_T2.json" in c26 and "sid_run9.py" in c26
    assert "21 of 40" in c26 and "best-of-candidates" in c26


def test_class_A_boundary_exception_is_real():
    """C13's corrected clause rests on this: at tau_c/T2 = 0.2 with eta_0 = 0.02 the pointwise
    band is NOT zero, while at 0.05 it is zero everywhere."""
    for row in ROWS:
        if row["tau_c_over_T2"] == 0.05:
            assert row["I_A"] == 0.0, "class A is nonzero at tau_c/T2 = 0.05"
    boundary = [r for r in ROWS if r["tau_c_over_T2"] == 0.2 and r["eta_0"] == 0.02]
    assert len(boundary) == 3
    for row in boundary:
        assert row["I_A"] > 0.0
        assert row["class_A_points_passing"] == 21
        # 3.39e-3 at C_0 = 0.9 up to 3.65e-3 at C_0 = 0.4; the point is that it is not zero
        assert 3.3e-3 < row["I_A"] / row["I_unc"] < 3.7e-3
