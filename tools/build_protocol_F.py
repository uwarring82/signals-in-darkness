#!/usr/bin/env python3
"""Build, check and freeze the roadmap-F protocol described in note 28.

Deterministic. It evaluates committed comparator formulas and archived grids only; it
simulates no latent trajectory, evaluates no ARMA likelihood and produces no F result.

    python tools/build_protocol_F.py                 # write analysis/protocol_F.json, if it is still a draft
    python tools/build_protocol_F.py --out PATH      # write a new draft elsewhere
    python tools/build_protocol_F.py --check         # read-only: the file matches its builder (and digest, if frozen)
    python tools/build_protocol_F.py --markdown      # read-only: print the tables quoted in note 28
    python tools/build_protocol_F.py --freeze        # approved Gate-1 step only: draft -> FROZEN with digest

Writing refuses to replace a protocol that is frozen (status not starting with DRAFT, or a
non-null digest). Freezing accepts only a draft that matches its builder, sets the status and
`frozen` fields, and computes the digest with the convention of tools/freeze_ladder_selections.py:
sha256 of the sorted JSON without the digest field, first 16 hex digits. Eight roadmap-C
artifacts recompute under it; benchmark_ladder_C, eligibility_C and schedule_class_C do not.

Design evidence records roundoff-level quantities as bounds, never as values: a total variation
of about 1e-12 came out 9.878e-13 on the drafting stack and 9.997e-13 on the execution stack.
"""
import argparse
import ast
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "diagnostics"))
from review_F_plan import comparators, exact_boundary_points, filter_factor, run4_kernels  # noqa: E402

OUT = ROOT / "analysis" / "protocol_F.json"
NOTE = "notes/2026-09-15-note-28-F-protocol-draft.md"
DRAFT_REVISION = 4
DELTA, KAPPA, R = 0.05, 0.25, 16
EVAL_GRID = (241, 7)
CHECK_GRIDS = ((121, 5), (121, 7), (241, 5))
POINT_ORDER = ("E1", "E2", "E3", "E4", "E5")          # p = 0..4 in the seed formulas
MANDATORY = ("E3", "E4", "E5")
STRESS = {"E3": (0.4, 0.5, 0.10, 0.15), "E4": (0.4, 0.5, 0.30, 0.35), "E5": (0.4, 1.0, 1.00, 1.05)}
N0 = (0.4, 0.5, 0.0, 0.05)
N_PILOT = 125_000
N_CHECK = 50_000
N_SIM = 250_000
N_NEST = 200_000

PREDICTION_MARGIN = 1.10
STOP_MARGIN = 1.25
POINT_CAP_SECONDS = 7200
AGGREGATE_CAP_SECONDS = 8 * 3600
GATE3_DEADLINE_SECONDS = 1800

PYTHON_PIN = "3.12.14"
NUMPY_PIN, SCIPY_PIN = "2.4.4", "1.17.1"
STACK_SPEC = "analysis/stack_F/conda-osx-arm64.txt"
PIP_SPEC = "analysis/stack_F/pip-requirements.txt"
REVIEWED_SOLVE = "analysis/stack_F/conda-dry-run-osx-arm64-python3.12.14.json"
SUPERSEDED_SOLVE = "analysis/stack_F/conda-dry-run-osx-arm64.json"
CONDA_COMMON = ["-n", "sid-f", "--override-channels", "-c", "conda-forge", "--no-default-packages",
                "--file", STACK_SPEC]
SOLVE_ARGS = ["conda", "create", "--dry-run", "--json"] + CONDA_COMMON
INSTALL_ARGS = ["conda", "create", "-y"] + CONDA_COMMON
SOLVE_ONLY_FLAGS = ("--dry-run", "--json")
INSTALL_ONLY_FLAGS = ("-y",)

FREEZE_STATUS = ("FROZEN at Gate 1 (2026-09-15): note 28 revision 4 accepted. Any change requires a superseding "
                 "protocol version that records supersedes_digest. sid_run13.py must verify this digest before "
                 "every phase.")
FROZEN_WHEN = ("2026-09-15, Gate 1, BEFORE any ARMA likelihood evaluation, execution-stack numerical check, "
               "pilot or evaluation")
FREEZE_KEYS = ("status", "frozen", "digest")

# ------------------------------------------------------------------------------------------- wording
_C08_FACT = (
    "C08's archived mid-fringe implementation divides the exact first-lag binary correlation by "
    "F(u). Its four quoted thresholds survive a lag-1-fit correction on the stated coarse grid, but "
    "the archived rate map is not the finite-window comparator.")
CAVEAT_BEFORE_EVALUATION = (_C08_FACT + " Binary-likelihood validation remains confined to C04's tested "
                            "point-sampled exact-r_k comparator; F remains open.")      # note 27, verbatim
CORRECTED_C08_CAVEAT = CAVEAT_BEFORE_EVALUATION
SCOPE_WITH_MANDATORY_VALIDATION = ("At the mandatory points E3–E5, the exact-r_k comparator (K1) is validated "
                                   "against the exact finite-window ARMA(1,1) binary likelihood within +/- 5 % "
                                   "(pointwise 95 % intervals) at {validated_tuples}.")
SCOPE_WITHOUT_MANDATORY_VALIDATION = "No mandatory point E3–E5 validated K1 against the finite-window binary likelihood."
C04_AND_BOUNDARY = ("C04 supplies the earlier point-sampled validation; results at the conditional boundary points "
                    "E1/E2 are reported separately.")
STATUS_SENTENCE = {"OPEN": "Roadmap F remains OPEN.",
                   "VALIDATED": "Roadmap F closed VALIDATED.",
                   "FAILED": "Roadmap F closed FAILED."}
TUPLE_REPORT = ("K1 at the mandatory points: VALIDATED at {validated}; FAILED at {failed}; "
                "UNRESOLVED or without a verdict at {other}.")
VERDICTS = ("VALIDATED", "FAILED", "UNRESOLVED", "NO_VERDICT")


def _check_verdicts(k1_verdicts):
    unknown_points = sorted(set(k1_verdicts) - set(POINT_ORDER))
    if unknown_points:
        raise ValueError(f"verdicts supplied for unknown points {unknown_points}")
    missing = [p for p in MANDATORY if p not in k1_verdicts]
    if missing:
        raise ValueError(f"no K1 verdict supplied for mandatory points {missing}")
    unknown = sorted(set(k1_verdicts.values()) - set(VERDICTS))
    if unknown:
        raise ValueError(f"unknown verdicts {unknown}")


def roadmap_F_status(k1_verdicts):
    """The numerical closure rule: K1 alone, at E3, E4 and E5. Boundary verdicts never enter it."""
    _check_verdicts(k1_verdicts)
    v = [k1_verdicts[p] for p in MANDATORY]
    if all(x == "VALIDATED" for x in v):
        return "VALIDATED"
    if all(x in ("VALIDATED", "FAILED") for x in v) and "FAILED" in v:
        return "FAILED"
    return "OPEN"


def tuple_label(point):
    return (f"(C, s, u, c/tau_c) = ({point['C']:.2f}, {point['s']:.2f}, {point['u']:.2f}, "
            f"{point['c_over_tau_c']:.2f})")


def _join(items):
    """'none', 'a', 'a and b', or 'a, b and c'."""
    if not items:
        return "none"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def closure_wording(k1_verdicts=None, points=None):
    """Caveat for the manuscript. Before evaluation: note 27's sentence. Afterwards: the scope at the
    mandatory points E3-E5 only, C04 and the separately reported boundary, the campaign status and
    the verdict tuples. E1/E2 verdicts may be supplied but never enter this text."""
    if k1_verdicts is None:
        return CAVEAT_BEFORE_EVALUATION
    status = roadmap_F_status(k1_verdicts)
    fmt = lambda names: _join([f"{n} {tuple_label(points[n])}" for n in names])  # noqa: E731
    validated = [p for p in MANDATORY if k1_verdicts[p] == "VALIDATED"]
    failed = [p for p in MANDATORY if k1_verdicts[p] == "FAILED"]
    other = [p for p in MANDATORY if k1_verdicts[p] not in ("VALIDATED", "FAILED")]
    scope = (SCOPE_WITH_MANDATORY_VALIDATION.format(validated_tuples=fmt(validated)) if validated
             else SCOPE_WITHOUT_MANDATORY_VALIDATION)
    return " ".join([_C08_FACT, scope, C04_AND_BOUNDARY, STATUS_SENTENCE[status],
                     TUPLE_REPORT.format(validated=fmt(validated), failed=fmt(failed), other=fmt(other))])


# ------------------------------------------------------------------------------------------- write, check, freeze
class ProtocolFrozenError(RuntimeError):
    """Raised instead of overwriting or re-freezing a protocol that is no longer a draft."""


def is_draft(doc):
    return isinstance(doc, dict) and isinstance(doc.get("status"), str) \
        and doc["status"].startswith("DRAFT") and doc.get("digest") is None


def digest_of(obj):
    """The convention of tools/freeze_ladder_selections.py."""
    return hashlib.sha256(json.dumps({k: v for k, v in obj.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def is_verified_frozen(doc):
    return isinstance(doc, dict) and isinstance(doc.get("status"), str) and doc["status"].startswith("FROZEN") \
        and isinstance(doc.get("frozen"), str) and isinstance(doc.get("digest"), str) \
        and doc["digest"] == digest_of(doc)


def unfrozen_view(doc):
    """The protocol content without the fields a freeze sets."""
    return {k: v for k, v in doc.items() if k not in FREEZE_KEYS}


def write_draft(doc, path):
    """Write a draft, refusing to replace anything that is not itself an unfrozen draft."""
    path = Path(path)
    if not is_draft(doc):
        raise ProtocolFrozenError("the builder writes drafts only")
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProtocolFrozenError(f"refusing to overwrite unreadable {path}") from exc
        if not is_draft(existing):
            raise ProtocolFrozenError(f"refusing to overwrite frozen protocol {path}; "
                                      "write a new draft elsewhere with --out")
    path.write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n")


def freeze_protocol(path, status=FREEZE_STATUS, frozen=FROZEN_WHEN):
    """Turn the reviewed draft on disk into a frozen protocol. Refuses anything else."""
    path = Path(path)
    current = json.loads(path.read_text())
    if not is_draft(current):
        raise ProtocolFrozenError(f"{path} is not an unfrozen draft")
    if not equivalent(current, build()):
        raise ProtocolFrozenError(f"{path} differs from its builder; rebuild and review before freezing")
    frozen_doc = {k: v for k, v in current.items() if k != "digest"}     # the reviewed values, as stored
    frozen_doc["status"] = status
    frozen_doc["frozen"] = frozen
    frozen_doc["digest"] = digest_of(frozen_doc)
    path.write_text(json.dumps(frozen_doc, indent=2, allow_nan=False) + "\n")
    return frozen_doc["digest"]


def stop_seconds(predicted_seconds, remaining_aggregate_seconds):
    """Latest permitted run time: the earliest of the margin, the point cap and the aggregate budget."""
    return min(STOP_MARGIN * predicted_seconds, POINT_CAP_SECONDS, remaining_aggregate_seconds)


# ------------------------------------------------------------------------------------------- design
def ma_root(F, phi):
    """MA coefficient b, |b| < 1, of eps_n = x_n + b x_{n-1} with rho_1 = F phi (note 28 §3)."""
    A = phi * (1 - F)
    B = 1 + phi * phi - 2 * F * phi * phi
    if A == 0.0:
        return 0.0
    disc = B * B - 4 * A * A
    if disc < 0:
        raise ValueError("finite-window spectrum is negative at omega = pi")
    b = min(((-B + math.sqrt(disc)) / (2 * A), (-B - math.sqrt(disc)) / (2 * A)), key=abs)
    rho1 = (phi * (1 + b * b) + b * (1 + phi * phi)) / (1 + b * b + 2 * b * phi)
    if not math.isclose(rho1, F * phi, rel_tol=1e-12, abs_tol=0.0):
        raise AssertionError("MA root does not reproduce rho_1 = F phi")
    return b


def series_convergence(C, s, A, phi):
    """Relative change of the sinh-series rate from (6 terms, 1024) to (12 terms, 4096)."""
    ns = run4_kernels()
    coarse = ns["gp_rate_series"](C, s, A, phi)[0]
    ns["W"] = np.pi * (np.arange(4096) + 0.5) / 4096
    d = ns["spectrum_series"](C, s, A, phi, M=12)
    return float(0.5 * np.mean(d - np.log1p(d)) / coarse - 1)


def grid_diagnostics(phi, vx, q, M, L):
    """Deterministic properties of the discretised latent chain the filter will use.

    The total variation between the stationary distribution and the Gaussian weights is recorded
    as bounds: about 2-5e-7 on L = 5 grids (a truncation effect) and about 1e-12 on L = 7 grids
    (roundoff, which differed by 1.2 % between the drafting and execution stacks)."""
    g = np.linspace(-L * math.sqrt(vx), L * math.sqrt(vx), M)
    T = np.exp(-(g[None, :] - phi * g[:, None]) ** 2 / (2 * q))
    T /= T.sum(1, keepdims=True)
    w, V = np.linalg.eig(T.T)
    pi = np.real(V[:, int(np.argmin(abs(w - 1)))])
    pi = pi / pi.sum()
    gauss = np.exp(-g ** 2 / (2 * vx))
    gauss /= gauss.sum()
    tv = float(0.5 * abs(pi - gauss).sum())
    return {"innovation_sd_over_spacing": float(math.sqrt(q) / (g[1] - g[0])),
            "stationary_residual_within_1e-12": bool(abs(pi @ T - pi).sum() <= 1e-12),
            "stationary_min_at_least_-1e-15": bool(pi.min() >= -1e-15),
            "tv_stationary_vs_gaussian_weights_below_1e-6": bool(tv < 1e-6),
            "tv_stationary_vs_gaussian_weights_below_1e-10": bool(tv < 1e-10)}


def run3_taus(T2):
    source = ast.parse((ROOT / "analysis" / "runs" / "sid_run3.py").read_text())
    nodes = [n for n in source.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == "taus" for t in n.targets)]
    assert len(nodes) == 1
    return eval(compile(ast.Expression(nodes[0].value), "run3:tau-grid", "eval"), {"np": np, "T2": T2})


def boundary_points():
    archive = json.loads((ROOT / "analysis" / "outputs" / "res3_comparator.json").read_text())
    grid = archive["tau_optimised_grid"]
    taus = run3_taus(grid["T2_over_t_dead"])
    out = {}
    for name, p in zip(("E1", "E2"), exact_boundary_points()):
        k = np.flatnonzero(taus / grid["T2_over_t_dead"] == p["tau_over_T2"])
        assert len(k) == 1
        out[name] = {
            "role": f"C08 boundary at the archived C0 column nearest {0.4 if name == 'E1' else 0.5}; "
                    "winner tau of the archived map form at the stored threshold",
            "archive_indices": {"C0_column": grid["C0"].index(p["C0"]),
                                "tau_c_row": grid["tau_c_over_t_dead"].index(p["tc_over_td"]),
                                "tau_index": int(k[0])},
            "C0": p["C0"], "tau_c_over_t_dead": p["tc_over_td"], "tau_over_T2": p["tau_over_T2"],
            "T2_over_t_dead": grid["T2_over_t_dead"], "g_sigma_x_T2": grid["g_sigma_x_T2"],
            "C": p["C"], "s": p["s"], "u": p["u"], "c_over_tau_c": p["c_over_tc"]}
    return out


def design(C, s, u, c_over_tc):
    F, phi = filter_factor(u), math.exp(-c_over_tc)
    b = ma_root(F, phi)
    vx = s * s / (1 + b * b + 2 * b * phi)
    q = vx * (1 - phi * phi)
    K = {k: float(v) for k, v in comparators(C, s, u, c_over_tc).items()}
    lo, hi = (1 - DELTA) / (1 + DELTA), (1 + DELTA) / (1 - DELTA)
    pairs = {}
    for i in ("K1", "K2", "K3", "K4"):
        for j in ("K1", "K2", "K3", "K4"):
            if i > j:
                r = K[i] / K[j]
                pairs[f"{i}/{j}"] = bool(r < lo or r > hi)
    return {
        "F": F, "phi": phi, "b": b, "v_x": vx, "q": q,
        "burn_in_W": max(1000, math.ceil(100 / c_over_tc)),
        "comparators": K,
        "ratios": {"K2/K1": K["K2"] / K["K1"], "K3/K1": K["K3"] / K["K1"],
                   "K4/K1": K["K4"] / K["K1"], "K3/K4": K["K3"] / K["K4"]},
        "forced_incompatible_pairs": pairs,
        "series_convergence_within_1e-6": {"K1": bool(abs(series_convergence(C, s, F, phi)) <= 1e-6),
                                           "K4": bool(abs(series_convergence(C, s, 1.0, phi)) <= 1e-6)},
        "grids": {f"M{M}_L{L}": grid_diagnostics(phi, vx, q, M, L)
                  for M, L in CHECK_GRIDS + (EVAL_GRID,)},
    }


def seeds():
    out = {phase: {name: [base + 20 * p + r for r in range(R)] for p, name in enumerate(POINT_ORDER)}
           for phase, base in (("pilot", 13000), ("evaluation", 14000), ("numerical_checks", 15000))}
    out["numerical_checks_use"] = {"grid_and_finite_history": "r = 0..7", "simulator": "r = 8..15"}
    out["nesting_N0"] = [15900]
    out["rng"] = "numpy.random.default_rng(seed) (PCG64); one generator per (phase, point, replicate)"
    flat = [s for ph in ("pilot", "evaluation", "numerical_checks") for v in out[ph].values() for s in v]
    flat += out["nesting_N0"]
    assert len(flat) == len(set(flat))
    return out


def offset(w_multiple, plus):
    """An observation index written as w_multiple * W + plus (1-based)."""
    return {"W_multiple": w_multiple, "plus": plus}


def check_passes():
    """Filter passes shared by NC5 and NC6. Every pass is estimated on the same final observations."""
    passes = {"M241_L7_2W_history": {"grid": "M241_L7", "first_observation": offset(0, 1)},
              "M241_L7_W_history": {"grid": "M241_L7", "first_observation": offset(1, 1)}}
    for M, L in CHECK_GRIDS:
        passes[f"M{M}_L{L}_W_history"] = {"grid": f"M{M}_L{L}", "first_observation": offset(1, 1)}
    return passes


def build():
    points = boundary_points()
    for name, (C, s, u, v) in STRESS.items():
        points[name] = {"role": "stress validation point (per-shot C and s set directly; dead time 0.05 tau_c)",
                        "C": C, "s": s, "u": u, "c_over_tau_c": v}
    points["N0"] = {"role": "nesting check only (point-sampled, F = 1, b = 0)",
                    "C": N0[0], "s": N0[1], "u": N0[2], "c_over_tau_c": N0[3]}
    evidence = {name: design(p["C"], p["s"], p["u"], p["c_over_tau_c"])
                for name, p in points.items()}
    points["mandatory"] = list(MANDATORY)
    points["conditional_pair"] = ["E1", "E2"]
    points["deferred"] = {"E6": "(C, s, u, c/tau_c) = (0.4, 1.0, 0.30, 0.35): K1 and K2 differ by 5.6 %, "
                                "inside the band, so it supplies no forced-incompatibility control (note 27)"}
    points["readout_angle"] = "theta = pi/2"

    constants = {"t_0975_df15": float(stats.t.ppf(0.975, 15)), "t_0975_df7": float(stats.t.ppf(0.975, 7)),
                 "z_0975": float(stats.norm.ppf(0.975)),
                 "chi2_005_df15": float(stats.chi2.ppf(0.05, 15)),
                 "chi2_005_df144": float(stats.chi2.ppf(0.05, R * 9)),
                 "chi2_005_df304": float(stats.chi2.ppf(0.05, R * 19)),
                 "band_lower": (1 - DELTA) / (1 + DELTA), "band_upper": (1 + DELTA) / (1 - DELTA)}

    return {
        "record": "roadmap F: validation of mid-fringe comparators against an exact ARMA(1,1) latent binary likelihood",
        "status": f"DRAFT FOR REVIEW (note 28, revision {DRAFT_REVISION}) -- not frozen. No digest is binding. "
                  "sid_run13.py must refuse every phase while status starts with DRAFT.",
        "version": 1,
        "draft_revision": DRAFT_REVISION,
        "revision_log": [
            {"revision": 1, "commit": "0a3584b"},
            {"revision": 2, "commit": "4f0b390", "changes": [
                "NC6 compares W- and 2W-history filters on the same final observations; the extra pass is costed",
                "every run stops at the earliest of 1.25 x prediction, the 7200 s point cap and the remaining "
                "aggregate budget; Gate 3 has an enforced 1800 s deadline including its first measurement",
                "the builder refuses to overwrite a frozen protocol; verification stays read-only",
                "one F-specific conda definition and channel policy for solve and installation; OpenBLAS pinned; "
                "pip packages locked separately",
                "separate caveats for open, failed and validated closure",
                "review decisions on note 28 §11 recorded"]},
            {"revision": 3, "commit": "a327ab5", "changes": [
                f"python pinned to {PYTHON_PIN} (review decision on r2 §11, option b); second dry-run solve recorded; "
                "stack checks, refusals and tests use the exact patch",
                "closure wording no longer confines validation to C04 once any finite-window validation exists: "
                "before evaluation note 27's sentence; afterwards scope, campaign status and the validated, failed "
                "and unresolved tuples are reported separately"]},
            {"revision": 4, "changes": [
                "the post-evaluation scope sentence speaks only about the mandatory points E3-E5; the global C04 "
                "restriction is replaced by 'C04 supplies the earlier point-sampled validation; results at the "
                "conditional boundary points E1/E2 are reported separately'",
                "fixture: E1/E2 VALIDATED with E3-E5 FAILED; every mandatory verdict combination is checked for "
                "a global C04 restriction",
                "design evidence records roundoff-level diagnostics as bounds: on the installed execution stack the "
                "E1 M121_L7 total variation was 9.997e-13 against 9.878e-13 on the drafting stack, which failed the "
                "rebuild check; series-convergence changes (at most 9.9e-14) are recorded as bounds as well",
                "freeze tooling: a draft that matches its builder becomes FROZEN with the digest convention of "
                "tools/freeze_ladder_selections.py"]}],
        "note": NOTE,
        "replaces_plan": "notes/2026-09-15-note-26-F-plan-draft.md (not accepted; reviewed in note 27)",
        "builder": "tools/build_protocol_F.py",
        "frozen_before": "any ARMA likelihood evaluation, execution-stack numerical check, pilot or evaluation",
        "adopted_choices": {
            "blas": "OpenBLAS pinned (libblas=*=*openblas)",
            "python": f"{PYTHON_PIN} pinned (option b of note 28 r2 §11)",
            "burn_in": "W = max(1000, ceil(100 tau_c/c)), subject to the corrected NC6",
            "pilot": "n_p = 125000 and stability factor 4, as planning choices; the variance bound is approximate",
            "checks": "eight 50000-observation windows; simulator threshold 5 standard errors",
            "margins": "prediction 1.10 and stop 1.25, subordinate to the enforced hard caps",
            "closure": "K1 alone decides roadmap F; C08-boundary validation is reported separately",
            "labbook": "the freeze pass is sufficient"},
        "estimand": {
            "quantity": "per-shot relative-entropy rate R of the theta = pi/2 binary record against the "
                        "i.i.d. null p0 = 1/2; latent phase = finite-window integrated stationary OU phase",
            "units": "nats per shot",
            "link": "P(Y=1 | eps) = (1 + C cos(theta + eps))/2 = (1 - C sin eps)/2"},
        "comparators": {
            "K1": {"definition": "six-term sinh-series Gaussian spectral rate with exact "
                                 "r_k = C^2 exp(-s^2) sinh(s^2 F(u) phi^k); 1024 midpoint frequencies "
                                 "omega = pi (j + 1/2)/1024",
                   "source": "analysis/runs/sid_run4.py gp_rate_series, read through the AST",
                   "role": "primary: the exact-r_k comparator class"},
            "K2": {"definition": "geometric closed form with rho = r1/phi, r1 = C^2 exp(-s^2) sinh(s^2 F(u) phi)",
                   "source": "analysis/runs/sid_run4.py gp_rate_geomfit", "role": "secondary: lag-1-matched fit"},
            "K3": {"definition": "geometric closed form with rho = r1/(F(u) phi)",
                   "source": "analysis/runs/sid_run3.py archived C08 map call, evaluated through the AST",
                   "role": "diagnostic: archived map form (note 27 erratum)"},
            "K4": {"definition": "six-term sinh series with A = 1", "source": "sid_run4.py gp_rate_series",
                   "role": "diagnostic control: point-sampled series, not a finite-window truth model"},
            "implementation_contract": "the Gate-2 library must reproduce design_evidence comparator values "
                                       "to relative 1e-12 on the execution stack"},
        "reference_filter": {
            "latent_model": "eps_n = x_n + b x_{n-1}; x_n = phi x_{n-1} + eta_n; eta_n ~ N(0, q)",
            "parameters": "phi = exp(-c/tau_c); F(u) = (cosh u - 1)/(u - 1 + exp(-u)); b = root with |b| < 1 of "
                          "phi(1-F) b^2 + (1 + phi^2 - 2 F phi^2) b + phi(1-F) = 0; "
                          "v_x = s^2/(1 + b^2 + 2 b phi); q = v_x (1 - phi^2)",
            "grid": "g_i = -L sqrt(v_x) + i 2 L sqrt(v_x)/(M - 1), i = 0..M-1",
            "transition": "T[i, i'] proportional to exp(-(g_i' - phi g_i)^2/(2 q)); every row normalised to 1",
            "emission": "E_y[i', i] = (1 + (2y - 1) C cos(theta + g_i' + b g_i))/2",
            "stationary_initialisation": "pi = left eigenvector of T for the eigenvalue nearest 1 "
                                         "(numpy.linalg.eig of T transpose, real part, normalised to sum 1); "
                                         "require sum|pi T - pi| <= 1e-12 and min(pi) >= -1e-15; entries in "
                                         "[-1e-15, 0) are set to 0 and pi is renormalised",
            "first_step": "at a pass's first observation m: alpha~_m(i, j) = pi(j) T[j, i] E_{y_m}(i, j)",
            "recursion": "beta(i) = sum_j alpha_{n-1}(i, j); alpha~_n(i', i) = T[i, i'] beta(i) E_{yn}(i', i); "
                         "Z_n = sum alpha~_n; alpha_n = alpha~_n / Z_n",
            "log_increment": "l_n = log Z_n - log(1/2)",
            "burn_in": "W = max(1000, ceil(100 tau_c/c)) observations; the filter runs through them and every "
                       "estimator excludes them",
            "per_seed_estimator": "pilot and evaluation passes start at observation 1; R_seed = mean of l_n over "
                                  "n = W+1 .. W+n",
            "evaluation_grid": {"M": EVAL_GRID[0], "L": EVAL_GRID[1]},
            "ar1_nesting_reference": "same grid (with b = 0, so v_x = s^2), T, pi, emission, burn-in W and estimator: "
                                     "alpha~_1(i) = pi(i) E_{y1}(i); alpha~_n(i') = sum_i alpha_{n-1}(i) T[i, i'] E_{yn}(i')",
            "committed_code_tie": "the AR(1) reference with sid_lib.make_hmm's Gaussian-weight prior, one "
                                  "propagation by T before the first emission and W = 0 must reproduce "
                                  "sid_lib.hmm_rate(C, s, theta, phi, N, seed, M=121) to relative 1e-12 on "
                                  "hmm_rate's own record"},
        "simulator": {
            "method": "exact OU in units of tau_c: standardised frequency z with unit variance and unit correlation time",
            "initial_state": "z_0 ~ N(0, 1)",
            "window": "over u: z <- e^{-u} z + xi_1 and I = (1 - e^{-u}) z_start + xi_2, with Var xi_1 = 1 - e^{-2u}, "
                      "Var xi_2 = 2[u - 2(1 - e^{-u}) + (1 - e^{-2u})/2], Cov(xi_1, xi_2) = (1 - e^{-u})^2, "
                      "drawn as the lower Cholesky factor times two standard normals",
            "phase": "eps_n = s I / sqrt(2 (u - 1 + e^{-u}))",
            "dead_time": "over d = c/tau_c - u: z <- e^{-d} z + sqrt(1 - e^{-2d}) xi_3",
            "outcome": "y_n = 1 if U_n < (1 + C cos(theta + eps_n))/2",
            "draw_order": "z_0 = standard_normal(); then in blocks of 2^20 shots (the last block shorter): "
                          "standard_normal((block, 3)) followed by random(block)",
            "independence": "uses neither phi nor b; the filter never sees the simulator's variables",
            "scope": "u > 0 only; the N0 nesting check uses sid_lib.simulate records"},
        "points": points,
        "numerical_checks": {
            "NC1_nesting": {"point": "N0", "seed": 15900, "records": f"sid_lib.simulate, N = {N_NEST}",
                            "grids": ["M121_L5", "M241_L7"],
                            "tolerance": "per increment |dl| <= 1e-12 + 1e-9 |l|; |sum dl| <= 1e-9 sum |l|",
                            "also": "the committed_code_tie of reference_filter",
                            "scope": "campaign-wide; failure blocks every point"},
            "NC2_simulator": {"seeds": "numerical_checks r = 8..15", "shots_per_seed": N_SIM,
                              "statistics": "sample variance of eps against s^2; lag-k autocorrelation against "
                                            "F(u) phi^k for k = 1..5",
                              "pass": "|mean over seeds - exact| <= 5 x across-seed standard error, for every statistic"},
            "NC3_series": {"pass": "K1 and K4 change by at most 1e-6 relative from (6 terms, 1024 frequencies) "
                                   "to (12 terms, 4096 frequencies)"},
            "NC4_stationary": {"pass": "stationary_initialisation requirements on every grid used"},
            "records_for_NC5_NC6": {
                "seeds": "numerical_checks r = 0..7",
                "length": offset(2, N_CHECK),
                "estimation_window": {"first": offset(2, 1), "last": offset(2, N_CHECK)},
                "passes": check_passes(),
                "initialisation": "each pass starts from the stationary distribution at its first observation, "
                                  "runs through the observations before the estimation window as burn-in and is "
                                  "estimated over the same final observations",
                "cost_per_seed": f"simulation 2W + {N_CHECK}; M241_L7: (2W + {N_CHECK}) + (W + {N_CHECK}) filter "
                                 f"steps; M241_L5, M121_L7 and M121_L5: W + {N_CHECK} each"},
            "NC5_grid": {"compare": {f"M{M}_L{L}_W_history": "M241_L7_W_history" for M, L in CHECK_GRIDS},
                         "pass": "for each pair, |mean paired difference| + t_{0.975,7} x its standard error <= 0.001 K1"},
            "NC6_finite_history": {"compare": {"M241_L7_W_history": "M241_L7_2W_history"},
                                   "pass": "|mean paired difference| + t_{0.975,7} x its standard error <= 0.001 K1",
                                   "meaning": "the same final observations, filtered after W versus 2W preceding "
                                              "observations; only the history length differs"},
            "failure": "a failed check marks the point NUMERICAL_CHECK_FAILED: no pilot, no evaluation, no verdict. "
                       "NC1 failure blocks every point. Grid, burn-in, record length and seeds change only "
                       "through a superseding protocol version."},
        "pilot": {
            "seeds": "pilot 13000 + 20p + r, r = 0..15",
            "per_seed": f"W burn-in + n_p = {N_PILOT} post-burn-in shots on the evaluation grid",
            "recorded": "per-seed wall time and shots; across-seed sample variance S^2 of per-seed means; "
                        "pooled batch-means variance for B = 10 and B = 20 equal batches; t_step = total "
                        "filter-plus-simulation seconds / total shots including burn-in",
            "not_recorded": "per-seed means, their average, any comparator ratio",
            "variance_bound": "approximate conservative planning bound, not an exact confidence limit: "
                              "U = max(U_seed, U_bm10, U_bm20); U_seed = 15 S^2 / chi2_{0.05,15}; "
                              "U_bmB = vbar_B df_B / chi2_{0.05,df_B}, vbar_B = mean over seeds of "
                              "var(batch means, ddof=1)/B, df_B = 16 (B - 1). The chi-square factors treat "
                              "per-seed and batch means as approximately normal and batches as approximately "
                              "independent",
            "stability": "if the largest of (S^2, vbar_10, vbar_20) exceeds 4 times the smallest, the point is "
                         "PILOT_UNSTABLE and is not evaluated"},
        "shot_rule": {
            "per_seed_length": "n_e = max(n_p, 1000 ceil(t_{0.975,15}^2 U n_p / (16 (kappa delta K1)^2) / 1000))",
            "total": "N = 16 n_e post-burn-in shots, plus 16 W burn-in shots",
            "no_topups": "n_e is fixed before evaluation starts; no extension, replacement seed or early stop "
                         "based on measured means",
            "blindness": "only K1 (deterministic) and the pilot variance bound enter n_e",
            "constants_source": "t, z and chi-square quantiles are read from this protocol's constants block and "
                                "never recomputed on the execution stack; SciPy 1.10 and 1.17 already differ by "
                                "2.5e-10 relative in t(0.975, 7)",
            "note": "planned N does not decide a verdict; the realised interval does"},
        "evaluation": {
            "seeds": "evaluation 14000 + 20p + r, r = 0..15",
            "interval": "R_bar +/- t_{0.975,15} s_R / 4 (pointwise 95 %)",
            "predicted_seconds": f"{PREDICTION_MARGIN:.2f} x 16 (W + n_e) t_step",
            "order": ["E3", "E4", "E5", "E1+E2"],
            "admission": "a mandatory point is evaluated only if predicted_seconds <= 7200 and <= the remaining "
                         "aggregate budget; E1 and E2 only together, if both passed their checks and pilots, "
                         "each predicted <= 7200 s and their sum <= the remaining budget",
            "hard_stop": "budget.stop_rule"},
        "verdicts": {
            "delta": DELTA, "kappa": KAPPA, "replicates": R,
            "rule": ["NO_VERDICT if the point failed a numerical check, was PILOT_UNSTABLE, not attempted or INCOMPLETE",
                     "UNRESOLVED if R_lo <= 0 (no division)",
                     "otherwise Q = [K/R_hi, K/R_lo]",
                     "VALIDATED if Q lies inside [1 - delta, 1 + delta]",
                     "FAILED if Q is disjoint from [1 - delta, 1 + delta]",
                     "UNRESOLVED otherwise, reported without a direction"],
            "coverage": "pointwise 95 % intervals; no simultaneous coverage across the up to 20 verdicts is claimed",
            "forced_incompatibility": "Ki and Kj cannot both validate at a point iff Ki/Kj lies outside "
                                      "[(1 - delta)/(1 + delta), (1 + delta)/(1 - delta)]"},
        "closure": {
            "roadmap_F": "Primary comparator K1. F closes VALIDATED iff K1 is VALIDATED at E3, E4 and E5. "
                         "F closes FAILED iff E3, E4 and E5 all receive VALIDATED or FAILED for K1 and at least "
                         "one is FAILED. Otherwise F remains OPEN.",
            "licensed_K1": "only at the validated tuples (C, s, u, c/tau_c), within +/- delta, pointwise",
            "licensed_K2": "a statement about the lag-1-matched fit only at the tuples where K2 is VALIDATED",
            "C08_boundary": "reported separately: a finite-window binary-likelihood statement at C08's boundary "
                            "requires E1 and E2 both evaluated and the comparator VALIDATED at both; otherwise "
                            "that validation remains open, whatever F's closure",
            "diagnostics": "K3 FAILED is a rate comparison consistent with note 27; the covariance defect is "
                           "established algebraically and does not depend on it. K4 verdicts are not "
                           "finite-window truth statements.",
            "wording": {
                "before_evaluation": CAVEAT_BEFORE_EVALUATION,
                "c08_fact": _C08_FACT,
                "scope_with_mandatory_validation": SCOPE_WITH_MANDATORY_VALIDATION,
                "scope_without_mandatory_validation": SCOPE_WITHOUT_MANDATORY_VALIDATION,
                "c04_and_boundary": C04_AND_BOUNDARY,
                "status": STATUS_SENTENCE,
                "tuple_report": TUPLE_REPORT,
                "assembly": "before evaluation: before_evaluation, verbatim. After evaluation: c08_fact; then "
                            "scope_with_mandatory_validation if K1 is VALIDATED at any of E3-E5, otherwise "
                            "scope_without_mandatory_validation; then c04_and_boundary; then the status sentence "
                            "for roadmap_F; then tuple_report. The scope sentences speak only about E3-E5; E1/E2 "
                            "verdicts never enter this caveat and are reported under C08_boundary. The campaign "
                            "status never determines the scope sentence.",
                "reference_implementation": "tools/build_protocol_F.py closure_wording and roadmap_F_status"},
            "post_unblinding": "any analysis not specified here is labelled post-unblinding and cannot change a verdict"},
        "budget": {
            "numerical_threads": 1,
            "aggregate_cap_seconds": AGGREGATE_CAP_SECONDS,
            "aggregate_clock": "the sum of wall-clock seconds recorded by every sid_run13 phase (numerical checks, "
                               "pilots and evaluations) in its res13 artifact; each run reads the remaining budget "
                               "from those records before it starts",
            "gate3_deadline_seconds": GATE3_DEADLINE_SECONDS,
            "gate3_deadline": "enforced from the start of the Gate-3 run for every step, including NC1, NC3 and the "
                              "first point's measurement, and never later than the remaining aggregate budget; a "
                              "step reaching it is stopped and recorded INCOMPLETE, and an incomplete NC1 blocks "
                              "every point",
            "gate3_order": ["NC1 and NC3", "E3", "E4", "E5", "E1", "E2"],
            "gate3_admission": "before each point's NC2, NC4-NC6 and pilot, predict their cost from the measured "
                               "t_step (the first point is run to measure it, within the deadline) and mark the "
                               "point NOT_ATTEMPTED if the prediction exceeds the time left before the deadline; "
                               "E1 and E2 are admitted together",
            "point_cap_seconds": POINT_CAP_SECONDS,
            "prediction_margin": PREDICTION_MARGIN,
            "stop_margin": STOP_MARGIN,
            "stop_rule": "every evaluation run stops at start + min(stop_margin x predicted_seconds, "
                         "point_cap_seconds, remaining aggregate seconds at its start); a stopped run is "
                         "INCOMPLETE and receives no verdict"},
        "seeds": seeds(),
        "execution_stack": {
            "conda_definition": STACK_SPEC,
            "pip_definition": PIP_SPEC,
            "pins": {"python": PYTHON_PIN, "numpy": NUMPY_PIN, "scipy": SCIPY_PIN},
            "platform": "osx-arm64, native; an osx-64 environment under Rosetta is a different stack and is not permitted",
            "channel_policy": "conda-forge only: both the solve and the installation pass --override-channels -c "
                              "conda-forge with the same spec file, so configured channels such as defaults "
                              "cannot enter either step",
            "blas": "OpenBLAS, pinned in the spec as libblas=*=*openblas",
            "commands": {
                "environment": {"CONDA_SUBDIR": "osx-arm64"},
                "solve": SOLVE_ARGS,
                "install": INSTALL_ARGS,
                "verify_architecture": ["file", "$ENV/bin/python3.12"],
                "conda_list_json": ["conda", "list", "-n", "sid-f", "--json"],
                "pip_report": ["$ENV/bin/python", "-m", "pip", "install", "--dry-run", "--no-cache-dir",
                               "--report", "analysis/stack_F/pip-report.json", "-r", PIP_SPEC],
                "pip_lock": ["$ENV/bin/python", "tools/lock_stack_F.py", "pip-lock", "analysis/stack_F/pip-report.json",
                             "analysis/stack_F/conda-list.json", "analysis/stack_F/pip-lock.txt"],
                "pip_install": ["$ENV/bin/python", "-m", "pip", "install", "--no-deps", "--require-hashes",
                                "--no-cache-dir", "-r", "analysis/stack_F/pip-lock.txt"],
                "conda_lock": ["conda", "list", "-n", "sid-f", "--explicit", "--md5"],
                "pip_installed": ["$ENV/bin/python", "-m", "pip", "list", "--format=json", "--verbose"],
                "record": ["$ENV/bin/python", "tools/lock_stack_F.py", "record", "analysis/stack_F/conda-list.json",
                           "analysis/stack_F/stack-record.json"]},
            "reviewed_solve": REVIEWED_SOLVE,
            "superseded_solve": SUPERSEDED_SOLVE + " (python=3.12 without a patch pin resolved to 3.12.0)",
            "stop_conditions": [
                "the installed conda package set (name, version, build) differs from the reviewed dry-run solve; "
                "channel metadata can change between the two steps",
                "the solve or installation takes any package from a channel other than conda-forge",
                "any conda package's subdir is neither osx-arm64 nor noarch",
                "libblas's build string does not contain openblas",
                f"python is not {PYTHON_PIN}, or numpy is not {NUMPY_PIN}, or scipy is not {SCIPY_PIN}",
                "the installed python binary is not arm64",
                "pip would install, upgrade or remove a distribution already provided by conda, or a pip report "
                "entry lacks a sha256"],
            "locks": {"conda": "analysis/stack_F/conda-osx-arm64.lock (conda list --explicit --md5)",
                      "conda_json": "analysis/stack_F/conda-list.json",
                      "pip": "analysis/stack_F/pip-lock.txt (name==version --hash=sha256:...) and "
                             "analysis/stack_F/pip-report.json",
                      "pip_installed": "analysis/stack_F/pip-installed.json (installer recorded per distribution)",
                      "record": "analysis/stack_F/stack-record.json"},
            "threads": "OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS, VECLIB_MAXIMUM_THREADS and "
                       "NUMEXPR_NUM_THREADS all equal 1, set before numpy is imported",
            "recorded": "python patch version, platform.machine(), numpy build configuration, libblas and "
                        "libopenblas build strings, thread variables, git revision, protocol digest",
            "refusal": f"sid_run13.py refuses a dirty tree, a python other than {PYTHON_PIN}, numpy or scipy other "
                       "than the pins, a machine other than arm64, a libblas build without openblas, any thread "
                       "variable other than 1, a DRAFT status or a digest mismatch",
            "timing": "all locks are committed before Gate 3"},
        "outputs": {"numerical_checks": "analysis/reproduction/res13_F_numerical_checks.json",
                    "pilot": "analysis/reproduction/res13_F_pilot.json",
                    "evaluation": "analysis/reproduction/res13_F_evaluation.json"},
        "constants": constants,
        "design_evidence": {"record": "deterministic quantities computed by the builder on the drafting stack; "
                                      "the execution stack must reproduce them. Roundoff-level quantities are "
                                      "recorded as bounds, not values",
                            "points": evidence},
        "digest": None,
    }


def equivalent(a, b, rel=1e-9, abs_tol=1e-14):
    """Structural equality with float tolerance, for rebuilds on another numerical stack."""
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
    """A draft must equal its rebuild; a frozen protocol must verify its digest and equal the rebuild
    apart from the fields the freeze set."""
    rebuilt = build() if rebuilt is None else rebuilt
    if is_draft(doc):
        return equivalent(doc, rebuilt)
    return is_verified_frozen(doc) and equivalent(unfrozen_view(doc), unfrozen_view(rebuilt))


def markdown(doc):
    pts, ev = doc["points"], doc["design_evidence"]["points"]
    names = ["E1", "E2", "E3", "E4", "E5", "N0"]
    status = {n: "mandatory" if n in pts["mandatory"] else "conditional" if n in pts["conditional_pair"]
              else "nesting" for n in names}
    lines = ["| Point | Status | C | s | u | c/τ_c | φ | F(u) | b | W | K1 (nats/shot) |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for n in names:
        p, e = pts[n], ev[n]
        lines.append(f"| {n} | {status[n]} | {p['C']:.6f} | {p['s']:.6f} | {p['u']:.6f} | {p['c_over_tau_c']:.6f} | "
                     f"{e['phi']:.6f} | {e['F']:.6f} | {e['b']:.6f} | {e['burn_in_W']} | {e['comparators']['K1']:.6e} |")
    lines += ["", "| Point | K2/K1 | K3/K1 | K4/K1 | K3/K4 | Forced-incompatible pairs at δ = 0.05 |",
              "|---|---:|---:|---:|---:|---|"]
    for n in names:
        r, f = ev[n]["ratios"], ev[n]["forced_incompatible_pairs"]
        bad = ", ".join(k for k, v in f.items() if v) or "none"
        lines.append(f"| {n} | {r['K2/K1']:.6f} | {r['K3/K1']:.6f} | {r['K4/K1']:.6f} | {r['K3/K4']:.6f} | {bad} |")
    lines += ["", "| Point | Innovation SD / spacing, M121 L5 | same, M241 L7 | TV(π, Gaussian) < 1e-6, all grids | "
                  "TV < 1e-10, grids | Series within 1e-6 (K1, K4) |",
              "|---|---:|---:|---|---|---|"]
    for n in names:
        g, c = ev[n]["grids"], ev[n]["series_convergence_within_1e-6"]
        below6 = all(d["tv_stationary_vs_gaussian_weights_below_1e-6"] for d in g.values())
        below10 = ", ".join(k for k, d in g.items() if d["tv_stationary_vs_gaussian_weights_below_1e-10"]) or "none"
        lines.append(f"| {n} | {g['M121_L5']['innovation_sd_over_spacing']:.2f} | {g['M241_L7']['innovation_sd_over_spacing']:.2f} | "
                     f"{below6} | {below10} | {c['K1']}, {c['K4']} |")
    lines += ["", "E1/E2 archive indices: " + "; ".join(
        f"{n}: C0 column {pts[n]['archive_indices']['C0_column']}, tau_c row {pts[n]['archive_indices']['tau_c_row']}, "
        f"tau index {pts[n]['archive_indices']['tau_index']}" for n in ("E1", "E2"))]
    k = doc["constants"]
    lines += ["", f"Constants: t(0.975, 15) = {k['t_0975_df15']:.6f}; t(0.975, 7) = {k['t_0975_df7']:.6f}; "
                  f"z(0.975) = {k['z_0975']:.6f}; χ²(0.05, 15) = {k['chi2_005_df15']:.6f}; "
                  f"χ²(0.05, 144) = {k['chi2_005_df144']:.4f}; χ²(0.05, 304) = {k['chi2_005_df304']:.4f}; "
                  f"band [{k['band_lower']:.6f}, {k['band_upper']:.6f}]; (t/z)² = {(k['t_0975_df15'] / k['z_0975']) ** 2:.4f}"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only comparison with the committed protocol")
    mode.add_argument("--markdown", action="store_true", help="read-only table output")
    mode.add_argument("--freeze", action="store_true", help="approved Gate-1 step: freeze the reviewed draft")
    ap.add_argument("--out", type=Path, default=OUT, help="destination for a new draft")
    args = ap.parse_args()
    if args.freeze:
        try:
            digest = freeze_protocol(OUT)
        except ProtocolFrozenError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        print(f"froze {OUT.relative_to(ROOT)} with digest {digest}")
        return 0
    doc = build()
    if args.markdown:
        print(markdown(json.loads(OUT.read_text()) if OUT.exists() else doc))
        return 0
    if args.check:
        ok = OUT.exists() and matches_builder(json.loads(OUT.read_text()), doc)
        print("protocol_F.json matches its builder" if ok else "protocol_F.json differs from its builder")
        return 0 if ok else 1
    try:
        write_draft(doc, args.out)
    except ProtocolFrozenError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.out} (DRAFT revision {DRAFT_REVISION}, digest null)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
