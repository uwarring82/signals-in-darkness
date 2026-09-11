"""The manifest-driven schedule factory must reproduce the implementations it replaces.

Roadmap C's ladder ranges over thirteen candidates. Six were measured in roadmap B by two
SEPARATE hard-coded implementations -- sid_policies.build_policies for the constants and
interleaves, sid_run8.run_batch_age for the age-based switches -- and adding the five new
members to both lists would have let the executed class drift from the manifest that froze it.
One factory now builds every member from analysis/schedule_class_C.json.

Replacing a measured implementation is only safe if the replacement reproduces it EXACTLY, so
these tests compare PER-REPLICATE stopping times, not means. A mean can agree while the runs
underneath differ, and the ladder reuses roadmap B's per-replicate outputs.
"""
import hashlib, json, pathlib, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
sys.path.insert(0, str(ROOT / "analysis" / "runs"))
import sid_policies as P            # noqa: E402
import sid_run8 as R8               # noqa: E402

CLASS_PATH = ROOT / "analysis" / "schedule_class_C.json"
H, MAXS, R, SEED = 1.5, 60_000, 24, 4242

# Per-replicate digests of the sched(n) policies, pinned when run_batch gained segment-age
# tracking. Age tracking must be INERT for schedules that do not ask for it: these are
# roadmap B's measured policies and their numbers are published.
GOLDEN = {
    "pilot|extremum-only": "293c4fab6f5ea634",
    "pilot|learner-interleave-B1(bank)": "56cab1d6c8ecf4ea",
    "pilot|learner-interleave-B10(bank)": "73a3aba710ec1dfb",
    "pilot|learner-mid(bank)": "80b97e19eca8da63",
    "pilot|oracle-mid(tc=1)": "5ebb996bd0633964",
    "pilot|oracle-mid(tc=20)": "0491aa03d119228b",
    "pilot|oracle-mid(tc=5)": "35012189766012a8",
    "stress|extremum-only": "d393f6956f89342e",
    "stress|learner-interleave-B1(bank)": "c1f46cfffcba05e5",
    "stress|learner-interleave-B10(bank)": "d635accbdba48cab",
    "stress|learner-mid(bank)": "af66f6e3b5800bb8",
    "stress|oracle-mid(tc=1)": "a640201d165dc7cd",
    "stress|oracle-mid(tc=20)": "4b354b91d578968b",
    "stress|oracle-mid(tc=5)": "13fa3d4e4c75c456",
}
OPS = (("pilot", P.PILOT), ("stress", P.STRESS))


def _digest(v):
    return hashlib.sha256(np.asarray(v).tobytes()).hexdigest()[:16]


def _pair(bank, sched):
    """Null and post-change stopping times under one shared seed."""
    return np.concatenate([P.run_batch(bank, sched, None, H, R, SEED, MAXS, True),
                           P.run_batch(bank, sched, 5.0, H, R, SEED, MAXS, False)])


def test_factory_builds_exactly_the_frozen_manifest():
    cls = json.loads(CLASS_PATH.read_text())
    built = P.frozen_schedule_class(CLASS_PATH)
    assert len(built) == cls["size"] == 11
    declared = [s["name"] for specs in cls["class"].values() for s in specs]
    assert [n for n, _ in built] == declared


def test_age_tracking_is_inert_for_sched_n_policies():
    """run_batch's age counter must not perturb any policy that does not read it."""
    for opname, op in OPS:
        policies, _, _ = P.build_policies(op)
        for name, (bank, sched) in policies.items():
            v = _pair(bank, sched)
            key = f"{opname}|{name}"
            # A pin over an all-censored constant detects nothing. Assert the pin still
            # carries information before trusting that it agrees.
            assert len(set(v.tolist())) >= 30, f"{key} degenerated to a near-constant pin"
            assert _digest(v) == GOLDEN[key], f"{key} changed under the sched(n) path"


def test_switch_matches_the_separate_age_implementation():
    """Factory switch@B == sid_run8.run_batch_age, per replicate, on both streams."""
    for _, op in OPS:
        bank = P.Bank([1.0, 4.0, 10.0, 25.0], op)
        for B in (100, 300, 600, 1000, 3000):
            sched = P.schedule_from_spec("switch", {"name": f"switch@{B}", "age": B})
            for null, tcc in ((True, None), (False, 5.0), (False, 20.0)):
                a = P.run_batch(bank, sched, tcc, 3.0, R, 909, 4000, null)
                b = R8.run_batch_age(bank, B, tcc, 3.0, R, 909, 4000, null)
                assert np.array_equal(a, b), f"switch@{B} null={null} tcc={tcc}"


def test_constants_and_interleave_match_their_hard_coded_originals():
    for _, op in OPS:
        bank = P.Bank([1.0, 4.0, 10.0, 25.0], op)
        policies, _, _ = P.build_policies(op)
        cases = [
            (("constants", {"name": "mid", "theta": "THM"}), policies["learner-mid(bank)"][1]),
            (("constants", {"name": "ext", "theta": "THX"}), P.sched_ext),
            (("interleave", {"name": "interleave-B1", "block": 1}),
             policies["learner-interleave-B1(bank)"][1]),
            (("interleave", {"name": "interleave-B10", "block": 10}),
             policies["learner-interleave-B10(bank)"][1]),
        ]
        for (kind, spec), reference in cases:
            sched = P.schedule_from_spec(kind, spec)
            for null, tcc in ((True, None), (False, 5.0)):
                a = P.run_batch(bank, sched, tcc, 3.0, R, 313, 3000, null)
                b = P.run_batch(bank, reference, tcc, 3.0, R, 313, 3000, null)
                assert np.array_equal(a, b), f"{spec['name']} null={null}"


def test_phase_is_mandatory_for_every_seed_family():
    """A missing or unknown phase must raise, never fall back to a default stream."""
    for bad in ("calibration", "design", "", None, "Selection"):
        try:
            P.data_seed(bad, 5.0, 0)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"data_seed accepted phase {bad!r}")
    assert P.data_seed("selection", 5.0, 0) == 705
    assert P.data_seed("evaluation", 5.0, 7000) == 7205


def test_selection_and_evaluation_streams_are_disjoint():
    """The whole point of two streams is that no run is shared between them."""
    for off in (0, 7000):
        sel = {P.data_seed("selection", t, off) for t in (1.0, 5.0, 20.0)}
        ev = {P.data_seed("evaluation", t, off) for t in (1.0, 5.0, 20.0)}
        assert len(sel) == len(ev) == 3
        assert sel.isdisjoint(ev)
