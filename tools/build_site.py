#!/usr/bin/env python3
"""Generate the public GitHub Pages views from the evidence record.

The ledgers are the one machine-readable source of truth for status (rule 3), and the
committed notebooks are the source for the rendered tutorials. Generated pages are never
edited by hand. Every transformation asserts its own postcondition (rule 6).

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
import base64
import datetime
import hashlib
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATUSES = {'result', 'pilot', 'open', 'withdrawn'}
STAMP = re.compile(r'^Generated .* from .*\. Do not edit\.$', re.M)
REPOSITORY_URL = 'https://github.com/uwarring82/signals-in-darkness'

TUTORIALS = (
    {
        'source': '00_how_many_coin_tosses.ipynb',
        'slug': '00-how-many-coin-tosses',
        'question': 'How many tosses does it take to notice that a coin changed?',
        'summary': ('Start with independent yes-or-no observations. Compare a fixed test with a '
                    'sequential alarm, then see why the answer depends on which delay you mean '
                    'and what kind of change is held fixed.'),
    },
    {
        'source': '01_when_the_coin_has_memory.ipynb',
        'slug': '01-when-the-coin-has-memory',
        'question': 'What changes when the coin remembers its previous tosses?',
        'summary': ('Two records can have the same number of heads and different ordering. This '
                    'tutorial shows how correlation becomes evidence, why count-only power can '
                    'plateau, and how the two sensor readouts acquire different strengths.'),
    },
)


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


def _cell_text(value):
    """Notebook text fields may be one string or a list of strings."""
    return value if isinstance(value, str) else ''.join(value or [])


def _title_from_notebook(notebook, fallback):
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') != 'markdown':
            continue
        match = re.search(r'^#\s+(.+)$', _cell_text(cell.get('source')), flags=re.M)
        if match:
            return match.group(1).strip()
    return fallback


def _rewrite_notebook_links(markdown, source_name):
    """Route notebook links outside docs/ to the corresponding repository file."""
    source_dir = pathlib.PurePosixPath('tutorials')

    def replace(match):
        target = match.group(1)
        if not target.startswith('../'):
            return match.group(0)
        path = source_dir.joinpath(target)
        # PurePath does not collapse '..', and importing posixpath solely for this is needless.
        parts = []
        for part in path.parts:
            if part == '..':
                if parts:
                    parts.pop()
            elif part != '.':
                parts.append(part)
        return '](' + REPOSITORY_URL + '/blob/main/' + '/'.join(parts) + ')'

    return re.sub(r'\]\((\.\./[^)]+)\)', replace, markdown)


def _render_output(output, asset_name, cell_number):
    """Return (HTML/Markdown fragment, optional PNG bytes) for one committed output."""
    kind = output.get('output_type')
    if kind == 'error':
        raise AssertionError(f'notebook cell {cell_number} contains a committed error output')
    if kind == 'stream':
        text = _cell_text(output.get('text')).rstrip()
        fragment = (f'<div class="tutorial-output" aria-label="Calculation output">\n'
                    f'<span class="output-label">Output</span>\n'
                    f'<pre><code>{html.escape(text)}</code></pre>\n</div>')
        return fragment, None
    if kind in ('display_data', 'execute_result'):
        data = output.get('data') or {}
        if 'image/png' in data:
            raw = base64.b64decode(_cell_text(data['image/png']))
            fragment = (
                '<figure class="tutorial-figure">\n'
                f'  <img src="{{{{ \'/assets/tutorials/{asset_name}\' | relative_url }}}}" '
                f'alt="Figure produced by calculation {cell_number}">\n'
                f'  <figcaption>Committed output from calculation {cell_number}.</figcaption>\n'
                '</figure>'
            )
            return fragment, raw
        if 'text/plain' in data:
            text = _cell_text(data['text/plain']).rstrip()
            fragment = (f'<div class="tutorial-output" aria-label="Calculation output">\n'
                        f'<span class="output-label">Output</span>\n'
                        f'<pre><code>{html.escape(text)}</code></pre>\n</div>')
            return fragment, None
    return '', None


def render_notebook(spec):
    """Render one committed notebook as a Jekyll page with visible stored outputs."""
    source = ROOT / 'tutorials' / spec['source']
    notebook = json.loads(source.read_text(encoding='utf-8'))
    title = _title_from_notebook(notebook, spec['source'])
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    page = [
        '---',
        'layout: default',
        f'title: "{title.replace(chr(34), chr(39))}"',
        '---',
        '',
        '<nav class="page-path" aria-label="Breadcrumb">',
        '  <a href="{{ \'/\' | relative_url }}">Home</a><span aria-hidden="true">/</span>',
        '  <a href="{{ \'/tutorials/\' | relative_url }}">Tutorials</a>',
        '</nav>',
        '',
        '<div class="tutorial-note">',
        '  <strong>Readable notebook view.</strong> Outputs below are the outputs committed with the',
        '  notebook; calculation code is available behind each “Show calculation” control.',
        f'  <a href="{REPOSITORY_URL}/blob/main/tutorials/{spec["source"]}">Open the original notebook</a>.',
        '</div>',
        '',
        f'<!-- generated from tutorials/{spec["source"]}; sha256={digest} -->',
        '',
    ]
    assets = {}
    calculation = 0
    figure = 0
    for cell_index, cell in enumerate(notebook.get('cells', [])):
        source_text = _cell_text(cell.get('source')).rstrip()
        if cell.get('cell_type') == 'markdown':
            page.extend((_rewrite_notebook_links(source_text, spec['source']), ''))
            continue
        if cell.get('cell_type') != 'code':
            continue
        calculation += 1
        page.extend((
            '<details class="tutorial-code" markdown="1">',
            f'<summary>Show calculation {calculation}</summary>',
            '',
            '````python',
            source_text,
            '````',
            '</details>',
            '',
        ))
        for output_index, output in enumerate(cell.get('outputs', [])):
            asset_name = (f'{spec["slug"]}-cell-{cell_index:02d}-'
                          f'output-{output_index:02d}.png')
            fragment, binary = _render_output(output, asset_name, calculation)
            if fragment:
                page.extend((fragment, ''))
            if binary is not None:
                figure += 1
                assets[f'assets/tutorials/{asset_name}'] = binary
    page.extend((
        '---',
        '',
        '<nav class="tutorial-footer" aria-label="Tutorial navigation">',
        '  <a href="{{ \'/tutorials/\' | relative_url }}">All tutorials</a>',
        f'  <a href="{REPOSITORY_URL}/blob/main/tutorials/{spec["source"]}">Notebook source</a>',
        '</nav>',
        '',
    ))
    assert calculation, f'{spec["source"]}: no code cells rendered'
    assert figure, f'{spec["source"]}: no figure output rendered'
    return '\n'.join(page), assets, {'title': title, 'figures': figure, 'digest': digest}


def render_tutorials():
    pages, assets, metadata = {}, {}, []
    if not (ROOT / 'tutorials').is_dir():
        return pages, assets
    for spec in TUTORIALS:
        page, new_assets, meta = render_notebook(spec)
        pages[f'tutorials/{spec["slug"]}'] = page
        assets.update(new_assets)
        metadata.append((spec, meta, next(iter(new_assets), None)))

    landing = [
        '---',
        'layout: default',
        'title: "Tutorials"',
        '---',
        '',
        '<nav class="page-path" aria-label="Breadcrumb">',
        '  <a href="{{ \'/\' | relative_url }}">Home</a><span aria-hidden="true">/</span>',
        '  <span>Tutorials</span>',
        '</nav>',
        '',
        '# Learn through the coin',
        '',
        'The project begins with one bit at a time. These readable versions preserve the committed',
        'notebook outputs, keep the calculations available, and label teaching examples separately',
        'from research claims.',
        '',
        '<div class="tutorial-grid">',
    ]
    for spec, meta, first_asset in metadata:
        landing.extend((
            '  <article class="tutorial-card">',
            (f'    <a class="tutorial-card-image" href="{{{{ \'/tutorials/{spec["slug"]}.html\' '
             f'| relative_url }}}}"><img src="{{{{ \'/{first_asset}\' | relative_url }}}}" '
             f'alt="Preview from {html.escape(meta["title"])}"></a>'),
            '    <div class="tutorial-card-body">',
            f'      <span class="tutorial-index">{spec["slug"][:2]}</span>',
            f'      <h2><a href="{{{{ \'/tutorials/{spec["slug"]}.html\' | relative_url }}}}">'
            f'{html.escape(meta["title"].split("—", 1)[-1].strip())}</a></h2>',
            f'      <p><strong>{html.escape(spec["question"])}</strong></p>',
            f'      <p>{html.escape(spec["summary"])}</p>',
            f'      <p class="tutorial-meta">Available now · {meta["figures"]} committed figures</p>',
            '    </div>',
            '  </article>',
        ))
    landing.extend((
        '</div>',
        '',
        '## What follows',
        '',
        '- **02 — From coin to quantum sensor** is deferred until roadmap B settles the second',
        '  operating point.',
        '- **03 — Detection is not identification** will explain why noticing changed contrast does',
        '  not by itself identify its physical cause.',
        '',
        f'[Notebook files and execution instructions]({REPOSITORY_URL}/tree/main/tutorials)',
        '',
    ))
    pages['tutorials/index'] = '\n'.join(landing)
    return pages, assets


def render_site(stamp):
    claims = load_yaml_list(ROOT / 'ledgers' / 'status.yaml')
    assert claims, 'empty status ledger'
    bad = [c['id'] for c in claims if c.get('status') not in STATUSES]
    assert not bad, f'bad status on {bad}'
    pages = {'status': render_status(claims, stamp)}
    for name in ('milestones', 'roadmap'):
        rows = load_yaml_list(ROOT / 'ledgers' / f'{name}.yaml')
        assert rows, f'empty {name}'
        pages[name] = render_table(name, rows, stamp)

    tutorial_pages, tutorial_assets = render_tutorials()
    pages.update(tutorial_pages)

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
    return pages, tutorial_assets, claims


def render_all(stamp):
    """Compatibility surface used by the ledger tests."""
    pages, _, claims = render_site(stamp)
    return pages, claims


def build(check=False):
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    pages, assets, claims = render_site(stamp)
    if check:
        drift = []
        for name, text in pages.items():
            path = ROOT / 'docs' / f'{name}.md'
            if not path.exists():
                drift.append(f'{name}.md is missing')
                continue
            live = STAMP.sub('', path.read_text(encoding='utf-8'))
            if STAMP.sub('', text) != live:
                drift.append(f'{name}.md is stale')
        for name, binary in assets.items():
            path = ROOT / 'docs' / name
            if not path.exists():
                drift.append(f'{name} is missing')
            elif path.read_bytes() != binary:
                drift.append(f'{name} is stale')
        asset_dir = ROOT / 'docs' / 'assets' / 'tutorials'
        existing = ({p.relative_to(ROOT / 'docs').as_posix() for p in asset_dir.glob('*.png')}
                    if asset_dir.exists() else set())
        extra = existing - set(assets)
        if extra:
            drift.append('unexpected tutorial assets: ' + ', '.join(sorted(extra)))
        if drift:
            print('site projection is stale:', '; '.join(drift), file=sys.stderr)
            return 1
        print('site projection is current:', len(claims), 'claims')
        return 0
    for name, text in pages.items():
        path = ROOT / 'docs' / f'{name}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    asset_dir = ROOT / 'docs' / 'assets' / 'tutorials'
    asset_dir.mkdir(parents=True, exist_ok=True)
    for old in asset_dir.glob('*.png'):
        if old.relative_to(ROOT / 'docs').as_posix() not in assets:
            old.unlink()
    for name, binary in assets.items():
        path = ROOT / 'docs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(binary)
    print('site pages built:', len(claims), 'claims,', len(TUTORIALS), 'tutorials,',
          len(assets), 'tutorial figures')
    return 0


if __name__ == '__main__':
    sys.exit(build(check='--check' in sys.argv))
