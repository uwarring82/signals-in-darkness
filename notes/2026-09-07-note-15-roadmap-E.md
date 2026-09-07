# Signals in Darkness — execution note 15 (7 Sept 2026): roadmap E, and what the regression gate caught

E is complete. `analysis/runs/sid_run9.py` writes `analysis/outputs/res9_identifiability_T2.json`,
36 rows, dimensionless throughout. `res7A_identifiability.json` is unchanged, and section A of
`sid_run7.py` is superseded rather than edited.

The six conditions are all met, and each is asserted by `tests/test_roadmap_E.py` rather than
claimed here. What follows is what the sixth condition — the regression against `res7A` — turned up,
because it is the substantive result of this run.

## 1. The regression gate caught a defect in my own implementation first

E's physics is unchanged. With u = τ/T₂, v = τ_c/T₂ and G = gσ_xT₂,

    s²(u,v) = G²·2·(vu − v²(1 − e^{−u/v}))

is algebraically identical to `sid_run7`'s form, and χ̂ = Γ̂τ = u. So the 24 shared rows should have
reproduced to machine precision. They did not: the first run came out **6.15 × 10⁻⁷ above `res7A`**
at one row, with the three optimiser starts landing on three different points spread over 1.1 %.

The cause was the reparameterisation itself. The class-B infimum is over Γ, and expressing it as
Γ/Γ̂ rescales the variable by T₂ = 10 — which changes how L-BFGS-B's default stopping tests bite.
Its `ftol` test divides by max(|f|, 1), so with an objective of order 10⁻⁶ it stops on an *absolute*
change of ~2 × 10⁻⁹, a relative change of ~3 × 10⁻⁴. Both parameterisations were under-converged; the
original merely happened to stop lower.

**`res7A` is vindicated.** With tolerances tightened, all three starts converge to
6.002659924203 × 10⁻⁶ at the boundary solution (1.0092, 1.1), and `res7A`'s stored value sits
**3.8 × 10⁻¹⁶ above it**. A 401 × 401 brute-force grid confirms the same minimum. The archive was
right; the new run was wrong, and the gate said so.

## 2. Tolerances are tightened to the numerical floor and no further

The first fix over-corrected. At `ftol = 1e-18, gtol = 1e-14`, **46 of 108 starts returned
`ABNORMAL_TERMINATION_IN_LNSRCH`** while still reporting the right minimum: scipy differentiates this
objective by finite differences, so its gradient carries ~10⁻¹⁴ of absolute noise and a `gtol` below
that asks the line search for progress it cannot measure. Recording a convergence status that is
"failed" 43 % of the time would have made condition 5 worthless.

`ftol = 1e-14, gtol = 1e-9` is the setting shipped: **all 108 starts converge**, the across-start
spread is at most 2.4 × 10⁻⁹ — twenty-five times inside the 6 × 10⁻⁸ regression tolerance — and the
infimum is unchanged to twelve digits.

**This revises the determinism wording.** The 6 × 10⁻⁸ recorded at `SCHEMA.md:43` is not an intrinsic
property of the infimum; it is default-tolerance under-convergence. E is seed-free, and with explicit
tolerances it is start-independent to ~10⁻¹⁷. Every start is stored with its solution, status,
objective and iteration count so this is auditable rather than asserted.

## 3. Two rows where `res7A` is under-converged

With the tolerances fixed, **0 breaches remain** — E is nowhere worse than `res7A` — and two rows
where E reaches a **strictly lower** infimum from all three starts:

| C₀ | η₀ | τ_c/T₂ | `res7A` I_B | E's I_B | start spread |
|---|---|---|---|---|---|
| 0.9 | 0.05 | 0.2 | 2.064347e-06 | **1.970344e-06** | 8.6e-18 |
| 0.9 | 0.10 | 0.2 | 2.035399e-06 | **1.817114e-06** | 8.5e-17 |

`res7A` overstates I_B at those two rows. The regression records "this run is worse" and "the
reference was under-converged" as **separate categories**, because a favourable sign is not a reason
to let a real regression hide. Both are C₀ = 0.9 — servo-context rows, which under D2 may not support
the parity-regime headline — and a test asserts that if under-convergence ever reaches a principal
row, C13's principal numbers must be rechecked before the assertion is relaxed.

## 4. C13, restated dimensionlessly, with three corrections

Item E asked for the criterion in dimensionless form rather than as a T₂ threshold. That is C13's
statement, so C13 is restated rather than duplicated:

    ΔΓ_φ/Γ̂ > 2η₀,   with   ΔΓ_φ/Γ̂ = (gσ_xT₂)²·(τ_c/T₂) = 0.25·τ_c/T₂

Three quantitative clauses were wrong, and all three are pre-existing — they are visible in `res7A`
and are not artefacts of this run.

- **"Zero retained information at τ_c ≲ T₂/5" is false at the boundary.** At τ_c/T₂ = 0.2 with
  η₀ = 0.02, the pointwise band retains **3.6 × 10⁻³** of the unconstrained rate, with **21 of 40**
  τ points passing the separation guard, at every contrast. It *is* zero at τ_c/T₂ = 0.05 for all η₀,
  and at 0.2 for η₀ ≥ 0.05. The unqualified "zero" was the error.
- **"2e-3 to 2e-2" understates the range.** The Markov class retains **2.1e-3 to 3.1e-2** at
  τ_c/T₂ ≤ 0.2, or 2.1e-3 to 2.3e-2 over the principal contrasts alone.
- **"20–50 % (η₀ = 2 %) for τ_c ≳ T₂" is 38–53 %.**

C13 keeps status `result`: the qualitative structure it asserts — identifiability collapsing at short
correlation time and surviving at long — is unchanged, and the criterion is now stated in the form
item E required. **The first correction is qualitative rather than a tightening, so it is flagged
explicitly here rather than folded into a range.**

## 5. Housekeeping done under this item

`sid_run7.py`'s unused `td = 1.0` is **removed**, not documented, along with the `tc/td` print label
that implied a dead-time axis. `res7A` and `res7B` were regenerated afterwards and compare at
6.005e-08 and exactly 0.0 respectively, so the removal changed nothing — as an unused assignment
could not.

## 6. Order

E is done and did not touch `sid_policies`, so **G is unblocked and unaffected**. Next is G's
immutable operating-point configuration, with the five reproducible pilot calibrations preserved,
and only then B.
