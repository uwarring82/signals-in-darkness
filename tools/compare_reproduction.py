#!/usr/bin/env python3
"""Compare analysis/reproduction/ against the published archive under declared tolerances.

The run scripts write into analysis/reproduction/; analysis/outputs/ is the published
reference and is never written by a run. This tool is the comparison step: it reports, per
file and per key, the largest relative deviation between what was just computed and what is
archived, and exits nonzero if any exceeds the tolerance declared for that file.

It does not adopt anything. Promotion of a reproduced output into the archive is a separate,
deliberate commit.

Usage:
    python tools/compare_reproduction.py [--json <path>]
"""
import json
import math
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'analysis' / 'outputs'
REPRODUCTION = ROOT / 'analysis' / 'reproduction'

# Declared per-file tolerances on the relative deviation of finite numbers.
# Everything here is deterministic given the recorded seeds, so the expectation is agreement
# far below these; the tolerances allow for library-version differences in the last digits,
# not for a different answer.
TOLERANCES = {
    'res1_core.json': 1e-9,
    'res2_partial.json': 1e-9,
    'res7B_servo.json': 1e-9,
    'res3_comparator.json': 1e-9,
    'res5_calibration.json': 1e-9,
    # res7A's class-B rows come from an L-BFGS-B infimum, whose convergence point moves with
    # the scipy version; 1e-6 is the optimiser's reach, not a numerical disagreement.
    'res7A_identifiability.json': 1e-6,
}
# res6_policies.json and res8_switch.json are compared by their own producers, which gate on
# an exact threshold match and a 3-sigma mean test (analysis/lib/sid_repro.py).
COMPARED_ELSEWHERE = {'res6_policies.json', 'res8_switch.json'}


def walk(a, b, path=''):
    """Yield (path, reference, fresh) for every leaf pair, and structural mismatches."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                yield (f'{path}.{k}', '<absent from reproduction>', '<present in archive>')
            elif k not in b:
                yield (f'{path}.{k}', '<present in reproduction>', '<absent from archive>')
            else:
                yield from walk(a[k], b[k], f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield (path, f'<{len(b)} items>', f'<{len(a)} items>')
            return
        for i, (x, y) in enumerate(zip(a, b)):
            yield from walk(x, y, f'{path}[{i}]')
    else:
        yield (path, b, a)


def compare(name):
    fresh_p, ref_p = REPRODUCTION / name, REFERENCE / name
    if not fresh_p.exists():
        return None
    fresh = json.loads(fresh_p.read_text(encoding='utf-8'))
    ref = json.loads(ref_p.read_text(encoding='utf-8'))
    tol = TOLERANCES.get(name, 1e-9)
    worst, where, problems = 0.0, None, []
    for path, r, f in walk(fresh, ref):
        if isinstance(r, str) and r.startswith('<'):
            problems.append(f'{path}: {r} / {f}')
            continue
        if isinstance(r, bool) or isinstance(f, bool) or r is None or f is None or \
                isinstance(r, str) or isinstance(f, str):
            if r != f:
                problems.append(f'{path}: archive {r!r} vs reproduction {f!r}')
            continue
        if not (math.isfinite(r) and math.isfinite(f)):
            problems.append(f'{path}: non-finite value')
            continue
        d = abs(f - r)/abs(r) if r else abs(f - r)
        if d > worst:
            worst, where = d, path
    return {'file': name, 'tolerance': tol, 'max_rel_dev': worst, 'at': where,
            'problems': problems, 'pass': worst <= tol and not problems}


def main(argv):
    results, failures = [], 0
    names = sorted(p.name for p in REFERENCE.glob('*.json'))
    print(f'comparing {REPRODUCTION.relative_to(ROOT)} against {REFERENCE.relative_to(ROOT)}\n')
    for name in names:
        if name in COMPARED_ELSEWHERE:
            print(f'  {name:32s} compared by its producer (exact h*, 3 sigma means)')
            continue
        r = compare(name)
        if r is None:
            print(f'  {name:32s} NOT REPRODUCED in this run')
            continue
        results.append(r)
        verdict = 'pass' if r['pass'] else 'FAIL'
        print(f"  {name:32s} {verdict}  max rel dev {r['max_rel_dev']:.3e} "
              f"(tol {r['tolerance']:.0e}) at {r['at']}")
        for p in r['problems']:
            print(f'      {p}')
        failures += 0 if r['pass'] else 1
    print(f'\n{len(results)} files compared, {failures} outside tolerance')
    if '--json' in argv:
        out = argv[argv.index('--json') + 1]
        pathlib.Path(out).write_text(json.dumps(results, indent=1), encoding='utf-8')
        print(f'wrote {out}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
