#!/usr/bin/env python3
"""Roadmap E — identifiability in dimensionless form, stated directly in units of T2.

Supersedes section A of sid_run7.py for the v2.0 record. Three things change and one
does not.

CHANGED.
  1. Every quantity is dimensionless in T2: tau/T2, tau_c/T2, g_sigma_x*T2, and the
     criterion ratio DeltaGamma_phi/Gamma_hat. sid_run7 carried an absolute T2 = 10 and a
     dead time td = 1.0 that it assigned and never used in any equation, which invited the
     reading that its axis priced dead time. It does not, and neither does this. `td` is
     removed here rather than documented.
  2. C_0 = 0.5 joins the grid as the second PRINCIPAL-REGIME slice (manifest D2), and the
     regime label is written into the output itself so a reader cannot mistake the servo
     context rows for principal ones.
  3. The class-B infimum records all three optimiser starts with their solutions,
     convergence status, objective, iteration count, and which start was selected. E is
     seed-free but optimiser-dependent; a bare infimum hides that.

UNCHANGED. The physics. With u = tau/T2, v = tau_c/T2 and G = g_sigma_x*T2,

    s^2(u, v) = G^2 * 2 * (v*u - v^2 * (1 - exp(-u/v)))

is algebraically identical to sid_run7's gs^2*2*(tc*tau - tc^2*(1-exp(-tau/tc))), and
chi_hat = Gamma_hat*tau = u. The 24 rows this run shares with res7A must therefore
reproduce it to REGRESSION_TOL, which is asserted, not hoped for.

E does not import sid_policies, so roadmap G's operating-point refactor cannot affect it.

Usage:
    python analysis/runs/sid_run9.py            # compute afresh, write to analysis/reproduction/
    python analysis/runs/sid_run9.py --check    # additionally fail on any regression breach
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from sid_identifiability import (G, TAU_OVER_T2, REGIME, GRID_N,
                                 GRID_REFINEMENT_CHECK, information_at)
import sid_repro

ARTIFACT = "res9_identifiability_T2.json"
REGRESSION_TOL = 6e-8  # absolute res7A regression budget; analysis/outputs/SCHEMA.md

# Rows where res7A is ACCEPTED as under-converged. A lower I_B is only evidence that the
# reference was under-converged; it is not proof, and treating any lower value as
# automatically acceptable would let a real regression pass whenever it happened to point
# downward. A row is accepted only if it is listed here AND every candidate this run
# produced -- all three named starts and the grid route -- lies below res7A. Anything else
# is review_required, not a pass. Keys are (C_0, eta_0, tau_c/T2); see note 16.
UNDER_CONVERGED_ALLOWLIST = {
    (0.9, 0.05, 0.2): "note 16 section 3; grid-and-polish confirms 1.970344e-06",
    (0.9, 0.10, 0.2): "note 16 section 3; grid-and-polish confirms 1.817114e-06",
}

# ---------------- dimensionless configuration, all in units of T2 ----------------
TAU_C_OVER_T2 = (0.05, 0.2, 1.0, 5.0)
C0_GRID = (0.4, 0.5, 0.9)
ETA0_GRID = (0.02, 0.05, 0.10)

# res7A's tau_c axis was in units of the (unused) dead time, with T2 = 10.
RES7A_TC_TO_T2 = {0.5: 0.05, 2.0: 0.2, 10.0: 1.0, 50.0: 5.0}


def compute():
    rows = []
    for C0 in C0_GRID:
        for eta0 in ETA0_GRID:
            for v in TAU_C_OVER_T2:
                row = information_at(C0, eta0, v)
                rows.append(row)
                print(f"C0={C0} ({REGIME[C0]:>13}) eta0={eta0:.2f} tau_c/T2={v:5.2f}: "
                      f"unc={row['I_unc']:.3e} A={row['I_A']:.3e} "
                      f"({row['class_A_points_passing']:2d}/40) B={row['I_B']:.3e} "
                      f"ref={row['I_ref']:.3e}  dG/Ghat={row['DeltaGamma_over_Gamma_hat']:6.4f}")
    return rows


def regress_against_res7A(rows):
    """The 24 rows shared with res7A must reproduce it within REGRESSION_TOL.

    res7A rows are positional: [C0, eta0, tau_c(dead-time units), I_unc, I_A, I_B, I_ref, ratio].
    C_0 = 0.5 is new and has no counterpart, so 24 of the 36 rows are checked.
    """
    ref = sid_repro.load_reference("res7A_identifiability.json")
    if ref is None:
        return {"status": "no reference present", "compared": 0, "max_abs_dev": None, "breaches": []}
    index = {}
    for r in ref:
        index[(round(r[0], 12), round(r[1], 12), RES7A_TC_TO_T2[r[2]])] = r
    compared, worst = 0, 0.0
    breaches, ref_under, review = [], [], []
    for row in rows:
        key = (round(row["C_0"], 12), round(row["eta_0"], 12), row["tau_c_over_T2"])
        if key not in index:
            continue
        r = index[key]
        compared += 1
        cands = [c["fun"] for c in row["optimizer"]["starts"]]
        for name, mine, theirs in (("I_unc", row["I_unc"], r[3]), ("I_A", row["I_A"], r[4]),
                                   ("I_B", row["I_B"], r[5]), ("I_ref", row["I_ref"], r[6]),
                                   ("ratio", row["DeltaGamma_over_2eta0_Gamma_hat"], r[7])):
            dev = abs(mine - theirs)
            worst = max(worst, dev)
            if dev <= REGRESSION_TOL:
                continue
            item = {"key": list(key), "field": name, "regime": row["regime"], "mine": mine,
                    "res7A": theirs, "abs_dev": dev,
                    "named_spread_rel": row["optimizer"]["named_spread_rel"],
                    "grid_beat_named": row["optimizer"]["grid_beat_named"]}
            if name != "I_B" or mine > theirs:
                breaches.append(item)
                continue
            # I_B is an infimum, so a lower value MAY mean the reference was under-converged.
            # Accept that reading only on an allowlisted row where every candidate agrees.
            allowed = UNDER_CONVERGED_ALLOWLIST.get(key)
            all_below = all(c < theirs for c in cands)
            item["all_candidates_below_reference"] = all_below
            item["allowlist_reason"] = allowed
            if allowed and all_below:
                ref_under.append(item)
            else:
                item["why_review"] = ("not allowlisted" if not allowed
                                      else "not every candidate lies below the reference")
                review.append(item)
    return {"status": "compared", "compared": compared, "expected": 24,
            "tolerance": REGRESSION_TOL, "max_abs_dev": worst,
            "breaches": breaches, "reference_under_converged": ref_under,
            "review_required": review,
            "interpretation": ("breaches: this run is WORSE than res7A -- failures. "
                               "reference_under_converged: allowlisted rows where every candidate "
                               "lies strictly below res7A, so res7A overstates I_B. "
                               "review_required: this run is lower but the row is not allowlisted "
                               "or not every candidate agrees; a human must check before it is "
                               "reclassified. A lower number is never accepted automatically.")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit nonzero if the res7A regression breaches its tolerance")
    args = ap.parse_args()

    print("== E. identifiability divergence per shot, dimensionless in T2 ==")
    print("   all axes are ratios: tau/T2 in [0.1, 2.0] (40 uniform points), tau_c/T2, "
          f"g*sigma_x*T2 = {G}")
    print("   PER-SHOT. This run prices no dead time; there is no cycle time in it.")
    print("   class A: pointwise band |chi - chi_hat| <= eta0*chi_hat ; "
          "class B: Markov chi = Gamma*tau, |Gamma - Gamma_hat| <= eta0*Gamma_hat\n")
    rows = compute()

    reg = regress_against_res7A(rows)
    print(f"\nres7A regression: {reg['compared']} of {reg.get('expected')} overlapping rows, "
          f"max abs dev {reg['max_abs_dev']:.3e}, tolerance {REGRESSION_TOL}")
    print(f"  breaches (this run worse):              {len(reg['breaches'])}")
    print(f"  res7A under-converged (allowlisted):    {len(reg['reference_under_converged'])}")
    print(f"  REVIEW REQUIRED:                        {len(reg['review_required'])}")
    for u in reg["reference_under_converged"] + reg["review_required"]:
        tag = u.get("why_review", "accepted")
        print(f"    C_0={u['key'][0]} ({u['regime']}) eta_0={u['key'][1]} tau_c/T2={u['key'][2]}: "
              f"I_B {u['res7A']:.6e} -> {u['mine']:.6e}  [{tag}]")

    config = {"G_g_sigma_x_T2": G, "tau_over_T2": [float(x) for x in TAU_OVER_T2],
              "tau_c_over_T2": list(TAU_C_OVER_T2), "C_0": list(C0_GRID), "eta_0": list(ETA0_GRID)}
    doc = {
        "schema": "res9_identifiability_T2 v1",
        "units": ("Every quantity is dimensionless, expressed in units of T2. tau/T2, tau_c/T2, "
                  "g*sigma_x*T2 and DeltaGamma_phi/Gamma_hat. Information is PER SHOT; this run "
                  "prices no dead time and contains no cycle time."),
        "regimes": {"principal": [c for c in C0_GRID if REGIME[c] == "principal"],
                    "servo-context": [c for c in C0_GRID if REGIME[c] == "servo-context"],
                    "note": ("The servo-context rows (C_0 = 0.9) exceed the parity ceiling and may "
                             "NOT be used to support the parity-regime headline.")},
        "determinism": ("Seed-free and deterministic, but NOT start-independent. I_B is a "
                        "BEST-OF-CANDIDATES estimate over three named starts plus a deterministic "
                        f"{GRID_N}x{GRID_N} grid scan and its polish -- not a certified global "
                        "infimum. The named starts alone are not reliable: at tau_c/T2 = 0.05 their "
                        "relative spread reaches 12 %, and at C_0 = 0.4, eta_0 = 0.10 they agreed to "
                        "0.11 % while all sitting 9.7 % ABOVE the lower grid-and-polish candidate, so low "
                        "spread does not indicate correctness. Every candidate is stored with its solution, "
                        "convergence status, objective and iteration count, and each row records "
                        "both absolute and relative named-start spread plus how far the grid route "
                        "beat the named ones."),
        "supersedes": ("section A of analysis/runs/sid_run7.py for the v2.0 record. "
                       "analysis/outputs/res7A_identifiability.json is left unchanged."),
        "grid_refinement_check": GRID_REFINEMENT_CHECK,
        "regression_vs_res7A": reg,
        "run": sid_repro.run_metadata(config),
        "rows": rows,
    }
    path = sid_repro.reproduction_path(ARTIFACT)
    sid_repro.write_json(path, doc, allow_nan=False)
    print(f"wrote {path}")
    print(f"computed: {len(rows)}, cached: 0")

    if args.check and (reg["breaches"] or reg["review_required"]):
        print(f"FAIL: {len(reg['breaches'])} breaches, {len(reg['review_required'])} rows "
              f"needing review against res7A", file=sys.stderr)
        for b in (reg["breaches"] + reg["review_required"])[:10]:
            print(f"  {b}", file=sys.stderr)
        return 2
    print("done9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
