"""Resolve any artifact digest to the errata recorded against it.

A frozen preregistration cannot be edited without destroying the record of what was frozen, so
corrections to one live in analysis/errata_C.json. That only works if the correction is
UNAVOIDABLE: anything that resolves a digest must surface its errata too, or a reader follows the
binding straight to the uncorrected text.

Usage:
    python tools/resolve_errata.py                  # scan every artifact and report
    python tools/resolve_errata.py <digest>         # errata for one digest
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ERRATA_FILES = ("errata_C.json",)
DIGEST_KEYS = ("digest", "schedule_class_digest", "benchmark_ladder_digest",
               "eligibility_digest", "selections_digest", "ladder_results_digest",
               "protocol_digest", "target_digest", "supersedes_digest")


def load_errata():
    """digest -> list of errata entries recorded against it."""
    out = {}
    for name in ERRATA_FILES:
        p = ROOT / "analysis" / name
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        out.setdefault(doc["target_digest"], []).extend(
            {**e, "source": name, "target_file": doc["target_file"]} for e in doc["errata"])
    return out


def digests_in(doc, found=None):
    """Every digest value an artifact carries, at any depth."""
    found = set() if found is None else found
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k in DIGEST_KEYS and isinstance(v, str):
                found.add(v)
            else:
                digests_in(v, found)
    elif isinstance(doc, list):
        for v in doc:
            digests_in(v, found)
    return found


def artifacts():
    """Tracked analysis artifacts, plus any reproduction outputs that happen to be present."""
    for p in sorted((ROOT / "analysis").glob("*.json")):
        yield p
    repro = ROOT / "analysis" / "reproduction"
    if repro.is_dir():
        for p in sorted(repro.glob("*.json")):
            yield p
    out = ROOT / "analysis" / "outputs"
    if out.is_dir():
        for p in sorted(out.glob("*.json")):
            yield p


def main(argv):
    errata = load_errata()
    if len(argv) > 1:
        for e in errata.get(argv[1], []):
            print(f"{e['id']}  {e['target_file']}  {e['path']}\n    {e['correction']}")
        if argv[1] not in errata:
            print("no errata recorded against that digest")
        return 0

    affected = 0
    for p in artifacts():
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        hits = digests_in(doc) & set(errata)
        # an errata file naming its own target is bookkeeping, not an affected artifact
        if p.name in ERRATA_FILES:
            continue
        if hits:
            affected += 1
            ids = sorted({e["id"] for d in hits for e in errata[d]})
            print(f"{p.relative_to(ROOT)}  carries {sorted(hits)}  -> errata {ids}")
    print(f"\n{affected} artifact(s) carry a digest with errata recorded against it")
    if not errata:
        print("no errata files found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
