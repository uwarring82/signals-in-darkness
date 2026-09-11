"""The frozen L1/L2/L3 selections must be legal under the predeclared rules.

These guard the property that makes the ladder interpretable: each rung's member was named
using only the selection stream, from the frozen class, restricted to candidates that passed
eligibility on their calibration alone.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEL = json.loads((ROOT / "analysis" / "selections_ladder_C.json").read_text())
ELIG = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())
LADDER = json.loads((ROOT / "analysis" / "benchmark_ladder_C.json").read_text())
TCCS = ("20.0", "5.0", "1.0")
L1_CLASS = {"mid", "ext"}
L2_CLASS = {"interleave-B1", "interleave-B10", "switch@300", "switch@1000"}


def test_digest_matches_contents():
    payload = {k: v for k, v in SEL.items() if k != "digest"}
    assert hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16] \
        == SEL["digest"]


def test_binds_the_eligibility_it_was_built_from():
    assert SEL["eligibility_digest"] == ELIG["digest"]


def test_every_selected_member_is_eligible_at_that_point():
    """A benchmark may not be a policy held to a different false-alarm rate."""
    for op, blk in SEL["operating_points"].items():
        eligible = set(ELIG["operating_points"][op]["eligible"])
        for t in TCCS:
            assert blk["L1"][t]["member"] in eligible
            assert blk["L3"][t]["member"] in eligible
        assert blk["L2"]["member"] in eligible


def test_members_come_from_their_declared_classes():
    for op, blk in SEL["operating_points"].items():
        for t in TCCS:
            assert blk["L1"][t]["member"] in L1_CLASS
        assert blk["L2"]["member"] in L2_CLASS
        # L3 ranges over all 13 candidates
        assert blk["L3"][t]["member"] in set(ELIG["operating_points"][op]["eligible"])


def test_selection_used_only_the_selection_stream():
    assert "700" in SEL["stream"]
    assert "200" in SEL["evaluation_stream_not_read"]


def test_l2_ineligible_members_were_excluded_not_silently_kept():
    for op, blk in SEL["operating_points"].items():
        eligible = set(ELIG["operating_points"][op]["eligible"])
        considered = set(blk["L2"]["considered"])
        assert considered == {m for m in L2_CLASS if m in eligible}
        for m in blk["L2"]["excluded_as_ineligible"]:
            assert m not in eligible


def test_l2_records_its_ratio_denominator():
    """The predeclared rule did not name one, so the artifact must."""
    for blk in SEL["operating_points"].values():
        assert blk["L2"]["ratio_denominator"].strip()


def test_cells_where_l3_selected_a_learner_are_named():
    named = SEL["L3_selected_a_learner_at"]
    actual = {f"{op}/tau_c={float(t)}" for op, blk in SEL["operating_points"].items()
              for t in TCCS if blk["L3"][t]["member"] in ("greedy", "sampling")}
    if actual:
        assert set(named) == actual, "a cell where L3 chose a learner is not disclosed"
    else:
        assert isinstance(named, str)


def test_no_regret_or_oracle_language_is_licensed():
    """L4 is not attempted, so these words are unavailable at every rung."""
    assert LADDER["L4"]["attempted"] is False
    blob = json.dumps(SEL).lower()
    for word in ("oracle", "optimal", "regret"):
        assert word not in blob, f"{word!r} appears in the selections artifact"
