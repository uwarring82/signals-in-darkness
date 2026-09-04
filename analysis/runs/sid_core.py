import os
# Producers write into analysis/reproduction/ (git-ignored), never into the published
# archive. REF_OUTD / REF_FIG are the archive, opened read-only for comparison.
REF_OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction")
os.makedirs(OUTD, exist_ok=True)
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
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import numpy as np, math, json, time
import sid_repro
from scipy.integrate import dblquad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, SEA, SIG, STONE, PARCH = "#1a1a1a", "#2c5f7c", "#c0392b", "#6b6b6b", "#f5f0e8"
plt.rcParams.update({"font.family": "serif", "axes.edgecolor": INK, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
REF_FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction", "figures")
os.makedirs(OUT, exist_ok=True)


def savefig_checked(fig, name, min_bytes=10_000):
    """Write a figure and assert it actually landed (rule 6).

    A figure writer that reports success without checking is how a rebuild can silently
    produce nothing, or a truncated file, and still print "rebuilt".
    """
    path = os.path.join(OUT, name)
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(path)
    assert os.path.exists(path), f"postcondition: {name} was not written"
    size = os.path.getsize(path)
    assert size >= min_bytes, f"postcondition: {name} is {size} bytes, expected >= {min_bytes}"
    print(f"   wrote {name} ({size//1024} kB)")
    return path

rng = np.random.default_rng(1)
report = {}

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

def I_mid_lo(C, s, S2):
    return 0.5*C**4*s**4*S2

def I_lo_theta(C, s, S2, theta):
    x = np.cos(theta)**2
    A = C**2*s**4/8; B = 0.5*C**4*s**4*S2
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

# ---------- A ----------
print("== A: extremum channel exact vs leading order ==")
A_rows = []
for C in [0.4, 0.5, 0.7, 0.9, 0.99]:
    for s in [0.1, 0.3, 0.5, 1.0]:
        ex, lo = I_ext_exact(C, s), I_ext_lo(C, s)
        val = s*s*C/(1-C*C)
        A_rows.append((C, s, ex, lo, lo/ex, val))
        print(f"C={C:5.2f} s={s:4.2f}  I_exact={ex:.3e}  I_lo={lo:.3e}  lo/exact={lo/ex:6.3f}  s^2 C/(1-C^2)={val:.3f}")
report["A"] = A_rows

# ---------- A2: contrast dependence of the expansion accuracy ----------
# Deterministic, no seed. Card v1.1 and note 01 §1 stated the leading-order extremum
# expansion as accurate "within 6 % for q = s^2 C/(1-C^2) <= 0.06" and within 20 % up to
# q = 0.17, as if q alone fixed the relative error. It does not: the first omitted term
# carries its own contrast dependence,
#     I_exact/I_LO = 1 - k s^2 + O(s^4),   k = 1/2 + C^2/(3(1-C^2)),
# so the accuracy at fixed q degrades as the contrast falls. The A grid above starts at
# C = 0.5, which is why the original check did not see it. Withdrawn as C01; see
# notes/2026-09-03-note-01a-errata.md.
from scipy.optimize import brentq

print("\n== A2: contrast dependence of the leading-order accuracy bound ==")


def _s_of_q(C, q):
    return math.sqrt(q*(1-C*C)/C)


def _rel_err(C, q):
    s = _s_of_q(C, q)
    return I_ext_lo(C, s)/I_ext_exact(C, s) - 1


A2_rows = []
# Bracket floor: below q ~ 1e-4 the exact divergence is O(1e-13) and the Bernoulli
# difference cancels in double precision, so _rel_err loses its sign there. The
# root is far above the floor in every row; the postcondition below checks it.
Q_LO, Q_HI = 1e-4, 1.0
for C in [0.3, 0.4, 0.5, 0.7, 0.9]:
    e06, e17 = _rel_err(C, 0.06), _rel_err(C, 0.17)
    q06 = brentq(lambda q: _rel_err(C, q) - 0.06, Q_LO, Q_HI)
    q20 = brentq(lambda q: _rel_err(C, q) - 0.20, Q_LO, Q_HI)
    assert abs(_rel_err(C, q06) - 0.06) < 1e-9 and abs(_rel_err(C, q20) - 0.20) < 1e-9, \
        f"A2 root-finding postcondition failed at C={C}"
    assert Q_LO < q06 < q20 < Q_HI, f"A2 roots outside the bracket at C={C}"
    k = 0.5 + C*C/(3*(1-C*C))
    A2_rows.append((C, e06, e17, q06, q20, k))
    print(f"C={C:4.2f}  err at q=0.06: {100*e06:5.1f}%   err at q=0.17: {100*e17:5.1f}%   "
          f"q for 6%: {q06:.4f}   q for 20%: {q20:.4f}   k={k:.4f}")
report["A2"] = A2_rows

# ---------- B ----------
print("\n== B: mid-fringe channel: 1/2 sum r_k^2 (exact r_k) vs exact HMM rate ==")
B_rows = []
cases = [(0.4, 0.5, 20.0), (0.4, 0.5, 5.0), (0.4, 0.5, 1.0), (0.9, 0.3, 5.0), (0.4, 1.0, 20.0), (0.9, 0.6, 20.0)]
for C, s, tcc in cases:
    a = math.exp(-1/tcc)
    ks = np.arange(1, 400); ak = a**ks
    S2 = S2_point(tcc)
    Imid_lo = I_mid_lo(C, s, S2)
    Imid_rk = 0.5*np.sum(rk_exact(C, s, ak)**2)
    t0 = time.time(); Imid_hmm = hmm_rate(C, s, math.pi/2, a, N=100_000, seed=1); dt = time.time()-t0
    pert = C**4*s**4*S2
    Iext = I_ext_exact(C, s)
    B_rows.append((C, s, tcc, S2, Imid_lo, Imid_rk, Imid_hmm, pert, Iext))
    print(f"C={C} s={s} tc/c={tcc:5.1f} S2={S2:6.2f}  lo={Imid_lo:.3e}  half-sum-rk^2(exact rk)={Imid_rk:.3e}  HMM={Imid_hmm:.3e}  "
          f"pert-param={pert:.3f}  I_ext_exact={Iext:.3e}  [{dt:.1f}s]")
report["B"] = B_rows

# ---------- C ----------
print("\n== C: endpoint lemma: exact HMM rate vs theta ==")
thetas = np.array([0, 15, 30, 45, 60, 75, 90])*math.pi/180
C_rows = {}
for C, s, tcc in [(0.4, 0.5, 20.0), (0.4, 0.5, 1.0), (0.9, 0.3, 5.0)]:
    a = math.exp(-1/tcc); S2 = S2_point(tcc)
    ex = []; lo = []
    for th in thetas:
        ex.append(hmm_rate(C, s, th, a, N=60_000, seed=2)); lo.append(I_lo_theta(C, s, S2, th))
    C_rows[f"{C},{s},{tcc}"] = (thetas.tolist(), ex, lo)
    print(f"C={C} s={s} tc/c={tcc}:")
    for th, e_, l_ in zip(thetas, ex, lo):
        print(f"   theta={math.degrees(th):4.0f}  exact={e_:.3e}  lo={l_:.3e}")
    i_ex = int(np.argmax(ex)); print(f"   exact argmax theta = {math.degrees(thetas[i_ex]):.0f} deg; endpoints: {ex[0]:.3e} (0), {ex[-1]:.3e} (90)")
report["C"] = C_rows

# ---------- D ----------
print("\n== D: filtered-OU corollary ==")
def F_closed(u):
    return (math.cosh(u)-1)/(u-1+math.exp(-u))
def s2_closed(tau, tc):  # per (g sigma_x)^2
    return 2*(tc*tau - tc*tc*(1-math.exp(-tau/tc)))
def cov_num(tau, tc, kc):
    f = lambda t2, t1: math.exp(-abs(kc+t2-t1)/tc)
    v, _ = dblquad(f, 0, tau, 0, tau)
    return v
D_rows = []
for tau, tc, c in [(0.1, 1.0, 0.3), (1.0, 1.0, 1.5), (3.0, 1.0, 3.5), (0.5, 5.0, 1.0)]:
    u = tau/tc
    s2c = s2_closed(tau, tc); s2n = cov_num(tau, tc, 0.0)
    a1c = math.exp(-c/tc)*F_closed(u); a1n = cov_num(tau, tc, c)/s2n
    D_rows.append((tau, tc, c, s2c, s2n, a1c, a1n))
    print(f"tau={tau} tc={tc} c={c}: s^2 closed={s2c:.5f} num={s2n:.5f} | a_1 closed={a1c:.5f} num={a1n:.5f}")
report["D"] = D_rows

# ---------- E ----------
print("\n== E: regime map ==")
def crossover_tcc(C):
    return 2.0/np.log1p(4*C*C*(1-C*C))
for C in [0.2, 0.4, 0.5, 0.7, 1/math.sqrt(2), 0.9, 0.99]:
    print(f"C={C:5.3f}: crossover tau_c/c = {crossover_tcc(C):6.2f} shots  (sum a_k^2 threshold {1/(4*C*C*(1-C*C)):6.2f})")

Cs = np.linspace(0.05, 0.995, 400); tccs = np.logspace(-0.7, 2.3, 400)
CC, TT = np.meshgrid(Cs, tccs)
S2g = 1.0/np.expm1(2.0/TT)
s_ref = 0.5
Iext_g = CC**2/(8*(1-CC**2)); Imid_g = 0.5*CC**4*S2g   # per s^4
win_mid = Imid_g > Iext_g
# ---- validity overlays ----
# Both overlays drawn before 4 Sept 2026 were wrong, and both flattered the map.
#
# Mid-fringe: the figure contoured Cbar^4 s^4 Sigma a_k^2 = 0.3, the v1.0 box that
# ledgers/status.yaml records as WITHDRAWN under C03 and that note 01 section 2b calls "the
# wrong parameter". Card v1.1 specifies delta(0) = 2 Sigma r_k with the exact
# r_k = Cbar^2 e^{-s^2} sinh(s^2 a^k). At Cbar = 0.4, s = 0.5 the withdrawn box put the
# boundary at tau_c/c = 376; delta(0) = 0.3 puts it at 5.29, i.e. 70x nearer, and only just
# above the crossover at 4.65 that the same figure draws.
#
# Extremum: the figure contoured s^2 Cbar/(1-Cbar^2) = 0.3, the uniform bound withdrawn as
# C01 (see notes/2026-09-03-note-01a-errata.md). q does not fix the relative error without a
# contrast range, so the exact error is contoured instead, at declared levels.
DELTA0_LEVEL = 0.3
EXT_ERROR_LEVELS = (0.20, 0.50)


def delta0(C, tcc, s=s_ref, M=8):
    """Spectral perturbation delta(0) = 2 sum_{k>=1} r_k for the exact mid-fringe r_k.

    sum_k sinh(x a^k) = sum_m x^(2m+1)/(2m+1)! * a^(2m+1)/(1 - a^(2m+1)), x = s^2, so the
    sum over lags closes in M terms instead of being truncated. Verified against direct
    summation to 2.6e-16 relative over C in [0.2, 0.99], tau_c/c in [0.2, 200].
    """
    a = np.exp(-1.0/np.asarray(tcc, float))
    x = s*s
    tot = np.zeros_like(a, dtype=float)
    for m in range(M):
        p = 2*m + 1
        tot += x**p/math.factorial(p) * a**p/(1 - a**p)
    return 2*np.asarray(C, float)**2*math.exp(-x)*tot


delta0_g = delta0(CC, TT)
ext_err = I_ext_lo(Cs, s_ref)/I_ext_exact(Cs, s_ref) - 1      # exact, not a bound
ext_err_min = float(ext_err.min())
ext_crossings = {}
for lv in EXT_ERROR_LEVELS:
    if ext_err_min > lv:
        ext_crossings[f'{lv}'] = None          # level never attained on this axis
    else:
        ext_crossings[f'{lv}'] = float(brentq(
            lambda c: float(I_ext_lo(c, s_ref)/I_ext_exact(c, s_ref) - 1 - lv), Cs[0], Cs[-1]))
print(f"   extremum leading-order error at s={s_ref}: {100*ext_err_min:.1f} % at Cbar={Cs[0]:.2f} "
      f"rising to {100*float(ext_err[-1]):.0f} % at Cbar={Cs[-1]:.3f}")
for lv, c in ext_crossings.items():
    print(f"     error {float(lv):.0%}: " + ("not attained anywhere on this map" if c is None
                                             else f"at Cbar = {c:.4f}"))

fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=150, facecolor=PARCH)
ax.set_facecolor(PARCH)
ax.contourf(CC, TT, win_mid.astype(float), levels=[-0.5, 0.5, 1.5], colors=[PARCH, "#cfdde6"])
ax.plot(Cs, crossover_tcc(Cs), color=SEA, lw=2, label="crossover  $\\Sigma a_k^2=1/[4\\bar C^2(1-\\bar C^2)]$")
ax.contour(CC, TT, delta0_g, levels=[DELTA0_LEVEL], colors=[SIG], linestyles="--", linewidths=1.4)
for lv, c in ext_crossings.items():
    if c is not None:
        ax.axvline(c, color=SIG, lw=1.2, ls=":")
        ax.text(c+0.006, 0.3, f"extremum LO error {float(lv):.0%}", color=SIG, fontsize=7,
                rotation=90, va="bottom")
ax.axvline(0.5, color=STONE, lw=1.2); ax.axvline(0.405, color=STONE, lw=1.2, ls="-.")
ax.text(0.505, 60, "parity ceiling $\\bar C=1/2$", color=STONE, fontsize=8, rotation=90, va="top")
ax.text(0.41, 60, "realistic parity $\\bar C\\simeq0.4$", color=STONE, fontsize=8, rotation=90, va="top")
ax.text(0.09, 120, "mid-fringe (correlation) wins", color=SEA, fontsize=10)
ax.text(0.24, 0.35, "extremum (contrast-loss) wins", color=INK, fontsize=10)
ax.plot([], [], color=SIG, ls="--", label=f"mid-fringe validity: $\\delta(0)=2\\Sigma r_k={DELTA0_LEVEL}$ ($s={s_ref}$, card v1.1)")
ax.plot([], [], color=SIG, ls=":", label=f"extremum: exact LO error (min {100*ext_err_min:.0f}% on this map)")
ax.set_yscale("log"); ax.set_xlabel("effective contrast $\\bar C$"); ax.set_ylabel("correlation time in shot cycles  $\\tau_c/c$")
ax.set_title("Operating-point regime map (leading order, point-sampled OU)\n"
             "the crossover is drawn beyond mid-fringe validity wherever it lies above the dashed curve",
             fontsize=10)
ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
fig.tight_layout(); savefig_checked(fig, "sid_regime_map.png"); plt.close(fig)

# ---- store the grids the figure is drawn from (work-plan step 4) ----
# Only boundaries that fall inside the plotted range are stored; the count of contrasts with
# no boundary in range is recorded rather than silently dropped.
boundary, omitted = [], 0
for C in Cs:
    f = lambda t: float(delta0(C, t)) - DELTA0_LEVEL
    if f(tccs[0])*f(tccs[-1]) < 0:
        boundary.append([float(C), float(brentq(f, tccs[0], tccs[-1]))])
    else:
        omitted += 1
report["E"] = {
    "s_ref": s_ref,
    "C_grid": Cs.tolist(),
    "tcc_grid": tccs.tolist(),
    "crossover_tcc": crossover_tcc(Cs).tolist(),
    "delta0_level": DELTA0_LEVEL,
    "delta0_boundary": boundary,
    "delta0_boundary_omitted": omitted,
    "ext_rel_error": ext_err.tolist(),
    "ext_error_crossings": ext_crossings,
    "ext_error_min": ext_err_min,
}
print(f"   stored E: {len(Cs)} contrasts, delta(0)={DELTA0_LEVEL} boundary at {len(boundary)} of them "
      f"({omitted} outside the plotted tau_c/c range)")

# tau-optimised map (leading order; amplitude cancels). Units: t_dead = 1, T2 = 10.
T2, td = 10.0, 1.0
C0s = np.linspace(0.05, 0.995, 120); tcs = np.logspace(-1, 2.5, 120)
taus = np.logspace(-2, np.log10(3*T2), 300)
win = np.zeros((len(tcs), len(C0s))); tau_opt = np.zeros_like(win); ratio = np.zeros_like(win)
for i, tc in enumerate(tcs):
    u = taus/tc; c = taus+td
    s2 = 2*(tc*taus - tc*tc*(1-np.exp(-u)))
    F = (np.cosh(u)-1)/(u-1+np.exp(-u))
    S2 = F**2/np.expm1(2*c/tc)
    for j, C0 in enumerate(C0s):
        Ct = C0*np.exp(-taus/T2)
        Rext = Ct**2*s2**2/(8*(1-Ct**2))/c
        Rmid = 0.5*Ct**4*s2**2*S2/c
        ie, im = np.argmax(Rext), np.argmax(Rmid)
        win[i, j] = 1.0 if Rmid[im] > Rext[ie] else 0.0
        tau_opt[i, j] = taus[im] if win[i, j] else taus[ie]
        ratio[i, j] = Rmid[im]/Rext[ie]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, facecolor=PARCH)
for a_ in ax: a_.set_facecolor(PARCH)
X, Y = np.meshgrid(C0s, tcs)
ax[0].contourf(X, Y, win, levels=[-0.5, 0.5, 1.5], colors=[PARCH, "#cfdde6"])
cs = ax[0].contour(X, Y, np.log10(ratio), levels=[-2, -1, 0, 1, 2], colors=[SEA], linewidths=1)
ax[0].clabel(cs, fmt="%d", fontsize=7)
ax[0].axvline(0.5, color=STONE, lw=1); ax[0].axvline(0.405, color=STONE, lw=1, ls="-.")
ax[0].set_yscale("log"); ax[0].set_xlabel("$\\bar C_0$ (zero-$\\tau$ contrast)"); ax[0].set_ylabel("$\\tau_c / t_{\\rm dead}$")
ax[0].set_title("$\\tau$-optimised winner; contours: $\\log_{10}(R_{\\rm mid}/R_{\\rm ext})$", fontsize=10)
ax[0].text(0.1, 100, "mid-fringe", color=SEA); ax[0].text(0.6, 0.15, "extremum", color=INK)
im = ax[1].pcolormesh(X, Y, np.log10(tau_opt/T2), cmap="cividis", shading="auto")
ax[1].set_yscale("log"); ax[1].set_xlabel("$\\bar C_0$"); ax[1].set_title("optimal $\\log_{10}(\\tau/T_2)$ of winning channel", fontsize=10)
fig.colorbar(im, ax=ax[1])
fig.suptitle(f"$\\tau$-optimised regime map, $T_2 = 10\\,t_{{\\rm dead}}$, exponential contrast, leading order (amplitude-free)", fontsize=10)
fig.tight_layout(); savefig_checked(fig, "sid_regime_map_tau_optimised.png"); plt.close(fig)
print("tau-optimised map: fraction of grid where mid-fringe wins =", win.mean().round(3))
print("tau_opt/T2 range (winner):", (tau_opt/T2).min().round(3), (tau_opt/T2).max().round(3))

# ---------- F ----------
print("\n== F: oracle CUSUM delay vs log(gamma)/I ==")
def cusum_ext(C, s, a, h, runs, seed):
    r = np.random.default_rng(seed)
    p0 = (1-C)/2; p1 = (1-C*math.exp(-s*s/2))/2
    l1, l0 = math.log(p1/p0), math.log((1-p1)/(1-p0))
    out = []
    for _ in range(runs):
        y = simulate(C, s, math.pi, a, 20*int(h/max(I_ext_exact(C, s), 1e-9)), r)
        W = 0.0
        for n, yn in enumerate(y):
            W = max(0.0, W + (l1 if yn else l0))
            if W >= h: out.append(n+1); break
    return np.array(out)

def cusum_mid(C, s, a, h, runs, seed, M=121):
    r = np.random.default_rng(seed)
    g, T, e1, e0, prior = make_hmm(C, s, math.pi/2, a, M)
    out = []
    Nmax = 12*int(h/max(hmm_rate_cache.get((C, s, a), 1e-3), 1e-9))
    for _ in range(runs):
        y = simulate(C, s, math.pi/2, a, Nmax, r)
        W = 0.0; alpha = prior.copy()
        for n, yn in enumerate(y):
            alpha = alpha @ T
            alpha *= (e1 if yn else e0)
            z = alpha.sum(); alpha /= z
            W = W + math.log(z) - math.log(0.5)
            if W <= 0.0:
                W = 0.0; alpha = prior.copy()     # reset filter with the statistic
            if W >= h: out.append(n+1); break
    return np.array(out)

hmm_rate_cache = {}
gamma = 1e3; h = math.log(gamma)


def _mean_se(sample, label):
    """Mean and standard error of a delay sample.

    Returns (None, None) when no run reached the threshold within the cap: the delay is
    then undefined, not a number, and is stored as JSON null. Any OTHER non-finite value
    is a calculation error and stops the run rather than being written to the archive.
    """
    if len(sample) == 0:
        return None, None
    m = float(sample.mean()); se = float(sample.std()/math.sqrt(len(sample)))
    if not (math.isfinite(m) and math.isfinite(se)):
        raise ValueError(f"non-finite {label} delay statistic from {len(sample)} completed runs")
    return m, se


def _fmt(v):
    return "undefined" if v is None else f"{v:.0f}"


F_rows = []
for C, s, tcc in [(0.4, 0.5, 20.0), (0.4, 0.5, 1.0)]:
    a = math.exp(-1/tcc)
    Iext = I_ext_exact(C, s)
    Imid = [row[6] for row in B_rows if row[0] == C and row[1] == s and row[2] == tcc][0]
    hmm_rate_cache[(C, s, a)] = Imid
    de = cusum_ext(C, s, a, h, 60, 11); dm = cusum_mid(C, s, a, h, 40, 12)
    de_m, de_se = _mean_se(de, "extremum"); dm_m, dm_se = _mean_se(dm, "mid-fringe")
    F_rows.append((C, s, tcc, Iext, Imid, de_m, de_se, h/Iext, dm_m, dm_se, h/Imid))
    print(f"C={C} s={s} tc/c={tcc}: extremum delay={_fmt(de_m)}+-{_fmt(de_se)} (h/I={h/Iext:.0f}) | "
          f"mid-fringe delay={_fmt(dm_m)}+-{_fmt(dm_se)} (h/I={h/Imid:.0f})  [runs {len(de)},{len(dm)}]")
report["F"] = F_rows

# endpoint figure
fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150, facecolor=PARCH); ax.set_facecolor(PARCH)
for (key, (th, ex, lo)), col in zip(C_rows.items(), [SEA, SIG, INK]):
    C, s, tcc = key.split(",")
    ax.plot(np.degrees(th), ex, "o-", color=col, label=f"exact HMM: $\\bar C$={C}, s={s}, $\\tau_c/c$={tcc}")
    ax.plot(np.degrees(th), lo, "--", color=col, alpha=0.6)
ax.set_xlabel("Ramsey phase $\\theta$ (deg; 0 = extremum, 90 = mid-fringe)"); ax.set_ylabel("information per shot (nats)")
ax.set_yscale("log"); ax.legend(fontsize=7.5); ax.set_title("Endpoint lemma check: exact (solid) vs leading order (dashed)", fontsize=10)
fig.tight_layout(); savefig_checked(fig, "sid_endpoint_check.png"); plt.close(fig)

# Postcondition (rule 6): the archive must be valid JSON. allow_nan=False refuses to
# serialise NaN/Infinity, so any non-finite value that is NOT a deliberate null stops the
# run instead of writing a file that conforming parsers reject. Deliberate "undefined"
# values are None above and serialise as null, matching the convention SCHEMA.md already
# documents for res2_partial.json.
sid_repro.write_json(os.path.join(OUTD, "res1_core.json"), report,
                     default=float, indent=1, allow_nan=False)
print("\ndone")
