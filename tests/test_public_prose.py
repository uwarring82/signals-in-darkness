"""The hand-written public pages are views over the ledger, and must not drift from it.

docs/status.md, roadmap.md and milestones.md are generated and are checked by
tests/test_site_projection.py. This file covers the pages a human writes: docs/index.md and
docs/where-we-are.md. The rule they inherit from the notebook contract is the same one --
claim identifiers and statuses are checked against ledgers/status.yaml, and no page becomes a
second source of truth for a number.
"""
import os
import re
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DOCS = os.path.join(ROOT, "docs")
PROSE = ("index.md", "where-we-are.md")
sys.path.insert(0, os.path.join(ROOT, "tools"))

CLAIM = re.compile(r"\bC\d{2}\b")
STATUSES = ("result", "pilot", "open", "withdrawn")


def _ledger():
    import pathlib

    import build_site
    return {c["id"]: c["status"]
            for c in build_site.load_yaml_list(pathlib.Path(ROOT) / "ledgers" / "status.yaml")}


def _text(name):
    with open(os.path.join(DOCS, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("name", PROSE)
def test_page_exists_and_is_not_a_stub(name):
    body = _text(name)
    assert len(body) > 1500, f"{name} is too short to be the page it claims to be"
    assert "Site stub" not in body


@pytest.mark.parametrize("name", PROSE)
def test_every_claim_id_mentioned_is_in_the_ledger(name):
    ledger = _ledger()
    for cid in sorted(set(CLAIM.findall(_text(name)))):
        assert cid in ledger, f"{name} cites {cid}, which is not in ledgers/status.yaml"


def test_claims_described_as_established_are_actually_results():
    """The 'What is established' section may only name claims the ledger calls `result`."""
    ledger = _ledger()
    body = _text("where-we-are.md")
    section = body.split("## What is established")[1].split("## What was corrected")[0]
    named = sorted(set(CLAIM.findall(section)))
    assert named, "the established section names no claims"
    for cid in named:
        assert ledger[cid] == "result", (
            f"where-we-are.md presents {cid} as established, but the ledger says {ledger[cid]}")


def test_claims_described_as_withdrawn_are_actually_withdrawn():
    ledger = _ledger()
    section = _text("where-we-are.md").split("## What was corrected or withdrawn")[1] \
                                      .split("## What remains open")[0]
    # every claim named as a withdrawal in the bullet list, excluding its replacements
    withdrawn_named = {cid for cid in CLAIM.findall(section) if ledger[cid] == "withdrawn"}
    assert withdrawn_named, "the corrections section names no withdrawn claim"
    actually = {cid for cid, st in ledger.items() if st == "withdrawn"}
    missing = actually - set(CLAIM.findall(section))
    assert not missing, f"withdrawn claims absent from the public corrections section: {sorted(missing)}"


def test_the_withdrawn_count_stated_in_prose_matches_the_ledger():
    """A count stated in prose must agree with the record that owns it.

    Matched on explicit count phrases rather than by substring: "none of them" contains
    "one of them", and a check that cannot tell those apart is worse than no check.
    """
    ledger = _ledger()
    n = sum(1 for st in ledger.values() if st == "withdrawn")
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
             8: "eight", 9: "nine", 10: "ten"}
    patterns = (r"\b(\w+) claims are `withdrawn`", r"there are (\w+) of them")
    found = 0
    for name in PROSE:
        body = _text(name)
        for pat in patterns:
            for stated in re.findall(pat, body, flags=re.I):
                found += 1
                assert stated.lower() == words[n], (
                    f"{name} states '{stated}' withdrawn claims; the ledger has {n}")
    assert found, "no page states the withdrawn count; the claim-count check is inert"


@pytest.mark.parametrize("name", PROSE)
def test_the_non_canonical_draft_is_not_linked(name):
    """The companion introduction predates the attribution boundary and describes settled
    results as proposed. It must not be reachable from the public pages."""
    body = _text(name)
    assert "plain-language-introduction-v2-draft-NOT-CANONICAL.md](" not in body, \
        f"{name} links the NOT CANONICAL draft"
    assert "(plain-language-introduction" not in body


@pytest.mark.parametrize("name", PROSE)
def test_internal_links_resolve(name):
    body = _text(name)
    for target in re.findall(r"\]\((?!https?:)([^)#]+)[^)]*\)", body):
        path = os.path.normpath(os.path.join(DOCS, target))
        assert os.path.exists(path), f"{name} links {target}, which does not exist"


def test_the_front_page_routes_to_the_tutorial_and_the_status_page():
    body = _text("index.md")
    assert "where-we-are.md" in body, "the front page does not link the plain-language status"
    assert "00_how_many_coin_tosses.ipynb" in body
    assert "01_when_the_coin_has_memory.ipynb" in body
    for generated in ("status.md", "roadmap.md", "milestones.md", "reproduce.md", "feedback.md"):
        assert generated in body, f"the front page does not link {generated}"


def test_the_lessons_section_is_present_and_specific():
    """The lessons are earned findings, not generic advice; each must be traceable."""
    body = _text("where-we-are.md")
    section = body.split("## Lessons from the work")[1].split("## Where to go next")[0]
    for phrase in ("skipped check", "provenance", "documented route",
                   "optimiser starts", "Zero information"):
        assert phrase.lower() in section.lower(), f"the lessons section is missing: {phrase}"
