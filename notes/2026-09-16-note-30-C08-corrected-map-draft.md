# Signals in Darkness — note 30: the corrected mid-fringe map — DRAFT r2 for review

**Revision log**

| r | Date | Commit | Change |
|---|---|---|---|
| 1 | 16 Sept 2026 | `19e3c46` | First draft: the producer, the three forms, the threshold comparison. |
| 2 | 17 Sept 2026 | `2f10eb7` | The review's numerical finding adopted. A fourth form separates the numerical correction from the normalisation correction; the contour statistic is corrected from 22 % to 34.4 %; a second, milder cancellation in `rk_exact` is disclosed; the "differ only in the normalisation" sentence is narrowed to the fit; the five decisions are recorded as adopted. |
| 3 | 17 Sept 2026 | this draft | Three record corrections: the small-signal limit carries its denominator, ρ²a²/(2(1−a²)); the artifact's `forms` metadata lists `archived_stable`; the two high-precision references are distinguished, and the precision finding is stated for the tested cell rather than as a uniform bound. The `rk_exact` decision is recorded as retained. |

**Status: DRAFT r2.** A deterministic recomputation. No claim changes here: C08 keeps the scope note
27 gave it, its four quoted coarse-grid thresholds. `sid_run3.py`, `res3_comparator.json` and the
figure are untouched, and the guard pinning the archived defect still passes.

## 1. What was built

[`analysis/runs/sid_run14.py`](../analysis/runs/sid_run14.py) reads run3's grid **from run3's own
source through the AST** and computes four rate forms on it, τ-optimised against the exact
dark-extremum rate exactly as run3 does:

| Form | Normalisation | Arithmetic | Role |
|---|---|---|---|
| `archived` | ρ = r₁/(F φ) | historical | reproduction control for the committed artifact |
| `archived_stable` | ρ = r₁/(F φ) | cancellation-free | isolates the numerical correction |
| `fit` | ρ = r₁/φ | cancellation-free | the correction: first lag r₁ |
| `series` | six-term sinh series, A = F(u) | — | exact r_k; also replaces the higher lags |

Output: `analysis/reproduction/res14_corrected_mid_fringe_map.json`, 13 s.

**Provenance control.** The `archived` form recomputed here reproduces the committed artifact
exactly: all six stored thresholds and the win fraction `0.20037037037037037` are identical.

## 2. Three separate effects, no longer mixed

r1 reported a single "archived versus fit" statistic. That mixed an arithmetic artefact with the
scientific change. Separated:

| Change | Median shift | Max | Cells beyond 0.01 dec | Winner flips |
|---|---:|---:|---:|---:|
| **Numerical** (`archived` → `archived_stable`) | 4.6×10⁻¹¹ dec | 8.50 dec | 740 / 8100 | **0** |
| **Normalisation** (`archived_stable` → `fit`) | **0.128472 dec = 34.42 %** | 0.825 dec | 6349 / 8100 | **30** |
| **Higher lags** (`fit` → `series`) | 3×10⁻⁵ dec | 3.4×10⁻⁴ dec | 0 | 2 |

The corrected contour statistic is therefore **34.4 %, not the 22 % reported in r1**: the old figure
was depressed by the cancellation. The arithmetic alone flips no winner and moves no threshold — it
distorts only rates that are already negligible — while the normalisation flips 30 winners and moves
the win fraction from 0.200370 to 0.204074.

**Thresholds.** All four forms agree in the four columns C08 quotes:

| C̄₀ | archived | archived_stable | fit | series |
|---:|---:|---:|---:|---:|
| 0.4004 | 211.759 | 211.759 | 211.759 | 211.759 |
| 0.4960 | 139.980 | 139.980 | 139.980 | 139.980 |
| 0.6977 | 75.232 | 75.232 | 75.232 | 75.232 |
| 0.8994 | 44.842 | 44.842 | 44.842 | 44.842 |
| 0.9950 | 40.43352203934773 | 40.43352203934773 | **36.45841237070733** | **36.45841237070733** |

The last row is **outside C08's four quoted thresholds**. It is the only threshold the correction
moves, by −9.8 %, and it is the normalisation that moves it, not the arithmetic.

## 3. The cancellation, and its cause

The archived closed form evaluates R = −½·log(α/(1+b²)) with α = 1 + a² − 2ρa². For small ρa the
numerator and denominator agree to machine precision, so the result is roundoff. The same closed
form reduces exactly, with t = a(1−2ρ) and S = √((1−a²)(1−t²)):

  R = −½·log((1 + a t + S)/2),  and since (1 − a t)² − S² = (a − t)² exactly,
  **R = −½·log1p(−ε),  ε = (a − t)² / (2(1 − a t + S)),  a − t = 2ρa.**

No step subtracts near-equal quantities. At fixed a < 1 and ρ → 0 this gives

  R ~ ρ²a² / (2(1 − a²)) = ½ Σ_{k≥1} (ρa^k)²,

which reduces to ½ρ²a² only when a is small as well; r2 stated the limit without its denominator.
The implemented formula gives the correct limit either way.

At the review's cell (C̄₀ = 0.05, τ_c/t_dead = 0.1), maximised over the same τ grid:

| Evaluation | Mid-fringe rate |
|---|---:|
| historical arithmetic | 1.0761908808×10⁻¹⁶ |
| stable arithmetic | 2.2932836135×10⁻²⁴ |
| 70-digit reference | 2.2932836576×10⁻²⁴ |

**Calling this a dead channel, as r1 did, named the symptom and missed the cause.** The channel is
indeed negligible there, but the reported number was the arithmetic's own noise floor.

### A second cancellation, disclosed

The stable value still differs from the 70-digit reference by 1.9×10⁻⁸. That residual is not in the
rate formula: `sid_lib.rk_exact` computes r₁ as exp(−s²(1−a₁)) − exp(−s²(1+a₁)), which loses
9.6×10⁻⁹ relative at this cell, and the rate goes as r₁². The algebraically equivalent
C̄²e^{−s²}sinh(s²a₁) is accurate to 1×10⁻¹⁶ there.

`rk_exact` is committed arithmetic shared by run3, run4 and the roadmap-F work. **Decision
(review): retain it here, with this disclosure.** The measured residual does not warrant changing a
shared library or roadmap F, and changing it would break comparability with the archive.

The precision statement belongs to the tested cell, not to the map: **at C̄₀ = 0.05,
τ_c/t_dead = 0.1 the stable value agrees with a 70-digit evaluation to 1.9×10⁻⁸**, and that gap is
r₁'s cancellation entering as r₁². It is a measurement at one cell, not a uniform error bound, and
it moves no winner and no threshold.

**The two high-precision references differ in their last digits, for a reason.** The review's check
held the floating-point ρ fixed and evaluated the rate formula alone; this note's recomputes r₁ at
high precision as well. The first isolates the rate formula, the second isolates `rk_exact`, and
their difference is exactly the second cancellation. Both confirm the stable rate formula.

## 4. Scope

**Roadmap F is OPEN.** Gate 3 passed its checks and pilots; no comparator has been validated against
the exact finite-window binary likelihood, and F's eventual pointwise verdicts would not
automatically validate this map. This corrects a comparator's lag-one normalisation and an
arithmetic defect; it establishes no finite-window truth model.

## 5. Implementation notes

- **The grid is run3's**, evaluated from run3's own assignments; a test checks it against the
  archived grid arrays.
- **run3's guard is kept**: taus with a₁ ≤ 1e-12 contribute zero in every form.
- **One overflow avoided**: the series prefactor (s²F)^11 is not representable on run3's grid — at
  τ_c = 0.1, τ = 30, F ≈ 6×10¹²⁷ — although F and φ ≈ 2×10⁻¹³⁵ are ordinary and their product is
  small. The kernel is written in a₁ = Fφ.
- **One writer**, through `sid_repro.reproduction_path`; the archive is opened read-only, and a test
  hashes it around a run.

## 6. Decisions, as adopted from the review

1. **C08's scope is retained; no new claim is created.**
2. **The errata pointer** gains the corrected artifact and this note, after this numerical revision.
3. **The 0.995 column** is stated explicitly, as lying outside C08's four quoted thresholds.
4. **The figure is deferred.**
5. **The artifact is committed**, regenerated from the clean committed producer. (The r1 artifact
   recorded `29302f6+dirty`.)
6. **`sid_lib.rk_exact` is retained** as it stands, with the §3 disclosure stated for the tested
   cell. The shared library and roadmap F are not touched.

## 7. Independent verification by the review

The review reproduced all three r1 maps, ran the 22 targeted tests, and refined the series to 12
terms and 4096 frequencies: **no winner and no threshold changed**, and the largest relative change
in the optimised series rate was 9.44×10⁻⁵. It also supplied the dead-corner cell and its 70-digit
value, which this revision reproduces.

## 8. Validation

- 18 tests in [`tests/test_c08_corrected_map.py`](../tests/test_c08_corrected_map.py): the grid
  against the archive; the historical form against `sid_lib.gp_rate_geom` elementwise; stable
  against historical away from the cancellation; **the stable form against a 70-digit evaluation at
  the review's cell**, with the historical form shown to be wrong there by a factor of 10⁸; the
  second `rk_exact` cancellation; the series kernel against run4's; the overflow statement; the
  lag-one contract; **all four forms reproducing the committed thresholds in C08's four columns**;
  the changed 0.995 column separating the two normalisations; the artifact's separation of the
  numerical and normalisation effects; the archive left byte-identical; and an unknown argument
  refused.
- The fold-provenance guard still rejects the archived form, which is why it is kept.

**Not done:** no figure, no claim change, no public-prose change beyond the ledger's errata pointer.
