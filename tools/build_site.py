#!/usr/bin/env python3
"""Generate docs/status.md, docs/milestones.md, docs/roadmap.md from ledgers/. Asserts its own postconditions.
Freshness: a generated page must not be older than the ledger it projects; the build fails otherwise."""
import sys, os, re, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
def load_yaml_list(path):
    # minimal parser for the flat '- key: value' lists used in ledgers/ (no external dependency)
    items, cur = [], None
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        m = re.match(r'^- (\w+): (.*)$', line)
        if m: cur = {m.group(1): m.group(2)}; items.append(cur); continue
        m = re.match(r'^  (\w+): (.*)$', line)
        if m and cur is not None: cur[m.group(1)] = m.group(2)
    return items
def build():
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    claims = load_yaml_list(ROOT/'ledgers'/'status.yaml')
    assert claims and all('status' in c and c['status'] in {'result','pilot','open','withdrawn'} for c in claims), 'bad status ledger'
    out = [f'# Current status\n\nGenerated {stamp} from ledgers/status.yaml. Do not edit.\n', '| id | status | statement | note |', '|---|---|---|---|']
    out += [f"| {c['id']} | {c['status']} | {c['statement']} | {c.get('note','')} |" for c in claims]
    (ROOT/'docs'/'status.md').write_text('\n'.join(out)+'\n')
    for name in ('milestones','roadmap'):
        rows = load_yaml_list(ROOT/'ledgers'/f'{name}.yaml'); assert rows, f'empty {name}'
        keys = [k for k in rows[0].keys()]
        out = [f'# {name.capitalize()}\n\nGenerated {stamp} from ledgers/{name}.yaml. Do not edit.\n', '| '+' | '.join(keys)+' |', '|'+'---|'*len(keys)]
        out += ['| '+' | '.join(r.get(k,'') for k in keys)+' |' for r in rows]
        (ROOT/'docs'/f'{name}.md').write_text('\n'.join(out)+'\n')
    # postconditions: every claim id appears in status page; freshness
    txt = (ROOT/'docs'/'status.md').read_text()
    assert all(c['id'] in txt for c in claims), 'postcondition: missing claim id'
    for name in ('status','milestones','roadmap'):
        assert (ROOT/'docs'/f'{name}.md').stat().st_mtime >= (ROOT/'ledgers'/f'{name}.yaml').stat().st_mtime, f'freshness: {name}'
    print('site pages built:', len(claims), 'claims')
if __name__ == '__main__':
    build()
