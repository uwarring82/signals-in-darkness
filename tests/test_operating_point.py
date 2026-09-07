"""Roadmap G — the operating point is an explicit, immutable, serialised object.

Until 7 September 2026 `analysis/lib/sid_policies.py` held `C, s = 0.4, 0.5` as mutable module
globals with three readers. That is a provenance defect, not a style one: a stored result did
not carry the parameters it was computed at, so a checkpoint could not refuse reuse under the
wrong ones. Claims C17 and C18 were withdrawn over calibration whose provenance could not be
established.

These tests are G's acceptance boundary, one test per condition.
"""
import json
import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "analysis", "lib"))
sys.path.insert(0, os.path.join(ROOT, "analysis", "runs"))

import sid_policies as P
import sid_repro


def _src(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as fh:
        return fh.read()


# ---- 1. an immutable operating-point object carrying C_eff and s -------------------------

def test_operating_point_is_immutable_and_carries_C_eff_and_s():
    op = P.OperatingPoint(C_eff=0.4, s=0.5)
    assert (op.C_eff, op.s) == (0.4, 0.5)
    with pytest.raises(Exception):
        op.C_eff = 0.9          # frozen dataclass
    assert op == P.OperatingPoint(C_eff=0.4, s=0.5), "operating points must compare by value"
    assert op != P.OperatingPoint(C_eff=0.5, s=0.5)
    assert op.as_dict() == {"C_eff": 0.4, "s": 0.5}


def test_the_field_is_C_eff_and_not_the_ambiguous_C_bar():
    """D1: B's effective contrast and E's zero-dephasing contrast are different quantities."""
    assert hasattr(P.OperatingPoint(0.4, 0.5), "C_eff")
    assert not hasattr(P.OperatingPoint(0.4, 0.5), "C_bar")
    assert not hasattr(P.OperatingPoint(0.4, 0.5), "C_0")


# ---- 2. every consumer receives it explicitly --------------------------------------------

def test_bank_and_build_policies_require_an_explicit_operating_point():
    with pytest.raises(TypeError):
        P.Bank([20.0])
    with pytest.raises(TypeError):
        P.build_policies()
    with pytest.raises(TypeError):
        P.Bank([20.0], "not an operating point")


def test_the_simulator_reads_the_operating_point_from_the_bank():
    """Two banks at different operating points must produce different behaviour, which is
    only possible if run_batch reads from the bank rather than from module state."""
    lo = P.Bank([20.0], P.OperatingPoint(C_eff=0.2, s=0.5))
    hi = P.Bank([20.0], P.OperatingPoint(C_eff=0.9, s=0.5))
    assert lo.p0(P.THX) != hi.p0(P.THX)
    a = P.run_batch(lo, P.sched_ext, None, 3.0, 8, 5, 400, True)
    b = P.run_batch(hi, P.sched_ext, None, 3.0, 8, 5, 400, True)
    assert list(a) != list(b), "the simulator is not responding to the bank's operating point"


def test_calibration_and_delay_take_their_operating_point_from_the_bank():
    """arl_of, delay_of and calibrate all reach the operating point through the bank they are
    handed. Checked by behaviour: the same threshold on two banks that differ ONLY in
    operating point must give different null run lengths."""
    assert P.Bank([20.0], P.PILOT).op is P.PILOT
    lo = P.Bank([20.0], P.OperatingPoint(C_eff=0.2, s=0.5))
    hi = P.Bank([20.0], P.OperatingPoint(C_eff=0.9, s=0.5))
    m_lo, _, _ = P.arl_of(lo, P.sched_ext, 2.5, 16, 11, cap=3000)
    m_hi, _, _ = P.arl_of(hi, P.sched_ext, 2.5, 16, 11, cap=3000)
    assert m_lo != m_hi, "arl_of does not respond to the bank's operating point"
    d_lo, _, _ = P.delay_of(lo, P.sched_ext, 20.0, 2.5, 16, 12, cap=3000)
    d_hi, _, _ = P.delay_of(hi, P.sched_ext, 20.0, 2.5, 16, 12, cap=3000)
    assert d_lo != d_hi, "delay_of does not respond to the bank's operating point"


# ---- 3. no mutable or imported module-level C and s ---------------------------------------

def test_no_module_level_operating_point_survives():
    assert not hasattr(P, "C"), "module-level C is back"
    assert not hasattr(P, "s"), "module-level s is back"
    src = _src("analysis/lib/sid_policies.py")
    assert "\nC, s = " not in src, "the mutable global assignment is back"


def test_no_run_imports_C_or_s_from_the_library():
    for run in ("sid_run6s.py", "sid_run8.py"):
        src = _src(os.path.join("analysis", "runs", run))
        for line in src.splitlines():
            if line.startswith("from sid_policies import"):
                imported = {n.strip() for n in line.split("import", 1)[1].split(",")}
                assert "C" not in imported and "s" not in imported, (
                    f"{run} still imports the operating point as loose names: {line}")


def test_the_pilot_constant_is_the_documented_one():
    assert P.PILOT == P.OperatingPoint(C_eff=0.4, s=0.5)


# ---- 4 & 5. serialised into checkpoint identity, and reuse refused when it differs ---------

def test_the_operating_point_enters_checkpoint_identity():
    import sid_run6s
    cfg = sid_run6s.cal_config(["extremum-only"])
    assert cfg["operating_point"] == P.PILOT.as_dict(), (
        "the calibration config does not carry the operating point, so a checkpoint cannot "
        "record what it was computed at")


def test_checkpoint_reuse_is_refused_when_the_operating_point_differs():
    """The condition G exists for: thresholds measured at one operating point must not be
    silently consumed by a run at another."""
    import sid_run6s
    have = sid_repro.run_metadata(sid_run6s.cal_config(["extremum-only"]))
    other = dict(sid_run6s.cal_config(["extremum-only"]))
    other["operating_point"] = P.OperatingPoint(C_eff=0.5, s=0.3).as_dict()
    want = sid_repro.run_metadata(other)
    why = sid_repro.incompatibilities(have, want)
    assert why, "a differing operating point did not make the checkpoint incompatible"
    # The refusal must NAME the operating point, not merely report an opaque digest mismatch.
    # Verified end to end on 7 Sept 2026: a tampered checkpoint made `sid_run6s.py delays`
    # exit 2 printing exactly this line alongside the digest difference.
    named = [r for r in why if "operating_point" in r]
    assert named, f"the refusal does not name the operating point: {why}"
    assert "0.5" in named[0] and "0.3" in named[0] and "0.4" in named[0], (
        f"the refusal does not show both operating points: {named[0]!r}")


def test_identical_configurations_remain_compatible():
    """The gate must reject a changed operating point without rejecting everything."""
    import sid_run6s
    cfg = sid_run6s.cal_config(["extremum-only"])
    a = sid_repro.run_metadata(cfg)
    b = sid_repro.run_metadata(dict(cfg))
    assert sid_repro.incompatibilities(a, b) == []


# ---- figure provenance --------------------------------------------------------------------

def test_the_policy_figure_does_not_hardcode_its_operating_point():
    src = _src(os.path.join("analysis", "runs", "sid_fig_policy_delays.py"))
    assert "\\\\bar C=0.4" not in src and "$s=0.5$" not in src, (
        "the figure names its operating point in a string literal, which keeps claiming it "
        "after the run beneath it moves")
    assert "operating_point" in src, "the figure does not read the recorded operating point"


# ---- 6 & 7. the pilot calibration rows, and what the preservation claim excludes -----------

WITHDRAWN_ROWS = ("oracle-mid(tc=20)", "learner-interleave-B10(bank)")
PRESERVED_ROWS = ("oracle-mid(tc=5)", "oracle-mid(tc=1)", "extremum-only",
                  "learner-mid(bank)", "learner-interleave-B1(bank)")


def test_the_preservation_claim_excludes_exactly_the_withdrawn_rows():
    """C17 withdrew two calibration rows. They are excluded from the preservation claim by
    name, not by whether they happen to reproduce."""
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    c17 = txt.split("- id: C17")[1].split("- id:")[0]
    assert "withdrawn" in c17
    for row in WITHDRAWN_ROWS:
        assert row in c17, f"{row} is not named in C17; the exclusion list may be wrong"
    ref = json.load(open(os.path.join(ROOT, "analysis", "outputs", "res6_policies.json"),
                         encoding="utf-8"))
    assert set(ref["cal"]) == set(WITHDRAWN_ROWS) | set(PRESERVED_ROWS), (
        "the archived calibration no longer holds exactly the seven pilot policies")


@pytest.mark.skipif(
    not os.path.exists(os.path.join(ROOT, "analysis", "reproduction", "res6_policies.json")),
    reason="no fresh calibration present; run sid_run6s.py cal:... to check preservation")
def test_the_five_valid_pilot_rows_reproduce_exactly_after_the_refactor():
    """G's central acceptance condition. Thresholds are compared by EXACT equality, which is
    the gate sid_repro already applies -- a refactor that changed the numbers at all would
    show up here rather than hiding inside a tolerance."""
    ref = json.load(open(os.path.join(ROOT, "analysis", "outputs", "res6_policies.json"),
                         encoding="utf-8"))["cal"]
    fresh = json.load(open(os.path.join(ROOT, "analysis", "reproduction", "res6_policies.json"),
                           encoding="utf-8"))["cal"]
    missing = [r for r in PRESERVED_ROWS if r not in fresh]
    if missing:
        pytest.skip(f"fresh calibration does not yet cover {missing}")
    for row in PRESERVED_ROWS:
        assert fresh[row][0] == ref[row][0], (
            f"{row}: threshold {fresh[row][0]!r} after the refactor, {ref[row][0]!r} in the "
            f"archive. The operating-point refactor must be numerically inert.")
