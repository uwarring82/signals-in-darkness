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
    assert LADDER["L3"]["class_size"] == CLASS["size"] + 1


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


def test_no_C_measurement_exists_yet():
    """This file is a preregistration. If a C artifact appears, these definitions were not
    frozen before the data and this test must be deleted deliberately."""
    for name in os.listdir(os.path.join(ROOT, "analysis", "outputs")):
        assert "posterior" not in name and "res10" not in name, (
            f"{name} exists: roadmap C was measured before its ladder was frozen")


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
