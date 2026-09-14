"""Compare sampling against each benchmark AT THE BENCHMARK'S OWN NULL ARL.

The ladder calibrates every policy to within +-30 % of one target E_0[T]. That is a band, not a
match, and a policy with a longer null ARL is harder to trip and so detects later. Where sampling
holds the LONGER ARL, that mismatch could manufacture the observed negative result, and no
threshold ratio can rule it out: different policies have different null increment distributions,
so h is not a common currency between them.

This reads sampling's delay off a MEASURED delay-versus-ARL curve at the benchmark's own ARL.

Two uncertainties are carried, where the frozen ladder intervals carried only the first:
  sampling error   paired bootstrap over replicate indices, shared between sampling and the
                   benchmark because they share the evaluation data seed
  calibration      every ARL entering the interpolation -- the benchmark's and each grid
                   point's -- is perturbed by its own standard error inside each draw, so the
                   interval no longer conditions on the calibrations being exactly right

Per-replicate interpolation is used rather than mean interpolation: the two bracketing grid
points are the same policy on the same data seed, so their replicates are strongly paired and
interpolating them individually preserves that pairing.

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


def main(argv):
    write = "--write" in argv[1:]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    elig = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())
    res = json.loads((ROOT / "analysis" / "ladder_results_C.json").read_text())

    rec = {"record": "sampling versus each benchmark at the benchmark's own null ARL",
           "why": "the +-30 % envelope is a band, not a match; a longer null ARL is harder to "
                  "trip and detects later, which is a confound in the direction that would "
                  "manufacture the ladder's negative result",
           "why_not_h_ratios": "different policies have different null increment distributions, "
                               "so equal h is not equal false-alarm rate and an h ratio bounds "
                               "nothing",
           "uncertainty": "paired bootstrap over replicates PLUS calibration uncertainty: every "
                          "ARL entering the interpolation is perturbed by its standard error "
                          "inside each draw",
           "ladder_results_digest": res["digest"], "eligibility_digest": elig["digest"],
           "revision": head, "cells": {}, "reproduction_check": {}}
    problems = []

    for op in OPS:
        p = ROOT / "analysis" / "reproduction" / f"res12_sensitivity_{op}.json"
        if not p.exists():
            problems.append(f"{op}: no sensitivity curve")
            continue
        curve = json.loads(p.read_text())["points"]
        cal = elig["operating_points"][op]["calibrations"]
        hs = cal["sampling"]["h_star"]

        # The grid includes sampling's own calibrated threshold: that point must reproduce the
        # frozen null and evaluation measurements exactly, or the curve is not the same policy.
        key = min(curve, key=lambda k: abs(float(k) - hs))
        pt = curve[key]
        if abs(float(key) - hs) < 1e-9:
            arl_ok = abs(pt["arl"] - cal["sampling"]["ARL"]) < 1e-6
            dly_ok = all(
                abs(pt["delays"][str(t)]["mean"]
                    - res["operating_points"][op]["cells"][str(t)]["learners"]["sampling"]["mean"])
                < 1e-6 for t in TCCS)
            rec["reproduction_check"][op] = {
                "grid_point_at_calibrated_threshold": float(key),
                "null_arl_reproduces": bool(arl_ok), "delays_reproduce": bool(dly_ok)}
            if not (arl_ok and dly_ok):
                problems.append(f"{op}: the curve's calibrated-threshold point does not "
                                f"reproduce the frozen measurements")
        else:
            problems.append(f"{op}: grid omits the calibrated threshold {hs!r}")

        hs_sorted = sorted(curve, key=lambda k: curve[k]["arl"])
        arls = np.array([curve[k]["arl"] for k in hs_sorted])
        arl_ses = np.array([curve[k]["arl_se"] for k in hs_sorted])

        for t in TCCS:
            cell = res["operating_points"][op]["cells"][str(t)]
            runs = {k: np.asarray(curve[k]["delays"][str(t)]["runs"], float) for k in hs_sorted}
            R = len(next(iter(runs.values())))
            for rung in ("L1", "L2"):
                e = cell["benchmarks"][rung]
                if e["is_a_learner"]:
                    continue
                bm_name = e["member"]
                tgt, tgt_se = cal[bm_name]["ARL"], cal[bm_name]["se"]
                bm_runs = np.asarray(
                    json.loads((ROOT / "analysis" / "reproduction"
                                / f"res11_evaluation_{op}.json").read_text()
                               )["delays"][f"{bm_name}|{t}"]["runs"], float)

                lo_a, hi_a = arls.min(), arls.max()
                extrapolated = not (lo_a <= tgt <= hi_a)
                rng = np.random.default_rng(RNG_SEED + int(t) + len(bm_name))
                idx = rng.integers(0, R, size=(B, R))
                a_draw = arls[None, :] + rng.normal(0, 1, (B, len(arls))) * arl_ses[None, :]
                t_draw = tgt + rng.normal(0, tgt_se, B)
                stack = np.stack([runs[k] for k in hs_sorted])          # G x R

                ratios = np.empty(B)
                for b in range(B):
                    order = np.argsort(a_draw[b])
                    la, ls = np.log(np.maximum(a_draw[b][order], 1.0)), stack[order]
                    lt = np.log(max(t_draw[b], 1.0))
                    j = int(np.clip(np.searchsorted(la, lt) - 1, 0, len(la) - 2))
                    w = (lt - la[j]) / (la[j + 1] - la[j]) if la[j + 1] != la[j] else 0.0
                    interp = (1 - w) * ls[j] + w * ls[j + 1]            # per replicate
                    ratios[b] = interp[idx[b]].mean() / bm_runs[idx[b]].mean()

                # point estimate at the unperturbed ARLs
                la, lt = np.log(arls), np.log(tgt)
                j = int(np.clip(np.searchsorted(la, lt) - 1, 0, len(la) - 2))
                w = (lt - la[j]) / (la[j + 1] - la[j])
                point_runs = (1 - w) * stack[j] + w * stack[j + 1]
                point = float(point_runs.mean() / bm_runs.mean())
                lo, hi = np.percentile(ratios, [2.5, 97.5])
                frozen = e["vs_learner"]["sampling"]
                rec["cells"][f"{op}/tau_c={t}/{rung}"] = {
                    "benchmark": bm_name, "benchmark_arl": tgt, "sampling_arl_as_calibrated":
                        cal["sampling"]["ARL"],
                    "matched_ratio_sampling_over_benchmark": point,
                    "ci95": [float(lo), float(hi)],
                    "resolved": bool(lo > 1.0 or hi < 1.0),
                    "direction": ("sampling slower" if lo > 1.0 else
                                  "sampling faster" if hi < 1.0 else "unresolved"),
                    "frozen_ratio_at_own_calibration": frozen["ratio_learner_over_benchmark"],
                    "frozen_ci95": frozen["ci95"],
                    "conclusion_survives_matching": bool(
                        (lo > 1.0) == (frozen["ci95"][0] > 1.0)),
                    "extrapolated_beyond_grid": bool(extrapolated),
                }
                # Extrapolation only blocks a cell that actually NEEDS matching. A cell where
                # sampling is not resolvedly slower has no negative conclusion to defend, so an
                # unbracketed target there is a gap in coverage, not a fault.
                needs = res["calibration_confound_checked"]["cells"].get(
                    f"{op}/tau_c={t}/{rung}", {}).get("status") == "requires_measured_sensitivity"
                rec["cells"][f"{op}/tau_c={t}/{rung}"]["required_matching"] = bool(needs)
                if extrapolated and needs:
                    problems.append(f"{op}/tau_c={t}/{rung}: target ARL {tgt:.0f} lies outside "
                                    f"the measured grid [{lo_a:.0f}, {hi_a:.0f}] and this cell "
                                    f"REQUIRES matching")
                elif extrapolated:
                    rec["cells"][f"{op}/tau_c={t}/{rung}"]["note"] = (
                        "target ARL outside the measured grid, so the matched figure is an "
                        "extrapolation; this cell does not require matching because sampling is "
                        "not resolvedly slower here")

    rec["digest"] = digest_of(rec)
    for k, v in rec["cells"].items():
        flip = "" if v["conclusion_survives_matching"] else "   <-- CONCLUSION CHANGES"
        ex = "  (EXTRAPOLATED)" if v["extrapolated_beyond_grid"] else ""
        print(f"{k:28s} vs {v['benchmark']:16s} "
              f"own-cal {v['frozen_ratio_at_own_calibration']:.3f} -> matched "
              f"{v['matched_ratio_sampling_over_benchmark']:.3f} "
              f"[{v['ci95'][0]:.3f}, {v['ci95'][1]:.3f}] {v['direction']}{flip}{ex}")
    print(f"\nreproduction check: {rec['reproduction_check']}")
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
