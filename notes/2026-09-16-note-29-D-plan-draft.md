# Signals in Darkness — note 29: roadmap D, the D0 specification — DRAFT r3 for review

**Revision log**

| r | Date | Commit | Change |
|---|---|---|---|
| 1 | 16 Sept 2026 | `29302f6` | First plan: what exists, the information-rate diagnosis, eight open decisions. |
| 2 | 17 Sept 2026 | `986c48b` | The review's eight decisions adopted; matched marginal, two estimands, a proposed algorithm, checks, uncertainty rules, gates. |
| 3 | 17 Sept 2026 | this draft | Three mathematical corrections from the review: the latent state is filtered **unwrapped** (the wrapped kernel is a different process); the score recursion carries its **quotient-rule term**; the Fisher estimator becomes the **conditional-information average**, because S_N²/N does not concentrate. Adds the interval construction, corrected cost arithmetic and pre-pilot freezing rules. |

**Status: DRAFT r3.** No D calculation has been run and C14 is unchanged. D gates nothing. The
baseline library extraction and its synthetic tests are approved to proceed independently of this
draft; correlated-model checks and pilots await its acceptance.

## 1. The problem

The four-outcome likelihood exists only inline in [`sid_run7.py`](../analysis/runs/sid_run7.py) §B,
with the oscillator phase redrawn independently each shot. Under an AR(1) oscillator phase the
record is not i.i.d., so D's answer is a per-shot information **rate**. Run7's phase is von Mises,
so adopting a Gaussian AR(1) process changes the marginal as well as adding correlation; D fixes the
marginal by construction and measures the residual difference separately.

## 2. Model

**Phase.** A point-sampled Gaussian AR(1) process:

  x_n = ρ x_{n−1} + √(1−ρ²) σ ξ_n,  ξ_n ~ N(0,1) i.i.d.,  x ~ N(0, σ²) stationary,

with the emission periodic in x. **σ is fixed by matching the stationary first circular moment** to
the von Mises at the same κ: E[e^{ix}] = e^{−σ²/2} = I₁(κ)/I₀(κ). Matching that moment does not make
the distributions identical; the residual is measured in ND6 and never folded into the correlation
effect. The exact σ values for κ = 5 and κ = 10 are computed to full precision and frozen at D1.

**Correlation.** τ_osc = 5 shots, ρ = e^{−1/5}, with ρ = 0 as the matched control at the same σ. A
declared sensitivity choice.

**Emission.** Run7's law at fixed phase offsets, conditionally independent given the phase:

  P(B₁,B₂ | x, ε) = ¼ (1 + B₁ C̄₁ cos(x+ph₁)) (1 + B₂ C̄₂ cos(x+ε+ph₂)),  C̄₁ = C̄₂ = 0.9.

**Signal.** The variance channel keeps run7's white Gaussian modulation, s = 0.3; oscillator
parameters are identical under both hypotheses.

**Offsets and records.** Offsets are frozen at the maximisers found at ρ = 0 under the matched
marginal and reused at every ρ. Records are paired across ρ by common random numbers.

## 3. Two estimands, kept distinct

| Channel | Run7, independent phase | D, correlated phase |
|---|---|---|
| Slope | `sqrt(FI_eps)` | C_eff,slope(ρ) = √J(ρ), J a Fisher-information **rate** |
| Variance | invert `I_ext_exact(C_eff, 0.3) = KL` | invert `I_ext_exact(C_eff, 0.3) = D(ρ)`, D a KL **rate** |

A small-ε Fisher calculation cannot substitute for the finite-amplitude variance KL.

## 4. Algorithm

### 4.1 The latent state is filtered unwrapped

r2 proposed a filter over the wrapped phase. **That is a different process.** States x and x+2π
share a wrapped phase, but their next-step means ρx and ρx + 2πρ differ by 2πρ, which is not
equivalent modulo 2π for general ρ: the wrapped chain is not a lumping of the Gaussian one, and a
projection preserves the Markov property only under lumpability conditions that do not hold here.

D therefore filters the **unwrapped Gaussian state on a truncated real grid**:

- grid x_i on [−L σ, L σ] with M points;
- T[i,j] ∝ N(x_j ; ρ x_i, (1−ρ²)σ²), rows normalised;
- the periodic emissions are evaluated directly at x_i, no wrapping step;
- initialisation is the **discretised chain's own stationary distribution** (left eigenvector of T),
  not the continuous N(0, σ²);
- convergence is in **grid spacing (M) and tail range (L)**, replacing r2's wrapping-range check.

### 4.2 Filter and tangent, with the quotient-rule term

  α̃_n = (Tᵀ α_{n−1}) ⊙ E_{y_n},  Z_n = Σ_i α̃_{n,i},  α_n = α̃_n / Z_n,
  α̃′_n = (Tᵀ α′_{n−1}) ⊙ E_{y_n} + (Tᵀ α_{n−1}) ⊙ ∂_ε E_{y_n},  Z′_n = Σ_i α̃′_{n,i},
  **u_n = Z′_n / Z_n,  α′_n = α̃′_n / Z_n − α_n u_n.**

r2 said only that both vectors are renormalised by Z_n, which is wrong: the normalised filter is a
quotient, so its derivative carries the second term. The invariant **Σ_i α′_{n,i} = 0** is asserted
at every step. On the review's synthetic two-state fixture, finite differences give
**0.09116734785**, the corrected recursion agrees, and dividing by Z_n alone gives
**0.36456553850**. ND4 rejects the omission explicitly.

### 4.3 The estimator is a conditional-information average

S_N = Σ_n u_n is retained **for derivative checks only**. It is not the estimator: S_N²/N is
unbiased for the finite-record information but its per-record variance need not shrink with N. Even
for i.i.d. Bernoulli data, averaging 16 such estimates leaves about **35 % relative standard error
in J** however long the records, so longer records alone do not cure it.

The estimator averages the conditional information along the filtered history:

  Ĵ = (1/N) Σ_n Σ_{y ∈ 4 outcomes} [∂_ε p_ε(y | Y_{<n})]² / p_ε(y | Y_{<n}) |_{ε=0},

with p_ε(y | Y_{<n}) = Σ_i (Tᵀα_{n−1})_i E_y(x_i, ε) and its derivative taken from the same tangent.
This keeps the full-history filter and tangent — it is **not** stationary single-shot averaging —
and at ρ = 0 it reduces exactly to the i.i.d. single-shot Fisher information, which supplies an
exact nesting check.

### 4.4 The KL rate

Two filters per record — emissions marginalised over run7's own 41-point white-Gaussian grid,
against unmodulated emissions — accumulating D̂ = (1/N) Σ_n log(Z¹_n / Z⁰_n) under p₁. This is a
time average of log ratios and does concentrate; its precision is still set by the pilot.

## 5. Numerical checks, all before any outcome-bearing run

| Check | Requirement |
|---|---|
| ND1 nesting | At ρ = 0, Ĵ and D̂ reproduce the i.i.d. single-shot Fisher information and KL from the extracted run7 functions, under the same discretised marginal, to a stated tolerance. |
| ND2 grid | Convergence in spacing M and tail range L, below a stated fraction of the 2 % tolerance. |
| ND3 brute force | On short records (N ≤ 8) the filter's likelihood equals an explicit sum over latent grid paths. |
| ND4 score | The analytic tangent matches central differences on fixed records **and** the un-corrected normalisation (α̃′/Z alone) is rejected, using the two-state fixture above. |
| ND5 simulator | Stationary variance, first circular moment and ρ̂ reproduce their targets within sampling error. |
| ND6 marginal | The von Mises baseline (ρ = 0) against the Gaussian baseline (ρ = 0), reported separately as the marginal effect. |
| ND7 burn-in | The conditional-information average is stable in the discarded burn-in length, by a stated criterion, for both filter and tangent. |

A failed check blocks the outcome.

## 6. Interval construction and classification

r2 named a generic t-interval without saying how a rate becomes a contrast ratio. Specified:

1. **Denominator.** J(0) is the directly computed i.i.d. value, deterministic under the matched
   marginal; it is the primary denominator, not a second Monte-Carlo estimate.
2. **Interval for J(ρ).** Across R paired records, R̄ ± t(0.975, R−1)·s/√R on Ĵ(ρ).
3. **Transform.** g(J) = √(J/J(0)) − 1 is monotone increasing, so the signed interval maps
   endpoint to endpoint.
4. **Absolute image.** If the signed interval [lo, hi] contains 0, the absolute interval is
   [0, max(|lo|,|hi|)] — an interval spanning zero must contain zero after the transform. Otherwise
   it is [min(|lo|,|hi|), max(|lo|,|hi|)].
5. **Classification.** BELOW if the absolute upper end < 2 %; ABOVE if the lower end > 2 %;
   **UNRESOLVED if it straddles 2 %**.
6. **Nonpositive bounds.** If the lower bound of Ĵ(ρ) is ≤ 0, the ratio is not formed and the point
   is UNRESOLVED, as roadmap F does for R_lo ≤ 0.
7. **Numerical error.** If the ND2 and ND7 residuals are not below their stated fraction of the
   tolerance, the point is UNRESOLVED on numerical grounds rather than classified.

The variance channel is reported separately with its own interval. Agreement between the two
channels is a further statistic, never D's change-from-independence criterion.

## 7. Gates and the pre-pilot freeze

- **D0** — this specification.
- **D1** — the baseline library extraction with synthetic tests (approved, proceeding), preserving
  run7's actual search: the variance channel searches `grid[::3]`, the slope channel the full 13×13
  grid. Then the unwrapped filter, tangent, estimator and simulator; ND1–ND7; a measured cost.
- **The pre-pilot freeze.** Before the variance pilot runs, freeze in
  `analysis/protocol_D.json`: the pilot's seeds, record length, deadline, the sizing rule that
  turns pilot variance into N and R for the outcome run, the numerical tolerances, and the
  filter/tangent burn-in convergence criteria. Freezing these after the pilot would leave the
  sizing procedure unspecified.
- **D2** — the outcome run at κ = 5 (primary) and κ = 10 (sensitivity), ρ ∈ {0, e^{−1/5}}, and
  C14's disposition.

## 8. What D will still not settle

- One correlation time, two κ, one signal model, frozen offsets: not a general servo equivalence,
  and a null result does not promote C14 beyond `pilot`.
- Jointly unknown oscillator and signal models stay outside D.
- On identifiability: comparable correlation times do not by themselves establish
  non-identifiability, and distinct times do not establish identifiability. D reports the size of an
  effect under a fixed declared design.
- F's pointwise verdicts concern the binary mid-fringe comparator and do not transfer here.

## 9. Cost

r2's "~10¹⁰ flops" was wrong in both arithmetic and unit. One propagation per shot at R = 16,
N = 2×10⁵ and M = 256 is

  R·N·M² = **2.097152×10¹¹ matrix terms**,

and the score recursion adds a second propagation while the KL channel runs two filters, so the
real count is several times that. This remains an **estimate**: D1 measures it, and no sizing rule
is set from an unmeasured cost.
