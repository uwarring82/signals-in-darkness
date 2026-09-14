"""The ARL-matched sensitivity analysis must obey its own frozen protocol.

This is a POST-UNBLINDING analysis, so the protections that matter are procedural: it must
declare what it is, follow the interpolation rule frozen before the curves were inspected,
never extrapolate, and reproduce the frozen measurements it claims to extend.

Skipped when the artifact is absent, so the suite stays green before the curves land.
"""
import hashlib
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATCHED = ROOT / "analysis" / "arl_matched_C.json"
pytestmark = pytest.mark.skipif(not MATCHED.exists(),
                                reason="matched comparison not yet computed")

PROTO = json.loads((ROOT / "analysis" / "sensitivity_protocol_C.json").read_text())
RES = json.loads((ROOT / "analysis" / "ladder_results_C.json").read_text())
ELIG = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())


def _doc():
    return json.loads(MATCHED.read_text())


def test_digest_and_bindings():
    d = _doc()
    body = {k: v for k, v in d.items() if k != "digest"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16] == d["digest"]
    assert d["protocol_digest"] == PROTO["digest"]
    assert d["ladder_results_digest"] == RES["digest"]
    assert d["eligibility_digest"] == ELIG["digest"]


def test_declares_itself_post_unblinding():
    """It may not be presented as part of the preregistered result."""
    d = _doc()
    assert "POST-UNBLINDING" in d["status"]
    assert "NOT PART OF THE PREREGISTERED RESULT" in d["status"]


def test_reproduces_the_frozen_measurements_it_extends():
    """The grid point at sampling's calibrated threshold, and each benchmark's own null."""
    for op, chk in _doc()["reproduction_check"].items():
        assert chk["sampling_null_reproduces"], op
        assert chk["sampling_delays_reproduce"], op
        assert chk["benchmark_nulls_reproduce"], op


def test_no_cell_is_extrapolated():
    """The protocol forbids extrapolation; unbracketed cells must be NOT_MATCHABLE instead."""
    for key, c in _doc()["cells"].items():
        if c.get("status") == "MATCHED":
            continue
        assert c["status"] == "NOT_MATCHABLE", key
        assert not c["required_matching"], (
            f"{key} requires matching but its target was not bracketed; the protocol forbids "
            f"extrapolating to it")


def test_every_cell_that_required_matching_was_matched():
    d = _doc()
    required = [k for k, v in RES["calibration_confound_checked"]["cells"].items()
                if v["status"] == "requires_measured_sensitivity"]
    assert required, "no cell required matching; the fixture no longer exercises this"
    for k in required:
        assert k in d["cells"], f"{k} required matching and is absent"
        assert d["cells"][k]["status"] == "MATCHED", k


def test_curve_is_monotone_so_the_inversion_is_well_defined():
    """Step 1 inverts log ARL against h; a non-monotone curve would make that ambiguous."""
    for op, c in _doc()["curves"].items():
        assert c["monotone_in_h"], f"{op}: ARL is not monotone in h"


def test_each_matched_cell_reports_the_required_quantities():
    for key, c in _doc()["cells"].items():
        if c.get("status") != "MATCHED":
            continue
        for f in ("benchmark_arl", "h_sampling_matched", "delay_sampling_matched",
                  "delay_benchmark", "ratio", "ci95"):
            assert f in c, f"{key} is missing {f}"
        assert c["ci95"][0] <= c["ci95"][1]


def test_unresolved_is_never_reported_as_a_direction():
    for key, c in _doc()["cells"].items():
        if c.get("status") != "MATCHED":
            continue
        lo, hi = c["ci95"]
        spans_one = lo <= 1.0 <= hi
        assert c["resolved"] is not spans_one, key
        if spans_one:
            assert c["direction"] == "unresolved", key


def test_matched_ratio_is_consistent_with_its_own_delays():
    for key, c in _doc()["cells"].items():
        if c.get("status") != "MATCHED":
            continue
        expect = c["delay_sampling_matched"] / c["delay_benchmark"]
        assert abs(expect - c["ratio"]) < 1e-6, key
