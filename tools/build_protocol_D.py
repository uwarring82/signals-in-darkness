#!/usr/bin/env python3
"""Build analysis/protocol_D.json, the compact executable specification for roadmap D.

The design is notes/2026-09-16-note-29-D-plan-draft.md, D0 r3, accepted 17 September 2026. This
builder turns it into the frozen contract that D's correlated checks, pilot and outcome run read.
It follows tools/build_protocol_F.py's conventions at D's smaller scope: the builder writes drafts
only, a freeze stamps the digest, and verification is read-only.

    python tools/build_protocol_D.py            # write the draft
    python tools/build_protocol_D.py --check    # read-only comparison with the committed file
    python tools/build_protocol_D.py --freeze   # gated: stamp the reviewed draft with its digest

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
GRID = {"M": 241, "L": 6.0}
RECORD = {"length": 200000, "burn_in": 2000, "replicates": 16}
PILOT = {"replicates": 8, "length": 50000, "burn_in": 2000, "deadline_seconds": 900}
TOLERANCE = 0.02                              # the 2 % change-from-independence tolerance
KAPPA_PRECISION = 1 / 4                       # half-width target as a fraction of the tolerance
BUDGET = {"aggregate_cap_seconds": 14400, "point_cap_seconds": 3600, "check_deadline_seconds": 1800}
SEED_BASE = {"checks": 17000, "pilot": 18000, "evaluation": 19000}
CONSTANTS = {"t_0975_df7": 2.3646242510102993, "t_0975_df15": 2.131449545559323}


def sigma_for(kappa):
    from sid_servo_rate import sigma_for_kappa
    return sigma_for_kappa(kappa)


def seeds(base, count, index):
    return [base + 100 * index + r for r in range(count)]


def design_points():
    points = {}
    for index, (name, kappa, role) in enumerate(DESIGN_POINTS):
        points[name] = {
            "kappa": kappa,
            "role": role,
            "seed_block": index,
            "sigma": sigma_for(kappa),
            "marginal_match": "exp(-sigma^2/2) = I1(kappa)/I0(kappa), the von Mises first circular moment",
            "rho": math.exp(-1.0 / TAU_OSC_SHOTS),
            "tau_osc_shots": TAU_OSC_SHOTS,
            "control_rho": 0.0,
            "seeds": {phase: seeds(base, RECORD["replicates"] if phase != "pilot" else PILOT["replicates"], index)
                      for phase, base in SEED_BASE.items()},
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
            "emission": "P(B1,B2 | x, eps) = (1 + B1 C1 cos(x+ph1))(1 + B2 C2 cos(x+eps+ph2))/4, C1 = C2 = 0.9",
            "signal": "white Gaussian modulation of variance 0.09 for the variance channel; oscillator "
                      "parameters identical under both hypotheses",
            "offsets": "frozen at the maximisers found at rho = 0 under the matched marginal and reused at "
                       "every rho; the slope channel searches the full 13x13 grid, the variance channel grid[::3]",
            "records": "paired across rho by common random numbers",
        },
        "grid": GRID,
        "records": RECORD,
        "design_points": design_points(),
        "estimands": {
            "slope": "C_eff,slope = sqrt(J), J the Fisher-information rate, estimated by the "
                     "conditional-information average along the filtered history",
            "variance": "C_eff,var solves I_ext_exact(C_eff, 0.3) = D, D the KL rate from two filters",
            "score": "the total score S_N is retained for derivative checks only; S_N^2/N is not an "
                     "estimator here, its per-record variance does not shrink with N",
        },
        "numerical_checks": {
            "ND1a_fisher_nesting": {"at": "rho = 0", "requirement": "the conditional-information estimator "
                                    "equals the single-shot Fisher information under the same discretised "
                                    "marginal", "tolerance_relative": 1e-10, "sampling": "none: exact by construction"},
            "ND1b_kl_nesting": {"at": "rho = 0", "requirement": "per-shot increments equal the i.i.d. "
                                "log-likelihood ratios, and the sampled mean agrees with the analytic i.i.d. KL "
                                "within sampling uncertainty",
                                "increment_tolerance_absolute": 1e-12, "mean_tolerance_standard_errors": 4},
            "ND2_grid": {"requirement": "J is stable in grid spacing M and tail range L",
                         "tolerance_relative": 2e-3, "enters_allowance": True},
            "ND3_brute_force": {"requirement": "on short records the filter's likelihood equals an explicit "
                                "sum over latent grid paths", "tolerance_relative": 1e-12},
            "ND4_score": {"requirement": "the analytic tangent matches central differences, and the "
                          "normalisation without the quotient-rule term is rejected",
                          "tolerance_relative": 1e-7, "tangent_sum_absolute": 1e-12},
            "ND5_simulator": {"requirement": "stationary variance, lag-one correlation and first circular "
                              "moment reproduce their targets", "tolerance_standard_errors": 6},
            "ND6_marginal": {"requirement": "the von Mises baseline at rho = 0 against the Gaussian baseline "
                             "at rho = 0, reported separately as the marginal effect, never as correlation"},
            "ND7_burn_in": {"requirement": "stability in the discarded burn-in length for the filter, the "
                            "tangent and both KL filters", "tolerance_relative": 1e-3, "enters_allowance": True},
            "failure": "a failed check blocks the outcome; these criteria are frozen before the checks run",
        },
        "pilot": {
            **PILOT,
            "seeds": "design_points[*].seeds.pilot, disjoint from checks and evaluation",
            "recorded": "per-record wall seconds and shots, the across-record variance of J_hat, and t_step",
            "not_recorded": "no per-record J, no mean of them, no ratio to J(0)",
            "purpose": "variance and cost only; it fixes N and R through the sizing rule below",
        },
        "sizing_rule": {
            "rule": "R and N are chosen so that the half-width of the absolute interval, after the "
                    "numerical allowance, is at most kappa_D x tolerance",
            "kappa_D": KAPPA_PRECISION,
            "replicates_minimum": RECORD["replicates"],
            "length_minimum": RECORD["length"],
            "no_topups": "N and R are fixed before the outcome run; no extension or replacement record "
                         "may follow from a measured value",
        },
        "uncertainty": {
            "interval": "t(0.975, R-1) on J_hat(rho) across paired records",
            "denominator": "J(0) computed directly and deterministically under the matched marginal, not a "
                           "second Monte-Carlo estimate",
            "transform": "g(J) = sqrt(J/J(0)) - 1, monotone, endpoint to endpoint",
            "absolute_image": "a signed interval containing 0 maps to [0, max(|lo|,|hi|)]; otherwise "
                              "[min(|lo|,|hi|), max(|lo|,|hi|)]",
            "numerical_allowance": "the ND2 and ND7 residuals and the numerical uncertainty of J(0), "
                                   "converted to ratio units, widen the absolute interval before it is "
                                   "compared with the tolerance; the verdict must survive that widening. "
                                   "Passing a convergence threshold does not settle a result near the tolerance.",
            "nonpositive": "if the lower bound of J_hat(rho) is <= 0 the ratio is not formed: UNRESOLVED",
        },
        "classification": {
            "tolerance": TOLERANCE,
            "rule": ["BELOW if the widened absolute interval lies wholly below the tolerance",
                     "ABOVE if it lies wholly above",
                     "UNRESOLVED if it straddles the tolerance, touches it, or the numerical allowance "
                     "cannot be met"],
            "variance_channel": "reported separately with its own interval",
            "channel_agreement": "a further statistic, never the change-from-independence criterion",
        },
        "budget": {**BUDGET, "threads": 1,
                   "cost_note": "R N M^2 is 2.097152e11 matrix terms for one propagation per shot at R = 16, "
                                "N = 2e5, M = 256; the score adds a propagation and the KL channel runs two "
                                "filters. D1 measures the real cost before any sizing is applied."},
        "outputs": {"checks": "analysis/reproduction/res15_D_numerical_checks.json",
                    "pilot": "analysis/reproduction/res15_D_pilot.json",
                    "evaluation": "analysis/reproduction/res15_D_evaluation.json"},
        "refusals": ["a draft status or a digest mismatch", "a dirty tree", "an existing output for the phase",
                     "any thread variable other than 1"],
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
