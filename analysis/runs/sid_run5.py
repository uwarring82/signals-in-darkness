import os
import sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Producers write into analysis/reproduction/ (git-ignored), never into the published
# archive. REF_OUTD / REF_FIG are the archive, opened read-only for comparison.
REF_OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reproduction")
os.makedirs(OUTD, exist_ok=True)
import numpy as np
from sid_lib import *
import sid_repro

C, s = 0.4, 0.5

def cusum_ext_run(a, h, r, null, Nmax=400_000):
    p0 = (1-C)/2; p1 = (1-C*math.exp(-s*s/2))/2
    l1, l0 = math.log(p1/p0), math.log((1-p1)/(1-p0))
    W = 0.0; n = 0
    if null:
        while True:
            yb = r.random(8192) < p0
            for yn in yb:
                n += 1; W = max(0.0, W+(l1 if yn else l0))
                if W >= h: return n
    y = simulate(C, s, math.pi, a, Nmax, r)
    for yn in y:
        n += 1; W = max(0.0, W+(l1 if yn else l0))
        if W >= h: return n
    return n

def cusum_mid_run(a, h, r, null, M=81, Nmax=400_000):
    g, T, e1, e0, prior = make_hmm(C, s, math.pi/2, a, M)
    W = 0.0; alpha = prior.copy(); n = 0
    def gen():
        if null:
            while True:
                for yn in (r.random(8192) < 0.5): yield yn
        else:
            for yn in simulate(C, s, math.pi/2, a, Nmax, r): yield yn
    for yn in gen():
        n += 1
        alpha = alpha @ T; alpha *= (e1 if yn else e0); z = alpha.sum(); alpha /= z
        W += math.log(z)-math.log(0.5)
        if W < -1e-9: W = 0.0; alpha = prior.copy()
        if W >= h: return n
    return n

def arl(fn, a, h, runs, seed):
    r = np.random.default_rng(seed)
    v = np.array([fn(a, h, r, True) for _ in range(runs)])
    return v.mean(), v.std()/math.sqrt(runs)

def calibrate(fn, a, gamma, runs, lo=1.5, hi=6.0, iters=7):
    """bisection on h for E0[T] = gamma (log ARL monotone in h); returns h*, measured ARL, se."""
    for _ in range(iters):
        mid = 0.5*(lo+hi); m, se = arl(fn, a, mid, runs, 100+_)
        if m > gamma: hi = mid
        else: lo = mid
    h = 0.5*(lo+hi); m, se = arl(fn, a, h, 2*runs, 999)
    return h, m, se

gamma = 3.0e4
print(f"target E0[T] = {gamma:.0f}")
out = {}
# Claim C10: the martingale bound E0[T] >= e^h and the measured slack. Printed only until
# 4 Sept 2026, which left a result claim with no machine-readable output.
res5 = {"gamma": gamma, "calibration_fields": ["policy", "tau_c/c (null for the extremum)",
        "h_star", "ARL_mean", "ARL_se", "exp_h_star", "slack_ARL_over_exp_h"],
        "calibration": [], "seeds": {"bisection": "100+i", "confirmation": 999,
        "delay_extremum": 7, "delay_mid": 8}}
for tcc in [20.0, 5.0, 1.0]:
    a = math.exp(-1/tcc)
    if "ext" not in out:
        he, me, se = calibrate(cusum_ext_run, a, gamma, 120)
        out["ext"] = (he, me, se); print(f"extremum : h*={he:.3f}  ARL={me:.0f}+-{se:.0f}   e^h*={math.exp(he):.0f}  (slack ARL/e^h = {me/math.exp(he):.0f})")
        res5["calibration"].append(["extremum", None, he, me, se, math.exp(he), me/math.exp(he)])
    hm, mm, sm = calibrate(cusum_mid_run, a, gamma, 24)
    out[("mid", tcc)] = (hm, mm, sm); print(f"mid tc/c={tcc:4.0f}: h*={hm:.3f}  ARL={mm:.0f}+-{sm:.0f}   e^h*={math.exp(hm):.0f}  (slack {mm/math.exp(hm):.0f})")
    res5["calibration"].append(["mid-fringe", tcc, hm, mm, sm, math.exp(hm), mm/math.exp(hm)])

# Written before the delay measurements below, so a failure there cannot destroy the
# calibration table (rule 6; the lesson of sid_run2's figure crash). Atomic write.
sid_repro.write_json(os.path.join(OUTD, "res5_calibration.json"), res5,
                     default=float, indent=1, allow_nan=False)

print("\ndelays at matched E0[T]:")
I_ext = I_ext_exact(C, s)
res5["delays_fields"] = ["tau_c/c", "delay_ext_mean", "delay_ext_se", "h_star_over_I_ext",
                         "delay_mid_mean", "delay_mid_se", "h_star_over_I_series",
                         "delay_ratio_ext_over_mid", "rate_ratio_I_mid_over_I_ext"]
res5["delays"] = []
for tcc, Imid in [(20.0, 3.06e-3), (5.0, 8.9e-4), (1.0, 7.5e-5)]:
    a = math.exp(-1/tcc)
    r = np.random.default_rng(7); de = np.array([cusum_ext_run(a, out["ext"][0], r, False) for _ in range(150)])
    r = np.random.default_rng(8); dm = np.array([cusum_mid_run(a, out[("mid", tcc)][0], r, False) for _ in range(40)])
    print(f"tc/c={tcc:4.0f}: extremum {de.mean():6.0f}+-{de.std()/math.sqrt(len(de)):3.0f} (h*/I={out['ext'][0]/I_ext:6.0f})  |  "
          f"mid-fringe {dm.mean():6.0f}+-{dm.std()/math.sqrt(len(dm)):4.0f} (h*/I_series={out[('mid',tcc)][0]/Imid:6.0f})  |  "
          f"delay ratio ext/mid = {de.mean()/dm.mean():.2f};  rate ratio I_mid/I_ext = {Imid/I_ext:.2f}")
    res5["delays"].append([tcc, de.mean(), de.std()/math.sqrt(len(de)), out["ext"][0]/I_ext,
                           dm.mean(), dm.std()/math.sqrt(len(dm)), out[("mid", tcc)][0]/Imid,
                           de.mean()/dm.mean(), Imid/I_ext])
sid_repro.write_json(os.path.join(OUTD, "res5_calibration.json"), res5,
                     default=float, indent=1, allow_nan=False)
print("done5")
