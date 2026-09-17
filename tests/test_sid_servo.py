"""Baseline tests for analysis/lib/sid_servo.py, the four-outcome law extracted from sid_run7.py §B.

The extraction exists for roadmap D (note 29). Its job here is to reproduce the published baseline
exactly, so that D's correlated work starts from the same arithmetic. sid_run7.py and its artifact
res7B_servo.json are the record and are untouched; these tests hold the module to that artifact.

Nothing here models a correlated phase: this module is the independent-phase baseline, which is the
assumption roadmap D exists to test.
"""
import ast
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "lib"))
import sid_servo as ss  # noqa: E402
from sid_lib import I_ext_exact  # noqa: E402

ARTIFACT_PATH = ROOT / "analysis" / "outputs" / "res7B_servo.json"
STORED = json.loads(ARTIFACT_PATH.read_text())
ARCHIVE_DIGESTS = {   # sha256 of the files this extraction reproduces, pinned at 17 Sept 2026
    "analysis/outputs/res7B_servo.json":
        "10581b505fb7c34cd8bf2c1a044f4f36adf0f275c8fed355d5a5fc5a14f20157",
    "analysis/runs/sid_run7.py":
        "ac1466f4a5eaa9c5e1c7504465a5e0a5c42f8a9da81552f0644bc13156e6227f",
}
C14_KAPPA_5 = (0.6653, 0.8126, 0.6650, 0.8073)     # the row C14's statement rests on


def _kappa(label):
    return math.inf if label == ss.KAPPA_INF else label


@pytest.mark.parametrize("row", STORED, ids=[str(r[0]) for r in STORED])
def test_every_published_row_is_reproduced(row):
    mine = ss.servo_row(_kappa(row[0]))
    assert mine[0] == row[0]
    for got, stored in zip(mine[1:], row[1:]):
        assert got == pytest.approx(stored, rel=1e-10)


def test_the_row_C14_quotes_is_the_one_reproduced():
    row = next(r for r in STORED if r[0] == 5.0)
    for got, quoted in zip(row[1:], C14_KAPPA_5):
        assert got == pytest.approx(quoted, abs=5e-5)
    assert row[2] > 0.8 > row[1], "C_eff > 0.8 at kappa = 5 holds for the four-outcome channel only"


def test_the_two_channels_keep_run7s_different_searches():
    """The variance channel searches every third offset. Losing that would silently change C14."""
    full = ss.offset_grid()
    assert len(full) == 169 and ss.slope_offsets() == full
    assert ss.variance_offsets() == full[::3] and len(ss.variance_offsets()) == 57
    kappa = 5.0
    thinned = max(ss.var_channel(kappa, a, b, full=True) for a, b in ss.variance_offsets())
    complete = max(ss.var_channel(kappa, a, b, full=True) for a, b in full)
    assert complete >= thinned, "a maximum over a superset cannot be smaller"
    assert ss.ceff_from_kl(complete) == pytest.approx(ss.ceff_from_kl(thinned), rel=1e-3)


def test_the_perfect_oscillator_limit_uses_its_closed_form():
    assert ss.von_mises_weights(math.inf) is None
    assert ss.von_mises_weights(5.0).sum() == pytest.approx(1.0, rel=1e-15)
    P = ss.four_outcome(0.0, math.inf, 0.0, 0.0)
    assert sum(P.values()) == pytest.approx(1.0, rel=1e-15)
    # at zero offsets both bits are fully contrasted, so the outcomes factorise
    assert P[(1, 1)] == pytest.approx(0.25 * (1 + ss.CONTRAST) ** 2, rel=1e-12)
    row = next(r for r in STORED if r[0] == ss.KAPPA_INF)
    assert row[2] == pytest.approx(ss.CONTRAST, rel=1e-6)          # full channel reaches C2
    assert row[1] == pytest.approx(ss.CONTRAST ** 2, rel=1e-6)     # parity only reaches C1 C2


def test_probabilities_parity_and_divergence_behave():
    P = ss.four_outcome(0.1, 2.0, 0.3, 0.7)
    assert sum(P.values()) == pytest.approx(1.0, rel=1e-14) and min(P.values()) > 0
    par = ss.parity(P)
    assert sum(par.values()) == pytest.approx(1.0, rel=1e-14)
    assert ss.kl(P, P) == pytest.approx(0.0, abs=1e-15)
    assert ss.kl(P, ss.four_outcome(0.0, 2.0, 0.3, 0.7)) > 0


def test_fisher_is_converged_in_its_difference_step():
    coarse = ss.fisher(5.0, 0.4, 0.9, full=True, d=1e-4)
    fine = ss.fisher(5.0, 0.4, 0.9, full=True, d=1e-5)
    assert coarse == pytest.approx(fine, rel=1e-6)
    assert ss.fisher(5.0, 0.4, 0.9, full=True) >= ss.fisher(5.0, 0.4, 0.9, full=False)


def test_effective_contrast_inverts_the_binary_link():
    for c in (0.2, 0.5, 0.85):
        assert ss.ceff_from_kl(I_ext_exact(c, math.sqrt(ss.SSQ))) == pytest.approx(c, rel=1e-6)
    assert ss.ceff_from_kl(1e3) == 1.0                       # saturates rather than raising


def test_the_extraction_models_an_independent_phase_and_leaves_run7_alone():
    source = (ROOT / "analysis" / "lib" / "sid_servo.py").read_text()
    tree = ast.parse(source)
    imports = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert not any("run7" in name for name in imports), "the library must not import a run script"
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "rho" not in names, "this module is the independent-phase baseline; D adds correlation"
    # Pinned digests, not a comparison with HEAD: comparing with HEAD detects only uncommitted
    # edits and would accept a committed alteration of the archive, which is what this guard exists
    # to prevent (review, 17 Sept 2026).
    for tracked, digest in ARCHIVE_DIGESTS.items():
        assert hashlib.sha256((ROOT / tracked).read_bytes()).hexdigest() == digest, \
            f"{tracked} is not the archived file this extraction was checked against"
    run7 = (ROOT / "analysis" / "runs" / "sid_run7.py").read_text()
    assert "def four_outcome" in run7, "run7 keeps its own copy; the extraction does not replace it"
