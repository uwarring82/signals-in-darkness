"""Implementation tests for analysis/runs/sid_run13.py (Gate 2).

No campaign phase is run. Refusals are shown on the command line and as pure functions; the
Gate-3 and Gate-4 orchestration runs only on a tiny synthetic plan (synthetic points, seeds,
grids and lengths) into a temporary directory, to show that deadlines, admission, blindness and
artifact digests behave as the protocol states.
"""
import copy
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "runs"))
import sid_run13 as run13  # noqa: E402

DOC = json.loads((ROOT / "analysis" / "protocol_F.json").read_text())
DRIVER = ROOT / "analysis" / "runs" / "sid_run13.py"
OUTPUTS = [ROOT / rel for rel in DOC["outputs"].values()]
GOOD_FACTS = {"python": "3.12.14", "machine": "arm64", "numpy": "2.4.4", "scipy": "1.17.1",
              "libblas_build": "11_h51639a9_openblas", "libopenblas_build": "openmp_h5e6e99c_1"}
ONES = {name: "1" for name in run13.THREAD_VARIABLES}
PROV = {"git_clean": True, "git_revision": "0" * 40, "protocol_digest": DOC["digest"]}


class StepClock:
    def __init__(self, dt):
        self.t, self.dt = 0.0, dt

    def __call__(self):
        self.t += self.dt
        return self.t


def _cli(args, **env):
    environment = {**os.environ, **ONES, **env}
    return subprocess.run([sys.executable, str(DRIVER), *args], capture_output=True, text=True, timeout=120,
                          cwd=str(ROOT), env=environment)


def _snapshot():
    return {str(p): (p.stat().st_mtime_ns if p.exists() else None) for p in OUTPUTS}


# ------------------------------------------------------------------------------------------- command line
def test_phase_is_required_and_has_no_default():
    for args in ([], ["--phase"], ["--phase", "campaign"], ["--phase", "preflight", "--extra"], ["--ph", "preflight"]):
        proc = _cli(args)
        assert proc.returncode == 2, (args, proc.stderr)


@pytest.mark.parametrize("phase", ["checks-and-pilots", "evaluation", "preflight"])
def test_a_thread_variable_other_than_one_is_refused_and_nothing_is_written(phase):
    before = _snapshot()
    proc = _cli(["--phase", phase], OMP_NUM_THREADS="2")
    assert proc.returncode == 2
    assert "OMP_NUM_THREADS is '2'" in proc.stderr and "nothing measured, nothing written" in proc.stderr
    assert _snapshot() == before


def test_thread_refusal_happens_before_numpy_is_imported():
    script = (f"import sys; sys.path.insert(0, {str(ROOT / 'analysis' / 'runs')!r}); import sid_run13; "
              "code = sid_run13.main(['--phase', 'preflight']); "
              "assert code == 2, code; assert 'numpy' not in sys.modules, 'numpy was imported'")
    env = {**os.environ, **ONES, "VECLIB_MAXIMUM_THREADS": "4"}
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120,
                          cwd=str(ROOT), env=env)
    assert proc.returncode == 0, proc.stderr
    assert "VECLIB_MAXIMUM_THREADS is '4'" in proc.stderr


# ------------------------------------------------------------------------------------------- refusal functions
def test_thread_refusals_cover_all_five_variables():
    assert run13.thread_refusals(ONES) == []
    assert len(run13.thread_refusals({})) == 5
    for name in run13.THREAD_VARIABLES:
        reasons = run13.thread_refusals({**ONES, name: "8"})
        assert len(reasons) == 1 and name in reasons[0]


@pytest.mark.parametrize("key, value", [("python", "3.12.0"), ("machine", "x86_64"), ("numpy", "2.4.3"),
                                        ("scipy", "1.17.0"), ("libblas_build", "20_osxarm64_mkl"),
                                        ("libblas_build", None), ("numpy", None)])
def test_stack_refusals(key, value):
    assert run13.stack_refusals(GOOD_FACTS) == []
    reasons = run13.stack_refusals({**GOOD_FACTS, key: value})
    assert len(reasons) == 1


def test_libblas_build_is_read_from_conda_metadata(tmp_path):
    meta = tmp_path / "conda-meta"
    meta.mkdir()
    (meta / "libblas-3.11.0-11_h51639a9_openblas.json").write_text(json.dumps({"build": "11_h51639a9_openblas"}))
    (meta / "libblas-dev-0.json").write_text("{}")                     # not the libblas package
    assert run13.conda_build(str(tmp_path), "libblas") == "11_h51639a9_openblas"
    assert run13.conda_build(str(tmp_path), "libopenblas") is None


def test_tree_refusals_on_a_real_repository(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)
    git("init")
    assert run13.tree_refusals(run13.git_state(tmp_path)) != []           # no revision yet
    (tmp_path / "a.txt").write_text("a")
    git("add", "a.txt")
    git("commit", "-m", "a")
    assert run13.tree_refusals(run13.git_state(tmp_path)) == []
    (tmp_path / "b.txt").write_text("b")
    assert run13.tree_refusals(run13.git_state(tmp_path)) == [run13.DIRTY_TREE]
    assert run13.tree_refusals({"revision": None, "porcelain": ""}) != []


def test_protocol_refusals_accept_the_frozen_file_and_refuse_drafts_and_tampering():
    assert run13.protocol_refusals(DOC) == []
    assert run13.digest_of(DOC) == run13.FROZEN_DIGEST
    draft = {**DOC, "status": "DRAFT for review", "digest": None}
    reasons = run13.protocol_refusals(draft)
    assert any("DRAFT" in r for r in reasons) and any("digest" in r for r in reasons)
    tampered = copy.deepcopy(DOC)
    tampered["constants"]["t_0975_df15"] = 2.2
    assert run13.protocol_refusals(tampered) == ["the protocol content does not recompute to the frozen digest"]
    tampered["digest"] = run13.digest_of(tampered)
    assert any("not the frozen" in r for r in run13.protocol_refusals(tampered))
    unfrozen = {**DOC, "status": "SUPERSEDED"}
    assert any("not FROZEN" in r for r in run13.protocol_refusals(unfrozen))
    assert run13.protocol_refusals(None) != []


def test_implementation_refusals_pass_for_this_library_and_catch_a_wrong_comparator():
    facts = run13.stack_facts()
    assert run13.implementation_refusals(DOC, facts) == []
    _, sa, _ = run13.numerical_imports()
    wrong = copy.deepcopy(DOC)
    wrong["design_evidence"]["points"]["E4"]["comparators"]["K3"] *= 1 + 1e-11
    assert run13.design_evidence_refusals(wrong, sa) and "E4 K3" in run13.design_evidence_refusals(wrong, sa)[0]


def test_existing_outputs_are_refused(tmp_path):
    existing = tmp_path / "res13_F_pilot.json"
    existing.write_text("{}")
    assert run13.output_refusals([tmp_path / "absent.json"]) == []
    assert len(run13.output_refusals([existing, tmp_path / "absent.json"])) == 1


def _gate3_artifact(run_id="r1", **changes):
    art = {"record": "x", "protocol_digest": run13.FROZEN_DIGEST, "provenance": {"git_clean": True},
           "run": {"phase": "checks-and-pilots", "run_id": run_id, "complete": True, "run_wall_seconds": 10.0},
           "points": {}}
    for key, value in changes.items():
        art[key] = value
    art["digest"] = run13.digest_of(art)
    return art


def test_gate3_input_refusals():
    good = _gate3_artifact()
    assert run13.gate3_input_refusals(good, _gate3_artifact()) == []
    edited = dict(good, points={"E3": {"status": "CHECKS_PASSED"}})
    cases = [
        (None, good),
        (edited, good),
        (_gate3_artifact(protocol_digest="0123456789abcdef"), good),
        (_gate3_artifact(provenance={"git_clean": False}), good),
        (_gate3_artifact(run={**good["run"], "complete": False}), _gate3_artifact(run={**good["run"], "complete": False})),
        (_gate3_artifact(run={**good["run"], "phase": "evaluation"}), good),
        (good, _gate3_artifact(run_id="r2")),
    ]
    for checks, pilot in cases:
        assert run13.gate3_input_refusals(checks, pilot) != [], (checks, pilot)


def test_implementation_change_is_refused_between_gates():
    head = run13.git_state()["revision"]
    assert run13.implementation_change_refusals(head) == []
    assert any("protocol_F.json changed" in r for r in run13.implementation_change_refusals("99cb09a"))
    assert run13.implementation_change_refusals("not-a-revision") != []


# ------------------------------------------------------------------------------------------- plan, budget, admission
def test_plan_reads_the_frozen_protocol():
    run13.numerical_imports()
    plan = run13.plan_from_protocol(DOC)
    assert plan["eval_grid"] == "M241_L7" and plan["grids"] == ["M121_L5", "M121_L7", "M241_L5", "M241_L7"]
    assert plan["nc1"] == {"seed": 15900, "N": 200000, "grids": ["M121_L5", "M241_L7"]}
    assert (plan["n_sim"], plan["n_pilot"]) == (250000, 125000)
    assert plan["seeds"]["pilot"]["E3"][0] == 13040 and plan["seeds"]["numerical_checks"]["E1"][15] == 15015
    assert run13.resolve(plan["record_length"], 1000) == 52000
    assert plan["nc6_pairs"] == [("M241_L7_W_history", "M241_L7_2W_history")]
    assert len(plan["nc5_pairs"]) == 3 and all(b == "M241_L7_W_history" for _, b in plan["nc5_pairs"])
    # NC2 8 x 250000; NC5/NC6 8 x (52000 simulated + 52000 + 4 x 51000 filtered); pilot 16 x 126000
    assert run13.gate3_units(plan, "E3", 1000) == 8 * 250000 + 8 * (52000 + 52000 + 4 * 51000) + 16 * 126000


def test_aggregate_clock_counts_each_run_once():
    a = {"run": {"run_id": "g3", "run_wall_seconds": 100.0}}
    b = {"run": {"run_id": "g3", "run_wall_seconds": 101.0}}
    c = {"run": {"run_id": "g4", "run_wall_seconds": 50.0}}
    assert run13.spent_seconds([a, b, c]) == 151.0
    assert run13.spent_seconds([]) == 0.0


def test_evaluation_admission_rules():
    cap = 7200
    ok = run13.evaluation_admission
    assert ok(("E3",), {"E3": 7200}, {"E3": True}, 7200, cap) == (True, None)
    assert not ok(("E3",), {"E3": 7201}, {"E3": True}, 28800, cap)[0]
    assert not ok(("E3",), {"E3": 100}, {"E3": True}, 99, cap)[0]
    assert not ok(("E3",), {}, {"E3": False}, 28800, cap)[0]
    pair = ("E1", "E2")
    assert ok(pair, {"E1": 3000, "E2": 3000}, {"E1": True, "E2": True}, 6000, cap)[0]
    assert not ok(pair, {"E1": 3000, "E2": 3000}, {"E1": True, "E2": True}, 5999, cap)[0]
    assert not ok(pair, {"E1": 7300, "E2": 10}, {"E1": True, "E2": True}, 28800, cap)[0]
    assert not ok(pair, {"E1": 10}, {"E1": True, "E2": False}, 28800, cap)[0]


# ------------------------------------------------------------------------------------------- tiny synthetic orchestration
def _tiny_plan():
    run13.numerical_imports()
    plan = run13.plan_from_protocol(DOC)
    plan["points"] = {name: {"C": 0.6, "s": 0.8, "u": 0.25, "c_over_tau_c": 0.5} for name in run13.POINTS}
    plan["points"]["N0"] = {"C": 0.8, "s": 1.0, "u": 0.0, "c_over_tau_c": 0.1}
    plan["nc1"] = {"seed": 202, "N": 5000, "grids": ["M41_L5", "M61_L7"]}
    plan["eval_grid"], plan["grids"] = "M61_L7", ["M61_L7"]
    plan["check_passes"] = {k: {"grid": "M61_L7", "first": v["first"]} for k, v in plan["check_passes"].items()}
    plan["record_length"] = {"W_multiple": 2, "plus": 2000}
    plan["window"] = {"first": {"W_multiple": 2, "plus": 1}, "last": {"W_multiple": 2, "plus": 2000}}
    plan["n_sim"], plan["n_pilot"] = 20000, 2000
    plan["seeds"] = {phase: {name: [base + 20 * p + r for r in range(16)] for p, name in enumerate(run13.POINTS)}
                     for phase, base in (("pilot", 913000), ("evaluation", 914000), ("numerical_checks", 915000))}
    return plan


def _paths(tmp):
    return {key: tmp / Path(rel).name for key, rel in DOC["outputs"].items()}


@pytest.fixture(scope="module")
def tiny_gate3(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("gate3")
    plan = _tiny_plan()
    checks, pilots = run13.run_checks_and_pilots(DOC, plan, PROV, _paths(tmp), spent=0.0)
    return plan, tmp, checks, pilots


def _keys(obj):
    if isinstance(obj, dict):
        return set(obj) | set().union(*(_keys(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(_keys(v) for v in obj)) if obj else set()
    return set()


def test_tiny_gate3_run_writes_verifiable_blind_artifacts(tiny_gate3):
    plan, tmp, checks, pilots = tiny_gate3
    on_disk = {k: json.loads(p.read_text()) for k, p in _paths(tmp).items() if k != "evaluation"}
    assert run13.gate3_input_refusals(on_disk["numerical_checks"], on_disk["pilot"]) == []
    assert checks["NC1"]["status"] == "PASSED" and checks["NC1"]["committed_code_tie"]["pass"]
    for name in run13.POINTS:
        assert checks["points"][name]["status"] == "CHECKS_PASSED", checks["points"][name]
        pilot = pilots["points"][name]
        assert pilot["status"] in ("PILOT_COMPLETE", "PILOT_UNSTABLE")
        assert [p["shots"] for p in pilot["per_seed"]] == [1000 + 2000] * 16
        assert math.isclose(pilot["t_step"], sum(p["wall_seconds"] for p in pilot["per_seed"]) / 48000)
    assert not any("mean" in key for key in _keys(on_disk["pilot"]))       # pilot: no means at all
    assert {k for k in _keys(on_disk["numerical_checks"]) if "mean" in k} <= {"mean_over_seeds", "mean_paired_difference"}
    assert checks["points"]["E4"]["admission"]["predicted_seconds"] is not None     # E3 measured the rate


def test_gate3_incomplete_NC1_or_failed_NC1_blocks_every_point(tmp_path):
    plan = _tiny_plan()
    called = []

    def point(*args):
        called.append(args)
        raise AssertionError("no point may run")

    plan_zero = dict(plan, gate3_deadline_seconds=0)
    checks, pilots = run13.run_checks_and_pilots(DOC, plan_zero, PROV, _paths(tmp_path), 0.0, steps={"point": point})
    assert checks["NC1"]["status"] == "INCOMPLETE"
    checks2, _ = run13.run_checks_and_pilots(DOC, plan, PROV, _paths(tmp_path), 0.0,
                                             steps={"nc1": lambda plan, deadline: {"pass": False}, "point": point})
    assert checks2["NC1"]["status"] == "FAILED"
    for c, p in ((checks, pilots), (checks2, None)):
        assert all(c["points"][n]["status"] == "BLOCKED_BY_NC1" for n in run13.POINTS)
    assert not called and checks["run"]["complete"]


def test_gate3_deadline_marks_the_running_point_incomplete_and_later_points_not_attempted(tmp_path):
    plan = _tiny_plan()
    checks, pilots = run13.run_checks_and_pilots(DOC, plan, PROV, _paths(tmp_path), 0.0, clock=StepClock(400.0),
                                                 steps={"nc1": lambda plan, deadline: {"pass": True}})
    assert checks["points"]["E3"]["status"] == "INCOMPLETE" and checks["points"]["E3"]["incomplete_step"]
    assert all(checks["points"][n]["status"] == "NOT_ATTEMPTED" for n in ("E4", "E5", "E1", "E2"))
    assert checks["run"]["deadline_seconds"] == 1800 and checks["run"]["complete"]


def test_gate3_deadline_never_exceeds_the_remaining_aggregate_budget(tmp_path):
    plan = _tiny_plan()
    checks, _ = run13.run_checks_and_pilots(DOC, plan, PROV, _paths(tmp_path), spent=28800 - 5.0,
                                            steps={"nc1": lambda plan, deadline: {"pass": False}})
    assert checks["run"]["deadline_seconds"] == 5.0


def test_gate3_prediction_exceeding_the_time_left_is_not_attempted_and_E1_E2_go_together(tmp_path):
    plan = _tiny_plan()

    def point(plan, name, nc3, deadline, clock):
        clock()
        return {"status": "CHECKS_PASSED"}, {"status": "PILOT_COMPLETE"}, 1

    checks, _ = run13.run_checks_and_pilots(DOC, plan, PROV, _paths(tmp_path), 0.0, clock=StepClock(100.0),
                                            steps={"nc1": lambda plan, deadline: {"pass": True}, "point": point})
    assert checks["points"]["E3"]["status"] == "CHECKS_PASSED"
    assert checks["points"]["E4"]["status"] == "NOT_ATTEMPTED"
    assert checks["points"]["E4"]["admission"]["predicted_seconds"] > checks["points"]["E4"]["admission"]["seconds_left_before_deadline"]
    assert checks["points"]["E1"]["status"] == checks["points"]["E2"]["status"] == "NOT_ATTEMPTED"


def _evaluation_inputs(tiny_gate3, t_step):
    plan, tmp, checks, pilots = tiny_gate3
    checks, pilots = copy.deepcopy(checks), copy.deepcopy(pilots)
    for name in run13.POINTS:
        if name != "E3":
            pilots["points"][name]["status"] = "PILOT_UNSTABLE"            # fixture: only E3 is eligible
    pilots["points"]["E3"].update(status="PILOT_COMPLETE", U=1e-15, t_step=t_step)   # n_e = n_p
    for art in (checks, pilots):
        art["digest"] = run13.digest_of(art)
    return plan, checks, pilots


def test_tiny_evaluation_applies_the_shot_rule_stop_rule_verdicts_and_closure(tiny_gate3, tmp_path):
    plan, checks, pilots = _evaluation_inputs(tiny_gate3, t_step=1e-3)
    art = run13.run_evaluation(DOC, plan, PROV, checks, pilots, tmp_path / "res13_F_evaluation.json", spent=0.0)
    e3 = art["points"]["E3"]
    assert e3["status"] == "EVALUATED" and e3["n_e"] == 2000 and len(e3["per_seed"]) == 16
    assert math.isclose(e3["predicted_seconds"], 1.10 * 16 * (1000 + 2000) * 1e-3)
    assert math.isclose(e3["stop_seconds"], 1.25 * e3["predicted_seconds"])
    assert set(e3["verdicts"].values()) <= {"VALIDATED", "FAILED", "UNRESOLVED"}
    for name in ("E4", "E5", "E1", "E2"):
        assert art["points"][name]["status"] == "NO_EVALUATION"
        assert set(art["points"][name]["verdicts"].values()) == {"NO_VERDICT"}
    assert art["closure"]["roadmap_F"] == "OPEN" and "Roadmap F remains OPEN." in art["closure"]["wording"]
    assert not any(v["validated_at_both"] for v in art["closure"]["C08_boundary"].values())
    on_disk = json.loads((tmp_path / "res13_F_evaluation.json").read_text())
    assert on_disk["digest"] == run13.digest_of(on_disk) and on_disk["run"]["complete"]
    assert on_disk["inputs"]["pilot_digest"] == pilots["digest"]


def test_tiny_evaluation_that_reaches_its_stop_is_incomplete_without_verdict(tiny_gate3, tmp_path):
    plan, checks, pilots = _evaluation_inputs(tiny_gate3, t_step=1e-3)
    art = run13.run_evaluation(DOC, plan, PROV, checks, pilots, tmp_path / "res13_F_evaluation.json", spent=0.0,
                               clock=StepClock(10.0))
    e3 = art["points"]["E3"]
    assert e3["status"] == "INCOMPLETE" and set(e3["verdicts"].values()) == {"NO_VERDICT"}
    assert "interval" not in e3 and art["closure"]["k1_verdicts"]["E3"] == "NO_VERDICT"
