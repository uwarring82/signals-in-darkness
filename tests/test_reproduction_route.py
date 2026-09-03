"""The documented reproduction route must actually compute, with the archive present.

This is the executable release gate for the defect recorded in
notes/2026-09-03-note-04-reproduction-defect.md. At tag archive-2026-09-03,
analysis/runs/sid_run6s.py used its own published output
(analysis/outputs/res6_policies.json) as mutable checkpoint state, so on a clean
clone the command the README documents printed the archived numbers in zero seconds
and simulated nothing. The tests below fail if that behaviour returns.

They deliberately run WITH the committed reference archive in place -- that is the
condition under which the original defect was invisible. The simulator itself is
stubbed or run at a trivial size, so the whole file executes in well under a second;
this gate checks the route's postconditions, not the physics (the physics is
checked by test_analytic.py and by a full clean-checkout rerun).
"""
import json
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "analysis", "lib"))
sys.path.insert(0, os.path.join(ROOT, "analysis", "runs"))

import sid_policies
import sid_repro
import sid_run6s

REFERENCE = os.path.join(ROOT, "analysis", "outputs", "res6_policies.json")


@pytest.fixture
def isolated_reproduction_dir(tmp_path, monkeypatch):
    """Point fresh output and checkpoints at a temporary directory."""
    monkeypatch.setattr(sid_repro, "REPRODUCTION_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def counting_calibrate(monkeypatch):
    """Replace the expensive calibration with a stub that records its calls."""
    calls = []

    def stub(bank, sched, gamma, R=48, iters=5, **kw):
        calls.append(R)
        sid_policies.STATS["run_batch_calls"] += 1        # a real calibrate would simulate
        return 3.421875, 30000.0, 1000.0, 0

    monkeypatch.setattr(sid_run6s, "calibrate", stub)
    return calls


def test_reference_archive_is_present():
    """If this fails the other tests prove nothing -- the defect only shows with the archive."""
    assert os.path.exists(REFERENCE), "published reference archive missing"
    state = json.load(open(REFERENCE))
    assert state["cal"], "reference archive has no calibration rows to short-circuit on"
    assert "extremum-only" in state["cal"]


def test_documented_command_computes_although_the_archive_holds_the_answer(
        isolated_reproduction_dir, counting_calibrate, capsys):
    rc = sid_run6s.main(["sid_run6s.py", "cal:extremum-only"])
    out = capsys.readouterr().out
    assert counting_calibrate == [32], "calibration was skipped: the route replayed stored values"
    assert "computed: 1, cached: 0" in out, out
    assert rc in (0, 1)          # 1 is a tolerance failure, which is still a real run


def test_fresh_is_the_default_and_resume_is_opt_in(
        isolated_reproduction_dir, counting_calibrate, capsys):
    sid_run6s.main(["sid_run6s.py", "cal:extremum-only"])
    capsys.readouterr()
    assert (isolated_reproduction_dir / "res6_policies.json").exists()

    # a second default run must recompute even though a checkpoint now exists
    sid_run6s.main(["sid_run6s.py", "cal:extremum-only"])
    assert "computed: 1, cached: 0" in capsys.readouterr().out
    assert len(counting_calibrate) == 2

    # only --resume may reuse it
    sid_run6s.main(["sid_run6s.py", "cal:extremum-only", "--resume"])
    assert "computed: 0, cached: 1" in capsys.readouterr().out
    assert len(counting_calibrate) == 2, "--resume recomputed instead of reusing"


def test_run_never_writes_into_the_published_archive(
        isolated_reproduction_dir, counting_calibrate):
    before = open(REFERENCE, "rb").read()
    sid_run6s.main(["sid_run6s.py", "cal:extremum-only"])
    assert open(REFERENCE, "rb").read() == before, "a run script mutated the published archive"


def test_reported_work_is_backed_by_simulation():
    """computed: N must mean the simulator ran; the counter is what the gate reads."""
    sid_policies.reset_stats()
    assert sid_policies.STATS["run_batch_calls"] == 0
    bank = sid_policies.Bank([20.0])
    stop = sid_policies.run_batch(bank, sid_policies.sched_ext, None, 2.0, 4, 7, 200, True)
    assert sid_policies.STATS["run_batch_calls"] == 1
    assert sid_policies.STATS["simulated_steps"] > 0
    assert len(stop) == 4


def test_declared_tolerance_rejects_a_transcribed_threshold():
    """h* must be compared exactly: the two bad archive rows pass a 3-sigma mean test."""
    fresh = {"oracle-mid(tc=20)": [4.671875, 44698.640625, 5208.357712, 4]}
    archived = {"oracle-mid(tc=20)": [4.359, 33852, 3394, 0]}
    verdicts, n_pass, n_fail = sid_repro.compare_rows(fresh, archived)
    assert n_fail == 1 and n_pass == 0
    assert "threshold" in verdicts[0]
    # the mean alone would NOT have caught it -- 1.74 sigma, inside the 3 sigma band
    dev = abs(44698.640625 - 33852)/((5208.357712**2 + 3394**2)**0.5)
    assert dev < sid_repro.SIGMA_TOL
