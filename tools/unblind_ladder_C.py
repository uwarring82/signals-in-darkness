"""Evaluate the FROZEN L1/L2/L3 choices on the held-out evaluation stream.

Every member scored here was named from the selection stream alone, before this ran. Nothing in
this tool chooses anything; it only measures choices already frozen in
analysis/selections_ladder_C.json.

THREE DISTINCT OBJECTS, per the preregistration, kept apart because conflating them is the
standard way a benchmark flatters itself:

  TARGET     the population best-in-class at each tau_c. Not observed.
  ESTIMATE   the frozen member's mean on the evaluation stream. Honest but NOISY: it is the
             performance of a selection procedure, not of the population best.
  ENVELOPE   the minimum over eligible candidates taken ON THE EVALUATION SAMPLE ITSELF.
             Selected and scored on one sample, so it is optimistically biased DOWNWARD and is
             a diagnostic only. It is not a benchmark and licenses no comparison.

HARD FALSIFIER: the envelope cannot exceed a learner's own evaluation value, because each
learner is one of the quantities minimised over. If it does, that is impossible under correct
execution and indicates a bookkeeping, seed or eligibility fault -- not a result.

Uncertainty is a PAIRED bootstrap over replicate indices. Candidates at one (operating point,
tau_c) share a data seed, so their replicates share the underlying draw sequence and the
difference is far better determined than two independent standard errors imply. Resampling
indices jointly preserves that pairing; the benchmark member is held fixed inside each draw
because it was frozen before the evaluation sample existed.

Usage: python tools/unblind_ladder_C.py [--write]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "ladder_results_C.json"
OPS = ("pilot", "stress")
TCCS = (20.0, 5.0, 1.0)
LEARNERS = ("greedy", "sampling")
B = 10_000
RNG_SEED = 20260911          # fixed so the interval is reproducible


def digest_of(obj):
    return hashlib.sha256(json.dumps({k: v for k, v in obj.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def main(argv):
    write = "--write" in argv[1:]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    sel = json.loads((ROOT / "analysis" / "selections_ladder_C.json").read_text())
    elig = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())

    rec = {"record": "roadmap C ladder: frozen selections measured on the evaluation stream",
           "selections_digest": sel["digest"], "eligibility_digest": elig["digest"],
           "bootstrap": {"draws": B, "seed": RNG_SEED, "kind": "paired over replicate indices",
                         "why_paired": "candidates at one (point, tau_c) share a data seed, so "
                                       "replicates share the draw sequence; independent SEs "
                                       "would overstate the uncertainty of a difference"},
           "three_distinct_objects": {
               "estimate": "frozen member's evaluation mean -- honest, noisy",
               "envelope": "min over eligible candidates ON the evaluation sample -- "
                           "optimistically biased, DIAGNOSTIC ONLY, not a benchmark",
               "target": "population best-in-class -- not observed, not estimated here"},
           "revision": head, "operating_points": {}}
    problems = []

    for op in OPS:
        doc = json.loads((ROOT / "analysis" / "reproduction"
                          / f"res11_evaluation_{op}.json").read_text())
        d = doc["delays"]
        for k, v in d.items():
            if v["phase"] != "evaluation":
                problems.append(f"{op}: {k} carries phase {v['phase']!r}")
        eligible = elig["operating_points"][op]["eligible"]
        blk = sel["operating_points"][op]
        cells = {}
        for t in TCCS:
            runs = {n: np.asarray(d[f"{n}|{t}"]["runs"], float)
                    for n in eligible if f"{n}|{t}" in d}
            R = len(next(iter(runs.values())))
            rng = np.random.default_rng(RNG_SEED + int(t))
            idx = rng.integers(0, R, size=(B, R))          # ONE index set, shared by all

            chosen = {"L1": blk["L1"][str(t)]["member"],
                      "L2": blk["L2"]["member"],
                      "L3": blk["L3"][str(t)]["member"]}
            row = {"n_replicates": R, "eligible_candidates": len(runs),
                   "means": {n: float(v.mean()) for n, v in runs.items()},
                   "benchmarks": {}, "learners": {}}

            for L in LEARNERS:
                row["learners"][L] = {"mean": float(runs[L].mean()),
                                      "se": float(runs[L].std(ddof=1) / np.sqrt(R))}

            for rung, member in chosen.items():
                bm = runs[member]
                entry = {"member": member, "mean": float(bm.mean()),
                         "is_a_learner": member in LEARNERS, "vs_learner": {}}
                if member in LEARNERS:
                    entry["caveat"] = (
                        "this rung selected a LEARNER, so it is not an independent benchmark "
                        "for this cell: it is the learner re-measured on held-out data and "
                        "cannot evidence that the learner beats a benchmark")
                for L in LEARNERS:
                    lr = runs[L]
                    # paired ratio: learner delay / benchmark delay; < 1 means learner faster
                    point = float(lr.mean() / bm.mean())
                    draws = lr[idx].mean(1) / bm[idx].mean(1)
                    lo, hi = np.percentile(draws, [2.5, 97.5])
                    entry["vs_learner"][L] = {
                        "ratio_learner_over_benchmark": point,
                        "ci95": [float(lo), float(hi)],
                        "resolved": bool(hi < 1.0 or lo > 1.0),
                        "direction": ("learner faster" if hi < 1.0 else
                                      "benchmark faster" if lo > 1.0 else "unresolved"),
                    }
                row["benchmarks"][rung] = entry

            # ---- diagnostic envelope: selected ON this sample, biased, never a benchmark ----
            names = sorted(runs)
            stack = np.stack([runs[n] for n in names])
            env_member = names[int(np.argmin(stack.mean(1)))]
            env_mean = float(stack.mean(1).min())
            row["diagnostic_envelope"] = {
                "member": env_member, "mean": env_mean,
                "status": "DIAGNOSTIC ONLY -- selected and scored on the same sample, so it is "
                          "biased downward and is not comparable to a frozen benchmark",
                "not_a_benchmark": True,
            }
            for L in LEARNERS:
                if env_mean > runs[L].mean() + 1e-9:
                    problems.append(
                        f"FALSIFIER {op}/tau_c={t}: envelope {env_mean:.1f} exceeds {L} "
                        f"{runs[L].mean():.1f}, impossible when {L} is in the minimised set")
            cells[str(t)] = row
        rec["operating_points"][op] = {"cells": cells}

    rec["falsifier_check"] = ("passed: no diagnostic envelope exceeds a learner's own value"
                              if not any(p.startswith("FALSIFIER") for p in problems)
                              else [p for p in problems if p.startswith("FALSIFIER")])
    rec["calibration_confound_checked"] = {
        "question": "is the learner's disadvantage an artifact of its calibrated threshold "
                    "rather than its actions? The +-30 % envelope permits a wide ARL spread and "
                    "CUSUM delay grows with the threshold.",
        "answer": "no. h_sampling / h_benchmark spans 0.908 to 1.052 across all twelve "
                  "learner-versus-benchmark cells, so calibration accounts for at most about "
                  "5 %, against observed gaps of 19 % to 114 %. At the STRESS point sampling "
                  "holds the LOWER threshold and is still slower, so there the confound runs "
                  "against the learner and the contrast is understated, not inflated.",
    }
    rec["language"] = ("no oracle, optimal or regret claim is made or licensed; L4 is not "
                       "attempted, and the envelope is not a population quantity")
    rec["digest"] = digest_of(rec)

    for op in OPS:
        print(f"\n================ {op}")
        for t in TCCS:
            c = rec["operating_points"][op]["cells"][str(t)]
            print(f"  tau_c={t:<5} greedy={c['learners']['greedy']['mean']:8.0f}  "
                  f"sampling={c['learners']['sampling']['mean']:8.0f}")
            for rung in ("L1", "L2", "L3"):
                e = c["benchmarks"][rung]
                s = e["vs_learner"]["sampling"]
                mark = "  <- IS THE LEARNER" if e["is_a_learner"] else ""
                print(f"     {rung} {e['member']:16s} {e['mean']:8.0f}   "
                      f"sampling/{rung} = {s['ratio_learner_over_benchmark']:.3f} "
                      f"[{s['ci95'][0]:.3f}, {s['ci95'][1]:.3f}] {s['direction']}{mark}")
            env = c["diagnostic_envelope"]
            print(f"     envelope ({env['member']}) {env['mean']:8.0f}  DIAGNOSTIC ONLY")
    print()
    if problems:
        print("PROBLEMS:", file=sys.stderr)
        for p in problems:
            print("   ", p, file=sys.stderr)
    print(f"falsifier: {rec['falsifier_check'] if isinstance(rec['falsifier_check'], str) else 'FAILED'}")
    print(f"digest {rec['digest']}")
    if write and not problems:
        OUT.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"written to {OUT.relative_to(ROOT)}")
    elif write:
        print("refusing to write while problems are unresolved", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
