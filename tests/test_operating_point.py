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


def test_no_run_imports_OR_REBINDS_C_or_s():
    """Forbidding the import is not enough. The first attempt at this fix removed
    `from sid_policies import C, s` from sid_run8 and then wrote `C, s = OP.C_eff, OP.s`
    one line below, rebuilding the same coupling: run_batch_age drew its post-change
    process from those module names while its filter and null came from bank.op, so a bank
    at a second operating point would have been simulated against the pilot's process.
    Freezing OP does not freeze a binding derived from it."""
    import ast
    for run in ("sid_run6s.py", "sid_run8.py"):
        src = _src(os.path.join("analysis", "runs", run))
        for line in src.splitlines():
            if line.startswith("from sid_policies import"):
                imported = {n.strip() for n in line.split("import", 1)[1].split(",")}
                assert "C" not in imported and "s" not in imported, (
                    f"{run} still imports the operating point as loose names: {line}")
        # and no module-level assignment binds them either
        for node in ast.parse(src).body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = set()
                for tgt in targets:
                    if isinstance(tgt, ast.Name):
                        names.add(tgt.id)
                    elif isinstance(tgt, ast.Tuple):
                        names |= {e.id for e in tgt.elts if isinstance(e, ast.Name)}
                assert not (names & {"C", "s"}), (
                    f"{run} rebinds the operating point at module level: {sorted(names & {chr(67), chr(115)})}")


def test_run_batch_age_reads_the_operating_point_from_its_bank():
    """The explore-then-switch simulator, which is a separate code path from run_batch and
    was the one that kept the defect after the first repair."""
    import sid_run8
    lo = P.Bank([1.0, 4.0], P.OperatingPoint(C_eff=0.2, s=0.5))
    hi = P.Bank([1.0, 4.0], P.OperatingPoint(C_eff=0.9, s=0.5))
    a = sid_run8.run_batch_age(lo, 50, 20.0, 2.5, 16, 21, 1500, False)
    b = sid_run8.run_batch_age(hi, 50, 20.0, 2.5, 16, 21, 1500, False)
    assert list(a) != list(b), (
        "run_batch_age does not respond to the bank's operating point; it is still reading "
        "module state for the post-change process")
    # and the null path too
    na = sid_run8.run_batch_age(lo, 50, None, 2.5, 16, 22, 1500, True)
    nb = sid_run8.run_batch_age(hi, 50, None, 2.5, 16, 22, 1500, True)
    assert list(na) != list(nb)


def test_sid_run8_has_a_serialised_configuration_identity():
    import sid_run8
    cfg = sid_run8.run_config()
    assert cfg["operating_point"] == P.PILOT.as_dict(), (
        "sid_run8's checkpoint carries no operating point, so it can be resumed at another")
    have = sid_repro.run_metadata(cfg)
    other = dict(cfg); other["operating_point"] = P.OperatingPoint(C_eff=0.5, s=0.3).as_dict()
    why = sid_repro.incompatibilities(have, sid_repro.run_metadata(other))
    assert any("operating_point" in r for r in why), (
        f"sid_run8 would not refuse a checkpoint from another operating point: {why}")


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


def test_sid_run8_refuses_to_resume_across_operating_points_end_to_end():
    """Not a unit check on incompatibilities(): the driver is run as a subprocess against a
    planted checkpoint and must exit nonzero. The reproduction checkpoint is git-ignored
    scratch, but it is saved and restored so an in-progress run is not destroyed."""
    import shutil
    import subprocess
    import tempfile

    repro = os.path.join(ROOT, "analysis", "reproduction")
    os.makedirs(repro, exist_ok=True)
    ckpt = os.path.join(repro, "res8_switch.json")
    backup = None
    if os.path.exists(ckpt):
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
        shutil.copy(ckpt, backup)
    try:
        import sid_run8
        cfg = dict(sid_run8.run_config())
        cfg["operating_point"] = P.OperatingPoint(C_eff=0.5, s=0.3).as_dict()
        planted = {"switch": {"300": [3.0, 3.0e4, {"20.0": [100.0, 1.0], "5.0": [100.0, 1.0],
                                                  "1.0": [100.0, 1.0]}]},
                   "meta": sid_repro.run_metadata(cfg)}
        with open(ckpt, "w", encoding="utf-8") as fh:
            json.dump(planted, fh)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "analysis", "runs", "sid_run8.py"),
                            "--resume"], capture_output=True, text=True, timeout=300)
        assert r.returncode == 2, (
            f"sid_run8 --resume accepted a checkpoint from another operating point "
            f"(exit {r.returncode})\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
        assert "operating_point" in r.stderr, (
            f"the refusal does not name the operating point:\n{r.stderr}")
    finally:
        if os.path.exists(ckpt):
            os.remove(ckpt)
        if backup:
            shutil.move(backup, ckpt)


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


def test_the_policy_figure_refuses_to_combine_unequal_operating_points():
    """It draws res6_policies and res8_switch on one axis, so labelling both from one file's
    metadata would be a silent misattribution once the two can differ."""
    src = _src(os.path.join("analysis", "runs", "sid_fig_policy_delays.py"))
    assert "_op6" in src and "_op8" in src, "the figure reads only one of its two sources"
    assert "refusing to combine outputs from different operating points" in src, \
        "the figure does not refuse mismatched operating points"
    assert "sys.exit(" in src, "the refusal does not stop the rebuild"


# ---- 6 & 7. the pilot calibration rows, and what the preservation claim excludes -----------

WITHDRAWN_ROWS = ("oracle-mid(tc=20)", "learner-interleave-B10(bank)")
PRESERVED_ROWS = ("oracle-mid(tc=5)", "oracle-mid(tc=1)", "extremum-only",
                  "learner-mid(bank)", "learner-interleave-B1(bank)")


EVIDENCE = os.path.join(ROOT, "analysis", "G_preservation_evidence.json")


def _evidence():
    assert os.path.exists(EVIDENCE), (
        "analysis/G_preservation_evidence.json is missing. Run the cal: stage of "
        "sid_run6s.py from a clean tree, then tools/record_preservation_evidence.py.")
    with open(EVIDENCE, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_preservation_evidence_is_committed_and_not_merely_local():
    """G's central condition must be checkable from a clean checkout.

    The first version of this test skipped when the git-ignored reproduction file was
    absent -- which is always, on a fresh clone -- so the evidence existed only in a
    terminal transcript and was not bound to any commit. A gate that cannot run is not a
    gate; that is the first entry on this repository's own lessons list.
    """
    doc = _evidence()
    assert doc["recorded_at_revision"], "the evidence names no revision"
    run = doc["calibration_run"]
    assert run["revision"] and not run["revision"].endswith("+dirty"), (
        f"the calibration was run from a dirty tree: {run['revision']!r}")
    assert doc["operating_point"] == P.PILOT.as_dict()
    # every path the evidence names as uncommitted must be a real path. The first version of
    # the recorder used stdout.strip(), which removed the leading space of the first porcelain
    # line and cut a character off that filename.
    for path in doc.get("uncommitted_when_recorded", []):
        assert os.path.exists(os.path.join(ROOT, path)), (
            f"the evidence names {path!r} as uncommitted, and no such path exists; the "
            f"porcelain parsing is mangling filenames")


def test_the_five_valid_pilot_rows_reproduced_exactly_after_the_refactor():
    """G's acceptance condition, asserted from the committed artifact -- no skip."""
    doc = _evidence()
    assert tuple(doc["preserved_rows"]) == PRESERVED_ROWS
    assert tuple(doc["withdrawn_rows_excluded_by_name"]) == WITHDRAWN_ROWS
    c = doc["counts"]
    assert c["preserved_exact"] == c["preserved_total"] == 5, (
        f"only {c['preserved_exact']} of {c['preserved_total']} valid rows reproduced exactly; "
        f"the operating-point refactor must be numerically inert")
    assert c["withdrawn_failing"] == c["withdrawn_total"] == 2, (
        "the two C17-withdrawn rows no longer fail; a gate that cannot reject is not a gate")
    for row in doc["rows"]:
        if row["class"] == "preserved":
            assert row["h_exact_match"], f"{row['policy']}: {row['h_fresh']} vs {row['h_archive']}"
        else:
            assert not row["h_exact_match"], f"{row['policy']} unexpectedly matches the archive"


def test_the_live_reproduction_agrees_with_the_committed_evidence():
    """When a fresh calibration is present it must not contradict the artifact."""
    fresh_path = os.path.join(ROOT, "analysis", "reproduction", "res6_policies.json")
    if not os.path.exists(fresh_path):
        pytest.skip("no local calibration; the committed evidence is the gate")
    fresh = json.load(open(fresh_path, encoding="utf-8"))["cal"]
    doc = _evidence()
    for row in doc["rows"]:
        if row["policy"] in fresh:
            assert fresh[row["policy"]][0] == row["h_fresh"], (
                f"{row['policy']}: local calibration disagrees with the committed evidence")


def test_the_preservation_claim_excludes_exactly_the_withdrawn_rows_in_the_ledger():
    """C17 withdrew two calibration rows. They are excluded by name, not by outcome."""
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    c17 = txt.split("- id: C17")[1].split("- id:")[0]
    assert "withdrawn" in c17
    for row in WITHDRAWN_ROWS:
        assert row in c17, f"{row} is not named in C17; the exclusion list may be wrong"
    ref = json.load(open(os.path.join(ROOT, "analysis", "outputs", "res6_policies.json"),
                         encoding="utf-8"))
    assert set(ref["cal"]) == set(WITHDRAWN_ROWS) | set(PRESERVED_ROWS), (
        "the archived calibration no longer holds exactly the seven pilot policies")
