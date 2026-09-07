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
    assert (P.C, P.s) == (shot["operating_point_pilot"]["C_eff"], shot["operating_point_pilot"]["s"])
    assert [P.THM, P.THX] == shot["action_set"]["theta"]
    assert P.GAMMA == shot["false_alarm_target"]["value"]
    assert [P.M, P.L] == [shot["bank"]["M"], shot["bank"]["L"]]


def test_second_operating_point_is_at_the_parity_ceiling():
    """D2: the second point sits AT the parity ceiling C_par <= 1/2, so it stays inside the
    oscillator-cancelled regime that carries the principal claims and does not depend on roadmap D."""
    second = MANIFEST["shot_stack"]["operating_point_second"]
    assert second["C_eff"] == 0.5, "second point must sit at the parity ceiling"
    assert second["s"] == 0.3
    assert "STRESS TEST" in second["label"], "the stress-test labelling is not optional"
    servo = MANIFEST["shot_stack"]["operating_point_servo_appendix"]
    assert servo["C_eff"] == 0.8 and "NON-GATING" in servo["status"]


def test_no_ambiguous_C_bar_field_survives_anywhere():
    """D1: B's C_eff and E's C_0 are different physical quantities and must not share a field."""
    blob = json.dumps(MANIFEST)
    assert '"C_bar"' not in blob, "an ambiguous C_bar field is back in the manifest"


def test_identifiability_stack_matches_run7():
    src = open(os.path.join(ROOT, "analysis", "runs", "sid_run7.py"), encoding="utf-8").read()
    ident = MANIFEST["identifiability_stack"]
    assert "for C0 in (0.4, 0.9):" in src, "run7's archived C_0 grid moved"
    assert list(ident["C_0"]["principal_regime"]) == [0.4, 0.5], "E's principal-regime slices are 0.4 and 0.5"
    assert 0.9 in ident["C_0"]["value"] and "MUST NOT" in ident["C_0"]["note"]
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


def test_delta0_at_the_second_point_matches_the_manifest():
    """One of the three grid points (tau_c/c = 20) is outside leading-order mid-fringe validity,
    which is why pre_B_sequence step 5 requires the exact comparator at 5 and 20."""
    import numpy as np
    from sid_lib import rk_exact
    second = MANIFEST["shot_stack"]["operating_point_second"]
    # delta(0) = 2 sum_{k>=1} r_k, summed directly rather than by importing sid_core,
    # which is a script and would run the whole analysis on import.
    def d0(C, s, tcc):
        a = math.exp(-1.0 / tcc)
        return 2.0 * float(np.sum(rk_exact(C, s, a ** np.arange(1, 20000))))
    got = [d0(second["C_eff"], second["s"], tcc) for tcc in (1.0, 5.0, 20.0)]
    assert got == pytest.approx([0.023949, 0.185840, 0.802549], rel=1e-3)
    assert list(second["delta0_at_grid"].values()) == pytest.approx(got, rel=1e-3)
    assert sum(g > 0.3 for g in got) == 1


def test_strict_and_slope_helpers_are_separately_named_and_differ():
    """The former ambiguous I_mid_lo is split. They agree through strict O(s^4) and diverge
    above it; a result attributing a number to the card formula must call the slope form."""
    from sid_lib import I_mid_strict, I_mid_slope, I_lo_theta_strict, I_lo_theta_slope, S2_point
    import sid_lib
    assert not hasattr(sid_lib, "I_mid_lo"), "the ambiguous name is back"
    assert not hasattr(sid_lib, "I_lo_theta"), "the ambiguous name is back"
    C, s, tcc = 0.4, 0.5, 20.0
    S2 = S2_point(tcc)
    assert I_mid_strict(C, s, S2) / I_mid_slope(C, s, S2) == pytest.approx(math.exp(2 * s * s), rel=1e-12)
    # they converge as s -> 0, which is what "agree through strict O(s^4)" means
    assert I_mid_strict(C, 1e-4, S2) / I_mid_slope(C, 1e-4, S2) == pytest.approx(1.0, abs=1e-7)
    th = math.pi / 3
    assert I_lo_theta_strict(C, s, S2, th) > I_lo_theta_slope(C, s, S2, th)


def test_C25_quotes_the_slope_form_not_the_strict_asymptote():
    """C25 attributes its comparison to the card formula, so it must carry 1496, not 907."""
    from sid_lib import I_mid_slope, S2_point
    h = 6.9
    assert h / I_mid_slope(0.4, 0.5, S2_point(20.0)) == pytest.approx(1495.6, rel=1e-3)
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    blk = txt.split("- id: C25")[1].split("- id:")[0]
    assert "1496" in blk and "910" in blk, "C25 must carry the corrected value and say what it replaced"


def test_withdrawn_rows_are_named_so_B_cannot_reuse_them():
    txt = open(os.path.join(ROOT, "ledgers", "status.yaml"), encoding="utf-8").read()
    for cid in MANIFEST["must_not_reuse"]:
        if not cid.startswith("C"):
            continue
        row = [ln for ln in txt.splitlines() if ln.strip().startswith(f"- id: {cid}")]
        assert row, f"manifest forbids reusing {cid}, which is not in the ledger"
        blk = txt.split(f"- id: {cid}")[1].split("- id:")[0]
        assert "withdrawn" in blk, f"{cid} is no longer withdrawn; re-check the manifest's must_not_reuse"
