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
from sid_policies import state_name_for  # noqa: F401


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
    cfg = sid_run8.run_config(P.PILOT, "pilot")
    assert cfg["operating_point"] == P.PILOT.as_dict(), (
        "sid_run8's checkpoint carries no operating point, so it can be resumed at another")
    # everything that can move a threshold must be in the identity, not only the pair (C, s)
    for field in ("bank_tccs", "bracket", "null_cap", "delay_cap", "seed_offset", "delay_tccs"):
        assert field in cfg, f"run_config omits {field}: editing it would leave the digest intact"
    have = sid_repro.run_metadata(cfg)
    why = sid_repro.incompatibilities(have, sid_repro.run_metadata(
        sid_run8.run_config(P.STRESS, "stress")))
    assert any("operating_point" in r for r in why), (
        f"sid_run8 would not refuse a checkpoint from another operating point: {why}")


def test_the_pilot_constant_is_the_documented_one():
    assert P.PILOT == P.OperatingPoint(C_eff=0.4, s=0.5)


# ---- 4 & 5. serialised into checkpoint identity, and reuse refused when it differs ---------

def test_the_operating_point_enters_checkpoint_identity():
    import sid_run6s
    cfg = sid_run6s.cal_config(["extremum-only"], P.PILOT, "pilot")
    assert cfg["operating_point"] == P.PILOT.as_dict(), (
        "the calibration config does not carry the operating point, so a checkpoint cannot "
        "record what it was computed at")


def test_checkpoint_reuse_is_refused_when_the_operating_point_differs():
    """The condition G exists for: thresholds measured at one operating point must not be
    silently consumed by a run at another."""
    import sid_run6s
    have = sid_repro.run_metadata(sid_run6s.cal_config(["extremum-only"], P.PILOT, "pilot"))
    other = sid_run6s.cal_config(["extremum-only"], P.STRESS, "stress")
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
        cfg = sid_run8.run_config(P.STRESS, "stress")
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
    cfg = sid_run6s.cal_config(["extremum-only"], P.PILOT, "pilot")
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


# ---- guards added after the roadmap B path audit, 7 Sept 2026 -----------------------------

def test_the_pilot_calibration_bracket_is_frozen():
    """The pilot's (lo, hi, iters) produced the archived thresholds and G's preservation
    evidence compares them by exact equality. Changing them silently invalidates that."""
    assert P.CAL_BRACKET["pilot"] == (1.0, 6.0, 5)
    assert P.SEED_OFFSET["pilot"] == 0, "a pilot seed offset would move its archived numbers"


def test_every_operating_point_has_its_own_bracket_and_seed_offset():
    for name in P.OPERATING_POINTS:
        assert name in P.CAL_BRACKET, f"{name} has no calibration bracket"
        assert name in P.SEED_OFFSET, f"{name} has no seed offset"
    # Distinct PHYSICAL operating points must not share a seed offset: simulate() scales the
    # same standard normals by s, so a shared seed makes their latent paths perfectly
    # correlated and the second is not an independent measurement. Profiles of the SAME point
    # (pilot vs pilot_recal) should share seeds -- that is what makes them comparable.
    by_point = {}
    for name, op in P.OPERATING_POINTS.items():
        by_point.setdefault((op.C_eff, op.s), []).append(P.SEED_OFFSET[name])
    for point, offsets in by_point.items():
        assert len(set(offsets)) == 1, (
            f"profiles of the same operating point {point} use different seeds, so they cannot "
            f"be compared: {offsets}")
    distinct = [offs[0] for offs in by_point.values()]
    assert len(set(distinct)) == len(distinct), (
        "two distinct operating points share a seed offset, so their latent noise paths are "
        "perfectly correlated and the second is not an independent measurement")


def test_calibrate_reports_a_bracket_end_that_never_moved(monkeypatch):
    """The defect this guard exists for: at the stress point under the pilot's bracket,
    oracle-mid(tc=1) converged to the midpoint of an untested [1.0, 1.156] and confirmed at
    ARL 23669, a 21 % miss, with nothing reporting it.

    Driven by a deterministic stub ARL(h) = e^h, so the branch taken at each probe is exactly
    known and the test exercises the bracket logic rather than a simulation.
    """
    monkeypatch.setattr(P, "arl_of",
                        lambda bank, sched, h, R, seed, cap=0: (math.exp(h), 0.0, 0))
    bank = P.Bank([1.0], P.PILOT)
    # gamma below ARL at every probe in [1, 6]: hi collapses, the floor is never moved
    _, _, _, _, pinned = P.calibrate(bank, P.sched_mid, math.exp(0.5), R=4, lo=1.0, hi=6.0,
                                     iters=4, seed=100)
    assert pinned == "floor", f"a pinned floor was not reported (got {pinned!r})"
    # gamma above ARL at every probe: lo climbs, the ceiling is never moved
    _, _, _, _, pinned_hi = P.calibrate(bank, P.sched_mid, math.exp(9.0), R=4, lo=1.0, hi=6.0,
                                        iters=4, seed=100)
    assert pinned_hi == "ceiling", f"a pinned ceiling was not reported (got {pinned_hi!r})"
    # gamma inside the bracket: both ends move and nothing is flagged
    h, _, _, _, clean = P.calibrate(bank, P.sched_mid, math.exp(3.0), R=4, lo=1.0, hi=6.0,
                                    iters=4, seed=100)
    assert clean is None, f"a two-sided bisection was wrongly flagged ({clean!r})"
    assert abs(h - 3.0) < 0.5, "the two-sided bisection did not converge near the true root"


def test_drivers_refuse_an_unknown_flag_rather_than_defaulting_to_the_pilot():
    """`--operating-point stress` with a space would otherwise select the pilot AND overwrite
    the pilot's checkpoint while the operator believed they were running B."""
    import subprocess
    for run in ("sid_run6s.py", "sid_run8.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "analysis", "runs", run),
                            "cal:extremum-only", "--operating-point", "stress"],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 2, f"{run} accepted a spaced --operating-point (exit {r.returncode})"
        assert "unrecognised option" in r.stderr, f"{run} did not name the bad flag:\n{r.stderr}"


def test_a_run_without_an_archived_reference_must_be_asked_for():
    """Otherwise it prints the tolerance header, lists NO-REFERENCE for every row, summarises
    '0 pass, 0 FAIL' and exits 0 -- indistinguishable from a run that compared and agreed.

    The stress point HAS an archive since roadmap B published one, so the archive is moved
    aside for the length of this test and restored afterwards. Asserting the refusal only
    when the file happens to be missing would make the guard untestable the moment it was
    first used, which is the shape of a check that quietly stops checking.
    """
    import shutil
    import subprocess
    import tempfile

    archive = os.path.join(ROOT, "analysis", "outputs", "res6_policies_stress.json")
    stash = None
    if os.path.exists(archive):
        stash = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
        shutil.move(archive, stash)
    try:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "analysis", "runs", "sid_run6s.py"),
                            "cal:extremum-only", "--operating-point=stress"],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 2, (
            f"a run with no archived reference was allowed without --no-reference "
            f"(exit {r.returncode})")
        assert "ESTABLISH" in r.stderr and "not verify" in r.stderr
    finally:
        if stash:
            shutil.move(stash, archive)
    assert os.path.exists(archive), "the stress archive was not restored"


def test_a_published_operating_point_is_compared_rather_than_established():
    """The other half: once an archive exists, the run must compare against it rather than
    still claiming it establishes anything."""
    assert os.path.exists(os.path.join(ROOT, "analysis", "outputs", "res6_policies_stress.json")), (
        "roadmap B's stress artifact is not published, so nothing verifies future stress runs")
    doc = json.load(open(os.path.join(ROOT, "analysis", "outputs", "res6_policies_stress.json"),
                         encoding="utf-8"))
    assert doc["meta"]["config"]["operating_point"] == P.STRESS.as_dict()
    assert not doc["meta"]["revision"].endswith("+dirty"), (
        "the published stress artifact was produced from an uncommitted tree")


def test_main_reads_the_operating_point_from_its_own_argv():
    """It was read from module-level sys.argv, so every programmatic caller -- including this
    test suite -- silently got the pilot regardless of what it asked for."""
    import sid_run6s
    src = _src(os.path.join("analysis", "runs", "sid_run6s.py"))
    assert "operating_point_from_argv(sys.argv)" not in src, (
        "the operating point is bound from module-level sys.argv again")
    assert "operating_point_from_argv(argv)" in src
    # an unknown flag is refused by main() itself, which proves it parsed the argv it was given
    assert sid_run6s.main(["x", "cal:extremum-only", "--operating-point", "stress"]) == 2
    # and the state name it derives follows the operating point it was handed
    assert sid_run6s.state_name_for("res6_policies.json", "stress") == "res6_policies_stress.json"


# ---- the matched-E0[T] premise, after note 19 ---------------------------------------------

def test_the_arl_envelope_is_a_gate_not_a_warning():
    """It lived as a warning inside sid_fig_policy_delays.py, printed AFTER the figure had been
    drawn from the offending rows. Every delay ratio divides by a benchmark, and a policy
    calibrated outside the envelope is not held to the same false-alarm rate as the others, so
    the ratios built on it are incomparable."""
    assert P.ARL_ENVELOPE == 0.30
    src = _src(os.path.join("analysis", "runs", "sid_run6s.py"))
    assert "envelope_failures" in src, "the driver does not collect envelope breaches"
    assert "ARL ENVELOPE BREACHES" in src, "the driver does not report them"
    assert "status = status or 4" in src, "an envelope breach does not fail the run"


def test_calibrate_refined_beats_plain_bisection_where_it_is_known_to_fail(monkeypatch):
    """Driven by a deterministic stub ARL(h) = e^h so the answer is known exactly.

    Plain bisection returns the midpoint of its final interval; the refinement interpolates
    ln(ARL) across that interval, which is exact for this stub and near-exact in practice
    because ARL grows close to exponentially in the threshold.
    """
    monkeypatch.setattr(P, "arl_of",
                        lambda bank, sched, h, R, seed, cap=0: (math.exp(h), 0.0, 0))
    bank = P.Bank([1.0], P.PILOT)
    target = math.exp(3.3)
    h_plain, _, _, _, _ = P.calibrate(bank, P.sched_mid, target, R=4, lo=1.0, hi=6.0,
                                      iters=4, seed=100)
    h_ref, m_ref, _, _, _, inside = P.calibrate_refined(bank, P.sched_mid, target, R=4, lo=1.0,
                                                        hi=6.0, iters=4, seed=100)
    assert abs(h_ref - 3.3) < abs(h_plain - 3.3), (
        f"the refinement is no better than bisection: {h_ref} vs {h_plain}, true 3.3")
    assert abs(h_ref - 3.3) < 1e-9, "log-interpolation should be exact for an exponential ARL"
    assert inside is True


def test_the_recal_profile_is_the_same_operating_point_but_a_separate_artifact():
    """The historical archive must not be overwritten by a recalibration of the same point."""
    assert P.OPERATING_POINTS["pilot_recal"] is P.PILOT
    assert P.state_name_for("res6_policies.json", "pilot_recal") == "res6_policies_pilot_recal.json"
    assert P.state_name_for("res6_policies.json", "pilot") == "res6_policies.json"


def test_no_result_claim_points_at_an_artifact_with_a_breaching_calibration():
    """A live invariant, not a snapshot.

    The first version of this test asserted that C09, C11 and C28 were `open` -- true while
    their chain breached the +-30 % envelope, and false the moment it was recalibrated. That is
    a check that stops checking, the failure mode this repository has now hit three times.

    What actually matters is the rule underneath: every delay ratio divides by a benchmark, so a
    claim marked `result` must not rest on an artifact in which any policy was calibrated outside
    the envelope. This walks each claim's own output pointer and enforces exactly that.
    """
    import re
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    blocks = re.split(r"^- id: ", txt, flags=re.M)[1:]
    checked = 0
    for blk in blocks:
        cid = blk.split("\n", 1)[0].strip()
        status = next((l.split(": ", 1)[1].strip() for l in blk.splitlines()
                       if l.startswith("  status: ")), None)
        out = next((l.split(": ", 1)[1].strip() for l in blk.splitlines()
                    if l.startswith("  output: ")), "")
        for name in re.findall(r"res6_policies[\w.]*\.json", out):
            path = os.path.join(ROOT, "analysis", "outputs", name)
            if not os.path.exists(path):
                continue
            cal = json.load(open(path, encoding="utf-8")).get("cal", {})
            breaches = {k: v[1] for k, v in cal.items()
                        if abs(v[1] - 3.0e4) / 3.0e4 > P.ARL_ENVELOPE}
            checked += 1
            if status != "result" or not breaches:
                continue
            # A `result` MAY rest on an artifact containing a breaching row, but only if it
            # DECLARES the breach. Silence is what makes a breach dangerous: a reader building
            # a ratio on that policy has no way to know it is not held to the same false-alarm
            # rate. This is the declared-exception rule the archive uses everywhere else --
            # a withdrawn claim must carry an errata pointer, an unverified reference must say
            # so -- applied to calibration.
            statement = next((l.split(": ", 1)[1] for l in blk.splitlines()
                              if l.startswith("  statement: ")), "")
            # Conservative on purpose. An earlier version tried to infer WHICH policies a claim
            # depends on, by matching policy names in its prose. That is fragile in both
            # directions -- "learner-mid(bank)" reduces to the token "mid", which matches
            # "mid-fringe" in any statement, and a claim can depend on a policy it never names.
            # So the rule is simply: if you mark a claim `result` on an artifact, you disclose
            # every calibration breach that artifact contains, and you quote its size. A claim
            # that does not use the breaching row says so in one clause; that is cheaper than a
            # heuristic that can be wrong silently.
            for policy, arl in sorted(breaches.items()):
                pct = 100 * (arl - 3.0e4) / 3.0e4
                quoted = (f"{pct:+.1f}"[1:] in statement or f"{arl:.0f}" in statement)
                assert quoted, (
                    f"{cid} is `result` and rests on {name}, in which {policy} is calibrated to "
                    f"ARL {arl:.0f} ({pct:+.1f} %), outside the +-{100*P.ARL_ENVELOPE:.0f} % "
                    f"envelope -- and the claim does not disclose it. Every delay ratio divides "
                    f"by a benchmark, so a policy outside the envelope is not held to the same "
                    f"false-alarm rate. Quote the breach and say whether the claim uses that "
                    f"row, or do not mark the claim `result`.")
    assert checked, "no claim points at a policy artifact; this invariant is inert"


def test_the_recalibrated_pilot_artifact_is_fully_inside_the_envelope():
    """The repair itself, asserted from the published artifact."""
    path = os.path.join(ROOT, "analysis", "outputs", "res6_policies_pilot_recal.json")
    assert os.path.exists(path), "the recalibrated pilot artifact is not published"
    doc = json.load(open(path, encoding="utf-8"))
    assert not doc["meta"]["revision"].endswith("+dirty")
    worst = max((abs(v[1] - 3.0e4) / 3.0e4, k) for k, v in doc["cal"].items())
    assert worst[0] <= P.ARL_ENVELOPE, (
        f"{worst[1]} is {100*worst[0]:.1f} % off target in the recalibrated artifact")
    assert sum(r[2] for t in doc["delays"].values() for r in t.values()) == 0, \
        "the recalibrated chain has capped delay runs"
