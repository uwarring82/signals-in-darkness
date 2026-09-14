"""Delay-versus-null-ARL curve for posterior sampling, to close the calibration confound.

The ladder compares policies calibrated to within +-30 % of the same target E_0[T]. That is a
band, not a match: at the pilot, sampling confirms at 34 444 while its L1 benchmarks confirm at
24 563 (mid) and 30 393 (ext). A policy with a LONGER null ARL is harder to trip and so detects
later, all else equal, which is a confound in exactly the direction that would manufacture the
observed negative result.

A threshold RATIO cannot settle this. Different policies have different null increment
distributions, so equal h does not mean equal false-alarm rate and a 5 % difference in h does not
imply a 5 % difference in delay. The only honest instrument is a measured curve: run the SAME
policy across a grid of thresholds, record what null ARL each one actually buys and what delay it
actually gives, then read the delay off at the benchmark's own ARL.

Protocol is copied from the stages being reconciled, so the grid point at the calibrated
threshold must reproduce them exactly, which is checked rather than assumed:
  null   arl_of  at 2*CONFIRM_R replicates, data seed 100 + offset + 99, cap CONFIRM_CAP_DEFAULT,
         action seed from the CALIBRATION family -- identical to calibrate_refined's confirmation
  delay  delay_of at DELAY_R replicates, data seed 200 + int(tau_c) + offset, cap 400_000,
         action seed from the EVALUATION family -- identical to the evaluation stage

Usage: sid_run12.py --operating-point=pilot [--no-reference]
Output: analysis/reproduction/res12_sensitivity_<point>.json (git-ignored).
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

import sid_repro                                                            # noqa: E402
from sid_policies import (ACTION_SEEDS, Bank, CONFIRM_CAP_DEFAULT, GAMMA, SEED_OFFSET,
                          arl_of, data_seed, delay_of, make_posterior_sampling_theta,
                          operating_point_from_argv)                        # noqa: E402

BANK_TCCS = [1.0, 4.0, 10.0, 25.0]
DELAY_TCCS = (20.0, 5.0, 1.0)
CONFIRM_R, DELAY_R = 64, 64

# Grids bracket the benchmark ARLs that must be matched, and INCLUDE each point's own calibrated
# threshold so the curve can be checked against the frozen measurements.
H_GRID = {
    "pilot": (3.30, 3.38, 3.45, 3.5190812815020247),
    "stress": (2.60546875, 2.68, 2.76, 2.84),
}
T0 = time.time()


def log(m):
    print(f"[{time.time()-T0:6.0f}s] {m}", flush=True)


def main(argv):
    known = ("--operating-point=", "--no-reference")
    for a in argv[1:]:
        if not any(a.startswith(k) for k in known):
            print(f"unknown flag {a!r}", file=sys.stderr)
            return 2
    if not any(a.startswith("--operating-point=") for a in argv[1:]):
        print("--operating-point= is required", file=sys.stderr)
        return 2
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        print("refusing to measure from a dirty tree\n" + dirty, file=sys.stderr)
        return 2

    op_name, op = operating_point_from_argv(argv)
    off = SEED_OFFSET[op_name]
    bank = Bank(BANK_TCCS, op)
    grid = H_GRID[op_name]

    cfg = {"purpose": "delay vs null ARL for posterior sampling, at fixed policy",
           "operating_point": op_name, "op": [op.C_eff, op.s], "h_grid": list(grid),
           "gamma_reference": GAMMA, "confirm_R": CONFIRM_R, "delay_R": DELAY_R,
           "null_seed": f"100 + {off} + 99", "null_cap": CONFIRM_CAP_DEFAULT,
           "delay_seed": f"200 + int(tau_c) + {off}",
           "action_seeds": {"null": f"calibration family 6100 + {off}",
                            "delay": f"evaluation family 6200 + int(tau_c) + {off}"}}
    state_name = f"res12_sensitivity_{op_name}.json"
    sid_repro.print_banner(f"roadmap C calibration sensitivity [{op_name}]", False,
                           json.dumps(cfg["action_seeds"]))
    print(f"# operating point : {op_name} ({op.label()})", flush=True)
    print(f"# h grid          : {', '.join(f'{h:.6f}' for h in grid)}", flush=True)

    if sid_repro.load_reference(state_name) is None and "--no-reference" not in argv[1:]:
        print(f"no archived reference for {state_name}; pass --no-reference to establish it.",
              file=sys.stderr)
        return 2

    st = sid_repro.load_checkpoint(state_name, True) or {}
    st.setdefault("points", {})
    st["config"] = cfg
    st["meta"] = sid_repro.run_metadata(cfg)

    null_action = ACTION_SEEDS["calibration"](off)
    for h in grid:
        key = f"{h:.9f}"
        if key in st["points"]:
            log(f"h={h:.6f} cached")
            continue
        sched = make_posterior_sampling_theta(bank, null_action)
        m, se, nc = arl_of(bank, sched, h, 2 * CONFIRM_R, 100 + off + 99,
                           cap=CONFIRM_CAP_DEFAULT)
        rec = {"h": float(h), "arl": float(m), "arl_se": float(se), "arl_capped": int(nc),
               "delays": {}}
        log(f"h={h:.6f}  ARL={m:8.0f} +- {se:5.0f}  capped {nc}/{2*CONFIRM_R}")
        for tcc in DELAY_TCCS:
            aseed = ACTION_SEEDS["evaluation"](tcc, off)
            dsched = make_posterior_sampling_theta(bank, aseed)
            dm, dse, dnc, runs = delay_of(bank, dsched, tcc, h, DELAY_R,
                                          data_seed("evaluation", tcc, off),
                                          cap=400_000, return_runs=True)
            rec["delays"][str(tcc)] = {"mean": float(dm), "se": float(dse), "capped": int(dnc),
                                       "action_seed": int(aseed),
                                       "runs": [int(x) for x in runs]}
            log(f"    tau_c={tcc:4.0f}  delay={dm:8.0f} +- {dse:5.0f}  capped {dnc}")
        st["points"][key] = rec
        sid_repro.save_checkpoint(state_name, st)

    sid_repro.save_checkpoint(state_name, st)
    log(f"sensitivity curve complete at {op_name}: {len(st['points'])} grid points")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
