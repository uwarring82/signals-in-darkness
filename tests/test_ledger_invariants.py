"""Invariants the claim ledger must satisfy for the repository to be releasable.

The binding one:

    `result` and `pilot` claims require an existing machine-readable output reference.
    `open` and `withdrawn` claims may carry a documented provenance exception.

A claim asserted as a standing result must be checkable by a reader without contacting the
author, which means its numbers must exist in a file, not only in a run's stdout. A claim that
is open or withdrawn makes no such promise, so it may record that its provenance is
irrecoverable — but it must say so, rather than leaving a dangling pointer.

This file is the executable form of that rule. It would have caught C05, C10 and C24, each of
which stood as `result` while its numbers existed only as printed output.
"""
import os
import re
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_site  # noqa: E402  (path set above)
import pathlib  # noqa: E402

CLAIMS = build_site.load_yaml_list(pathlib.Path(ROOT) / "ledgers" / "status.yaml")
ASSERTED = ("result", "pilot")
EXEMPT = ("open", "withdrawn")
UNREPRODUCED = "[unreproduced-from-file]"


def _referenced_files(claim):
    """Repository-relative paths named in a claim's output field that exist on disk."""
    out = claim.get("output", "") or ""
    found = []
    for token in re.findall(r"[A-Za-z0-9_./-]+\.(?:json|csv|png|svg|yaml)", out):
        if os.path.exists(os.path.join(ROOT, token)):
            found.append(token)
    return found


def test_the_ledger_is_not_empty():
    assert CLAIMS and len(CLAIMS) >= 20


@pytest.mark.parametrize("claim", [c for c in CLAIMS if c.get("status") in ASSERTED],
                         ids=lambda c: c["id"])
def test_asserted_claims_have_a_machine_readable_output(claim):
    """A result or pilot claim must point at a file that exists."""
    assert UNREPRODUCED not in (claim.get("output") or ""), (
        f"{claim['id']} is '{claim['status']}' but its output is marked {UNREPRODUCED}. "
        "Persist the table from its producer, or demote the claim.")
    files = _referenced_files(claim)
    assert files, (
        f"{claim['id']} is '{claim['status']}' but names no existing machine-readable output; "
        f"output field was {claim.get('output')!r}")


@pytest.mark.parametrize("claim", [c for c in CLAIMS if c.get("status") in EXEMPT],
                         ids=lambda c: c["id"])
def test_exempt_claims_document_their_exception(claim):
    """open and withdrawn claims may lack an output, but must say why."""
    out = claim.get("output") or ""
    if UNREPRODUCED in out or not _referenced_files(claim):
        explanation = " ".join(filter(None, (claim.get("errata"), claim.get("reproduced"),
                                             claim.get("note"))))
        assert explanation.strip(), (
            f"{claim['id']} is '{claim['status']}' with no retrievable output and no errata, "
            "reproduced or note field explaining the gap")


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c["id"])
def test_every_named_output_file_exists(claim):
    """No claim may point at a file that is not in the repository."""
    out = claim.get("output") or ""
    for token in re.findall(r"(?:analysis|figures|docs)/[A-Za-z0-9_./-]+\.(?:json|csv|png|svg)", out):
        assert os.path.exists(os.path.join(ROOT, token)), \
            f"{claim['id']} names {token}, which does not exist"


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda c: c["id"])
def test_every_named_producer_exists(claim):
    """A claim's run field must name scripts that are in the repository.

    C24 stood as a result citing 'sid_run6s.py (section 1)' for a table no script in this
    repository computes; the pointer looked plausible because the file existed.
    """
    run = claim.get("run") or ""
    for token in re.findall(r"analysis/runs/[A-Za-z0-9_]+\.py", run):
        assert os.path.exists(os.path.join(ROOT, token)), \
            f"{claim['id']} names producer {token}, which does not exist"


def test_withdrawn_claims_carry_an_errata_pointer():
    for c in CLAIMS:
        if c.get("status") == "withdrawn":
            assert c.get("errata"), f"{c['id']} is withdrawn without an errata pointer"
