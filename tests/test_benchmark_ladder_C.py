"""Roadmap C's benchmark ladder, asserted before any C measurement exists.

The first preregistration (e5f779a) claimed a falsifier its construction could not support:
L3's class held only PRECOMMITTED schedules while the posterior policy sits outside it, so the
learner beating L3 is what you expect if feedback helps, not a diagnostic. These tests pin the
repair, so the property is checked rather than asserted in prose.
"""
import hashlib
import json
import os

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LADDER = json.load(open(os.path.join(ROOT, "analysis", "benchmark_ladder_C.json"),
                        encoding="utf-8"))
CLASS = json.load(open(os.path.join(ROOT, "analysis", "schedule_class_C.json"), encoding="utf-8"))


def test_the_schedule_class_digest_is_intact():
    """The eleven-member class was frozen first and must not drift."""
    body = dict(CLASS)
    for k in ("digest", "superseded_by"):
        body.pop(k, None)
    assert hashlib.sha256(
        json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16] == CLASS["digest"], "the frozen schedule class has been edited"
    assert CLASS["size"] == 11
    assert LADDER["schedule_class"]["frozen_digest"] == CLASS["digest"]


def test_L3_separates_the_population_optimum_from_the_selected_estimate():
    """The second repair, and the one that took two attempts to get right.

    Putting the learner in the class guarantees only that it CAN be selected. It does not
    guarantee that whichever member IS selected beats it out of sample. The mathematical
    property belongs to the population optimum; the observable quantity is an estimate.
    """
    o = LADDER["L3"]["three_distinct_objects"]
    assert set(o) == {"target", "estimate", "diagnostic_envelope"}
    assert o["target"]["observable"] is False, "an estimand is being reported as a measurement"
    assert o["estimate"]["observable"] is True
    assert "CAN lose" in o["estimate"]["property"]
    assert o["diagnostic_envelope"]["optimistically_biased"] is True
    # two learners since 8 Sept: greedy retained as a negative baseline alongside sampling
    assert LADDER["L3"]["class_size"] == CLASS["size"] + 2


def test_the_hard_falsifier_is_attached_only_to_the_diagnostic_envelope():
    f = LADDER["falsifier"]
    assert "DIAGNOSTIC ENVELOPE" in f["hard"]
    assert "NOT a falsifier" in f["not_a_falsifier"]
    assert "selection instability" in f["not_a_falsifier"]


def test_selection_on_finite_data_really_can_pick_a_worse_member():
    """The claim, demonstrated rather than asserted.

    Candidates with a true best, selected on one independent sample and scored on another. If
    membership alone guaranteed domination this would never lose; it does, which is exactly why
    the guarantee had to be moved off the estimate.
    """
    import numpy as np
    # Scaled to THIS measurement's regime, not a convenient one: roadmap B's worst-case ratios
    # are ~1.6 with standard errors ~0.17, and the candidates differ by 0.03 to 0.4. The noise
    # is therefore comparable to or larger than the gaps being selected on, which is exactly
    # the regime where selection instability bites.
    rng = np.random.default_rng(3)
    trials = 4000
    truth = np.array([1.60, 1.61, 1.63, 2.02, 2.55])   # candidate 0 is genuinely best
    se = 0.17                                           # measured scale, not chosen for effect
    losses = 0
    for _ in range(trials):
        sel = truth + rng.normal(0, se, truth.size)
        ev = truth + rng.normal(0, se, truth.size)
        if ev[int(np.argmin(sel))] > ev[0]:   # selected member worse than the learner, in-sample
            losses += 1
    frac = losses / trials
    assert frac > 0.20, (
        f"independent selection lost to the learner in only {100*frac:.1f} % of trials; if the "
        f"effect were this small the preregistration would be overstating the risk")
    assert LADDER["L3"]["three_distinct_objects"]["estimate"]["property"].count("CAN lose") == 1


def test_a_learner_failing_the_envelope_does_not_silently_leave_the_class():
    """Otherwise the invalid first construction returns by the back door: a domination claim
    over eleven precommitted schedules with the learner quietly removed."""
    text = LADDER["L3"]["learner_ineligibility"]
    assert "NO COMPARABLE LEARNER RESULT" in text
    assert "must NOT simply drop out" in text


def test_L2_has_an_explicit_selection_rule_on_the_selection_seeds():
    """'Best robust schedule from B' was underspecified and would have been chosen on B's own
    evaluation data -- the selection bias the ladder exists to avoid."""
    rule = LADDER["L2"]["selection_rule"]
    assert "700" in rule and "200" in rule, "L2 does not separate selection from evaluation"
    assert "smallest worst-case delay ratio" in rule.replace("SMALLEST", "smallest")
    assert len(LADDER["L2"]["class"]) == 4


def test_ineligibility_is_decided_by_calibration_not_by_result():
    e = LADDER["eligibility"]
    assert "INELIGIBLE" in e["rule"]
    assert "never by the delay result" in e["predeclared"]
    assert "switch@300" in e["why"], "the known instance is not named"


def test_no_rung_licenses_oracle_or_regret_language_without_L4():
    assert LADDER["L4"]["attempted"] is False
    assert "no C result may use those words" in LADDER["L4"]["licenses"]
    assert "Not finite-class regret" in LADDER["L3"]["licenses"], (
        "L3's estimate is a noisy selection procedure's out-of-sample performance, not the "
        "population best-in-class value, so the difference from it is not regret")
    assert LADDER["L3"]["regret_language"]["status"].startswith("no such estimate")


def test_the_superseded_preregistration_is_kept_and_points_forward():
    """The correction is valuable history; the first attempt is not deleted."""
    assert "superseded_by" in CLASS
    assert CLASS["superseded_by"]["file"] == "analysis/benchmark_ladder_C.json"
    assert "e5f779a" in LADDER["supersedes"]["commits"]
    assert "bb102d3" in LADDER["supersedes"]["commits"]
    assert "ALSO FALSE" in LADDER["supersedes"]["why"]


def test_no_calibrated_or_confirmatory_delay_result_exists_yet():
    """The guard, corrected 8 Sept 2026.

    It first asserted that NOTHING had been measured, which stopped being true when an R=8
    scouting table was produced. It then said "no confirmatory measurement", which is still
    loose: R=8 AND R=32 design evidence both exist, for both policies. The accurate condition
    is that no CALIBRATED or CONFIRMATORY DELAY result exists. Design evidence does, at
    uncalibrated thresholds, and is recorded in analysis/scouting_C_greedy.json.
    """
    for name in os.listdir(os.path.join(ROOT, "analysis", "outputs")):
        assert "posterior" not in name and "res10" not in name, (
            f"{name} exists: roadmap C was measured before its ladder was frozen")
    scout = json.load(open(os.path.join(ROOT, "analysis", "scouting_C_greedy.json"),
                           encoding="utf-8"))
    assert scout["status"] == "SCOUTING, not confirmatory"
    assert "correction_appended_2026_09_08" in scout, "the correction was not appended"
    # the original account must SURVIVE the correction, not be replaced by it
    assert scout["scouting_measurement"]["results_mid_fringe_fraction"]["stress"]["1.0"] == 1.000, (
        "the original R=8 account was overwritten; corrections are appended here")
    assert scout["revision"], "the scouting run names no revision"
    for field in ("R", "cap", "h", "seeds"):
        assert field in scout["scouting_measurement"], f"scouting run does not record {field}"
    assert scout["scouting_measurement"]["limitations"], "scouting run states no limitations"


def test_scouting_separates_deterministic_properties_from_measured_ones():
    """The starting action and switching thresholds are closed-form consequences of the rate
    table; the switching table is data. Presenting them together would let a deterministic fact
    borrow the authority of a measurement, or a thin measurement borrow the certainty of a
    theorem."""
    scout = json.load(open(os.path.join(ROOT, "analysis", "scouting_C_greedy.json"),
                           encoding="utf-8"))
    det = scout["deterministic_properties"]
    assert "NOT measurements" in det["what"]
    assert det["pilot"]["posterior_mass_on_tau_c_1_needed_to_switch"] == 0.578
    assert det["stress"]["posterior_mass_on_tau_c_1_needed_to_switch"] == 0.770
    assert "R=8" in scout["scouting_measurement"]["what"]


def test_self_trapping_is_an_open_question_not_a_result():
    """Absorbing and merely-slow are different claims; the scouting data settles neither."""
    scout = json.load(open(os.path.join(ROOT, "analysis", "scouting_C_greedy.json"),
                           encoding="utf-8"))
    assert "MATHEMATICALLY self-trapping" in scout["not_yet_established"]
    assert "OPERATIONALLY trapped" in scout["not_yet_established"]
    assert "independently seeded confirmation" in scout["may_become_a_negative_result_only_after"]


def test_diagnostics_cannot_be_satisfied_by_pooled_frequencies_alone():
    """A policy can be nominally adaptive and behaviourally constant; pooling hides it."""
    dg = LADDER["required_diagnostics"]
    null_s = " ".join(dg["store"]["null_stream"]).lower()
    post_s = " ".join(dg["store"]["post_change_stream"]).lower()
    # tau_c does not exist under H0, so the null stream must not be GROUPED by it. The text may
    # legitimately mention true tau_c in a negation ("no true tau_c does"), so the check is on
    # the grouping phrase rather than on the words appearing at all -- the third time in this
    # suite that a bare substring test would have flagged a correct sentence for saying the
    # opposite of what it forbids.
    assert "by true tau_c" not in null_s, (
        "null diagnostics are grouped by a tau_c that does not exist under H0")
    assert "operating point" in null_s and "seed stream" in null_s
    assert "true tau_c" in post_s, "post-change diagnostics are not grouped by the real tau_c"
    for s in (null_s, post_s):
        assert "switch counts" in s and "tie counts" in s
    assert "EVALUATION STRATUM" in dg["store"]["stratification_caveat"]
    assert "POST-CHANGE behaviour specifically" in dg["acceptance"], (
        "the acceptance rule is not scoped to post-change behaviour")
    assert "nothing to adapt to" in dg["acceptance"]


def test_L3_holds_both_learners_and_names_the_pilot_informed_one():
    assert LADDER["L3"]["class_size"] == CLASS["size"] + 2
    for dig in ("fa22bac9ac38d6d7", "1778e8ebd51c92cb",
                "8b9c96327df16cae", "53a01df4b279cbbf"):
        assert dig in LADDER["L3"]["class"], f"{dig} is not named in L3's class"
    ln = LADDER["learners"]
    assert ln["posterior_sampling"]["status"] == "PILOT-INFORMED, not blind"
    assert "NOT retired" in ln["greedy_posterior_expected_rate"]["status"]
    assert "did not survive" in ln["greedy_posterior_expected_rate"]["why_retained"]


def test_design_seeds_are_excluded_from_calibration_and_evaluation():
    """Action randomness must not reuse a stream the policy was designed on."""
    excluded = set(LADDER["learners"]["posterior_sampling"]
                   ["design_seeds_excluded_from_calibration_and_evaluation"])
    used = set()
    for off in (0, 7000):
        used |= {100 + off, 900 + off} | {200 + int(t) + off for t in (20, 5, 1)}
    assert not (excluded & used), f"design seeds reused for measurement: {sorted(excluded & used)}"
    assert 5150 in excluded, "the action seed is not excluded"


def test_the_acceptance_rule_demands_an_interval_not_a_floor():
    a = LADDER["required_diagnostics"]["acceptance"]
    assert "INTERVAL, not a bare floor" in a
    assert "[-0.7, 7.8]" in a, "the unresolved example is not recorded"
    assert "UNDEMONSTRATED -- which is different from absent" in a


def test_responsiveness_is_marked_provisional_and_detection_is_not_implied():
    pl = LADDER["provisional_language"]
    assert any("BALANCED" in s for s in pl["supported_now"])
    assert any("more responsive" in s for s in pl["provisional"])
    assert any("better detection" in s for s in pl["not_implied_by_either"])
