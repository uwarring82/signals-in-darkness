# Signals in Darkness — note 29: roadmap D, the D0 specification — DRAFT r2 for review

**Revision log**

| r | Date | Commit | Change |
|---|---|---|---|
| 1 | 16 Sept 2026 | `29302f6` | First plan: what exists, the information-rate diagnosis, eight open decisions. |
| 2 | 17 Sept 2026 | this draft | The review's decisions adopted. Adds the phase model with a matched marginal, two separate estimands, an observed-record algorithm with convergence criteria and a cost estimate, numerical checks, uncertainty rules, the classification rule and the gate structure. Records the von Mises versus Gaussian marginal problem the review identified. |

**Status: DRAFT r2.** No D calculation has been run, no D code exists yet, and C14 is unchanged. D
gates nothing (`ledgers/roadmap.yaml`: `gates_freeze: false`).

## 1. The problem, restated

The four-outcome likelihood exists only inline in [`sid_run7.py`](../analysis/runs/sid_run7.py) §B,
where the oscillator phase is redrawn independently every shot. With an AR(1) oscillator phase the
record is no longer i.i.d., so D's answer is a per-shot information **rate**. Marginalising a
correlated phase shot by shot would keep exactly the independence assumption D exists to test.

**The marginal problem** (review, r2). Run7's phase is von Mises with concentration κ. The
project's AR(1) machinery is Gaussian, so adopting it changes the *marginal* as well as adding
correlation, and a naive comparison would attribute both effects to correlation. D therefore fixes
the marginal by construction and measures the marginal change separately.

## 2. Model

**Phase.** A point-sampled Gaussian AR(1) process, wrapped to the circle:

  x_n = ρ x_{n−1} + √(1−ρ²) σ ξ_n,  ξ_n ~ N(0,1) i.i.d.,  φ_n = x_n mod 2π,  x ~ N(0, σ²) stationary.

**Marginal matching.** σ is fixed by matching the stationary first circular moment to the von Mises
distribution at the same κ:

  E[e^{i φ}] = e^{−σ²/2} = I₁(κ)/I₀(κ).

Matching this moment does **not** make the two distributions identical; the residual difference is
measured and reported separately (§5, ND6), never folded into the correlation effect. The exact σ
values for κ = 5 and κ = 10 are computed to full precision and frozen in the D1 specification.

**Correlation.** τ_osc = 5 shots, so ρ = e^{−1/5}, with ρ = 0 as the matched control at the same σ.
This is a declared sensitivity choice, not an inference from any measurement.

**Emission.** Run7's four-outcome law at fixed phase offsets, conditionally independent given φ:

  P(B₁,B₂ | φ, ε) = ¼ (1 + B₁ C̄₁ cos(φ+ph₁)) (1 + B₂ C̄₂ cos(φ+ε+ph₂)),  C̄₁ = C̄₂ = 0.9.

**Signal.** The variance channel keeps run7's white Gaussian modulation, s = 0.3, and the oscillator
parameters are held identical under both hypotheses.

**Phase offsets and records.** The offsets are frozen at the maximisers found at ρ = 0 under the
matched marginal, and the same offsets are used at every ρ. Records are paired across ρ by common
random numbers: the same innovation and outcome streams drive both, so the comparison is paired.

## 3. Two estimands, kept distinct

Run7 uses two different definitions, and the review requires both to survive.

| Channel | Run7, independent phase | D, correlated phase |
|---|---|---|
| Slope | `sqrt(FI_eps)` | C_eff,slope(ρ) = √J(ρ), J = Fisher-information **rate** |
| Variance | invert `I_ext_exact(C_eff, 0.3) = KL` | invert `I_ext_exact(C_eff, 0.3) = D(ρ)`, D = KL **rate** |

  J(ρ) = lim_N (1/N) E[(∂_ε log p_ε(Y₁..Y_N)|_{ε=0})²],
  D(ρ) = lim_N (1/N) E₁[log p₁(Y₁..Y_N) / p₀(Y₁..Y_N)].

A small-ε Fisher calculation cannot substitute for the finite-amplitude variance KL, and neither
channel's number is a substitute for the other's.

## 4. Algorithm: observed-record, no single-shot averaging

Averaging a single-shot Fisher information over the stationary phase would retain the original
problem, so both estimands are computed from whole records through a grid filter.

**Filter.** M phase points on (−π, π]; transition T[i,j] from the wrapped normal density of
x_j − ρ x_i with variance (1−ρ²)σ², summed over K wrapping images and row-normalised; the
stationary vector is the discretised wrapped normal, checked against the filter's own fixed point.
Forward step: α̃_n = (Tᵀ α_{n−1}) ⊙ E_{y_n}; Z_n = Σ α̃_n; α_n = α̃_n / Z_n.

**Score recursion (slope channel).** Differentiate that recursion in ε at ε = 0:

  α̃′_n = (Tᵀ α′_{n−1}) ⊙ E + (Tᵀ α_{n−1}) ⊙ ∂_ε E,  S_N = Σ_n Z′_n / Z_n,

with ∂_ε P = ¼ (1 + B₁C̄₁cos(φ+ph₁)) (−B₂ C̄₂ sin(φ+ε+ph₂)) analytic, both vectors renormalised by
Z_n each step. Estimator: Ĵ = S_N²/N, averaged over R independent records generated at ε = 0.

**Variance channel.** Two filters per record — emissions marginalised over the per-shot white
Gaussian on run7's own 41-point grid, against unmodulated emissions — accumulating the
log-likelihood ratio under p₁; D̂ = (1/N) Σ_n log(Z¹_n / Z⁰_n).

**Cost.** Both are O(M²) per shot. At M = 256, N = 2×10⁵ and R = 16 a cell is of order 10¹⁰
floating-point operations, expected in the minutes on one thread. **This is an estimate, not a
measurement**; D1 measures it before D2 is proposed.

## 5. Numerical checks, all before any outcome-bearing run

| Check | Requirement |
|---|---|
| ND1 nesting | At ρ = 0 the filter's rates reproduce the single-shot Fisher information and single-shot KL computed directly from the extracted run7 functions, under the same discretised marginal. |
| ND2 grid | Convergence in M and in the wrapping range K: the change in C_eff is below a stated fraction of the 2 % tolerance. |
| ND3 brute force | On short records (N ≤ 8) the filter's likelihood equals an explicit sum over latent grid paths. |
| ND4 score | The analytic score matches a central difference in ε on fixed records, to a stated tolerance. |
| ND5 simulator | The simulated phase reproduces σ², the first circular moment and ρ within sampling error. |
| ND6 marginal | The von Mises baseline (run7's own marginal, ρ = 0) against the Gaussian baseline (ρ = 0): reported as the marginal effect, never as part of the correlation effect. |

A failed check blocks the outcome.

## 6. Uncertainty and the classification rule

- R = 16 independent records per cell, paired across ρ by common random numbers; intervals are
  R̄ ± t(0.975, 15)·s/√16.
- **Primary quantity:** |C_eff,slope(ρ)/C_eff,slope(0) − 1|, compared with 2 %, at the matched
  marginal and identical phase offsets.
- **Classification:** BELOW if the interval lies wholly below 2 %; ABOVE if wholly above;
  **UNRESOLVED if it crosses 2 %.**
- The variance-channel change is reported separately with its own interval. Agreement between the
  two channels is a further statistic, not D's change-from-independence criterion.
- N and R are fixed before the outcome run, sized from a D1 variance pilot on disjoint seeds, as in
  roadmap F. No top-ups, no outcome-driven extension.

## 7. Gates

- **D0** — this specification, revised.
- **D1** — extract the four-outcome law into `analysis/lib` with baseline tests that preserve run7's
  actual search (the variance channel searches `grid[::3]`, the slope channel the full 13×13 grid);
  implement the filter, score recursion and simulator; run ND1–ND6; measure cost; and freeze a
  compact `analysis/protocol_D.json` with inputs, estimators, checks, uncertainty rules and budget,
  plus its digest. Its size reflects D's narrower scope.
- **D2** — the outcome run at κ = 5 (primary) and κ = 10 (sensitivity), ρ ∈ {0, e^{−1/5}}, and C14's
  disposition.

Each gate keeps its own approval; local commits are drafts until accepted.

## 8. What D will still not settle

- One correlation time, two κ, one signal model, frozen offsets: not a general servo equivalence,
  and a null result does not promote C14 beyond `pilot`.
- Jointly unknown oscillator and signal models stay outside D.
- On identifiability: comparable correlation times do not by themselves establish
  non-identifiability, and distinct times do not establish identifiability. D reports the size of an
  effect under a fixed declared design; it makes no identifiability claim.
- F's eventual pointwise verdicts concern the binary mid-fringe comparator and do not transfer here.

## 9. Cost

Not measured. §4's estimate is an expectation to be replaced by D1's measurement, and the budget is
frozen with the D1 specification before any outcome-bearing computation.
