"""Deterministic review of note 26; no latent simulation or likelihood evaluation.

Run from the repository root. Historical driver formulas are read through the AST,
never by importing a driver. JSON goes to stdout; no archive is written.
"""
import ast
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'analysis/lib'))
from sid_lib import gp_rate_geom, rk_exact


def run4_kernels():
    source = ast.parse((ROOT / 'analysis/runs/sid_run4.py').read_text())
    names = {'spectrum_series', 'gp_rate_series', 'gp_rate_geomfit', 'gp_rate_geom'}
    nodes = [n for n in source.body
             if isinstance(n, ast.FunctionDef) and n.name in names
             or isinstance(n, ast.Assign) and any(
                 isinstance(t, ast.Name) and t.id in {'NF', 'W'} for t in n.targets)]
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == names
    ns = {'np': np, 'math': math}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'run4:pure-kernels', 'exec'), ns)
    return ns


def filter_factor(u):
    return (math.cosh(u)-1)/(u-1+math.exp(-u)) if u else 1.0


def run3_map_parameters(C, s, F, phi):
    """Evaluate the actual map call's arguments, not a retyped version of its fold."""
    source = ast.parse((ROOT / 'analysis/runs/sid_run3.py').read_text())
    assigns = [n for n in ast.walk(source) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'Rmid' for t in n.targets)]
    assert len(assigns) == 1
    calls = [n for n in ast.walk(assigns[0]) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'gp_rate_geom']
    assert len(calls) == 1
    expression = ast.Expression(ast.Tuple(elts=calls[0].args, ctx=ast.Load()))
    ns = {'Ct': [C], 's2': [s*s], 'a1': [F*phi], 'c': [-math.log(phi)],
          'tc': 1.0, 'k': 0, 'math': math, 'rk_exact': rk_exact, 'max': max}
    return eval(compile(ast.fix_missing_locations(expression), 'run3:map-arguments', 'eval'), ns)


def assert_lag_one(rho, phi, r1):
    """Contract of a lag-1-matched geometric fit: its first lag must be r1."""
    np.testing.assert_allclose(rho*phi, r1, rtol=1e-12, atol=0)


def comparators(C, s, u, c_over_tc):
    ns = run4_kernels()
    F, phi = filter_factor(u), math.exp(-c_over_tc)
    rho, a = run3_map_parameters(C, s, F, phi)
    return {
        'K1': ns['gp_rate_series'](C, s, F, phi)[0],
        'K2': ns['gp_rate_geomfit'](C, s, F, phi),
        'K3': gp_rate_geom(rho, a),
        'K4': ns['gp_rate_series'](C, s, 1.0, phi)[0],
    }


def exact_boundary_points():
    """Derive E1/E2 alternatives from the stored C08 columns and run3's actual tau grid."""
    archive = json.loads((ROOT / 'analysis/outputs/res3_comparator.json').read_text())
    source = ast.parse((ROOT / 'analysis/runs/sid_run3.py').read_text())
    grids = [n for n in source.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'taus' for t in n.targets)]
    assert len(grids) == 1
    T2 = archive['tau_optimised_grid']['T2_over_t_dead']
    taus = eval(compile(ast.Expression(grids[0].value), 'run3:tau-grid', 'eval'),
                {'np': np, 'T2': T2})
    out = []
    for target in (0.4, 0.5):
        C0, tc = min(archive['tau_optimised_threshold'], key=lambda p: abs(p[0]-target))
        c, u = taus+1, taus/tc
        s2 = (0.5/T2)**2*2*(tc*taus-tc*tc*(1-np.exp(-u)))
        F = (np.cosh(u)-1)/(u-1+np.exp(-u))
        phi = np.exp(-c/tc)
        Ct = C0*np.exp(-taus/T2)
        rates = [gp_rate_geom(*run3_map_parameters(Ct[k], math.sqrt(s2[k]), F[k], phi[k]))/c[k]
                 for k in range(len(taus))]
        k = int(np.argmax(rates))
        out.append(dict(C0=C0, tc_over_td=tc, tau_over_T2=float(taus[k]/T2),
                        C=float(Ct[k]), s=math.sqrt(s2[k]), u=float(u[k]),
                        c_over_tc=float(c[k]/tc)))
    return out


def main():
    rows = {}
    for name, s, u, v in [('E3', .5, .1, .15), ('E4', .5, .3, .35),
                           ('E5', 1., 1., 1.05), ('E6', 1., .3, .35)]:
        K = comparators(.4, s, u, v)
        rows[name] = {**K, 'K3_over_K4': K['K3']/K['K4'],
                      'K2_over_K1': K['K2']/K['K1']}
    K = rows['E6']
    result = {'record': 'post-hoc deterministic review; no F likelihood result',
              'stress_points': rows, 'exact_archive_boundary_points': exact_boundary_points(),
              'E6_example_R_over_K1': 1.03,
              'E6_example_Q1': 1/1.03,
              'E6_example_Q2': K['K2_over_K1']/1.03,
              'max_comparator_ratio_allowing_both_at_delta_005': 1.05/.95}
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
