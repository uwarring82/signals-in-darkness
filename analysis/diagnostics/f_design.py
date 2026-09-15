"""Design inputs for the F plan (diagnostic; computes no ARMA likelihood and no F outcome).
Part 1: continuous C08 thresholds under three mid-fringe forms, sid_run3 committed tau grid.
Part 2: candidate validation points -- F, phi, MA root b (algebra-checked), comparator variants."""
import ast, json, math, sys
import numpy as np
sys.path.insert(0, "analysis/lib")
from sid_lib import rk_exact, I_ext_exact, gp_rate_geom

src = ast.parse(open("analysis/runs/sid_run4.py").read())
names = {"spectrum_series", "gp_rate_series", "gp_rate_geomfit", "gp_rate_geom"}
nodes = [n for n in src.body if (isinstance(n, ast.FunctionDef) and n.name in names)
         or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"NF", "W"} for t in n.targets))]
R4 = {"np": np, "math": math}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "run4", "exec"), R4)
series = lambda C, s, A, a: R4["gp_rate_series"](C, s, A, a)[0]
Ffac = lambda u: (math.cosh(u)-1)/(u-1+math.exp(-u))

def mid(form, C, s, F, phi):
    a1 = phi*F
    if form == "series_F": return series(C, s, F, phi)
    if a1 <= 1e-12: return 0.0
    r1 = rk_exact(C, s, a1)
    return gp_rate_geom(r1/a1 if form == "run3" else r1/phi, phi)

T2, td = 10.0, 1.0; gs = 0.5/T2
taus = np.logspace(-1.5, np.log10(3*T2), 160)
def ratio(C0, tc, form):
    best_mid = best_ext = 0.0
    for tau in taus:
        u = tau/tc; c = tau+td; phi = math.exp(-c/tc); F = Ffac(u)
        s = math.sqrt(gs*gs*2*(tc*tau - tc*tc*(1-math.exp(-u)))); Ct = C0*math.exp(-tau/T2)
        best_mid = max(best_mid, mid(form, Ct, s, F, phi)/c); best_ext = max(best_ext, I_ext_exact(Ct, s)/c)
    return best_mid/best_ext

print("== Part 1: continuous tau-optimised thresholds (tau_c/t_dead), post-hoc diagnostic ==")
stored = {round(r[0], 4): r[1] for r in json.load(open("analysis/outputs/res3_comparator.json"))["tau_optimised_threshold"]}
C0s = np.linspace(0.05, 0.995, 90)
for C0 in [C0s[int(np.argmin(abs(C0s-x)))] for x in (0.4, 0.5, 0.7, 0.9)]:
    out = {}
    for form in ("run3", "fit", "series_F"):
        lo, hi = stored[round(C0, 4)]/1.6, stored[round(C0, 4)]*1.05
        assert ratio(C0, lo, form) < 1 < ratio(C0, hi, form), (C0, form)
        for _ in range(40):
            m = math.sqrt(lo*hi)
            lo, hi = (m, hi) if ratio(C0, m, form) < 1 else (lo, m)
        out[form] = hi
    print(f"C0={C0:.4f}: grid-stored {stored[round(C0,4)]:.2f} | continuous run3 form {out['run3']:.2f} | "
          f"lag-1 fit {out['fit']:.2f} ({(out['fit']/out['run3']-1)*100:+.2f} %) | series A=F {out['series_F']:.2f} "
          f"({(out['series_F']/out['run3']-1)*100:+.2f} %)")

print("\n== Part 2: candidate validation points (per-shot quantities) ==")
def ma_root(F, phi):
    A = phi*(1-F); B = 1 + phi*phi - 2*F*phi*phi
    if abs(A) < 1e-15: return 0.0
    disc = B*B - 4*A*A
    assert disc >= 0, "spectrum not positive"
    roots = [(-B + sgn*math.sqrt(disc))/(2*A) for sgn in (1, -1)]
    b = min(roots, key=abs)
    rho = lambda k: (phi*(1+b*b) + b*(1+phi*phi))/(1+b*b+2*b*phi) * phi**(k-1)
    assert all(abs(rho(k) - F*phi**k) < 1e-12 for k in range(1, 8))
    return b
pts = []
for C0, tc_td, tauT2 in [(0.4, 211.76, 0.512), (0.5, 139.98, 0.512)]:   # C08 boundary, physical calibration
    tau = tauT2*T2; u = tau/tc_td; c = tau+td
    pts.append((f"boundary C0={C0}", C0*math.exp(-tau/T2), math.sqrt(gs*gs*2*(tc_td*tau - tc_td**2*(1-math.exp(-u)))), u, c/tc_td))
for label, C, s, u, c_tc in [("nest (C04 case)", 0.4, 0.5, 0.0, 1/20), ("stress u=0.1", 0.4, 0.5, 0.10, 0.15),
                              ("stress u=0.3", 0.4, 0.5, 0.30, 0.35), ("stress u=0.3 s=1", 0.4, 1.0, 0.30, 0.35),
                              ("stress u=1 s=1", 0.4, 1.0, 1.00, 1.05)]:
    pts.append((label, C, s, u, c_tc))
ref_rate, ref_se, ref_N = 3.05e-3, 0.07, 1e5     # note 02 Check 3a: (0.4, 0.5, 20), series comparator, SE ~7 % at 1e5
print(f"{'point':>18} {'C':>6} {'s':>5} {'u':>6} {'phi':>6} {'F':>7} {'b':>7} {'seriesF':>9} {'fit/serF':>8} {'run3/serF':>9} {'N_1%~':>8}")
for label, C, s, u, c_tc in pts:
    phi = math.exp(-c_tc); F = Ffac(u) if u > 0 else 1.0; b = ma_root(F, phi)
    sF = series(C, s, F, phi)
    n1 = ref_N*(ref_se/0.01)**2*(ref_rate/sF)
    print(f"{label:>18} {C:6.3f} {s:5.3f} {u:6.4f} {phi:6.4f} {F:7.4f} {b:7.4f} {sF:9.3e} {mid('fit',C,s,F,phi)/sF:8.4f} "
          f"{mid('run3',C,s,F,phi)/sF:9.4f} {n1:8.1e}")
print("N_1% is a CRUDE scaling from note 02 (SE_rel ∝ (rate·N)^-1/2); the pilot replaces it.")
