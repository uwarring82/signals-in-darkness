"""Contract tests for analysis/runs/sid_run14.py, the corrected mid-fringe map (note 27 §1, note 30).

The archived producer and artifact are the historical record and stay untouched;
tests/test_c08_fold_provenance.py pins the archived defect as a negative control. These tests check
that the new producer computes run3's own map, that the numerical correction and the lag-one
normalisation are separated rather than mixed, and that it writes nowhere near the archive.
"""
import hashlib
import json
import math
import subprocess
import sys
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "runs"))
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
sys.path.insert(0, str(ROOT / "analysis" / "diagnostics"))
import sid_run14 as r14  # noqa: E402
from review_F_plan import filter_factor, run4_kernels  # noqa: E402
from sid_lib import gp_rate_geom, rk_exact  # noqa: E402

ARCHIVE_PATH = ROOT / "analysis" / "outputs" / "res3_comparator.json"
ARTIFACT_PATH = ROOT / "analysis" / "reproduction" / "res14_corrected_mid_fringe_map.json"
ARCHIVE = json.loads(ARCHIVE_PATH.read_text())
STORED = {round(c0, 4): thr for c0, thr in ARCHIVE["tau_optimised_threshold"]}
CLAIMED_COLUMNS = (0.4, 0.5, 0.7, 0.9)            # the four thresholds C08 quotes
CHANGED_COLUMN = 0.995                            # outside the claim; the correction moves it
CORRECTED_CHANGED_THRESHOLD = 36.45841237070733
DEAD_CORNER = {"stable": 2.2932836135e-24, "historical": 1.0761908808e-16}


def test_the_grid_is_run3s_own_grid_not_a_retyped_one():
    grid = r14.run3_grid()
    stored = ARCHIVE["tau_optimised_grid"]
    assert np.array_equal(grid["C0s"], np.array(stored["C0"]))
    assert np.array_equal(grid["tcs"], np.array(stored["tau_c_over_t_dead"]))
    assert grid["T2"] == stored["T2_over_t_dead"]
    assert grid["gs"] * grid["T2"] == stored["g_sigma_x_T2"]
    assert len(grid["taus"]) == 160


# ------------------------------------------------------------------ the two arithmetics
def test_historical_rate_equals_the_committed_scalar_elementwise():
    rng = np.random.default_rng(0)
    rho, a = rng.uniform(1e-6, 0.5, 500), rng.uniform(0.01, 0.999, 500)
    np.testing.assert_array_equal(r14.geometric_rate_historical(rho, a),
                                  np.array([gp_rate_geom(p, q) for p, q in zip(rho, a)]))


def test_stable_rate_agrees_with_the_historical_one_away_from_the_cancellation():
    rng = np.random.default_rng(1)
    rho, a = rng.uniform(0.05, 0.5, 500), rng.uniform(0.2, 0.99, 500)
    historical = r14.geometric_rate_historical(rho, a)
    np.testing.assert_allclose(r14.geometric_rate_stable(rho, a), historical, rtol=1e-10, atol=0)


def _dead_corner_column():
    """The cell the review identified: C0 = 0.05, tau_c/t_dead = 0.1, where the mid-fringe rate
    is 1e-24 and the historical arithmetic returns its own roundoff."""
    grid = r14.run3_grid()
    taus, T2, td, gs = grid["taus"], grid["T2"], grid["td"], grid["gs"]
    tc, C0 = float(grid["tcs"][0]), float(grid["C0s"][0])
    u, c = taus / tc, taus + td
    s2 = gs * gs * 2 * (tc * taus - tc * tc * (1 - np.exp(-u)))
    F = (np.cosh(u) - 1) / (u - 1 + np.exp(-u))
    phi = np.exp(-c / tc)
    a1 = phi * F
    Ct = C0 * np.exp(-taus / T2)
    rho = rk_exact(Ct, np.sqrt(s2), a1) / phi
    return {"rho": rho, "phi": phi, "c": c, "s2": s2, "Ct": Ct, "a1": a1}


def test_stable_rate_matches_a_seventy_digit_evaluation_where_the_historical_one_collapses():
    cell = _dead_corner_column()
    stable = r14.geometric_rate_stable(cell["rho"], cell["phi"]) / cell["c"]
    historical = r14.geometric_rate_historical(cell["rho"], cell["phi"]) / cell["c"]
    k = int(np.argmax(stable))
    assert stable[k] == pytest.approx(DEAD_CORNER["stable"], rel=1e-9)
    assert historical.max() == pytest.approx(DEAD_CORNER["historical"], rel=1e-6)

    getcontext().prec = 70
    D = Decimal
    a, s2d, Ctd, a1d, cd = (D(float(cell[k_][k])) for k_ in ("phi", "s2", "Ct", "a1", "c"))
    r1d = D("0.5") * Ctd * Ctd * ((-s2d * (1 - a1d)).exp() - (-s2d * (1 + a1d)).exp())
    rho_d = r1d / a
    t = a * (1 - 2 * rho_d)
    S = ((1 - a * a) * (1 - t * t)).sqrt()
    reference = (-D("0.5") * (1 - (a - t) ** 2 / (2 * (1 - a * t + S))).ln()) / cd
    # the residual is r1's own cancellation in sid_lib.rk_exact, entering as r1^2; see note 30
    assert abs(D(float(stable[k])) - reference) / reference < D("1e-7")
    # at the maximising tau the historical form has lost the value completely, and its own maximum
    # over tau sits about 4.7e7 above the true rate
    assert historical[k] == 0.0
    assert historical.max() / stable.max() > 1e7


def test_r1_carries_a_second_milder_cancellation_that_bounds_the_corrected_rate():
    """sid_lib.rk_exact subtracts two near-equal exponentials. It is committed arithmetic shared
    with run3, run4 and roadmap F, so the corrected map keeps it and note 30 discloses the bound."""
    cell = _dead_corner_column()
    k = int(np.argmax(r14.geometric_rate_stable(cell["rho"], cell["phi"]) / cell["c"]))
    getcontext().prec = 70
    D = Decimal
    s2d, Ctd, a1d = (D(float(cell[n][k])) for n in ("s2", "Ct", "a1"))
    reference = D("0.5") * Ctd * Ctd * ((-s2d * (1 - a1d)).exp() - (-s2d * (1 + a1d)).exp())
    committed = float(rk_exact(cell["Ct"][k], math.sqrt(cell["s2"][k]), cell["a1"][k]))
    sinh_form = cell["Ct"][k] ** 2 * math.exp(-cell["s2"][k]) * math.sinh(cell["s2"][k] * cell["a1"][k])
    assert abs(D(committed) - reference) / reference > D("1e-9")      # the committed form loses digits
    assert abs(D(sinh_form) - reference) / reference < D("1e-15")     # an equivalent form does not


# ------------------------------------------------------------------ the series form
@pytest.mark.parametrize("C,s,u,c", [(0.4, 0.5, 0.3, 0.35), (0.4, 1.0, 1.0, 1.05), (0.9, 0.1, 0.01, 0.02)])
def test_series_kernel_reproduces_run4s_kernel(C, s, u, c):
    F, phi = filter_factor(u), math.exp(-c)
    d = C * C * r14.series_kernel(np.array([s * s]), np.array([F * phi]), np.array([phi]))[0]
    rate = 0.5 * np.mean(d - np.log1p(d))
    assert rate == pytest.approx(run4_kernels()["gp_rate_series"](C, s, F, phi)[0], rel=1e-12)


def test_series_kernel_avoids_an_overflow_a_kernel_written_in_F_alone_would_hit():
    grid = r14.run3_grid()
    tc, tau = float(grid["tcs"].min()), float(grid["taus"].max())
    u, c = tau / tc, tau + grid["td"]
    F = (math.cosh(u) - 1) / (u - 1 + math.exp(-u))
    phi = math.exp(-c / tc)
    s2 = grid["gs"] ** 2 * 2 * (tc * tau - tc * tc * (1 - math.exp(-u)))
    assert math.isfinite(F) and F > 1e100 and 0 < phi < 1e-100
    with np.errstate(over="ignore"):
        assert not np.isfinite(np.float64(s2 * F) ** 11)
    assert 0 < s2 * F * phi < 1e-3
    assert np.all(np.isfinite(r14.series_kernel(np.array([s2]), np.array([F * phi]), np.array([phi]))))
    dead = r14.series_kernel(np.array([0.015]), np.array([0.0]), np.array([0.0]))
    assert np.all(np.isfinite(dead)) and np.max(np.abs(dead)) == 0.0


def test_the_correction_is_exactly_the_lag_one_normalisation():
    contract = r14.lag_one_contract()
    assert contract["fit_matches_r1"] and not contract["archived_matches_r1"]
    F = filter_factor(contract["point"]["u"])
    assert contract["archived_first_lag"] == pytest.approx(contract["exact_r1"] / F, rel=1e-12)
    assert F > 1.0


# ------------------------------------------------------------------ thresholds, per form
@pytest.mark.parametrize("target", CLAIMED_COLUMNS)
def test_every_form_reproduces_the_committed_threshold_in_the_claimed_columns(target):
    """C08's four quoted thresholds must survive the numerical correction, the normalisation
    correction and the exact-r_k series alike."""
    grid = r14.run3_grid()
    column = int(np.argmin(abs(grid["C0s"] - target)))
    C0s, tcs, maps = r14.map_over_grid(grid, c0_columns=[column])
    stored = STORED[round(float(C0s[0]), 4)]
    for form in r14.FORMS:
        won = np.flatnonzero(maps[form]["win"][:, 0] > 0)
        assert len(won), f"{form} never wins in the {target} column"
        assert float(tcs[won[0]]) == pytest.approx(stored, rel=1e-12), form


def test_the_changed_column_separates_the_normalisations():
    """Outside the claim, at C0 = 0.995, the corrected normalisation moves the threshold and the
    numerical correction alone does not."""
    grid = r14.run3_grid()
    column = int(np.argmin(abs(grid["C0s"] - CHANGED_COLUMN)))
    C0s, tcs, maps = r14.map_over_grid(grid, c0_columns=[column])
    stored = STORED[round(float(C0s[0]), 4)]
    first = {f: float(tcs[np.flatnonzero(maps[f]["win"][:, 0] > 0)[0]]) for f in r14.FORMS}
    assert first["archived"] == pytest.approx(stored, rel=1e-12)
    assert first["archived_stable"] == pytest.approx(stored, rel=1e-12)
    assert first["fit"] == pytest.approx(CORRECTED_CHANGED_THRESHOLD, rel=1e-12)
    assert first["series"] == pytest.approx(CORRECTED_CHANGED_THRESHOLD, rel=1e-12)
    assert first["fit"] < stored


def test_the_artifact_separates_the_numerical_from_the_normalisation_change():
    """The committed map must keep the two effects apart: arithmetic alone flips no winner."""
    art = json.loads(ARTIFACT_PATH.read_text())
    comparison = art["comparison"]
    assert comparison["cells"] == 8100
    numerical, normalisation = comparison["numerical_correction"], comparison["normalisation_correction"]
    assert numerical["winner_flips"] == 0 and numerical["median_abs_log10_shift"] < 1e-9
    assert numerical["max_abs_log10_shift"] > 8.0 and numerical["cells_beyond_0p01_decades"] > 500
    assert normalisation["winner_flips"] == 30
    assert normalisation["median_abs_log10_shift"] == pytest.approx(0.128472, abs=5e-6)
    assert normalisation["median_percent"] == pytest.approx(34.42, abs=0.01)
    assert comparison["higher_lag_change"]["winner_flips"] == 2
    assert art["archived_reproduction"]["thresholds_identical"] is True
    assert art["archived_reproduction"]["win_fraction_identical"] is True
    assert art["archived"]["win_fraction"] == art["archived_stable"]["win_fraction"]
    assert art["fit"]["win_fraction"] > art["archived"]["win_fraction"]


# ------------------------------------------------------------------ hygiene
def test_the_producer_writes_only_to_reproduction_and_leaves_the_archive_alone():
    before = hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest()
    proc = subprocess.run([sys.executable, str(ROOT / "analysis" / "runs" / "sid_run14.py"), "--quick"],
                          capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr
    assert hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest() == before
    quick = ROOT / "analysis" / "reproduction" / "res14_corrected_mid_fringe_map_QUICK_NOT_THE_MAP.json"
    assert quick.exists() and json.loads(quick.read_text())["quick"] is True
    source = (ROOT / "analysis" / "runs" / "sid_run14.py").read_text()
    assert source.count("write_json") == 1, "one writer only"
    assert "sid_repro.write_json(path" in source and "reproduction_path(name)" in source
    assert source.count("ARCHIVE") == 2 and 'open(ARCHIVE, encoding="utf-8")' in source   # read-only


def test_unknown_arguments_are_refused():
    proc = subprocess.run([sys.executable, str(ROOT / "analysis" / "runs" / "sid_run14.py"), "--all"],
                          capture_output=True, text=True, timeout=120, cwd=str(ROOT))
    assert proc.returncode == 2 and "unknown arguments" in proc.stderr
