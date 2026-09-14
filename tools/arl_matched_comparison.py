"""Sampling versus each benchmark AT THE BENCHMARK'S OWN NULL ARL.

POST-UNBLINDING SENSITIVITY ANALYSIS. Not part of the preregistered result: it was motivated by
the observed comparison and reuses the frozen streams. It can establish that the negative L1
comparison is robust to the calibration band; it cannot be independent confirmation, which would
need an independently seeded repetition. See analysis/sensitivity_protocol_C.json.

The +-30 % envelope is a band, not a match, and a policy with a longer null ARL is harder to trip
and so detects later. Where sampling holds the longer ARL that could manufacture the negative
result. A threshold RATIO cannot rule it out -- different policies have different null increment
distributions, so h is not a common currency -- and that argument stays withdrawn regardless of
what this tool reports.

INTERPOLATION RULE, frozen before the extended curves were inspected:
  step 1  linear in log(ARL_hat) against h, inverted for h_matched where sampling's null ARL
          equals the benchmark's
  step 2  linear in delay against h, evaluated at h_matched
Choosing a functional form by goodness of fit is forbidden.

BRACKETING: every target must lie inside the measured grid. Extrapolation is not permitted; the
grid was extended outward instead.

UNCERTAINTY, joint. Inside every draw: resample the sampling null runs at every grid threshold
(indices shared across thresholds, which are the same replicates), resample the benchmark's null
runs, resample the paired post-change stopping times, then solve for h_matched from THAT draw's
curve and THAT draw's target and recompute the ratio. So the interval carries uncertainty in the
target ARL and in the curve, not only sampling error in the delays.

Usage: python tools/arl_matched_comparison.py [--write]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "arl_matched_C.json"
OPS = ("pilot", "stress")
TCCS = (20.0, 5.0, 1.0)
B = 10_000
RNG_SEED = 20260914


def digest_of(o):
    return hashlib.sha256(json.dumps({k: v for k, v in o.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def invert(hs, log_arl, target_log):
    """h where the piecewise-linear log-ARL curve crosses target_log. None if unbracketed."""
    for i in range(len(hs) - 1):
        a, b = log_arl[i], log_arl[i + 1]
        if (a <= target_log <= b) or (b <= target_log <= a):
            if a == b:
                return hs[i]
            return hs[i] + (target_log - a) * (hs[i + 1] - hs[i]) / (b - a)
    return None


def main(argv):
    write = "--write" in argv[1:]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    proto = json.loads((ROOT / "analysis" / "sensitivity_protocol_C.json").read_text())
    elig = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())
    res = json.loads((ROOT / "analysis" / "ladder_results_C.json").read_text())

    rec = {"record": "sampling versus each benchmark at the benchmark's own null ARL",
           "status": proto["status"], "protocol_digest": proto["digest"],
           "ladder_results_digest": res["digest"], "eligibility_digest": elig["digest"],
           "revision": head, "cells": {}, "reproduction_check": {}, "curves": {}}
    problems = []

    for op in OPS:
        p = ROOT / "analysis" / "reproduction" / f"res12_sensitivity_{op}.json"
        if not p.exists():
            problems.append(f"{op}: no sensitivity curve")
            continue
        doc = json.loads(p.read_text())
        curve, bnulls = doc["points"], doc.get("benchmark_nulls", {})
        cal = elig["operating_points"][op]["calibrations"]
        ev = json.loads((ROOT / "analysis" / "reproduction"
                         / f"res11_evaluation_{op}.json").read_text())["delays"]

        keys = sorted(curve, key=lambda k: float(k))
        hs = np.array([float(k) for k in keys])
        null_stack = np.stack([np.asarray(curve[k]["null_runs"], float) for k in keys])  # G x Rn
        arls = null_stack.mean(1)
        rec["curves"][op] = {"h": hs.tolist(), "arl": arls.tolist(),
                             "monotone_in_h": bool(np.all(np.diff(arls) > 0))}
        if not np.all(np.diff(arls) > 0):
            problems.append(f"{op}: measured ARL is not monotone in h; the inversion in step 1 "
                            f"would be ambiguous")

        # the grid point at sampling's own calibrated threshold must reproduce the frozen numbers
        hstar = cal["sampling"]["h_star"]
        kk = min(keys, key=lambda k: abs(float(k) - hstar))
        if abs(float(kk) - hstar) < 1e-9:
            arl_ok = abs(curve[kk]["arl"] - cal["sampling"]["ARL"]) < 1e-6
            dly_ok = all(abs(curve[kk]["delays"][str(t)]["mean"]
                             - res["operating_points"][op]["cells"][str(t)]["learners"]
                             ["sampling"]["mean"]) < 1e-6 for t in TCCS)
            bench_ok = all(v.get("reproduces_frozen_arl") for v in bnulls.values())
            rec["reproduction_check"][op] = {
                "sampling_null_reproduces": bool(arl_ok),
                "sampling_delays_reproduce": bool(dly_ok),
                "benchmark_nulls_reproduce": bool(bench_ok)}
            if not (arl_ok and dly_ok and bench_ok):
                problems.append(f"{op}: curve does not reproduce the frozen measurements")
        else:
            problems.append(f"{op}: grid omits sampling's calibrated threshold")

        for t in TCCS:
            cell = res["operating_points"][op]["cells"][str(t)]
            dly_stack = np.stack([np.asarray(curve[k]["delays"][str(t)]["runs"], float)
                                  for k in keys])                                # G x Rd
            Rd = dly_stack.shape[1]
            Rn = null_stack.shape[1]
            for rung in ("L1", "L2"):
                e = cell["benchmarks"][rung]
                if e["is_a_learner"]:
                    continue
                bm = e["member"]
                key = f"{op}/tau_c={t}/{rung}"
                if bm not in bnulls:
                    problems.append(f"{key}: no per-replicate null runs for benchmark {bm}")
                    continue
                bm_null = np.asarray(bnulls[bm]["runs"], float)
                bm_dly = np.asarray(ev[f"{bm}|{t}"]["runs"], float)
                target = float(bm_null.mean())

                needs = res["calibration_confound_checked"]["cells"].get(key, {}).get(
                    "status") == "requires_measured_sensitivity"
                if not (arls.min() <= target <= arls.max()):
                    problems.append(f"{key}: target ARL {target:.0f} outside the measured grid "
                                    f"[{arls.min():.0f}, {arls.max():.0f}]; protocol forbids "
                                    f"extrapolation" if needs else
                                    f"{key}: target outside grid (cell does not require matching)")
                    rec["cells"][key] = {"benchmark": bm, "benchmark_arl": target,
                                         "status": "NOT_MATCHABLE", "required_matching": needs}
                    continue

                # ---- point estimate under the frozen rule ----
                h_m = invert(hs, np.log(arls), np.log(target))
                d_m = float(np.interp(h_m, hs, dly_stack.mean(1)))
                point = d_m / float(bm_dly.mean())

                # ---- joint bootstrap ----
                rng = np.random.default_rng(RNG_SEED + int(t) + sum(map(ord, bm)))
                ratios, unb = np.empty(B), 0
                for b in range(B):
                    ni = rng.integers(0, Rn, Rn)          # shared across grid thresholds
                    bi = rng.integers(0, Rn, Rn)
                    di = rng.integers(0, Rd, Rd)          # paired: sampling AND benchmark
                    a_b = null_stack[:, ni].mean(1)
                    tgt_b = bm_null[bi].mean()
                    hm = invert(hs, np.log(a_b), np.log(max(tgt_b, 1.0)))
                    if hm is None:
                        unb += 1
                        hm = hs[0] if tgt_b < a_b[0] else hs[-1]
                    dm = np.interp(hm, hs, dly_stack[:, di].mean(1))
                    ratios[b] = dm / bm_dly[di].mean()
                lo, hi = np.percentile(ratios, [2.5, 97.5])
                frozen = e["vs_learner"]["sampling"]
                rec["cells"][key] = {
                    "benchmark": bm,
                    "benchmark_arl": target,
                    "h_sampling_matched": float(h_m),
                    "h_sampling_as_calibrated": hstar,
                    "delay_sampling_matched": d_m,
                    "delay_sampling_as_calibrated": float(
                        cell["learners"]["sampling"]["mean"]),
                    "delay_benchmark": float(bm_dly.mean()),
                    "ratio": float(point),
                    "ci95": [float(lo), float(hi)],
                    "resolved": bool(lo > 1.0 or hi < 1.0),
                    "direction": ("sampling slower" if lo > 1.0 else
                                  "sampling faster" if hi < 1.0 else "unresolved"),
                    "frozen_ratio_at_own_calibration": frozen["ratio_learner_over_benchmark"],
                    "frozen_ci95": frozen["ci95"],
                    "conclusion_survives_matching": bool((lo > 1.0) == (frozen["ci95"][0] > 1.0)),
                    "required_matching": bool(needs),
                    "draws_needing_end_extrapolation": int(unb),
                    "status": "MATCHED",
                }
                # Draws whose resampled target falls off the resampled curve are handled by the
                # end segment. That is a within-draw extrapolation, so it is disclosed per cell.
                # It BLOCKS only where the cell's negative conclusion depends on matching;
                # elsewhere it is recorded and the cell is read with that caveat.
                if unb > 0.05 * B and needs:
                    problems.append(f"{key}: {unb}/{B} bootstrap draws fell outside the "
                                    f"resampled grid, and this cell REQUIRES matching")
                elif unb > 0.05 * B:
                    rec["cells"][key]["elevated_draw_extrapolation"] = (
                        f"{100*unb/B:.1f} % of draws fell outside the resampled grid and used "
                        f"the end segment; the interval for this cell is correspondingly less "
                        f"trustworthy. This cell does not require matching.")

    rec["digest"] = digest_of(rec)
    for k, v in sorted(rec["cells"].items()):
        if v.get("status") != "MATCHED":
            print(f"{k:28s} {v['status']}  (required={v['required_matching']})")
            continue
        flip = "" if v["conclusion_survives_matching"] else "   <-- CONCLUSION CHANGES"
        req = "*" if v["required_matching"] else " "
        print(f"{req}{k:27s} vs {v['benchmark']:15s} ARL={v['benchmark_arl']:7.0f} "
              f"h_m={v['h_sampling_matched']:.4f} D_s={v['delay_sampling_matched']:7.0f} "
              f"D_b={v['delay_benchmark']:7.0f} ratio={v['ratio']:.3f} "
              f"[{v['ci95'][0]:.3f},{v['ci95'][1]:.3f}] {v['direction']}{flip}")
    print(f"\nreproduction: {rec['reproduction_check']}")
    if problems:
        print("\nPROBLEMS:", file=sys.stderr)
        for p in problems:
            print("   ", p, file=sys.stderr)
    print(f"digest {rec['digest']}")
    if write and not problems:
        OUT.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"written to {OUT.relative_to(ROOT)}")
    elif write:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
