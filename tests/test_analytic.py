import math, sys, os
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis", "lib"))
from sid_lib import DB, I_ext_exact, I_ext_lo, rk_exact, S2_point, I_mid_strict, I_mid_slope

def test_extremum_small_s_expansion_independent_expectation():
    # independent derivation: Delta p = C(1-e^{-s^2/2})/2, D ~ Delta p^2 / (2 p0 (1-p0))
    C, s = 0.4, 0.1
    dp = C*(1-math.exp(-s*s/2))/2; p0 = (1-C)/2
    approx = dp*dp/(2*p0*(1-p0))
    assert abs(I_ext_exact(C, s)/approx - 1) < 0.02
    assert abs(I_ext_lo(C, s)/(C*C*s**4/(8*(1-C*C))) - 1) < 1e-12

def test_lag_correlation_closed_form_vs_bivariate_gaussian_quadrature():
    C, s, a = 0.4, 0.5, 0.9
    # E[sin X sin Y] for bivariate Gaussian via Monte Carlo-free quadrature
    n = 401; x = np.linspace(-5*s, 5*s, n); X, Y = np.meshgrid(x, x)
    cov = np.array([[s*s, a*s*s], [a*s*s, s*s]]); inv = np.linalg.inv(cov)
    pdf = np.exp(-0.5*(inv[0,0]*X*X + 2*inv[0,1]*X*Y + inv[1,1]*Y*Y)); pdf /= pdf.sum()
    E = np.sum(np.sin(X)*np.sin(Y)*pdf)
    assert abs(C*C*E - rk_exact(C, s, a)) < 2e-4
    assert abs(rk_exact(C, s, a) - C*C*math.exp(-s*s)*math.sinh(s*s*a)) < 1e-12

def test_crossover_threshold_values():
    for C, thr in [(0.4, 1.86), (0.5, 1.33), (0.7, 1.00), (0.9, 1.62), (0.99, 12.8)]:
        assert abs(1/(4*C*C*(1-C*C))/thr - 1) < 0.01
    # point-sampled OU: tau_c/c at crossover = 2/ln(1+4C^2(1-C^2)); minimum at C=1/sqrt(2)
    f = lambda C: 2/math.log1p(4*C*C*(1-C*C))
    assert abs(f(1/math.sqrt(2)) - 2/math.log(2)) < 1e-12
    assert f(0.4) > f(1/math.sqrt(2)) and f(0.99) > f(0.9)

def test_geometric_sum_boundary():
    # sum_{k>=1} e^{-2kc/tau_c} = 1/(e^{2c/tau_c}-1); check at and just beyond the C=0.4 crossover
    thr = 1/(4*0.16*0.84)
    for tcc, below in [(4.6, True), (4.7, False)]:
        assert (S2_point(tcc) < thr) == below

def test_endpoint_lemma_numerator_linear_and_positive_at_x1():
    C = 0.9; A = 1.0; B = 3.0
    num = lambda x: A*(1-C*C*x) - 2*B*(1-C*C)*(1-x)
    xs = np.linspace(0, 1, 11); v = num(xs)
    assert abs(np.polyfit(xs, v, 1)[0]*1 - (v[-1]-v[0])) < 1e-12   # linear
    assert num(1.0) > 0


def test_mid_fringe_strict_and_slope_agree_at_leading_order_and_diverge_above_it():
    """The two forms this file previously imported under one unused name. They agree through
    strict O(s^4) -- so the ratio -> 1 as s -> 0 -- and differ by exactly e^{2s^2} elsewhere.
    A result that attributes its number to the card formula must use the slope form; see
    notes/2026-09-07-note-14-helper-split-and-BE-decisions.md."""
    C, S2 = 0.4, S2_point(20.0)
    for s in (1e-4, 0.1, 0.3, 0.5, 1.0):
        assert I_mid_strict(C, s, S2) / I_mid_slope(C, s, S2) == pytest.approx(math.exp(2*s*s), rel=1e-13)
    assert I_mid_strict(C, 1e-5, S2) / I_mid_slope(C, 1e-5, S2) == pytest.approx(1.0, abs=1e-9)
    # the divergence that made the split necessary, at the pilot amplitude
    assert I_mid_strict(C, 0.5, S2) / I_mid_slope(C, 0.5, S2) == pytest.approx(1.6487, rel=1e-4)


def test_mid_fringe_strict_matches_the_half_sum_of_exact_rk_as_s_goes_to_zero():
    """I_strict is the s -> 0 limit of the exact 1/2 sum r_k^2, which is what makes it the
    strict asymptote rather than an approximation with a missing factor."""
    C, tcc, s = 0.4, 20.0, 1e-3
    a = math.exp(-1/tcc); ak = a**np.arange(1, 20000)
    exact_half_sum = 0.5*np.sum(rk_exact(C, s, ak)**2)
    assert I_mid_strict(C, s, S2_point(tcc)) == pytest.approx(exact_half_sum, rel=1e-5)
