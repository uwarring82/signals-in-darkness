# 2026-09-02/03 — Pass 2: identification, servo regime, and whether hedging helps

**Question:** Can a τ-scan tell stochastic frequency noise from a change in T₂; does the theorem survive a partially coherent oscillator; and does any hedge beat a fixed operating point when the correlation time is unknown?
**Finding:** A τ-scan identifies the signal only because the admissible dephasing class has shape — a pointwise uncertainty band gives nothing at short correlation time; the general fast-noise criterion is ΔΓ_φ > 2η₀Γ̂. In an independent-phase oscillator model both channels reduce to the binary-link form with matching effective contrast within 2 %. At the pilot operating point no tested hedge shows a worst-case advantage over fixed-extremum operation, and ARL precision does not order the fixed extremum (1.56) against the best hedges (1.64–1.67). The earlier 10 % extremum bonus was noise; at most 6 % in one corner.
**Why it matters:** Reweighted the paper: crossover and identifiability lead; the servo reduction is supported, not proved; the policy study is a pilot, not an adaptive or minimax result (see note 03a).
**Status:** result (identifiability, at tested parameters); pilot (servo, policies); withdrawn (10 % bonus).
**Next test:** posterior-driven action selection against a true oracle over the same action set; second operating point; correlated oscillator residual.

Technical record: notes/2026-09-02-note-03.md and notes/2026-09-03-note-03a-errata.md; sid_run6s.py, sid_run7.py, sid_run8.py; outputs res6_policies.json, res8_switch.json, res7A_identifiability.json, res7B_servo.json; figures sid_policy_delays.png, sid_servo_effective_contrast.png.
