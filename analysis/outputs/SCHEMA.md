# Output schemas
- `res1_core.json` — dict with keys A (list of [C, s, I_exact, I_lo, ratio, validity_param]), B (list of [C, s, tcc, S2, I_lo, I_halfsum_exact_rk, I_hmm, pert_param, I_ext]), C (dict "C,s,tcc" -> [thetas_rad, exact, lo]), D (list of [tau, tc, c, s2_closed, s2_num, a1_closed, a1_num]), F (invalid mid-fringe entries; see seeds.md).
- `res2_partial.json` — dict B2: list of [C, s, tcc, null, null, null, I_hmm]; reconstructed from run2 stdout after a figure crash; the other fields are in the note.
- `res6_policies.json` — {"cal": {policy: [h_star, ARL, ARL_se, capped_runs]}, "delays": {tau_c: {policy: [mean, se, capped]}}}. Units: shots.
- `res8_switch.json` — {B: [h_star, ARL, {tau_c: [mean, se]}]}.
- `res7A_identifiability.json` — rows [C0, eta0, tau_c/t_dead, I_known_baseline, I_classA, I_classB, I_best_single_tau, DeltaGamma/(2 eta0 Gamma)]; nats per shot; T2=10, t_dead=1, g sigma_x T2=0.5.
- `res7B_servo.json` — rows [kappa, Ceff_slope_parity, Ceff_slope_full, Ceff_var_parity, Ceff_var_full]; C1=C2=0.9; variance channel at s=0.3.
Missing as files (printed only): crossover table (C05), calibration slack table (C10), bonus table (C15) — flagged [unreproduced-from-file] in the ledger; step 2 of the work plan stores them.
