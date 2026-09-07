"""Policy comparison at matched null run length: calibration and detection delays.

Purpose  : calibrate each of the seven pilot policies to E_0[T] ~ 3e4 by bisection
           on the CUSUM threshold, then measure detection delay at tau_c/c in
           {20, 5, 1}. Feeds claims C09, C11, C12 in ledgers/status.yaml.
Inputs   : the operating point, passed explicitly as sid_policies.PILOT and carried in
           checkpoint identity and output metadata (roadmap G).
Seeds    : calibration bisection seeds 100..104, confirmation seed 199;
           delay seeds 200 + int(tau_c/c). Recorded in analysis/seeds.md.
Outputs  : analysis/reproduction/res6_policies.json (fresh run; git-ignored).
           The published reference stays at analysis/outputs/res6_policies.json and
           is NEVER written by this script -- it is only read, to compare against.
Runtime  : calibration ~8.5 min, delays ~1 min on one core (measured 2026-09-04 in the
           pinned environment: python 3.12.14, numpy 2.4.4, macOS x86_64 under Rosetta 2).

Usage:
    python sid_run6s.py "cal:<policy>,<policy>,..."   # calibrate, fresh by default
    python sid_run6s.py delays                        # delays at the FRESH thresholds
    python sid_run6s.py delays --thresholds=archive   # delays at the ARCHIVED thresholds
    ... add --resume to reuse a partial analysis/reproduction/ run.
    ... add --operating-point=stress for roadmap B's second point (C_eff=0.5, s=0.3).
        Each operating point writes its own checkpoint, so two cannot be mixed on disk.

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
from sid_policies import (CAL_BRACKET, GAMMA, SEED_OFFSET, build_policies, calibrate,
                          delay_of, operating_point_from_argv, state_name_for)

CAL_SEEDS = "bisection 100-104, confirmation 199"
DELAY_SEEDS = "200 + int(tau_c/c)"
KNOWN_FLAGS = ("--resume", "--thresholds=archive", "--operating-point=", "--no-reference")

T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


CAL_R = 32
BANK_TCCS = {"oracle": [20.0, 5.0, 1.0], "learner": [1.0, 4.0, 10.0, 25.0]}
DELAY_TCCS = (20.0, 5.0, 1.0)
NULL_CAP, DELAY_CAP = 150_000, 100_000


def cal_config(policy_names, op, op_name):
    """The configuration the thresholds depend on. A change here invalidates them.

    Everything that can move a threshold belongs here. The bank correlation-time lists and
    the two step caps were added 7 Sept 2026: editing either changes every number in the run
    while leaving the digest untouched, so --resume would have consumed an incompatible
    checkpoint without complaint.
    """
    lo, hi, iters = CAL_BRACKET[op_name]
    return {"operating_point": op.as_dict(), "operating_point_name": op_name,
            "gamma": GAMMA, "R": CAL_R, "iters": iters, "bracket": [lo, hi],
            "seed_offset": SEED_OFFSET[op_name], "bank_tccs": BANK_TCCS,
            "delay_tccs": list(DELAY_TCCS), "null_cap": NULL_CAP, "delay_cap": DELAY_CAP,
            "seeds": CAL_SEEDS, "policies": sorted(policy_names)}


def empty_state():
    return {"cal": {}, "delays": {}}


def main(argv):
    # The operating point is parsed from THIS argv, not module-level sys.argv, so a
    # programmatic caller cannot silently get the pilot while asking for something else.
    op_name, op = operating_point_from_argv(argv)
    state_name = state_name_for("res6_policies.json", op_name)
    resume = "--resume" in argv
    use_archived_thresholds = "--thresholds=archive" in argv
    allow_no_reference = "--no-reference" in argv

    # An unrecognised flag is refused rather than ignored. "--operating-point stress" with a
    # space, or a misspelt "--operating_point=", would otherwise fall back to the pilot and
    # overwrite the pilot's checkpoint while the operator believed they were running B.
    unknown = [a for a in argv[1:]
               if a.startswith("--") and not any(a == f or a.startswith(f) for f in KNOWN_FLAGS)]
    if unknown:
        print(f"unrecognised option(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"  known: {', '.join(KNOWN_FLAGS)}", file=sys.stderr)
        print("  note --operating-point=NAME takes an '=', not a space.", file=sys.stderr)
        return 2
    positional = [a for a in argv[1:] if not a.startswith("--")]
    if not positional:
        print(__doc__)
        return 2
    arg = positional[0]

    stage = "calibration" if arg.startswith("cal:") else arg
    seeds = CAL_SEEDS if arg.startswith("cal:") else DELAY_SEEDS
    sid_repro.print_banner(stage, resume, seeds)
    print(f"# operating point: {op_name} ({op.label()}) -> {state_name}", flush=True)

    state = sid_repro.load_checkpoint(state_name, resume) or empty_state()
    published = sid_repro.load_reference(state_name)
    reference = published or empty_state()
    bracket_failures = []

    # An operating point with no archived counterpart cannot be verified against anything.
    # Left alone the run would print the tolerance header, list NO-REFERENCE for every row,
    # summarise "0 pass, 0 FAIL" and exit 0 -- indistinguishable, to any reader or gate, from
    # a run that compared everything and agreed. It must be asked for.
    if published is None:
        if not allow_no_reference:
            print(f"no archived reference for operating point {op_name!r} "
                  f"({state_name} is not in analysis/outputs).", file=sys.stderr)
            print("  This run would ESTABLISH those numbers, not verify them, and nothing "
                  "would be compared.", file=sys.stderr)
            print("  Pass --no-reference to say so deliberately.", file=sys.stderr)
            return 2
        log(f"NO ARCHIVED REFERENCE for {op_name!r}: this run establishes these numbers, "
            f"it does not verify them. Nothing below is a comparison.")

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
        prior = sid_repro.load_checkpoint(state_name, True) or {}
        if prior.get("cal"):
            want = sid_repro.run_metadata(cal_config(sorted(prior["cal"]), op, op_name))
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
                f"{len(prior['cal'])} policies, {prior['meta']['machine']} / "
                f"{prior['meta']['blas']}")
            if not sid_repro.blas_is_identified(prior["meta"]):
                log("note: BLAS could not be identified, so this run certifies one build "
                    "only -- no cross-platform checkpoint compatibility is claimed")
    policies, _, _ = build_policies(op)
    computed = cached = 0

    if arg.startswith("cal:"):
        for name in arg[4:].split(","):
            if name in state["cal"]:
                cached += 1
                log("resumed", name, state["cal"][name])
                continue
            bk, sc = policies[name]
            lo, hi, iters = CAL_BRACKET[op_name]
            h, m, se, nc, endpoint = calibrate(bk, sc, GAMMA, R=CAL_R, lo=lo, hi=hi,
                                               iters=iters, seed=100 + SEED_OFFSET[op_name])
            state["cal"][name] = [h, m, se, int(nc)]
            state["meta"] = sid_repro.run_metadata(cal_config(state["cal"], op, op_name))
            sid_repro.save_checkpoint(state_name, state)
            computed += 1
            log(f"{name:32s} h*={h:.3f}  ARL={m:.0f} +- {se:.0f}  (capped runs: {nc}/{2*CAL_R})")
            if endpoint:
                bracket_failures.append((name, endpoint, h, m))
                log(f"  ** bracket {endpoint} never moved: h*={h:.6f} is set by the bracket "
                    f"[{lo}, {hi}], not by the data; ARL {m:.0f} is {100*(m-GAMMA)/GAMMA:+.0f} % "
                    f"off target **")
        verdicts, n_pass, n_fail = sid_repro.compare_rows(
            state["cal"], reference.get("cal"), threshold_index=0, mean_index=1, se_index=2, label="cal")

    elif arg == "delays":
        source = reference["cal"] if use_archived_thresholds else state["cal"]
        if not source:
            print("no thresholds available: run the cal: stage first (or pass --thresholds=archive "
                  "to measure delays at the archived thresholds).", file=sys.stderr)
            return 2
        log(f"thresholds from: {'archive' if use_archived_thresholds else 'this reproduction run'}")
        for true_tcc in DELAY_TCCS:
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
                m, se, nc = delay_of(bk, sc, true_tcc, source[name][0], 64,
                                    200 + int(true_tcc) + SEED_OFFSET[op_name], cap=DELAY_CAP)
                row[name] = [m, se, int(nc)]
                state.setdefault("meta", {})["operating_point"] = op.as_dict()
                sid_repro.save_checkpoint(state_name, state)
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
    status = sid_repro.report(computed, cached, verdicts, n_pass, n_fail, time.time()-T0)

    if published is None:
        print(f"\nNOT A COMPARISON: no archived reference for operating point {op_name!r}. "
              f"The rows above were established by this run, not verified against anything.")
    if bracket_failures:
        print(f"\nCALIBRATION BRACKET FAILURES ({len(bracket_failures)}): a threshold whose "
              f"bracket end never moved is set by the bracket, not by the data.", file=sys.stderr)
        for name, end, h, m in bracket_failures:
            print(f"  {name}: {end} pinned, h*={h:.6f}, ARL={m:.0f} "
                  f"({100*(m-GAMMA)/GAMMA:+.0f} % off target)", file=sys.stderr)
        print(f"  widen CAL_BRACKET[{op_name!r}] or raise its iteration count.", file=sys.stderr)
        status = status or 3
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
