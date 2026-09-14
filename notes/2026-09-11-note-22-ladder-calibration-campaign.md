# Signals in Darkness — execution note 22 (11 Sept 2026): one schedule factory, and what regenerating roadmap B's calibrations exposed

Roadmap C's benchmark ladder ranges L1/L2/L3 over thirteen candidates: the eleven frozen
schedules plus both learners. When I went to compute the rungs, none could be computed. Seven of
the eleven schedules had never been calibrated, and **no candidate had ever been run on the
selection stream at all**, including the six inherited from roadmap B.

The cheap move was to redefine L3 over whatever had historical outputs. That was rejected, and
rightly: it replaces performance-driven selection with availability-driven selection, and it
undoes the entire protection of freezing the class before unblinding. If the full campaign were
too expensive the honest alternative was to stop at L2 and leave L3 open — not to redefine L3
after seeing what it would cost.

## 1. Two hard-coded lists became one manifest-driven factory

Roadmap B measured the class through two separate implementations: `build_policies` for the
constants and interleaves, and `sid_run8.run_batch_age` with its own `B_VALUES` tuple for the
age-based switches. Adding five members meant editing both, which is precisely how an executed
class drifts from the manifest that froze it.

`sid_policies.schedule_from_spec` now builds every member from `analysis/schedule_class_C.json`,
and `run_batch` tracks segment age itself, absorbing `run_batch_age`'s job into the shared
simulator.

Replacing a measured implementation is only safe if the replacement reproduces it, and "means
agree" is not good enough — the ladder reuses per-replicate outputs, and a mean can agree while
the runs underneath differ. `tests/test_schedule_factory.py` therefore compares **per-replicate
stopping times**, at both operating points, on both the null and post-change streams. All three
hold: age tracking is inert for every `sched(n)` policy, factory `switch@B` is bit-identical to
`run_batch_age`, and the constants and interleaves match their hard-coded originals.

**A defect I introduced and caught.** The first version of those golden pins was vacuous. The
parameters I chose put *every* run at the step cap, so all fourteen digests agreed because they
were all the same constant — a test that would pass no matter what broke. It now asserts a
uniqueness floor and fails loudly if a pin degenerates that way. This is the third time in this
project a guard has been written that could not fail; the pattern is worth naming.

## 2. Roadmap B is a historically mixed calibration chain

Reconciling fresh calibrations against the archive turned up something larger than expected.
**Three different routines produced roadmap B's archived thresholds**, and which one a member got
depends on when and under which driver flag it was measured:

| variant | where |
|---|---|
| plain bisection | the whole STRESS point |
| refined, last secant iterate | pilot constants and interleaves, at `ec0d8e0` |
| refined, best of measured | pilot switches, at `aab80b7` |

The stress finding is the sharp one. Both drivers refine only when the operating-point name ends
in `_recal`, and the stress runs used `op_name='stress'`, so **every archived stress threshold is
plain bisection** and no `res6_policies_stress_recal` artifact exists. One consequence is visible
without any new measurement: archived stress `interleave-B1` sits at **+31.8 %**, outside the
±30 % envelope that eligibility requires.

The consequence for C is unambiguous. B's delays remain valid historical evidence *for B* —
nothing here retracts them — but they cannot be imported into C's matched comparison, because
they were measured at thresholds a different procedure chose. Regenerating all thirteen uniformly
stopped being a luxury and became the only defensible route.

## 3. The cap-independence property, measured rather than read

The reconciliation predicts that a member archived at `aab80b7` or later reproduces its threshold
*exactly* at HEAD. That rests entirely on one property: commit `5024d59`'s enlarged confirmation
cap must be applied only **after** `h` has been selected. I had read that off the source, which
does not license a scientific prediction.

`tests/test_calibration_cap_independence.py` now measures it. Three adversarial lenses attacked
the first version and none refuted the property — but all three found the supporting experiment
substantially **vacuous**: in six of eight cells the returned `h` was the bracket floor, where the
clamp pins it and nothing downstream could move it. Agreement there proves nothing.

The test now converges the bracket two-sided, checks `h` lands *off* the bisection grid so
best-of-measured genuinely selected a secant iterate, and uses a confirmation cap that actually
binds — it censors 11 of 16 runs and moves the ARL from 1975 to 713 while `h` stays bit-identical
at `1.0304499535745162`. It also asserts the converse, that the *search* cap does move `h`, so the
apparatus has demonstrated resolution rather than mere silence. `NULL_CAP_DEFAULT` is 150 000 at
`ec0d8e0`, `aab80b7`, `5024d59` and HEAD, so the search cap is held fixed across every comparison.

## 4. Twenty-two calibrations, twelve predictions, no failures

Predictions were pinned before the measurements that tested them, with the boundary recorded
explicitly: only `mid` at each point had been observed when the mechanism was identified, so those
two are retrospective and are not evidence for the rule.

Both `EXACT_H` predictions held **bit-identically** — `switch@300` at `3.8125` and `switch@1000`
at `3.439270080909095`. Ten `H_DIFFERS` predictions held for members archived under a different
selection rule. Nothing failed.

## 5. Two results the reconciliation made visible

**Uncensoring is not cosmetic.** `interleave-B10`'s archived pilot ARL of +16.4 % was a lower
bound with 3 of 128 runs capped. Uncensored it is **+23.6 %**, which turns a comfortable member
into a marginal one, 0.52 σ from the ceiling. A censored ARL does not merely bias the number; it
can make a marginal member look safe.

**`switch@300` was excluded from roadmap B on noise.** Note 21 recorded it as un-recalibratable at
+52.4 % and excluded it. At the *identical* threshold, C's protocol measures **+12.8 %**,
comfortably inside. The estimator change is not systematically biased — `switch@1000` reproduces
to 0.05 standard errors under exactly the same change — so the +52.4 % was an outlier draw from a
64-replicate confirmation, not a property of the schedule. `cal_age` confirmed with `2*R` = 64
replicates while `calibrate_refined` uses `2*confirm_R` = 128.

## 6. Eligibility, frozen

13 of 13 eligible at the pilot; 12 of 13 at stress, with `interleave-B1` out at **+37.9 %**. That
exclusion is robust rather than a censoring artifact: the archived value was +31.8 % with one run
capped, and uncensoring moved it *further out*, the direction correcting censoring must move it.
Every confirmation is uncensored, so no eligibility decision rests on a lower bound.

Four candidates sit within one standard error of the boundary and are named in the artifact:
`pilot/interleave-B10` at 0.52 σ, `stress/ext` at 0.50 σ, `stress/greedy` at 0.11 σ, and
`stress/interleave-B1` at 0.72 σ outside. Anything resting on those rows inherits the fragility.

The class stays frozen throughout. Eligibility removes a member on false-alarm-rate grounds, never
on performance, and it is decided by the calibration alone before any delay exists.

## 7. Process notes

The driver was restarted once, a few minutes in, for a real reason: it was not writing provenance
into the artifact. `sid_repro.print_banner` prints the revision and numerical stack to stdout, but
stdout is not the evidence — `res11_*.json` is, and it recorded only the config. Provenance is now
captured **at start** rather than at write time, so that a file created while a run is in flight
cannot retroactively relabel measurements taken from a clean tree. That is not hypothetical: I
added the eligibility freezer mid-run and would have tainted every cell.

Measurement from a dirty tree is now refused outright. This repository has produced `+dirty`
artifacts four times, each caught only afterwards; the guard costs one subprocess call.
