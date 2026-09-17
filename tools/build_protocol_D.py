#!/usr/bin/env python3
"""Build analysis/protocol_D.json, the executable specification for roadmap D.

The design is notes/2026-09-16-note-29-D-plan-draft.md, accepted at r3 and amended at r4. This
builder turns it into the contract D's correlated checks, pilot and outcome run read. It follows
tools/build_protocol_F.py's conventions at D's smaller scope: the builder writes drafts only, a
freeze stamps the digest, and verification is read-only.

    python tools/build_protocol_D.py            # write the draft
    python tools/build_protocol_D.py --check    # read-only comparison with the committed file
    python tools/build_protocol_D.py --freeze   # gated: stamp the reviewed draft with its digest

Selected inputs are stored, not recomputed here. The variance channel's optimum is fourfold
degenerate to about 1e-13, so recomputing an argmax at run time would pick among equivalent offsets
by roundoff -- it picked index 0 at kappa = 5 and index 56 at kappa = 10. The indices below are
frozen under a declared tie rule, and tests/test_protocol_D.py recomputes them to confirm the
frozen index is a maximiser.

Nothing here runs a calculation. D2 is unapproved, and no outcome-bearing phase may run against a
draft.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
OUT = ROOT / "analysis" / "protocol_D.json"
NOTE = "notes/2026-09-16-note-29-D-plan-draft.md"
DRAFT_STATUS = ("DRAFT (D1): prepared for review, not frozen. No correlated design-point check, "
                "pilot or outcome run may execute against a draft.")
FREEZE_STATUS = ("FROZEN at D1: the reviewed specification. Any change requires a superseding "
                 "version recording supersedes_digest.")
FREEZE_KEYS = ("status", "frozen", "digest")

# The declared order fixes the seed blocks. Sorting the names instead would put K10 first, giving
# the sensitivity point block 0, and adding a third kappa would renumber the existing blocks.
DESIGN_POINTS = (("K5", 5.0, "primary"), ("K10", 10.0, "sensitivity"))
TAU_OSC_SHOTS = 5
BASE_GRID = {"M": 241, "L": 6.0}
REFINEMENTS = {"spacing": {"M": 481, "L": 6.0}, "tail": {"M": 241, "L": 7.5}}
EVALUATION = {"retained": 200000, "warm_up": 2000, "replicates": 16}
PILOT = {"retained": 50000, "warm_up": 2000, "replicates": 8}
CHECKS = {"retained": 20000, "warm_up": 2000, "replicates": 4}
TOLERANCE = 0.02
KAPPA_D = 1 / 4
SEED_BASE = {"checks": 17000, "pilot": 18000, "evaluation": 19000}
BLOCK = 1 << 16
OFFSET_GRID_POINTS = 13
VARIANCE_STRIDE = 3
TIE_RELATIVE = 1e-9

# Selected at rho = 0 under each point's matched marginal, on the base grid; see the module
# docstring for why they are stored rather than recomputed.
SELECTED = {
    "K5": {"slope_index": 84, "slope_offsets": [1.5707963267948966, 1.5707963267948966],
           "J0": 0.6607682013602832,
           "variance_index": 0, "variance_full_index": 0, "variance_offsets": [0.0, 0.0],
           "kl0": 0.0017146880834477893, "signal_law_relative_difference": 1.226e-3},
    "K10": {"slope_index": 84, "slope_offsets": [1.5707963267948966, 1.5707963267948966],
            "J0": 0.7332264156123289,
            "variance_index": 0, "variance_full_index": 0, "variance_offsets": [0.0, 0.0],
            "kl0": 0.0024268372839882264, "signal_law_relative_difference": 1.214e-3},
}

# Computed once on the execution stack (sid-f, scipy 1.17.1) and never recomputed at run time.
# protocol_F.json stores the scipy 1.10 values of the two t quantiles; they differ by about
# 2.5e-10 relative, which is why each protocol carries its own block.
CONSTANTS = {"t_0975_df7": 2.364624251592784, "t_0975_df15": 2.131449545559776,
             "chi2_005_df7": 2.167349909298057, "chi2_005_df15": 7.260943927670032,
             "source": "scipy 1.17.1 on sid-f, 17 September 2026"}

BUDGET = {"check_ceiling_seconds": 1800, "pilot_ceiling_seconds": 900,
          "point_ceiling_seconds": 3600, "aggregate_ceiling_seconds": 14400}
PREDICTION_MARGIN = 1.10
PROPAGATIONS_PER_SHOT = 4          # Fisher: filter and tangent; KL: one filter per hypothesis


def sigma_for(kappa):
    from sid_servo_rate import sigma_for_kappa
    return sigma_for_kappa(kappa)


def design_points():
    points = {}
    for index, (name, kappa, role) in enumerate(DESIGN_POINTS):
        chosen = SELECTED[name]
        points[name] = {
            "kappa": kappa,
            "role": role,
            "seed_block": index,
            "sigma": sigma_for(kappa),
            "marginal_match": "exp(-sigma^2/2) = I1(kappa)/I0(kappa), the von Mises first circular moment",
            "rho": math.exp(-1.0 / TAU_OSC_SHOTS),
            "tau_osc_shots": TAU_OSC_SHOTS,
            "control_rho": 0.0,
            "offsets": {
                "slope": {"index": chosen["slope_index"], "values": chosen["slope_offsets"],
                          "searched": f"the full {OFFSET_GRID_POINTS}x{OFFSET_GRID_POINTS} grid"},
                "variance": {"index": chosen["variance_index"], "index_in_full_grid": chosen["variance_full_index"],
                             "values": chosen["variance_offsets"],
                             "searched": f"every {VARIANCE_STRIDE}rd offset, as sid_run7 does"},
            },
            "J0_reference": chosen["J0"],
            "kl0_reference": chosen["kl0"],
            "signal_law_relative_difference": chosen["signal_law_relative_difference"],
            "seeds": {"checks": [SEED_BASE["checks"] + 100 * index + r for r in range(CHECKS["replicates"])],
                      "pilot": [SEED_BASE["pilot"] + 100 * index + r for r in range(PILOT["replicates"])],
                      "evaluation": [SEED_BASE["evaluation"] + 100 * index + r
                                     for r in range(EVALUATION["replicates"])]},
        }
    return points


def build():
    return {
        "record": "roadmap D: the size of a correlated oscillator residual in the four-outcome servo likelihood",
        "status": DRAFT_STATUS,
        "note": NOTE,
        "builder": "tools/build_protocol_D.py",
        "libraries": {"baseline": "analysis/lib/sid_servo.py (independent phase, reproduces res7B_servo.json)",
                      "rates": "analysis/lib/sid_servo_rate.py (correlated phase)"},
        "claim": "C14 (pilot). D revises its appendix scope only; D gates no freeze.",
        "model": {
            "phase": "point-sampled Gaussian AR(1): x_n = rho x_{n-1} + sqrt(1-rho^2) sigma xi_n, xi ~ N(0,1)",
            "latent_state": "unwrapped x on a truncated real grid; the wrapped phase is not a Markov "
                            "lumping of it, since x and x + 2 pi have next-step means differing by 2 pi rho",
            "initialisation": "the left eigenvector of the discretised transition, not the continuous N(0, sigma^2)",
            "emission": "P(B1,B2 | x, eps) = (1 + B1 C1 cos(x+ph1))(1 + B2 C2 cos(x+eps+ph2))/4, C1 = C2 = 0.9",
            "signal": "white Gaussian modulation of variance 0.09. The likelihood uses its exact marginal, "
                      "C2 -> C2 exp(-0.045), because the simulator draws the continuous Gaussian; sid_run7's "
                      "41-point truncated sum is a different law, kept in the baseline, and its deterministic "
                      "difference is recorded per point and reported separately",
            "offsets": "frozen by index; the slope optimum is unique, the variance optimum is fourfold "
                       "degenerate to about 1e-13, so a run-time argmax would choose by roundoff",
            "tie_rule": f"among offsets within {TIE_RELATIVE:g} relative of the maximum, the lowest index "
                        "in the declared grid order is selected",
            "records": "paired across rho and across the two hypotheses by common random numbers",
        },
        "grids": {"base": BASE_GRID, "refinements": REFINEMENTS},
        "records": {"evaluation": EVALUATION, "pilot": PILOT, "checks": CHECKS,
                    "estimation": "the retained observations follow the warm-up; warm-up observations are "
                                  "filtered and excluded from every estimator"},
        "design_points": design_points(),
        "rng": {
            "generator": "numpy.random.default_rng(seed), PCG64",
            "streams": "one generator per (phase, design point, record); seed = phase base + 100 x seed_block "
                       "+ record index, as stored in each point's seeds block",
            "draw_order": f"x_0 = standard_normal() * sigma; then per block of {BLOCK} shots: the phase "
                          "innovations, then the signal modulation, then one uniform per shot",
            "hypothesis_independence": "the modulation is drawn under both hypotheses and multiplied by zero "
                                       "when unmodulated, so the stream does not depend on the hypothesis",
            "prefixes": "records from one seed agree on complete blocks only; every phase regenerates at its "
                        "frozen length and never relies on a prefix of a longer record",
        },
        "estimands": {
            "slope": "C_eff,slope = sqrt(J), J the Fisher-information rate, estimated by the "
                     "conditional-information average along the filtered history",
            "variance": "C_eff,var solves I_ext_exact(C_eff, 0.3) = D, D the KL rate from two filters",
            "score": "the total score S_N is retained for derivative checks only; S_N^2/N is not an "
                     "estimator here, its per-record variance does not shrink with N",
        },
        "numerical_checks": {
            "ND1a_fisher_nesting": {
                "at": "rho = 0", "records": CHECKS, "seeds": "each point's checks block",
                "requirement": "the conditional-information estimator equals the single-shot Fisher "
                               "information under the same discretised marginal",
                "tolerance_relative": 1e-10, "sampling": "none: exact by construction",
                "enters_allowance": False},
            "ND1b_kl_nesting": {
                "at": "rho = 0", "records": CHECKS, "seeds": "each point's checks block",
                "requirement": "per-shot increments equal the i.i.d. log-likelihood ratios, and the sampled "
                               "mean agrees with the analytic i.i.d. KL within sampling uncertainty",
                "increment_tolerance_absolute": 1e-12, "mean_tolerance_standard_errors": 4,
                "sampling": "the KL average fluctuates; it does not nest exactly", "enters_allowance": False},
            "ND2_grid": {
                "requirement": "J and D are stable from the base grid to each refinement",
                "base": BASE_GRID, "refinements": REFINEMENTS,
                "channels": ["fisher", "kl"], "records": CHECKS, "seeds": "each point's checks block",
                "aggregation": "the maximum relative change over records, refinements and channels",
                "tolerance_relative": 2e-3, "enters_allowance": True},
            "ND3_brute_force": {
                "requirement": "at rho > 0 the summed increments of the production kl_rate filter equal the "
                               "brute-force log-likelihood difference over latent grid paths, and replacing "
                               "correlated filtering with stationary-marginal i.i.d. marginalisation is rejected",
                "fixture": "4-point grid, 5 observations, rho = 0.6", "tolerance_relative": 1e-12,
                "enters_allowance": False},
            "ND4_score": {
                "requirement": "the analytic tangent matches central differences, and the normalisation "
                               "without the quotient-rule term is rejected",
                "fixture": {"kappa": 5.0, "rho": "the design point's rho", "grid": {"M": 61, "L": 5.0},
                            "offsets": [0.4, 0.9], "observations": 200, "seed": 7},
                "finite_difference_step": 1e-5,
                "tolerance_relative": 1e-7,
                "near_zero": "if the reference score is below 1e-12 in absolute value the comparison is "
                             "absolute at 1e-12, not relative",
                "rejection_relative": 1e-3,
                "tangent_sum_absolute": 1e-12, "enters_allowance": False},
            "ND5_simulator": {
                "requirement": "stationary variance, lag-one correlation and first circular moment reproduce "
                               "their targets",
                "statistics": ["variance against sigma^2", "lag-one correlation against rho",
                               "mean of cos(x) against exp(-sigma^2/2)"],
                "effective_sample_size": "N_eff = N (1 - rho^2)/(1 + rho^2): the draws are correlated and an "
                                         "i.i.d. standard error would be too small",
                "standard_errors": {"variance": "sigma^2 sqrt(2/N_eff)",
                                    "lag_one": "sqrt((1 - rho^2)/N)",
                                    "circular_moment": "sqrt((0.5 (1 + exp(-2 sigma^2)) - exp(-sigma^2))/N_eff)"},
                "aggregation": "every check record must satisfy |statistic - target| <= 6 SE, and the mean over "
                               "the check records must satisfy the same bound with SE/sqrt(replicates)",
                "tolerance_standard_errors": 6, "enters_allowance": False},
            "ND6_marginal": {
                "requirement": "the von Mises baseline at rho = 0 against the Gaussian baseline at rho = 0, "
                               "reported separately as the marginal effect, never as correlation",
                "enters_allowance": False},
            "ND7_burn_in": {
                "requirement": "warm-ups of W and 2W observations are compared on the SAME final estimation "
                               "window, for the filter, the tangent and both KL filters",
                "window": "the last `retained` observations of a record of 2W + retained observations",
                "records": CHECKS, "aggregation": "the maximum relative change over records and channels",
                "tolerance_relative": 1e-3, "enters_allowance": True},
            "ND8_signal_law": {
                "requirement": "the deterministic difference between the analytic Gaussian marginal and "
                               "sid_run7's 41-point truncated sum is computed and reported per point",
                "reported_not_gating": True, "enters_allowance": False},
            "failure": "a failed check blocks the outcome; these criteria are frozen before the checks run",
        },
        "allowance": {
            "inputs": ["the ND2 aggregated relative change in J and in D",
                       "the ND7 aggregated relative change",
                       "the grid residual of J(0) itself, measured the same way"],
            "nature": "adopted numerical allowances, taken from refinement differences; they are not "
                      "certified error bounds",
            "units": "absolute rate units: each relative residual multiplies the rate it belongs to, the "
                     "numerator residuals J_hat(rho) and the denominator residuals J(0)",
            "combination": "summed within each side, not added in quadrature; numerator and denominator "
                           "allowances stay separate",
            "application": "propagated through the ratio before the absolute image is taken: "
                           "lo = sqrt((J_lo - e_rho)/(J0 + e_0)) - 1 and hi = sqrt((J_hi + e_rho)/(J0 - e_0)) - 1. "
                           "Widening the absolute interval by half the relative residual is first order at the "
                           "reference only, and can declare a case the exact transformation leaves open",
            "nonpositive": "if a permitted numerator or denominator is not positive, the ratio is not formed "
                           "and the point is UNRESOLVED",
            "sizing_only": "the first-order form, 0.5 x the summed relative residuals in ratio units, is used "
                           "in the sizing rule and never in classification",
            "exhaustion": f"if the allowance alone reaches kappa_D x tolerance ({KAPPA_D * TOLERANCE:g}) the "
                          "point is UNRESOLVED_NUMERICAL and is not evaluated",
        },
        "sizing_rule": {
            "pilot_statistic": "s^2, the across-record variance of J_hat over the pilot's records; no mean, "
                               "no ratio and no per-record value is recorded",
            "conservative_bound": "U = (R_pilot - 1) s^2 / chi2_005_df7",
            "extrapolation": "the estimator averages N shots, so Var(J_hat) scales as 1/N: "
                             "U(N) = U x (pilot retained / N)",
            "reference": "J(0), deterministic and known before the pilot; the pilot records no mean, so no "
                         "measured interval centre enters the sizing",
            "half_width": "h(N) = t_0975_df15 x sqrt(U(N)/R) / (2 J(0)), the delta method at the reference",
            "requirement": "h(N) + the first-order sizing allowance <= kappa_D x tolerance; sizing may use "
                           "that approximation, classification may not",
            "solve": "N >= pilot_retained x U x t_0975_df15^2 / (4 R J(0)^2 (kappa_D x tolerance - allowance)^2)",
            "rounding": "round N up to a multiple of 10000, and never below the evaluation minimum",
            "replicates": "R is fixed at 16 for this protocol: the sixteen evaluation seeds and the df = 15 "
                          "quantile are frozen for that R and a larger R would need both reissued",
            "refusals": ["allowance >= kappa_D x tolerance: UNRESOLVED_NUMERICAL, no run",
                         "predicted cost above the point ceiling or the remaining aggregate: NOT_ATTEMPTED",
                         "no shortened records, no replacement records, no top-ups"],
            "predicted_versus_guaranteed": "this sizes for a predicted half-width; the realised interval "
                                           "decides the verdict. A realised half-width above target is "
                                           "reported as it stands and never repaired by further records",
        },
        "uncertainty": {
            "interval": "t_0975_df15 on J_hat(rho) across the 16 paired records",
            "denominator": "J(0) computed directly and deterministically under the matched marginal, not a "
                           "second Monte-Carlo estimate; the driver recomputes it on the frozen grid and must "
                           "reproduce J0_reference to 1e-9 relative",
            "transform": "g(J) = sqrt(J/J(0)) - 1, monotone, endpoint to endpoint",
            "absolute_image": "a signed interval containing 0 maps to [0, max(|lo|,|hi|)]; otherwise "
                              "[min(|lo|,|hi|), max(|lo|,|hi|)]",
            "numerical_allowance": "see the allowance block: the adopted allowances, including J(0)'s own "
                                   "residual, are propagated through the ratio and the verdict must survive "
                                   "them. Passing a convergence threshold does not settle a result near the "
                                   "tolerance, and halving the residual is not enough to decide one.",
            "nonpositive": "if the lower bound of J_hat(rho) is <= 0 the ratio is not formed: UNRESOLVED",
            "reference_implementation": "analysis/lib/sid_servo_rate.py verdict()",
        },
        "classification": {
            "tolerance": TOLERANCE,
            "kappa_D": KAPPA_D,
            "states": ["BELOW", "ABOVE", "UNRESOLVED", "UNRESOLVED_NUMERICAL", "NO_VERDICT"],
            "rule": ["BELOW if the widened absolute interval lies wholly below the tolerance",
                     "ABOVE if it lies wholly above",
                     "UNRESOLVED if it straddles the tolerance, touches it, or the numerical allowance "
                     "cannot be met",
                     "NO_VERDICT if a check failed, the point was not attempted, or the run was INCOMPLETE"],
            "variance_channel": "reported separately with its own interval",
            "channel_agreement": "a further statistic, never the change-from-independence criterion",
        },
        "execution": {
            "stack": "the sid-f environment of roadmap F: analysis/stack_F/conda-osx-arm64.txt with its "
                     "committed lock records analysis/stack_F/conda-osx-arm64.lock, conda-list.json, "
                     "pip-lock.txt and stack-record.json",
            "pins": {"python": "3.12.14", "numpy": "2.4.4", "scipy": "1.17.1"},
            "platform": "osx-arm64, native",
            "threads": {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                               "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")},
            "deadline_accounting": "wall-clock seconds are recorded per phase in its res15 artifact; each run "
                                   "reads the remaining aggregate from those records before it starts, and "
                                   "every run counts once however many artifacts it writes",
            "admission": "a phase starts only if its predicted cost fits the phase ceiling and the remaining "
                         "aggregate; a point whose prediction exceeds the point ceiling is NOT_ATTEMPTED",
            "runtime_stop": "a phase stops at its start plus the minimum of the applicable ceiling (checks, "
                            "pilot or point) and the remaining aggregate budget. The deadline covers setup, "
                            "simulation and filtering alike, and a run that reaches it is INCOMPLETE with "
                            "NO_VERDICT: it is never completed by shortening records",
            "cost_prediction": f"charged per propagation over every shot the phase runs, warm-ups included. "
                               f"The Fisher pass costs two propagations, the filter and its tangent, and the "
                               f"KL pass two, one filter per hypothesis: R x (warm_up + retained) x 4 "
                               f"propagation-shots, times the pilot's measured seconds per propagation-shot, "
                               f"times a margin of {PREDICTION_MARGIN}",
            "interruption": "artifacts are written before any computation and checkpointed after every step; "
                            "an interrupted or stopped run keeps its elapsed time, is INCOMPLETE and receives "
                            "NO_VERDICT. An unaffordable or interrupted calculation never acquires a verdict "
                            "through shortened or replacement records",
            "provenance": "git revision and tree state, python, numpy and scipy versions, platform and "
                          "machine, libblas build, the five thread variables and this protocol's digest, "
                          "recorded at the start of every phase",
            "refusal": "a draft status or digest mismatch, a dirty tree, an existing output for the phase, a "
                       "stack outside the pins, or any thread variable other than 1",
        },
        "budget": {**BUDGET, "threads": 1,
                   "cost_note": "R N M^2 is 2.097152e11 matrix terms for one propagation per shot at R = 16, "
                                "N = 2e5, M = 256; the score adds a propagation and the KL channel runs two "
                                "filters. D1 measures the real cost before any sizing is applied.",
                   "ceilings_are_not_authorisation": "these bound a run that has been approved; they neither "
                                                     "authorise execution nor promise completion"},
        "outputs": {"checks": "analysis/reproduction/res15_D_numerical_checks.json",
                    "pilot": "analysis/reproduction/res15_D_pilot.json",
                    "evaluation": "analysis/reproduction/res15_D_evaluation.json"},
        "constants": CONSTANTS,
        "digest": None,
    }


# ------------------------------------------------------------------ write, check, freeze
class ProtocolFrozenError(RuntimeError):
    """Raised instead of overwriting or re-freezing a protocol that is no longer a draft."""


def digest_of(obj):
    return hashlib.sha256(json.dumps({k: v for k, v in obj.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def is_draft(doc):
    return isinstance(doc, dict) and str(doc.get("status", "")).startswith("DRAFT") and doc.get("digest") is None


def is_verified_frozen(doc):
    return (isinstance(doc, dict) and str(doc.get("status", "")).startswith("FROZEN")
            and isinstance(doc.get("digest"), str) and doc["digest"] == digest_of(doc))


def equivalent(a, b, rel=1e-9, abs_tol=1e-14):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and \
            math.isclose(a, b, rel_tol=rel, abs_tol=abs_tol)
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(equivalent(a[k], b[k], rel, abs_tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(equivalent(x, y, rel, abs_tol) for x, y in zip(a, b))
    return a == b


def matches_builder(doc, rebuilt=None):
    rebuilt = build() if rebuilt is None else rebuilt
    if is_draft(doc):
        return equivalent(doc, rebuilt)
    return is_verified_frozen(doc) and equivalent({k: v for k, v in doc.items() if k not in FREEZE_KEYS},
                                                  {k: v for k, v in rebuilt.items() if k not in FREEZE_KEYS})


def write_draft(doc, path):
    path = Path(path)
    if not is_draft(doc):
        raise ProtocolFrozenError("the builder writes drafts only")
    if path.exists() and not is_draft(json.loads(path.read_text())):
        raise ProtocolFrozenError(f"refusing to overwrite frozen protocol {path}")
    path.write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")


def freeze_protocol(path, when):
    path = Path(path)
    current = json.loads(path.read_text())
    if not is_draft(current):
        raise ProtocolFrozenError(f"{path} is not an unfrozen draft")
    if not equivalent(current, build()):
        raise ProtocolFrozenError(f"{path} differs from its builder; rebuild and review before freezing")
    frozen = {k: v for k, v in current.items() if k != "digest"}
    frozen["status"] = FREEZE_STATUS
    frozen["frozen"] = when
    frozen["digest"] = digest_of(frozen)
    path.write_text(json.dumps(frozen, indent=2, allow_nan=False) + "\n")
    return frozen["digest"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build roadmap D's specification.", allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only comparison with the committed file")
    mode.add_argument("--freeze", metavar="WHEN", help="gated: stamp the reviewed draft, e.g. 2026-09-18")
    args = parser.parse_args(argv)
    if args.freeze:
        try:
            print(f"froze {OUT.name} with digest {freeze_protocol(OUT, args.freeze)}")
        except ProtocolFrozenError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        return 0
    doc = build()
    if args.check:
        ok = OUT.exists() and matches_builder(json.loads(OUT.read_text()), doc)
        print("protocol_D.json matches its builder" if ok else "protocol_D.json differs from its builder")
        return 0 if ok else 1
    try:
        write_draft(doc, OUT)
    except ProtocolFrozenError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {OUT.relative_to(ROOT)} (DRAFT, digest null)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
