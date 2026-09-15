"""Keep the geometric archive and note 02's series calculation distinguishable.

Run4 is a monolithic producer. Load its pure definitions and declared grid through the AST
without executing its simulations or writing reproduction outputs. See note 25.
"""
import ast
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis/lib"))
from sid_lib import I_ext_exact, I_mid_gp


def _run4_comparator():
    source = ast.parse((ROOT / "analysis/runs/sid_run4.py").read_text())
    names = {"spectrum_series", "gp_rate_series", "gp_rate_geomfit", "gp_rate_geom"}
    nodes = [n for n in source.body
             if (isinstance(n, ast.FunctionDef) and n.name in names)
             or (isinstance(n, ast.Assign) and any(
                 isinstance(t, ast.Name) and t.id in {"NF", "W"} for t in n.targets))]
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == names
    loop = next(n for n in source.body if isinstance(n, ast.For)
                and isinstance(n.target, ast.Name) and n.target.id == "C")
    grid = next(n for n in ast.walk(loop) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "grid" for t in n.targets))
    namespace = {"np": np, "math": math}
    exec(compile(ast.Module(body=nodes + [grid], type_ignores=[]),
                 "sid_run4.py:pure-comparator", "exec"), namespace)
    return namespace, ast.literal_eval(loop.iter)


def _first_crossing(grid, rate, threshold):
    return next((float(t) for t in grid if rate(t) > threshold), None)


def test_res3_crossover_is_reproduced_by_the_geometric_comparator():
    archive = json.loads((ROOT / "analysis/outputs/res3_comparator.json").read_text())
    grid = np.logspace(*archive["grid"]["logspace"])
    for row in archive["comparator_crossover"]:
        C, s = row[:2]
        fresh = _first_crossing(grid, lambda t: I_mid_gp(C, s, t), I_ext_exact(C, s))
        if row[3] is None:
            assert fresh is None
        else:
            assert fresh == pytest.approx(row[3], rel=1e-14, abs=0)


@pytest.mark.parametrize("C,note_fit,note_series", [(0.4, 34, 40), (0.7, 25, 29),
                                                  (0.9, 249, 323)])
def test_run4_reproduces_note02_series_comparison_at_large_amplitude(C, note_fit, note_series):
    functions, contrasts = _run4_comparator()
    assert C in contrasts
    threshold = I_ext_exact(C, 1.0)
    fit = _first_crossing(functions["grid"], lambda t: functions["gp_rate_geomfit"](
        C, 1.0, 1.0, math.exp(-1/t)), threshold)
    series = _first_crossing(functions["grid"], lambda t: functions["gp_rate_series"](
        C, 1.0, 1.0, math.exp(-1/t))[0], threshold)
    # The integer pairs are printed in note 02, not inferred from v1.1's different table.
    assert fit == pytest.approx(note_fit, abs=0.5, rel=0)
    assert series == pytest.approx(note_series, abs=0.5, rel=0)
    assert series > fit
