"""Contract tests for analysis/runs/sid_run14.py, the corrected mid-fringe map (note 27 §1).

The archived producer and artifact are the historical record and stay untouched;
tests/test_c08_fold_provenance.py pins the archived defect as a negative control. These tests check
that the new producer computes run3's own map, differs from it only in the lag-one normalisation,
and writes nowhere near the archive.
"""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "runs"))
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
sys.path.insert(0, str(ROOT / "analysis" / "diagnostics"))
import sid_run14 as r14  # noqa: E402
from review_F_plan import filter_factor, run4_kernels  # noqa: E402
from sid_lib import gp_rate_geom  # noqa: E402

ARCHIVE_PATH = ROOT / "analysis" / "outputs" / "res3_comparator.json"
ARCHIVE = json.loads(ARCHIVE_PATH.read_text())
STORED = {round(c0, 4): thr for c0, thr in ARCHIVE["tau_optimised_threshold"]}


def test_the_grid_is_run3s_own_grid_not_a_retyped_one():
    grid = r14.run3_grid()
    stored = ARCHIVE["tau_optimised_grid"]
    assert np.array_equal(grid["C0s"], np.array(stored["C0"]))
    assert np.array_equal(grid["tcs"], np.array(stored["tau_c_over_t_dead"]))
    assert grid["T2"] == stored["T2_over_t_dead"]
    assert grid["gs"] * grid["T2"] == stored["g_sigma_x_T2"]
    assert len(grid["taus"]) == 160


def test_vectorised_geometric_rate_equals_the_committed_scalar():
    rng = np.random.default_rng(0)
    rho, a = rng.uniform(1e-6, 0.5, 500), rng.uniform(0.01, 0.999, 500)
    np.testing.assert_array_equal(r14.geometric_rate(rho, a),
                                  np.array([gp_rate_geom(p, q) for p, q in zip(rho, a)]))


@pytest.mark.parametrize("C,s,u,c", [(0.4, 0.5, 0.3, 0.35), (0.4, 1.0, 1.0, 1.05), (0.9, 0.1, 0.01, 0.02)])
def test_series_kernel_reproduces_run4s_kernel(C, s, u, c):
    F, phi = filter_factor(u), math.exp(-c)
    d = C * C * r14.series_kernel(np.array([s * s]), np.array([F * phi]), np.array([phi]))[0]
    rate = 0.5 * np.mean(d - np.log1p(d))
    assert rate == pytest.approx(run4_kernels()["gp_rate_series"](C, s, F, phi)[0], rel=1e-12)


def test_series_kernel_avoids_an_overflow_a_kernel_written_in_F_alone_would_hit():
    """On run3's own grid F and phi are both representable, but the series prefactor (s^2 F)^11 is
    not: the kernel has to be written in a1 = F phi."""
    grid = r14.run3_grid()
    tc, tau = float(grid["tcs"].min()), float(grid["taus"].max())
    u, c = tau / tc, tau + grid["td"]
    F = (math.cosh(u) - 1) / (u - 1 + math.exp(-u))
    phi = math.exp(-c / tc)
    s2 = grid["gs"] ** 2 * 2 * (tc * tau - tc * tc * (1 - math.exp(-u)))
    assert math.isfinite(F) and F > 1e100 and 0 < phi < 1e-100
    with np.errstate(over="ignore"):
        assert not np.isfinite(np.float64(s2 * F) ** 11)          # the form that overflowed
    assert 0 < s2 * F * phi < 1e-3                                # the form the kernel uses
    assert np.all(np.isfinite(r14.series_kernel(np.array([s2]), np.array([F * phi]), np.array([phi]))))
    dead = r14.series_kernel(np.array([0.015]), np.array([0.0]), np.array([0.0]))
    assert np.all(np.isfinite(dead)) and np.max(np.abs(dead)) == 0.0


def test_the_correction_is_exactly_the_lag_one_normalisation():
    contract = r14.lag_one_contract()
    assert contract["fit_matches_r1"] and not contract["archived_matches_r1"]
    F = filter_factor(contract["point"]["u"])
    assert contract["archived_first_lag"] == pytest.approx(contract["exact_r1"] / F, rel=1e-12)
    assert F > 1.0


@pytest.mark.parametrize("target", [0.4, 0.5])
def test_both_forms_reproduce_the_committed_threshold_in_a_full_resolution_column(target):
    """Note 27: the corrected fit's first crossings on the committed grid equal the stored values."""
    grid = r14.run3_grid()
    column = int(np.argmin(abs(grid["C0s"] - target)))
    C0s, tcs, maps = r14.map_over_grid(grid, c0_columns=[column])
    stored = STORED[round(float(C0s[0]), 4)]
    for form in ("archived", "fit"):
        won = np.flatnonzero(maps[form]["win"][:, 0] > 0)
        assert len(won), f"{form} never wins in the {target} column"
        assert float(tcs[won[0]]) == pytest.approx(stored, rel=1e-12), form


def test_the_producer_writes_only_to_reproduction_and_leaves_the_archive_alone(tmp_path):
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
