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


# ---- CITATION.cff is canonical for the fields both records share ----

def _records():
    import json
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed")
    cff = yaml.safe_load(_read("CITATION.cff").decode())
    cm = json.loads(_read("codemeta.json").decode())
    return cff, cm


@pytest.mark.parametrize("field", ["title", "affiliation", "keywords", "version",
                                   "date", "repository"])
def test_codemeta_agrees_with_citation_cff(field):
    """Two machine-readable records disagreeing is a parallel source (rule 3)."""
    cff, cm = _records()
    got = {
        "title": (cff["title"], cm["name"]),
        "affiliation": (cff["authors"][0]["affiliation"], cm["author"][0]["affiliation"]),
        "keywords": (cff["keywords"], cm["keywords"]),
        "version": (cff["version"], cm["version"]),
        "date": (cff["date-released"], cm["datePublished"]),
        "repository": (cff["repository-code"], cm["codeRepository"]),
    }[field]
    assert got[0] == got[1], f"{field}: CITATION.cff has {got[0]!r}, codemeta.json has {got[1]!r}"


def test_pinned_dependencies_agree_between_environment_and_requirements():
    """A pin present in one file and absent or different in the other is not reproducible."""
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed")
    env = yaml.safe_load(_read("environment.yml").decode())
    conda = dict(d.split("=", 1) for d in env["dependencies"] if isinstance(d, str) and "=" in d)
    req = dict(line.strip().split("==", 1) for line in _read("requirements.txt").decode().splitlines()
               if "==" in line)
    assert req, "requirements.txt pins nothing"
    for pkg, version in req.items():
        assert pkg in conda, f"{pkg} pinned in requirements.txt but absent from environment.yml"
        assert conda[pkg] == version, f"{pkg}: environment.yml={conda[pkg]}, requirements.txt={version}"
    for pkg in conda:
        if pkg == "python":
            continue
        assert pkg in req, f"{pkg} pinned in environment.yml but absent from requirements.txt"
    assert all("=" in d for d in env["dependencies"] if isinstance(d, str)), \
        "every conda dependency must carry a version pin"
