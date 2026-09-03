# Current status

Generated 2026-09-03T10:22:22+00:00 from ledgers/status.yaml. Do not edit.

| id | status | statement | note |
|---|---|---|---|
| C01 | result | Extremum-channel exact Bernoulli divergence and its small-s expansion; expansion within 6 % for s^2 C/(1-C^2) <= 0.06 | notes/2026-09-02-note-01.md#1 |
| C02 | result | Exact mid-fringe lag correlation r_k = C^2 e^{-s^2} sinh(s^2 a_k); leading-order rate carries factor e^{-2 s^2} | notes/2026-09-02-note-01.md#2a |
| C03 | result | Mid-fringe leading-order expansion valid only when the spectral perturbation delta(0)=2 sum r_k << 1; v1.0 box C^4 s^4 sum a_k^2 << 1 withdrawn | notes/2026-09-02-note-01.md#2b |
| C04 | result | Gaussian spectral comparator with exact r_k reproduces the grid-converged latent-AR(1) binary rate within Monte-Carlo error (SE ~7 % at 1e5 shots) in all tested cases | notes/2026-09-02-note-02.md (checks 2, 3a) |
| C05 | result | Crossover in tau_c/c is amplitude-dependent beyond leading order (C=0.4: 4.65 at s->0, 5.46 at s=0.3, 7.24 at s=0.5); absent at C=0.99 for s>=0.5 | notes/2026-09-02-note-01.md#3 |
| C06 | result | Endpoint lemma — interior critical point is a minimum; reference-detector profiles consistent with flatness within ~5 % over theta in [60,90] deg near the crossover | notes/2026-09-02-note-01.md#4; note-02 check 3a |
| C07 | result | Filtered-OU closed forms for s_tau^2 and a_k match numerical integration | notes/2026-09-02-note-01.md#5 |
| C08 | result | tau-optimised physical map (T2=10 t_dead, g sigma_x T2 = 0.5 rad): mid-fringe wins only for tau_c/t_dead >~ 210 (C0=0.4), 140 (0.5), 75 (0.7), 45 (0.9) | notes/2026-09-02-note-01.md#6 |
| C09 | pilot | Delay crossover at matched measured E0[T]~3e4 lies between tau_c/c=5 and 20, consistent with the comparator crossover 7.2; delay advantage compressed 1.5-3x relative to rate ratio | notes/2026-09-02-note-02.md (check 3b); note-03 §2 |
| C10 | result | Martingale bound E0[T] >= e^h holds for the restarted-SPRT variant under the action-conditional null but is loose by 1e2-1e4; calibration is by simulation | notes/2026-09-02-note-02.md; cards/v1.1-frozen.md (false-alarm control) |
| C11 | pilot | At the pilot operating point (C=0.4, s=0.5, E0T~3e4, tau_c/c in {1,5,20}) no tested hedge shows a worst-case delay-ratio advantage over fixed-extremum operation (1.56 vs 1.64-1.67); ARL precision +-30 % does not order them | notes/2026-09-02-note-03.md#3; notes/2026-09-03-note-03a-errata.md E1-E3 |
| C12 | pilot | Composite-model (bank) detection at mid-fringe shows no resolved penalty relative to the known-tau_c fixed endpoint (0.98x) | notes/2026-09-03-note-03a-errata.md E2 |
| C13 | result | tau-scan identifiability — pointwise band gives zero retained information at tau_c <~ T2/5; Markov-parametric class retains 2e-3 to 2e-2 there and 20-50 % (eta0=2 %) for tau_c >~ T2; general fast-noise criterion Delta Gamma_phi > 2 eta0 Gamma_hat | notes/2026-09-02-note-03.md#4; note-03a E4 |
| C14 | pilot | In the tested independent-phase, small-modulation servo model both channels reduce to the binary-link form with matching effective contrast within 2 %; C_eff>0.8 needs kappa >~ 5 at C1=C2=0.9 | notes/2026-09-02-note-03.md#5; note-03a E5 |
| C15 | withdrawn | Extremum-stream correlation bonus at most 6 % across tested points; the earlier 10 % figure was Monte-Carlo noise | notes/2026-09-02-note-03.md#1; note-03a E6 |
| C16 | withdrawn | Learn-then-lock-in O(A^2) vs O(A^4) scaling argument (draft 03) | cards/history/scope-path.md |
