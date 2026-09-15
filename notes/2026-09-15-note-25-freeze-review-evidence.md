# Signals in Darkness — note 25 (15 Sept 2026): crossover estimators and the class-A zero set

Review of the v2.0 freeze draft exposed an overstatement about reproduction and an incomplete
inventory of zero-information rows. This note corrects the draft, clarifies the relationship
between v1.1's crossover table and its cited notes, and supplements C26's description of the
existing archive. It changes no frozen card, earlier note, claim status or archived output.
The evidence inspected is at revision `f377f6b883154f2a8e5591281ebffdfaadb32b22`.

## 1. Erratum to the draft's crossover-reproduction statement

The draft said the crossover rows leaving the headline were all “archived and reproduced”
in [res3](../analysis/outputs/res3_comparator.json), and that recovering their values needed
no new computation. That was too broad. For s = 0.3 and 0.5, the finite crossings in
[v1.1](../cards/v1.1-frozen.md) and res3 agree within about 1.1 %. At s = 1 they differ:

| C̄ | v1.1 frozen table | Note 01 | res3 geometric fit, 400-point grid | Note 02 series | Current run4 series, 500-point grid |
|---|---:|---:|---:|---:|---:|
| 0.4 | 40 | 34 | 34.283703 | 40 | 40.198368 |
| 0.5 | ≈30 | 26 | 25.839297 | not tabulated | not in the producer's contrast loop |
| 0.7 | 29 | 25 | 24.816289 | 29 | 28.636097 |
| 0.9 | 320 | 248 | 248.162892 | 323 | 322.862820 |

The quantities in the last four numerical columns are first-crossing grid estimates in
τ_c/c. They must not be interchanged with log-interpolated crossings or binary-HMM estimates.
[Run3](../analysis/runs/sid_run3.py) uses the geometric fit: I_mid_gp sets a = exp(−1/tcc),
matches r₁ through rho = r₁/a, then evaluates gp_rate_geom. That reproduces res3 exactly on
the current stack and supplies [note 01's](../notes/2026-09-02-note-01.md) rounded s = 1 values.
It does not reproduce v1.1's s = 1 column.

The review suggested no producer had been found for the frozen column. The wider record
supports a narrower conclusion: [note 02, Check 2](../notes/2026-09-02-note-02.md) explicitly
records geometric-fit versus series crossings of 34/40, 25/29 and 249/323 at C̄ = 0.4, 0.7
and 0.9. It names the large-s failure of the geometric shortcut and adopts the series for
v1.1. [Run4](../analysis/runs/sid_run4.py) contains that comparison, with six sinh terms,
1024 midpoint frequency samples and a 500-point correlation-time grid. Re-executing only
those pure definitions and that grid gives the last column above and reproduces note 02's
integer pairs at their displayed precision. Neither driver is imported as a module, so the
larger simulations and output-writing bodies are not run in this check.

This identifies the estimator distinction and existing support for three series rows; it
does not recover a producing record for every exact entry in v1.1. In particular, 320 is
not the current run4 grid value or note 02's 323, and C̄ = 0.5 is absent from run4's declared
contrast loop. As a separately labelled diagnostic, applying run4's same kernel and grid
at C̄ = 0.5 gives 30.547097, consistent with the approximate “≈30” but not evidence of how
that frozen entry was originally produced. No archived output is replaced by this diagnostic.

The geometric fit and the multi-term spectrum are also distinct from a strict single
m = 0 term: run3 matches the exact first lag, rather than substituting only the first sinh
coefficient. Note 02 documents the fit/series discrepancy directly, so the correction does
not depend on treating those two shortcuts as identical.

The same distinction matters for the retained headline numbers. C04 validates the spectral
comparator with exact r_k against the point-sampled binary reference; the archived C05
values and C08 thresholds instead use the geometric fit matching the exact first lag
([note 08](2026-09-04-note-08-comparator-vs-hmm-crossover.md) and
[run3](../analysis/runs/sid_run3.py)). Note 02's Check 2 supplies the link: crossover
differences within 2 % at the tested s ≤ 0.5 points, and a maximum relative rate difference
of 0.38 % at the map's mid-fringe-optimal τ over its tested grid, with different winners on
0.03 % of grid points. These bounds compare estimators; they are not a further binary
likelihood validation. Note 02 selected the series for v1.1's working figure formula, but
the archived map producer retained the geometric fit. The draft now states this chain
before the seed's verbatim F caveat.

**Disposition:** the s = 1 frozen entries are not reproduced by res3. The draft now points
to this distinction and records the remaining provenance limits, rather than presenting the
geometric values outside their stated useful regime as substitutes. The headline still
retains C05's stated scope; no additional crossover claim is promoted. The physical-map
record C08 and its separate finite-window validation caveat are unchanged.

## 2. Supplement to C26 and note 15: all 18 zero-information rows

[C26](../ledgers/status.yaml) and [note 15](../notes/2026-09-07-note-15-roadmap-E.md) list
zero class-A information at τ_c/T₂ = 0.05 and at 0.2 with η₀ ≥ 0.05. Those statements
are correct but incomplete. The full zero set in
[res9](../analysis/outputs/res9_identifiability_T2.json) contains 18 of its 36 rows:

| τ_c/T₂ | η₀ | C₀ values | Rows with I_A = 0 |
|---:|---|---|---:|
| 0.05 | 0.02, 0.05, 0.10 | 0.4, 0.5, 0.9 | 9 |
| 0.2 | 0.05, 0.10 | 0.4, 0.5, 0.9 | 6 |
| 1 | 0.10 | 0.4, 0.5, 0.9 | 3 |

This is an inventory on the committed finite scan, not a new universal zero-region theorem.
It includes both principal contrasts and servo-context C₀ = 0.9. The remaining 18 rows
have positive I_A, including the previously corrected τ_c/T₂ = 0.2, η₀ = 0.02 boundary.

The three previously omitted rows provide a particularly direct finite-scan counterexample:
ΔΓ_φ/(2η₀Γ̂) = 1.25 exceeds one, but none of the 40 interrogation times separates the
pointwise bands. Recomputing s_τ²/2 − 2η₀Γ̂τ in T₂ units gives a maximum margin of
−0.01879064549 over the committed scan. Their class-B candidate fractions are:

| C₀ | I_A | I_B / I_unc |
|---:|---:|---:|
| 0.4 | 0 | 8.726971 % |
| 0.5 | 0 | 8.879743 % |
| 0.9 | 0 | 10.367670 % |

I_unc is the known-baseline information under the same equal shot allocation. I_B remains
a best-of-candidates estimate and an upper bound on the true class-B infimum. These positive
candidates do not by themselves certify that infimum's positivity. The fast-noise ratio is
necessary but not sufficient for class-A separation on this scan.

**Disposition:** condition 4 of v1.1 fails on all 18 class-A zero rows under the stated
calibration and scan, not only at the shortest correlation time. The draft's zero inventory,
condition-4 disposition and baseline-class change log now include all three groups. C26 is
supplemented here rather than edited in place; no status is changed and C13 stays withdrawn.

## 3. Provenance and the future freeze marker

v1.1 and note 03 both entered Git at `81058de`, the archive import. Their import history
does not establish their writing order. The content establishes the relationship used in
the draft: [note 03 §4](../notes/2026-09-02-note-03.md#4-τ-scan-identifiability-corollary-card-item-3)
applies card v1.1's divergence to two classes, and its “Card implications” item 1 proposes
changing the admissible class. The draft now attributes that inference to the document.

At the inspected revision, the Git tags are `archive-2026-09-03`, `repo-v0.1.0` and
`repo-v0.2.0`. `card-v1.0` and `card-v1.1` occur as milestone labels, not Git tags, and the
milestones have no commit-hash field. The draft therefore proposes an **explicit new
convention**: an annotated `card-v2.0` Git tag on the eventual freeze commit. No tag or
milestone is created by this review pass.

## 4. Checks

- `tests/test_crossover_provenance.py` recomputes res3's geometric crossings and executes
  run4's pure kernels on its own declared grid to recover note 02's three fit/series pairs.
  It preserves the estimator distinction without changing either producer.
- `tests/test_numerical_invariants.py` now checks the exact membership of the 18-row zero
  set against the finite-scan guard, including the three ratio-1.25 rows. The earlier
  `unseparated_scan` check already contained that counterexample but did not name the set.

The existing shared-sensing regression checks still compare fresh information values with
all 36 res9 rows. The three test modules passed together: **55 passed in 2.48 s** on the
local Python 3.13.7 / NumPy 2.4.4 / SciPy 1.17.1 stack. This is a targeted check, not a
full-suite run or a runtime guarantee. The frozen cards, previous notes, ledgers, manifest and archived outputs
remain unchanged. This is an evidence clarification and draft correction, not a card freeze.
