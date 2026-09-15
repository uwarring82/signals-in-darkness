"""Roadmap F driver under the frozen protocol analysis/protocol_F.json (digest b7c09ce90f33c37b).

    python analysis/runs/sid_run13.py --phase preflight
    python analysis/runs/sid_run13.py --phase checks-and-pilots     # Gate 3
    python analysis/runs/sid_run13.py --phase evaluation            # Gate 4

The phase is required and has no default. Running a measuring phase needs that gate's own approval;
approving this driver approved neither. preflight measures nothing and writes nothing.

Refusals (exit 2; nothing measured, nothing written) follow execution_stack.refusal and hygiene:
  * any of the five thread variables other than 1 (checked before numpy is imported);
  * python, numpy or scipy other than the pins, a machine other than arm64, a libblas build
    without openblas;
  * a dirty tree, or a tree whose state cannot be read;
  * a DRAFT or unfrozen protocol, a digest other than b7c09ce90f33c37b, content that does not
    recompute to it, a protocol that does not match its builder, or a library that does not
    reproduce design_evidence (comparators to relative 1e-12, the contract);
  * an existing output for the phase: a rerun is a replacement and needs its own decision;
  * evaluation only: Gate-3 artifacts that are missing, do not recompute to their own digest, name
    another protocol digest, record an unfinished run or a dirty tree, come from different runs,
    or were produced by an implementation that has changed since.

The outputs lie in analysis/reproduction, which git ignores, so a clean tree cannot vouch for
them. Every res13 artifact therefore carries its own digest (the protocol's convention), and the
evaluation artifact records the digests of the Gate-3 artifacts it read.

Blindness: the pilot artifact records per-seed wall time and shots, S^2, vbar_10, vbar_20, the
bounds and t_step; never a per-seed mean, their average or a comparator ratio. NC5/NC6 record
paired differences only. Nothing prints a rate estimate before evaluation.

Gate-3 admission (implementation choice, for review): after the first point that runs filter
steps, the rate is (seconds spent on points) / (filter steps run: NC5/NC6 passes and pilot
shots). A later point's prediction is that rate times its NC2 shots, NC5/NC6 simulated shots,
NC5/NC6 filter steps and pilot shots, each counted as a unit. Simulation-only work is thereby
charged in the prediction but not credited in the rate, so the prediction errs long.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import uuid
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "analysis" / "protocol_F.json"
FROZEN_DIGEST = "b7c09ce90f33c37b"
PHASES = ("preflight", "checks-and-pilots", "evaluation")
PHASE_OUTPUTS = {"preflight": (), "checks-and-pilots": ("numerical_checks", "pilot"), "evaluation": ("evaluation",)}
THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                    "NUMEXPR_NUM_THREADS")
PINS = {"python": "3.12.14", "numpy": "2.4.4", "scipy": "1.17.1"}
MACHINE = "arm64"
POINTS = ("E1", "E2", "E3", "E4", "E5")
GROUPS = (("E3",), ("E4",), ("E5",), ("E1", "E2"))
COMPARATORS = ("K1", "K2", "K3", "K4")
IMPLEMENTATION_FILES = ("analysis/lib/sid_arma.py", "analysis/lib/sid_lib.py", "analysis/lib/sid_repro.py",
                        "analysis/runs/sid_run13.py", "analysis/protocol_F.json", "tools/build_protocol_F.py",
                        "analysis/diagnostics/review_F_plan.py")
DIRTY_TREE = ("refusing to measure from a dirty tree: the artifact would be attributed to a revision that does "
              "not describe the code that produced it")


# ------------------------------------------------------------------------------------------- refusals before numpy
def digest_of(obj):
    """The convention of tools/freeze_ladder_selections.py, which the protocol's digest uses."""
    return hashlib.sha256(json.dumps({k: v for k, v in obj.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def thread_refusals(environ):
    return [f"{name} is {environ.get(name)!r}; every thread variable must be '1' before numpy is imported"
            for name in THREAD_VARIABLES if environ.get(name) != "1"]


def conda_build(prefix, package):
    files = glob.glob(os.path.join(prefix, "conda-meta", f"{package}-[0-9]*.json"))
    if len(files) != 1:
        return None
    with open(files[0], encoding="utf-8") as f:
        return json.load(f).get("build")


def stack_facts(prefix=sys.prefix):
    facts = {"python": platform.python_version(), "machine": platform.machine()}
    for dist in ("numpy", "scipy"):
        try:
            facts[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            facts[dist] = None
    facts["libblas_build"] = conda_build(prefix, "libblas")
    facts["libopenblas_build"] = conda_build(prefix, "libopenblas")
    return facts


def stack_refusals(facts):
    out = [f"{key} is {facts.get(key)!r}, not the pinned {pin}" for key, pin in PINS.items() if facts.get(key) != pin]
    if facts.get("machine") != MACHINE:
        out.append(f"machine is {facts.get('machine')!r}, not {MACHINE}")
    build = facts.get("libblas_build")
    if not build or "openblas" not in build:
        out.append(f"libblas build is {build!r}; an OpenBLAS build is required")
    return out


def git_state(root=ROOT):
    def git(*args):
        try:
            p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return p.stdout.strip() if p.returncode == 0 else None
    return {"revision": git("rev-parse", "HEAD"), "porcelain": git("status", "--porcelain")}


def tree_refusals(state):
    if state.get("revision") is None or state.get("porcelain") is None:
        return ["the git revision or tree state could not be read"]
    return [DIRTY_TREE] if state["porcelain"] else []


def protocol_refusals(doc):
    if not isinstance(doc, dict):
        return ["the protocol could not be read as a JSON object"]
    out = []
    status = doc.get("status")
    if not isinstance(status, str):
        out.append("the protocol has no status")
    elif status.startswith("DRAFT"):
        out.append("the protocol status is DRAFT")
    elif not status.startswith("FROZEN"):
        out.append(f"the protocol status {status[:40]!r} is not FROZEN")
    if doc.get("digest") != FROZEN_DIGEST:
        out.append(f"the protocol digest is {doc.get('digest')!r}, not the frozen {FROZEN_DIGEST}")
    elif digest_of(doc) != FROZEN_DIGEST:
        out.append("the protocol content does not recompute to the frozen digest")
    return out


def output_refusals(paths):
    return [f"{p} already exists; a rerun replaces a measurement and needs its own decision"
            for p in paths if Path(p).exists()]


def gate3_input_refusals(checks, pilot):
    out = []
    for label, art in (("numerical-checks", checks), ("pilot", pilot)):
        if not isinstance(art, dict):
            out.append(f"the {label} artifact is missing or unreadable")
            continue
        if art.get("digest") != digest_of(art):
            out.append(f"the {label} artifact does not recompute to its own digest")
        if art.get("protocol_digest") != FROZEN_DIGEST:
            out.append(f"the {label} artifact names protocol digest {art.get('protocol_digest')!r}")
        run = art.get("run") or {}
        if run.get("phase") != "checks-and-pilots":
            out.append(f"the {label} artifact was not written by the checks-and-pilots phase")
        if run.get("complete") is not True:
            out.append(f"the {label} artifact records an unfinished Gate-3 run")
        if (art.get("provenance") or {}).get("git_clean") is not True:
            out.append(f"the {label} artifact does not record a clean tree")
    if isinstance(checks, dict) and isinstance(pilot, dict) and \
            (checks.get("run") or {}).get("run_id") != (pilot.get("run") or {}).get("run_id"):
        out.append("the numerical-checks and pilot artifacts come from different runs")
    return out


def implementation_change_refusals(gate3_revision, root=ROOT):
    try:
        p = subprocess.run(["git", "-C", str(root), "diff", "--name-only", str(gate3_revision), "HEAD", "--",
                            *IMPLEMENTATION_FILES], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        p = None
    if p is None or p.returncode != 0:
        return [f"the implementation cannot be compared with the Gate-3 revision {gate3_revision!r}"]
    return [f"{name} changed since the Gate-3 run at {gate3_revision}" for name in p.stdout.split()]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------------------------------- refusals after numpy
def numerical_imports():
    for sub in ("analysis/lib", "tools"):
        path = str(ROOT / sub)
        if path not in sys.path:
            sys.path.insert(0, path)
    import numpy
    import build_protocol_F
    import sid_arma
    return numpy, sid_arma, build_protocol_F


def design_evidence_refusals(doc, sa, rel=1e-12):
    out = []
    for name, ev in doc["design_evidence"]["points"].items():
        p = doc["points"][name]
        par = sa.arma_parameters(p["s"], p["u"], p["c_over_tau_c"])
        values = {**{k: par[k] for k in ("F", "phi", "b", "v_x", "q")},
                  **sa.comparators(p["C"], p["s"], p["u"], p["c_over_tau_c"])}
        expected = {**{k: ev[k] for k in ("F", "phi", "b", "v_x", "q")}, **ev["comparators"]}
        for key, value in values.items():
            if not math.isclose(value, expected[key], rel_tol=rel, abs_tol=0.0):
                out.append(f"{name} {key} = {value!r} does not reproduce design_evidence {expected[key]!r} "
                           f"to relative {rel:g}")
        if par["W"] != ev["burn_in_W"]:
            out.append(f"{name} burn-in {par['W']} differs from design_evidence {ev['burn_in_W']}")
    return out


def implementation_refusals(doc, facts):
    numpy, sa, bp = numerical_imports()
    import scipy
    out = []
    if numpy.__version__ != facts.get("numpy") or scipy.__version__ != facts.get("scipy"):
        out.append("the imported numpy or scipy differs from the installed distribution")
    if bp.digest_of(doc) != FROZEN_DIGEST:
        out.append("the builder's digest convention does not give the frozen digest")
    if not bp.matches_builder(doc):
        out.append("the protocol does not match its builder")
    return out + design_evidence_refusals(doc, sa)


def provenance(doc, facts, git, environ):
    numpy = sys.modules["numpy"]
    import scipy
    try:
        build = numpy.show_config("dicts")
    except Exception:            # older numpy; the pinned stack always has it
        build = "unavailable"
    return {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "python": facts.get("python"),
            "machine": facts.get("machine"), "platform": platform.platform(), "numpy": numpy.__version__,
            "scipy": scipy.__version__, "numpy_build_configuration": build,
            "libblas_build": facts.get("libblas_build"), "libopenblas_build": facts.get("libopenblas_build"),
            "thread_variables": {v: environ.get(v) for v in THREAD_VARIABLES},
            "git_revision": git.get("revision"), "git_clean": git.get("porcelain") == "",
            "protocol_digest": doc.get("digest")}


# ------------------------------------------------------------------------------------------- plan and budget
def grid_of(label):
    M, L = label.split("_")
    return int(M[1:]), int(L[1:])


def resolve(offset, W):
    return offset["W_multiple"] * W + offset["plus"]


def plan_from_protocol(doc):
    """Everything a phase needs, read from the verified protocol (and the builder's constants,
    which matches_builder has tied to it)."""
    bp = sys.modules["build_protocol_F"]
    nc, budget = doc["numerical_checks"], doc["budget"]
    records = nc["records_for_NC5_NC6"]
    ev = doc["reference_filter"]["evaluation_grid"]
    return {
        "points": {n: {k: doc["points"][n][k] for k in ("C", "s", "u", "c_over_tau_c")} for n in POINTS + ("N0",)},
        "eval_grid": f"M{ev['M']}_L{ev['L']}",
        "grids": sorted({spec["grid"] for spec in records["passes"].values()}),
        "check_passes": {name: {"grid": spec["grid"], "first": spec["first_observation"]}
                         for name, spec in records["passes"].items()},
        "record_length": records["length"], "window": records["estimation_window"],
        "nc5_pairs": sorted(nc["NC5_grid"]["compare"].items()),
        "nc6_pairs": sorted(nc["NC6_finite_history"]["compare"].items()),
        "nc1": {"seed": doc["seeds"]["nesting_N0"][0], "N": bp.N_NEST, "grids": nc["NC1_nesting"]["grids"]},
        "n_sim": bp.N_SIM, "n_pilot": bp.N_PILOT,
        "seeds": {phase: doc["seeds"][phase] for phase in ("pilot", "evaluation", "numerical_checks")},
        "constants": doc["constants"], "delta": doc["verdicts"]["delta"], "kappa": doc["verdicts"]["kappa"],
        "aggregate_cap_seconds": budget["aggregate_cap_seconds"],
        "gate3_deadline_seconds": budget["gate3_deadline_seconds"],
        "point_cap_seconds": budget["point_cap_seconds"], "prediction_margin": budget["prediction_margin"],
    }


def point_tuple(plan, name):
    p = plan["points"][name]
    return p["C"], p["s"], p["u"], p["c_over_tau_c"]


def spent_seconds(artifacts):
    """The aggregate clock: every recorded run counted once, however many artifacts it wrote."""
    by_run = {}
    for art in artifacts:
        run = art["run"]
        by_run[run["run_id"]] = max(by_run.get(run["run_id"], 0.0), float(run["run_wall_seconds"]))
    return math.fsum(by_run.values())


def gate3_units(plan, name, W):
    """Predicted units for a point's NC2, NC5/NC6 and pilot (see the module docstring)."""
    length, last = resolve(plan["record_length"], W), resolve(plan["window"]["last"], W)
    filter_steps = sum(last - resolve(spec["first"], W) + 1 for spec in plan["check_passes"].values())
    return 8 * plan["n_sim"] + 8 * (length + filter_steps) + 16 * (W + plan["n_pilot"])


def evaluation_admission(group, predicted, eligible, remaining, point_cap):
    """(admitted, reason). A mandatory point: prediction <= point cap and <= remaining budget.
    E1 and E2: both eligible, each prediction <= point cap and their sum <= remaining budget."""
    if not all(eligible[p] for p in group):
        return False, ("E1 and E2 run only together, after both passed their checks and pilots" if len(group) > 1
                       else "the point did not pass its checks and pilot")
    if any(predicted[p] > point_cap for p in group):
        return False, "a prediction exceeds the point cap"
    if math.fsum(predicted[p] for p in group) > remaining:
        return False, "the prediction exceeds the remaining aggregate budget"
    return True, None


# ------------------------------------------------------------------------------------------- artifacts
def new_artifact(kind, doc, prov, run):
    return {"record": f"roadmap F {kind}, analysis/runs/sid_run13.py", "protocol": "analysis/protocol_F.json",
            "protocol_digest": doc["digest"], "provenance": prov, "run": run}


def write_artifact(path, art):
    import sid_repro
    art["digest"] = digest_of(art)
    sid_repro.write_json(str(path), art, indent=1)


def output_paths(doc):
    return {key: ROOT / rel for key, rel in doc["outputs"].items()}


# ------------------------------------------------------------------------------------------- Gate 3
def nc1_step(plan, deadline):
    numpy, sa, _ = numerical_imports()
    import sid_lib
    C, s, _, c = point_tuple(plan, "N0")
    W, N, seed = sa.burn_in(c), plan["nc1"]["N"], plan["nc1"]["seed"]
    deadline.check()
    y = sid_lib.simulate(C, s, sa.THETA, math.exp(-c), N, numpy.random.default_rng(seed))
    grids = {}
    for label in plan["nc1"]["grids"]:
        deadline.check()
        grids[label] = sa.nesting_check(y, C, s, c, *grid_of(label), W, deadline=deadline)
    deadline.check()
    tie = sa.committed_code_tie(C, s, c, N, seed, M=121)
    deadline.check()
    ok = all(g["pass"] and g["NC4"]["pass"] for g in grids.values()) and tie["pass"]
    return {"point": "N0", "seed": seed, "N": N, "W": W, "grids": grids, "committed_code_tie": tie,
            "NC4_on_N0_grids_enters_NC1": True, "pass": ok}


def point_step(plan, name, nc3, deadline, clock):
    """NC4, NC2, NC5/NC6 and the pilot for one point. Returns (check record, pilot record, filter steps run)."""
    numpy, sa, _ = numerical_imports()
    C, s, u, c = point_tuple(plan, name)
    par = sa.arma_parameters(s, u, c)
    W, K1 = par["W"], sa.comparators(C, s, u, c)["K1"]
    t7, constants = plan["constants"]["t_0975_df7"], plan["constants"]
    seeds = plan["seeds"]["numerical_checks"][name]
    rec, pilot, steps, step = {"W": W, "status": None}, {"status": "NO_PILOT"}, 0, "NC3"

    def failed(check):
        rec["status"], rec["failed_check"] = "NUMERICAL_CHECK_FAILED", check
        return rec, pilot, steps

    try:
        if not nc3["pass"]:
            return failed("NC3")
        step = "NC4"
        models = {}
        for label in plan["grids"]:
            deadline.check()
            models[label] = sa.arma_model(C, s, u, c, *grid_of(label))
        rec["NC4"] = {label: m["stationary"] for label, m in models.items()}
        if not all(r["pass"] for r in rec["NC4"].values()):
            return failed("NC4")

        step = "NC2"
        stats = []
        for seed in seeds[8:16]:
            _, eps = sa.simulate_window_record(C, s, u, c, plan["n_sim"], numpy.random.default_rng(seed),
                                               return_phase=True, deadline=deadline)
            stats.append(sa.simulator_statistics(eps))
        rec["NC2"] = {"seeds": seeds[8:16], "shots_per_seed": plan["n_sim"],
                      **sa.simulator_check(stats, s, par["F"], par["phi"])}
        if not rec["NC2"]["pass"]:
            return failed("NC2")

        step = "NC5_NC6"
        length = resolve(plan["record_length"], W)
        first, last = resolve(plan["window"]["first"], W), resolve(plan["window"]["last"], W)
        pairs = plan["nc5_pairs"] + plan["nc6_pairs"]
        diffs = {pair: [] for pair in pairs}
        for seed in seeds[0:8]:
            y = sa.simulate_window_record(C, s, u, c, length, numpy.random.default_rng(seed), deadline=deadline)
            means = {}                                   # window means stay in memory: never recorded
            for pass_name, spec in plan["check_passes"].items():
                start = resolve(spec["first"], W)
                means[pass_name] = sa.pass_window_mean(y, models[spec["grid"]], start, first, last, deadline)
                steps += last - start + 1
            for a, b in pairs:
                diffs[(a, b)].append(means[a] - means[b])
        window = {"seeds": seeds[0:8], "record_length": length, "window": [first, last]}
        rec["NC5"] = {**window, "pairs": {f"{a} - {b}": sa.paired_criterion(diffs[(a, b)], K1, t7)
                                          for a, b in plan["nc5_pairs"]}}
        rec["NC6"] = {**window, "pairs": {f"{a} - {b}": sa.paired_criterion(diffs[(a, b)], K1, t7)
                                          for a, b in plan["nc6_pairs"]}}
        for check in ("NC5", "NC6"):
            if not all(r["pass"] for r in rec[check]["pairs"].values()):
                return failed(check)
        rec["status"] = "CHECKS_PASSED"

        step = "pilot"
        pilot = {"status": "INCOMPLETE"}
        summaries, per_seed = [], []
        for seed in plan["seeds"]["pilot"][name]:
            t = clock()
            y = sa.simulate_window_record(C, s, u, c, W + plan["n_pilot"], numpy.random.default_rng(seed),
                                          deadline=deadline)
            summaries.append(sa.seed_summary(sa.arma_filter(y, models[plan["eval_grid"]], burn_in=W,
                                                            deadline=deadline)))
            per_seed.append({"seed": seed, "wall_seconds": clock() - t, "shots": W + plan["n_pilot"]})
            steps += W + plan["n_pilot"]
        bound = sa.pilot_bound(summaries, constants)
        pilot = {"status": "PILOT_COMPLETE" if bound["stable"] else "PILOT_UNSTABLE", "grid": plan["eval_grid"],
                 "W": W, "n_p": plan["n_pilot"], "per_seed": per_seed, **bound,
                 "t_step": math.fsum(p["wall_seconds"] for p in per_seed) / sum(p["shots"] for p in per_seed)}
    except sa.DeadlineReached:
        rec["status"], rec["incomplete_step"] = "INCOMPLETE", step
        if step == "pilot":
            pilot = {"status": "INCOMPLETE"}
    return rec, pilot, steps


def run_checks_and_pilots(doc, plan, prov, paths, spent, clock=time.monotonic, steps=None):
    _, sa, _ = numerical_imports()
    steps = {"nc1": nc1_step, "point": point_step, **(steps or {})}
    t0 = clock()
    remaining = plan["aggregate_cap_seconds"] - spent
    deadline_seconds = max(0.0, min(plan["gate3_deadline_seconds"], remaining))
    deadline = sa.Deadline(deadline_seconds, clock)
    run = {"phase": "checks-and-pilots", "run_id": uuid.uuid4().hex, "spent_before_seconds": spent,
           "remaining_aggregate_at_start_seconds": remaining, "deadline_seconds": deadline_seconds,
           "run_wall_seconds": 0.0, "complete": False}
    checks = {**new_artifact("numerical checks", doc, prov, run), "NC1": None, "NC3": {}, "points": {}}
    pilots = {**new_artifact("pilots", doc, prov, run), "points": {}}

    def save(complete=False):
        run["run_wall_seconds"], run["complete"] = clock() - t0, complete
        write_artifact(paths["numerical_checks"], checks)
        write_artifact(paths["pilot"], pilots)

    try:
        nc1 = steps["nc1"](plan, deadline)
        checks["NC1"] = {**nc1, "status": "PASSED" if nc1["pass"] else "FAILED"}
    except sa.DeadlineReached:
        checks["NC1"] = {"status": "INCOMPLETE"}
    checks["NC3"] = {name: sa.series_convergence_check(*point_tuple(plan, name)) for name in POINTS}
    save()

    point_seconds, filter_steps = 0.0, 0
    for group in GROUPS:
        if checks["NC1"]["status"] != "PASSED":
            for name in group:
                checks["points"][name] = {"status": "BLOCKED_BY_NC1"}
                pilots["points"][name] = {"status": "NO_PILOT"}
            continue
        Ws = {name: sa.burn_in(point_tuple(plan, name)[3]) for name in group}
        rate = point_seconds / filter_steps if filter_steps else None
        units = {name: gate3_units(plan, name, Ws[name]) for name in group}
        left = deadline.remaining()
        predicted = None if rate is None else rate * sum(units.values())
        admission = {"rate_seconds_per_unit": rate, "units": units, "predicted_seconds": predicted,
                     "seconds_left_before_deadline": left}
        if left <= 0 or (predicted is not None and predicted > left):
            for name in group:
                checks["points"][name] = {"status": "NOT_ATTEMPTED", "admission": admission}
                pilots["points"][name] = {"status": "NOT_ATTEMPTED"}
            save()
            continue
        for name in group:
            t_point = clock()
            rec, pilot, done = steps["point"](plan, name, checks["NC3"][name], deadline, clock)
            point_seconds += clock() - t_point
            filter_steps += done
            checks["points"][name] = {**rec, "admission": admission, "seconds": clock() - t_point}
            pilots["points"][name] = pilot
            save()
    save(complete=True)
    return checks, pilots


# ------------------------------------------------------------------------------------------- Gate 4
def run_evaluation(doc, plan, prov, checks, pilots, path, spent, clock=time.monotonic):
    numpy, sa, bp = numerical_imports()
    t0 = clock()
    cap, t15 = plan["aggregate_cap_seconds"], plan["constants"]["t_0975_df15"]
    run = {"phase": "evaluation", "run_id": uuid.uuid4().hex, "spent_before_seconds": spent,
           "remaining_aggregate_at_start_seconds": cap - spent, "run_wall_seconds": 0.0, "complete": False}
    art = {**new_artifact("evaluation", doc, prov, run),
           "inputs": {"numerical_checks_digest": checks["digest"], "pilot_digest": pilots["digest"],
                      "gate3_run_id": checks["run"]["run_id"]}, "points": {}}

    def save(complete=False):
        run["run_wall_seconds"], run["complete"] = clock() - t0, complete
        write_artifact(path, art)

    for group in GROUPS:
        recs, eligible, predicted = {}, {}, {}
        for name in group:
            C, s, u, c = point_tuple(plan, name)
            K, W = sa.comparators(C, s, u, c), sa.burn_in(c)
            chk, pil = checks["points"].get(name, {}), pilots["points"].get(name, {})
            eligible[name] = chk.get("status") == "CHECKS_PASSED" and pil.get("status") == "PILOT_COMPLETE"
            recs[name] = {"comparators": K, "W": W, "gate3_status": chk.get("status"), "pilot_status": pil.get("status")}
            if eligible[name]:
                n_e = sa.per_seed_length(pil["U"], plan["n_pilot"], K["K1"], t15, plan["kappa"], plan["delta"])
                predicted[name] = plan["prediction_margin"] * 16 * (W + n_e) * pil["t_step"]
                recs[name].update(n_e=n_e, predicted_seconds=predicted[name])
        remaining = cap - spent - (clock() - t0)
        admitted, reason = evaluation_admission(group, predicted, eligible, remaining, plan["point_cap_seconds"])
        for name in group:
            rec = recs[name]
            rec["admission"] = {"admitted": admitted, "reason": reason, "remaining_aggregate_seconds": remaining}
            rec["verdicts"] = {k: "NO_VERDICT" for k in COMPARATORS}
            if not admitted:
                rec["status"] = "NOT_ATTEMPTED" if eligible[name] else "NO_EVALUATION"
                art["points"][name] = rec
                continue
            C, s, u, c = point_tuple(plan, name)
            rec["stop_seconds"] = bp.stop_seconds(rec["predicted_seconds"], cap - spent - (clock() - t0))
            deadline, t_run = sa.Deadline(rec["stop_seconds"], clock), clock()
            model = sa.arma_model(C, s, u, c, *grid_of(plan["eval_grid"]))
            per_seed = rec["per_seed"] = []
            if not model["stationary"]["pass"]:          # passed at Gate 3; a failure here is recorded, not run
                rec["status"], rec["failed_check"] = "NUMERICAL_CHECK_FAILED", "NC4"
                art["points"][name] = rec
                save()
                continue
            try:
                for seed in plan["seeds"]["evaluation"][name]:
                    t = clock()
                    y = sa.simulate_window_record(C, s, u, c, rec["W"] + rec["n_e"], numpy.random.default_rng(seed),
                                                  deadline=deadline)
                    total, count = sa.arma_filter(y, model, burn_in=rec["W"], keep=False, deadline=deadline)
                    del y
                    per_seed.append({"seed": seed, "shots": rec["W"] + rec["n_e"], "wall_seconds": clock() - t,
                                     "mean": total / count})
                interval = rec["interval"] = sa.mean_interval([p["mean"] for p in per_seed], t15)
                rec["verdicts"] = {k: sa.verdict(rec["comparators"][k], interval["R_lo"], interval["R_hi"],
                                                 plan["delta"]) for k in COMPARATORS}
                rec["Q"] = ({k: [rec["comparators"][k] / interval["R_hi"], rec["comparators"][k] / interval["R_lo"]]
                             for k in COMPARATORS} if interval["R_lo"] > 0 else None)
                rec["status"] = "EVALUATED"
            except sa.DeadlineReached:
                rec["status"] = "INCOMPLETE"
            rec["run_seconds"] = clock() - t_run
            art["points"][name] = rec
            save()

    k1 = {name: art["points"][name]["verdicts"]["K1"] for name in POINTS}
    art["closure"] = {
        "k1_verdicts": k1, "roadmap_F": bp.roadmap_F_status(k1),
        "wording": bp.closure_wording(k1, plan["points"]),
        "C08_boundary": {k: {"E1": art["points"]["E1"]["verdicts"][k], "E2": art["points"]["E2"]["verdicts"][k],
                             "validated_at_both": art["points"]["E1"]["verdicts"][k] == "VALIDATED"
                             == art["points"]["E2"]["verdicts"][k]} for k in COMPARATORS}}
    save(complete=True)
    return art


# ------------------------------------------------------------------------------------------- command line
def refuse(reasons):
    print("sid_run13: refused; nothing measured, nothing written:", file=sys.stderr)
    for reason in reasons:
        print(f"  - {reason}", file=sys.stderr)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="Roadmap F under the frozen protocol_F.json.", allow_abbrev=False)
    parser.add_argument("--phase", required=True, choices=PHASES,
                        help="preflight (no measurement), checks-and-pilots (Gate 3) or evaluation (Gate 4)")
    args = parser.parse_args(argv)
    environ = os.environ

    doc = load_json(PROTOCOL_PATH)
    facts, git = stack_facts(), git_state()
    reasons = thread_refusals(environ) + stack_refusals(facts) + tree_refusals(git) + protocol_refusals(doc)
    paths = output_paths(doc) if not protocol_refusals(doc) else {}
    reasons += output_refusals(paths[key] for key in PHASE_OUTPUTS[args.phase] if key in paths)
    existing = {key: load_json(p) for key, p in paths.items() if p.exists()}
    if any(art is None or "run" not in art for art in existing.values()):
        reasons.append("an existing res13 artifact is unreadable, so the aggregate budget cannot be read")
    if args.phase == "evaluation" and paths:
        checks, pilots = load_json(paths["numerical_checks"]), load_json(paths["pilot"])
        input_reasons = gate3_input_refusals(checks, pilots)
        reasons += input_reasons
        if not input_reasons:
            reasons += implementation_change_refusals(checks["provenance"]["git_revision"])
    if reasons:
        return refuse(reasons)

    reasons = implementation_refusals(doc, facts)            # numpy is imported only now
    if reasons:
        return refuse(reasons)
    plan, prov = plan_from_protocol(doc), provenance(doc, facts, git, environ)
    spent = spent_seconds([art for art in existing.values()])
    if args.phase == "preflight":
        print(f"sid_run13 preflight passed at {git['revision'][:12]} with protocol {FROZEN_DIGEST}; "
              f"{plan['aggregate_cap_seconds'] - spent:.0f} s of the aggregate budget remain. "
              "Nothing measured, nothing written.")
        return 0
    if args.phase == "checks-and-pilots":
        checks, pilots = run_checks_and_pilots(doc, plan, prov, paths, spent)
        print(f"NC1 {checks['NC1']['status']}; " + "; ".join(
            f"{n} checks {checks['points'][n]['status']}, pilot {pilots['points'][n]['status']}" for n in POINTS))
        return 0
    art = run_evaluation(doc, plan, prov, existing["numerical_checks"], existing["pilot"], paths["evaluation"], spent)
    print(f"roadmap F: {art['closure']['roadmap_F']}; K1 verdicts {art['closure']['k1_verdicts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
