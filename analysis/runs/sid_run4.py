import os
import sys, math, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Producers write into analysis/reproduction/ (git-ignored), never into the published
# archive. REF_OUTD / REF_FIG are the archive, opened read-only for comparison.
REF_OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction")
os.makedirs(OUTD, exist_ok=True)
import numpy as np
from sid_lib import *
import matplotlib.pyplot as plt
REF_FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction", "figures")
os.makedirs(OUT, exist_ok=True)

# ---------- exact-r_k spectral rate via sinh series: r_k = C^2 e^{-s^2} sum_m x^{2m+1}/(2m+1)! (a^{2m+1})^k, x = s^2 A ----------
NF = 1024
W = np.pi*(np.arange(NF)+0.5)/NF          # omega in (0, pi); spectrum symmetric

def spectrum_series(C, s, A, a, M=6):
    """S(omega)-1 for r_k = C^2 e^{-s^2} sinh(s^2 A a^k), as a finite sum of geometric spectra."""
    x = s*s*A; pref = C*C*math.exp(-s*s)
    out = np.zeros_like(W)
    for m in range(M):
        rho = pref*x**(2*m+1)/math.factorial(2*m+1); am = a**(2*m+1)
        out += 2*rho*(am*np.cos(W)-am*am)/(1-2*am*np.cos(W)+am*am)
    return out

def gp_rate_series(C, s, A, a):
    d = spectrum_series(C, s, A, a)
    return 0.5*np.mean(d-np.log1p(d)), d.max()

def gp_rate_geomfit(C, s, A, a):
    r1 = C*C*math.exp(-s*s)*math.sinh(s*s*A*a)
    return gp_rate_geom(r1/a, a)

def gp_rate_geom(rho, a):
    alpha = 1+a*a-2*rho*a*a; beta = 2*a*(rho-1)
    if abs(beta) < 1e-14: return 0.0
    b = (-alpha+math.sqrt(alpha*alpha-beta*beta))/beta
    return -0.5*math.log(alpha/(1+b*b))

# sanity: series vs direct numeric sum with exact r_k (point sampling A=1)
print("== series spectrum vs direct exact-r_k sum ==")
for C, s, tcc in [(0.4, 0.5, 20.0), (0.4, 1.0, 20.0), (0.9, 0.6, 20.0)]:
    a = math.exp(-1/tcc); ks = np.arange(1, 6000); rk = rk_exact(C, s, a**ks)
    d_direct = 2*np.sum(rk[:, None]*np.cos(ks[:, None]*W[None, :]), axis=0)
    r_direct = 0.5*np.mean(d_direct-np.log1p(d_direct)); r_series, _ = gp_rate_series(C, s, 1.0, a)
    print(f"C={C} s={s} tc/c={tcc}: direct={r_direct:.4e} series={r_series:.4e} geomfit={gp_rate_geomfit(C, s, 1.0, a):.4e}")

# ---------- Check 2: geometric-fit vs exact-series over the full tau-optimised domain ----------
print("\n== Check 2: geometric-fit closed form vs exact-r_k spectral integral, full map, tau-optimised ==")
T2, td, gs = 10.0, 1.0, 0.05
C0s = np.linspace(0.05, 0.995, 60); tcs = np.logspace(-1, 3, 60); taus = np.logspace(-1.5, np.log10(3*T2), 120)
win_fit = np.zeros((len(tcs), len(C0s))); win_ser = np.zeros_like(win_fit)
relerr_at_winner = np.zeros_like(win_fit); relerr_max_over_tau = np.zeros_like(win_fit); delta0_at_winner = np.zeros_like(win_fit)
t0 = time.time()
for i, tc in enumerate(tcs):
    u = taus/tc; c = taus+td
    s2 = gs*gs*2*(tc*taus-tc*tc*(1-np.exp(-u))); F = (np.cosh(u)-1)/(u-1+np.exp(-u)); a = np.exp(-c/tc)
    for j, C0 in enumerate(C0s):
        Ct = C0*np.exp(-taus/T2); sv = np.sqrt(s2)
        Rext = np.array([I_ext_exact(Ct[k], sv[k]) for k in range(len(taus))])/c
        Rfit = np.array([gp_rate_geomfit(Ct[k], sv[k], F[k], a[k]) for k in range(len(taus))])/c
        ser = [gp_rate_series(Ct[k], sv[k], F[k], a[k]) for k in range(len(taus))]
        Rser = np.array([v[0] for v in ser])/c; d0 = np.array([v[1] for v in ser])
        ie = int(np.argmax(Rext)); kf = int(np.argmax(Rfit)); ks_ = int(np.argmax(Rser))
        win_fit[i, j] = Rfit[kf] > Rext[ie]; win_ser[i, j] = Rser[ks_] > Rext[ie]
        relerr_at_winner[i, j] = (Rfit[ks_]/Rser[ks_]-1) if Rser[ks_] > 1e-300 else 0.0
        good = Rser > max(1e-12*Rser.max(), 1e-300)
        relerr_max_over_tau[i, j] = np.max(np.abs(Rfit[good]/Rser[good]-1)) if good.any() else 0.0
        delta0_at_winner[i, j] = d0[ks_]
print(f"   [{time.time()-t0:.0f}s]  winner disagreement fraction = {np.mean(win_fit != win_ser):.4f}")
print(f"   geomfit/series - 1 at the mid-fringe-optimal tau: max |.| = {np.abs(relerr_at_winner).max():.4f}, "
      f"median |.| = {np.median(np.abs(relerr_at_winner)):.4f}")
print(f"   max over all tau in domain: {relerr_max_over_tau.max():.4f}")
print(f"   delta(0) at mid-fringe optimum: range {delta0_at_winner.min():.3f} .. {delta0_at_winner.max():.3f}; "
      f"fraction of grid with delta(0) > 1: {np.mean(delta0_at_winner > 1):.3f}")
# where is the error largest
ii, jj = np.unravel_index(np.argmax(np.abs(relerr_at_winner)), relerr_at_winner.shape)
print(f"   largest error at C0={C0s[jj]:.2f}, tau_c/t_dead={tcs[ii]:.1f}")

# also point-sampled crossover table with series vs geomfit
print("\n   crossover tau_c/c (point-sampled) geomfit vs series:")
for C in [0.4, 0.7, 0.9]:
    line = f"   C={C}:"
    for s in [0.3, 0.5, 1.0]:
        Ie = I_ext_exact(C, s); grid = np.logspace(-0.5, 3, 500)
        xf = xs = float("inf")
        for t in grid:
            a = math.exp(-1/t)
            if xf == float("inf") and gp_rate_geomfit(C, s, 1.0, a) > Ie: xf = t
            if xs == float("inf") and gp_rate_series(C, s, 1.0, a)[0] > Ie: xs = t
        line += f"  s={s}: fit {xf:6.2f} / series {xs:6.2f}"
    print(line)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), dpi=150, facecolor=PARCH)
X, Y = np.meshgrid(C0s, tcs)
for a_ in ax: a_.set_facecolor(PARCH)
im = ax[0].pcolormesh(X, Y, 100*relerr_at_winner, cmap="RdBu_r", vmin=-5, vmax=5, shading="auto"); ax[0].set_yscale("log")
ax[0].contour(X, Y, win_ser, levels=[0.5], colors=[SEA]); ax[0].contour(X, Y, win_fit, levels=[0.5], colors=[SIG], linestyles="--")
ax[0].set_title("geometric-fit closed form vs exact-$r_k$ spectral rate (%), at mid-fringe-optimal $\\tau$", fontsize=8)
ax[0].set_xlabel("$\\bar C_0$"); ax[0].set_ylabel("$\\tau_c/t_{\\rm dead}$"); fig.colorbar(im, ax=ax[0])
im2 = ax[1].pcolormesh(X, Y, np.log10(delta0_at_winner), cmap="viridis", shading="auto"); ax[1].set_yscale("log")
ax[1].contour(X, Y, win_ser, levels=[0.5], colors=[SEA]); ax[1].set_title("$\\log_{10}\\delta(0)$ at mid-fringe-optimal $\\tau$ (LO valid only where $\\ll 0$)", fontsize=8)
ax[1].set_xlabel("$\\bar C_0$"); fig.colorbar(im2, ax=ax[1])
fig.suptitle("Check 2 — solid: series winner boundary; dashed: geometric-fit winner boundary", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/sid_check2_geomfit_vs_series.png"); plt.close(fig)

# ---------- Check 3a: HMM grid convergence (common random numbers) ----------
print("\n== Check 3a: latent-AR(1) grid reference convergence (same seed => common random numbers) ==")
def hmm_rate_ML(C, s, theta, a, N, seed, M, L):
    r = np.random.default_rng(seed)
    g = np.linspace(-L*s, L*s, M); sd = s*np.sqrt(1-a*a)
    T = np.exp(-(g[None, :]-a*g[:, None])**2/(2*sd*sd)); T /= T.sum(1, keepdims=True)
    e1 = 0.5*(1+C*np.cos(theta+g)); e0 = 1-e1
    prior = np.exp(-g**2/(2*s*s)); prior /= prior.sum()
    y = simulate(C, s, theta, a, N, r); p0 = 0.5*(1+C*np.cos(theta))
    alpha = prior.copy(); ll1 = 0.0
    for n in range(N):
        alpha = alpha @ T; alpha *= (e1 if y[n] else e0); z = alpha.sum(); ll1 += math.log(z); alpha /= z
    return (ll1-np.sum(y*np.log(p0)+(1-y)*np.log(1-p0)))/N
conv = {}
for C, s, tcc, th in [(0.4, 0.5, 20.0, math.pi/2), (0.9, 0.3, 5.0, math.pi/2), (0.4, 1.0, 20.0, math.pi/2), (0.9, 0.3, 5.0, 0.0)]:
    a = math.exp(-1/tcc); vals = {}
    for M, L in [(41, 5), (61, 5), (101, 5), (161, 5), (241, 5), (101, 4), (101, 6), (161, 7)]:
        vals[(M, L)] = hmm_rate_ML(C, s, th, a, 80_000, 5, M, L)
    ref = vals[(241, 5)]
    conv[f"{C},{s},{tcc},{th:.2f}"] = {f"{k}": v for k, v in vals.items()}
    print(f"C={C} s={s} tc/c={tcc} theta={math.degrees(th):.0f}: ref(M=241,L=5)={ref:.4e}; rel. dev: " +
          " ".join(f"M{M}L{L}:{(v/ref-1)*100:+.2f}%" for (M, L), v in vals.items()))
    print(f"      series comparator at this point: {gp_rate_series(C, s, 1.0, a)[0]:.4e}" if th > 1 else f"      exact D_Bern: {I_ext_exact(C, s):.4e}")

# ---------- Check 3b: CUSUM null run length and delays at matched E0[T] ----------
print("\n== Check 3b: null ARL calibration ==")
def cusum_ext_run(C, s, a, h, r, null):
    p0 = (1-C)/2; p1 = (1-C*math.exp(-s*s/2))/2
    l1, l0 = math.log(p1/p0), math.log((1-p1)/(1-p0))
    W = 0.0; n = 0
    if null:
        while True:
            yb = r.random(4096) < p0
            for yn in yb:
                n += 1; W = max(0.0, W+(l1 if yn else l0))
                if W >= h: return n
    else:
        y = simulate(C, s, math.pi, a, 200_000, r)
        for yn in y:
            n += 1; W = max(0.0, W+(l1 if yn else l0))
            if W >= h: return n
        return n

def cusum_mid_run(C, s, a, h, r, null, M=101):
    g, T, e1, e0, prior = make_hmm(C, s, math.pi/2, a, M)
    W = 0.0; alpha = prior.copy(); n = 0
    def step(yn):
        nonlocal W, alpha
        alpha = alpha @ T; alpha *= (e1 if yn else e0); z = alpha.sum(); alpha /= z
        W += math.log(z)-math.log(0.5)
        if W < -1e-9: W = 0.0; alpha = prior.copy()
        return W >= h
    if null:
        while True:
            yb = r.random(4096) < 0.5
            for yn in yb:
                n += 1
                if step(yn): return n
    else:
        y = simulate(C, s, math.pi/2, a, 200_000, r)
        for yn in y:
            n += 1
            if step(yn): return n
        return n

gamma = 1000.0
C, s = 0.4, 0.5
res = {}
for tcc in [20.0, 5.0]:
    a = math.exp(-1/tcc)
    for name, fn, nruns in [("ext", cusum_ext_run, 200), ("mid", cusum_mid_run, 30)]:
        if name == "ext" and tcc == 5.0:   # null ARL of the extremum detector does not depend on tau_c
            res[(tcc, name)] = res[(20.0, name)]; continue
        hs = [4.0, 5.0, 6.0]; arl = []
        r = np.random.default_rng(77)
        for h in hs:
            runs = [fn(C, s, a, h, r, True) for _ in range(nruns)]
            arl.append(np.mean(runs))
        # log ARL linear in h
        co = np.polyfit(hs, np.log(arl), 1); h_star = (math.log(gamma)-co[1])/co[0]
        r = np.random.default_rng(78)
        arl_star = np.mean([fn(C, s, a, h_star, r, True) for _ in range(nruns)])
        res[(tcc, name)] = (hs, arl, h_star, arl_star)
        print(f"{name} tc/c={tcc}: ARL(h)={[f'{x:.0f}' for x in arl]} at h={hs}; calibrated h*={h_star:.2f} -> ARL={arl_star:.0f} (target {gamma:.0f}); "
              f"margin vs martingale bound e^h: ARL/e^h at h=6 = {arl[2]/math.exp(6):.2f}")

print("\n   delays at calibrated h* (E0 T ~ 1000 for both detectors):")
for tcc in [20.0, 5.0]:
    a = math.exp(-1/tcc)
    r = np.random.default_rng(91)
    de = [cusum_ext_run(C, s, a, res[(tcc, 'ext')][2], r, False) for _ in range(120)]
    r = np.random.default_rng(92)
    dm = [cusum_mid_run(C, s, a, res[(tcc, 'mid')][2], r, False) for _ in range(40)]
    print(f"   tc/c={tcc}: extremum {np.mean(de):.0f} +- {np.std(de)/math.sqrt(len(de)):.0f}  (h*={res[(tcc,'ext')][2]:.2f}) | "
          f"mid-fringe {np.mean(dm):.0f} +- {np.std(dm)/math.sqrt(len(dm)):.0f}  (h*={res[(tcc,'mid')][2]:.2f}) | ratio mid/ext = {np.mean(dm)/np.mean(de):.2f}")
print("done4")
