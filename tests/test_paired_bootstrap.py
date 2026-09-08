"""The estimator behind C11, C27 and C28.

Marginal error propagation is wrong here in two opposite ways: policies at one tau_c share a
seed so their runs are PAIRED (which makes a difference better measured than marginal errors
imply), and the statistic is a MAXIMUM over three correlation times (which is biased upward by
selection). These tests pin both properties on synthetic data where the answer is known, and
then assert the published artifacts still carry what the estimator needs.
"""
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TOOL = os.path.join(ROOT, "tools", "paired_bootstrap.py")
TCCS = ("20.0", "5.0", "1.0")


def test_every_published_policy_artifact_carries_per_replicate_runs():
    """Without them the bootstrap cannot run, and only marginal errors are available."""
    for name in ("res6_policies_pilot_recal.json", "res6_policies_stress.json"):
        doc = json.load(open(os.path.join(ROOT, "analysis", "outputs", name), encoding="utf-8"))
        for t, row in doc["delays"].items():
            for policy, cell in row.items():
                assert len(cell) >= 4, f"{name}: {policy}@{t} has no per-replicate stopping times"
                assert len(cell[3]) == 64, f"{name}: {policy}@{t} stores {len(cell[3])} runs"
                assert abs(np.mean(cell[3]) - cell[0]) < 1e-9, (
                    f"{name}: {policy}@{t} stored runs disagree with the stored mean")
    for name in ("res8_switch_pilot_recal.json", "res8_switch_stress.json"):
        doc = json.load(open(os.path.join(ROOT, "analysis", "outputs", name), encoding="utf-8"))
        for B, row in doc.get("switch", doc).items():
            for t, cell in row[2].items():
                assert len(cell) >= 4, f"{name}: switch@{B}@{t} has no per-replicate runs"
                assert abs(np.mean(cell[3]) - cell[0]) < 1e-9


def test_the_published_artifacts_keep_their_calibration_and_identity():
    """A delays-only re-run once overwrote res6_policies_stress.json, leaving zero cal rows and
    no run identity. Attaching per-replicate runs must never cost the calibration block."""
    for name in ("res6_policies_pilot_recal.json", "res6_policies_stress.json"):
        doc = json.load(open(os.path.join(ROOT, "analysis", "outputs", name), encoding="utf-8"))
        assert len(doc["cal"]) == 7, f"{name} has {len(doc['cal'])} calibration rows, expected 7"
        meta = doc["meta"]
        assert meta.get("run_id") and meta.get("revision"), f"{name} lost its run identity"
        assert not meta["revision"].endswith("+dirty"), f"{name} was produced from a dirty tree"


def _synthetic(tmp_path, paired, worse_at):
    """Two policies and a benchmark, with a known truth. `paired` controls whether the two
    policies see the same replicate noise."""
    tmp_path = pathlib.Path(tmp_path); tmp_path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(4)
    n = 64
    six, eight = {}, {}
    for t in TCCS:
        shared = rng.normal(0, 200, n)
        bench = 1000 + shared
        extra = shared if paired else rng.normal(0, 200, n)
        hedge = (1000 + 60 * (worse_at is None or t == worse_at)) + extra
        six[t] = {f"oracle-mid(tc={int(float(t))})": [float(bench.mean()), 0.0, 0, bench.tolist()],
                  "extremum-only": [float(bench.mean()), 0.0, 0, bench.tolist()],
                  "learner-mid(bank)": [float(hedge.mean()), 0.0, 0, hedge.tolist()],
                  "learner-interleave-B10(bank)": [float(hedge.mean()), 0.0, 0, hedge.tolist()],
                  "learner-interleave-B1(bank)": [float(hedge.mean()), 0.0, 0, hedge.tolist()]}
        eight[t] = [0.0, 3.0e4, {}]
    d6 = {"cal": {}, "delays": six, "meta": {}}
    d8 = {"switch": {"300": [0.0, 3.0e4, {t: [1000.0, 0.0, 0, [1000.0] * n] for t in TCCS}],
                     "1000": [0.0, 3.0e4, {t: [1000.0, 0.0, 0, [1000.0] * n] for t in TCCS}]}}
    p6 = tmp_path / "r6.json"; p6.write_text(json.dumps(d6))
    p8 = tmp_path / "r8.json"; p8.write_text(json.dumps(d8))
    return str(p6), str(p8)


def test_pairing_narrows_the_interval_it_is_entitled_to_narrow(tmp_path):
    """Identical policies differing only by a constant offset: when their runs are paired the
    difference is measured far better than when they are independent."""
    widths = {}
    for paired in (True, False):
        p6, p8 = _synthetic(tmp_path / f"p{int(paired)}", paired, "20.0")
        r = subprocess.run([sys.executable, TOOL, p6, p8, "--draws", "3000"],
                           capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stderr
        line = [l for l in r.stdout.splitlines() if "learner-mid(bank)" in l and "[" in l][0]
        lo, hi = (float(x) for x in line.split("[")[1].split("]")[0].split(","))
        widths[paired] = hi - lo
    assert widths[True] < widths[False], (
        f"pairing did not narrow the interval: paired {widths[True]:.3f} vs "
        f"independent {widths[False]:.3f}; the bootstrap is not preserving the shared indices")


def test_the_maximum_is_taken_inside_each_draw_so_selection_bias_is_carried():
    """A maximum of noisy quantities is biased upward: whichever tau_c fluctuates high is the
    one reported. If worst_case() took the max once outside the resampling loop, the bootstrap
    distribution would centre on the point estimate instead of sitting above it.

    Asserted in-process at full precision. Through the CLI the effect is invisible, because it
    lives in the third decimal and the table prints two -- which is itself worth knowing about
    the printed output.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import paired_bootstrap as pb

    rng = np.random.default_rng(11)
    n = 64
    # three tau_c with INDEPENDENT noise and identical truth: the max over them is pure selection
    six = {t: {} for t in TCCS}
    for t in TCCS:
        bench = 1000 + rng.normal(0, 150, n)
        hedge = 1000 + rng.normal(0, 150, n)
        six[t] = {f"oracle-mid(tc={int(float(t))})": bench, "extremum-only": bench,
                  "learner-mid(bank)": hedge, "learner-interleave-B10(bank)": hedge,
                  "learner-interleave-B1(bank)": hedge}
    eight = {t: {} for t in TCCS}

    full = {t: np.arange(n) for t in TCCS}
    point = pb.worst_case(six, eight, full, full)["learner-mid(bank)"]
    draws = np.empty(3000)
    for k in range(3000):
        idx = {t: rng.integers(0, n, n) for t in TCCS}
        draws[k] = pb.worst_case(six, eight, idx, idx)["learner-mid(bank)"]
    assert float(np.median(draws)) > point, (
        f"the bootstrap median of the maximum ({np.median(draws):.6f}) does not exceed the "
        f"point estimate ({point:.6f}). With three exchangeable tau_c a resampled maximum is "
        f"biased upward, so the max is probably taken once outside the resampling loop.")


def test_the_tool_refuses_artifacts_without_per_replicate_runs(tmp_path):
    d6 = {"cal": {}, "delays": {t: {"oracle-mid(tc=%d)" % int(float(t)): [1.0, 0.0, 0],
                                    "extremum-only": [1.0, 0.0, 0]} for t in TCCS}}
    p6 = tmp_path / "r6.json"; p6.write_text(json.dumps(d6))
    p8 = tmp_path / "r8.json"; p8.write_text(json.dumps({"switch": {}}))
    r = subprocess.run([sys.executable, TOOL, str(p6), str(p8)], capture_output=True, text=True)
    assert r.returncode != 0 and "per-replicate" in (r.stdout + r.stderr)
