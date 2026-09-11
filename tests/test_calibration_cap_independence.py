"""The confirmation cap cannot alter the calibrated threshold.

This property is load-bearing for reproduction claims. Roadmap C reconciles fresh calibrations
against roadmap B's archived ones, and predicts that a member calibrated at aab80b7 or later
reproduces its threshold EXACTLY at HEAD. The only change to calibrate_refined since aab80b7 is
commit 5024d59, which moved the final confirmation from the search cap to a larger uncensored
one. That prediction is therefore valid ONLY IF the confirmation cap is applied strictly after h
has been selected -- otherwise the archived and fresh thresholds are not comparable at all and
the whole reconciliation is unfounded.

Reading the code is not enough to license a scientific prediction, so the property is measured.

WHY THESE PARAMETERS. A test of this shape fails silently in two ways, both of which an earlier
draft actually hit:
  - DEGENERATE h: if the search returns a bracket endpoint or a bisection midpoint, h is pinned
    by the bracket geometry and no downstream change could move it, so agreement proves nothing.
    The settings below converge the bracket TWO-SIDED (endpoint is None) and land h OFF the
    bisection grid, i.e. on a genuine secant iterate chosen by the best-of-measured line that
    aab80b7 added -- the very branch that selects h.
  - VACUOUS CAP: if neither cap ever binds, the two runs are literally the same computation.
    The small cap here truncates most confirmation runs, and the test asserts that it did.

The converse is asserted too: the SEARCH cap does change h. Without that, a test showing "h did
not move" cannot distinguish a real invariance from an apparatus too blunt to detect anything.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
import sid_policies as P            # noqa: E402

# Converges two-sided and puts h on a secant iterate; see the module docstring.
KW = dict(R=8, lo=0.5, hi=4.0, iters=4, seed=11, confirm_R=8, max_secant=2)
GAMMA, SEARCH_CAP = 2000, 40_000
SMALL_CONFIRM, LARGE_CONFIRM = 800, 60_000


def _calibrate(cap, confirm_cap):
    bank = P.Bank([1.0, 4.0], P.PILOT)
    return P.calibrate_refined(bank, P.sched_mid, GAMMA, cap=cap,
                               confirm_cap=confirm_cap, **KW)


def test_confirmation_cap_cannot_alter_threshold():
    small = _calibrate(SEARCH_CAP, SMALL_CONFIRM)
    large = _calibrate(SEARCH_CAP, LARGE_CONFIRM)
    h_s, m_s, _, nc_s, ep_s, _ = small
    h_l, m_l, _, nc_l, ep_l, _ = large

    # The apparatus must be non-degenerate, or agreement below is uninformative.
    assert ep_s is None and ep_l is None, (
        f"bracket hit an endpoint ({ep_s!r}, {ep_l!r}); h would be pinned by the bracket, not "
        f"chosen, and this test would prove nothing")
    grid = (KW["hi"] - KW["lo"]) / 2 ** KW["iters"] / 2
    steps = (h_l - KW["lo"]) / grid
    assert abs(steps - round(steps)) > 1e-9, (
        f"h={h_l!r} sits on the bisection grid, so it is a midpoint or bracket anchor rather "
        f"than a secant iterate; the branch that selects h is not being exercised")

    # The cap must actually bind, or both runs are the same computation.
    assert nc_s > 0 and nc_l == 0, (
        f"VACUOUS: the small cap censored {nc_s} runs and the large one {nc_l}; the caps must "
        f"differ in effect for this comparison to mean anything")
    assert m_s != m_l, (
        f"VACUOUS: the confirmed ARL did not move with confirm_cap ({m_s} vs {m_l})")

    # The property itself.
    assert h_s == h_l, (
        f"confirm_cap CHANGED the threshold: {h_s!r} (cap {SMALL_CONFIRM}) vs {h_l!r} "
        f"(cap {LARGE_CONFIRM}). Every exact-reproduction prediction across 5024d59 is void.")
    assert ep_s == ep_l


def test_search_cap_does_change_the_threshold():
    """The converse: this test can detect a moved threshold, so the invariance above is real."""
    wide = _calibrate(SEARCH_CAP, LARGE_CONFIRM)
    tight = _calibrate(3_000, LARGE_CONFIRM)
    assert wide[0] != tight[0], (
        "the search cap did not move h either, so this test cannot distinguish invariance from "
        "an apparatus with no resolution")
