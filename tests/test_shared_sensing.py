"""Shared tutorial/research kernels retain their physical and archival meaning."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from numpy.polynomial.hermite import hermgauss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
from sid_lib import I_ext_exact, I_mid_gp, ramsey_probability, ramsey_mean
from sid_identifiability import (TAU_OVER_T2, class_a_margin, dephased_probability,
                                 information_at, s2_of)

# Independent relative budget for the res9 grid, not the driver's absolute res7A budget.
# Review measurements (14 Sept 2026): largest relative deviations were 0 on the archive
# stack (Python 3.9.7 / SciPy 1.10), 6.6e-10 on SciPy 1.15.2 and 6.3e-9 on SciPy 1.17.1.
# This leaves about 10x headroom over the largest observed deviation. See labbook pass 23.
RES9_RELATIVE_TOL = 6e-8


@pytest.mark.parametrize("C,s", [(0.4, 0.5), (0.5, 0.3), (0.9, 1.0)])
def test_marginal_readout_matches_gaussian_quadrature(C, s):
    """Average the actual conditional link, independently of its analytic Gaussian mean."""
    nodes, weights = hermgauss(64)
    angles = np.linspace(0, 2*np.pi, 17)
    averaged = (ramsey_probability(C, angles[:, None], np.sqrt(2)*s*nodes)
                @ weights / np.sqrt(np.pi))
    np.testing.assert_allclose(averaged, ramsey_mean(C, s, angles), atol=2e-15, rtol=0)
    assert I_ext_exact(C, s) > 0


def test_extracted_comparator_retains_archived_rate_check():
    archive = json.loads((ROOT / "analysis/outputs/res3_comparator.json").read_text())
    check = archive["rate_check"]
    fresh = [I_mid_gp(check["C"], check["s"], tc) for tc in check["tcc"]]
    np.testing.assert_allclose(fresh, check["gp_closed_form"], rtol=1e-10, atol=1e-15)


E_ROWS = json.loads((ROOT / "analysis/outputs/res9_identifiability_T2.json").read_text())["rows"]


@pytest.mark.parametrize("archived", E_ROWS,
                         ids=lambda r: f"C{r['C_0']}-eta{r['eta_0']}-v{r['tau_c_over_T2']}")
def test_extracted_identifiability_recomputes_the_archived_grid(archived):
    fresh = information_at(archived["C_0"], archived["eta_0"], archived["tau_c_over_T2"])
    for field in ("I_unc", "I_A", "I_B", "I_ref"):
        if archived[field] == 0:
            assert fresh[field] == 0  # never turn non-identifiability into a small positive rate
        else:
            # An absolute allowance could swallow the smallest class-B values entirely.
            assert fresh[field] == pytest.approx(archived[field], rel=RES9_RELATIVE_TOL, abs=0)
    assert fresh["class_A_points_passing"] == archived["class_A_points_passing"]
    assert [c["kind"] for c in fresh["optimizer"]["starts"]] == [
        "named", "named", "named", "grid-polish", "grid-raw"]


def test_class_a_separation_guard_agrees_with_probability_interval_overlap():
    """Check the exponent-space guard against the two probability intervals it describes."""
    C0, eta = 0.4, 0.02
    for v in (0.05, 0.2, 1.0):
        variance = np.array([s2_of(u, v) for u in TAU_OVER_T2])
        signal_low = dephased_probability(C0, TAU_OVER_T2, gamma=1-eta,
                                         phase_variance=variance)
        null_high = dephased_probability(C0, TAU_OVER_T2, gamma=1+eta)
        np.testing.assert_array_equal(class_a_margin(TAU_OVER_T2, variance, eta) > 0,
                                      signal_low > null_high)
