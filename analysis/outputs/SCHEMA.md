# Output schemas

## Representation (all files)

Every stored output is **strict JSON**: no `NaN`, `Infinity` or `-Infinity` tokens, which
RFC 8259 does not permit and conforming parsers reject. `null` means *undefined or not
applicable* and nothing else — a quantity that was not measured, or a limit at which the
column's unit does not apply. Any other non-finite result is a calculation error and stops
the producing run rather than being written (`allow_nan=False` on every writer).
`tests/test_output_schema.py` enforces this on every `analysis/outputs/*.json`.

*Representation migration, 4 Sept 2026.* `res1_core.json` previously stored four `NaN`
tokens and `res7B_servo.json` one `Infinity`; both files were therefore invalid JSON. They
now carry `null` in those positions, written by the producers rather than by editing the
archive. No finite value changed meaning; the former artifacts remain in git history.
Recorded in `notes/2026-09-04-note-05-representation-migration.md`.

## Files
- `res1_core.json` — dict with keys A (list of [C, s, I_exact, I_lo, ratio, validity_param]), A2 (list of [C, err_at_q0.06, err_at_q0.17, q_for_6pc, q_for_20pc, k]; see notes/2026-09-03-note-01a-errata.md and claim C21), B (list of [C, s, tcc, S2, I_lo, I_halfsum_exact_rk, I_hmm, pert_param, I_ext]), C (dict "C,s,tcc" -> [thetas_rad, exact, lo]), D (list of [tau, tc, c, s2_closed, s2_num, a1_closed, a1_num]), E (regime-map grids; see below), F (list of [C, s, tcc, I_ext, I_mid, delay_ext_mean, delay_ext_se, h_over_I_ext, delay_mid_mean, delay_mid_se, h_over_I_mid]; units shots). In F, `delay_mid_mean` and `delay_mid_se` are `null` where no mid-fringe run reached the threshold within the cap, so the delay is undefined — this is the case at tau_c/c = 20 and 1. See seeds.md.
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
- `res2_partial.json` — dict B2: list of [C, s, tcc, null, null, null, I_hmm]; reconstructed from run2 stdout after a figure crash; the other fields are in the note.
- `res6_policies.json` — {"cal": {policy: [h_star, ARL, ARL_se, capped_runs]}, "delays": {tau_c: {policy: [mean, se, capped]}}}. Units: shots.
- `res8_switch.json` — {B: [h_star, ARL, {tau_c: [mean, se]}]}.
- `res7A_identifiability.json` — rows [C0, eta0, tau_c/t_dead, I_known_baseline, I_classA, I_classB, I_best_single_tau, DeltaGamma/(2 eta0 Gamma)]; nats per shot; T2=10, t_dead=1, g sigma_x T2=0.5.
- `res7B_servo.json` — rows [kappa, Ceff_slope_parity, Ceff_slope_full, Ceff_var_parity, Ceff_var_full]; C1=C2=0.9; variance channel at s=0.3. `kappa = null` is the perfect-oscillator limit (kappa -> infinity), where no finite coherence applies; it is the last row, and `sid_run7.py` draws it at 100 on the symlog axis.
Missing as files (printed only): crossover table (C05), calibration slack table (C10), bonus table (C15) — flagged [unreproduced-from-file] in the ledger; step 2 of the work plan stores them.
