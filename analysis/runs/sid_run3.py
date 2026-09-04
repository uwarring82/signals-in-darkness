import os
import sys, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
import numpy as np
from sid_lib import *
import matplotlib.pyplot as plt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
REPRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction")
# sid_run3.py consumes res2_partial.json, which only sid_run2.py produces, and the README's
# Reproduce block did not run sid_run2.py. The archived copy therefore answered silently, the
# same failure as the run6s cache. A fresh run is now required unless --from-archive says
# otherwise, so consuming the archive is a stated choice rather than a default.
_fresh = os.path.join(REPRO, "res2_partial.json")
if "--from-archive" in sys.argv:
    _src = os.path.join(OUTD, "res2_partial.json")
    print(f"[input] archived res2_partial.json (explicitly requested)")
elif os.path.exists(_fresh):
    _src = _fresh
    print(f"[input] fresh res2_partial.json from analysis/reproduction/")
else:
    sys.exit("sid_run3.py needs res2_partial.json.\n"
             "  Run `python sid_run2.py` first, or pass --from-archive to read the committed\n"
             "  copy in analysis/outputs/ deliberately.")
res2 = json.load(open(_src))

def gp_rate_num(rk, nf=4096):
    K = len(rk); f = (np.arange(nf)+0.5)/nf
    S = 1 + 2*np.sum(rk[:, None]*np.cos(2*np.pi*np.arange(1, K+1)[:, None]*f[None, :]), axis=0)
    return 0.5*np.mean(S-1-np.log(S))

def gp_rate_geom(rho, a):
    """Closed form for geometric correlations r_k = rho a^k (k>=1), unit variance:
       S(w) = [alpha + beta cos w]/[1 - 2a cos w + a^2],  rate = -1/2 log kappa, alpha+beta cos w = kappa(1+b^2-2b cos w)."""
    alpha = 1 + a*a - 2*rho*a*a; beta = 2*a*(rho-1)
    if abs(beta) < 1e-14: return 0.0
    b = (-alpha + math.sqrt(alpha*alpha - beta*beta))/beta
    kappa = alpha/(1+b*b)
    return -0.5*math.log(kappa)

print("== closed-form GP (geometric fit r_k = r_1 a^(k-1)) vs numeric GP with exact r_k vs exact HMM ==")
for C, s, tcc, hmm in [(r[0], r[1], r[2], r[6]) for r in res2["B2"]]:
    a = math.exp(-1/tcc); ak = a**np.arange(1, 4000); rk = rk_exact(C, s, ak)
    num = gp_rate_num(rk); clo = gp_rate_geom(rk[0]/a, a)
    print(f"C={C} s={s} tc/c={tcc:5.1f}: GP-num={num:.3e}  GP-closed={clo:.3e}  HMM={hmm:.3e}  closed/HMM={clo/hmm:.3f}")

# ---------- exact-comparator crossover in (C, tau_c/c) at fixed s ----------
def I_mid_gp(C, s, tcc):
    a = math.exp(-1/tcc); r1 = rk_exact(C, s, a)
    return gp_rate_geom(r1/a, a)

print("\n== crossover tau_c/c: leading order vs GP comparator, fixed s ==")
for C in [0.4, 0.5, 0.7, 0.9, 0.99]:
    lo = 2/math.log1p(4*C*C*(1-C*C))
    line = f"C={C:4.2f}: LO={lo:6.2f}"
    for s in [0.1, 0.3, 0.5, 1.0]:
        Ie = I_ext_exact(C, s)
        grid = np.logspace(-0.5, 3, 400)
        Im = np.array([I_mid_gp(C, s, t) for t in grid])
        idx = np.where(Im > Ie)[0]
        xc = grid[idx[0]] if len(idx) else float("inf")
        line += f"  s={s}: {xc:6.2f}"
    print(line)

# ---------- figure: rate check (fixed) ----------
fig, ax = plt.subplots(figsize=(6.6, 4.3), dpi=150, facecolor=PARCH); ax.set_facecolor(PARCH)
C, s = 0.4, 0.5
tcc_grid = np.array([1, 2, 3, 5, 8, 12, 20, 35, 60, 100])
lo_v, hs_v, gp_v, hmm_v = [], [], [], []
for tcc in tcc_grid:
    a = math.exp(-1/tcc); ak = a**np.arange(1, 4000); rk = rk_exact(C, s, ak)
    lo_v.append(I_mid_lo(C, s, S2_point(tcc))); hs_v.append(0.5*np.sum(rk**2)); gp_v.append(gp_rate_geom(rk[0]/a, a))
    hmm_v.append(hmm_rate(C, s, math.pi/2, a, N=100_000, seed=7, M=101))
ax.plot(tcc_grid, lo_v, "--", color=STONE, label=r"leading order $\frac{1}{2}\bar{C}^4 s^4 \Sigma a_k^2$ (card)")
ax.plot(tcc_grid, hs_v, ":", color=STONE, label=r"$\frac{1}{2}\Sigma r_k^2$ with exact $r_k$")
ax.plot(tcc_grid, gp_v, "-", color=SEA, label="Gaussian-process closed form")
ax.plot(tcc_grid, hmm_v, "o", color=SIG, label="exact latent-AR(1) binary HMM (MC)")
ax.axhline(I_ext_exact(C, s), color=INK, lw=1, label=r"extremum, exact $D_{\rm Bern}$")
ax.axhline(0.5*C*C*s*s, color=SEA, lw=0.8, ls="-.", label=r"frozen-offset limit $\bar C^2 s^2/2$")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel(r"$\tau_c/c$"); ax.set_ylabel("information per shot (nats)")
ax.set_title(fr"Mid-fringe rate approximations, $\bar C={C}$, $s={s}$ rad", fontsize=10); ax.legend(fontsize=7.5)
fig.tight_layout(); fig.savefig(f"{OUT}/sid_midfringe_rate_check.png"); plt.close(fig)
assert os.path.getsize(f"{OUT}/sid_midfringe_rate_check.png") > 10_000, "figure not written"
print("rate-check values (tcc, LO, halfsum, GP, HMM):")
for t, l, h_, g, m in zip(tcc_grid, lo_v, hs_v, gp_v, hmm_v): print(f"  {t:4d}  {l:.2e}  {h_:.2e}  {g:.2e}  {m:.2e}")

# ---------- exact-comparator tau-optimised map, fixed amplitude scale ----------
# units: t_dead = 1, T2 = 10; g*sigma_x chosen so that s_tau = 0.5 rad at tau = T2 in the tau << tau_c limit.
T2, td = 10.0, 1.0
gs = 0.5/T2
C0s = np.linspace(0.05, 0.995, 90); tcs = np.logspace(-1, 3, 90); taus = np.logspace(-1.5, np.log10(3*T2), 160)
win = np.zeros((len(tcs), len(C0s))); ratio = np.zeros_like(win); tau_w = np.zeros_like(win); s_w = np.zeros_like(win)
for i, tc in enumerate(tcs):
    u = taus/tc; c = taus+td
    s2 = gs*gs*2*(tc*taus - tc*tc*(1-np.exp(-u)))
    F = (np.cosh(u)-1)/(u-1+np.exp(-u)); a1 = np.exp(-c/tc)*F
    for j, C0 in enumerate(C0s):
        Ct = C0*np.exp(-taus/T2)
        Rext = np.array([I_ext_exact(Ct[k], math.sqrt(s2[k])) for k in range(len(taus))])/c
        Rmid = np.array([gp_rate_geom(rk_exact(Ct[k], math.sqrt(s2[k]), a1[k])/max(a1[k], 1e-300), math.exp(-c[k]/tc)) if a1[k] > 1e-12 else 0.0
                         for k in range(len(taus))])/c
        ie, im = int(np.argmax(Rext)), int(np.argmax(Rmid))
        w = Rmid[im] > Rext[ie]; win[i, j] = float(w); ratio[i, j] = Rmid[im]/max(Rext[ie], 1e-300)
        tau_w[i, j] = taus[im] if w else taus[ie]; s_w[i, j] = math.sqrt(s2[im] if w else s2[ie])
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), dpi=150, facecolor=PARCH)
for a_ in ax: a_.set_facecolor(PARCH)
X, Y = np.meshgrid(C0s, tcs)
ax[0].contourf(X, Y, win, levels=[-0.5, 0.5, 1.5], colors=[PARCH, "#cfdde6"])
cs = ax[0].contour(X, Y, np.log10(ratio), levels=[-3, -2, -1, 0, 1], colors=[SEA], linewidths=0.9); ax[0].clabel(cs, fmt="%d", fontsize=7)
ax[0].axvline(0.5, color=STONE, lw=1); ax[0].axvline(0.405, color=STONE, lw=1, ls="-.")
ax[0].set_yscale("log"); ax[0].set_xlabel(r"$\bar C_0$"); ax[0].set_ylabel(r"$\tau_c/t_{\rm dead}$")
ax[0].set_title(r"winner after $\tau$ optimisation; contours $\log_{10}(R_{\rm mid}/R_{\rm ext})$", fontsize=9)
ax[0].text(0.08, 400, "mid-fringe", color=SEA); ax[0].text(0.55, 0.15, "extremum", color=INK)
im1 = ax[1].pcolormesh(X, Y, np.log10(tau_w/T2), cmap="cividis", shading="auto"); ax[1].set_yscale("log"); ax[1].set_xlabel(r"$\bar C_0$")
ax[1].set_title(r"optimal $\log_{10}(\tau/T_2)$ of winner", fontsize=9); fig.colorbar(im1, ax=ax[1])
im2 = ax[2].pcolormesh(X, Y, s_w, cmap="magma", shading="auto"); ax[2].set_yscale("log"); ax[2].set_xlabel(r"$\bar C_0$")
ax[2].set_title(r"$s_\tau$ (rad) at the winner's $\tau$", fontsize=9); fig.colorbar(im2, ax=ax[2])
fig.suptitle(r"Exact-comparator $\tau$-optimised map: $T_2=10\,t_{\rm dead}$, $g\sigma_x T_2 = 0.5$ rad, exp. contrast decay, GP mid-fringe rate", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/sid_regime_map_tau_optimised_exact.png"); plt.close(fig)
print("\nexact-comparator tau-optimised map: mid-fringe wins on", round(win.mean(), 3), "of grid")
# where does mid-fringe start winning, per contrast column
for j in [np.argmin(abs(C0s-c_)) for c_ in [0.2, 0.4, 0.5, 0.7, 0.9, 0.99]]:
    idx = np.where(win[:, j] > 0)[0]
    print(f"  C0={C0s[j]:.2f}: mid-fringe wins for tau_c/t_dead >= {tcs[idx[0]]:.1f}" if len(idx) else f"  C0={C0s[j]:.2f}: never")
print("done3")
