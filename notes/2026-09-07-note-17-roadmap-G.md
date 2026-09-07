# Signals in Darkness — execution note 17 (7 Sept 2026): roadmap G, the operating point becomes an object

G is complete. It is bookkeeping in the sense that it computes nothing new, and it is not
bookkeeping in the sense that matters: it removes the structural condition under which C17 and C18
were lost.

## 1. What was wrong

`analysis/lib/sid_policies.py` held

    C, s = 0.4, 0.5

as mutable module globals, read by three consumers that could disagree — `sid_run6s.py` through
`build_policies()`, `sid_run8.py` by importing `C` and `s` directly, and
`sid_fig_policy_delays.py` by naming them in a figure title string.

The consequence is not a style complaint. **A stored result did not carry the parameters it was
computed at.** A calibration checkpoint recorded seeds, revision, interpreter and library versions,
and said nothing about the operating point. A threshold measured at one operating point could
therefore be consumed by a delay run at another with nothing in the machinery able to notice. C17
withdrew two calibration rows and C18 the delay measurements built on them, in both cases because
provenance could not be established after the fact. G is the structural fix for that class of
failure, and it is a precondition for roadmap B, which introduces a second operating point.

## 2. What replaced it

An immutable `OperatingPoint(C_eff, s)`, a frozen dataclass with `as_dict()` for serialisation and
value equality. The field is **`C_eff`**, the effective per-shot contrast including all loss at the
implicit fixed interrogation — deliberately *not* `C_bar`, and not the zero-dephasing `C_0` that the
physical maps and roadmap E use. A test asserts `C_bar` and `C_0` are absent, so decision D1's
distinction cannot erode back into a shared field.

- `Bank(tccs, op)` and `build_policies(op)` require it, and raise `TypeError` naming roadmap G when
  it is missing or of the wrong type.
- `run_batch` reads `bank.op.C_eff` and `bank.op.s`. Nothing consults module state.
- Module-level `C` and `s` are **gone**, asserted both as absent attributes and as an absent
  assignment line, and no run imports them as loose names.
- `PILOT = OperatingPoint(C_eff=0.4, s=0.5)` is a named constant, not a default argument: callers
  pass it explicitly.

## 3. Provenance, and refusal

The operating point enters `cal_config()`, so it flows into `run_metadata` → `config_digest` →
`incompatibilities()` — machinery that already existed and was already tested. Reuse under a
different operating point is now refused, and the refusal **names the culprit** rather than
reporting an opaque digest difference. Verified end to end by tampering a checkpoint and running the
delays stage:

    refusing thresholds that are not this run's cal output:
      - config_digest: thresholds 'ee27d214f881b4b5' vs this run '2d7b1884e89e26c1'
      -   config.operating_point: thresholds {'C_eff': 0.5, 's': 0.3} vs this run {'C_eff': 0.4, 's': 0.5}
      rerun the cal: stage, or pass --thresholds=archive deliberately.

Exit code 2. A companion test asserts that *identical* configurations remain compatible, because a
gate that rejects everything is not a gate.

`sid_fig_policy_delays.py` no longer names the operating point in a title literal; it reads it from
the stored run's metadata. The archived `res6_policies.json` predates G and carries none, so the
rebuilt figure now reads **"operating point not recorded in this output"**. That is the honest
rendering of a pre-G artefact, and it makes the provenance gap visible instead of restating a
literal the archive cannot support.

## 4. The refactor is numerically inert

A full fresh calibration of all seven pilot policies was run after the refactor, on
python 3.9.7 / numpy 1.23.5 / scipy 1.10.0 — **not** the pinned stack, so this is a second
independent environment.

| policy | fresh h* | archive | verdict |
|---|---|---|---|
| oracle-mid(tc=5) | 3.421875 | 3.421875 | pass, mean 0.00 σ |
| oracle-mid(tc=1) | 1.546875 | 1.546875 | pass, mean 0.00 σ |
| extremum-only | 3.734375 | 3.734375 | pass, mean 0.00 σ |
| learner-mid(bank) | 3.421875 | 3.421875 | pass, mean 0.00 σ |
| learner-interleave-B1(bank) | 3.421875 | 3.421875 | pass, mean 0.00 σ |
| **oracle-mid(tc=20)** | 4.671875 | 4.359 | **FAIL — withdrawn as C17** |
| **learner-interleave-B10(bank)** | 3.734375 | 3.55 | **FAIL — withdrawn as C17** |

**Five pass, two fail, and the two that fail are exactly the two that must.** Thresholds are
compared by exact equality, not within a tolerance, so any numerical drift from the refactor would
appear here rather than hide. The two withdrawn rows are excluded from the preservation claim **by
name**, not by whether they happen to reproduce — a test reads C17 from the ledger and asserts both
rows are named there, so the exclusion list cannot quietly grow.

## 5. What G does not do

It does not add the second operating point; that is B. It does not backfill provenance into the
archived outputs — `res6_policies.json` still carries no metadata, and no amount of refactoring
recovers what was not recorded. And it does not revisit C17 or C18: those stay withdrawn on their
own terms. What changed is that the same failure cannot happen again silently.

Next is **B**, at C_eff = 0.5, s = 0.3, labelled an upper-bound stress test at the parity ceiling,
with every policy calibrated afresh and no archived C17/C18 threshold entering.

---

## Repair pass, appended 7 September 2026 (same day, after review)

The note above declared G complete. **It was not.** Four defects survived the first pass; three
were in code and one was in the tests that were supposed to catch them.

**1. The shared simulator was fixed; the explore-then-switch path was not.** `sid_run8.py` had its
`from sid_policies import C, s` removed — and then rebound the same names one line below as
`C, s = OP.C_eff, OP.s`. `run_batch_age` drew its post-change process from those module names while
its filter (`bank.e1`) and null (`bank.p0`) came from `bank.op`. A bank built at C_eff = 0.5,
s = 0.3 would therefore have been simulated against the pilot's C_eff = 0.4, s = 0.5 process, with
nothing anywhere to detect the mismatch. **Freezing `OP` does not freeze a binding derived from it.**
Both the null and non-null paths now read `C, s` from `bank.op` inside the function.

**2. `sid_run8`'s checkpoint had no identity at all** — no operating point, no config digest, no
compatibility check — so a checkpoint written at one operating point could be resumed at another.
That is precisely the defect G exists to eliminate, left intact in the second driver. It now has
`run_config()`, stores `{"switch": …, "meta": run_metadata(…)}`, and refuses a mismatched resume by
name. Pre-G flat checkpoints carrying no identity are refused rather than silently resumed.

**3. The acceptance tests forbade *importing* `C` and `s` but not *rebinding* them**, which is
exactly why they passed over defect 1. They now walk the module AST of both drivers and reject any
module-level assignment to those names, and they exercise `run_batch_age` at two operating points on
both paths.

**4. The policy figure** draws `res6_policies` and `res8_switch` on one axis but was titled from
`res6` alone. It now reads both, refuses to combine unequal operating points, and names the source
when only one file records it.

### The evidence is now committed, and the gate does not skip

The original preservation test skipped when the git-ignored reproduction file was absent — which is
always, on a fresh clone — so G's central numerical claim lived only in a terminal transcript and
was bound to no commit. `analysis/G_preservation_evidence.json` now holds the comparison, produced
by `tools/record_preservation_evidence.py`, and the test asserts it unconditionally.

The first attempt to produce it recorded **`b927e6e+dirty`**, because the tests were being edited
while the calibration ran. That is the same provenance failure G exists to remove, committed live
during the work to remove it. The run was discarded and repeated from a stashed-clean tree.

One rule was deliberately narrowed rather than enforced as first written. The recorder refuses
outright if the **calibration** ran dirty — that is the load-bearing constraint, since numbers from
an uncommitted tree name no revision. The tree at *recording* time is weaker: this tool and the test
it feeds cannot be committed before the artifact they gate exists. So the artifact **records** which
files were uncommitted when it was written rather than refusing, and a test asserts every path it
names actually exists — the first version of that parsing used `stdout.strip()`, which removed the
leading space of the first porcelain line and cut a character off the filename.

Clean-tree calibration at `b927e6e`, run `d2a1960161d7`, python 3.9.7 / numpy 1.23.5: five valid
rows exact, two C17-withdrawn rows failing as required. **G is complete as of this repair pass.**
