"""Per-member reconciliation of roadmap C's fresh calibrations against roadmap B's archives.

Roadmap B is a historically MIXED calibration chain. Three different routines produced its
archived thresholds, and which one a member got depends on when and under which driver flag it
was measured:

  plain bisection                 sid_policies.calibrate. Both drivers refine only when the
                                  operating-point name ends in '_recal', so the whole STRESS
                                  point is unrefined.
  refined, last secant iterate    calibrate_refined before aab80b7.
  refined, best of measured       calibrate_refined at aab80b7 and later.

So B's delays cannot be imported into C's matched comparison: they were measured at thresholds
a different procedure chose. B's delays remain valid historical evidence FOR B -- nothing here
retracts them. This table records the correspondence so the regeneration is auditable rather
than asserted.

The exact-reproduction prediction is CONDITIONAL on one property: the enlarged confirmation cap
introduced by 5024d59 must be applied only after h has been selected, otherwise a member
calibrated at aab80b7 would not be expected to reproduce at HEAD either. That property is
measured, not assumed, by tests/test_calibration_cap_independence.py. It also requires the
SEARCH cap to be unchanged, which it is: NULL_CAP_DEFAULT = 150_000 at ec0d8e0, aab80b7,
5024d59 and HEAD.

Usage: python tools/reconcile_calibrations.py [--write]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "reconciliation_C.json"
GAMMA, ENVELOPE = 3.0e4, 0.30

LAST_ITERATE = "refined: last secant iterate (pre-aab80b7)"
BEST_MEASURED = "refined: best of measured (aab80b7 and later)"
BISECTION = "plain bisection (sid_policies.calibrate; driver refines only for *_recal)"

# Verified against the artifacts and 'git show' at each revision -- not inferred from names.
ARCHIVE = {
    ("pilot", "mid"): ("res6_policies_pilot_recal.json", "cal", "learner-mid(bank)",
                       "ec0d8e0", LAST_ITERATE),
    ("pilot", "interleave-B1"): ("res6_policies_pilot_recal.json", "cal",
                                 "learner-interleave-B1(bank)", "ec0d8e0", LAST_ITERATE),
    ("pilot", "interleave-B10"): ("res6_policies_pilot_recal.json", "cal",
                                  "learner-interleave-B10(bank)", "ec0d8e0", LAST_ITERATE),
    ("pilot", "switch@300"): ("res8_switch_pilot_recal.json", "switch", "300",
                              "aab80b7", BEST_MEASURED),
    ("pilot", "switch@1000"): ("res8_switch_pilot_recal.json", "switch", "1000",
                               "aab80b7", BEST_MEASURED),
    ("stress", "mid"): ("res6_policies_stress.json", "cal", "learner-mid(bank)",
                        "5ea5806", BISECTION),
    ("stress", "interleave-B1"): ("res6_policies_stress.json", "cal",
                                  "learner-interleave-B1(bank)", "5ea5806", BISECTION),
    ("stress", "interleave-B10"): ("res6_policies_stress.json", "cal",
                                   "learner-interleave-B10(bank)", "5ea5806", BISECTION),
    ("stress", "switch@300"): ("res8_switch_stress.json", "switch", "300",
                               "5ea5806", BISECTION),
    ("stress", "switch@1000"): ("res8_switch_stress.json", "switch", "1000",
                                "5ea5806", BISECTION),
}
# 'ext' is absent by VERIFICATION, not oversight: roadmap B only ever ran the extremum schedule
# on an ORACLE bank ('extremum-only', Bank([20.0])). The ladder's 'ext' is on the LEARNER bank
# Bank([1,4,10,25]), a different detector, so there is nothing to reproduce.
NO_ARCHIVE_REASON = {
    "ext": "B ran the extremum schedule only on an oracle bank; no learner-bank counterpart",
}


def digest_of(obj):
    return hashlib.sha256(json.dumps({k: v for k, v in obj.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def archived_row(op, member):
    spec = ARCHIVE.get((op, member))
    if spec is None:
        return None
    fname, section, key, rev, variant = spec
    doc = json.loads((ROOT / "analysis" / "outputs" / fname).read_text())
    row = doc.get(section, {}).get(key)
    if row is None:
        return {"file": fname, "revision": rev, "variant": variant, "h": None, "arl": None,
                "capped": None, "missing": f"{key!r} absent from {fname}:{section}"}
    # res6 'cal' rows are [h, arl, se, capped]; res8 'switch' rows are [h, arl, {delays}]
    capped = row[3] if section == "cal" and len(row) > 3 else None
    return {"file": fname, "archived_name": key, "revision": rev, "variant": variant,
            "h": row[0], "arl": row[1], "capped": capped,
            "capped_recorded": capped is not None,
            "pct_off_target": 100 * (row[1] - GAMMA) / GAMMA}


def main(argv):
    write = "--write" in argv[1:]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    cls = json.loads((ROOT / "analysis" / "schedule_class_C.json").read_text())
    members = [s["name"] for specs in cls["class"].values() for s in specs]

    rows, problems, failed = [], [], []
    for op in ("pilot", "stress"):
        p = ROOT / "analysis" / "reproduction" / f"res11_cal_{op}.json"
        fresh_doc = json.loads(p.read_text()) if p.exists() else {"cal": {}}
        fresh_all = fresh_doc.get("cal", {})
        fresh_rev = fresh_doc.get("meta", {}).get("revision", "unrecorded")
        for member in members:
            arch = archived_row(op, member)
            fresh = fresh_all.get(member)
            if arch is None:
                predicted = "NOT_APPLICABLE_NO_ARCHIVE"
                why = NO_ARCHIVE_REASON.get(
                    member, "never calibrated in roadmap B; this is a new class member")
            elif arch["variant"] == BEST_MEASURED:
                predicted = "EXACT_H"
                why = ("archived under the same selection rule as HEAD; the only later change "
                       "to the search was 5024d59's confirmation cap, which cannot alter h "
                       "(measured: tests/test_calibration_cap_independence.py), and the search "
                       "cap NULL_CAP_DEFAULT is 150_000 at both revisions")
            else:
                predicted = "H_DIFFERS"
                why = (f"archived by {arch['variant']}, a different rule for choosing h than "
                       f"HEAD's best-of-measured")

            row = {"operating_point": op, "member": member, "predicted": predicted,
                   "prediction_reason": why, "archived": arch,
                   "fresh": None, "fresh_revision": fresh_rev, "outcome": "PENDING"}

            if fresh is None:
                rows.append(row)
                continue
            row["fresh"] = {"h": fresh["h"], "arl": fresh["arl"], "se": fresh["se"],
                            "capped": fresh["capped"], "pct_off_target": fresh["pct"],
                            "endpoint": fresh["endpoint"],
                            "inside_envelope": fresh["inside_envelope"]}
            near = GAMMA * (1 + ENVELOPE) if fresh["pct"] > 0 else GAMMA * (1 - ENVELOPE)
            sigma = abs(fresh["arl"] - near) / fresh["se"] if fresh["se"] > 0 else None
            row["eligibility"] = {
                "eligible": bool(fresh["inside_envelope"]),
                "sigma_from_boundary": sigma,
                "marginal": bool(sigma is not None and sigma < 1.0),
                "decided_by": "fresh calibration alone, never by a delay result",
            }
            if arch and arch["h"] is not None:
                same = fresh["h"] == arch["h"]
                row["difference"] = {
                    "h_delta": fresh["h"] - arch["h"], "h_identical": same,
                    "arl_delta": fresh["arl"] - arch["arl"],
                    "arl_delta_pct": 100 * (fresh["arl"] - arch["arl"]) / arch["arl"],
                    "archived_censored": (None if arch["capped"] is None
                                          else arch["capped"] > 0),
                    "fresh_censored": fresh["capped"] > 0,
                }
                if predicted == "EXACT_H":
                    row["outcome"] = "PREDICTION_HELD" if same else "PREDICTION_FAILED"
                elif predicted == "H_DIFFERS":
                    row["outcome"] = "PREDICTION_HELD" if not same else "PREDICTION_FAILED"
                if row["outcome"] == "PREDICTION_FAILED":
                    failed.append(f"{op}/{member}: predicted {predicted}, "
                                  f"archived h={arch['h']!r} fresh h={fresh['h']!r}")
            else:
                row["outcome"] = "NO_COMPARISON"
            rows.append(row)

    done = sum(1 for r in rows if r["fresh"] is not None)
    rec = {
        "record": "roadmap C: per-member reconciliation of fresh calibrations against roadmap B",
        "why": ("roadmap B is a historically mixed calibration chain -- three routines produced "
                "its archived thresholds. Its delays remain valid evidence FOR B but cannot be "
                "imported into C's matched comparison, because they were measured at thresholds "
                "a different procedure chose."),
        "conditional_property": {
            "statement": "the enlarged confirmation cap is applied only after h is selected",
            "verified_by": "tests/test_calibration_cap_independence.py",
            "also_requires": "the SEARCH cap unchanged: NULL_CAP_DEFAULT = 150_000 at ec0d8e0, "
                             "aab80b7, 5024d59 and HEAD",
            "without_it": "no exact-reproduction prediction is logically licensed",
        },
        "variants": {"plain_bisection": BISECTION, "last_iterate": LAST_ITERATE,
                     "best_of_measured": BEST_MEASURED},
        "stress_point_was_never_refined": (
            "every archived STRESS threshold is plain bisection: both drivers gate refinement "
            "on op_name.endswith('_recal') and the stress runs used op_name='stress'. There is "
            "no res6_policies_stress_recal artifact."),
        "rows": rows, "completed": done, "total": len(rows),
        "frozen_at_head": head,
        "digest": None,
    }
    rec["digest"] = digest_of(rec)

    for op in ("pilot", "stress"):
        print(f"=== {op}")
        for r in rows:
            if r["operating_point"] != op:
                continue
            a, f = r["archived"], r["fresh"]
            ah = "--" if not a or a["h"] is None else f"{a['h']:.6f}"
            fh = "--" if not f else f"{f['h']:.6f}"
            arev = "none" if not a else a["revision"]
            el = "" if not f else ("ELIGIBLE" if f["inside_envelope"] else "INELIGIBLE")
            marg = " MARGINAL" if f and r.get("eligibility", {}).get("marginal") else ""
            print(f"  {r['member']:16s} {arev:8s} arch_h={ah:10s} fresh_h={fh:10s} "
                  f"{r['predicted']:24s} {r['outcome']:18s} {el}{marg}")
    print(f"\n{done}/{len(rows)} cells measured; {len(failed)} prediction failures")
    for x in failed:
        print("   FAILED:", x, file=sys.stderr)
    print(f"digest {rec['digest']}")
    if write:
        if done != len(rows):
            print(f"refusing to write a partial reconciliation ({done}/{len(rows)})",
                  file=sys.stderr)
            return 3
        OUT.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"written to {OUT.relative_to(ROOT)}")
    return 4 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
