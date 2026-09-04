"""Reproduction-route support: separates the published archive from mutable state.

Purpose   : keep three things apart that sid_run6s.py conflated at tag
            archive-2026-09-03 -- (a) the published reference outputs under
            analysis/outputs/, (b) mutable resume checkpoints, and (c) the fresh
            results of the run you just performed. It also supplies the declared
            tolerances used to compare (c) against (a), and the provenance banner
            every reproduction run must print.
Inputs    : none.
Seeds     : none.
Outputs   : none directly; hands callers the paths to write under.
Runtime   : negligible.

Why this exists: notes/2026-09-03-note-04-reproduction-defect.md. The rule is that
a run script never writes into analysis/outputs/. Fresh results and checkpoints go
to analysis/reproduction/, which is ignored by git, and are then COMPARED against
the archive rather than silently replacing or replaying it.

Declared tolerances (see compare_rows):
  threshold h*  exact equality. The bisection is deterministic given the recorded
                seeds, so any difference is a different code path or a different
                seed, never Monte-Carlo noise. This is the test that catches a
                transcribed row; the mean test alone does not.
  means         |fresh - reference| <= SIGMA_TOL * sqrt(se_fresh^2 + se_ref^2),
                with SIGMA_TOL = 3.
  capped runs   reported, never gated (a cap change is diagnostic, not a verdict).
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time

SIGMA_TOL = 3.0

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
REFERENCE_DIR = os.path.join(REPO_ROOT, "analysis", "outputs")
REPRODUCTION_DIR = os.path.join(REPO_ROOT, "analysis", "reproduction")


def reference_path(name):
    """Path to a published reference output. Read-only for every run script."""
    return os.path.join(REFERENCE_DIR, name)


def reproduction_path(name):
    """Path a fresh run writes to. Created on demand; ignored by git."""
    os.makedirs(REPRODUCTION_DIR, exist_ok=True)
    return os.path.join(REPRODUCTION_DIR, name)


def load_reference(name):
    p = reference_path(name)
    return json.load(open(p)) if os.path.exists(p) else None


def load_checkpoint(name, resume):
    """Fresh by default. Only --resume reads back a previous partial run."""
    if not resume:
        return None
    p = os.path.join(REPRODUCTION_DIR, name)
    return json.load(open(p)) if os.path.exists(p) else None


def write_json(path, obj, **kw):
    """Write JSON atomically: a temporary file in the same directory, then os.replace.

    An interrupted write must not leave a half-written file that later parses as valid JSON
    with truncated content, or that fails to parse at all and is mistaken for a missing run.
    os.replace is atomic within a filesystem.
    """
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(obj, fh, **kw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def save_checkpoint(name, state):
    write_json(reproduction_path(name), state)


# ---- binding a stage's output to the run that produced it ----
# Calibration thresholds are a required output of the current reproduction, not anonymous
# reusable state. The delay stage must be able to tell "the cal stage of this run" from
# "some thresholds someone left on disk", so the checkpoint carries the identity of the run
# that wrote it and the delay stage refuses anything that does not match.

def run_metadata(config):
    prov = provenance()
    ident = hashlib.sha256(json.dumps(
        {"revision": prov["revision"], "python": prov["python"], "numpy": prov["numpy"],
         "scipy": prov["scipy"], "config": config}, sort_keys=True, default=str
    ).encode()).hexdigest()[:12]
    return {"run_id": ident, "revision": prov["revision"], "python": prov["python"],
            "numpy": prov["numpy"], "scipy": prov["scipy"], "config": config,
            "written": prov["started"]}


def incompatibilities(have, want):
    """Return the reasons `have` may not be consumed by a stage expecting `want`."""
    if not have:
        return ["the thresholds carry no run metadata (written by an older version?)"]
    out = []
    for field in ("revision", "python", "numpy", "scipy"):
        if have.get(field) != want.get(field):
            out.append(f"{field}: thresholds {have.get(field)!r} vs this run {want.get(field)!r}")
    hc, wc = have.get("config") or {}, want.get("config") or {}
    for key in sorted(set(hc) | set(wc)):
        if key == "policies":
            missing = [p for p in (wc.get("policies") or []) if p not in (hc.get("policies") or [])]
            if missing:
                out.append(f"config.policies: no threshold for {', '.join(missing)}")
        elif hc.get(key) != wc.get(key):
            out.append(f"config.{key}: thresholds {hc.get(key)!r} vs this run {wc.get(key)!r}")
    return out


def provenance():
    try:
        rev = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
        dirty = subprocess.run(["git", "-C", REPO_ROOT, "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        rev, dirty = "unknown", ""
    versions = {}
    for mod in ("numpy", "scipy", "matplotlib"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:
            versions[mod] = "absent"
    # Platform is part of the provenance, not a footnote: the same pins on a different
    # architecture, or under translation, are a different numerical stack.
    try:
        blas = numpy_blas()
    except Exception:
        blas = "unknown"
    return {
        "revision": rev + ("+dirty" if dirty else ""),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "blas": blas,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        **versions,
    }


def numpy_blas():
    """Name and version of the BLAS numpy was built against, or 'unknown'."""
    import numpy as _np
    try:
        cfg = _np.show_config("dicts") or {}
        b = (cfg.get("Build Dependencies") or {}).get("blas") or {}
        name, ver = b.get("name"), b.get("version")
        return f"{name} {ver}".strip() or "unknown"
    except Exception:
        return "unknown"


def print_banner(stage, resume, seeds, prov=None):
    prov = prov or provenance()
    print(f"# stage        : {stage}")
    print(f"# mode         : {'resume (reuses analysis/reproduction/)' if resume else 'fresh (recomputes everything)'}")
    print(f"# revision     : {prov['revision']}")
    print(f"# environment  : python {prov['python']}, numpy {prov['numpy']}, scipy {prov['scipy']}, "
          f"matplotlib {prov['matplotlib']}")
    print(f"# platform     : {prov['platform']} | machine {prov['machine']} | blas {prov['blas']}")
    print(f"# seeds        : {seeds}")
    print(f"# reference    : {os.path.relpath(REFERENCE_DIR, REPO_ROOT)} (read-only)")
    print(f"# writes to    : {os.path.relpath(REPRODUCTION_DIR, REPO_ROOT)}")
    print(f"# started      : {prov['started']}", flush=True)
    return prov


def compare_rows(fresh, reference, threshold_index=0, mean_index=1, se_index=2, label="row"):
    """Compare fresh rows against reference rows under the declared tolerances.

    Each row is a list [threshold, mean, se, capped] (calibration) or
    [mean, se, capped] (delays, with threshold_index=None).
    Returns (verdicts, n_pass, n_fail) where a verdict is a printable string.
    """
    verdicts, n_pass, n_fail = [], 0, 0
    for name in sorted(fresh):
        f = fresh[name]
        r = (reference or {}).get(name)
        if r is None:
            verdicts.append(f"  NO-REFERENCE  {label} {name}: nothing archived to compare against")
            continue
        problems = []
        if threshold_index is not None:
            hf, hr = f[threshold_index], r[threshold_index]
            if hf != hr:
                problems.append(f"threshold h* {hf!r} != archived {hr!r} (exact match required)")
        mf, sf = f[mean_index], f[se_index]
        mr, sr = r[mean_index], r[se_index]
        spread = (sf*sf + sr*sr) ** 0.5
        dev = abs(mf - mr)
        nsig = dev/spread if spread > 0 else float("inf")
        if dev > SIGMA_TOL*spread:
            problems.append(f"mean {mf:.1f} vs archived {mr:.1f} = {nsig:.2f} sigma > {SIGMA_TOL:.0f}")
        if problems:
            n_fail += 1
            verdicts.append(f"  FAIL  {label} {name}: " + "; ".join(problems))
        else:
            n_pass += 1
            verdicts.append(f"  pass  {label} {name}: mean {mf:.1f} vs {mr:.1f} ({nsig:.2f} sigma)")
    return verdicts, n_pass, n_fail


def report(computed, cached, verdicts, n_pass, n_fail, elapsed):
    print(f"\ncomputed: {computed}, cached: {cached}")
    print(f"runtime: {elapsed:.0f} s")
    print("comparison against the published archive (declared tolerances: h* exact, "
          f"means within {SIGMA_TOL:.0f} sigma):")
    for v in verdicts:
        print(v)
    print(f"summary: {n_pass} pass, {n_fail} FAIL")
    return 1 if n_fail else 0
