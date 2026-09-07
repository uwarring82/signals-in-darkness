# Signals in Darkness — execution note 18 (7 Sept 2026): roadmap B, and an operating-point inversion

B is complete. It found what it was built to be able to find: **the ordering of detection policies
reverses between operating points.** The card's justification for B was that "the demotion of
adaptivity must rest on two points, not one." On two points, it does not rest at all.

## 1. What was run

At the parity-ceiling stress point **C_eff = 0.5, s = 0.3** — an upper-bound stress test, not a
realistic contrast — the seven pilot policies were calibrated afresh to E₀[T] ≈ 3×10⁴ and their
detection delays measured at τ_c/c ∈ {20, 5, 1}, together with the two explore-then-switch hedges.
No archived threshold entered: the stress point has no archive, and the run had to be asked for with
`--no-reference` precisely so that it could not be mistaken for a verification.

Then the **pilot chain was re-run from scratch on its own fresh thresholds**, because the published
pilot ratios all divide by a τ_c/c = 20 benchmark that was withdrawn as C18. Without that, the two
operating points could not be compared like for like.

The fresh pilot reproduces the archive: **15 of 15 delay rows and 6 of 6 switch rows pass**, with
calibration failing on exactly the two rows withdrawn as C17. Zero capped runs anywhere, at either
operating point.

## 2. The result

Worst-case delay ratio to the best fixed-endpoint benchmark, over τ_c/c ∈ {20, 5, 1}:

| policy | pilot (archived, C18 chain) | pilot (fresh, clean) | **stress (fresh, clean)** |
|---|---|---|---|
| fixed-extremum | 1.56 | **1.44** | **2.88** |
| switch@300 | 1.64 | 1.64 | 2.19 |
| interleave-B1 | 1.67 | 1.67 | 1.87 |
| interleave-B10 | 2.07 | 2.12 | 2.01 |
| **switch@1000** | 2.60 | 2.60 | **1.51** |
| learner-mid(bank) | 7.60 | 7.60 | 4.95 |

At the pilot, fixed-extremum wins and no hedge beats it. At the stress point, fixed-extremum
degrades to 2.88 while four of five hedges beat it, the best by a factor of **1.91**. `switch@1000`
travels from worst hedge (2.60) to best policy overall (1.51).

**The cleanest anchor is switch@1000 against fixed-extremum at the stress point: both miss the ARL
target by +13 %.** A 1.91× gap between two policies calibrated to the same accuracy cannot be
attributed to calibration mismatch. The weaker part of the claim is "four of five", because those
five miss the target by between +9 % and +32 %; the two-policy comparison does not depend on it.

The mechanism is visible in the columns, not just the worst case. Fixed-extremum is *optimal* at
τ_c/c = 1 — it is the benchmark there — and collapses at τ_c/c = 20 where the mid-fringe channel
dominates. The hedges give up a little everywhere and lose much less in the bad corner, which is
what a hedge is for. At the pilot the crossover sits such that the trade does not pay; at the stress
point it does.

## 3. What this is NOT

**Every schedule tested is precommitted.** `sid_policies.sched(n)` takes the step index and nothing
else — it cannot consult the posterior, and `run_batch` calls it as `sched(n)`. The banks do mix
over τ_c, so the *filter* learns; the *action rule* never uses what it learns, `switch@B` included,
which switches on segment age. So C27 is evidence about **robust action scheduling across unknown
correlation times**, and it is not evidence that online action learning succeeds. Posterior-driven
selection is roadmap C and remains untested.

That distinction is structural rather than interpretive, and it is worth keeping in exactly those
terms: a reader who takes "adaptive policies win at the second operating point" from this note would
be taking something the run cannot support.

## 4. Three claims repaired, one added

C09, C11 and C12 were `open` **because they rested on the withdrawn C18 benchmark**, not because
their content was doubted. The fresh pilot chain removes that dependency, so all three move to
`result` — with corrected numbers, because replacing the withdrawn benchmark changes them.

- **C09** → `result`. Crossover between τ_c/c = 5 and 20 confirmed on fresh numbers.
- **C11** → `result`, scope narrowed to the pilot **explicitly**. Its 1.56 becomes 1.44, and its
  published range 1.64–1.67 omitted interleave-B10 at 2.12.
- **C12** → `result`, scope narrowed. Its 0.98× becomes 0.90× against a fresh benchmark, and the
  "no resolved penalty" holds at τ_c/c = 20 and 5 only: at τ_c/c = 1 the bank costs **1.60×**,
  because a mixture over τ_c ∈ {1, 4, 10, 25} is furthest from the truth at the shortest correlation
  time.
- **C27** added, `result`: the inversion itself.

## 5. What made this run trustworthy

An adversarial audit of the B path was run **before** the compute, and it found a defect that would
have invalidated the entire comparison. Under the pilot's calibration bracket, `oracle-mid(tc=1)` at
the stress point never moves the bisection floor: the returned h* = 1.078125 is the midpoint of an
*untested* interval and confirms at ARL 23 669, a 21 % miss, reported as a clean calibration. The
matched-E₀[T] premise — which every ratio in this note depends on — would have been quietly false
for that policy. See `notes/2026-09-07-note-17-roadmap-G.md` for the machinery that made a
per-operating-point bracket possible, and commit 5ea5806 for the guards.

One deviation is recorded rather than fixed: `learner-interleave-B1` at the stress point calibrates
to ARL 39 543, **+31.8 %**, outside the ±30 % envelope note 03 §2 states. It is held to a stricter
false-alarm rate than the others, so its measured delay is biased **upward** — the bias runs against
the hedge, which means correcting it would strengthen C27 rather than weaken it.
