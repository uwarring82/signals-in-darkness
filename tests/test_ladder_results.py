"""The unblinded ladder results must keep estimate, envelope and target apart.

The failure this guards is the standard one: quoting the diagnostic envelope as if it were a
benchmark. The envelope is minimised over the same sample it is scored on, so it is biased
downward and licenses no comparison. It is recorded because it bounds the sample, and because
it carries the hard falsifier.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = json.loads((ROOT / "analysis" / "ladder_results_C.json").read_text())
SEL = json.loads((ROOT / "analysis" / "selections_ladder_C.json").read_text())
ELIG = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())
TCCS = ("20.0", "5.0", "1.0")
LEARNERS = ("greedy", "sampling")


def test_digest_and_bindings():
    payload = {k: v for k, v in RES.items() if k != "digest"}
    assert hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16] \
        == RES["digest"]
    assert RES["selections_digest"] == SEL["digest"]
    assert RES["eligibility_digest"] == ELIG["digest"]


def test_measured_members_are_the_frozen_ones():
    """Nothing may be re-chosen at evaluation time."""
    for op, blk in RES["operating_points"].items():
        for t in TCCS:
            cell = blk["cells"][t]
            assert cell["benchmarks"]["L1"]["member"] == SEL["operating_points"][op]["L1"][t]["member"]
            assert cell["benchmarks"]["L2"]["member"] == SEL["operating_points"][op]["L2"]["member"]
            assert cell["benchmarks"]["L3"]["member"] == SEL["operating_points"][op]["L3"][t]["member"]


def test_envelope_is_labelled_and_never_called_a_benchmark():
    for blk in RES["operating_points"].values():
        for t in TCCS:
            env = blk["cells"][t]["diagnostic_envelope"]
            assert env["not_a_benchmark"] is True
            assert "DIAGNOSTIC ONLY" in env["status"]


def test_hard_falsifier_holds():
    """No learner beats the envelope: the envelope is never SLOWER than either learner.

    Lower delay is better, so the envelope -- a minimum over a set that CONTAINS each learner --
    always beats or ties every learner. The inequality is D_envelope <= D_learner. Saying the
    envelope "cannot beat a learner" states the reverse and is wrong; the assertion below has
    always tested the correct direction, but the prose described the opposite.
    """
    assert isinstance(RES["falsifier_check"], str), RES["falsifier_check"]
    for blk in RES["operating_points"].values():
        for t in TCCS:
            cell = blk["cells"][t]
            env = cell["diagnostic_envelope"]["mean"]
            for L in LEARNERS:
                assert env <= cell["learners"][L]["mean"] + 1e-9


def test_cells_where_a_rung_is_the_learner_carry_their_caveat():
    for blk in RES["operating_points"].values():
        for t in TCCS:
            for rung, e in blk["cells"][t]["benchmarks"].items():
                if e["is_a_learner"]:
                    assert "not an independent benchmark" in e["caveat"]
                    assert e["vs_learner"][e["member"]]["ratio_learner_over_benchmark"] == 1.0


def test_unresolved_contrasts_are_not_called_resolved():
    """A confidence interval spanning 1 must not be reported as a direction."""
    for blk in RES["operating_points"].values():
        for t in TCCS:
            for e in blk["cells"][t]["benchmarks"].values():
                for v in e["vs_learner"].values():
                    lo, hi = v["ci95"]
                    spans_one = lo <= 1.0 <= hi
                    assert v["resolved"] is not spans_one
                    if spans_one:
                        assert v["direction"] == "unresolved"


def test_no_oracle_or_regret_language():
    """Scan the CLAIMS, not the disclaimer that denies making them.

    A bare substring check fails on its own disclaimer -- 'no oracle, optimal or regret claim is
    made' contains all three words while asserting the opposite. This repository has made that
    mistake three times; the fix is to narrow the scan, never to drop the guard.
    """
    disclaimer = RES["language"]
    for word in ("oracle", "optimal", "regret"):
        assert word in disclaimer, "the disclaimer must name the words it disclaims"

    scanned = {k: v for k, v in RES.items() if k != "language"}
    blob = json.dumps(scanned).lower()
    for word in ("oracle", "regret"):
        assert word not in blob, f"{word!r} used outside the disclaimer"


def test_the_calibration_confound_is_classified_per_cell():
    """Every resolved-negative cell must be classified from MEASURED ARLs, never from h ratios."""
    c = RES["calibration_confound_checked"]
    assert "not threshold ratios" in c["method"]
    seen = set()
    for op, blk in RES["operating_points"].items():
        for t in TCCS:
            for rung in ("L1", "L2"):
                e = blk["cells"][t]["benchmarks"][rung]
                if e["is_a_learner"]:
                    continue
                key = f"{op}/tau_c={float(t)}/{rung}"
                assert key in c["cells"], f"{key} unclassified"
                row = c["cells"][key]
                seen.add(key)
                slower = e["vs_learner"]["sampling"]["ci95"][0] > 1.0
                if not slower:
                    assert row["status"] == "not_a_negative_cell"
                elif row["sampling_arl_shorter"]:
                    assert row["status"] == "directionally_robust"
                else:
                    assert row["status"] == "requires_measured_sensitivity"
    assert seen == set(c["cells"])


def test_conditional_cells_are_declared_conditional():
    """A cell whose mismatch runs the dangerous way may not be reported as settled."""
    c = RES["calibration_confound_checked"]
    pending = c["unresolved_without_measurement"]
    if pending:
        assert "CONDITIONAL" in c["status"]
        for k in pending:
            assert c["cells"][k]["status"] == "requires_measured_sensitivity"
    else:
        assert "directionally robust" in c["status"]
