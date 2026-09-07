# Signals in Darkness — execution note 13 (7 Sept 2026): the shared B/E parameter manifest, and what locking it exposed

Step 1 of the agreed order was to lock one parameter manifest for roadmap items B and E. The
manifest is `analysis/manifest_BE.json`, made executable by `tests/test_manifest_BE.py`: every value
it declares `source: code` is asserted against the committed source, and every hazard it names is
asserted to still be real.

Locking it was supposed to be bookkeeping. It was not. Three defects and three decisions came out of
it, and two of the defects touch published claims.

## 1. There are three time conventions, not two

The repository runs three disjoint stacks, and the manifest's first job is to keep them apart.

| stack | units | dead time | used by |
|---|---|---|---|
| shot | dimensionless τ_c/c, no absolute c | not modelled | B (policies, delays) |
| physical | c = τ + t_dead, t_dead = 1 | yes | C08's τ-optimised map |
| identifiability | τ_c/T₂, T₂ = 10 | **none** | E |

The third was not previously distinguished. `sid_run7.py:20` assigns `td = 1.0` and never uses it in
any equation; no cycle time is formed, and `SCHEMA.md:111` records `res7A` as *nats per shot*. Item E
prices no dead time at all, and its real axis is τ_c/T₂ ∈ {0.05, 0.2, 1, 5}. Any attempt to state E's
criterion "in dimensionless form" while importing the shot stack's τ_c/c would be a category error.

**`u = τ/τ_c`, not `c/τ_c`** — `sid_run3.py:129`, `sid_run4.py:59`, `sid_core.py:207`. This matters
for note 12: since ρ₁ = F(u)·e^{−c/τ_c}, the AR(1) reduction is exact as **τ/τ_c → 0** — a short
interrogation window relative to the correlation time — and *not* as c/τ_c → 0. Note 12 §4 and
labbook pass 6 wrote `F(u)` without defining u, which is incomplete rather than wrong, but the
ambiguity is demonstrably live: the audit brief that produced this manifest assumed `u = c/τ_c` and
had to be corrected. Erratum recorded here; the numbers in note 12 are unaffected, because they were
computed as a function of u itself.

## 2. `I_mid_lo` omits a factor that C02 says the rate carries

`cards/v1.1-frozen.md:235` gives the leading-order mid-fringe rate as
½C̄⁴s⁴**e^{−2s²}**Σa_k², and C02's own ledger statement says "leading-order rate carries factor
e^{-2 s^2}". The committed helper omits it, in both copies:

    analysis/lib/sid_lib.py:42    def I_mid_lo(C, s, S2): return 0.5*C**4*s**4*S2
    analysis/runs/sid_core.py:70  (identical)

The omitted factor is not small at the operating point: e^{−2s²} = 0.6065 at s = 0.5, so the helper
is **65 % high**. It is 19.7 % high at s = 0.3, the proposed second amplitude.

This is not merely internal. **C12's parenthetical is mislabelled.** C12 states that at τ_c/c = 20,
C̄ = 0.4, s = 0.5, γ = 1e3, h = 6.9, "the card leading order would give 910". Recomputing:
h/I with the *code* helper gives **907.1** — the published number — while the card's own formula
gives **1495.6**. The number attributed to the card came from the helper that drops the card's
factor.

C12's conclusion survives: measured mid-fringe delay is 2010 ± 170 and the exact rate predicts 2240,
so the leading-order rate is not a usable predictor either way. But the size of its failure is
misstated — 26 % low, not 55 % low — and the attribution is wrong.

**Why it survived.** `I_mid_lo` is imported into `tests/test_analytic.py:4` and never called. No test
constrains it. The value propagates into `res1_core.json["B"]` and `res2_partial.json["B2"]` as a
stored column.

Nothing is changed in the code by this note. Correcting `I_mid_lo` changes archived columns and is a
regeneration event with its own errata, to be done deliberately rather than folded into a manifest
commit. `tests/test_manifest_BE.py::test_hazard_I_mid_lo_still_omits_the_exp_factor` pins the present
state so the defect cannot be fixed silently.

## 3. Hazards the manifest carries forward

- **The operating point is a mutable module global.** `analysis/lib/sid_policies.py:23` holds
  `C, s = 0.4, 0.5` with three inconsistent readers. Every `Bank` depends on it — the grid, the prior
  and the per-shot likelihood all derive from `s`, and `e1` from both. Introducing a second operating
  point by reassigning the global will silently mis-build any bank constructed before the
  reassignment. This is the highest-risk item for B, and it is a code-structure problem, not a
  parameter one.
- **δ(0) at the proposed second point.** Computed from the committed `delta0()` at (C̄ = 0.8,
  s = 0.3): **0.0613, 0.4757, 2.0544** at τ_c/c = 1, 5, 20, against C23's declared validity level 0.3.
  Two of the three proposed grid points lie outside leading-order mid-fringe validity. The exact
  comparator that carries C08 is unaffected; only leading-order statements are.
- **C17/C18 poison every τ_c/c = 20 baseline** in `res6_policies.json`, including
  bench(20) = 1332.19 ± 114.43. B must recalibrate at τ_c/c = 20 from scratch and may not compare
  against the archived row.
- **"Three hedges" is four in the code**: interleave B=1, interleave B=10, switch@300, switch@1000.
  Note 03a's "three schedule families" reconciles the count only if the two switch policies are one
  family. The card should say which.

## 4. Three decisions the manifest cannot make for itself

**D1 — is C̄ = 0.8 the effective contrast or the zero-τ contrast?** The shot stack uses C̄(τ); the
physical maps use C̄₀ and apply `Ct = C0*exp(-taus/T2)` themselves. The two differ by e^{−τ/T₂}.
Nothing in the card or the code says which is meant. Blocks both B and E.

**D2 — C̄ = 0.8 leaves the parity regime.** `cards/v1.1-frozen.md:117` caps the parity contrast at
C̄_par = ½C̄₁C̄₂ ≤ ½; `:132` states that effective contrasts above ½ "require the full four-outcome
likelihood with residual oscillator noise"; `:134` makes C̄ ≤ ½ versus C̄ > ½ the principal figure's
distinction. `cards/v2.0-seed.md:11` then decided that the paper's principal claims live in the
oscillator-cancelled parity regime C̄ ≤ ½, with C_eff(κ) an appendix. As specified, B therefore places
a **freeze-gating** run in the regime the card relegated to an appendix, and makes it depend on
roadmap D — the four-outcome likelihood — which is currently non-gating and scheduled after the
freeze. Blocks B.

Related: **C̄ = 0.8 is not a computed value.** It is a rounded reading of note 03 §5's "C_eff > 0.8
requires κ ≳ 5". The nearest actually-computed entries in `res7B_servo.json` are 0.8126 (slope) and
0.8073 (variance) at κ = 5, C̄₁ = C̄₂ = 0.9 — and that claim, C14, is status `pilot`, not `result`.
An exhaustive search of every script under `analysis/` and every `outputs/*.json` finds 0.8 as a
contrast nowhere.

**D3 — η₀ is already three values, not two.** Item E asks for "two calibration uncertainties";
`res7A` already carries η₀ ∈ {0.02, 0.05, 0.10}. E's wording is behind the archive, not ahead of it.
Affects the card's wording, not the run.

## 5. Consequence for the run order

The agreed order stands, and E's position at the front is vindicated for a reason beyond cost: E is
the item whose conventions the manifest found to be *cleanest* — every dimensionless ratio item E
asks for (ΔΓ_φ/Γ̂ = 0.25·τ_c/T₂, and ΔΓ_φ/(2η₀Γ̂), already stored as `res7A` column 8) is computable
from committed code with no new machinery. E needs only D1, and only if the second point enters it.

B is the item that is not ready. It needs D1 and D2 answered, the mutable-global hazard resolved
before a second operating point is introduced, and a fresh calibration at τ_c/c = 20 that does not
touch the withdrawn rows.

One qualification on "E is deterministic": class B is a numerical L-BFGS-B infimum over three starts.
It is seed-free but optimiser-dependent — a third stack reproduced it to 6.0e-8 against the tolerance
`SCHEMA.md:43` states. E is reproducible, not bitwise-deterministic across stacks.
