import os
import sys, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Producers write into analysis/reproduction/ (git-ignored), never into the published
# archive. REF_OUTD / REF_FIG are the archive, opened read-only for comparison.
REF_OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction")
os.makedirs(OUTD, exist_ok=True)
import numpy as np
from scipy.special import i0
from scipy.optimize import brentq, minimize
from sid_lib import DB, I_ext_exact, PARCH, SEA, SIG, INK, STONE
import sid_repro
import matplotlib.pyplot as plt
REF_FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction", "figures")
os.makedirs(OUT, exist_ok=True)

# ================= A. tau-scan identifiability =================
T2 = 10.0                 # sid_run9.py supersedes section A in dimensionless T2 units.
# There is no dead time in this run: an unused td = 1.0 was removed 7 Sept 2026, because
# assigning it invited the reading that this axis prices dead time. It does not; res7A is
# nats PER SHOT (SCHEMA.md:111).
gs = 0.5/T2
def s2_of(tau, tc): return gs*gs*2*(tc*tau - tc*tc*(1-math.exp(-tau/tc)))
def pd(Cc): return (1-Cc)/2          # dark-fringe probability for contrast Cc

taus = np.linspace(0.1*T2, 2.0*T2, 40); w = np.ones_like(taus)/len(taus)
Gam = 1/T2
print("== A. identifiability divergence per shot, uniform tau allocation on [0.1,2] T2 ==")
print("   class A: pointwise band |chi - chi_hat| <= eta0 * chi_hat ;  class B: Markov chi = Gamma tau, |Gamma-Gamma_hat| <= eta0*Gamma_hat")
rows = []
for C0 in (0.4, 0.9):
    for eta0 in (0.02, 0.05, 0.10):
        for tc in (0.5, 2.0, 10.0, 50.0):
            s2 = np.array([s2_of(t, tc) for t in taus]); chihat = Gam*taus; eta = eta0*chihat
            # unconstrained (both chi fixed at chi_hat)
            I_unc = sum(wt*DB(pd(C0*math.exp(-ch-x/2)), pd(C0*math.exp(-ch))) for wt, ch, x in zip(w, chihat, s2))
            # class A: decouples per tau
            I_A = 0.0
            for wt, ch, x, e in zip(w, chihat, s2, eta):
                if x/2 > 2*e:
                    I_A += wt*DB(pd(C0*math.exp(-ch+e-x/2)), pd(C0*math.exp(-ch-e)))
            # class B: 2-parameter infimum
            def objB(v):
                Gs, G0 = v
                return sum(wt*DB(pd(C0*math.exp(-Gs*t-x/2)), pd(C0*math.exp(-G0*t))) for wt, t, x in zip(w, taus, s2))
            best = min((minimize(objB, x0, bounds=[(Gam*(1-eta0), Gam*(1+eta0))]*2, method="L-BFGS-B").fun
                        for x0 in ([Gam, Gam], [Gam*(1-eta0), Gam*(1+eta0)], [Gam*(1+eta0), Gam*(1-eta0)])))
            I_B = max(best, 0.0)
            # single-tau extremum reference (best tau, unconstrained null) for scale
            I_ref = max(DB(pd(C0*math.exp(-ch-x/2)), pd(C0*math.exp(-ch))) for ch, x in zip(chihat, s2))
            dG = gs*gs*tc            # extra dephasing rate in the tau >> tau_c limit
            rows.append((C0, eta0, tc, I_unc, I_A, I_B, I_ref, dG/(2*eta0*Gam)))
            print(f"C0={C0} eta0={eta0:.2f} tau_c={tc:5.1f} (=tau_c/T2 {tc/T2:.2f}): unconstrained={I_unc:.2e}  classA={I_A:.2e}  classB={I_B:.2e}  "
                  f"best-single-tau={I_ref:.2e}   DeltaGamma/(2 eta0 Gamma)={dG/(2*eta0*Gam):5.2f}")
sid_repro.write_json(os.path.join(OUTD, "res7A_identifiability.json"), rows, allow_nan=False)

# ================= B. servo regime: four-outcome effective contrast vs kappa =================
print("\n== B. servo regime: effective contrast of the two channels vs oscillator coherence kappa ==")
KAPPA_INF = "positive-infinity"   # sentinel for the kappa -> infinity row; see SCHEMA.md
C1 = C2 = 0.9
phi = np.linspace(-math.pi, math.pi, 4001)[:-1]
def vm(kappa, mu=0.0):
    if kappa == math.inf: return None
    q = np.exp(kappa*np.cos(phi-mu)); return q/q.sum()
def four_outcome(eps, kappa, ph1, ph2):
    """P(B1,B2) marginalised over the oscillator phase (von Mises, mean tracked at 0)."""
    q = vm(kappa)
    if q is None:
        c1 = C1*math.cos(ph1); c2 = C2*math.cos(eps+ph2)
        return {(b1, b2): 0.25*(1+b1*c1)*(1+b2*c2) for b1 in (-1, 1) for b2 in (-1, 1)}
    c1 = C1*np.cos(phi+ph1); c2 = C2*np.cos(phi+eps+ph2)
    return {(b1, b2): float(np.sum(q*0.25*(1+b1*c1)*(1+b2*c2))) for b1 in (-1, 1) for b2 in (-1, 1)}
def parity(P): return {+1: P[(1, 1)]+P[(-1, -1)], -1: P[(1, -1)]+P[(-1, 1)]}
def KL(P, Q): return sum(P[k]*math.log(P[k]/Q[k]) for k in P if P[k] > 0)
def fisher(kappa, ph1, ph2, full=True, d=1e-4):
    Pp = four_outcome(d, kappa, ph1, ph2); Pm = four_outcome(-d, kappa, ph1, ph2); P0 = four_outcome(0.0, kappa, ph1, ph2)
    if not full: Pp, Pm, P0 = parity(Pp), parity(Pm), parity(P0)
    return sum(((Pp[k]-Pm[k])/(2*d))**2/P0[k] for k in P0)
def var_channel(kappa, ph1, ph2, ssq, full=True):
    """KL of a white Gaussian phase modulation of variance ssq vs none (extremum-type channel)."""
    xs = np.linspace(-4, 4, 41)*math.sqrt(ssq); wts = np.exp(-xs**2/(2*ssq)); wts /= wts.sum()
    keys = [(b1, b2) for b1 in (-1, 1) for b2 in (-1, 1)]
    P1 = {k: 0.0 for k in keys}
    for x, wt in zip(xs, wts):
        P = four_outcome(float(x), kappa, ph1, ph2)
        for k in keys: P1[k] += wt*P[k]
    P0 = four_outcome(0.0, kappa, ph1, ph2)
    if not full: P1, P0 = parity(P1), parity(P0)
    return KL(P1, P0)
ssq = 0.3**2
print(f"   C1=C2={C1}; slope channel: sqrt(FI_eps) at best phases; variance channel: KL for white s={math.sqrt(ssq)} at best phases, mapped to an equivalent binary-link contrast")
def ceff_from_kl(kl):
    f = lambda c: I_ext_exact(c, math.sqrt(ssq)) - kl
    return brentq(f, 1e-4, 0.999999) if f(0.999999) > 0 else 1.0
grid = [(a, b) for a in np.linspace(0, math.pi, 13) for b in np.linspace(0, math.pi, 13)]
tab = []
for kappa in (0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, math.inf):
    fi_par = max(fisher(kappa, a, b, False) for a, b in grid); fi_full = max(fisher(kappa, a, b, True) for a, b in grid)
    kv_par = max(var_channel(kappa, a, b, ssq, False) for a, b in grid[::3]); kv_full = max(var_channel(kappa, a, b, ssq, True) for a, b in grid[::3])
    # kappa -> infinity is the perfect-oscillator limit: a KNOWN limiting case, not a missing
    # or inapplicable value, so it carries an explicit sentinel string rather than null. null
    # stays reserved for undefined/not-applicable. Infinity is not valid JSON. See SCHEMA.md.
    tab.append((KAPPA_INF if math.isinf(kappa) else kappa, math.sqrt(fi_par), math.sqrt(fi_full),
                ceff_from_kl(kv_par), ceff_from_kl(kv_full)))
    print(f"kappa={kappa:>5}: slope C_eff parity={math.sqrt(fi_par):.3f} full={math.sqrt(fi_full):.3f} | variance C_eff parity={ceff_from_kl(kv_par):.3f} full={ceff_from_kl(kv_full):.3f}")
sid_repro.write_json(os.path.join(OUTD, "res7B_servo.json"), tab, allow_nan=False)

fig, ax = plt.subplots(figsize=(6.2, 4.0), dpi=150, facecolor=PARCH); ax.set_facecolor(PARCH)
kap = [100 if t[0] == KAPPA_INF else t[0] for t in tab]   # perfect oscillator drawn at 100
ax.plot(kap, [t[1] for t in tab], "o--", color=STONE, label="slope channel, parity only")
ax.plot(kap, [t[2] for t in tab], "o-", color=SEA, label="slope channel, four-outcome")
ax.plot(kap, [t[3] for t in tab], "s--", color=STONE, label="variance channel, parity only")
ax.plot(kap, [t[4] for t in tab], "s-", color=SIG, label="variance channel, four-outcome")
ax.axhline(0.5*C1*C2, color=INK, lw=0.8, ls=":", label="$\\bar C_{par}=\\frac{1}{2}\\bar C_1\\bar C_2$")
ax.axhline(C2, color=INK, lw=0.8, label="$\\bar C_2$ (perfect oscillator)")
ax.set_xscale("symlog", linthresh=1); ax.set_xlabel("oscillator coherence $\\kappa$ (von Mises; 100 = perfect)"); ax.set_ylabel("equivalent binary-link contrast")
ax.set_title(f"Servo regime: effective contrast of each channel, $\\bar C_1=\\bar C_2={C1}$", fontsize=10); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(f"{OUT}/sid_servo_effective_contrast.png"); plt.close(fig)
print("done7")
