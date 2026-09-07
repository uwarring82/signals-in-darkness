# Signals in Darkness — execution note 16 (7 Sept 2026): correcting note 15, and closing E

Note 15 got E's physics right and two things around it wrong. This note corrects both, records the
C13/C26 supersession, and closes the item.

## 1. Erratum to note 15 §2 — "start-independent to ~10⁻¹⁷" was false

Note 15 claimed that with explicit tolerances every start converges to the same solution, on the
strength of a recorded `start_spread`. That figure was an **absolute** objective difference, and
I_B ranges over four orders of magnitude across the grid. Where I_B is of order 10⁻⁹ — every row at
τ_c/T₂ = 0.05 — an absolute spread of 2.4 × 10⁻⁹ is a **12 % disagreement**, not agreement. The test
that guarded the claim asserted the absolute figure, so it passed while the claim it protected was
wrong.

Measured relatively, across the three named starts:

- **5 of 36 rows** disagree by more than 0.1 %
- **4 exceed 1 %**
- the worst is **12.07 %**, with parameter solutions 0.091 apart

`success = True` from every optimiser does not mean they found the same solution. Both the absolute
and the relative spread are now stored per row.

## 2. Worse: low spread did not indicate correctness

The five discordant rows were validated against a deterministic grid-and-polish check, and it found
something sharper than expected. On **five rows the grid beat every named start**, and those are
*not* the rows where the named starts disagreed:

| C₀ | η₀ | τ_c/T₂ | grid beats named by | named spread |
|---|---|---|---|---|
| 0.4 | 0.10 | 0.05 | **9.715 %** | 0.115 % |
| 0.5 | 0.05 | 0.05 | 4.585 % | 0.026 % |
| 0.4 | 0.05 | 0.05 | 4.498 % | 0.019 % |
| 0.5 | 0.02 | 0.05 | 1.453 % | 0.004 % |
| 0.4 | 0.02 | 0.05 | 1.425 % | 0.003 % |

All five are **principal-regime** rows. On the worst, the three named starts agreed to 0.115 % and
all three sat 9.7 % above the lower grid-and-polish candidate, which lies on the g₀ boundary. So across-start agreement
was *anti*-correlated with correctness, and a best-of-three would have published wrong numbers on
exactly the rows C26's short-correlation clause rests on.

The deterministic 121 × 121 grid scan and its polish are therefore **part of the method**, not a
diagnostic. The grid route supplies the selected minimum on 11 of 36 rows. It is seed-free, so E
stays deterministic.

**The determinism wording is corrected accordingly**: I_B is a *best-of-candidates estimate* over
three named starts plus a deterministic grid scan and its polish — **not a certified global
infimum**, and not start-independent. The artifact says so, and a test asserts the artifact does not
claim otherwise. Nothing here identifies a *true* minimum; the language throughout is
"grid-stable minimum" or "lower grid-and-polish candidate".

**Grid refinement.** Recomputing every row at 241 × 241 changes the best-of-candidates value by at
most **1.28 × 10⁻¹¹** relatively (worst row C₀ = 0.5, η₀ = 0.02, τ_c/T₂ = 0.2), so the scan is
converged at 121. The figure depends on which candidates are compared, so the artifact records the
method alongside it.

## 3. The regression gate no longer accepts a lower number automatically

Note 15's gate classified any sufficiently lower I_B as "reference under-converged". That direction
is plausible but it is not proof, and a rule that accepts anything pointing downward would let a real
regression through whenever it happened to point that way. The gate now has three outcomes:

- **breach** — this run is worse. A failure.
- **reference_under_converged** — accepted only when the row is in an explicit allowlist *and* every
  candidate, all three named starts and the grid route, lies below `res7A`.
- **review_required** — anything else that is lower. Not a pass; `--check` exits nonzero.

The two known rows (C₀ = 0.9, η₀ = 0.05 and 0.10, τ_c/T₂ = 0.2) are allowlisted with their
grid-confirmed values and satisfy the unanimity condition. There are currently **0 breaches and 0
rows requiring review**.

## 4. C13 is withdrawn; C26 supersedes it

Note 15 rewrote C13 in place. That was wrong, and the C01/C21 precedent gives the right shape.

**C13 is restored to its historical statement and marked `withdrawn`**, keeping its own run
(`sid_run7.py`) and its own output (`res7A`). Its exact-zero assertion is false: at τ_c/T₂ = 0.2 with
η₀ = 0.02 the pointwise band retains 3.6 × 10⁻³ of the unconstrained rate, with 21 of 40 τ points
passing the separation guard. **Exact zero means non-identifiability; 3.6 × 10⁻³ means difficult but
asymptotically identifiable.** That is a change of kind, not of magnitude, and it cannot be absorbed
by tightening a range in place.

**C26 is added as `result`, `supersedes: C13`**, pointing at `sid_run9.py` and
`res9_identifiability_T2.json`. It carries the dimensionless criterion ΔΓ_φ/Γ̂ > 2η₀ with
ΔΓ_φ/Γ̂ = 0.25·τ_c/T₂, the corrected boundary behaviour, the Markov retention 2.05 × 10⁻³ to
3.09 × 10⁻² at τ_c/T₂ ≤ 0.2 (2.05 × 10⁻³ to 2.33 × 10⁻² over principal contrasts alone) and 38–53 %
at η₀ = 2 % for τ_c/T₂ ≥ 1, and the statement that I_B is a best-of-candidates estimate.

This is a bookkeeping correction, not a scientific demotion. The withdrawal separates a false
formulation from its supported replacement, which is what the ledger's status vocabulary is for.
Note that C26's short-correlation range moved slightly from note 15's figures (2.1 × 10⁻³ → 2.05 ×
10⁻³) because the grid corrected the very rows that set the lower bound.

## 5. E closes

With the above, all six conditions hold and are asserted by `tests/test_roadmap_E.py`. E is complete
and never imported `sid_policies`, so **G is unblocked and unaffected**. Next is G's immutable
operating-point configuration, preserving the five reproducible pilot calibrations, and then B.
