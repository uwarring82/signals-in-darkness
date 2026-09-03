"""The published pages must be faithful projections of the ledgers (rule 3).

The generator's original freshness check could not fail: it asserted each page's mtime
was at least its ledger's, having written that page milliseconds earlier in the same
call, and a fresh clone gives every file the checkout time regardless. These tests use
`build_site.py --check`, which re-renders and compares against what is committed, so a
ledger edited without regenerating its projection fails here instead of publishing a
status that contradicts the source of truth.
"""
import os
import pathlib
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_site


def test_committed_pages_match_the_ledgers():
    assert build_site.build(check=True) == 0, \
        "run `python tools/build_site.py` -- a ledger changed without regenerating its projection"


def test_every_withdrawn_claim_publishes_its_errata_pointer():
    """The card's acceptance criterion, read off the generated page rather than the ledger."""
    pages, claims = build_site.render_all("stamp")
    page = pages["status"]
    withdrawn = [c for c in claims if c["status"] == "withdrawn"]
    assert withdrawn, "no withdrawn claims -- this test would be vacuous"
    for c in withdrawn:
        row = [ln for ln in page.splitlines() if ln.startswith(f"| {c['id']} |")]
        assert len(row) == 1
        assert c["errata"] in row[0], c["id"]


def test_render_refuses_a_withdrawn_claim_without_an_errata_pointer(tmp_path, monkeypatch):
    led = tmp_path / "ledgers"
    led.mkdir()
    (led / "status.yaml").write_text(
        "- id: C99\n  statement: something retracted\n  status: withdrawn\n", encoding="utf-8")
    (led / "milestones.yaml").write_text("- date: 2026-09-03\n  summary: x\n", encoding="utf-8")
    (led / "roadmap.yaml").write_text("- id: A\n  title: x\n  state: open\n", encoding="utf-8")
    monkeypatch.setattr(build_site, "ROOT", tmp_path)
    with pytest.raises(AssertionError, match="withdrawn with no errata"):
        build_site.render_all("stamp")


def test_parser_raises_rather_than_dropping_a_line(tmp_path, monkeypatch):
    """A silently dropped line let a reformatted ledger publish a claim under another status."""
    led = tmp_path / "ledgers"
    led.mkdir()
    (led / "status.yaml").write_text(
        '- id: C01\n  statement: fine\n  status: result\n'
        '- "id": C02\n  statement: reformatted header the regex misses\n  status: pilot\n',
        encoding="utf-8")
    monkeypatch.setattr(build_site, "ROOT", tmp_path)
    with pytest.raises(AssertionError, match="unparsed line"):
        build_site.load_yaml_list(led / "status.yaml")


def test_all_three_ledgers_parse_completely():
    for name in ("status", "milestones", "roadmap"):
        rows = build_site.load_yaml_list(pathlib.Path(ROOT) / "ledgers" / f"{name}.yaml")
        assert rows, name
