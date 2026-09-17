"""Contract tests for analysis/protocol_D.json and tools/build_protocol_D.py (roadmap D1).

The specification is prepared for review, not frozen: these tests check that the committed draft is
exactly what its builder produces, that the freezing machinery refuses what it should, and that the
clauses the D0 review required are present and say what they must.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
import build_protocol_D as bd  # noqa: E402

PATH = ROOT / "analysis" / "protocol_D.json"
DOC = json.loads(PATH.read_text())


def test_the_committed_draft_is_what_the_builder_produces():
    assert bd.matches_builder(DOC)
    assert bd.is_draft(DOC) and DOC["digest"] is None
    assert not bd.is_verified_frozen(DOC)
    assert DOC["note"] == "notes/2026-09-16-note-29-D-plan-draft.md"


def test_the_builder_writes_drafts_and_refuses_frozen_files(tmp_path):
    target = tmp_path / "protocol_D.json"
    bd.write_draft(bd.build(), target)
    assert bd.is_draft(json.loads(target.read_text()))
    digest = bd.freeze_protocol(target, "2026-09-18")
    frozen = json.loads(target.read_text())
    assert bd.is_verified_frozen(frozen) and frozen["digest"] == digest
    assert bd.matches_builder(frozen)
    with pytest.raises(bd.ProtocolFrozenError):
        bd.write_draft(bd.build(), target)             # a draft may not replace a frozen file
    with pytest.raises(bd.ProtocolFrozenError):
        bd.freeze_protocol(target, "2026-09-19")       # nor may it be frozen twice
    before = target.read_bytes()
    with pytest.raises(bd.ProtocolFrozenError):
        bd.write_draft(bd.build(), target)
    assert target.read_bytes() == before


def test_a_tampered_frozen_document_does_not_verify(tmp_path):
    target = tmp_path / "protocol_D.json"
    bd.write_draft(bd.build(), target)
    bd.freeze_protocol(target, "2026-09-18")
    doc = json.loads(target.read_text())
    doc["classification"]["tolerance"] = 0.05
    assert not bd.is_verified_frozen(doc) and not bd.matches_builder(doc)


def test_the_design_points_declare_their_order_and_disjoint_seeds():
    points = DOC["design_points"]
    assert [p["role"] for p in points.values()] == ["primary", "sensitivity"]
    assert points["K5"]["kappa"] == 5.0 and points["K5"]["seed_block"] == 0
    assert points["K10"]["kappa"] == 10.0 and points["K10"]["seed_block"] == 1
    for point in points.values():
        assert point["rho"] == pytest.approx(0.8187307530779818, rel=1e-12)   # exp(-1/5)
        assert point["control_rho"] == 0.0
        assert point["sigma"] > 0
    everything = [s for p in points.values() for block in p["seeds"].values() for s in block]
    assert len(everything) == len(set(everything)), "seed blocks must be disjoint"
    assert len(points["K5"]["seeds"]["pilot"]) == DOC["pilot"]["replicates"]
    assert len(points["K5"]["seeds"]["evaluation"]) == DOC["records"]["replicates"]


def test_the_marginal_is_matched_to_the_von_mises_moment():
    import math
    from scipy.special import i0e, i1e
    for point in DOC["design_points"].values():
        kappa, sigma = point["kappa"], point["sigma"]
        assert math.exp(-sigma ** 2 / 2) == pytest.approx(float(i1e(kappa) / i0e(kappa)), rel=1e-12)


def test_the_two_nesting_checks_are_distinguished():
    checks = DOC["numerical_checks"]
    fisher, kl = checks["ND1a_fisher_nesting"], checks["ND1b_kl_nesting"]
    assert "exact" in fisher["sampling"] and "tolerance_relative" in fisher
    assert kl["mean_tolerance_standard_errors"] >= 1, "the sampled KL agrees only within sampling error"
    assert "increment_tolerance_absolute" in kl
    assert "both KL filters" in checks["ND7_burn_in"]["requirement"]
    assert "frozen before the checks run" in checks["failure"]


def test_numerical_uncertainty_can_change_the_verdict():
    allowance = DOC["uncertainty"]["numerical_allowance"]
    assert "J(0)" in allowance and "widen" in allowance
    assert "survive" in allowance and "convergence threshold does not settle" in allowance
    assert any(c.get("enters_allowance") for c in DOC["numerical_checks"].values() if isinstance(c, dict))
    rule = DOC["classification"]["rule"]
    assert any("touches it" in clause for clause in rule), "touching the tolerance is UNRESOLVED"
    assert DOC["classification"]["tolerance"] == 0.02
    assert "never the change-from-independence criterion" in DOC["classification"]["channel_agreement"]


def test_the_estimator_and_sizing_rules_are_stated():
    assert "conditional-information average" in DOC["estimands"]["slope"]
    assert "S_N^2/N is not an estimator" in DOC["estimands"]["score"]
    assert DOC["sizing_rule"]["kappa_D"] == 0.25
    assert "no extension or replacement record" in DOC["sizing_rule"]["no_topups"]
    assert DOC["pilot"]["not_recorded"].startswith("no per-record J")
    assert "2.097152e11" in DOC["budget"]["cost_note"]
    assert DOC["budget"]["threads"] == 1
    assert set(DOC["outputs"]) == {"checks", "pilot", "evaluation"}
    assert all(v.startswith("analysis/reproduction/res15_D_") for v in DOC["outputs"].values())


def test_the_model_records_why_the_state_is_unwrapped():
    model = DOC["model"]
    assert "unwrapped" in model["latent_state"] and "2 pi rho" in model["latent_state"]
    assert "grid[::3]" in model["offsets"] and "13x13" in model["offsets"]
    assert "common random numbers" in model["records"]
