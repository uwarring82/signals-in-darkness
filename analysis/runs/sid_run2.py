import os
import sys, math, time, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Producers write into analysis/reproduction/ (git-ignored), never into the published
# archive. REF_OUTD / REF_FIG are the archive, opened read-only for comparison.
REF_OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction")
os.makedirs(OUTD, exist_ok=True)
import numpy as np
from sid_lib import *
import sid_repro
import matplotlib.pyplot as plt

REF_FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction", "figures")
os.makedirs(OUT, exist_ok=True)
res = {}

# ---------- B2: Gaussian-process comparator for the mid-fringe rate ----------
def gp_rate(rk):
    """KL rate of a stationary Gaussian process with unit variance and lag correlations rk (k>=1) vs white:
       1/2 * mean_f [ S(f) - 1 - log S(f) ],  S(f) = 1 + 2 sum_k rk cos(2 pi f k)."""
    K = len(rk); f = (np.arange(0, 4096)+0.5)/4096
    S = 1 + 2*np.sum(rk[:, None]*np.cos(2*np.pi*np.arange(1, K+1)[:, None]*f[None, :]), axis=0)
    return 0.5*np.mean(S-1-np.log(S)), S.max()

print("== B2: mid-fringe: LO vs 1/2 sum rk^2 vs Gaussian comparator vs exact HMM ==")
rows = []
for C, s, tcc in [(0.4, 0.5, 1.0), (0.4, 0.5, 5.0), (0.4, 0.5, 20.0), (0.4, 0.5, 60.0), (0.4, 0.2, 60.0), (0.9, 0.3, 5.0), (0.4, 1.0, 20.0)]:
    a = math.exp(-1/tcc); ks = np.arange(1, 3000); ak = a**ks
    rk = rk_exact(C, s, ak)
    lo = I_mid_lo(C, s, S2_point(tcc)); hs = 0.5*np.sum(rk**2); gp, Smax = gp_rate(rk)
    hmm = hmm_rate(C, s, math.pi/2, a, N=150_000, seed=3)
    delta0 = 2*np.sum(rk)             # spectral perturbation at f=0
    frozen = 0.5*C*C*s*s              # frozen-offset (tracking) limit ~ C^2 s^2 /2
    rows.append((C, s, tcc, lo, hs, gp, hmm, delta0, frozen, I_ext_exact(C, s)))
    print(f"C={C} s={s} tc/c={tcc:5.1f}: LO={lo:.3e}  halfsum={hs:.3e}  GP={gp:.3e}  HMM={hmm:.3e}  "
          f"delta(0)={delta0:.2f}  C^2s^2/2={frozen:.3e}  I_ext={I_ext_exact(C,s):.3e}")
res["B2"] = rows

# ---------- exact crossover in tau_c/c at fixed (C, s), using HMM ----------
print("\n== exact crossover location (HMM) vs leading order ==")
xo = {}
for C, s in [(0.4, 0.5), (0.4, 0.2), (0.9, 0.3)]:
    Iext = I_ext_exact(C, s)
    grid = [2, 3, 4, 5, 6, 8, 10, 14, 20]
    vals = []
    for tcc in grid:
        a = math.exp(-1/tcc)
        vals.append(hmm_rate(C, s, math.pi/2, a, N=120_000, seed=4))
    vals = np.array(vals)
    # first crossing
    idx = np.where(vals > Iext)[0]
    xc = None
    if len(idx) and idx[0] > 0:
        i = idx[0]; x0, x1 = grid[i-1], grid[i]; y0, y1 = vals[i-1], vals[i]
        xc = x0 + (Iext-y0)*(x1-x0)/(y1-y0)
    xo[f"{C},{s}"] = (grid, vals.tolist(), Iext, xc)
    print(f"C={C} s={s}: I_ext={Iext:.3e}; HMM mid-fringe by tc/c:", " ".join(f"{g}:{v:.2e}" for g, v in zip(grid, vals)))
    print(f"    LO crossover tc/c = {2/math.log1p(4*C*C*(1-C*C)):.2f};  exact (interp) = {xc}")
res["crossover"] = xo

# ---------- C2: endpoint lemma, variance-reduced ----------
print("\n== C2: endpoint lemma near the crossover, larger N, 3 seeds (common random numbers within seed) ==")
thetas = np.array([0, 20, 40, 60, 75, 85, 90])*math.pi/180
C, s, tcc = 0.9, 0.3, 5.0; a = math.exp(-1/tcc)
E = np.zeros((3, len(thetas)))
for si, seed in enumerate([21, 22, 23]):
    for ti, th in enumerate(thetas):
        E[si, ti] = hmm_rate(C, s, th, a, N=250_000, seed=seed, M=101)
m, se = E.mean(0), E.std(0, ddof=1)/math.sqrt(3)
for th, mm, ss in zip(thetas, m, se):
    print(f"   theta={math.degrees(th):4.0f}: {mm:.3e} +- {ss:.1e}")
res["C2"] = (thetas.tolist(), m.tolist(), se.tolist())

# ---------- F2: CUSUM delays (fixed reset rule) ----------
print("\n== F2: oracle CUSUM delay vs h/I ==")
def cusum_mid(C, s, a, h, runs, seed, Imid, M=101):
    r = np.random.default_rng(seed)
    g, T, e1, e0, prior = make_hmm(C, s, math.pi/2, a, M)
    out = []
    Nmax = 15*int(h/Imid)+2000
    for _ in range(runs):
        y = simulate(C, s, math.pi/2, a, Nmax, r)
        W = 0.0; alpha = prior.copy()
        for n, yn in enumerate(y):
            alpha = alpha @ T; alpha *= (e1 if yn else e0)
            z = alpha.sum(); alpha /= z
            W += math.log(z) - math.log(0.5)
            if W < -1e-9:
                W = 0.0; alpha = prior.copy()
            if W >= h:
                out.append(n+1); break
    return np.array(out)

def cusum_ext(C, s, a, h, runs, seed):
    r = np.random.default_rng(seed)
    p0 = (1-C)/2; p1 = (1-C*math.exp(-s*s/2))/2
    l1, l0 = math.log(p1/p0), math.log((1-p1)/(1-p0))
    out = []
    Nmax = 15*int(h/I_ext_exact(C, s))
    for _ in range(runs):
        y = simulate(C, s, math.pi, a, Nmax, r)
        W = 0.0
        for n, yn in enumerate(y):
            W = max(0.0, W + (l1 if yn else l0))
            if W >= h: out.append(n+1); break
    return np.array(out)

h = math.log(1e3)


def _mean_se(sample, label):
    """(mean, s.e.) or (None, None) if no run reached the threshold -- that is undefined.

    Any other non-finite value is a calculation error and stops the run here, rather than at
    the json.dump at the end of the script after the whole computation has been paid for.
    """
    if len(sample) == 0:
        return None, None
    m = float(sample.mean()); se = float(sample.std()/math.sqrt(len(sample)))
    if not (math.isfinite(m) and math.isfinite(se)):
        raise ValueError(f"non-finite {label} statistic from {len(sample)} completed runs")
    return m, se


frows = []
for C, s, tcc in [(0.4, 0.5, 20.0), (0.4, 0.5, 5.0), (0.4, 0.5, 1.0)]:
    a = math.exp(-1/tcc)
    Imid = [r_[6] for r_ in rows if (r_[0], r_[1], r_[2]) == (C, s, tcc)][0]
    Iext = I_ext_exact(C, s)
    de = cusum_ext(C, s, a, h, 80, 31); dm = cusum_mid(C, s, a, h, 40, 32, Imid)
    de_m, de_se = _mean_se(de, "extremum"); dm_m, dm_se = _mean_se(dm, "mid-fringe")
    frows.append((C, s, tcc, Iext, Imid, de_m, de_se, h/Iext, dm_m, dm_se, h/Imid, len(dm)))
    print(f"C={C} s={s} tc/c={tcc:5.1f}: ext delay={de.mean():6.0f}+-{de.std()/math.sqrt(len(de)):4.0f} (h/I={h/Iext:6.0f}) | "
          f"mid delay={dm.mean():6.0f}+-{dm.std()/math.sqrt(len(dm)):4.0f} (h/I_HMM={h/Imid:6.0f})  detected {len(dm)}/40")
res["F2"] = frows

# ---------- extremum-stream correlation excess (independent check of note 03 section 1) ----------
# Note 03 section 1 reports a dark-fringe excess of the exact extremum rate over the marginal
# Bernoulli divergence, at 3.84e6 shots per point (64 x 60 000). NO SCRIPT IN THIS REPOSITORY
# PRODUCED THAT TABLE -- no other hmm_rate call uses theta = pi -- and its seeds were never
# recorded, so the published rows cannot be reproduced, only the method. This block is an
# INDEPENDENT CHECK at the same design with seeds 0..63 recorded, not a reproduction of the
# published values. See claim C24 and notes/2026-09-04-note-09-extremum-bonus-provenance.md.
print("\n== extremum-stream correlation excess (independent check, seeds 0-63) ==")
bonus = []
for C_, s_, tcc_ in [(0.9, 0.3, 5.0), (0.9, 0.3, 20.0), (0.4, 0.5, 20.0)]:
    a_ = math.exp(-1/tcc_)
    v = np.array([hmm_rate(C_, s_, math.pi, a_, N=60_000, seed=k) for k in range(64)])
    m_, se_ = float(v.mean()), float(v.std(ddof=1)/math.sqrt(len(v)))
    db = float(I_ext_exact(C_, s_))
    bonus.append([C_, s_, tcc_, m_, se_, db, 100*(m_/db - 1), 100*se_/db])
    print(f"C={C_} s={s_} tc/c={tcc_:4.1f}: exact={m_:.4e}+-{se_:.1e}  D_Bern={db:.4e}  "
          f"excess={100*(m_/db-1):+.2f} +- {100*se_/db:.2f} %")
res["extremum_bonus"] = bonus
res["extremum_bonus_fields"] = ["C", "s", "tau_c/c", "exact_rate_mean", "exact_rate_se",
                                "marginal_D_Bern", "excess_percent", "excess_se_percent"]
res["extremum_bonus_design"] = {"theta": "pi (dark fringe)", "N_per_seed": 60000,
                                "seeds": "0..63", "shots_per_point": 3840000,
                                "independent_check_of": "notes/2026-09-02-note-03.md#1"}

# Numerical output is written BEFORE any plotting: a figure failure must not be able
# to destroy the run's data. The archived res2_partial.json had to be reconstructed
# from stdout precisely because the dump used to sit after a figure that always crashed.
# Atomic: temporary file then os.replace, so an interruption cannot leave a truncated
# res2_partial.json that still parses. Written before any plotting (see above).
sid_repro.write_json(os.path.join(OUTD, "res2_partial.json"), res,
                     default=float, indent=1, allow_nan=False)

# ---------- figure: mid-fringe rate approximations vs tau_c/c ----------
fig, ax = plt.subplots(figsize=(6.6, 4.3), dpi=150, facecolor=PARCH); ax.set_facecolor(PARCH)
C, s = 0.4, 0.5
tcc_grid = np.array([1, 2, 3, 5, 8, 12, 20, 35, 60, 100])
lo_v, hs_v, gp_v, hmm_v = [], [], [], []
for tcc in tcc_grid:
    a = math.exp(-1/tcc); ak = a**np.arange(1, 4000); rk = rk_exact(C, s, ak)
    lo_v.append(I_mid_lo(C, s, S2_point(tcc))); hs_v.append(0.5*np.sum(rk**2)); gp_v.append(gp_rate(rk)[0])
    hmm_v.append(hmm_rate(C, s, math.pi/2, a, N=100_000, seed=7, M=101))
ax.plot(tcc_grid, lo_v, "--", color=STONE, label="leading order $\\frac{1}{2}\\bar C^4 s^4 \\Sigma a_k^2$")
ax.plot(tcc_grid, hs_v, ":", color=STONE, label="$\\frac{1}{2}\\Sigma r_k^2$ with exact $r_k$")
ax.plot(tcc_grid, gp_v, "-", color=SEA, label="Gaussian-process comparator")
ax.plot(tcc_grid, hmm_v, "o", color=SIG, label="exact latent-AR(1) binary HMM")
ax.axhline(I_ext_exact(C, s), color=INK, lw=1, label="extremum, exact $D_{\\rm Bern}$")
ax.axhline(0.5*C*C*s*s, color=SEA, lw=0.8, ls="-.", label="frozen-offset limit $\\bar C^2 s^2/2$")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("$\\tau_c/c$"); ax.set_ylabel("information per shot (nats)")
ax.set_title(f"Mid-fringe rate approximations, $\\bar C={C}$, $s={s}$ rad", fontsize=10); ax.legend(fontsize=7.5)
# Renamed 4 Sept 2026: this and sid_run3.py both wrote sid_midfringe_rate_check.png with
# different curves (numeric GP comparator here, closed-form geometric fit there), so the
# archived figure depended on which script ran last. See figures/README.md.
fig.tight_layout(); fig.savefig(f"{OUT}/sid_midfringe_rate_check_gp_numeric.png"); plt.close(fig)
assert os.path.getsize(f"{OUT}/sid_midfringe_rate_check_gp_numeric.png") > 10_000, "figure not written"

print("done2")
