"""Roadmap C ladder campaign: calibrate, select, then evaluate the thirteen candidates.

The benchmark ladder (analysis/benchmark_ladder_C.json) ranges L1/L2/L3 over thirteen
candidates: the eleven frozen schedules plus both learners. Seven of the eleven had never been
measured, and no candidate had ever been run on the SELECTION stream, so no ladder rung could
be computed without this campaign.

Why one driver. Roadmap B measured the class through two separate hard-coded lists --
build_policies for constants/interleaves, sid_run8.B_VALUES for the age-based switches.
Extending both would let the executed class drift from the manifest that froze it, so every
candidate here is built by sid_policies.schedule_from_spec from schedule_class_C.json.
tests/test_schedule_factory.py holds the factory to per-replicate agreement with both
implementations it replaces.

Why phase is an argument and never a default. The stage IS the phase, and each phase has its
own data stream (selection 700 + int(tau_c), evaluation 200 + int(tau_c), both plus the
operating-point offset) and, for the learners, its own action stream. The one place this
codebase defaulted a phase silently measured the sampling learner on the stream it had been
tuned against. There is no default here and an unknown phase is a crash.

Order is enforced, not advised: selection refuses to run until every candidate it ranges over
is calibrated and eligibility is frozen, because a selection over a partial class is chosen by
availability rather than performance.

Usage:
  sid_run11.py --stage=cal        --operating-point=pilot  [--smoke] [--no-reference]
  sid_run11.py --stage=selection  --operating-point=pilot
  sid_run11.py --stage=evaluation --operating-point=pilot

Outputs  : analysis/reproduction/res11_<stage>_<point>.json (git-ignored).
"""
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))

import sid_repro                                                        # noqa: E402
from sid_policies import (ACTION_SEEDS, ARL_ENVELOPE, Bank, CAL_BRACKET, CAL_SEED_BASE,
                          CONFIRM_CAP_DEFAULT, GAMMA, NULL_CAP_DEFAULT, SEED_OFFSET,
                          calibrate_refined,
                          data_seed, delay_of, frozen_schedule_class, make_posterior_theta,
                          make_posterior_sampling_theta, operating_point_from_argv,
                          schedule_from_spec)                             # noqa: E402

BANK_TCCS = [1.0, 4.0, 10.0, 25.0]
DELAY_TCCS = (20.0, 5.0, 1.0)
CAL_R, CONFIRM_R, MAX_SECANT, DELAY_R = 32, 64, 4, 64
CLASS_PATH = ROOT / "analysis" / "schedule_class_C.json"
LADDER_PATH = ROOT / "analysis" / "benchmark_ladder_C.json"
ELIG_PATH = ROOT / "analysis" / "eligibility_ladder_C.json"
LEARNERS = ("greedy", "sampling")
T0 = time.time()


def log(msg):
    print(f"[{time.time()-T0:6.0f}s] {msg}", flush=True)


def schedule_kind(name):
    """The manifest section a member belongs to -- fixes its calibration seed family."""
    cls = json.loads(CLASS_PATH.read_text())
    for kind, specs in cls["class"].items():
        if any(s["name"] == name for s in specs):
            return kind
    raise KeyError(name)


def learner_policy(name, bank, op_name, phase, tcc):
    """A learner plus the action seed for THIS phase. No phase default, ever."""
    if name == "greedy":
        return make_posterior_theta(bank), None
    off = SEED_OFFSET[op_name]
    if phase == "calibration":
        seed = ACTION_SEEDS["calibration"](off)
    elif phase in ("selection", "evaluation"):
        if tcc is None:
            raise SystemExit(f"phase {phase!r} needs tau_c to pick its action seed")
        seed = ACTION_SEEDS[phase](tcc, off)
    else:
        raise SystemExit(f"no action-seed family declared for phase {phase!r}")
    return make_posterior_sampling_theta(bank, seed), seed


def learner_threshold(name, op_name):
    """Learner thresholds come from the run10 calibration; they are not recalibrated here."""
    st = sid_repro.load_checkpoint(f"res10_{name}_{op_name}.json", True) or {}
    cal = st.get("cal") or {}
    if not cal:
        raise SystemExit(f"learner {name}/{op_name} has no calibration; run sid_run10 --stage=cal")
    rec = cal[sorted(cal)[0]] if isinstance(next(iter(cal.values())), dict) else cal
    return float(rec["h"] if isinstance(rec, dict) else rec[0])


def candidates(bank, op_name, phase, tcc=None, smoke=False):
    """All thirteen: the eleven frozen schedules, then both learners."""
    out = [(n, s, None) for n, s in frozen_schedule_class(CLASS_PATH)]
    for L in LEARNERS:
        sched, aseed = learner_policy(L, bank, op_name, phase, tcc)
        out.append((L, sched, aseed))
    return out


def stage_cal(bank, op_name, state, smoke, state_name):
    """Calibrate every frozen schedule. Learners are calibrated by sid_run10, not here."""
    lo, hi, iters = CAL_BRACKET[op_name]
    off = SEED_OFFSET[op_name]
    computed = 0
    for name, sched in frozen_schedule_class(CLASS_PATH):
        if name in state["cal"]:
            log(f"{name:16s} cached")
            continue
        seed = CAL_SEED_BASE[schedule_kind(name)] + off
        h, m, se, nc, endpoint, inside = calibrate_refined(
            bank, sched, GAMMA, R=(8 if smoke else CAL_R), lo=lo, hi=hi,
            iters=(2 if smoke else iters), seed=seed,
            confirm_R=(8 if smoke else CONFIRM_R), max_secant=(1 if smoke else MAX_SECANT),
            cap=(4_000 if smoke else NULL_CAP_DEFAULT),
            confirm_cap=(8_000 if smoke else CONFIRM_CAP_DEFAULT))
        pct = 100 * (m - GAMMA) / GAMMA
        state["cal"][name] = {"h": float(h), "arl": float(m), "se": float(se),
                              "capped": int(nc), "endpoint": bool(endpoint),
                              "inside_envelope": bool(inside), "pct": float(pct),
                              "cal_seed": int(seed)}
        computed += 1
        if not smoke:
            sid_repro.save_checkpoint(state_name, state)
        log(f"{name:16s} h*={h:.6f}  ARL={m:.0f} +- {se:.0f} ({pct:+.1f} %)  "
            f"capped {nc}/{2*(8 if smoke else CONFIRM_R)}  "
            f"{'INSIDE' if inside else 'OUTSIDE'} the +-{ARL_ENVELOPE:.0%} envelope")
    return computed


def require_frozen_eligibility(op_name):
    """Selection may not range over a class that is not yet fully calibrated and frozen."""
    if not ELIG_PATH.exists():
        raise SystemExit("eligibility is not frozen; run --stage=cal at BOTH points and freeze "
                         "analysis/eligibility_ladder_C.json before any selection run")
    elig = json.loads(ELIG_PATH.read_text())
    if op_name not in elig.get("operating_points", {}):
        raise SystemExit(f"eligibility is frozen but has no entry for {op_name}")
    return elig["operating_points"][op_name]


def stage_delays(bank, op_name, state, phase, smoke, state_name):
    """Delay runs for every candidate on THIS phase's stream. Per-replicate output is kept."""
    off = SEED_OFFSET[op_name]
    elig = None if smoke else require_frozen_eligibility(op_name)
    cal = state.get("_cal_source", {})
    computed = 0
    for tcc in (DELAY_TCCS[:1] if smoke else DELAY_TCCS):
        for name, sched, aseed in candidates(bank, op_name, phase, tcc, smoke):
            key = f"{name}|{tcc}"
            if key in state["delays"]:
                continue
            if elig is not None and name not in elig["eligible"]:
                log(f"{name:16s} tc={tcc:4.0f}  SKIPPED -- ineligible at {op_name}")
                continue
            h = (2.0 if smoke else
                 (learner_threshold(name, op_name) if name in LEARNERS else cal[name]["h"]))
            dseed = data_seed(phase, tcc, off)
            m, se, nc, runs = delay_of(bank, sched, tcc, h, (8 if smoke else DELAY_R),
                                       dseed, cap=(3000 if smoke else 400_000),
                                       return_runs=True)
            state["delays"][key] = {"mean": float(m), "se": float(se), "capped": int(nc),
                                    "h": float(h), "data_seed": int(dseed),
                                    "action_seed": (None if aseed is None else int(aseed)),
                                    "phase": phase,
                                    "runs": [int(x) for x in runs]}
            computed += 1
            if not smoke:
                sid_repro.save_checkpoint(state_name, state)
            log(f"{name:16s} tc={tcc:4.0f}  delay={m:8.0f} +- {se:5.0f}  capped {nc}  "
                f"data_seed={dseed}" + ("" if aseed is None else f"  action_seed={aseed}"))
    return computed


def main(argv):
    known = ("--stage=", "--operating-point=", "--smoke", "--no-reference", "--resume")
    for a in argv[1:]:
        if not any(a.startswith(k) for k in known):
            print(f"unknown flag {a!r}; known flags are {known}", file=sys.stderr)
            return 2
    stage = next((a.split("=", 1)[1] for a in argv[1:] if a.startswith("--stage=")), None)
    if stage not in ("cal", "selection", "evaluation"):
        print("--stage= is required and must be cal, selection or evaluation. The stage is the "
              "PHASE and picks the seed streams; there is deliberately no default.",
              file=sys.stderr)
        return 2
    smoke = "--smoke" in argv[1:]
    if not smoke:
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            print("refusing to measure from a dirty tree: the artifact would be attributed to a "
                  "revision that does not describe the code that produced it. Commit or stash "
                  "first.\n" + dirty, file=sys.stderr)
            return 2
    if not any(a.startswith("--operating-point=") for a in argv[1:]):
        print("--operating-point= is required. It is not defaulted here: the two points have "
              "different brackets, seed offsets and thresholds, and a silent default would "
              "attribute one point's numbers to the other.", file=sys.stderr)
        return 2
    op_name, op = operating_point_from_argv(argv)
    bank = Bank(BANK_TCCS, op)

    cfg = {"stage": stage, "phase": stage, "operating_point": op_name, "op": [op.C_eff, op.s],
           "bank_tccs": BANK_TCCS, "gamma": GAMMA, "envelope": ARL_ENVELOPE,
           "cal": {"R": CAL_R, "confirm_R": CONFIRM_R, "max_secant": MAX_SECANT,
                   "bracket": CAL_BRACKET[op_name], "seed_base": CAL_SEED_BASE},
           "delay_R": DELAY_R, "delay_tccs": list(DELAY_TCCS),
           "schedule_class_digest": json.loads(CLASS_PATH.read_text())["digest"],
           "benchmark_ladder_digest": json.loads(LADDER_PATH.read_text())["digest"],
           "seeds": {"calibration": "family base + offset (constants/interleave 100, switch 300)",
                     "selection": f"700 + int(tau_c) + {SEED_OFFSET[op_name]}",
                     "evaluation": f"200 + int(tau_c) + {SEED_OFFSET[op_name]}"}}

    state_name = f"res11_{stage}_{op_name}.json"
    sid_repro.print_banner(f"roadmap C ladder campaign [{stage}]", False,
                           json.dumps(cfg["seeds"]))
    print(f"# operating point : {op_name} ({op.label()})", flush=True)
    print(f"# phase           : {stage} (mandatory; selects the data and action streams)",
          flush=True)
    print(f"# class / ladder  : {cfg['schedule_class_digest']} / "
          f"{cfg['benchmark_ladder_digest']}", flush=True)
    if smoke:
        print("# SMOKE RUN -- tiny R, not evidence; nothing is archived", flush=True)

    published = sid_repro.load_reference(state_name)
    if published is None and "--no-reference" not in argv[1:] and not smoke:
        print(f"no archived reference for {state_name}; this run would ESTABLISH its numbers, "
              f"not verify them. Pass --no-reference to say so deliberately.", file=sys.stderr)
        return 2

    st = sid_repro.load_checkpoint(state_name, True) or {}
    st.setdefault("cal", {})
    st.setdefault("delays", {})
    st["config"] = cfg
    # Captured at START, not at write time: a file created while the run is in flight must not
    # retroactively relabel measurements that were produced from a clean tree.
    st["meta"] = sid_repro.run_metadata(cfg)

    if stage == "cal":
        computed = stage_cal(bank, op_name, st, smoke, state_name)
        inside = [n for n, r in st["cal"].items() if r["inside_envelope"]]
        outside = [n for n, r in st["cal"].items() if not r["inside_envelope"]]
        log(f"calibrated {len(st['cal'])}/11: {len(inside)} inside the envelope, "
            f"{len(outside)} outside")
        if outside:
            log(f"OUTSIDE (ineligible at {op_name}): {', '.join(sorted(outside))}")
    else:
        cal_state = sid_repro.load_checkpoint(f"res11_cal_{op_name}.json", True) or {}
        if not smoke and len(cal_state.get("cal", {})) != 11:
            print(f"only {len(cal_state.get('cal', {}))}/11 schedules are calibrated at "
                  f"{op_name}; a {stage} run over a partial class would be selecting on "
                  f"availability. Run --stage=cal first.", file=sys.stderr)
            return 3
        st["_cal_source"] = cal_state.get("cal", {})
        st["cal_source_digest"] = cal_state.get("meta", {}).get("digest")
        computed = stage_delays(bank, op_name, st, stage, smoke, state_name)

    if not smoke:
        sid_repro.save_checkpoint(state_name, {k: v for k, v in st.items()
                                               if not k.startswith("_")})
    log(f"stage {stage} complete at {op_name}: {computed} cells computed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
