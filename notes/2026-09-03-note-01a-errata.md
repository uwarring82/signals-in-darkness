# Signals in Darkness — execution note 01a (3 Sept 2026): errata to note 01 §1

**Erratum: contrast dependence of the extremum expansion error**

**Applies to:** frozen task card v1.1, execution note 01 §1, and claim C01.
**Status:** C01 withdrawn.

Note 01 is left as written for provenance. The statement below supersedes the corresponding passage.

## The withdrawn statement

Claim C01 stated that the leading-order extremum information was within 6 % of the exact Bernoulli divergence whenever

    q = s² C̄ / (1 − C̄²) ≤ 0.06,

and within 20 % up to q = 0.17. These were presented as contrast-independent numerical accuracy bounds. That statement is false.

At q = 0.06 the relative overestimate I_LO/I_exact − 1 is:

| C̄ | 0.3 | 0.4 | 0.5 | 0.7 | 0.9 |
|---|---|---|---|---|---|
| error | 10.1 % | 7.3 % | 5.6 % | 3.6 % | 2.4 % |

The original numerical check sampled only contrasts for which the 6 % statement happened to hold — the A grid of `sid_core.py` starts at C̄ = 0.5. It did not test the project's reference parity contrast, C̄ = 0.4.

The adjacent 20 % statement has the same defect. At q = 0.17 the corresponding errors are 30.5 %, 21.6 %, 16.3 %, 10.3 % and 6.8 %.

## Why

The reason is visible in the first omitted term. With I_LO = C̄²s⁴ / (8(1 − C̄²)), the exact divergence satisfies

    I_exact / I_LO = 1 − k s² + O(s⁴),    k = 1/2 + C̄² / (3(1 − C̄²)).

Consequently q alone does not define a uniform relative-error bound unless a contrast range is also specified.

At the reference contrast C̄ = 0.4, direct comparison with the exact Bernoulli divergence gives:

- 6 % accuracy only for approximately q ≤ 0.0497;
- 20 % accuracy only for approximately q ≤ 0.1583.

## What stands and what does not

The exact extremum divergence remains correct, as does its small-s asymptotic expansion. What is withdrawn is the claimed contrast-independent numerical accuracy range. All working calculations should use the exact divergence. Any figure, validity overlay, or downstream classification that used the withdrawn bounds must be audited before release.

The replacement numerical claim is entered separately, and only after the expanded deterministic calculation and its stored output are committed. No random seed applies.

## Record

The contrast-dependent calculation is section A2 of `analysis/runs/sid_core.py`, extending the existing core calculation rather than adding a driver; its rows (C̄, error at q = 0.06, error at q = 0.17, q for 6 %, q for 20 %, k) are stored in `analysis/outputs/res1_core.json` under key `A2`. Deterministic; no seed applies.

The coefficient k was confirmed independently at 60-digit precision, agreeing with the closed form to 13 significant figures at C̄ = 0.3, 0.4, 0.5 and 0.9. The double-precision check degrades below s ≈ 0.02 through cancellation in the Bernoulli divergence, which is why the closed form rather than a numerical fit is quoted here.
