"""Note 27: distinguish the archived C08 defect from the corrected fit.

The archive producer remains reproducible. It is an explicit negative control for
the lag-one contract, never evidence that the contract passes.
"""
import hashlib
import math
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'analysis/diagnostics'))
from review_F_plan import (assert_lag_one, comparators, filter_factor,
                           run3_map_parameters, run4_kernels)


@pytest.mark.parametrize('u,v', [(0.1, 0.15), (0.3, 0.35), (1.0, 1.05)])
def test_lag_one_guard_rejects_archived_map_and_accepts_run4_fit(u, v):
    C, s = 0.4, 0.5
    F, phi = filter_factor(u), math.exp(-v)
    r1 = C*C*math.exp(-s*s)*math.sinh(s*s*F*phi)
    rho, a = run3_map_parameters(C, s, F, phi)
    assert rho*a == pytest.approx(r1/F, rel=1e-12)
    with pytest.raises(AssertionError):
        assert_lag_one(rho, a, r1)
    fit = run4_kernels()
    fit['gp_rate_geom'] = lambda rho, a: (rho, a)
    assert_lag_one(*fit['gp_rate_geomfit'](C, s, F, phi), r1)


def test_point_sampling_cannot_expose_the_map_fold_defect():
    C, s, phi = 0.4, 0.5, math.exp(-0.05)
    r1 = C*C*math.exp(-s*s)*math.sinh(s*s*phi)
    assert_lag_one(*run3_map_parameters(C, s, 1.0, phi), r1)
    K = comparators(C, s, 0.0, 0.05)
    assert K['K3'] == pytest.approx(K['K2'], rel=1e-12)
    assert K['K1'] == K['K4']


def test_e6_does_not_force_either_comparator_to_fail_at_five_percent():
    K = comparators(.4, 1., .3, .35)
    assert .05 < K['K2']/K['K1']-1 < .06
    # A possible narrow reference interval: both comparator intervals validate.
    lo, hi = 1.0299*K['K1'], 1.0301*K['K1']
    for key in ('K1', 'K2'):
        assert .95 < K[key]/hi < K[key]/lo < 1.05


def test_point_sampled_equivalence_is_not_uniform_over_the_stress_set():
    K = comparators(.4, 1., 1., 1.05)
    assert .05 < K['K3']/K['K4']-1 < .06


@pytest.mark.parametrize('s,u,v', [(.5, .1, .15), (.5, .3, .35),
                                  (1., 1., 1.05), (1., .3, .35)])
def test_deterministic_series_is_converged_at_the_proposed_stress_points(s, u, v):
    ns = run4_kernels()
    F, phi = filter_factor(u), math.exp(-v)
    coarse = ns['gp_rate_series'](.4, s, F, phi)[0]
    ns['W'] = np.pi*(np.arange(4096)+.5)/4096
    d = ns['spectrum_series'](.4, s, F, phi, M=12)
    fine = .5*np.mean(d-np.log1p(d))
    assert coarse == pytest.approx(fine, rel=1e-6, abs=0)


def test_erratum_leaves_the_tagged_card_intact():
    assert hashlib.sha256((ROOT / 'cards/v2.0-frozen.md').read_bytes()).hexdigest() == (
        '682560ba2cce9209b6996de34c108a79e49f5ba5f4f0d9f17bcb84349ad805da')
