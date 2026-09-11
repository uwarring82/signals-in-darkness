"""The frozen ladder eligibility and reconciliation artifacts must stay self-consistent.

Eligibility gates which candidates the L1/L2/L3 selections may range over, so a silent edit to
it would silently change the benchmark. These check the artifacts against their own declared
rule rather than against remembered numbers.
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ELIG = json.loads((ROOT / "analysis" / "eligibility_ladder_C.json").read_text())
RECON = json.loads((ROOT / "analysis" / "reconciliation_C.json").read_text())
CLASS = json.loads((ROOT / "analysis" / "schedule_class_C.json").read_text())
MEMBERS = [s["name"] for specs in CLASS["class"].values() for s in specs]
GAMMA, ENVELOPE = 3.0e4, 0.30


def _digest(doc):
    return hashlib.sha256(json.dumps({k: v for k, v in doc.items() if k != "digest"},
                                     sort_keys=True).encode()).hexdigest()[:16]


def test_digests_match_contents():
    assert _digest(ELIG) == ELIG["digest"]
    assert _digest(RECON) == RECON["digest"]


def test_every_candidate_is_decided_at_both_points():
    for op in ("pilot", "stress"):
        blk = ELIG["operating_points"][op]
        assert blk["candidates"] == 13
        decided = set(blk["eligible"]) | set(blk["ineligible"])
        for m in MEMBERS + ["greedy", "sampling"]:
            assert m in decided, f"{m} undecided at {op}"
        assert len(decided) == 13


def test_verdicts_follow_the_declared_envelope_rule():
    """Eligibility must be reproducible from the recorded ARL, not merely asserted."""
    for op in ("pilot", "stress"):
        blk = ELIG["operating_points"][op]
        for name, row in blk["calibrations"].items():
            inside = abs(row["ARL"] - GAMMA) / GAMMA <= ENVELOPE
            assert inside == row["inside_envelope"], f"{op}/{name} verdict contradicts its ARL"
            assert (name in blk["eligible"]) == inside, f"{op}/{name} listing contradicts rule"


def test_no_eligibility_decision_rests_on_a_censored_confirmation():
    """A capped null run makes the ARL a downward-biased lower bound, which cannot clear a ceiling."""
    for op in ("pilot", "stress"):
        for name, row in ELIG["operating_points"][op]["calibrations"].items():
            assert row["capped"] == 0, f"{op}/{name} decided on a censored confirmation"


def test_marginal_members_are_all_disclosed():
    """Anything within one standard error of the boundary must be named, not buried."""
    listed = ELIG["marginality"]
    listed_keys = set() if isinstance(listed, str) else {m.split(":")[0] for m in listed}
    for op in ("pilot", "stress"):
        for name, row in ELIG["operating_points"][op]["calibrations"].items():
            near = GAMMA * (1 + ENVELOPE) if row["pct_off_target"] > 0 else GAMMA * (1 - ENVELOPE)
            if row["se"] > 0 and abs(row["ARL"] - near) / row["se"] < 1.0:
                assert f"{op}/{name}" in listed_keys, f"{op}/{name} is marginal but undisclosed"


def test_reconciliation_covers_every_cell_and_records_no_failure():
    assert RECON["completed"] == RECON["total"] == 22
    for r in RECON["rows"]:
        assert r["outcome"] != "PENDING"
        assert r["outcome"] != "PREDICTION_FAILED", (
            f"{r['operating_point']}/{r['member']} failed its reproduction prediction")


def test_exact_reproduction_claims_are_backed_by_bit_identity():
    """An EXACT_H row may only be marked held if the thresholds are literally equal."""
    exact = [r for r in RECON["rows"] if r["predicted"] == "EXACT_H"]
    assert exact, "no EXACT_H rows: the conditional property would be untested"
    for r in exact:
        assert r["difference"]["h_identical"] is True
        assert r["archived"]["h"] == r["fresh"]["h"]
        assert r["difference"]["h_delta"] == 0.0


def test_the_conditional_property_is_named_with_its_test():
    prop = RECON["conditional_property"]
    assert "test_calibration_cap_independence" in prop["verified_by"]
    assert (ROOT / "tests" / "test_calibration_cap_independence.py").exists()
