# Signals in Darkness — note 30 (16 Sept 2026): the corrected mid-fringe map — DRAFT for review

**Status: DRAFT.** A deterministic recomputation, proposed for review. No claim changes here: C08
keeps the scope note 27 gave it, its four quoted coarse-grid thresholds. The archived producer
`sid_run3.py`, its artifact `res3_comparator.json` and its figure are untouched, and the guard that
pins the archived defect as a negative control still passes.

## 1. What was built

[`analysis/runs/sid_run14.py`](../analysis/runs/sid_run14.py) is the separately identified producer
note 27 §1 asked for. It reads run3's own grid **from run3's source through the AST**, so the two
producers cannot drift apart, and computes three rate forms on it:

| Form | Fitted process | First binary lag |
|---|---|---|
| `archived` | `rho = r1/(F phi)`, `a = phi` — sid_run3's call | `r1/F(u)` — the defect |
| `fit` | `rho = r1/phi`, `a = phi` — run4's `gp_rate_geomfit` | `r1` — the correction |
| `series` | six-term sinh series, `A = F(u)`, 1024 frequencies | exact `r_k` |

Each is τ-optimised against the exact dark-extremum rate exactly as run3 does. The output is
`analysis/reproduction/res14_corrected_mid_fringe_map.json`; the run takes 9.3 s.

**Provenance control.** The `archived` form recomputed here reproduces the committed artifact
exactly: all six stored thresholds and the win fraction `0.20037037037037037` are identical, not
merely close. The corrected forms therefore differ from the archive only in the normalisation.

## 2. What the correction changes

**The thresholds C08 quotes do not move.** Under both corrected forms:

| C̄₀ column | Archived | Corrected fit | Exact-r_k series |
|---:|---:|---:|---:|
| 0.1987 | 901.688 | 901.688 | 901.688 |
| **0.4004** | **211.759** | **211.759** | **211.759** |
| **0.4960** | **139.980** | **139.980** | **139.980** |
| **0.6977** | **75.232** | **75.232** | **75.232** |
| **0.8994** | **44.842** | **44.842** | **44.842** |
| 0.9950 | 40.434 | 36.458 | 36.458 |

The four bold rows are C08's claim, and they are unchanged, which is what note 27 predicted from the
continuous solve. The correction is not vacuous, though: the C̄₀ = 0.995 column moves down by 9.8 %,
and it is only the 10.9 % grid step that keeps the other columns still.

**The map underneath does move.**

- Winner flips: 30 of 8100 cells between `archived` and `fit` (0.37 %), 28 between `archived` and
  `series`, and 2 between `fit` and `series`.
- Win fraction: 0.200370 archived, 0.204074 fit, 0.203827 series.
- Rate contours: the median absolute change in log₁₀(R_mid/R_ext) from `archived` to `fit` is 0.085,
  about 22 % in the ratio, reaching +0.78 decades. This is the quantitative form of note 27's
  warning that the archived rate contours and optimal-time panels are not validated by the survival
  of the coarse thresholds.

**The two corrected forms agree where it matters.** They give identical thresholds, win fractions
within 2.5×10⁻⁴, and the same winner in 8098 of 8100 cells. Their largest log-ratio difference, 7.7
decades, is at τ_c/t_dead = 0.1, C̄₀ = 0.05, where the mid-fringe rate is 1.1×10⁻¹⁶ against an
extremum rate of 1.2×10⁻¹⁰: a dead channel, not a disagreement about a winner.

## 3. Scope

**Roadmap F is OPEN.** Gate 3 passed its numerical checks and pilots, and no comparator has been
validated against the exact finite-window binary likelihood. This work corrects a comparator's
lag-one normalisation; it does not establish a validated finite-window map, and neither corrected
form is a truth model. If F closes VALIDATED at E3–E5, that licenses K1 at those tuples only; the
C08 boundary points E1/E2 exceed their cost cap and will carry no verdict, so the boundary question
stays open regardless.

## 4. Implementation notes worth a reviewer's eye

- **The grid is run3's, not a retyped copy.** `run3_grid()` evaluates run3's own assignments for
  `T2`, `td`, `gs`, `C0s`, `tcs` and `taus`. A test checks the result against the archived grid
  arrays.
- **run3's guard is kept.** Taus with `a1 <= 1e-12` contribute zero in every form, as in run3, so
  the two maps drop the same taus.
- **One overflow had to be avoided.** The series prefactor `(s² F)^(2m+1)` is not representable on
  run3's own grid: at τ_c = 0.1 and τ = 30, u = 300 gives F ≈ 6×10¹²⁷, so `(s² F)^11` overflows,
  although F and φ ≈ 2×10⁻¹³⁵ are both ordinary numbers and their product is small. The kernel is
  therefore written in `a1 = F φ`, which is algebraically identical and stays below 10⁻³ there. A
  test pins both halves of that statement.
- **The producer writes once,** through `sid_repro.reproduction_path`, and opens the archive
  read-only. A test hashes `res3_comparator.json` around a run.

## 5. Decisions I need

1. **Claim disposition.** I propose no new claim, per note 27: hold `res14` as a corrected
   diagnostic artifact until F closes. The alternative is a new claim for the corrected thresholds,
   which I do not recommend while the comparator itself is unvalidated.
2. **Ledger pointer.** Add `res14_corrected_mid_fringe_map.json` to C08's errata field as the
   corrected recomputation? The field currently points only to note 27.
3. **The 0.995 column.** State the 40.434 → 36.458 move in the erratum? It lies outside C08's four
   quoted thresholds but shows the correction has teeth.
4. **Figure.** None produced. A corrected figure would need its own name and a caption stating that
   it is not a validated finite-window map; I would rather wait for F.
5. **Archiving.** The artifact is in `analysis/reproduction/`, which git ignores. Commit it
   explicitly, as we did for the Gate-3 artifacts, or leave it reproducible-on-demand at 9.3 s?

## 6. Validation

- 8 new tests in [`tests/test_c08_corrected_map.py`](../tests/test_c08_corrected_map.py): the grid
  against the archive, the vectorised rate against `sid_lib.gp_rate_geom` elementwise, the series
  kernel against run4's kernel to 10⁻¹², the overflow statement, the lag-one contract separating
  the two forms, both corrected forms reproducing two committed thresholds at full τ_c resolution,
  the archive left byte-identical by a run, and an unknown argument refused.
- The existing fold-provenance guard still passes: the archived form is still rejected by the
  lag-one contract, which is the point of keeping it.

**Not done:** no figure, no claim change, no ledger edit, no public-prose change.
