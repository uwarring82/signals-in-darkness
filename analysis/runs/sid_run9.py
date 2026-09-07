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
import math
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import numpy as np
from scipy.optimize import minimize
from sid_lib import DB
import sid_repro

ARTIFACT = "res9_identifiability_T2.json"
REGRESSION_TOL = 6e-8          # SCHEMA.md:43; the spread measured across stacks under DEFAULT tolerances

# L-BFGS-B's defaults are absolute-dominated when the objective is ~1e-6: its ftol test
# divides by max(|f|, 1), so with |f| << 1 it stops on an absolute change of ~2e-9, which
# here is a relative change of ~3e-4. Under the reparameterisation from Gamma to
# Gamma/Gamma_hat that premature stop became visible -- the three starts landed on three
# different points spread over 1.1 %, and the infimum came out 6.15e-7 ABOVE res7A. With
# these tolerances every start converges to the same boundary solution and the across-start
# spread falls to 2.4e-9, twenty-five times inside REGRESSION_TOL.
#
# They are tightened to the numerical floor and no further. scipy differentiates this
# objective by finite differences, so its gradient carries ~1e-14 absolute noise; asking for
# gtol below that made 46 of 108 starts return ABNORMAL_TERMINATION_IN_LNSRCH while still
# reporting the right minimum, which would have made the recorded convergence status
# worthless. At these values all 108 starts converge cleanly. See note 15.
OPT_OPTIONS = {"ftol": 1e-14, "gtol": 1e-9, "maxiter": 5000, "maxfun": 50000}
GRID_N = 121            # deterministic pre-scan per axis; see class_b_infimum

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
G = 0.5                        # g*sigma_x*T2, radians
TAU_OVER_T2 = np.linspace(0.1, 2.0, 40)
TAU_C_OVER_T2 = (0.05, 0.2, 1.0, 5.0)
C0_GRID = (0.4, 0.5, 0.9)
ETA0_GRID = (0.02, 0.05, 0.10)
REGIME = {0.4: "principal", 0.5: "principal", 0.9: "servo-context"}

# res7A's tau_c axis was in units of the (unused) dead time, with T2 = 10.
RES7A_TC_TO_T2 = {0.5: 0.05, 2.0: 0.2, 10.0: 1.0, 50.0: 5.0}


def s2_of(u, v):
    """Stationary Ramsey-phase variance at interrogation u = tau/T2, correlation v = tau_c/T2."""
    return G * G * 2.0 * (v * u - v * v * (1.0 - math.exp(-u / v)))


def pd(contrast):
    """Dark-fringe outcome probability for an effective contrast."""
    return (1.0 - contrast) / 2.0


def _spread(record):
    """Absolute AND relative objective spread across the three NAMED starts.

    Absolute spread alone is misleading: at tau_c/T2 = 0.05 the infimum is of order 1e-9,
    where an absolute spread of 2.4e-9 is a 12 % disagreement. Both are recorded.
    """
    funs = [r["fun"] for r in record if r["kind"] == "named"]
    lo, hi = min(funs), max(funs)
    return hi - lo, ((hi - lo) / lo if lo > 0 else 0.0)


def _grid_beat(record):
    """By how much the deterministic grid route beat the best named start, relatively.

    Positive means the named multi-start missed the minimum and the grid caught it.
    """
    named = min(r["fun"] for r in record if r["kind"] == "named")
    grid = min(r["fun"] for r in record if r["kind"] != "named")
    return (named - grid) / grid if grid > 0 else 0.0


def _obj_grid(C0, s2, weights, gs, g0):
    """Vectorised objective over a mesh of (Gamma_s, Gamma_0)/Gamma_hat, for the grid scan."""
    u = TAU_OVER_T2[None, None, :]
    x = s2[None, None, :]
    w = weights[None, None, :]
    p = (1.0 - C0 * np.exp(-gs[:, None, None] * u - x / 2)) / 2.0
    q = (1.0 - C0 * np.exp(-g0[None, :, None] * u)) / 2.0
    return np.sum(w * (p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))), axis=2)


def class_b_infimum(C0, eta0, s2, weights):
    """Two-parameter infimum over the Markov class: three named starts AND a grid-and-polish.

    The class is chi(tau) = Gamma*tau with |Gamma - Gamma_hat| <= eta0*Gamma_hat. In T2
    units Gamma/Gamma_hat is the free variable, so the bounds are [1-eta0, 1+eta0].

    WHY THE GRID. Agreement between the three named starts does not certify a minimum. At
    C_0 = 0.4, eta_0 = 0.10, tau_c/T2 = 0.05 -- a PRINCIPAL row -- all three starts landed
    within 0.11 % of each other and all three were 9.7 % ABOVE the true infimum, which a
    deterministic grid scan finds at the g_0 boundary. Low across-start spread was therefore
    an unreliable indicator, and a bare best-of-three would have published the wrong number.
    The grid is deterministic, so this stays reproducible without a seed.

    The value returned is a BEST-OF-CANDIDATES estimate, not a certified global infimum.
    """
    def obj(v):
        gs, g0 = v
        return sum(wt * DB(pd(C0 * math.exp(-gs * u - x / 2)), pd(C0 * math.exp(-g0 * u)))
                   for wt, u, x in zip(weights, TAU_OVER_T2, s2))

    bounds = [(1.0 - eta0, 1.0 + eta0)] * 2
    named = ([1.0, 1.0], [1.0 - eta0, 1.0 + eta0], [1.0 + eta0, 1.0 - eta0])

    axis = np.linspace(1.0 - eta0, 1.0 + eta0, GRID_N)
    mesh = _obj_grid(C0, s2, weights, axis, axis)
    gi, gj = np.unravel_index(np.argmin(mesh), mesh.shape)
    grid_seed = [float(axis[gi]), float(axis[gj])]

    record = []
    for kind, x0 in [("named", s) for s in named] + [("grid-polish", grid_seed)]:
        r = minimize(obj, x0, bounds=bounds, method="L-BFGS-B", options=OPT_OPTIONS)
        record.append({
            "kind": kind,
            "x0": [float(a) for a in x0],
            "x": [float(a) for a in r.x],
            "fun": float(r.fun),
            "success": bool(r.success),
            "status": int(r.status),
            "nit": int(r.nit),
            "message": str(r.message),
        })
    record.append({"kind": "grid-raw", "x0": grid_seed, "x": grid_seed,
                   "fun": float(mesh[gi, gj]), "success": True, "status": 0, "nit": 0,
                   "message": f"deterministic {GRID_N}x{GRID_N} scan minimum"})
    selected = min(range(len(record)), key=lambda i: record[i]["fun"])
    return record, selected


def compute():
    w = np.ones_like(TAU_OVER_T2) / len(TAU_OVER_T2)
    chihat = TAU_OVER_T2.copy()          # chi_hat = Gamma_hat*tau = tau/T2 = u
    rows = []
    for C0 in C0_GRID:
        for eta0 in ETA0_GRID:
            for v in TAU_C_OVER_T2:
                s2 = np.array([s2_of(u, v) for u in TAU_OVER_T2])
                eta = eta0 * chihat

                I_unc = sum(wt * DB(pd(C0 * math.exp(-ch - x / 2)), pd(C0 * math.exp(-ch)))
                            for wt, ch, x in zip(w, chihat, s2))

                # class A decouples per tau; the guard is the exact separation condition
                I_A, passing = 0.0, 0
                for wt, ch, x, e in zip(w, chihat, s2, eta):
                    if x / 2 > 2 * e:
                        I_A += wt * DB(pd(C0 * math.exp(-ch + e - x / 2)), pd(C0 * math.exp(-ch - e)))
                        passing += 1

                record, selected = class_b_infimum(C0, eta0, s2, w)
                I_B = max(record[selected]["fun"], 0.0)

                I_ref = max(DB(pd(C0 * math.exp(-ch - x / 2)), pd(C0 * math.exp(-ch)))
                            for ch, x in zip(chihat, s2))

                dG_over_Gamma = G * G * v                 # DeltaGamma_phi/Gamma_hat
                rows.append({
                    "C_0": C0,
                    "regime": REGIME[C0],
                    "eta_0": eta0,
                    "tau_c_over_T2": v,
                    "I_unc": I_unc,
                    "I_A": I_A,
                    "I_B": I_B,
                    "I_ref": I_ref,
                    "DeltaGamma_over_Gamma_hat": dG_over_Gamma,
                    "DeltaGamma_over_2eta0_Gamma_hat": dG_over_Gamma / (2 * eta0),
                    "class_A_points_passing": passing,
                    "class_A_points_total": int(len(TAU_OVER_T2)),
                    "optimizer": {"starts": record, "selected_index": selected,
                                  "selected_fun": record[selected]["fun"],
                                  "named_spread_abs": _spread(record)[0],
                                  "named_spread_rel": _spread(record)[1],
                                  "grid_beat_named": _grid_beat(record),
                                  "grid_n": GRID_N,
                                  "options": OPT_OPTIONS},
                })
                print(f"C0={C0} ({REGIME[C0]:>13}) eta0={eta0:.2f} tau_c/T2={v:5.2f}: "
                      f"unc={I_unc:.3e} A={I_A:.3e} ({passing:2d}/40) B={I_B:.3e} "
                      f"ref={I_ref:.3e}  dG/Ghat={dG_over_Gamma:6.4f}")
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
                        "0.11 % while all sitting 9.7 % ABOVE the true minimum, so low spread does "
                        "not indicate correctness. Every candidate is stored with its solution, "
                        "convergence status, objective and iteration count, and each row records "
                        "both absolute and relative named-start spread plus how far the grid route "
                        "beat the named ones."),
        "supersedes": ("section A of analysis/runs/sid_run7.py for the v2.0 record. "
                       "analysis/outputs/res7A_identifiability.json is left unchanged."),
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
