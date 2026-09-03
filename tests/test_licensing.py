"""Licensing declarations must stay consistent with the files they describe.

The repository is Apache-2.0 for code and CC-BY-4.0 for the evidence record. That split
is declared in REUSE.toml, because CITATION.cff cannot express it: CFF reads a list of
licences as OR over the whole cited work. These tests guard the two ways that
arrangement can silently rot -- a stubbed field that invalidates the citation record,
and the one deliberate duplicate licence text drifting from its original.
"""
import os

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), "rb") as fh:
        return fh.read()


def test_root_license_and_reuse_copy_are_identical():
    """LICENSES/Apache-2.0.txt exists for REUSE; LICENSE exists for GitHub detection."""
    assert _read("LICENSE") == _read("LICENSES", "Apache-2.0.txt")


def test_both_licence_texts_are_present_and_named_by_spdx_id():
    for name in ("Apache-2.0.txt", "CC-BY-4.0.txt"):
        assert os.path.exists(os.path.join(ROOT, "LICENSES", name)), name


def test_reuse_declares_both_licences_and_parses():
    # tomllib is stdlib from 3.11; environment.yml pins 3.12, but the suite must still
    # run on an older interpreter rather than erroring at collection.
    tomllib = pytest.importorskip("tomllib", reason="python < 3.11 and tomli absent")
    with open(os.path.join(ROOT, "REUSE.toml"), "rb") as fh:
        data = tomllib.load(fh)
    ids = {a["SPDX-License-Identifier"] for a in data["annotations"]}
    assert ids == {"Apache-2.0", "CC-BY-4.0"}, ids
    covered = {p for a in data["annotations"] for p in a["path"]}
    for expected in ("analysis/lib/**", "analysis/outputs/**", "notes/**", "tests/**"):
        assert expected in covered, expected


def test_citation_cff_carries_no_placeholder_and_no_license_field():
    """A stubbed orcid invalidates the whole CFF record; a license field would misstate it."""
    text = _read("CITATION.cff").decode()
    live = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert not any("TODO" in ln for ln in live), "placeholder left in a live CITATION.cff field"
    assert not any(ln.startswith("license:") for ln in live), \
        "CFF reads multiple licences as OR; the split is declared in REUSE.toml instead"


def test_citation_cff_validates():
    cffconvert = pytest.importorskip("cffconvert.cli.create_citation",
                                     reason="cffconvert not installed")
    cffconvert.create_citation(os.path.join(ROOT, "CITATION.cff"), None).validate()
