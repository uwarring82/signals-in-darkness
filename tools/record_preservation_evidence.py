#!/usr/bin/env python3
"""Record roadmap G's preservation evidence as a committed artifact.

G's central acceptance condition is that making the operating point an explicit object
changed no number: the five valid pilot calibration rows must reproduce the archive under
EXACT threshold equality, and the two rows withdrawn as C17 must still fail.

That evidence lived only in a git-ignored reproduction file and a terminal transcript, so a
clean checkout could neither see it nor check it, and the test guarding it skipped when the
file was absent. This tool freezes the comparison into `analysis/G_preservation_evidence.json`,
which `tests/test_operating_point.py` then asserts unconditionally.

What must be clean is the CALIBRATION: if the numbers came from an uncommitted tree they
cannot be tied to a revision, which is the provenance gap that cost C17 and C18. That is
refused outright. The tree at *recording* time is a weaker matter -- this tool and the test
it feeds cannot be committed before the artifact they gate exists -- so it is recorded
rather than refused, and the artifact says which files were uncommitted when it was written.

Usage:
    python analysis/runs/sid_run6s.py "cal:<all seven policies>"
    python tools/record_preservation_evidence.py
"""
import json
import math
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ARTIFACT = os.path.join(ROOT, "analysis", "G_preservation_evidence.json")

WITHDRAWN_ROWS = ("oracle-mid(tc=20)", "learner-interleave-B10(bank)")
PRESERVED_ROWS = ("oracle-mid(tc=5)", "oracle-mid(tc=1)", "extremum-only",
                  "learner-mid(bank)", "learner-interleave-B1(bank)")


def main():
    fresh_path = os.path.join(ROOT, "analysis", "reproduction", "res6_policies.json")
    if not os.path.exists(fresh_path):
        sys.exit("no fresh calibration at analysis/reproduction/res6_policies.json; "
                 "run the cal: stage of sid_run6s.py first")
    fresh_doc = json.load(open(fresh_path, encoding="utf-8"))
    fresh, meta = fresh_doc["cal"], fresh_doc.get("meta") or {}
    ref = json.load(open(os.path.join(ROOT, "analysis", "outputs", "res6_policies.json"),
                         encoding="utf-8"))["cal"]

    # The load-bearing check: the numbers must come from a committed tree.
    if meta.get("revision", "").endswith("+dirty"):
        sys.exit(f"the calibration was run from a dirty tree ({meta['revision']}); rerun it "
                 "from the committed state, or the evidence names no real revision")
    revision = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    # NOT .strip(): porcelain lines begin with a two-character status field, and stripping
    # the whole output removes the leading space of the FIRST line, shifting its path by one
    # character. A provenance record that mangles filenames is not a provenance record.
    dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    uncommitted = sorted(line[3:] for line in dirty.splitlines() if line.strip())

    missing = [r for r in PRESERVED_ROWS + WITHDRAWN_ROWS if r not in fresh]
    if missing:
        sys.exit(f"the fresh calibration does not cover all seven pilot policies: {missing}")

    rows = []
    for name in PRESERVED_ROWS + WITHDRAWN_ROWS:
        f, a = fresh[name], ref[name]
        sigma = abs(f[1] - a[1]) / math.sqrt(f[2] ** 2 + a[2] ** 2) if (f[2] or a[2]) else 0.0
        rows.append({
            "policy": name,
            "class": "preserved" if name in PRESERVED_ROWS else "withdrawn-C17",
            "h_fresh": f[0], "h_archive": a[0], "h_exact_match": f[0] == a[0],
            "arl_fresh": f[1], "arl_archive": a[1], "arl_sigma": sigma,
            "verdict": "pass" if f[0] == a[0] else "FAIL (expected for withdrawn rows)",
        })

    doc = {
        "artifact": "roadmap G preservation evidence",
        "what_it_shows": ("Making the operating point an explicit immutable object changed no "
                          "number. The five valid pilot calibration rows reproduce the archive "
                          "under exact threshold equality; the two rows withdrawn as C17 still "
                          "fail, which is required, and they are excluded from the preservation "
                          "claim by name rather than by outcome."),
        "recorded_at_revision": revision,
        "tree_clean_at_recording": not uncommitted,
        "uncommitted_when_recorded": uncommitted,
        "note_on_cleanliness": ("The CALIBRATION revision is the one that matters and is "
                                "asserted clean. The recording tree may hold this tool and its "
                                "test, which cannot be committed before the artifact they gate "
                                "exists; those files are listed rather than silently allowed."),
        "calibration_run": {k: meta.get(k) for k in
                            ("run_id", "revision", "python", "numpy", "scipy", "matplotlib",
                             "machine", "platform", "blas", "written")},
        "operating_point": (meta.get("config") or {}).get("operating_point"),
        "comparison": "h* by exact equality; ARL means reported with their combined-sigma distance",
        "preserved_rows": list(PRESERVED_ROWS),
        "withdrawn_rows_excluded_by_name": list(WITHDRAWN_ROWS),
        "counts": {
            "preserved_exact": sum(1 for r in rows if r["class"] == "preserved" and r["h_exact_match"]),
            "preserved_total": len(PRESERVED_ROWS),
            "withdrawn_failing": sum(1 for r in rows if r["class"] == "withdrawn-C17"
                                     and not r["h_exact_match"]),
            "withdrawn_total": len(WITHDRAWN_ROWS),
        },
        "rows": rows,
    }
    tmp = ARTIFACT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, allow_nan=False)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, ARTIFACT)

    c = doc["counts"]
    print(f"wrote {ARTIFACT}")
    print(f"  revision {revision[:12]}, calibration run {meta.get('run_id')} on "
          f"python {meta.get('python')} / numpy {meta.get('numpy')}")
    print(f"  preserved exact: {c['preserved_exact']}/{c['preserved_total']}   "
          f"withdrawn failing: {c['withdrawn_failing']}/{c['withdrawn_total']}")
    ok = (c["preserved_exact"] == c["preserved_total"]
          and c["withdrawn_failing"] == c["withdrawn_total"])
    if not ok:
        print("  EVIDENCE DOES NOT MEET G's ACCEPTANCE CONDITION", file=sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
