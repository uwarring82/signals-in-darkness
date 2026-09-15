# Signals in Darkness — note 27 (15 Sept 2026): C08 fold erratum and review of the F plan

**Status:** The C08 implementation defect is confirmed deterministically. Note 26 is
not accepted as an executable F protocol. This note records the erratum, review findings
and preferred protocol choices; no likelihood, pilot or F result has been computed.

**Evidence snapshot:** `97e73b2`, annotated tag `card-v2.0`. The frozen card's SHA-256 is
`682560ba2cce9209b6996de34c108a79e49f5ba5f4f0d9f17bcb84349ad805da`.
The card and tag remain intact. The reviewed draft is
[note 26](2026-09-15-note-26-F-plan-draft.md).

## 1. Erratum: run3's map does not use run4's lag-1-matched fit

For `gp_rate_geom(rho, phi)`, the first binary lag is `rho*phi`. The
[run3 map](../analysis/runs/sid_run3.py) supplies `rho = r1/a1`, where `a1 = F(u)*phi`.
Its first lag is therefore `r1/F(u)`. The
[run4 fit](../analysis/runs/sid_run4.py) supplies `rho = r1/phi` and preserves `r1`.
Note 02's Check 2 compared run4's fit with the series, not run3's map implementation.
The finite-window factor is lost at leading order in the map's binary correlation.
At finite amplitude the map is not exactly a point-sampled comparator either.

This corrects the C08 descriptions in:

- [note 12, §4](2026-09-05-note-12-a2-noise-physics-provenance.md) and
  [pass 6](../labbook/2026-09-05-pass-6-noise-physics-provenance.md);
- the F caveat in the [seed](../cards/v2.0-seed.md) and
  [frozen v2.0 card](../cards/v2.0-frozen.md), including item 1, its figure specification
  and the validation row in its change log;
- [note 25, §1](2026-09-15-note-25-freeze-review-evidence.md),
  [pass 24's final review addition](../labbook/2026-09-15-pass-24-freeze-draft-evidence.md),
  [pass 25](../labbook/2026-09-15-pass-25-card-v2-freeze.md), and the original `card-v2.0`
  milestone summary in [milestones.yaml](../ledgers/milestones.yaml).

In particular, “C08 uses the correct ARMA-consistent covariance” and the extension of
“matches the exact first lag” to C08 are withdrawn. C05 is point-sampled (F = 1), so this
normalization defect does not affect its crossover calculation. C04's validation scope
also remains the exact-r_k comparator at its tested point-sampled cases.

The last review's model-generated sentence extended a correct C05 statement to C08.
The coding assistant accepted and froze it without checking run3's actual normalization.
The earlier claim in note 12 already made that mistake. This erratum records both the
review's contribution and the acceptance failure; responsibility is not transferred to
U. Warring as author of that review.

### Numerical extent and claim disposition

The two original scratch scripts have been recovered and preserved byte-for-byte in
[analysis/diagnostics](../analysis/diagnostics/README.md). Re-executing them reproduces
note 26's single-point ratios, all four stored threshold values, its continuously solved
thresholds and the candidate-point table. These are post-hoc deterministic diagnostics.
The continuous solve still optimizes over run3's discrete tau grid.

| Actual C0 grid value, rounded | Stored threshold | Archived form, continuous | Corrected fit, continuous | Series with F, continuous |
|---:|---:|---:|---:|---:|
| 0.4004 | 211.759 | 209.32 | 205.69 | 205.83 |
| 0.4960 | 139.980 | 137.61 | 133.98 | 134.06 |
| 0.6977 | 75.232 | 71.42 | 67.84 | 67.88 |
| 0.8994 | 44.842 | 44.71 | 41.19 | 41.20 |

The corrected-fit first crossings on the committed correlation-time grid equal the four
stored values. The grid step is about 10.9 %. The continuous series crossings move
−1.67 %, −2.58 %, −4.96 % and −7.84 % relative to the archived form. Equality of the coarse
thresholds does not validate the archived rate contours or optimal-time panels.

**Disposition:** retain C08 as a `result` only at the scope of its four quoted coarse-grid
thresholds, with this erratum attached in the claim ledger. Do not promote these continuous
diagnostics into new claims. The archived rate map is not a correct finite-window map and
must not be used as such in the manuscript. A corrected map needs a separately identified
producer/output and claim review; it must not silently overwrite res3 or its figure.
The old producer is retained to reproduce the historical artifact. The tagged card,
earlier notes, passes and original milestone summary are not rewritten; a correcting
milestone and current README/site pointers make this erratum discoverable.

**Replacement caveat for current use:** C08's archived mid-fringe implementation divides
the exact first-lag binary correlation by F(u). Its four quoted thresholds survive a
lag-1-fit correction on the stated coarse grid, but the archived rate map is not the
finite-window comparator. Binary-likelihood validation remains confined to C04's tested
point-sampled exact-r_k comparator; F remains open.

The [guard](../tests/test_c08_fold_provenance.py) evaluates the live run3 map call's arguments
through the AST. It requires the lag-one contract to reject that form at finite u and
accept run4's fit, and shows why F = 1 cannot expose the defect. This is an explicit
negative control, not a passing assertion that the defective producer is correct.

## 2. Findings that prevent accepting note 26 as written

1. **The E6 impossibility claim is false (§7).** If K2/K1 = 1.056286 and the true reference
   were 1.03 K1, then K1/R = 0.970874 and K2/R = 1.025520. Both fit inside ±5 %, even with
   arbitrarily precise intervals. Two positive comparators can both validate whenever
   their ratio is at most (1+δ)/(1−δ) = 1.105263 at δ = 5 %. E4/E5 do provide incompatible
   K1/K3 controls; E6 is a sensitivity point, not a forced failure. E3's 5.5 % gap is also
   not a forced failure under this rule.
2. **The shot rule is not yet executable (§6).** No mapping assigns variance estimates
   from P1/P2 to each evaluation point. Cost and variance can change with the parameters.
   Pilot length, batch lengths, variance-stability handling and the budget are unset.
   The formula uses a normal quantile although evaluation uses 16-seed t intervals;
   using t(15) instead increases that component of planned N by about 18.3 %. Define total
   N versus shots per seed, round to complete equal-length replicates, and prohibit
   outcome-driven top-ups. A cost cap cannot substitute for those definitions.
3. **The boundary points are approximations (§5).** `f_design.py` hard-codes C0 = 0.4/0.5,
   tau/T2 = 0.512 and rounded stored thresholds. It does not extract the archived winner.
   The actual columns are 0.4003932584 and 0.4959550562; the common winner is
   tau/T2 = 0.5121956665. At the latter column the effective contrast is 0.2971656251,
   not the table's 0.300. Freeze full-precision inputs derived from the archive, or label
   the current points nearby design examples and abandon the exact-provenance claim.
4. **The outcome table overstates what can close (§7).** “Every evaluated point” could
   exclude required points skipped under the cap. Require every mandatory point to be
   attempted and resolved before any campaign-level closure. Stress-point validation
   licenses only those points; unattempted boundary points leave C08's finite-window
   binary-likelihood validation open. The K2 row also says s ≤ 0.5 although E5 has s = 1;
   enumerate the actual tested tuples. K3 failure is a rate comparison, not a necessary
   test of the algebraically established covariance defect. Failure must use the corrected
   caveat above, not the frozen caveat now known to be false.
5. **Reference and convergence rules need precise implementation contracts (§§3–4).** The
   pair-state recursion does have O(M²) work per shot: summing out the older coordinate
   prevents an M²-by-M² transition. But the grid filter is an approximation to the exact
   latent model. The Gaussian weights used by `make_hmm` are not exactly the stationary
   distribution of its row-normalized finite-grid transition. Specify initialization and
   handle the distinction between a stationary simulated process and finite-history
   predictive likelihoods; stationarity alone does not eliminate finite-record rate bias.
   Specify common-record length and seeds for grid comparisons, a final grid, and what
   happens on failure. Near-zero log increments need an absolute as well as a relative
   nesting tolerance. Also check series truncation/frequency convergence independently.
6. **Interval and scope edge cases are missing.** If R_lo ≤ 0, the proposed ratio interval
   cannot be formed as written; report UNRESOLVED and do not divide. A failed numerical
   check must prevent statistical validation. The 95 % intervals are pointwise, not a
   simultaneous coverage statement for every reported verdict. The §1 “within 0.2 %”
   point-sampling comparison applies to its four physical examples, not all finite-window
   inputs: K3/K4 is 1.05257 at E5 and 1.08453 at E6. The proposed guard
   `K3 = K1*(K3/K1)` is tautological unless the ratio is an independently fixed reference;
   use the actual lag-one contract and independent deterministic controls instead.

These findings do not contradict the proposed OU simulator's independence from the ARMA
mapping, or the algebraic mapping at the candidate points. They concern the executable
protocol and what its eventual evidence would license.

## 3. Preferred decisions for the revised plan

These are review decisions to incorporate before freezing a protocol, not execution
authorization or a claim that an implementation has passed its checks.

| Decision | Disposition |
|---|---|
| C08 | Apply §1's erratum; retain the four coarse thresholds with that limited scope. A corrected rate-map artifact is a separate deterministic workstream. |
| Comparators | Include K1, K2, K3 and K4, the point-sampled series with A = 1. K4 is a diagnostic control, not a finite-window truth model. All use the same eventual reference interval. |
| Evaluation points | E3–E5 mandatory. E1/E2 conditional as a pair, using exact archived-grid inputs, with their unattempted status explicit if cost excludes them. Defer E6 from the initial campaign; it supplies no forced-failure control at 5 %. |
| Pilot points | Prefer variance-only pilots at the selected evaluation parameters on disjoint seeds. That resolves the unspecified P1/P2 variance transport without consulting measured means. P1/P2 can remain optional implementation checks, not the source of per-point precision guarantees. |
| Precision | Retain δ = 0.05, κ = 1/4 and R = 16. Use t(15), not z, for sizing; total N is a multiple of 16. Freeze a conservative variance-estimation rule and per-seed minimum length before the pilot. The realised interval, not planned N, decides the verdict. |
| Initial compute envelope | At most eight aggregate hours with one numerical thread; pilot/validation work at most 30 minutes of that total, and at most two hours of evaluation per point. Schedule E3, E4, E5 first; admit E1/E2 together only if both fit the remaining predicted budget. On a cap, report incomplete/not attempted, never accept a partial sample at the intended precision. This is a bounded first campaign, not a prediction of feasibility. |
| Grid convergence | Retain 0.001 K1 as the maximum absolute paired rate change across M = 121/241 and L = 5/7; use M = 241, L = 7 for evaluation only after the check passes. Fix record lengths/seeds and a finite-history check before acceptance. No automatic grid or sample-size escalation after seeing evaluation means. |
| Seed blocks | Enumerate point indices p = 0…4 for E1…E5 and r = 0…15. Proposed pilot seeds: 13000+20p+r; evaluation: 14000+20p+r; numerical checks: 15000+20p+r. Reserve 15900 for N0. Store the explicit arrays and RNG identity; verify pairwise disjointness. This replaces the draft's incomplete phase assignment. |
| Files | Retain `analysis/lib/sid_arma.py`, `analysis/runs/sid_run13.py`, `analysis/protocol_F.json`; use `res13_F_pilot.json`, `res13_F_numerical_checks.json`, and `res13_F_evaluation.json` under `analysis/reproduction/`. None is created or frozen in this pass. |
| Execution stack | Use the Python 3.12 environment specified in `environment.yml`, with its NumPy/SciPy pins and one BLAS thread. Record actual patch versions, BLAS, architecture and thread settings. The local Python 3.13 review checks are not execution-stack certification. |

Before acceptance, revise note 26 around these choices, fix the remaining sampling and
reference contracts in §2, and commit the diagnostic producers. Then freeze the complete
protocol and its digest. A protocol hash must bind all points, numerical settings, rules,
seeds and resource caps, not just the prose title.

Using the same parameter coordinates for variance pilots does not reuse evaluation data:
the streams are disjoint, the points are fixed in advance, and measured reference means
remain excluded from the sample-size rule. The remaining pilot length, batching and
finite-history choices still need to be specified; this review does not silently fill
those gaps by treating the preferred decisions as an accepted protocol.

## 4. Review evidence and limits

The original two scripts reproduce note 26's printed deterministic tables on the local
Python 3.13.7 / NumPy 2.4.4 / SciPy 1.17.1 stack.
[review_F_plan.py](../analysis/diagnostics/review_F_plan.py) produces the additional
point-sampling ratios, E6 counterexample and exact boundary inputs above.
[The focused tests](../tests/test_c08_fold_provenance.py) check the lag-one failure and
positive control, point-sampled nesting, the E6 counterexample, the restricted K3/K4
scope, deterministic-series convergence and the frozen card hash. They do not implement
or validate an ARMA filter. No numerical archive or old frozen record is replaced.
The review and its implementation used model assistance.

Local validation: 66 tests passed across the fold-provenance, crossover-provenance,
numerical-invariant and shared-sensing modules; 126 ledger/site/public-prose/tutorial-page
tests also passed. The link audit resolved 73 local links and anchors. All 126 pre-existing
files under cards, notes, labbook, analysis, figures and tutorials were byte-identical to
the freeze revision; only the current claim ledger's C08 errata field and an appended
milestone change the scientific metadata. The original milestone prefix and `card-v2.0`
tag target were checked unchanged. The full suite and analysis drivers were not rerun.
