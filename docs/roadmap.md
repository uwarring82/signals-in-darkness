# Roadmap

Generated 2026-09-07T05:43:41+00:00 from ledgers/roadmap.yaml. Do not edit.

| id | title | state | gates_freeze |
|---|---|---|---|
| A1 | Operating-point and sequential-detection prior-art audit — C05 mechanism re-scoped; quantitative detection-theoretic boundary not found by targeted search | complete | true |
| A2 | C23 noise-physics provenance — closed as a bounded audit. The Ginzburg-style self-consistency move is prior art (Hohenberg & Krekhov, Phys. Rep. 572, Sec. V.B); the sensing-specific instantiation was not found. C02's correlator conceded to Wudarski et al. Eq. 29. No status changed. | complete | true |
| B | Second operating point C_eff=0.5, s=0.3 at the parity ceiling, labelled an upper-bound stress test (D2, 7 Sept 2026; replaces C=0.8, which would have made this gate depend on D) — benchmark, hedges, tau_c in {1,5,20}, tightened ARL. Blocked by G. Exact comparator for interpretation at tau_c/c = 5 and 20. | open | true |
| C | Posterior-driven action selection vs true oracle over the same action set | open | false |
| D | Correlated oscillator residual (AR(1) phase) in the four-outcome likelihood — size effect on C_eff | open | false |
| E | Identifiability in dimensionless form with C_0=0.5 added as the second principal-regime slice and ALL THREE calibration uncertainties eta_0 in {0.02,0.05,0.10} (D3). Per-shot over tau_c/T2; prices no dead time. C_0=0.9 rows kept as servo context only. | open | true |
| F | Model-consistency — validate the binary comparator against an exact ARMA(1,1) latent likelihood at a few finite-window points. The committed HMM is AR(1) in the phase, exact only for point sampling; the finite-window integrated phase is ARMA(1,1). Not a prior-art gate; resolve before the v2.0 manuscript freezes. | open | false |
| G | Operating-point provenance repair — replace the mutable sid_policies C,s globals with an immutable configuration passed into Bank and every simulator; carry it in checkpoint identity and output metadata; prove the refactor preserves all five reproducible pilot calibration rows. Gates B, not the freeze. | open | false |
