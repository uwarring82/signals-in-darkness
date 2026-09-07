# Output schemas

## Representation (all files)

Every stored output is **strict JSON**: no `NaN`, `Infinity` or `-Infinity` tokens, which
RFC 8259 does not permit and conforming parsers reject. Any non-finite result that is not one
of the two declared cases below is a calculation error and stops the producing run rather than
being written (`allow_nan=False` on every writer). `tests/test_output_schema.py` enforces this
on every `analysis/outputs/*.json`.

Two distinct things must not be conflated:

- **`null` means undefined, missing, or not applicable** — a quantity that was not measured,
  or one for which no value exists. Nothing else.
- **A known limiting case carries an explicit sentinel string**, currently
  `"positive-infinity"`. An infinite limit is a *value the calculation deliberately visited*,
  not an absence, and writing it as `null` would erase that distinction. Consumers must test
  for the sentinel explicitly.

*Representation migration, 4 Sept 2026.* `res1_core.json` previously stored four `NaN`
tokens and `res7B_servo.json` one `Infinity`; both files were therefore invalid JSON. The
four undefined delay entries now carry `null`, and the infinite coherence carries the
sentinel `"positive-infinity"`, both written by the producers rather than by editing the
archive. No finite value changed meaning; the former artifacts remain in git history.
Recorded in `notes/2026-09-04-note-05-representation-migration.md`.

## Producing stack

The archive is deliberately **mixed-provenance**. Files are not regenerated to make it
homogeneous: that would replace valid historical outputs with values differing only in the
twelfth significant figure, for no scientific gain. What matters is that each artifact says
which stack produced it, and that the whole archive reproduces within the criteria declared in
`tools/compare_reproduction.py` under the pinned environment. It does; see
`notes/2026-09-04-note-07-pinned-certification.md`.

| file | produced by | reproduces under the pinned stack |
|---|---|---|
| `res1_core.json` | python 3.11.11 / numpy 2.2.4 / scipy 1.15.2 (3 Sept 2026) | 1.7e-12, tolerance 1e-9 |
| `res2_partial.json` | **pinned**: python 3.12.14 / numpy 2.4.4 / scipy 1.17.1 (4 Sept 2026) | 0 (it is that run's output) |
| `res3_comparator.json` | **pinned**: python 3.12.14 / numpy 2.4.4 / scipy 1.17.1 (4 Sept 2026) | 0 (it is that run's output) |
| `res5_calibration.json` | **pinned**: python 3.12.14 / numpy 2.4.4 / scipy 1.17.1 (4 Sept 2026) | 0 (it is that run's output) |
| `res6_policies.json` | pre-import; provenance of two calibration rows lost (C17, C18) | five of seven cal rows and eleven of fifteen delay rows bitwise; the rest are the withdrawn entries |
| `res7A_identifiability.json` | python 3.11.11 / numpy 2.2.4 / scipy 1.15.2 | 6.0e-8, tolerance 1e-6 |
| `res7B_servo.json` | python 3.11.11 / numpy 2.2.4 / scipy 1.15.2 | 1.4e-16 |
| `res8_switch.json` | pre-import | compared by its producer |

The pinned stack is python 3.12.14, numpy 2.4.4, scipy 1.17.1, matplotlib 3.10.8, BLAS 3.9.0,
on macOS x86_64 **under Rosetta 2** on an Apple M1 Pro host. Native arm64 is untested.

## Files
- `res1_core.json` — dict with keys A (list of [C, s, I_exact, I_lo, ratio, validity_param]), A2 (list of [C, err_at_q0.06, err_at_q0.17, q_for_6pc, q_for_20pc, k]; see notes/2026-09-03-note-01a-errata.md and claim C21), B (list of [C, s, tcc, S2, I_mid_strict, I_halfsum_exact_rk, I_hmm, pert_param, I_ext]), C (dict "C,s,tcc" -> [thetas_rad, exact, lo_strict]), D (list of [tau, tc, c, s2_closed, s2_num, a1_closed, a1_num]), E (regime-map grids; see below), F (list of [C, s, tcc, I_ext, I_mid, delay_ext_mean, delay_ext_se, h_over_I_ext, delay_mid_mean, delay_mid_se, h_over_I_mid]; units shots). In F, `delay_mid_mean` and `delay_mid_se` are `null` where no mid-fringe run reached the threshold within the cap, so the delay is undefined — this is the case at tau_c/c = 20 and 1. See seeds.md.
- `res1_core.json` key **E** — the grids behind `figures/sid_regime_map.png`, so its curves can be
  checked without rerunning section E. Keys: `s_ref` (the reference phase spread, 0.5);
  `C_grid`, `tcc_grid` (the plotted axes, 400 points each); `crossover_tcc` (the leading-order
  crossover, one value per contrast); `delta0_level` (0.3, the card v1.1 mid-fringe validity
  level); `delta0_boundary` (list of [C, tau_c/c] where delta(0) reaches that level — stored only
  for contrasts whose boundary falls inside `tcc_grid`); `delta0_boundary_omitted` (count of
  contrasts with no boundary in range, so the truncation is explicit); `ext_rel_error` (the exact
  extremum leading-order relative error I_LO/I_exact − 1 at `s_ref`, one value per contrast);
  `ext_error_crossings` (contrast at which that error reaches each declared level; `null` if the
  level is not attained on the axis); `ext_error_min` (the floor over the axis). See
  notes/2026-09-04-note-06-regime-map-overlays.md.
- `res2_partial.json` — written by `sid_run2.py`. Four keys:
  - `B2` — 7 rows of [C, s, tau_c/c, I_mid_strict, half_sum_rk2, I_gp, I_hmm, delta0, frozen_limit, I_ext_exact]; nats per shot.
  - `crossover` — {"C,s": [tau_c/c grid, I_hmm at each, I_ext_exact, crossover tau_c/c]} from the HMM grid. This is `sid_run2.py`'s own crossover estimate and is NOT the comparator crossover of claim C05, which comes from `sid_run3.py` and is stored in `res3_comparator.json`. The two estimators agree; see notes/2026-09-04-note-08-comparator-vs-hmm-crossover.md.
  - `C2` — [thetas_rad, exact_rate, standard_error] over 7 Ramsey phases; the endpoint profile behind note 01 section 4.
  - `extremum_bonus` — 3 rows of [C, s, tau_c/c, exact_rate_mean, exact_rate_se,
    marginal_D_Bern, excess_percent, excess_se_percent] at theta = pi with seeds 0-63, plus
    `extremum_bonus_fields` and `extremum_bonus_design`. An INDEPENDENT CHECK of note 03
    section 1, not a reproduction of it: no script in this repository produced that table and
    its seeds were never recorded. See claim C24 and
    notes/2026-09-04-note-09-extremum-bonus-provenance.md.
  - `F2` — 3 rows of [C, s, tau_c/c, I_ext, I_mid, delay_ext_mean, delay_ext_se, h/I_ext, delay_mid_mean, delay_mid_se, h/I_mid, runs_detected]; shots, at gamma = 1e3, h = ln(1e3). Claim C25.

  *Provenance, 4 Sept 2026.* Earlier copies of this file held only `B2`, with 7 fields per row and
  columns 3-5 null, because they were reconstructed by hand from stdout: `sid_run2.py` used a
  `\tfrac` mathtext macro that no matplotlib version defines, and its `json.dump` sat after that
  figure, so the script always died before writing. With the macro corrected and the dump moved
  ahead of all plotting, this file is now the direct output of a run in the pinned environment
  (python 3.12.14, numpy 2.4.4, scipy 1.17.1, matplotlib 3.10.8; macOS x86_64 under Rosetta 2 on
  an Apple M1 Pro; BLAS 3.9.0). The legacy 7 fields map index-for-index onto the first 7 of the
  new 10; every overlapping value equals the reproduced value rounded to the 4 significant figures
  it was stored at. Columns 3-5, columns 7-9 and the keys `crossover`, `C2` and `F2` are newly
  archived — they were never previously stored and are not reproductions of archived values.
  See notes/2026-09-04-note-07-pinned-certification.md.
- `res3_comparator.json` — written by `sid_run3.py`; the comparator results that were printed
  only until 4 Sept 2026. Keys:
  - `comparator_crossover` — 20 rows of [C, s, crossover_leading_order,
    crossover_comparator_as_published, crossover_comparator_log_interpolated, I_ext_exact].
    Claim C05. `as_published` is the first grid point above I_ext, the estimator the note used;
    it is biased high by up to one log-grid step (factor in `grid.step_factor`, 2.04 %), and the
    log-interpolated value is stored beside it rather than replacing it. Both are `null` at
    C = 0.99, s >= 0.5, where no crossover exists — the claim states exactly that, so the null
    means "does not exist", not "not measured". This is the COMPARATOR crossover; the HMM-grid
    crossover under key `crossover` of `res2_partial.json` is a different estimator, and
    notes/2026-09-04-note-08-comparator-vs-hmm-crossover.md shows the two agree.
  - `rate_check` — the curves behind `figures/sid_midfringe_rate_check.png` (leading order,
    half-sum of r_k^2, GP closed form, HMM), with the HMM seed and N.
  - `tau_optimised_threshold` — [C0, minimum tau_c/t_dead at which mid-fringe wins]; `null`
    would mean never. Claim C08. With `tau_optimised_grid` and `tau_optimised_win_fraction`.
- `res5_calibration.json` — written by `sid_run5.py`; claim C10, printed only until 4 Sept 2026.
  `calibration`: 4 rows of [policy, tau_c/c (`null` for the extremum, which has no correlation
  time), h_star, ARL_mean, ARL_se, exp_h_star, slack_ARL_over_exp_h] — the martingale bound
  e^h against the measured ARL, whose ratio is the claim's looseness. `delays`: 3 rows of
  [tau_c/c, delay_ext_mean, delay_ext_se, h_star/I_ext, delay_mid_mean, delay_mid_se,
  h_star/I_series, delay_ratio, rate_ratio]. `seeds` records the bisection, confirmation and
  delay seeds. The calibration block is written before the delay measurements, so a failure
  there cannot destroy it.
- `res6_policies.json` — {"cal": {policy: [h_star, ARL, ARL_se, capped_runs]}, "delays": {tau_c: {policy: [mean, se, capped]}}}. Units: shots.
- `res8_switch.json` — {B: [h_star, ARL, {tau_c: [mean, se]}]}.
- `res7A_identifiability.json` — rows [C0, eta0, tau_c/t_dead, I_known_baseline, I_classA, I_classB, I_best_single_tau, DeltaGamma/(2 eta0 Gamma)]; nats per shot; T2=10, t_dead=1, g sigma_x T2=0.5.
- `res7B_servo.json` — rows [kappa, Ceff_slope_parity, Ceff_slope_full, Ceff_var_parity, Ceff_var_full]; C1=C2=0.9; variance channel at s=0.3. `kappa = "positive-infinity"` is the perfect-oscillator limit, the last row: a known limiting case the calculation deliberately visits, carried as the declared sentinel string rather than as null (which would claim the value is absent) or as the JSON-invalid token Infinity. `sid_run7.py` draws it at 100 on the symlog axis.
Missing as files (printed only): crossover table (C05), calibration slack table (C10), bonus table (C15) — flagged [unreproduced-from-file] in the ledger; step 2 of the work plan stores them.

- `res9_identifiability_T2.json` — **roadmap E**, first published 7 Sept 2026. Object with keys
  `schema`, `units`, `regimes`, `determinism`, `supersedes`, `regression_vs_res7A`, `run`, `rows`.
  36 rows over C_0 ∈ {0.4, 0.5, 0.9} × η₀ ∈ {0.02, 0.05, 0.10} × τ_c/T₂ ∈ {0.05, 0.2, 1.0, 5.0},
  each an object carrying `C_0`, `regime` (`principal` for 0.4 and 0.5, `servo-context` for 0.9),
  `eta_0`, `tau_c_over_T2`, `I_unc`, `I_A`, `I_B`, `I_ref`, `DeltaGamma_over_Gamma_hat`,
  `DeltaGamma_over_2eta0_Gamma_hat`, `class_A_points_passing`/`_total`, and an `optimizer` block.
  That block holds **five candidates**, each with `kind`, `x0`, solution `x`, objective `fun`,
  `success`, `status`, `nit` and `message`: three `named` L-BFGS-B starts, one `grid-polish` seeded
  from the deterministic 121×121 scan's argmin, and the raw `grid-raw` scan minimum itself. It also
  holds `selected_index` and `selected_fun` (the reported `I_B`), `grid_n`, the tolerance `options`,
  and **two spread measures over the named starts only**: `named_spread_abs` and
  `named_spread_rel`. Both are needed — `I_B` spans four orders of magnitude across the grid, so an
  absolute spread of 2.4e-9 is 12 % where `I_B` ~ 1e-9 and negligible where `I_B` ~ 1e-4.
  `grid_beat_named` records how far the grid route fell below the best named start; it is positive
  on 5 of 36 rows, by up to 9.7 %, and on those rows the named starts agreed to between 0.003 % and
  0.115 % — so low named spread does not certify a minimum. The top-level `grid_refinement_check`
  records that going to 241×241 moves the reported value by at most 1.28e-11 relatively.
  `I_B` is a **best-of-candidates estimate, not a certified global infimum**.
  **Every quantity is dimensionless in T₂ and information is per shot; this run prices no dead time
  and contains no cycle time.** It supersedes section A of `sid_run7.py` for the v2.0 record;
  `res7A_identifiability.json` is unchanged. The `servo-context` rows exceed the parity ceiling and
  may not support the parity-regime headline.

*Column relabelling, 7 Sept 2026.* The columns formerly named `I_lo`, `lo` and `I_mid_lo` are
renamed `I_mid_strict` and `lo_strict`. **No stored value changed.** They always held the strict
O(s^4) asymptote 1/2 Cbar^4 s^4 Sum a_k^2, while the name `lo` and one figure label attributed them
to the card's leading-order rate, which retains the slope-loss resummation e^{-2s^2}
(cards/v1.1-frozen.md:235, :292). The two agree through strict O(s^4) and differ by 19.7 % at
s = 0.3 and 64.9 % at s = 0.5. The helpers are now separately named `I_mid_strict`/`I_mid_slope` and
`I_lo_theta_strict`/`I_lo_theta_slope`. Only labels promising the card formula were changed: the
false attribution in analysis/runs/sid_run3.py's figure legend, and claim C25's quoted comparison
(910 -> 1496). See notes/2026-09-07-note-14-helper-split-and-BE-decisions.md.
