"""Policy comparison at matched null run length: calibration and detection delays.

Purpose  : calibrate each of the seven pilot policies to E_0[T] ~ 3e4 by bisection
           on the CUSUM threshold, then measure detection delay at tau_c/c in
           {20, 5, 1}. Feeds claims C09, C11, C12 in ledgers/status.yaml.
Inputs   : none (operating point C = 0.4, s = 0.5 fixed in analysis/lib/sid_policies.py)
Seeds    : calibration bisection seeds 100..104, confirmation seed 199;
           delay seeds 200 + int(tau_c/c). Recorded in analysis/seeds.md.
Outputs  : analysis/reproduction/res6_policies.json (fresh run; git-ignored).
           The published reference stays at analysis/outputs/res6_policies.json and
           is NEVER written by this script -- it is only read, to compare against.
Runtime  : calibration ~8 min, delays ~25 min on one core (measured 2026-09-03,
           python 3.11 / numpy 2.2).

Usage:
    python sid_run6s.py "cal:<policy>,<policy>,..."   # calibrate, fresh by default
    python sid_run6s.py delays                        # delays at the FRESH thresholds
    python sid_run6s.py delays --thresholds=archive   # delays at the ARCHIVED thresholds
    ... add --resume to reuse a partial analysis/reproduction/ run.

Exits nonzero if any row falls outside the declared tolerances in
analysis/lib/sid_repro.py. See notes/2026-09-03-note-04-reproduction-defect.md for
why this script no longer treats its own published output as checkpoint state.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sid_repro
from sid_policies import GAMMA, build_policies, calibrate, delay_of

STATE_NAME = "res6_policies.json"
CAL_SEEDS = "bisection 100-104, confirmation 199"
DELAY_SEEDS = "200 + int(tau_c/c)"

T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


CAL_R, CAL_ITERS = 32, 5


def cal_config(policy_names):
    """The configuration the thresholds depend on. A change here invalidates them."""
    return {"gamma": GAMMA, "R": CAL_R, "iters": CAL_ITERS,
            "seeds": CAL_SEEDS, "policies": sorted(policy_names)}


def empty_state():
    return {"cal": {}, "delays": {}}


def main(argv):
    resume = "--resume" in argv
    use_archived_thresholds = "--thresholds=archive" in argv
    positional = [a for a in argv[1:] if not a.startswith("--")]
    if not positional:
        print(__doc__)
        return 2
    arg = positional[0]

    stage = "calibration" if arg.startswith("cal:") else arg
    seeds = CAL_SEEDS if arg.startswith("cal:") else DELAY_SEEDS
    sid_repro.print_banner(stage, resume, seeds)

    state = sid_repro.load_checkpoint(STATE_NAME, resume) or empty_state()
    reference = sid_repro.load_reference(STATE_NAME) or empty_state()

    # The delays stage needs the thresholds the cal stage measured. Those are a required
    # OUTPUT OF THE CURRENT RUN, not anonymous reusable state: they live in this run's
    # reproduction checkpoint, never in the archive. --resume governs whether delay rows
    # already measured are reused; it must not decide whether this stage can see its own
    # input, or "fresh by default" would make the documented two-command path impossible.
    #
    # Because that input is read outside --resume, it is bound to the run that produced it.
    # Thresholds from a different revision, interpreter, library set or policy configuration
    # are refused rather than silently mixed into a fresh measurement.
    if arg == "delays" and not state["cal"] and not use_archived_thresholds:
        prior = sid_repro.load_checkpoint(STATE_NAME, True) or {}
        if prior.get("cal"):
            want = sid_repro.run_metadata(cal_config(sorted(prior["cal"])))
            why = sid_repro.incompatibilities(prior.get("meta"), want)
            if why:
                print("refusing thresholds that are not this run's cal output:", file=sys.stderr)
                for reason in why:
                    print(f"  - {reason}", file=sys.stderr)
                print("  rerun the cal: stage, or pass --thresholds=archive deliberately.",
                      file=sys.stderr)
                return 2
            state["cal"] = prior["cal"]
            state["meta"] = prior["meta"]
            log(f"thresholds from this run's cal stage: run {prior['meta']['run_id']}, "
                f"{len(prior['cal'])} policies")
    policies, _, _ = build_policies()
    computed = cached = 0

    if arg.startswith("cal:"):
        for name in arg[4:].split(","):
            if name in state["cal"]:
                cached += 1
                log("resumed", name, state["cal"][name])
                continue
            bk, sc = policies[name]
            h, m, se, nc = calibrate(bk, sc, GAMMA, R=CAL_R, iters=CAL_ITERS)
            state["cal"][name] = [h, m, se, int(nc)]
            state["meta"] = sid_repro.run_metadata(cal_config(state["cal"]))
            sid_repro.save_checkpoint(STATE_NAME, state)
            computed += 1
            log(f"{name:32s} h*={h:.3f}  ARL={m:.0f} +- {se:.0f}  (capped runs: {nc}/64)")
        verdicts, n_pass, n_fail = sid_repro.compare_rows(
            state["cal"], reference.get("cal"), threshold_index=0, mean_index=1, se_index=2, label="cal")

    elif arg == "delays":
        source = reference["cal"] if use_archived_thresholds else state["cal"]
        if not source:
            print("no thresholds available: run the cal: stage first (or pass --thresholds=archive "
                  "to measure delays at the archived thresholds).", file=sys.stderr)
            return 2
        log(f"thresholds from: {'archive' if use_archived_thresholds else 'this reproduction run'}")
        for true_tcc in (20.0, 5.0, 1.0):
            row = state["delays"].setdefault(str(true_tcc), {})
            for name, (bk, sc) in policies.items():
                if name.startswith("oracle-mid") and f"(tc={int(true_tcc)})" not in name:
                    continue
                if name in row:
                    cached += 1
                    continue
                if name not in source:
                    log(f"skipping {name}: no threshold for it")
                    continue
                m, se, nc = delay_of(bk, sc, true_tcc, source[name][0], 64, 200+int(true_tcc))
                row[name] = [m, se, int(nc)]
                sid_repro.save_checkpoint(STATE_NAME, state)
                computed += 1
                log(f"tc/c={true_tcc:4.0f}  {name:32s} delay={m:7.0f} +- {se:5.0f}  (capped {nc})")
        for true_tcc, row in state["delays"].items():
            needed = [f"oracle-mid(tc={int(float(true_tcc))})", "extremum-only",
                      "learner-mid(bank)", "learner-interleave-B10(bank)", "learner-interleave-B1(bank)"]
            missing = [n for n in needed if n not in row]
            if missing:
                log(f"tc/c={float(true_tcc):4.0f} summary skipped, no delay for: {', '.join(missing)}")
                continue
            orc = min(row[f"oracle-mid(tc={int(float(true_tcc))})"][0], row["extremum-only"][0])
            line = f"tc/c={float(true_tcc):4.0f} oracle={orc:6.0f} |"
            for name in ("extremum-only", "learner-mid(bank)",
                         "learner-interleave-B10(bank)", "learner-interleave-B1(bank)"):
                line += f" {name}: +{row[name][0]-orc:6.0f} ({row[name][0]/orc:4.2f}x)"
            log(line)
        verdicts, n_pass, n_fail = [], 0, 0
        for true_tcc, row in state["delays"].items():
            v, p, f = sid_repro.compare_rows(
                row, (reference.get("delays") or {}).get(true_tcc), threshold_index=None,
                mean_index=0, se_index=1, label=f"delay(tc/c={true_tcc})")
            verdicts += v; n_pass += p; n_fail += f
    else:
        print(__doc__)
        return 2

    log("stage done")
    return sid_repro.report(computed, cached, verdicts, n_pass, n_fail, time.time()-T0)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
