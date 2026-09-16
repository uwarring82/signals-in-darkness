"""Corrected mid-fringe tau-optimised map: the separate producer note 27 §1 requires.

sid_run3.py's archived map passes rho = r1/(F(u) phi) to gp_rate_geom, so the first binary lag of
its fitted process is r1/F(u): the finite-window factor is lost. That producer and its artifact
res3_comparator.json stay exactly as they are -- tests/test_c08_fold_provenance.py pins the defect
as a negative control -- and this producer writes its own artifact instead. Nothing here reads or
rewrites res3 except to check that the archived form is reproduced.

Three rate forms on run3's own grid, which is read from its source through the AST so that the two
producers cannot drift apart:

  archived   rho = r1/(F phi), a = phi   the committed form, recomputed as a reproduction control
  fit        rho = r1/phi,     a = phi   run4's gp_rate_geomfit; its first lag is r1 (the fix)
  series     six-term sinh series with A = F(u) at 1024 midpoint frequencies (run4's kernel)

Each form is tau-optimised against the exact dark-extremum rate, exactly as run3 does: per
(tau_c, C0) cell the winner is the larger of max_tau R_mid and max_tau R_ext, and the C08
thresholds are the first tau_c/t_dead at which mid-fringe wins in a contrast column.

Scope. Roadmap F is OPEN: no finite-window comparator has been validated against the exact binary
likelihood. This corrects an implementation defect in a comparator; it does not establish a
validated finite-window map, and it changes no claim. C08 keeps the scope note 27 gave it, its
four quoted coarse-grid thresholds.

Usage:
    python analysis/runs/sid_run14.py [--quick]

--quick evaluates every tenth grid line, for tests. Full runs write
analysis/reproduction/res14_corrected_mid_fringe_map.json; quick runs append a marker to the name
so a test artifact can never be mistaken for the map.
"""
import ast
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import numpy as np

import sid_repro
from sid_lib import I_ext_exact, gp_rate_geom, rk_exact

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RUN3 = os.path.join(ROOT, "analysis", "runs", "sid_run3.py")
ARCHIVE = os.path.join(ROOT, "analysis", "outputs", "res3_comparator.json")
ARTIFACT = "res14_corrected_mid_fringe_map.json"
GRID_NAMES = ("T2", "td", "gs", "C0s", "tcs", "taus")
THRESHOLD_COLUMNS = (0.2, 0.4, 0.5, 0.7, 0.9, 0.99)      # run3's own six contrast columns
TERMS, NF = 6, 1024
FORMS = ("archived", "fit", "series")


def run3_grid():
    """run3's grid, evaluated from its own assignments rather than retyped here."""
    source = ast.parse(open(RUN3, encoding="utf-8").read())
    wanted, nodes = set(GRID_NAMES), []
    for node in source.body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            names |= {e.id for t in node.targets if isinstance(t, ast.Tuple)
                      for e in t.elts if isinstance(e, ast.Name)}
            if names & wanted:
                nodes.append(node)
    ns = {"np": np, "math": math}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "run3:grid", "exec"), ns)
    missing = [n for n in GRID_NAMES if n not in ns]
    assert not missing, f"run3 no longer defines {missing}"
    return {name: ns[name] for name in GRID_NAMES}


def geometric_rate(rho, a):
    """gp_rate_geom over arrays; identical arithmetic, evaluated elementwise."""
    alpha = 1 + a * a - 2 * rho * a * a
    beta = 2 * a * (rho - 1)
    small = np.abs(beta) < 1e-14
    safe = np.where(small, 1.0, beta)
    b = (-alpha + np.sqrt(np.maximum(alpha * alpha - beta * beta, 0.0))) / safe
    return np.where(small, 0.0, -0.5 * np.log(alpha / (1 + b * b)))


def series_kernel(s2, a1, phi):
    """S(omega) - 1 divided by C^2: the sinh series carries the contrast as a prefactor only.

    Written with a1 = F(u) phi rather than F and phi separately. The two are the same algebraically,
    (s^2 F)^(2m+1) phi^(2m+1) = (s^2 a1)^(2m+1), but the left form is not representable on run3's
    own grid: at tau_c = 0.1 and tau = 30, u = 300 gives F ~ 6e127, so (s^2 F)^11 overflows even
    though phi ~ 2e-135 makes the product ordinary. s^2 a1 stays below 1e-3 there."""
    cos_w = np.cos(np.pi * (np.arange(NF) + 0.5) / NF)
    x = s2 * a1
    g = np.zeros((len(s2), NF))
    for m in range(TERMS):
        pref = np.exp(-s2) * x ** (2 * m + 1) / math.factorial(2 * m + 1)
        am = (phi ** (2 * m + 1))[:, None]
        g += 2 * pref[:, None] * (cos_w[None, :] - am) / (1 - 2 * am * cos_w[None, :] + am * am)
    return g


def column_rates(Ct, c, r1, a1, phi, kernel, live):
    """Per-tau rates of every form in one (tau_c, C0) cell, in nats per unit time.

    live is run3's own guard a1 > 1e-12, kept so that this map and the archived one drop the same
    taus: those whose first binary lag is too small to fit a geometric process to. Like run3's
    scalar comparison, it is also false for any non-finite a1."""
    safe_a1 = np.where(live, a1, 1.0)
    safe_r1 = np.where(live, r1, 0.0)
    safe_phi = np.where(live, phi, 1.0)
    archived = np.where(live, geometric_rate(safe_r1 / safe_a1, safe_phi), 0.0) / c
    fit = np.where(live, geometric_rate(safe_r1 / safe_phi, safe_phi), 0.0) / c
    d = (Ct * Ct)[:, None] * kernel
    series = np.where(live, 0.5 * np.mean(d - np.log1p(d), axis=1), 0.0) / c
    return {"archived": archived, "fit": fit, "series": series}


def map_over_grid(grid, stride=1, c0_columns=None):
    """The map over run3's grid. stride thins both axes for a quick pass; c0_columns selects
    contrast columns by index, so one column can be recomputed at full tau_c resolution."""
    T2, td, gs = grid["T2"], grid["td"], grid["gs"]
    taus = grid["taus"]
    tcs = grid["tcs"] if c0_columns is not None else grid["tcs"][::stride]
    C0s = grid["C0s"][np.asarray(c0_columns)] if c0_columns is not None else grid["C0s"][::stride]
    shape = (len(tcs), len(C0s))
    out = {f: {"win": np.zeros(shape), "ratio": np.zeros(shape), "tau_over_T2": np.zeros(shape),
               "s_at_winner": np.zeros(shape)} for f in FORMS}
    for i, tc in enumerate(tcs):
        # run3's own arithmetic. At small tau_c, F(u) reaches ~6e127 and phi ~2e-135; both are
        # representable and their product is ordinary, so only a kernel written in F alone would
        # overflow. Warnings are suppressed here, values are not.
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            u = taus / tc
            c = taus + td
            s2 = gs * gs * 2 * (tc * taus - tc * tc * (1 - np.exp(-u)))
            s = np.sqrt(s2)
            F = (np.cosh(u) - 1) / (u - 1 + np.exp(-u))
            phi = np.exp(-c / tc)
            a1 = phi * F
            live = a1 > 1e-12
            kernel = series_kernel(s2, np.where(live, a1, 0.0), phi)
            for j, C0 in enumerate(C0s):
                Ct = C0 * np.exp(-taus / T2)
                rates = column_rates(Ct, c, rk_exact(Ct, s, a1), a1, phi, kernel, live)
                R_ext = I_ext_exact(Ct, s) / c
                ie = int(np.argmax(R_ext))
                for form, R_mid in rates.items():
                    im = int(np.argmax(R_mid))
                    won = bool(R_mid[im] > R_ext[ie])
                    out[form]["win"][i, j] = float(won)
                    out[form]["ratio"][i, j] = R_mid[im] / max(R_ext[ie], 1e-300)
                    out[form]["tau_over_T2"][i, j] = taus[im if won else ie] / T2
                    out[form]["s_at_winner"][i, j] = s[im if won else ie]
    return C0s, tcs, out


def thresholds(C0s, tcs, win):
    """First tau_c/t_dead at which mid-fringe wins, in run3's six contrast columns."""
    rows = []
    for target in THRESHOLD_COLUMNS:
        j = int(np.argmin(abs(C0s - target)))
        idx = np.flatnonzero(win[:, j] > 0)
        rows.append([float(C0s[j]), float(tcs[idx[0]]) if len(idx) else None])
    return rows


def archived_reproduction(rows, win_fraction):
    """The archived form recomputed here must reproduce the committed artifact exactly."""
    import json
    archive = json.load(open(ARCHIVE, encoding="utf-8"))
    stored = archive["tau_optimised_threshold"]
    same = len(stored) == len(rows) and all(
        a[1] == b[1] and math.isclose(a[0], b[0], rel_tol=1e-12) for a, b in zip(stored, rows))
    return {"artifact": "analysis/outputs/res3_comparator.json",
            "stored_thresholds": stored, "recomputed_thresholds": rows,
            "thresholds_identical": bool(same),
            "stored_win_fraction": archive["tau_optimised_win_fraction"],
            "recomputed_win_fraction": win_fraction,
            "win_fraction_identical": bool(archive["tau_optimised_win_fraction"] == win_fraction)}


def lag_one_contract(C=0.4, s=0.5, u=0.3, c_over_tau_c=0.35):
    """What the correction is: the fitted process's first binary lag, against the exact r1."""
    F, phi = (math.cosh(u) - 1) / (u - 1 + math.exp(-u)), math.exp(-c_over_tau_c)
    r1 = rk_exact(C, s, F * phi)
    return {"point": {"C": C, "s": s, "u": u, "c_over_tau_c": c_over_tau_c}, "exact_r1": float(r1),
            "archived_first_lag": float((r1 / (F * phi)) * phi), "fit_first_lag": float((r1 / phi) * phi),
            "archived_matches_r1": bool(math.isclose((r1 / (F * phi)) * phi, r1, rel_tol=1e-12)),
            "fit_matches_r1": bool(math.isclose((r1 / phi) * phi, r1, rel_tol=1e-12))}


def main(argv):
    quick = "--quick" in argv
    unknown = [a for a in argv[1:] if a != "--quick"]
    if unknown:
        print(f"sid_run14.py: unknown arguments {unknown}", file=sys.stderr)
        return 2
    grid = run3_grid()
    C0s, tcs, maps = map_over_grid(grid, stride=10 if quick else 1)
    result = {
        "record": "corrected mid-fringe tau-optimised map (note 27 §1 erratum; C08 workstream)",
        "supersedes_nothing": "analysis/outputs/res3_comparator.json and its figure are unchanged; "
                              "sid_run3.py remains the producer of the historical artifact",
        "scope": "roadmap F is OPEN: no finite-window comparator is validated against the exact "
                 "binary likelihood. This corrects a comparator's lag-one normalisation and "
                 "establishes no finite-window truth map. C08's claim is unchanged.",
        "forms": {"archived": "rho = r1/(F phi), a = phi (sid_run3.py, the defect)",
                  "fit": "rho = r1/phi, a = phi (sid_run4.py gp_rate_geomfit, first lag r1)",
                  "series": f"{TERMS}-term sinh series with A = F(u), {NF} midpoint frequencies"},
        "grid": {"T2_over_t_dead": grid["T2"], "t_dead": grid["td"], "g_sigma_x_T2": grid["gs"] * grid["T2"],
                 "C0": C0s.tolist(), "tau_c_over_t_dead": tcs.tolist(),
                 "tau": grid["taus"].tolist(), "source": "sid_run3.py, read through the AST"},
        "quick": quick,
        "lag_one_contract": lag_one_contract(),
        "provenance": sid_repro.provenance(),
    }
    for form in FORMS:
        win = maps[form]["win"]
        rows = thresholds(C0s, tcs, win)
        result[form] = {
            "thresholds": rows,
            "threshold_fields": ["C0", "min tau_c/t_dead at which mid-fringe wins (null = never)"],
            "win_fraction": float(win.mean()),
            "log10_ratio": np.round(np.log10(np.maximum(maps[form]["ratio"], 1e-300)), 6).tolist(),
            "tau_over_T2_at_winner": np.round(maps[form]["tau_over_T2"], 6).tolist(),
            "s_at_winner": np.round(maps[form]["s_at_winner"], 6).tolist(),
        }
    if not quick:
        result["archived_reproduction"] = archived_reproduction(result["archived"]["thresholds"],
                                                               result["archived"]["win_fraction"])
    name = ARTIFACT if not quick else ARTIFACT.replace(".json", "_QUICK_NOT_THE_MAP.json")
    path = sid_repro.reproduction_path(name)
    sid_repro.write_json(path, result, default=float, indent=1, allow_nan=False)
    for form in FORMS:
        shown = ", ".join("never" if t is None else f"{t:.1f}" for _, t in result[form]["thresholds"])
        print(f"{form:9s} win fraction {result[form]['win_fraction']:.3f}; thresholds {shown}")
    if not quick:
        rep = result["archived_reproduction"]
        print(f"archived form reproduces the committed artifact: thresholds "
              f"{rep['thresholds_identical']}, win fraction {rep['win_fraction_identical']}")
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
