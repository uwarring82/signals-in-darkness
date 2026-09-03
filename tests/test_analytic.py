import math, sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis", "lib"))
from sid_lib import DB, I_ext_exact, I_ext_lo, rk_exact, S2_point, I_mid_lo

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
