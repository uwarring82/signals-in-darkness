# Signals in Darkness — execution note 20 (8 Sept 2026): the recalibrated pilot, and what survives

Note 19 sent the pilot chain back for recalibration because two rows breached the ±30 % matched-ARL
envelope. It has been recalibrated, all seven rows now pass, and the conclusions change twice — once
when the numbers arrive, and once again when their uncertainties are propagated. The second change
matters more than the first.

## 1. The recalibration

`calibrate_refined` bisects, then runs a secant root-find on ln(ARL) versus h. The first version
interpolated *inside* the bisection bracket and failed on exactly the two rows it was written to
fix, returning thresholds **bit-identical** to plain bisection — the signature of a silent fallback.
The bracket had converged entirely above the crossing, so the interpolation fraction fell outside
[0, 1]. A refinement confined to a bracket cannot repair a bracket that has already excluded the
root, and noisy downward-biased probes are exactly what produces one.

| policy | recal h* | ARL | miss | archived h* |
|---|---|---|---|---|
| oracle-mid(tc=20) | 4.285106 | 29 308 | −2.3 % | 4.359 |
| interleave-B10 | 3.542105 | 34 923 | +16.4 % | **3.55** |
| extremum-only | 3.775250 | 33 930 | +13.1 % | 3.734375 |
| interleave-B1 | 3.366558 | 30 610 | +2.0 % | 3.421875 |
| learner-mid | 3.343144 | 24 563 | −18.1 % | 3.421875 |
| oracle-mid(tc=1) | 1.564421 | 32 907 | +9.7 % | 1.546875 |
| oracle-mid(tc=5) | 3.174060 | 25 817 | −13.9 % | 3.421875 |

No envelope breaches, no bracket failures, zero capped delay runs.

## 2. What the recalibration says about C17

Every archived threshold, **including both withdrawn ones**, lies within about 2 % of the converged
value — `3.55` against `3.542105` is 0.2 % — with `oracle-mid(tc=5)` the sole outlier at 7.2 %. The
documented five-iteration bisection, by contrast, lands 5–9 % away on precisely the two rows that
were withdrawn, and outside the envelope.

Three independent lines now agree: the withdrawn values are better calibrated than their documented
replacements; `3.55` is not a reachable output of that bisection's lattice at all; and a converged
root-find lands essentially on it. **The archive looks right and the procedure record looks wrong.**

This does not un-withdraw C17. Its subject is provenance, and an unreproducible number stays
unreliable however well a later measurement agrees with it — agreement is not a substitute for
knowing where a number came from. But the record currently reads as though those values were
defective, and that is not what the evidence says. Wording left to the owner.

## 3. The result changes, then changes back

With the recalibrated benchmark the pilot's point estimates put a hedge first: interleave-B1 at
1.60 against fixed-extremum at 1.63. Read as an ordering, that would have inverted C11.

It does not resolve. Propagating uncertainties from the delay standard errors of numerator **and**
benchmark:

| policy | pilot worst case | vs fixed-extremum |
|---|---|---|
| interleave-B1 | 1.60 ± 0.17 | 0.1 σ — not resolved |
| switch@300 | 1.61 ± 0.17 | 0.1 σ — not resolved |
| **fixed-extremum** | **1.63 ± 0.19** | — |
| interleave-B10 | 2.02 ± 0.21 | 1.4 σ worse — not resolved |
| switch@1000 | 2.55 ± 0.28 | **2.7 σ worse — resolved** |
| learner-mid | 6.98 ± 1.05 | **5.0 σ worse — resolved** |

**C11 survives, and its own closing clause was the right reading all along**: ARL precision does not
order them. A 0.03 difference on ± 0.25 is not a finding. Reading point estimates as an ordering is
the same error as reading a fixed mean as a fixed distribution (pass 12) and reading matching
optimiser starts as convergence (pass 14) — the third instance in a week of treating a number as a
conclusion without asking what its uncertainty permits.

## 4. What is genuinely established

The same propagation at the stress point:

| policy | stress worst case | vs fixed-extremum |
|---|---|---|
| **switch@1000** | 1.51 ± 0.18 | **3.1 σ better — resolved** |
| interleave-B1 | 1.87 ± 0.26 | **2.2 σ better — resolved** |
| interleave-B10 | 2.01 ± 0.25 | 1.9 σ — not resolved |
| switch@300 | 2.19 ± 0.30 | 1.4 σ — not resolved |
| fixed-extremum | 2.88 ± 0.40 | — |
| learner-mid | 4.95 ± 0.65 | 2.7 σ worse — resolved |

So "four of five hedges beat it" was also a point-estimate count; **two of five are resolved**, and
C27 is corrected accordingly.

What survives is sharper than the claim it replaces. **`switch@1000` reverses with both directions
resolved**: 2.7 σ *worse* than fixed-extremum at the pilot, 3.1 σ *better* at the stress point, with
both operating points calibrated inside the envelope. That is a reversal of a resolved ordering, not
of point estimates, and it is a statement about one named schedule rather than about hedging in
general — because at the pilot no hedge is resolvedly better, and at the stress point only two of
five are.

## 5. Claims

- **C09** → `result`. The crossover between τ_c/c = 5 and 20 holds on a fully matched chain.
- **C11** → `result`, unchanged in substance, restated in terms of what resolves.
- **C27** → `result`, corrected from "four of five" to the two that resolve.
- **C28** → `result`, narrowed from "the ordering inverts" to the `switch@1000` reversal, which is
  the part that is actually resolved in both directions.
- **C29** numbers updated to the recalibrated chain: 0.96× at τ_c/c = 20, 1.13× at 5, 1.49× at 1.
