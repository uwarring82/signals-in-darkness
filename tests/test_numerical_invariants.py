"""Directional claims, enforced as arithmetic rather than as wording.

Four direction-of-inequality errors have now been found in this project's prose, each with
correct code underneath: the falsifier ("cannot beat a learner" for an inequality that says the
opposite), the censoring bound ("only violation of a floor"), the regret bias ("understate"), and
public hedge counts quoted from point estimates. Checking wording catches these only if someone
thinks to re-read the sentence. Checking arithmetic catches them whenever the suite runs.

Each test below asserts the NUMBER, and where a direction could plausibly go either way it also
exhibits a counterexample, so the invariant cannot be satisfied vacuously.
"""
import json
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import resolve_errata                                                   # noqa: E402
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
from sid_identifiability import G, TAU_OVER_T2, s2_of

RES = json.loads((ROOT / "analysis" / "ladder_results_C.json").read_text())
LADDER = json.loads((ROOT / "analysis" / "benchmark_ladder_C.json").read_text())
ERRATA = json.loads((ROOT / "analysis" / "errata_C.json").read_text())
HEDGE = json.loads((ROOT / "analysis" / "hedge_bootstrap_C.json").read_text())
TCCS = ("20.0", "5.0", "1.0")
LEARNERS = ("greedy", "sampling")
GAMMA, ENVELOPE = 3.0e4, 0.30
IDENT = json.loads((ROOT / "analysis/outputs/res9_identifiability_T2.json").read_text())["rows"]


def test_nested_baseline_classes_cannot_reverse_the_information_order():
    """B is a subset of A: I_A <= true infimum over B <= every feasible B candidate."""
    strict = []
    for row in IDENT:
        for candidate in row["optimizer"]["starts"]:
            # Verify feasibility before using the candidate as an upper bound.
            assert all(1-row["eta_0"] <= x <= 1+row["eta_0"] for x in candidate["x"])
            assert candidate["fun"] >= row["I_A"]
        assert row["I_B"] >= row["I_A"]
        assert row["I_B"] == min(c["fun"] for c in row["optimizer"]["starts"])
        strict.append(row["I_B"] > row["I_A"])
    assert any(strict), "the subset comparison must include a strict gap"


def test_fast_noise_ratio_is_necessary_but_not_sufficient_for_scan_separation():
    """The exact OU exponent lies below the fast-noise limit at every finite grid time."""
    below_threshold = []
    incomplete_scan = []
    unseparated_scan = []
    for row in IDENT:
        v = row["tau_c_over_T2"]
        exact = np.array([s2_of(u, v)/2 for u in TAU_OVER_T2])
        fast = G*G*v*TAU_OVER_T2
        assert np.all(exact < fast)
        separated = exact > 2*row["eta_0"]*TAU_OVER_T2
        assert int(separated.sum()) == row["class_A_points_passing"]
        ratio = row["DeltaGamma_over_2eta0_Gamma_hat"]
        if separated.any():
            assert ratio > 1  # necessary
        if ratio <= 1:
            below_threshold.append(row)
            assert not separated.any()
            assert row["I_A"] == 0
        elif not separated.all():
            incomplete_scan.append(row)
            if not separated.any():
                unseparated_scan.append(row)
    assert below_threshold, "the necessary-condition check would be vacuous"
    assert incomplete_scan, "need a counterexample to separation at every time"
    assert unseparated_scan, "ratio > 1 can even fail to separate anywhere on this finite scan"


# --------------------------------------------------------------------------- errata reachability
def test_errata_target_still_matches_the_live_frozen_digest():
    """If the ladder were ever re-frozen, the erratum would silently detach from it."""
    assert ERRATA["target_digest"] == LADDER["digest"], (
        "errata_C.json targets a digest the ladder no longer has; the correction is dangling")


def test_every_artifact_carrying_the_affected_digest_resolves_to_the_errata():
    errata = resolve_errata.load_errata()
    assert errata, "no errata loaded"
    affected = []
    for p in resolve_errata.artifacts():
        if p.name in resolve_errata.ERRATA_FILES:
            continue
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        hits = resolve_errata.digests_in(doc) & set(errata)
        if hits:
            affected.append(p)
            for d in hits:
                assert errata[d], f"{p.name} carries {d} with an empty errata list"
    # The frozen ladder itself always carries its own digest, so this can never be empty.
    assert affected, "no artifact resolved to the errata; the resolver is not seeing them"


# ------------------------------------------------------------------ censoring is a LOWER bound
def test_censoring_can_only_lower_a_mean():
    """measured <= true, for every cap, on real null runs."""
    src = ROOT / "analysis" / "reproduction" / "res12_sensitivity_pilot.json"
    if src.exists():
        pts = json.loads(src.read_text())["points"]
        runs = np.asarray(next(iter(pts.values()))["null_runs"], float)
    else:                      # reproduction outputs are git-ignored; fall back to a fixture
        rng = np.random.default_rng(0)
        runs = rng.exponential(30_000, 512)
    true_mean = runs.mean()
    for cap in (1_000, 10_000, 30_000, 100_000):
        assert np.minimum(runs, cap).mean() <= true_mean + 1e-9
    # non-vacuity: at least one cap must actually bind, or this proves nothing
    assert np.minimum(runs, 10_000).mean() < true_mean


def test_a_lower_bound_settles_only_two_of_the_four_directions():
    """It can show ceiling VIOLATION and floor COMPLIANCE; never their opposites.

    Both impossibilities are demonstrated by counterexample, so the claim is arithmetic.
    """
    ceiling, floor = GAMMA * (1 + ENVELOPE), GAMMA * (1 - ENVELOPE)
    rng = np.random.default_rng(7)
    runs = rng.exponential(GAMMA, 4096)

    for cap in (5_000, 20_000, 60_000):
        measured = np.minimum(runs, cap).mean()
        true = runs.mean()
        if measured > ceiling:                 # violation of a ceiling: provable
            assert true > ceiling
        if measured >= floor:                  # compliance with a floor: provable
            assert true >= floor

    # counterexample 1: measured <= ceiling while true > ceiling -- compliance with a ceiling
    # is NOT provable from a lower bound. This is exactly why eligibility refuses censored rows.
    heavy = np.full(4096, ceiling * 2.0)
    assert np.minimum(heavy, ceiling * 0.5).mean() <= ceiling < heavy.mean()

    # counterexample 2: measured < floor while true >= floor -- violation of a floor is NOT
    # provable either, which is the direction the old wording claimed.
    assert np.minimum(heavy, floor * 0.5).mean() < floor <= heavy.mean()


# --------------------------------------------------------- envelope is never slower than a learner
def test_envelope_is_never_slower_than_either_learner():
    gaps = []
    for blk in RES["operating_points"].values():
        for t in TCCS:
            cell = blk["cells"][t]
            env = cell["diagnostic_envelope"]["mean"]
            for L in LEARNERS:
                gap = cell["learners"][L]["mean"] - env
                assert gap >= -1e-9, "a learner beat the envelope it is minimised inside"
                gaps.append(gap)
    assert max(gaps) > 0, "every gap is exactly zero; the invariant would hold vacuously"


def test_a_downward_biased_target_overstates_regret():
    """regret = learner - target. Substituting something SMALLER than the target enlarges it."""
    for blk in RES["operating_points"].values():
        for t in TCCS:
            cell = blk["cells"][t]
            env = cell["diagnostic_envelope"]["mean"]
            for L in LEARNERS:
                learner = cell["learners"][L]["mean"]
                # any true target is at least the envelope, since the envelope is the sample min
                for target in (env, env * 1.05, env * 1.20):
                    assert (learner - env) >= (learner - target) - 1e-9
                # and strictly larger whenever the bias is non-zero
                if env * 1.05 > env:
                    assert (learner - env) > (learner - env * 1.05)


# ------------------------------------------------------- public counts come from the measurement
def _word_to_int(w):
    return {"zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}[w.lower()]


def test_public_hedge_counts_match_the_structured_bootstrap():
    """Every 'N of five' in public prose must equal the RESOLVED count, or be marked superseded.

    'four of five' was a point-estimate count that reached the public page as an ordering. The
    structured bootstrap record is the single source; prose is checked against it.
    """
    stress = HEDGE["operating_points"]["stress"]
    resolved = stress["n_resolved_better"]
    point_only = stress["n_better_on_point_estimate"]
    assert resolved == sum(r["resolved_better"] for r in stress["policies"].values())
    assert point_only > resolved, "the fixture no longer distinguishes the two counts"

    pat = re.compile(r"\b(zero|no|one|two|three|four|five)\s+of\s+five\b", re.I)
    checked = 0
    for rel in ("docs/where-we-are.md", "docs/status.md", "ledgers/roadmap.yaml",
                "ledgers/status.yaml"):
        p = ROOT / rel
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            for m in pat.finditer(line):
                ctx = line[max(0, m.start() - 120):m.end() + 160].lower()
                # a superseded count QUOTED as history is not a live claim
                if any(s in ctx for s in ("counted point estimate", "corrects", "superseded",
                                          "earlier", "marginal error propagation", "'four of",
                                          "'two of")):
                    continue
                checked += 1
                assert _word_to_int(m.group(1)) == resolved, (
                    f"{rel}: '{m.group(0)}' does not match the resolved count {resolved}")
    assert checked > 0, "no live hedge count found; this test would pass vacuously"
