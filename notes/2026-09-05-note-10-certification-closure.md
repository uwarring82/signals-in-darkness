# Signals in Darkness — execution note 10 (5 Sept 2026): closure of C19 and C20

Two claims carried closure conditions written before the pinned certification existed. The
certified run published as `repo-v0.1.0` satisfied both. This note records that, and nothing
else; `notes/2026-09-03-note-04-reproduction-defect.md` stands unaltered, as the record of what
was wrong at the time it was written.

Evidence: the certification of commit `d845a80`, from a clean clone in the pinned environment
(python 3.12.14, numpy 2.4.4, scipy 1.17.1, matplotlib 3.10.8; macOS x86_64 under Rosetta 2 on
an Apple M1 Pro; BLAS 3.9.0), published as an asset of that release.

## C19 — `res8_switch.json` independently regenerated

C19 recorded that `sid_run8.py` wrote its output to the current working directory rather than to
`analysis/outputs/`, so the archived file could not have been written in place by a run
performed as documented. Its condition was that the values remain unverified "until
independently regenerated and compared".

In the certified run `sid_run8.py` reported `computed: 2, cached: 0` and its six delay rows
matched the archive at **0.00 σ** — `switch@300` at τ_c/c = 20, 5, 1 giving 1546.3, 2002.8,
3644.0, and `switch@1000` giving 1147.2, 2219.7, 5756.7, each identical to the stored value.
The regeneration came from computation, not from cache: the producer writes into
`analysis/reproduction/` and never reads the archive, and the run's counters show no reuse.

**C19 → `result`.** What is settled is that the archived values are correct and reproducible.
What is *not* settled, and is preserved rather than quietly dropped: **the creation path of the
original file remains unknown.** It was written by some run whose working directory is not
recorded, and no evidence recovers that. The values are now independently confirmed; their
original provenance is not.

## C20 — the repaired route completed from a clean checkout

C20 recorded that the documented reproduction route consumed committed cache state, so a clean
clone recomputed nothing. Its condition was that the criterion "stays open until a clean-checkout
rerun of the whole affected chain under a pinned environment".

That rerun is the certification. Every stage computed afresh — `computed: 7, cached: 0` for
calibration, `15, 0` for delays, `2, 0` for explore-then-switch — with 164 tests passing and
none skipped, the site projection current, strict JSON across archive and reproduction, and six
comparable outputs inside their declared tolerances.

The route also failed in the one way it should. `sid_run6s.py cal` exited nonzero, refusing the
two calibration rows whose provenance is lost (C17, C18) on the exact-threshold test, while the
other five reproduced at 0.00 σ. A gate that cannot reject is not a gate; this one rejected
exactly what it was built to reject, under a different interpreter and a different numpy major
version from the one that first found the defect.

**C20 → `result`.** The interface is repaired and demonstrated, and the closure conditions listed
in note 04 §5 are met: fresh-by-default execution, correct output destinations, explicit resume,
a regression test that runs with the committed archive present, and a clean-checkout rerun of the
affected chain.

## What this note does not do

It does not revisit C09, C11 or C12. Those remain `open` on their own terms: their headline
numbers rest on the withdrawn threshold chain, and the certified run put fixed-extremum at 1.44×
rather than the 1.56 note 03 §3 reports once thresholds are derived instead of transcribed.
Reproducing the route is not the same as re-establishing the comparisons that ran on it.
