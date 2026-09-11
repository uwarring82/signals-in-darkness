"""Freeze eligibility for all thirteen ladder candidates, at both operating points.

Eligibility is decided by the CALIBRATION alone -- never by a delay result -- because a policy
outside the matched-E0[T] envelope is not held to the same false-alarm rate, so its delay ratio
is not comparable. Deciding it after seeing delays would let the class be trimmed to flatter
whichever conclusion emerged.

This must run, and its output must be frozen, BEFORE any selection delay: a selection over a
partially calibrated class is made by availability rather than performance.

A censored confirmation is refused. A capped null run contributes the cap instead of its true
larger stopping time, so a censored ARL is a downward-biased LOWER BOUND -- it cannot establish
compliance with a ceiling, only violation of a floor.

Usage: python tools/freeze_ladder_eligibility.py [--write]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GAMMA, ENVELOPE = 3.0e4, 0.30
OPS = ("pilot", "stress")
LEARNERS = ("greedy", "sampling")
OUT = ROOT / "analysis" / "eligibility_ladder_C.json"


def digest_of(obj):
    payload = {k: v for k, v in obj.items() if k != "digest"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def main(argv):
    write = "--write" in argv[1:]
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    if dirty and write:
        print("refusing to freeze from a dirty tree; the artifact records a revision and that "
              "revision must describe the code that produced it.\n" + dirty, file=sys.stderr)
        return 2

    learner_elig = json.loads((ROOT / "analysis" / "eligibility_C.json").read_text())["decisions"]
    cls = json.loads((ROOT / "analysis" / "schedule_class_C.json").read_text())
    members = [s["name"] for specs in cls["class"].values() for s in specs]

    record = {
        "record": "roadmap C ladder eligibility: 13 candidates at each of 2 operating points",
        "rule": f"eligible iff |ARL - {GAMMA:.0e}|/{GAMMA:.0e} <= {ENVELOPE:.2f}, decided by the "
                f"CALIBRATION alone, never by a delay result",
        "why": "a policy outside the envelope is not held to the same false-alarm rate, so its "
               "delay ratio is not comparable to an eligible policy's",
        "decided_per_operating_point": "a candidate ineligible at one point is NOT thereby "
                                       "ineligible at the other; the envelope is a property of "
                                       "the calibration, which is per point",
        "revision": head,
        "supersedes": {"file": "analysis/eligibility_C.json",
                       "why": "that file covered only the two learners at two points (4 rows). "
                              "The ladder ranges over 13 candidates, so eligibility must cover "
                              "all of them. The four learner rows below are carried over "
                              "unchanged, not recomputed."},
        "operating_points": {},
    }

    problems, marginal, cal_revs = [], [], {}
    for op in OPS:
        path = ROOT / "analysis" / "reproduction" / f"res11_cal_{op}.json"
        if not path.exists():
            problems.append(f"{op}: no calibration artifact at {path.name}")
            continue
        doc = json.loads(path.read_text())
        cal = doc.get("cal", {})
        cal_rev = doc.get("meta", {}).get("revision", "unrecorded")
        if cal_rev.endswith("+dirty") or cal_rev == "unrecorded":
            problems.append(f"{op}: calibration revision is {cal_rev!r}; an eligibility "
                            f"decision must rest on measurements whose code state is pinned")
        cal_revs[op] = cal_rev
        missing = [m for m in members if m not in cal]
        if missing:
            problems.append(f"{op}: {len(missing)} of 11 schedules uncalibrated: "
                            f"{', '.join(sorted(missing))}")
            continue

        rows, eligible, ineligible = {}, [], {}
        for name in members:
            r = cal[name]
            if r["capped"] > 0:
                problems.append(f"{op}/{name}: confirmation censored ({r['capped']} runs at the "
                                f"cap); a censored ARL is a lower bound and cannot decide a ceiling")
            rows[name] = {"h_star": r["h"], "ARL": r["arl"], "se": r["se"],
                          "pct_off_target": r["pct"], "capped": r["capped"],
                          "bracket_endpoint": r["endpoint"],
                          "inside_envelope": r["inside_envelope"], "cal_seed": r["cal_seed"]}
            (eligible.append(name) if r["inside_envelope"]
             else ineligible.update({name: f"ARL {r['arl']:.0f} is {r['pct']:+.1f} % off target"}))
            # How many standard errors separate the estimate from the nearer boundary?
            near = GAMMA * (1 + ENVELOPE) if r["pct"] > 0 else GAMMA * (1 - ENVELOPE)
            if r["se"] > 0 and abs(r["arl"] - near) / r["se"] < 1.0:
                marginal.append(f"{op}/{name}: {r['pct']:+.1f} %, "
                                f"{abs(r['arl']-near)/r['se']:.2f} sigma from the boundary")

        for L in LEARNERS:
            d = learner_elig[f"{L}/{op}"]
            rows[L] = {"h_star": d["h_star"], "ARL": d["ARL"], "se": d["se"],
                       "pct_off_target": d["pct_off_target"], "capped": d["capped"],
                       "inside_envelope": d["inside_envelope"],
                       "policy_digest": d["policy_digest"],
                       "carried_from": "analysis/eligibility_C.json @ " + d["revision"]}
            (eligible.append(L) if d["inside_envelope"]
             else ineligible.update({L: f"ARL {d['ARL']:.0f} is {d['pct_off_target']:+.1f} % off"}))
            near = GAMMA * (1 + ENVELOPE) if d["pct_off_target"] > 0 else GAMMA * (1 - ENVELOPE)
            if d["se"] > 0 and abs(d["ARL"] - near) / d["se"] < 1.0:
                marginal.append(f"{op}/{L}: {d['pct_off_target']:+.1f} %, "
                                f"{abs(d['ARL']-near)/d['se']:.2f} sigma from the boundary")

        record["operating_points"][op] = {
            "candidates": 13, "eligible": sorted(eligible),
            "n_eligible": len(eligible), "ineligible": ineligible,
            "calibrations": rows,
            "calibration_revision": cal_rev,
        }

    # Both points must come from ONE revision. Roadmap B's pilot chain mixed two calibration
    # algorithms across its halves (res6 at ec0d8e0, res8 at aab80b7, which changed how the
    # threshold is picked), and the mixture was invisible in the artifacts. A ladder whose two
    # operating points disagreed the same way would not be comparable between points.
    if len(set(cal_revs.values())) > 1:
        problems.append(f"calibrations come from different revisions {cal_revs}; the two "
                        f"operating points would not be comparable")
    record["calibration_revisions"] = cal_revs
    record["revision_note"] = ("recorded revision is the one that MEASURED the calibrations, "
                               "not HEAD at freeze time")
    record["marginality"] = (marginal if marginal else
                             "no candidate sits within one standard error of the envelope boundary")
    record["not_decided_here"] = ("nothing about delays, ordering, or whether feedback helps. "
                                  "Eligibility only.")
    record["digest"] = digest_of(record)

    for op, blk in record["operating_points"].items():
        print(f"{op}: {blk['n_eligible']}/13 eligible")
        if blk["ineligible"]:
            for n, why in sorted(blk["ineligible"].items()):
                print(f"    INELIGIBLE {n:16s} {why}")
    if marginal:
        print("marginal (within 1 sigma of the boundary):")
        for m in marginal:
            print(f"    {m}")
    if problems:
        print("\nNOT FROZEN -- unresolved problems:", file=sys.stderr)
        for p in problems:
            print(f"    {p}", file=sys.stderr)
        return 3
    print(f"\ndigest {record['digest']}  calibrated at {sorted(set(cal_revs.values()))}"
          f"  frozen at HEAD {head}")
    if write:
        OUT.write_text(json.dumps(record, indent=2) + "\n")
        print(f"written to {OUT.relative_to(ROOT)}")
    else:
        print("dry run; pass --write to freeze")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
