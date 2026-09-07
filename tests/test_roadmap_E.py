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


def test_all_three_optimizer_starts_are_recorded_with_their_status():
    """Requirement 5: starts, solutions, convergence status, objective, iterations, selection."""
    for row in ROWS:
        opt = row["optimizer"]
        assert len(opt["starts"]) == 3
        for st in opt["starts"]:
            for field in ("x0", "x", "fun", "success", "status", "nit", "message"):
                assert field in st, f"optimizer start is missing {field}"
            assert st["success"], f"a start did not converge at C_0={row['C_0']}"
        assert opt["selected_fun"] == min(s["fun"] for s in opt["starts"])
        assert row["I_B"] == pytest.approx(max(opt["selected_fun"], 0.0), rel=1e-15)


def test_explicit_tolerances_collapse_the_across_start_spread():
    """The 6e-8 recorded for res7A was default-tolerance under-convergence, not an intrinsic
    property of the infimum. With explicit tolerances the three starts agree far more tightly."""
    worst = max(r["optimizer"]["start_spread"] for r in ROWS)
    assert worst < 1e-8, f"across-start spread {worst:.2e} is back at the default-tolerance level"
    assert worst < ART["regression_vs_res7A"]["tolerance"], (
        "the across-start spread must sit inside the regression tolerance, or the regression "
        "is measuring optimiser noise rather than agreement")
    for row in ROWS:
        assert row["optimizer"]["options"]["ftol"] <= 1e-13


def test_the_24_overlapping_rows_regress_against_res7A():
    """Requirement 6, with the direction preserved: a lower infimum is the reference being
    under-converged, not this run failing."""
    reg = ART["regression_vs_res7A"]
    assert reg["compared"] == 24 and reg["expected"] == 24
    assert reg["tolerance"] == 6e-8
    assert reg["breaches"] == [], f"E is worse than res7A somewhere: {reg['breaches']}"
    for u in reg["reference_under_converged"]:
        assert u["mine"] < u["res7A"], "an under-convergence entry is not actually lower"
        assert u["regime"] == "servo-context", (
            "res7A under-convergence has reached a principal-regime row; C13's principal "
            "numbers must be rechecked before this is relaxed")


def test_C13_carries_the_dimensionless_criterion_and_its_corrections():
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    blk = txt.split("- id: C13")[1].split("- id:")[0]
    assert "Delta Gamma_phi / Gamma_hat > 2 eta0" in blk, "C13 is not stated dimensionlessly"
    assert "sid_run9.py" in blk
    # the boundary exception that the earlier unqualified "zero" got wrong
    assert "0.02" in blk and "21 of 40" in blk


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
