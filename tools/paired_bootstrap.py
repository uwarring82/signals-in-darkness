#!/usr/bin/env python3
"""Paired bootstrap for the worst-case delay-ratio comparison.

The headline statistic of roadmap B is, for each policy, the MAXIMUM over tau_c in {20, 5, 1}
of (its mean delay) / (the best fixed-endpoint benchmark at that tau_c). Comparing two policies
by propagating marginal standard errors gets two things wrong, in opposite directions:

  * PAIRING. Policies measured at one tau_c in res6 share a seed (200 + int(tau_c) + offset),
    so replicate i of every policy sees the same noise realisation. Their delays are positively
    correlated, and a difference between them is measured far better than marginal errors imply.
    Marginal propagation OVERSTATES the uncertainty of a difference.
    The switch policies in res8 use a different seed schedule (500 + int(tau_c) + offset), so
    they are NOT paired with the res6 benchmark and are resampled independently here.

  * SELECTION. The statistic is a maximum over three noisy ratios, and a maximum is biased
    upward: whichever tau_c happens to fluctuate high is the one reported. Marginal propagation
    ignores this entirely, and it does not cancel between two policies whose worst case falls at
    different tau_c.

This resamples replicate indices with replacement, jointly across policies within each source
so the pairing is preserved, recomputes the benchmark, the ratios and the maximum inside every
resample, and reports percentile intervals for the difference against fixed-extremum.

Usage:
    python tools/paired_bootstrap.py <res6.json> <res8.json> [--draws 20000]
"""
import argparse
import json
import os
import sys

import numpy as np

TCCS = ("20.0", "5.0", "1.0")
BASE = ("extremum-only", "learner-mid(bank)",
        "learner-interleave-B10(bank)", "learner-interleave-B1(bank)")


def _runs(row, label):
    if len(row) < 4:
        sys.exit(f"{label} carries no per-replicate stopping times; rerun the delays stage "
                 f"with the version that stores them (delay_of(..., return_runs=True))")
    return np.asarray(row[3], dtype=float)


def load(res6_path, res8_path):
    d6 = json.load(open(res6_path, encoding="utf-8"))
    d8 = json.load(open(res8_path, encoding="utf-8"))
    d8 = d8.get("switch", d8)
    six, eight = {}, {}
    for t in TCCS:
        six[t] = {p: _runs(d6["delays"][t][p], f"res6 {p} @ {t}") for p in d6["delays"][t]}
        eight[t] = {f"switch@{B}": _runs(d8[B][2][t], f"res8 switch@{B} @ {t}") for B in d8}
    return six, eight


def worst_case(six, eight, idx6, idx8):
    """Worst-case ratio per policy under one resample of replicate indices."""
    ratio = {}
    for t in TCCS:
        oracle = f"oracle-mid(tc={int(float(t))})"
        b = min(six[t][oracle][idx6[t]].mean(), six[t]["extremum-only"][idx6[t]].mean())
        for p in BASE:
            ratio.setdefault(p, []).append(six[t][p][idx6[t]].mean() / b)
        for p in eight[t]:
            ratio.setdefault(p, []).append(eight[t][p][idx8[t]].mean() / b)
    return {p: max(v) for p, v in ratio.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("res6")
    ap.add_argument("res8")
    ap.add_argument("--draws", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20260908)
    a = ap.parse_args()

    six, eight = load(a.res6, a.res8)
    n6 = {t: len(next(iter(six[t].values()))) for t in TCCS}
    n8 = {t: len(next(iter(eight[t].values()))) for t in TCCS}

    point = worst_case(six, eight, {t: np.arange(n6[t]) for t in TCCS},
                       {t: np.arange(n8[t]) for t in TCCS})
    rng = np.random.default_rng(a.seed)
    draws = {p: np.empty(a.draws) for p in point}
    for k in range(a.draws):
        i6 = {t: rng.integers(0, n6[t], n6[t]) for t in TCCS}
        i8 = {t: rng.integers(0, n8[t], n8[t]) for t in TCCS}
        w = worst_case(six, eight, i6, i8)
        for p in draws:
            draws[p][k] = w[p]

    print(f"paired bootstrap, {a.draws} draws, replicate indices resampled jointly within each")
    print("source so the shared-seed pairing is preserved; the maximum over tau_c is recomputed")
    print("inside every resample, so selection bias is included.\n")
    # The median is printed because a MAXIMUM of noisy quantities is biased upward: whichever
    # tau_c fluctuates high is the one reported. median > point is that bias, made visible
    # rather than assumed away.
    print(f"{'policy':30s}{'worst case':>12}{'median':>9}{'2.5%':>9}{'97.5%':>9}")
    for p, v in sorted(point.items(), key=lambda x: x[1]):
        lo, med, hi = np.percentile(draws[p], [2.5, 50, 97.5])
        print(f"{p:30s}{v:12.2f}{med:9.2f}{lo:9.2f}{hi:9.2f}")

    ref = "extremum-only"
    print(f"\ndifference from {ref} (positive = the policy is BETTER), paired within source:")
    for p, v in sorted(point.items(), key=lambda x: x[1]):
        if p == ref:
            continue
        d = draws[ref] - draws[p]
        lo, hi = np.percentile(d, [2.5, 97.5])
        frac = float((d > 0).mean())
        verdict = ("RESOLVED better" if lo > 0 else
                   "RESOLVED worse" if hi < 0 else "not resolved")
        print(f"  {p:30s} {point[ref]-v:+6.2f}  [{lo:+6.2f}, {hi:+6.2f}]  "
              f"P(better) = {frac:.3f}   {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
