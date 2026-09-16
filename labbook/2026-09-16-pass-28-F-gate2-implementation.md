# 2026-09-16 — Pass 28: an implementation that can fail its own checks

**Question:** Can the frozen roadmap-F protocol be implemented so that every numerical check,
refusal, deadline and record is executable — and demonstrably able to fail?

**Finding:** Yes, after four review findings.
[analysis/lib/sid_arma.py](../analysis/lib/sid_arma.py) and
[analysis/runs/sid_run13.py](../analysis/runs/sid_run13.py) implement
[protocol_F.json](../analysis/protocol_F.json) at digest `b7c09ce90f33c37b`.
- **Library:** the exact ARMA(1,1) grid filter in vector form, with the protocol's literal
  pair-state recursion kept as a check; stationary initialisation (NC4); the AR(1) nesting
  reference and the `hmm_rate` tie (NC1); the exact OU window simulator in the frozen draw order
  (NC2); comparators K1–K4 and series convergence (NC3); the paired criterion (NC5/NC6); the pilot
  bound, shot rule, intervals and verdicts. It performs no I/O and sets no threads.
- **Driver:** a required `--phase` with no default; the protocol's refusals plus existing outputs,
  Gate-3 artifact integrity and an implementation-change check between gates; the Gate-3 deadline,
  evaluation admission and stop rule; blind, self-digested artifacts; closure through the builder.
- **Tests:** 73 implementation tests on synthetic fixtures. Every numerical check and every refusal
  is shown passing on a correct input and failing on a wrong one.

**Why it matters:** four defects survived a prose reading of code that passed its own tests.
- **The tie compared two summations, not two filters.** `hmm_rate` accumulates `log Z` into a
  running float; the implementation summed its own increments with `math.fsum`. The filter agreed
  exactly, but at N = 200 000 the two roundings differ by 1.7 × 10⁻¹² relative — enough to fail the
  frozen 10⁻¹² tolerance on a *correct* filter. The tie now reproduces `hmm_rate`'s arithmetic;
  estimators keep the stable summation.
- **The deadline did not cover every computation.** NC3 ran unconditionally after NC1 had already
  exhausted the budget, and the tie polled its deadline only around `sid_lib`'s uninterruptible
  loops. Nothing starts after expiry now, and a timer raises inside the committed loops.
- **An interrupted first calculation left no record.** Both phases now write their artifacts before
  computing, checkpoint after every step, and keep the elapsed time when a step raises or the run is
  interrupted. Without that, a failed run lost its provenance and its share of the aggregate clock,
  and looked like a fresh start.
- **A reconstructed start time hid spent budget.** Recomputing the evaluation's `t0` after its first
  write excluded that write: with a five-second budget and a six-second write, admission reported
  five seconds remaining and evaluated the point. The corrected driver reports −1 s and does not.

**Status:** Gate 2 accepted on 2026-09-16. No campaign phase has run: no NC1–NC6 on protocol seeds,
no pilot and no evaluation. The frozen protocol is unchanged. Gate 3 is approved; Gate 4 is pending.

**Next test:** Gate 3 — NC1–NC6 and the pilots through the main-thread CLI on `sid-f`, all five
thread variables at 1, under the frozen 1800-second deadline. Both artifacts are then committed at
their frozen output paths, added explicitly against the ignore rule, with their digests, derived
shot counts and predicted evaluation costs for Gate-4 review.

**Validation.**
- **`sid-f` 3.12.14 and 3.13.7:** 73 implementation tests pass on each; 141 with the protocol, lock
  and prose tests.
- **Python 3.9.7:** the full suite passes, 598 passed and 2 skipped.
- **Design evidence:** parameters and comparators reproduce to ≤ 1.7 × 10⁻¹⁶ relative on all three
  stacks, against a contract of 10⁻¹².
- **Preflight** passes on `sid-f` and writes nothing; off the pinned stack it refuses.
- **Costs:** an M241 filter step takes 12.4 µs on synthetic parameters.

**Also recorded.**
- NC2's five-standard-error rule reads an eight-seed standard error, so it is a t₇ test: a correct
  simulator fails a single statistic with probability 0.16 %, and a point with six statistics with
  probability up to 0.9 %. This is a property of the frozen protocol, disclosed rather than changed.
- `analysis/reproduction/` is ignored by git, so a clean tree cannot vouch for the Gate-3 artifacts.
  Each artifact carries its own digest, the evaluation records the digests it read, and the review
  decided that both Gate-3 files are committed at their frozen paths before Gate-4 review.
- Three of the first test failures were faults in the tests, not the implementation.
- Two corrections outside F: pass 27's revision chronology (two wording defects were filed under the
  revision that corrected them), and the stale F-prose guard that `590c6af` broke.

Technical record: [note 28](../notes/2026-09-15-note-28-F-protocol-draft.md) (design and review
history), [pass 27](2026-09-15-pass-27-F-protocol-frozen.md) (the freeze),
[tests/test_sid_arma.py](../tests/test_sid_arma.py) and
[tests/test_sid_run13.py](../tests/test_sid_run13.py).

Review, drafting and implementation used model assistance.
