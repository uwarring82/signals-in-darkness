"""Freeze the L1/L2/L3 selections from the SELECTION stream, before any evaluation is inspected.

Each rung names its member using only 700 + int(tau_c) data. The evaluation stream
(200 + int(tau_c)) is not read here and must not be: selecting and scoring on the same sample
makes the benchmark look stronger than it is, and for a BENCHMARK that means the learner looks
weaker than it is.

L1  best fixed endpoint, chosen per true tau_c over {mid, ext}.
L2  best ROBUST precommitted schedule from roadmap B's four, one member for ALL tau_c, chosen by
    smallest worst-case delay ratio across tau_c.
L3  best eligible member per true tau_c over all 13 candidates.

Ineligible candidates are excluded: a policy outside the matched-E0[T] envelope is not held to
the same false-alarm rate, so its delay is not comparable.

Usage: python tools/freeze_ladder_selections.py [--write]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPS = ("pilot", "stress")
TCCS = (20.0, 5.0, 1.0)
L1_CLASS = ("mid", "ext")
L2_CLASS = ("interleave-B1", "interleave-B10", "switch@300", "switch@1000")
OUT = ROOT / "analysis" / "selections_ladder_C.json"


def digest_of(obj):
    return hashlib.sha256(json.dumps({k: v for k, v in obj.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def main(argv):
    write = "--write" in argv[1:]
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    if dirty and write:
        print("refusing to freeze from a dirty tree\n" + dirty, file=sys.stderr)
        return 2

    elig_doc = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())
    rec = {
        "record": "roadmap C ladder selections, frozen from the SELECTION stream only",
        "stream": "700 + int(tau_c) + operating-point offset",
        "evaluation_stream_not_read": "200 + int(tau_c) + offset was not opened by this tool",
        "why": "a member chosen on the sample it is then scored on is chosen partly by noise; "
               "the benchmark would be optimistically biased and the learner would look weaker "
               "than it is",
        "eligibility_digest": elig_doc["digest"],
        "revision": head,
        "operating_points": {},
    }
    problems = []

    for op in OPS:
        path = ROOT / "analysis" / "reproduction" / f"res11_selection_{op}.json"
        if not path.exists():
            problems.append(f"{op}: no selection artifact")
            continue
        doc = json.loads(path.read_text())
        d = doc.get("delays", {})
        eligible = set(elig_doc["operating_points"][op]["eligible"])

        for cell in d.values():
            if cell["phase"] != "selection":
                problems.append(f"{op}: a cell carries phase {cell['phase']!r}, not 'selection'")
                break

        def mean(name, tcc):
            c = d.get(f"{name}|{tcc}")
            return None if c is None else c["mean"]

        missing = [f"{n}|{t}" for n in eligible for t in TCCS if mean(n, t) is None]
        if missing:
            problems.append(f"{op}: {len(missing)} eligible cells missing: {missing[:6]}")
            continue
        capped = [f"{n}|{t}" for n in eligible for t in TCCS
                  if d[f"{n}|{t}"]["capped"] > 0]

        # ---- L1: per tau_c, over the two constants ----
        l1 = {}
        for t in TCCS:
            cands = [n for n in L1_CLASS if n in eligible]
            if not cands:
                problems.append(f"{op}: neither constant is eligible; L1 is undefined")
                continue
            best = min(cands, key=lambda n: mean(n, t))
            l1[str(t)] = {"member": best, "selection_mean": mean(best, t),
                          "considered": {n: mean(n, t) for n in cands},
                          "degenerate": len(cands) < len(L1_CLASS),
                          "degenerate_note": (
                              "" if len(cands) == len(L1_CLASS) else
                              f"only {cands} eligible; L1 degenerates to it and is no longer a "
                              f"CHOICE between endpoints at this operating point")}

        # ---- L2: ONE robust member for all tau_c, smallest worst-case ratio to the best ----
        cands2 = [n for n in L2_CLASS if n in eligible]
        l2 = {}
        if not cands2:
            problems.append(f"{op}: no eligible member of roadmap B's four-schedule class")
        else:
            best_at = {t: min(mean(n, t) for n in cands2) for t in TCCS}
            worst = {n: max(mean(n, t) / best_at[t] for t in TCCS) for n in cands2}
            pick = min(worst, key=lambda n: worst[n])
            l2 = {"member": pick, "worst_case_ratio": worst[pick],
                  "rule": "smallest worst-case ratio to the best eligible member at each tau_c",
                  "ratio_denominator": (
                      "the best eligible member of L2's own four-schedule class at that tau_c. "
                      "The predeclared rule says 'smallest worst-case delay ratio over tau_c' "
                      "without naming a denominator; this is the within-class competitive ratio "
                      "reading, recorded explicitly so the choice is auditable rather than "
                      "implicit."),
                  "eligible_members": cands2,
                  "excluded_as_ineligible": [n for n in L2_CLASS if n not in eligible],
                  "considered": worst,
                  "selection_means": {str(t): mean(pick, t) for t in TCCS}}

        # ---- L3: per tau_c, over all eligible candidates ----
        l3 = {}
        for t in TCCS:
            cands = sorted(eligible)
            best = min(cands, key=lambda n: mean(n, t))
            ordered = sorted(((mean(n, t), n) for n in cands))
            gap = (ordered[1][0] - ordered[0][0]) / ordered[0][0] if len(ordered) > 1 else None
            se0 = d[f"{best}|{t}"]["se"]
            l3[str(t)] = {
                "member": best, "selection_mean": mean(best, t),
                "runner_up": ordered[1][1] if len(ordered) > 1 else None,
                "runner_up_margin_pct": None if gap is None else 100 * gap,
                "margin_in_se": None if gap is None else
                                (ordered[1][0] - ordered[0][0]) / se0 if se0 > 0 else None,
                "considered": {n: mean(n, t) for n in cands},
                "selected_a_learner": best in ("greedy", "sampling"),
            }

        rec["operating_points"][op] = {
            "n_eligible": len(eligible), "eligible": sorted(eligible),
            "capped_selection_cells": capped,
            "L1": l1, "L2": l2, "L3": l3,
        }

    learner_cells = [f"{op}/tau_c={t}" for op, blk in rec["operating_points"].items()
                     for t in TCCS if blk["L3"][str(t)]["selected_a_learner"]]
    rec["L3_selected_a_learner_at"] = learner_cells or "no cell selected a learner"
    rec["L3_learner_selection_meaning"] = (
        "both learners are IN L3's class by design, so L3 selecting one is expected rather than "
        "an error. Where it happens the rung stops being an independent benchmark for that cell: "
        "it is the learner, re-measured on the evaluation stream, and cannot evidence that the "
        "learner beats a benchmark.")
    rec["selection_noise_caveat"] = (
        "L3 names the member with the smallest SELECTION-stream mean. That is a noisy procedure: "
        "where the runner-up sits within about one standard error, a different selection draw "
        "would often name a different member. The frozen choice is still evaluated honestly on "
        "the held-out stream -- this caveat bounds what the choice means, not whether it is valid."
    )
    rec["digest"] = digest_of(rec)

    for op, blk in rec["operating_points"].items():
        print(f"--- {op} ({blk['n_eligible']}/13 eligible)")
        for t in TCCS:
            l3 = blk["L3"][str(t)]
            m = l3["margin_in_se"]
            margin = "n/a" if m is None else f"{m:.2f} se"
            print(f"    tau_c={t:4.0f}  L1={blk['L1'][str(t)]['member']:14s} "
                  f"L3={l3['member']:16s} (runner-up {l3['runner_up']}, margin {margin})")
        print(f"    L2 (robust, all tau_c) = {blk['L2'].get('member')}")
        if blk["capped_selection_cells"]:
            print(f"    CAPPED selection cells: {blk['capped_selection_cells']}")
    if problems:
        print("\nNOT FROZEN:", file=sys.stderr)
        for p in problems:
            print("   ", p, file=sys.stderr)
        return 3
    print(f"\ndigest {rec['digest']}  revision {head}")
    if write:
        OUT.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"written to {OUT.relative_to(ROOT)}")
    else:
        print("dry run; pass --write to freeze")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
