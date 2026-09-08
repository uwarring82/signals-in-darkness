#!/usr/bin/env python3
"""Roadmap C — posterior-driven action selection: null calibration and post-change delays.

Purpose  : calibrate the posterior-expected-rate theta policy to E_0[T] ~ 3e4 and measure its
           detection delay, with the diagnostics that make the feedback path causally checkable.
Inputs   : the operating point (--operating-point), the frozen schedule class and benchmark
           ladder in analysis/, and the policy's own identity digest.
Seeds    : null 100 + offset (calibration), 900 + offset (diagnostic null run);
           post-change evaluation 200 + int(tau_c) + offset, matching roadmap B's stream so
           L1, L2 and L3 are measured on the same realisations.
Outputs  : analysis/reproduction/res10_posterior_<point>.json (git-ignored).
Runtime  : calibration dominates; comparable to one roadmap B policy.

Usage:
    python sid_run10.py cal    [--operating-point=NAME] [--no-reference]
    python sid_run10.py delays [--operating-point=NAME] [--no-reference]

THE POLICY MAY FAIL. If its calibration falls outside the declared +-30 % envelope, this
script reports "no comparable learner result" and exits nonzero. It does NOT retune after
seeing delays, and the policy does not quietly leave L3's eligible set while a domination
claim continues about the remaining eleven -- that is predeclared in
analysis/benchmark_ladder_C.json and it is the failure the ladder's history exists to prevent.
"""
import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import numpy as np

import sid_repro
from sid_policies import (ARL_ENVELOPE, CAL_BRACKET, GAMMA, SEED_OFFSET, THM, THX, Bank,
                          calibrate_refined, make_posterior_theta, operating_point_from_argv,
                          run_batch)

BANK_TCCS = [1.0, 4.0, 10.0, 25.0]
DELAY_TCCS = (20.0, 5.0, 1.0)
CAL_R, CONFIRM_R, MAX_SECANT = 32, 64, 4
DIAG_R, DELAY_R = 64, 64
NULL_CAP, DELAY_CAP = 150_000, 100_000
MAX_SWITCH_RECORDS = 200          # per run; the total count is always kept
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


def _digest_of(path):
    return json.load(open(path, encoding="utf-8"))["digest"]


def recording_policy(bank):
    """The posterior policy, wrapped so every action is recorded with its cause.

    The posterior vector is stored at the moment each run's action changes, together with the
    action before and after. Recording it at every step would be ~1e7 floats per calibration and
    would add nothing: between switches the decision is unchanged, so the causal question --
    what did the filter believe when it changed its mind -- is answered exactly at the switches.
    Ties are counted separately because the tie-break is part of the policy identity, and a
    policy sitting on a tie is choosing arbitrarily.

    The per-step action matrix is kept so that every statistic can be TRUNCATED AT EACH RUN'S
    OWN STOPPING TIME. run_batch continues until the last run alarms, so a run that stopped
    early keeps being simulated; counting its later actions would inflate its switch count and
    could push its mid-fringe fraction above 1, which is how this was caught.
    """
    inner = make_posterior_theta(bank)
    mid, ext = inner.rates
    state = {"prev": None, "switches": [], "ties": 0, "actions": []}

    def sched(n, w, bk):
        th = inner(n, w, bk)
        exp_mid = w @ mid
        state["ties"] += int(np.sum(exp_mid == ext))
        if state["prev"] is not None:
            changed = np.nonzero(th != state["prev"])[0]
            for r in changed:
                if len(state["switches"]) < MAX_SWITCH_RECORDS * 4:
                    state["switches"].append({
                        "run": int(r), "step": int(n),
                        "posterior": [round(float(x), 6) for x in w[r]],
                        "expected_mid_rate": float(exp_mid[r]), "ext_rate": float(ext),
                        "from": "mid" if abs(state["prev"][r] - THM) < 1e-12 else "ext",
                        "to": "mid" if abs(th[r] - THM) < 1e-12 else "ext"})
        state["actions"].append(np.abs(th - THM) < 1e-12)      # True = mid-fringe
        state["prev"] = th
        return th

    sched.needs_posterior = True
    sched.identity = inner.identity
    sched.state = state
    return sched


def diagnostics(sched, stopping, label):
    """Every statistic truncated at each run's own stopping time."""
    s = sched.state
    stop = np.asarray(stopping, dtype=int)
    acts = np.asarray(s["actions"], dtype=bool)                # (steps, R)
    steps, R = acts.shape
    alive = np.arange(steps)[:, None] < np.minimum(stop, steps)[None, :]
    n_alive = alive.sum(0)
    mid_frac = np.where(n_alive > 0, (acts & alive).sum(0) / np.maximum(n_alive, 1), 0.0)
    changed = acts[1:] != acts[:-1]
    n_switch = (changed & alive[1:]).sum(0)
    # switch records past a run's stop are dropped, not merely uncounted
    kept = [rec for rec in s["switches"] if rec["step"] < int(stop[rec["run"]])]
    return {"stratum": label,
            "steps_simulated": int(steps),
            "shots_before_alarm_total": int(n_alive.sum()),
            "ties": int(s["ties"]),
            "switches_per_run": n_switch.tolist(),
            "mean_switches_per_run": float(n_switch.mean()),
            "switches_per_1000_shots": float(1000 * n_switch.sum() / max(n_alive.sum(), 1)),
            "fraction_of_shots_at_mid_fringe": [float(x) for x in mid_frac],
            "mean_fraction_at_mid_fringe": float(mid_frac.mean()),
            "switch_records": kept,
            "switch_records_truncated": bool(int(n_switch.sum()) > len(kept))}


def config(op, op_name, policy_identity):
    lo, hi, iters = CAL_BRACKET[op_name]
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    return {
        "operating_point": op.as_dict(), "operating_point_name": op_name,
        "policy_digest": policy_identity["digest"],
        "schedule_class_digest": _digest_of(os.path.join(here, "schedule_class_C.json")),
        "benchmark_ladder_digest": _digest_of(os.path.join(here, "benchmark_ladder_C.json")),
        "method": "secant-refined", "arl_envelope": ARL_ENVELOPE,
        "gamma": GAMMA, "R": CAL_R, "confirm_R": CONFIRM_R, "max_secant": MAX_SECANT,
        "iters": iters, "bracket": [lo, hi], "seed_offset": SEED_OFFSET[op_name],
        "bank_tccs": BANK_TCCS, "delay_tccs": list(DELAY_TCCS),
        "null_cap": NULL_CAP, "delay_cap": DELAY_CAP,
        "diag_R": DIAG_R, "delay_R": DELAY_R,
        "seeds": {"calibration_null": f"100 + {SEED_OFFSET[op_name]}",
                  "diagnostic_null": f"900 + {SEED_OFFSET[op_name]}",
                  "post_change_evaluation": f"200 + int(tau_c) + {SEED_OFFSET[op_name]}"},
    }


def main(argv):
    op_name, op = operating_point_from_argv(argv)
    allow_no_reference = "--no-reference" in argv
    positional = [a for a in argv[1:] if not a.startswith("--")]
    if not positional or positional[0] not in ("cal", "delays"):
        print(__doc__)
        return 2
    stage = positional[0]
    state_name = f"res10_posterior_{op_name}.json"

    bank = Bank(BANK_TCCS, op)
    probe = make_posterior_theta(bank)
    cfg = config(op, op_name, probe.identity)
    want = sid_repro.run_metadata(cfg)

    sid_repro.print_banner(f"roadmap C {stage}", False, json.dumps(cfg["seeds"]))
    print(f"# operating point : {op_name} ({op.label()})", flush=True)
    print(f"# policy digest   : {cfg['policy_digest']}", flush=True)
    print(f"# class / ladder  : {cfg['schedule_class_digest']} / "
          f"{cfg['benchmark_ladder_digest']}", flush=True)

    published = sid_repro.load_reference(state_name)
    if published is None and not allow_no_reference:
        print(f"no archived reference for {state_name}; this run would ESTABLISH its numbers, "
              f"not verify them. Pass --no-reference to say so deliberately.", file=sys.stderr)
        return 2

    st = sid_repro.load_checkpoint(state_name, True) or {}
    computed = cached = 0

    if stage == "cal":
        lo, hi, iters = CAL_BRACKET[op_name]
        h, m, se, nc, endpoint, inside = calibrate_refined(
            bank, probe, GAMMA, R=CAL_R, lo=lo, hi=hi, iters=iters,
            seed=100 + SEED_OFFSET[op_name], confirm_R=CONFIRM_R, max_secant=MAX_SECANT)
        computed += 1
        pct = 100 * (m - GAMMA) / GAMMA
        log(f"posterior policy: h*={h:.6f}  ARL={m:.0f} +- {se:.0f} ({pct:+.1f} %)  "
            f"capped {nc}/{2*CONFIRM_R}")

        # diagnostic null run at h*, recorded. Under H0 there is no tau_c: this is stratified by
        # operating point and seed stream only, and the posterior it reports is the filter's
        # belief while it fits noise.
        rec = recording_policy(bank)
        stop = run_batch(bank, rec, None, h, DIAG_R, 900 + SEED_OFFSET[op_name], NULL_CAP, True)
        null_diag = diagnostics(rec, stop, f"null | operating point {op_name} | seed 900+offset")
        log(f"null diagnostics: {null_diag['mean_switches_per_run']:.1f} switches/run, "
            f"{100*null_diag['mean_fraction_at_mid_fringe']:.1f} % of shots at mid-fringe, "
            f"{null_diag['ties']} ties")

        st["cal"] = {"h": h, "ARL": m, "se": se, "capped": int(nc),
                     "bracket_endpoint": endpoint, "inside_envelope": bool(inside),
                     "pct_off_target": pct, "null_runs": stop.tolist()}
        st["null_diagnostics"] = null_diag
        st["policy_identity"] = probe.identity
        st["meta"] = want
        sid_repro.save_checkpoint(state_name, st)

        print(f"\ncomputed: {computed}, cached: {cached}")
        if not inside:
            print(f"\nNO COMPARABLE LEARNER RESULT at operating point {op_name!r}: the posterior "
                  f"policy calibrates to ARL {m:.0f} ({pct:+.1f} %), outside the "
                  f"+-{100*ARL_ENVELOPE:.0f} % envelope.", file=sys.stderr)
            print("  Per analysis/benchmark_ladder_C.json this comparison STOPS. The policy is "
                  "not retuned after inspecting delays, and it does not leave L3's eligible set "
                  "while a domination claim continues about the remaining eleven.", file=sys.stderr)
            return 4
        log("calibration inside the envelope; delays may proceed")
        return 0

    # ---- delays -------------------------------------------------------------------------
    if not st.get("cal") or not st["cal"].get("inside_envelope"):
        print("no in-envelope calibration for this operating point; run the cal stage first "
              "(and if it reported no comparable learner result, this stage must not run).",
              file=sys.stderr)
        return 2
    h = st["cal"]["h"]
    st.setdefault("delays", {})
    st.setdefault("post_change_diagnostics", {})
    for tcc in DELAY_TCCS:
        key = str(tcc)
        if key in st["delays"]:
            cached += 1
            continue
        rec = recording_policy(bank)
        stop = run_batch(bank, rec, tcc, h, DELAY_R, 200 + int(tcc) + SEED_OFFSET[op_name],
                         DELAY_CAP, False)
        d = diagnostics(rec, stop, f"post-change | true tau_c/c = {tcc}")
        st["delays"][key] = [float(stop.mean()), float(stop.std() / np.sqrt(DELAY_R)),
                             int((stop >= DELAY_CAP).sum()), stop.tolist()]
        st["post_change_diagnostics"][key] = d
        computed += 1
        log(f"tc/c={tcc:4.0f}: delay={stop.mean():7.0f} +- {stop.std()/np.sqrt(DELAY_R):5.0f} "
            f"(capped {int((stop >= DELAY_CAP).sum())}/{DELAY_R})  "
            f"{100*d['mean_fraction_at_mid_fringe']:5.1f} % mid-fringe, "
            f"{d['mean_switches_per_run']:.1f} switches/run")
        st["meta"] = want
        sid_repro.save_checkpoint(state_name, st)

    fracs = {k: v["mean_fraction_at_mid_fringe"] for k, v in st["post_change_diagnostics"].items()}
    spread = max(fracs.values()) - min(fracs.values())
    print(f"\ncomputed: {computed}, cached: {cached}")
    print(f"\naction frequency by true tau_c (post-change): "
          + ", ".join(f"{k}: {100*v:.1f} % mid" for k, v in sorted(fracs.items())))
    print(f"spread across tau_c: {100*spread:.1f} percentage points")
    if spread < 0.01:
        print("\nACCEPTANCE RULE FAILED: post-change action frequency does not vary with true "
              "tau_c, so the policy is not using the posterior in any way that matters. No "
              "feedback claim may be made whatever the delays show "
              "(analysis/benchmark_ladder_C.json).", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
