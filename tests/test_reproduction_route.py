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
        # 5-tuple since 7 Sept 2026: the last element names a bracket end that never moved,
        # or None when the bisection was two-sided. The stub reports a clean bracket.
        return 3.421875, 30000.0, 1000.0, 0, None

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
    bank = sid_policies.Bank([20.0], sid_policies.PILOT)
    stop = sid_policies.run_batch(bank, sid_policies.sched_ext, None, 2.0, 4, 7, 200, True)
    assert sid_policies.STATS["run_batch_calls"] == 1
    assert sid_policies.STATS["simulated_steps"] > 0
    assert len(stop) == 4


def _stub_delay(monkeypatch):
    calls = []

    def stub(bank, sched, true_tcc, h, R, seed, cap=100_000, return_runs=False):
        calls.append((true_tcc, h))
        # Since 8 Sept 2026 the driver asks for per-replicate stopping times, which the paired
        # bootstrap needs. The stub returns a constant series whose mean matches the mean it
        # reports, so anything downstream that recomputes from the runs stays consistent.
        out = (1234.0, 56.0, 0)
        return (*out, [1234.0] * R) if return_runs else out

    monkeypatch.setattr(sid_run6s, "delay_of", stub)
    return calls


ALL_POLICIES = ("cal:oracle-mid(tc=20),oracle-mid(tc=5),oracle-mid(tc=1),extremum-only,"
                "learner-mid(bank),learner-interleave-B10(bank),learner-interleave-B1(bank)")


def test_documented_two_command_sequence(isolated_reproduction_dir, counting_calibrate,
                                         monkeypatch, capsys):
    """`cal:` then `delays`, exactly as the README documents, with nothing carried in."""
    delays = _stub_delay(monkeypatch)
    assert sid_run6s.main(["sid_run6s.py", ALL_POLICIES]) in (0, 1)
    out = capsys.readouterr().out
    assert "computed: 7, cached: 0" in out, out

    sid_run6s.main(["sid_run6s.py", "delays"])
    out = capsys.readouterr().out
    assert "thresholds from this run's cal stage" in out, out
    assert "no thresholds available" not in out
    assert len(delays) == 15, f"expected 15 delay measurements, got {len(delays)}"
    assert "computed: 15, cached: 0" in out, out


def test_delays_refuses_thresholds_from_a_different_run(isolated_reproduction_dir,
                                                        counting_calibrate, monkeypatch, capsys):
    """Thresholds are a required output of THIS run, not state someone left on disk."""
    _stub_delay(monkeypatch)
    sid_run6s.main(["sid_run6s.py", ALL_POLICIES])
    capsys.readouterr()

    state_path = isolated_reproduction_dir / "res6_policies.json"
    state = json.loads(state_path.read_text())
    assert state["meta"]["run_id"], "cal output carries no run identity"
    state["meta"]["numpy"] = "0.0.0-from-another-machine"
    state_path.write_text(json.dumps(state))

    rc = sid_run6s.main(["sid_run6s.py", "delays"])
    err = capsys.readouterr().err
    assert rc == 2, "a mismatched threshold file must be refused, not consumed"
    assert "not this run's cal output" in err, err
    assert "numpy" in err, err


@pytest.mark.parametrize("field", sid_repro.IDENTITY_FIELDS)
def test_delays_refuses_on_every_bound_identity_field(isolated_reproduction_dir,
                                                      counting_calibrate, monkeypatch,
                                                      capsys, field):
    """Parametrised over IDENTITY_FIELDS itself, so a new bound field cannot go untested.

    machine/platform/blas matter as much as the library versions: identical pins on a
    different architecture, or under binary translation, are a different numerical stack.
    """
    _stub_delay(monkeypatch)
    sid_run6s.main(["sid_run6s.py", ALL_POLICIES])
    capsys.readouterr()
    p = isolated_reproduction_dir / "res6_policies.json"
    state = json.loads(p.read_text())
    state["meta"][field] = "mutated-for-this-test"
    p.write_text(json.dumps(state))
    assert sid_run6s.main(["sid_run6s.py", "delays"]) == 2, f"{field} mismatch was accepted"
    assert field in capsys.readouterr().err


@pytest.mark.parametrize("field", sid_repro.IDENTITY_FIELDS)
def test_delays_refuses_when_a_bound_field_is_absent(isolated_reproduction_dir,
                                                     counting_calibrate, monkeypatch,
                                                     capsys, field):
    """Fail closed: a missing identity field must not read as 'compatible'."""
    _stub_delay(monkeypatch)
    sid_run6s.main(["sid_run6s.py", ALL_POLICIES])
    capsys.readouterr()
    p = isolated_reproduction_dir / "res6_policies.json"
    state = json.loads(p.read_text())
    del state["meta"][field]
    p.write_text(json.dumps(state))
    assert sid_run6s.main(["sid_run6s.py", "delays"]) == 2, f"absent {field} was accepted"
    assert field in capsys.readouterr().err


def test_delays_refuses_a_changed_configuration_field(isolated_reproduction_dir,
                                                      counting_calibrate, monkeypatch, capsys):
    """A threshold measured at a different gamma is not this run's threshold."""
    _stub_delay(monkeypatch)
    sid_run6s.main(["sid_run6s.py", ALL_POLICIES])
    capsys.readouterr()
    p = isolated_reproduction_dir / "res6_policies.json"
    state = json.loads(p.read_text())
    state["meta"]["config"]["gamma"] = 1.0e4
    state["meta"]["config_digest"] = sid_repro.config_digest(state["meta"]["config"])
    p.write_text(json.dumps(state))
    assert sid_run6s.main(["sid_run6s.py", "delays"]) == 2
    err = capsys.readouterr().err
    assert "config_digest" in err and "gamma" in err, err


def test_delays_refuses_a_changed_policy_set(isolated_reproduction_dir, counting_calibrate,
                                             monkeypatch, capsys):
    """The digest must move when the policy set does, even if every other field matches."""
    _stub_delay(monkeypatch)
    sid_run6s.main(["sid_run6s.py", ALL_POLICIES])
    capsys.readouterr()
    p = isolated_reproduction_dir / "res6_policies.json"
    state = json.loads(p.read_text())
    state["meta"]["config"]["policies"] = state["meta"]["config"]["policies"][:-1]
    state["meta"]["config_digest"] = sid_repro.config_digest(state["meta"]["config"])
    p.write_text(json.dumps(state))
    assert sid_run6s.main(["sid_run6s.py", "delays"]) == 2
    assert "config.policies" in capsys.readouterr().err


def test_identity_is_not_silently_narrowed():
    """The four platform facts must stay bound; dropping one would weaken the gate quietly."""
    for field in ("machine", "platform", "blas", "scipy"):
        assert field in sid_repro.IDENTITY_FIELDS, field
    meta = sid_repro.run_metadata({"a": 1})
    assert set(sid_repro.IDENTITY_FIELDS) <= set(meta), "run_metadata omits a bound field"
    assert meta["config_digest"] == sid_repro.config_digest({"a": 1})
    assert sid_repro.incompatibilities(meta, meta) == []
    assert sid_repro.blas_is_identified({"blas": "unknown"}) is False
    assert sid_repro.blas_is_identified({"blas": "blas 3.9.0"}) is True


def test_resume_skips_measured_delay_rows_only(isolated_reproduction_dir, counting_calibrate,
                                               monkeypatch, capsys):
    """--resume reuses delay rows already measured; it does not turn cal back into cache."""
    delays = _stub_delay(monkeypatch)
    sid_run6s.main(["sid_run6s.py", ALL_POLICIES])
    sid_run6s.main(["sid_run6s.py", "delays"])
    capsys.readouterr()
    assert len(delays) == 15

    # drop one measured row; --resume must recompute exactly that one
    p = isolated_reproduction_dir / "res6_policies.json"
    state = json.loads(p.read_text())
    del state["delays"]["20.0"]["extremum-only"]
    p.write_text(json.dumps(state))

    delays.clear()
    sid_run6s.main(["sid_run6s.py", "delays", "--resume"])
    out = capsys.readouterr().out
    assert len(delays) == 1, f"--resume recomputed {len(delays)} rows, expected 1"
    assert "computed: 1, cached: 14" in out, out


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
