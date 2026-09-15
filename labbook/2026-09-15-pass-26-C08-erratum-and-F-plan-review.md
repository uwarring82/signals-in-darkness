# 2026-09-15 — Pass 26: a matching threshold can hide a wrong rate

**Question:** Can note 26 be accepted as the F protocol, and does its C08 finding change
the frozen manuscript scope?

**Finding:** The run3 map drops F(u) from its first binary lag. Run4's checked fit does
not. Both original diagnostic scripts were recovered and reproduce the reported tables.
The four quoted coarse thresholds coincide after correcting the fit; the rate map does
not. The review also finds a false E6 verdict claim, unspecified variance transport and
reference checks, rounded boundary inputs described as exact, and an overbroad closure rule.

**Why it matters:** Reproducing a coarse-grid threshold cannot establish the correctness
of the rate used to obtain it. Nor does a comparator difference just larger than 5 %
force one of them to fail a ±5 % validation test against a third quantity.

**Status:** [Note 27](../notes/2026-09-15-note-27-C08-fold-erratum-and-F-review.md) records
the erratum against the frozen card and earlier prose, and decisions for revising note 26.
C08 retains only its four quoted coarse thresholds under that erratum. The archived map
cannot be used as a correct finite-window figure. The card and tag remain intact; no
corrected map claim is promoted. Note 26 remains an unaccepted draft and F stays open.

The last model-generated review introduced the incorrect C05/C08 equivalence; the coding
assistant accepted it without checking run3's normalization. Both failures are recorded.
The correction is attached to the claim ledger and a new milestone, rather than rewriting
the historical card, notes, passes or original milestone summary.

**Next test:** Revise and freeze the full F protocol only after the sampling, initialization,
convergence and verdict rules are executable. Then implement and check the independent OU
simulator and ARMA filter. No likelihood, pilot or F outcome was computed in this pass.

The preserved scripts and additional review producer are in
[analysis/diagnostics](../analysis/diagnostics/README.md); the explicit failing and passing
lag-one controls are in [the focused tests](../tests/test_c08_fold_provenance.py).
Review, drafting and implementation used model assistance.

Validation: 66 targeted scientific tests and 126 ledger/site tests passed locally;
73 local links resolved. The full suite was not rerun. All pre-existing scientific and
historical files, the frozen tag target and the original milestone entries were preserved;
the claim ledger gained only C08's erratum pointer and scope qualification.
