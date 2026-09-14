# 2026-09-14 — Pass 23: teaching the result without enlarging it

**Question:** Do the new tutorials preserve the scope of the research claims, and can readers find the corrections made during review?

**Finding:** The calculations survived review, but several public statements needed narrowing. Posterior sampling's demonstrated action response could not be attributed to the greedy policy. A stress-point crossover calculation could not inherit C05's claim status. The successful hedges could not be ranked by their point estimates alone. Notebook 03 also needed the direction of its numerical bound: a feasible class-B candidate can overstate the retained information, while the larger class A supplies a lower bound. Note 24 records these repairs and corrects a stale line reference in the locked B/E manifest.

**Why it matters:** Correct numerical output does not protect a reader from an overbroad interpretation. Nor does a correction protect the record if readers cannot find it. The manifest's content-checking test now points to note 24, and a SHA-256 test pins the existing locked bytes. The res9 recomputation test has its own relative tolerance, so future changes to the separate res7A budget cannot silently change this check.

**Status:** No scientific claim changed. Notebooks 02 and 03 remain executed drafts, and the manifest, ledgers and archived outputs are preserved. Review of the extraction found identical rows and unchanged simulated records; the narrower prose and repaired guards passed the reported checks on two numerical stacks. These are validation observations, not a new sensing result.

**Next test:** Keep the manifest lock and the independent res9 tolerance in the regression suite. Roadmaps D and F remain the next scientific checks; the tutorials do not close either.

Technical record: [note 24 — tutorial review and citation erratum](../notes/2026-09-14-note-24-tutorial-review.md),
[manifest checks](../tests/test_manifest_BE.py), and
[shared-calculation checks](../tests/test_shared_sensing.py). This pass accompanies note 24;
it does not supersede a scientific claim. Drafting and implementation used model assistance;
the review measurements below were reported by the owner and are attributed as such.

The owner reported 117 affected tests passing on Python 3.9.7 / SciPy 1.10, and 61 E,
shared-sensing and invariant tests passing on Python 3.13.7 / SciPy 1.17.1. The largest relative
deviation from res9 was zero on the stack that wrote it, 6.6e-10 on SciPy 1.15.2 and 6.3e-9 on
SciPy 1.17.1. The Python 3.11 environment had no pytest, so its observation was a deviation
measurement only. The independent relative budget remains 6e-8, about ten times the largest
reported deviation; positive rates receive no absolute allowance, and zero rates must remain
exactly zero. The full-suite run recorded during the preceding implementation pass was 452
passed with one missing-cffconvert skip; the owner did not repeat that full run.

Runtime also depends on the stack. The owner reported fresh notebook contract-test times of
4.5–4.8 s per notebook on Python 3.9.7, compared with the local Python 3.13.7 observations of
1.71 s for notebook 02 and 1.32 s for notebook 03 recorded in note 24. Both include startup and
imports and remain well within the 60 s contract. These measurements are not a guarantee or
release recertification. The earlier under-two-second authoring measurement used an already
started process and did not establish an end-to-end runtime.
