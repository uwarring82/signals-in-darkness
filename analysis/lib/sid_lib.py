import os
"""Signals in Darkness v1.0 -- core numerical execution.

Sections
  A  extremum channel: exact Bernoulli divergence vs leading order
  B  mid-fringe channel: exact lag correlation, 1/2 sum r_k^2 vs exact HMM rate
  C  endpoint lemma: exact information rate vs Ramsey phase theta
  D  filtered-OU corollary: closed-form a_k vs numerical integration
  E  regime map (C, tau_c/c): analytic crossover, validity overlays, tau-optimised map
  F  oracle CUSUM delay vs log(gamma)/I at both operating points
"""
import numpy as np, math, json, time
from scipy.integrate import dblquad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, SEA, SIG, STONE, PARCH = "#1a1a1a", "#2c5f7c", "#c0392b", "#6b6b6b", "#f5f0e8"
plt.rcParams.update({"font.family": "serif", "axes.edgecolor": INK, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")



# ---------- helpers ----------
def DB(p, q):
    return p*np.log(p/q) + (1-p)*np.log((1-p)/(1-q))

def I_ext_exact(C, s):
    return DB((1-C*np.exp(-s*s/2))/2, (1-C)/2)

def I_ext_lo(C, s):
    return C**2*s**4/(8*(1-C**2))

def rk_exact(C, s, a):
    # theta = pi/2: P(Y=1|eps)=1/2(1 - C sin eps); Corr = C^2 E[sin sin]; Var=1/4
    return 0.5*C**2*(np.exp(-s*s*(1-a)) - np.exp(-s*s*(1+a)))

def S2_point(tc_over_c):
    return 1.0/np.expm1(2.0/tc_over_c)

def I_mid_strict(C, s, S2):
    """Strict O(s^4) mid-fringe asymptote: 1/2 Cbar^4 s^4 Sum a_k^2.

    This is NOT the card's leading-order rate. cards/v1.1-frozen.md:235 and :292 retain
    the slope-loss resummation e^{-2s^2}; see I_mid_slope. The two agree through strict
    O(s^4) and diverge above it -- by 19.7 % at s = 0.3 and 64.9 % at s = 0.5 -- so a
    result that attributes a number to the card formula must call I_mid_slope. Split out
    of the former ambiguous I_mid_lo on 7 Sept 2026; see note 13 and note 14.
    """
    return 0.5*C**4*s**4*S2

def I_mid_slope(C, s, S2):
    """The card's leading-order mid-fringe rate: 1/2 Cbar^4 s^4 e^{-2s^2} Sum a_k^2."""
    return I_mid_strict(C, s, S2)*np.exp(-2.0*s*s)

def I_lo_theta_strict(C, s, S2, theta):
    """Endpoint-lemma information at readout angle theta, strict O(s^4) B term."""
    x = np.cos(theta)**2
    A = C**2*s**4/8; B = I_mid_strict(C, s, S2)
    return A*x/(1-C**2*x) + B*(1-x)**2/(1-C**2*x)**2

def I_lo_theta_slope(C, s, S2, theta):
    """As I_lo_theta_strict, with the card's resummed B = 1/2 Cbar^4 s^4 e^{-2s^2} Sum a_k^2.

    The interior-minimum-versus-endpoint conclusion of C06 is unchanged by the choice
    (checked at (0.9,0.3,5), (0.4,0.5,20) and (0.4,0.5,1)); only the minimum's location
    moves, e.g. 0.3416 -> 0.3954 rad at C=0.9, s=0.3, tau_c/c=5.
    """
    x = np.cos(theta)**2
    A = C**2*s**4/8; B = I_mid_slope(C, s, S2)
    return A*x/(1-C**2*x) + B*(1-x)**2/(1-C**2*x)**2

# ---------- exact latent-AR(1) binary HMM ----------
def make_hmm(C, s, theta, a, M=121, L=5.0):
    g = np.linspace(-L*s, L*s, M)
    sd = s*np.sqrt(1-a*a)
    T = np.exp(-(g[None, :]-a*g[:, None])**2/(2*sd*sd)); T /= T.sum(1, keepdims=True)
    e1 = 0.5*(1+C*np.cos(theta+g)); e0 = 1-e1
    prior = np.exp(-g**2/(2*s*s)); prior /= prior.sum()
    return g, T, e1, e0, prior

def simulate(C, s, theta, a, N, rng):
    sd = s*np.sqrt(1-a*a)
    eta = rng.normal(0, 1, N); eps = np.empty(N); x = rng.normal(0, s)
    for n in range(N):
        x = a*x + sd*eta[n]; eps[n] = x
    p = 0.5*(1+C*np.cos(theta+eps))
    return (rng.random(N) < p).astype(np.int8)

def hmm_rate(C, s, theta, a, N=100_000, seed=0, M=121):
    """Exact (grid) KL rate E_1[log P1(y_n|past) - log P0(y_n)] for the latent AR(1) binary process."""
    r = np.random.default_rng(seed)
    g, T, e1, e0, prior = make_hmm(C, s, theta, a, M)
    y = simulate(C, s, theta, a, N, r)
    p0 = 0.5*(1+C*np.cos(theta))
    alpha = prior.copy(); ll1 = 0.0
    for n in range(N):
        alpha = alpha @ T
        alpha *= (e1 if y[n] else e0)
        z = alpha.sum(); ll1 += math.log(z); alpha /= z
    ll0 = np.sum(y*np.log(p0) + (1-y)*np.log(1-p0))
    return (ll1-ll0)/N

