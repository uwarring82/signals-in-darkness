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


def test_L3_contains_the_learner_so_its_falsifier_is_true_by_construction():
    """The repair. With the learner inside the class the selector can always choose it, so L3's
    ratio is at most the learner's at every tau_c. Only then is a loss diagnostic."""
    assert LADDER["L3"]["class_size"] == CLASS["size"] + 1
    assert "posterior policy" in LADDER["L3"]["class"]
    assert "digest" in LADDER["L3"]["class"]
    assert "cannot beat L3 by construction" in LADDER["L3"]["why_the_learner_is_in_the_class"]


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
    assert "FINITE-CLASS" in LADDER["L3"]["licenses"]


def test_the_superseded_preregistration_is_kept_and_points_forward():
    """The correction is valuable history; the first attempt is not deleted."""
    assert "superseded_by" in CLASS
    assert CLASS["superseded_by"]["file"] == "analysis/benchmark_ladder_C.json"
    assert LADDER["supersedes"]["commit"] == "e5f779a"
    assert "invalid" in LADDER["supersedes"]["why"]


def test_no_C_measurement_exists_yet():
    """This file is a preregistration. If a C artifact appears, these definitions were not
    frozen before the data and this test must be deleted deliberately."""
    for name in os.listdir(os.path.join(ROOT, "analysis", "outputs")):
        assert "posterior" not in name and "res10" not in name, (
            f"{name} exists: roadmap C was measured before its ladder was frozen")
