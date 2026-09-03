#!/usr/bin/env python3
"""Generate docs/status.md, docs/milestones.md, docs/roadmap.md from ledgers/.

The ledgers are the one machine-readable source of truth (rule 3); these pages are
projections of them and are never edited by hand. Every transformation asserts its own
postcondition (rule 6).

Usage:
    python tools/build_site.py            # regenerate the pages
    python tools/build_site.py --check    # verify the committed pages match the ledgers

--check re-renders and compares against what is committed, ignoring only the generation
timestamp, and exits nonzero on any drift. It replaces an mtime comparison that could
never fail: the old check asserted that each page was newer than its ledger, having
written that page milliseconds earlier in the same call, and after a fresh clone all
files carry the checkout time anyway. --check is the form that works on a clean checkout
and is exercised by tests/test_site_projection.py.
"""
import datetime
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATUSES = {'result', 'pilot', 'open', 'withdrawn'}
STAMP = re.compile(r'^Generated .* from .*\. Do not edit\.$', re.M)


def load_yaml_list(path):
    """Minimal parser for the flat '- key: value' lists in ledgers/ (no dependency).

    Raises on any line it cannot account for: silently dropping a line would let a
    reformatted ledger publish a claim under the wrong status.
    """
    items, cur = [], None
    for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        m = re.match(r'^- (\w+): (.*)$', line)
        if m:
            cur = {m.group(1): m.group(2)}
            items.append(cur)
            continue
        m = re.match(r'^  (\w+): (.*)$', line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2)
            continue
        raise AssertionError(f'{path.name}:{lineno}: unparsed line -> {line!r}')
    n_items = sum(1 for ln in path.read_text(encoding='utf-8').splitlines()
                  if re.match(r'^- \w+: ', ln))
    assert len(items) == n_items, f'{path.name}: parsed {len(items)} items, file declares {n_items}'
    return items


def render_status(claims, stamp):
    out = [f'# Current status\n\nGenerated {stamp} from ledgers/status.yaml. Do not edit.\n',
           '| id | status | statement | note | errata / supersedes |',
           '|---|---|---|---|---|']
    for c in claims:
        pointer = '; '.join(p for p in (c.get('errata', ''), c.get('supersedes', '')) if p)
        out.append(f"| {c['id']} | {c['status']} | {c['statement']} | {c.get('note','')} | {pointer} |")
    return '\n'.join(out) + '\n'


def render_table(name, rows, stamp):
    keys = list(rows[0].keys())
    out = [f'# {name.capitalize()}\n\nGenerated {stamp} from ledgers/{name}.yaml. Do not edit.\n',
           '| ' + ' | '.join(keys) + ' |', '|' + '---|' * len(keys)]
    out += ['| ' + ' | '.join(r.get(k, '') for k in keys) + ' |' for r in rows]
    return '\n'.join(out) + '\n'


def render_all(stamp):
    claims = load_yaml_list(ROOT / 'ledgers' / 'status.yaml')
    assert claims, 'empty status ledger'
    bad = [c['id'] for c in claims if c.get('status') not in STATUSES]
    assert not bad, f'bad status on {bad}'
    pages = {'status': render_status(claims, stamp)}
    for name in ('milestones', 'roadmap'):
        rows = load_yaml_list(ROOT / 'ledgers' / f'{name}.yaml')
        assert rows, f'empty {name}'
        pages[name] = render_table(name, rows, stamp)

    # Postconditions on the projection itself, row by row rather than by substring.
    txt = pages['status']
    for c in claims:
        row = [ln for ln in txt.splitlines() if ln.startswith(f"| {c['id']} |")]
        assert len(row) == 1, f"postcondition: {c['id']} appears {len(row)} times"
        assert f"| {c['status']} |" in row[0], f"postcondition: {c['id']} published under the wrong status"
        # the card's acceptance criterion, made executable
        if c['status'] == 'withdrawn':
            assert c.get('errata'), f"{c['id']} is withdrawn with no errata pointer in the ledger"
            assert c['errata'] in row[0], f"postcondition: {c['id']}'s errata pointer was dropped"
    return pages, claims


def build(check=False):
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    pages, claims = render_all(stamp)
    if check:
        drift = []
        for name, text in pages.items():
            path = ROOT / 'docs' / f'{name}.md'
            if not path.exists():
                drift.append(f'{name}.md is missing')
                continue
            live = STAMP.sub('', path.read_text(encoding='utf-8'))
            if STAMP.sub('', text) != live:
                drift.append(f'{name}.md does not match ledgers/{name}.yaml')
        if drift:
            print('site projection is stale:', '; '.join(drift), file=sys.stderr)
            return 1
        print('site projection is current:', len(claims), 'claims')
        return 0
    for name, text in pages.items():
        (ROOT / 'docs' / f'{name}.md').write_text(text, encoding='utf-8')
    print('site pages built:', len(claims), 'claims')
    return 0


if __name__ == '__main__':
    sys.exit(build(check='--check' in sys.argv))
