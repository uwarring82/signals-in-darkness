# 2026-09-15 — Pass 27: a protocol checked on the stack that will run it

**Question:** Is the roadmap-F comparison fixed tightly enough to freeze before any ARMA
likelihood, numerical check, pilot or evaluation exists?

**Finding:** Yes, after four draft revisions.
[analysis/protocol_F.json](../analysis/protocol_F.json) is frozen at Gate 1 with digest
`b7c09ce90f33c37b`, described in [note 28](../notes/2026-09-15-note-28-F-protocol-draft.md),
revision 4. It fixes:
- **Comparators and points:** four comparators, with K1 alone deciding F at the mandatory points
  E3–E5; the C08 boundary points E1/E2 at exact archived grid inputs, as a conditional pair
  reported separately.
- **Reference:** an exact ARMA(1,1) grid filter with stationary initialisation and burn-in; an
  AR(1) nesting reference that shares both, tied to the committed `hmm_rate`; and an exact OU
  simulator that never sees the ARMA parameters.
- **Checks and sampling:** numerical checks NC1–NC6, per-point variance pilots, a blind shot rule
  and three-way pointwise verdicts.
- **Budget:** hard time caps.
- **Wording:** a closure caveat that never claims more than the verdicts it inspects.

The execution stack (`sid-f`: Python 3.12.14, NumPy 2.4.4, SciPy 1.17.1, OpenBLAS, native arm64)
is installed exactly as solved and is locked.

**Why it matters:** Every revision failed an executable check that a prose reading had
passed:
- two windows called paired did not share their observations;
- a stop margin could run past its cap;
- the builder could overwrite a frozen file;
- a dry run and an installation used different channel policies;
- a caveat confined validation to C04 while the protocol licensed results contradicting it;
- a roundoff-level diagnostic was stored as a value that the execution stack could not reproduce.

A frozen protocol is only useful if the stack that will run it can verify it.

**Status:** The protocol is frozen with digest `b7c09ce90f33c37b`. Roadmap F stays OPEN, and no F
outcome exists. Gates 2–4 — implementation, numerical checks with pilots, and evaluation —
keep their separate approvals.

**Next test:** Gate 2.
- **Build:** implement `analysis/lib/sid_arma.py` and `analysis/runs/sid_run13.py` against the frozen
  contracts, with NC1–NC6 as tests that can fail.
- **Driver refusals:** a dirty tree, the wrong stack, thread variables other than 1, or a digest
  mismatch.
- **Separate workstream:** the corrected C08 map, after Gate 2.

Technical record: [note 28](../notes/2026-09-15-note-28-F-protocol-draft.md) (design, review
history and installation), [note 27](../notes/2026-09-15-note-27-C08-fold-erratum-and-F-review.md)
(the review of the rejected note 26), [tests/test_protocol_F.py](../tests/test_protocol_F.py),
[tools/build_protocol_F.py](../tools/build_protocol_F.py) and the stack records in
[analysis/stack_F](../analysis/stack_F/conda-osx-arm64.txt).

The failures along the way stay in the record:
- **Note 26:** its E6 "forced failure" claim was false; rounded boundary inputs were presented as
  exact; and its sampling rule was not executable.
- **Revision 1 (`0a3584b`):**
  - NC6 compared different observations;
  - a 1.25× stop could exceed the 2 h cap;
  - the builder replaced a frozen protocol on a temporary fixture;
  - the dry run excluded `defaults`, while installing from `environment.yml` would append it.
- **Revision 2 (`4f0b390`):**
  - `python=3.12` resolved to 3.12.0 although 3.12.14 builds existed. A missing `__osx` virtual
    package was ruled out, and the cause was not established. The second solve pinned 3.12.14.
  - The OPEN and FAILED caveats confined validation to C04 despite permitted mixed outcomes.
    Revision 3 corrected this.
- **Revision 3 (`a327ab5`):**
  - The post-evaluation scope sentence spoke about every other input ("At every other input its
    binary-likelihood validation remains confined to C04's tested point-sampled cases") while the
    wording helper inspected only E3–E5. Revision 4 corrected this.
  - Its test count was misstated (43 and 5 for 41 and 7).
- **Revision 4 (`99cb09a`),** failures met while preparing it:
  - On the installed stack, a total variation of about 10⁻¹² came out 9.997 × 10⁻¹³ against
    9.878 × 10⁻¹³ and failed the rebuild check, so design evidence now records bounds.
  - The first digest fixture, `benchmark_ladder_C.json`, did not recompute under the convention.
- **Installation (`009deb5`):** every stop condition passed. `docopt 0.6.2` was built from source
  with `setuptools 84.0.0` fetched unpinned, which is disclosed.
- **Outside F:** the digests of `benchmark_ladder_C`, `eligibility_C` and `schedule_class_C` do not
  recompute, and `sid_run10.py` only reads the stored field. This is recorded for a separate
  check.

**Validation.**
- **Python 3.9.7:** 91 targeted tests pass.
- **Python 3.13.7 and `sid-f` 3.12.14:** the 58 protocol and lock tests pass on each.
- **Rebuild check:** the frozen-aware `--check` matches the builder and verifies the digest on all
  three stacks.
- **Refusals:** the committed file refuses both a draft write and a second freeze, and its bytes
  stay unchanged.
- **Not done:** the full suite was not rerun.

**Correction (2026-09-16).** As first written, this list filed two wording defects under the
revision that corrected them, not the revision that contained them:
- The every-input scope sentence was listed under revision 4. It was in revision 3 (`a327ab5`), and
  revision 4 replaced it. The Gate-1 review identified this misattribution.
- The C04-confined OPEN and FAILED caveats were listed under revision 3. They were in revision 2
  (`4f0b390`: `CAVEAT_OPEN` and `CAVEAT_FAILED`), and revision 3 removed them. This was found while
  checking the first misattribution against the commits.

The protocol's own revision log records changes, not defects, and is unaffected.

Review, drafting, implementation and installation used model assistance.
