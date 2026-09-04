# Signals in Darkness — execution note 08 (4 Sept 2026): two crossover estimators, and why they differ

Adopting `res2_partial.json` (note 07) archived a `crossover` key giving τ_c/c = 6.29 at
C̄ = 0.4, s = 0.5, while claim C05 reports 7.24 for the same operating point. Both are in the
repository, both are correct outputs of their own producers, and neither supersedes the other.
This note establishes what each measures and whether the difference is real.

**It is not.** The comparator value sits at the centre of the HMM estimator's own seed-to-seed
distribution. The archived 6.29 is one ordinary draw from a noisy estimator.

## 1. Two different estimators

| | comparator (C05) | HMM grid (`res2_partial.json` key `crossover`) |
|---|---|---|
| producer | `sid_run3.py` | `sid_run2.py` |
| mid-fringe rate | Gaussian-process closed form, geometric fit, deterministic | exact latent-AR(1) binary HMM, Monte-Carlo, N = 1.2 × 10⁵, one seed |
| τ grid | 400 points, log-spaced over [10^−0.5, 10³] | 9 points: 2, 3, 4, 5, 6, 8, 10, 14, 20 |
| root | first grid point above I_ext | linear interpolation between bracketing points |
| value at C̄ = 0.4, s = 0.5 | **7.24** | **6.29** |

They are not competing measurements of the same quantity to the same precision: one is a
deterministic evaluation of an approximate rate, the other a stochastic evaluation of the exact
rate.

## 2. The HMM estimator's spread

The crossover was recomputed with the HMM on the same coarse grid at eight seeds:

    seed  4: 6.286    seed 11: 7.711    seed 12: 7.055    seed 13: 6.450
    seed 14: 6.473    seed 15: 8.484    seed 16: 9.039    seed 17: 5.624

    mean 7.140   sd 1.177   s.e. of the mean 0.416   range 5.624 to 9.039

A single-seed HMM crossover therefore carries a standard deviation of about **1.2, i.e. 17 %**,
at this N. That is the expected size: note 02 check 3a records ≈ 5–10 % standard error on the
rate at N = 10⁵, and near the crossing d ln I_mid / d ln τ = 0.98, so a fractional rate error
transfers into an almost equal fractional error in the crossover location.

Against that distribution:

- comparator as published, 7.239 → **+0.08 sd** from the HMM mean;
- comparator log-interpolated, 7.177 → +0.03 sd;
- the archived single-seed value, 6.286 → −0.73 sd.

The two estimators agree. The apparent 15 % discrepancy is one draw of a σ ≈ 17 % estimator
landing below its mean, and 6.29 should not be read as evidence against 7.24.

## 3. Consequences, and what was deliberately not changed

The comparator is the more precise estimator here, which is what note 02 check 3a already
concluded for the rate itself ("the series form is the more precise number in every case"). C05
therefore stands on the comparator, and its numbers are unchanged.

`sid_run3.py` takes the first grid point above I_ext rather than interpolating, so its crossover
is biased high by up to one grid step — the log grid steps by 2.04 %. Log-interpolating gives
7.177 against the published 7.239. **The published estimator was not replaced**: doing so would
silently move a published number for a 0.9 % refinement. Both values are now stored side by side
in `analysis/outputs/res3_comparator.json`, as
`crossover_comparator_as_published` and `crossover_comparator_log_interpolated`, and the grid
step factor is stored with them so the bias is quantified rather than described.

The HMM-grid crossover keeps its own key in `res2_partial.json`, labelled in `SCHEMA.md` as
`sid_run2.py`'s own estimate and explicitly not C05's. Neither was deleted in favour of the
other.

## 4. Record

`sid_run3.py` now stores what it had only ever printed: the comparator crossover table (C05,
both estimators, with I_ext and the grid), the rate-check values behind
`figures/sid_midfringe_rate_check.png`, and the τ-optimised thresholds behind C08. C05 and C08
lose `[unreproduced-from-file]` — the archival gap is closed. Their scientific status is
unchanged by that: reproduction into a file is a records fact, not a promotion.
