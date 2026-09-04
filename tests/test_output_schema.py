"""Every stored output must be strict JSON, and null must mean only "undefined".

RFC 8259 has no NaN or Infinity. Python's json module emits and accepts them by default,
which is why res1_core.json (four NaN) and res7B_servo.json (one Infinity) sat in the
archive as invalid JSON: node's JSON.parse rejects both, while jq happens to be lenient.
The FAIR matrix promises retrievable, interoperable open formats, so a file only a Python
reader can load does not satisfy it.

These tests read the raw bytes rather than a parsed object, because json.load() would
silently accept the very tokens under test.
"""
import glob
import json
import math
import os

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUTPUTS = sorted(glob.glob(os.path.join(ROOT, "analysis", "outputs", "*.json")))

# Documented in analysis/outputs/SCHEMA.md. Every null in the archive must be one of these,
# written out rather than derived from the file: an expectation computed from the data
# under test cannot fail (rule 4). EXPECTED_SHAPE pins the row counts these positions assume.
EXPECTED_NULLS = {
    # F: mid-fringe delay mean and s.e., undefined at tau_c/c = 20 and 1 where no run
    # reached the threshold within the cap
    "res1_core.json": {("F", 0, 8), ("F", 0, 9), ("F", 1, 8), ("F", 1, 9)},
    # res7B_servo.json has no nulls: its infinite coherence is a known limiting case and
    # carries the sentinel string instead (see test_known_limiting_case_uses_the_sentinel)
    "res7B_servo.json": set(),
    # res2_partial.json has no nulls since the 4 Sept 2026 adoption: it is now the direct
    # output of sid_run2.py rather than a hand reconstruction with three unstored columns.
    "res2_partial.json": set(),
    # the last two comparator rows are C = 0.99 at s = 0.5 and 1.0, where no crossover exists:
    # the mid-fringe rate never overtakes the extremum on the grid, so the value is genuinely
    # absent rather than unmeasured. Claim C05 states exactly this.
    "res3_comparator.json": {("comparator_crossover", 18, 3), ("comparator_crossover", 18, 4),
                             ("comparator_crossover", 19, 3), ("comparator_crossover", 19, 4)},
    # the extremum policy has no correlation time, so its tau_c/c cell is not applicable
    "res5_calibration.json": {("calibration", 0, 1)},
}

EXPECTED_SHAPE = {
    "res1_core.json": lambda d: len(d["F"]) == 2,
    "res7B_servo.json": lambda d: len(d) == 8,
    "res2_partial.json": lambda d: (len(d["B2"]) == 7 and len(d["B2"][0]) == 10
                                    and set(d) == {"B2", "C2", "F2", "crossover", "extremum_bonus",
                                                   "extremum_bonus_fields", "extremum_bonus_design"}),
    "res5_calibration.json": lambda d: len(d["calibration"]) == 4 and len(d["delays"]) == 3,
    "res3_comparator.json": lambda d: (len(d["comparator_crossover"]) == 20
                                       and len(d["comparator_crossover"][0]) == 6),
}


def _null_positions(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _null_positions(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _null_positions(v, path + (i,))
    elif obj is None:
        yield path


def test_outputs_exist():
    assert OUTPUTS, "no stored outputs found"


@pytest.mark.parametrize("path", OUTPUTS, ids=lambda p: os.path.basename(p))
def test_no_non_finite_tokens_in_the_raw_file(path):
    raw = open(path, encoding="utf-8").read()
    for token in ("NaN", "Infinity", "-Infinity"):
        assert token not in raw, f"{os.path.basename(path)} contains the JSON-invalid token {token}"


@pytest.mark.parametrize("path", OUTPUTS, ids=lambda p: os.path.basename(p))
def test_round_trips_through_a_conforming_serialiser(path):
    """json.dumps(..., allow_nan=False) is the strictness a conforming parser applies."""
    obj = json.loads(open(path, encoding="utf-8").read(), parse_constant=_reject)
    json.dumps(obj, allow_nan=False)


def _reject(name):
    raise AssertionError(f"non-finite constant {name!r} in a stored output")


@pytest.mark.parametrize("path", OUTPUTS, ids=lambda p: os.path.basename(p))
def test_every_null_is_a_documented_undefined_value(path):
    """A null that SCHEMA.md does not account for is an undeclared hole in the record."""
    name = os.path.basename(path)
    obj = json.loads(open(path, encoding="utf-8").read())
    shape = EXPECTED_SHAPE.get(name)
    if shape is not None:
        assert shape(obj), f"{name}: row count changed; the declared null positions no longer apply"
    found = set(_null_positions(obj))
    expected = EXPECTED_NULLS.get(name, set())
    assert found == expected, (
        f"{name}: nulls {sorted(map(str, found))} but SCHEMA.md declares "
        f"{sorted(map(str, expected))}")


@pytest.mark.parametrize("path", OUTPUTS, ids=lambda p: os.path.basename(p))
def test_no_parsed_value_is_non_finite(path):
    obj = json.loads(open(path, encoding="utf-8").read())
    bad = []

    def walk(x, p=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{p}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")
        elif isinstance(x, float) and not math.isfinite(x):
            bad.append((p, x))

    walk(obj)
    assert not bad, f"{os.path.basename(path)}: non-finite values at {bad}"


def test_known_limiting_case_uses_the_sentinel_not_null():
    """kappa -> infinity is a value the calculation visited, not an absent one.

    null would claim the perfect-oscillator row has no coherence value; the sentinel says it
    has one and names it. The distinction is the whole point of the convention, so it is
    asserted on the column rather than left to prose.
    """
    rows = json.loads(open(os.path.join(ROOT, "analysis", "outputs", "res7B_servo.json"),
                           encoding="utf-8").read())
    assert len(rows) == 8
    kappas = [r[0] for r in rows]
    assert kappas[-1] == "positive-infinity", kappas[-1]
    assert all(isinstance(k, (int, float)) for k in kappas[:-1]), kappas[:-1]
    assert kappas[:-1] == sorted(kappas[:-1]), "finite coherences should be ascending"
    assert None not in kappas, "an infinite limit must not be written as null"


def test_schema_documents_the_sentinel_and_the_null_rule_separately():
    text = open(os.path.join(ROOT, "analysis", "outputs", "SCHEMA.md"), encoding="utf-8").read()
    assert "positive-infinity" in text
    assert "undefined, missing, or not applicable" in text


def test_schema_documents_the_representation_rule():
    text = open(os.path.join(ROOT, "analysis", "outputs", "SCHEMA.md"), encoding="utf-8").read()
    assert "strict JSON" in text and "null" in text, "SCHEMA.md must state the null convention"
