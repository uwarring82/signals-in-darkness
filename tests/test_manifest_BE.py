"""The B/E parameter manifest, made executable.

A manifest that merely records values drifts the moment the code moves; this file
asserts that every constant it declares as source=code is still what the code holds,
and that the three hazards it names are still real. If one of these fails, the fix is
to update analysis/manifest_BE.json and its note -- not to relax the assertion.
"""
import json, math, os, sys
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "analysis", "lib"))
MANIFEST = json.load(open(os.path.join(ROOT, "analysis", "manifest_BE.json"), encoding="utf-8"))


def test_manifest_is_strict_json_and_declares_its_record():
    txt = open(os.path.join(ROOT, "analysis", "manifest_BE.json"), encoding="utf-8").read()
    for bad in ("NaN", "Infinity"):
        assert bad not in txt, f"manifest carries non-RFC-8259 literal {bad}"
    assert os.path.exists(os.path.join(ROOT, MANIFEST["record"])), "manifest names a record that does not exist"


def test_shot_stack_matches_sid_policies():
    import sid_policies as P
    shot = MANIFEST["shot_stack"]
    assert (P.C, P.s) == (shot["operating_point_pilot"]["C_bar"], shot["operating_point_pilot"]["s"])
    assert [P.THM, P.THX] == shot["action_set"]["theta"]
    assert P.GAMMA == shot["false_alarm_target"]["value"]
    assert [P.M, P.L] == [shot["bank"]["M"], shot["bank"]["L"]]


def test_second_operating_point_appears_nowhere_in_committed_code():
    """The manifest calls C_bar=0.8, s=0.3 'proposed'. If someone lands it in code,
    that claim becomes false and the manifest must be re-locked."""
    assert MANIFEST["shot_stack"]["operating_point_second"]["source"] == "proposed"
    import sid_policies as P
    assert (P.C, P.s) != (0.8, 0.3), "second operating point is now in code; re-lock the manifest"


def test_identifiability_stack_matches_run7():
    src = open(os.path.join(ROOT, "analysis", "runs", "sid_run7.py"), encoding="utf-8").read()
    ident = MANIFEST["identifiability_stack"]
    assert "for C0 in (0.4, 0.9):" in src
    assert list(ident["C_bar_0"]["value"]) == [0.4, 0.9]
    assert "for eta0 in (0.02, 0.05, 0.10):" in src
    assert list(ident["eta_0"]["value"]) == [0.02, 0.05, 0.10], "manifest and run7 disagree on eta_0"
    assert "np.linspace(0.1*T2, 2.0*T2, 40)" in src
    assert ident["tau_scan"]["points"] == 40


def test_u_is_tau_over_tau_c_not_c_over_tau_c():
    """The distinction the manifest exists to protect: rho_1 = F(tau/tau_c) exp(-c/tau_c),
    so the AR(1) reduction is exact as tau/tau_c -> 0, not as c/tau_c -> 0."""
    for f in ("sid_run3.py", "sid_run4.py"):
        src = open(os.path.join(ROOT, "analysis", "runs", f), encoding="utf-8").read()
        assert "u = taus/tc" in src, f"{f} no longer defines u = tau/tau_c"
    F = lambda u: (math.cosh(u) - 1) / (u - 1 + math.exp(-u))
    assert F(1e-6) == pytest.approx(1.0, abs=1e-9)
    assert F(1.0) == pytest.approx(1.4762462210, abs=1e-9)


def test_hazard_delta0_outside_validity_at_the_second_point():
    """Two of the three proposed tau_c/c points sit outside leading-order mid-fringe validity."""
    sys.path.insert(0, os.path.join(ROOT, "analysis", "runs"))
    from sid_core import delta0
    got = [delta0(0.8, tcc, s=0.3) for tcc in (1.0, 5.0, 20.0)]
    assert got == pytest.approx([0.061281, 0.475708, 2.054372], rel=1e-4)
    assert sum(g > 0.3 for g in got) == 2, "hazard text says two of three points exceed delta(0)=0.3"


def test_hazard_I_mid_lo_still_omits_the_exp_factor():
    """C02's statement says the leading-order rate carries e^{-2s^2}; the helper omits it.
    Recorded as a defect in note 13. When it is fixed, this test must be updated together
    with C02, C12 and the affected archived columns -- not before."""
    from sid_lib import I_mid_lo, S2_point
    C, s, tcc = 0.4, 0.5, 20.0
    code = I_mid_lo(C, s, S2_point(tcc))
    assert code == pytest.approx(0.5 * C**4 * s**4 * S2_point(tcc), rel=1e-15)
    assert code != pytest.approx(code * math.exp(-2 * s * s), rel=1e-6)


def test_withdrawn_rows_are_named_so_B_cannot_reuse_them():
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    for cid in MANIFEST["must_not_reuse"]:
        if not cid.startswith("C"):
            continue
        row = [ln for ln in txt.splitlines() if ln.strip().startswith(f"- id: {cid}")]
        assert row, f"manifest forbids reusing {cid}, which is not in the ledger"
        blk = txt.split(f"- id: {cid}")[1].split("- id:")[0]
        assert "withdrawn" in blk, f"{cid} is no longer withdrawn; re-check the manifest's must_not_reuse"
