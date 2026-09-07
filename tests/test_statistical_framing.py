"""Guards on statistical *meaning*, which the other contracts do not check.

tests/test_tutorials.py verifies that a notebook imports rather than restates, is
deterministic, writes nothing, and labels its conclusions against the ledger. All of that
passed while notebook 01 asserted something false: that a count-based test at mid-fringe has
*no* power against a correlated process. It does have power -- the correlations roughly double
the variance of the count -- and provenance checks cannot see an error of that kind.

These tests pin the specific confusions that were actually made here. They are narrow on
purpose: each one corresponds to a mistake in the record, not to a general principle.
"""
import json
import math
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "analysis", "lib"))
NB01 = os.path.join(ROOT, "tutorials", "01_when_the_coin_has_memory.ipynb")


def _nb_text(path):
    with open(path, encoding="utf-8") as fh:
        nb = json.load(fh)
    return "\n".join("".join(c["source"]) for c in nb["cells"])


def _plain(text):
    """Emphasis stripped and whitespace collapsed.

    A phrase check must not be defeated by a bold word inside the phrase, nor by the line
    wrapping that puts "is not" and "strictly deaf" on different lines.
    """
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text))


def _docs(name):
    with open(os.path.join(ROOT, "docs", name), encoding="utf-8") as fh:
        return fh.read()


def test_a_fixed_mean_is_not_a_fixed_distribution():
    """The error itself: at mid-fringe the marginal is exactly 1/2, but the count is
    overdispersed, so a count-only test has limited power rather than none."""
    from sid_lib import rk_exact
    C, s, tau_c, N = 0.4, 0.5, 20.0, 4000
    a = math.exp(-1.0 / tau_c)
    k = np.arange(1, N)
    vif = 1 + 2 * float(np.sum((1 - k / N) * rk_exact(C, s, a ** k)))
    assert vif == pytest.approx(2.2130, rel=1e-3), (
        "the variance-inflation factor moved; notebook 01's overdispersion numbers must be redone")
    assert vif > 1.0, "positive lag correlations must inflate the variance of the count"


def test_notebook_01_does_not_claim_the_count_test_is_powerless():
    text = _plain(_nb_text(NB01)).lower()
    for phrase in ("it has none", "no power at all", "has none.",
                   "does not merely have low power"):
        assert phrase not in text, (
            f"notebook 01 claims the count test is powerless ({phrase!r}). It is not: the "
            f"correlations roughly double the variance of the count.")
    # and it must state the correct thing
    assert "overdispersion" in text, "notebook 01 does not name the mechanism"
    assert "variance-inflation factor" in text
    assert "realised" in text, (
        "notebook 01 must distinguish two realised records from the processes generating them")


def test_notebook_01_does_not_claim_the_extremum_is_deaf_to_ordering():
    """The extremum's pair correlations begin at higher order and are small in the principal
    regime, but they are not zero -- that is claim C24, which is open."""
    text = _nb_text(NB01)
    low = _plain(text).lower()
    for sentence in re.split(r"(?<=[.!?])\s+", low):
        if "deaf to ordering" in sentence:
            assert "not strictly deaf to ordering" in sentence, (
                "notebook 01 calls the extremum deaf to ordering; C24 says otherwise and is open")
        if "deaf to the count" in sentence or "deaf to balance" in sentence:
            assert "not strictly deaf" in sentence, (
                "notebook 01 calls mid-fringe deaf to the count; it is overdispersed, "
                "not uninformative")
    assert "exactly deaf to balance" not in low
    assert "correlation bonus omitted" in low, \
        "the flat extremum curve must be labelled as omitting its correlation bonus"
    assert re.search(r"C24\s*[-—]\s*open", text), \
        "notebook 01 must cite C24 with its actual status, which is open"


def test_notebook_01_does_not_generalise_that_memory_is_always_slower():
    text = _nb_text(NB01).lower()
    assert "memory takes longer than balance" not in text, (
        "notebook 01's own crossover shows the memory channel overtaking the balance channel; "
        "the claim must be scoped to the weak-correlation regime")
    assert "weak-correlation regime" in text


def test_the_iid_scale_is_not_called_a_standard_error_for_a_correlated_record():
    text = _nb_text(NB01).lower()
    if "1/sqrt(n)" in text or "sqrt{n}" in text:
        assert "iid" in text, (
            "the 1/sqrt(N) band must be labelled an approximate iid reference scale, not a "
            "standard error for the correlated record, which it understates")


def test_public_prose_does_not_overstate_reproducibility():
    """One withdrawn historical table has irrecoverable provenance."""
    body = _docs("index.md")
    assert "every number can be recomputed" not in body.lower(), \
        "index.md overstates reproducibility; one withdrawn table cannot be reproduced"
    assert "`result` and `pilot`" in body, "the reproducibility claim is not scoped"


def test_public_prose_separates_the_leading_order_curve_from_the_exact_map():
    """C23 limits the closed-form leading-order crossover, not C05's exact-comparator map."""
    body = _docs("where-we-are.md")
    section = body.split("**C23")[1].split("**C26")[0]
    assert "leading-order" in section, "the C23 paragraph does not name the leading-order curve"
    assert "exact" in section and "unaffected" in section, (
        "the C23 paragraph must say the exact map is unaffected, or it reads as a limit on C05")


def test_public_prose_distinguishes_the_two_nuisance_classes():
    """The broad pointwise class does produce exact-zero rows; the Markov class does not."""
    body = _docs("where-we-are.md")
    section = body.split("**C26")[1].split("Supporting these")[0]
    assert "exactly zero" in section, (
        "the C26 paragraph must say the broad class does give exact zero, or it understates the "
        "strength of the non-identifiability result")
    assert "shape-constrained" in section and "broad class" in section


def test_public_prose_does_not_say_C24_bounds_anything():
    body = _docs("where-we-are.md")
    for cid_sentence in re.findall(r"\*\*C24\*\*[^.]*\.", body):
        assert "bounds a" not in cid_sentence, \
            "C24 is open; its proposed 6 % ceiling is not established, so it bounds nothing yet"


def test_nonzero_power_is_not_presented_as_eventual_certainty():
    """The alternative differs from the null in WIDTH, not centre, so the count-only test's
    power plateaus at 2*Phi(-1.96/sqrt(V_inf)) = 18.83 % however long the record gets. Saying
    a low-power statistic "gets there eventually" is false for this test."""
    from sid_lib import rk_exact
    from scipy.stats import norm
    C, s, tau_c = 0.4, 0.5, 20.0
    a = math.exp(-1.0 / tau_c)
    v_inf = 1 + 2 * float(np.sum(rk_exact(C, s, a ** np.arange(1, 200_000))))
    assert v_inf == pytest.approx(2.2192, rel=1e-4)
    asymptotic = 2 * float(norm.cdf(-norm.isf(0.025) / math.sqrt(v_inf)))
    assert asymptotic == pytest.approx(0.1883, abs=5e-4), \
        "the asymptotic power moved; notebook 01's plateau statement must be redone"
    assert asymptotic < 0.25, "the count-only test must NOT approach certainty"

    text = _plain(_nb_text(NB01)).lower()
    # The correct wording is a NEGATION of the false claim, so the negated forms are removed
    # before scanning; a blanket ban would flag the very sentence that fixes the error.
    scan = text
    for negated in ("it does not imply that one total count becomes decisive as the record grows.",
                    "it does not mean one total count eventually becomes decisive."):
        scan = scan.replace(negated, "")
    for phrase in ("gets there eventually", "becomes decisive as the record grows",
                   "eventually becomes decisive"):
        assert phrase not in scan, \
            f"notebook 01 implies the count test eventually wins ({phrase!r}); it plateaus"
    assert "does not imply that one total count becomes decisive" in text, \
        "notebook 01 must say explicitly that nonzero power is not eventual certainty"
    assert "18.83" in text, "notebook 01 does not state the asymptotic power"


def test_the_monte_carlo_power_reports_its_standard_error():
    text = _plain(_nb_text(NB01)).lower()
    assert "pp" in text and "se" in text or "+- " in text, \
        "the Monte-Carlo power estimate must carry its standard error"


def test_the_variance_inflation_is_one_plus_the_spectral_perturbation():
    """V_inf = 1 + delta(0), tying the tutorial's overdispersion to the project's own
    validity criterion. If this identity ever fails, one of the two is defined wrongly."""
    from sid_lib import rk_exact
    C, s, tau_c = 0.4, 0.5, 20.0
    a = math.exp(-1.0 / tau_c)
    two_sum_rk = 2 * float(np.sum(rk_exact(C, s, a ** np.arange(1, 200_000))))
    assert two_sum_rk == pytest.approx(1.2192, rel=1e-4), "delta(0) moved"
    assert 1 + two_sum_rk == pytest.approx(2.2192, rel=1e-4)


def test_public_prose_scopes_the_symmetric_model_and_B_and_G():
    body = _plain(_docs("where-we-are.md"))
    assert "symmetric, zero-mean model studied here" in body, \
        "the half-average statement must be scoped to the symmetric model"
    assert "provenance-critical" in body, "G is not housekeeping"
    assert "not a guarantee" in body or "not expected to move" in body, \
        "F must not be promised to disturb nothing"
    gap = body.split("Generality across operating points.")[1].split("---")[0]
    assert "parity regime" in gap and "not a demonstration of generality" in gap, \
        "B's scope must be stated as one further point in the same regime"
