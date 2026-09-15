"""Diagnostic, not part of F: does C08's map fold the finite-window factor as intended?
Compares sid_run3's rho = r1/a1 form with a lag-1-matched fit (rho = r1/phi) and run4's exact
sinh series with A = F(u). Replicates the stored C08 thresholds first. No ARMA likelihood."""
import ast, json, math, sys, time
import numpy as np
sys.path.insert(0, "analysis/lib")
from sid_lib import rk_exact, I_ext_exact, gp_rate_geom

src = ast.parse(open("analysis/runs/sid_run4.py").read())
names = {"spectrum_series", "gp_rate_series", "gp_rate_geomfit", "gp_rate_geom"}
nodes = [n for n in src.body if (isinstance(n, ast.FunctionDef) and n.name in names)
         or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"NF", "W"} for t in n.targets))]
R4 = {"np": np, "math": math}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "run4", "exec"), R4)

T2, td = 10.0, 1.0; gs = 0.5/T2
Ffac = lambda u: (math.cosh(u)-1)/(u-1+math.exp(-u))

print("== single points: ratios of mid-fringe rates ==")
for C0, tc, tauT2 in [(0.4, 210, 0.512), (0.9, 45, 0.491), (0.4, 20, 0.3), (0.4, 10, 1.0)]:
    tau = tauT2*T2; u = tau/tc; c = tau+td; phi = math.exp(-c/tc); F = Ffac(u); a1 = phi*F
    s = math.sqrt(gs*gs*2*(tc*tau - tc*tc*(1-math.exp(-u)))); Ct = C0*math.exp(-tau/T2)
    r1 = rk_exact(Ct, s, a1)
    run3 = gp_rate_geom(r1/a1, phi)          # as in sid_run3.py:126
    fit = gp_rate_geom(r1/phi, phi)          # matches the exact lag-1 correlation
    ser_F = R4["gp_rate_series"](Ct, s, F, phi)[0]
    ser_1 = R4["gp_rate_series"](Ct, s, 1.0, phi)[0]
    print(f"C0={C0} tc/td={tc} tau/T2={tauT2}: u={u:.4f} F={F:.4f} s={s:.3f} | run3/seriesF={run3/ser_F:.4f} "
          f"fit/seriesF={fit/ser_F:.4f} run3/series(A=1)={run3/ser_1:.4f} 1/F^2={1/F**2:.4f}")

print("\n== C08 thresholds on sid_run3's committed grids ==")
stored = json.load(open("analysis/outputs/res3_comparator.json"))["tau_optimised_threshold"]
C0s = np.linspace(0.05, 0.995, 90); tcs = np.logspace(-1, 3, 90); taus = np.logspace(-1.5, np.log10(3*T2), 160)
t0 = time.time()
for C0_stored, thr_stored in stored:
    j = int(np.argmin(abs(C0s - C0_stored))); C0 = C0s[j]
    if round(C0, 1) not in (0.4, 0.5, 0.7, 0.9): continue
    thr = {"run3": None, "fit": None}
    for tc in tcs:
        u = taus/tc; c = taus+td
        s2 = gs*gs*2*(tc*taus - tc*tc*(1-np.exp(-u)))
        F = (np.cosh(u)-1)/(u-1+np.exp(-u)); a1 = np.exp(-c/tc)*F; phi = np.exp(-c/tc)
        Ct = C0*np.exp(-taus/T2)
        Rext = max(I_ext_exact(Ct[k], math.sqrt(s2[k]))/c[k] for k in range(len(taus)))
        for key in thr:
            if thr[key] is not None: continue
            Rmid = []
            for k in range(len(taus)):
                if a1[k] <= 1e-12: Rmid.append(0.0); continue
                r1 = rk_exact(Ct[k], math.sqrt(s2[k]), a1[k])
                rho = r1/max(a1[k], 1e-300) if key == "run3" else r1/phi[k]
                Rmid.append(gp_rate_geom(rho, phi[k])/c[k])
            if max(Rmid) > Rext: thr[key] = float(tc)
        if all(v is not None for v in thr.values()): break
    print(f"C0={C0:.4f}: stored {thr_stored:.3f} | replicated run3 form {thr['run3']:.3f} | lag-1-matched fit {thr['fit']:.3f} "
          f"({(thr['fit']/thr['run3']-1)*100:+.1f} %, grid step {(tcs[1]/tcs[0]-1)*100:.1f} %)")
print(f"[{time.time()-t0:.0f}s]")
