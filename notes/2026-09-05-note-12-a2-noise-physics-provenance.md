# Signals in Darkness — execution note 12 (5 Sept 2026): roadmap A2, noise-physics provenance

A2 asked whether the prior art behind C03, C21 and C23 reaches the layer at which C23 actually
operates. It closes as a **bounded prior-art audit, not as proof of uniqueness**. Nothing here
changes evidential standing; ledger status records what the evidence supports, not who first
thought of it. Two claims are re-scoped in attribution only, and one model-consistency item is
opened that is *not* a prior-art gate.

## 1. The three layers, kept apart

The audit was structured so that a rich haul at the lower layers could not be mistaken for an
answer at the top one.

| layer | content | standing |
|---|---|---|
| 1 — noise physics | Gaussian dephasing functional, filter functions, cumulant truncation, OU closed forms, OU→AR(1) | **standard**; the project claims none of it |
| 2a — spectral expansion | the mid-fringe rate as a Gaussian information rate; validity controlled by δ(0) | objects textbook; the criterion's specific form not found published within the boundary |
| 2b — Bernoulli expansion | the extremum divergence's leading-order error and its contrast dependence (C21) | quadratic approximation textbook; the base-rate dependence of its *error* not found within the boundary |
| 3 — the crossover-validity map | evaluating those error criteria **on the crossover curve itself** (C23) | **the method is prior art; this instantiation was not found** |

## 2. Layer 3 — the gate

**The move is prior art.** Testing whether a boundary derived from a leading-order expansion lies
inside that expansion's own validity region, and obtaining a *parameter-dependent* verdict, is a
Ginzburg-style self-consistency test. Hohenberg & Krekhov, *Phys. Rep.* **572**, 1 (2015),
arXiv:1410.7285, **Sec. V.B, pp. 17–18**, read at full text from the review PDF: it tests the
self-consistency of mean-field theory using the Ginzburg–Landau expansion's own fluctuation
estimate, attributes the test to Levanyuk (1959) and its reformulation to Ginzburg (1960), derives
a parameter-dependent validity region, and contrasts conventional superconductors
(E_F/T_c ~ 10³–10⁴) against high-T_c materials (E_F/T_c ~ 1–10). That is C23's logical shape: valid
over part of the parameter range, not over all of it.

**The wording matters.** The record states:

> C23 is a Ginzburg-style self-consistency test applied to a binary-information crossover.

It does **not** state that C23 *is* the Levanyuk–Ginzburg criterion. That name concerns fluctuation
corrections around a critical mean-field theory, and the geometry differs: Ginzburg tests validity
approaching a single critical point, C23 tests pointwise along a curve in the (C̄, s) plane. The
logical method is prior art; the sensing-specific instantiation — an information-theoretic error
criterion evaluated on a measurement-design boundary — was not found by the bounded search.

Attribution: **cite Hohenberg & Krekhov directly.** Levanyuk (1959) and Ginzburg (1960) are recorded
as **second-hand and unread**, and stay so until their originals are read.

**What "not found" means.** The Layer-3 negative carries a structural weakness that the record must
keep: the arXiv API search covered **title and abstract only**, and this move is exactly the kind of
remark that lives in a footnote or a results-section aside. INSPIRE-HEP, Google Scholar, ADS full
text, Scopus, Web of Science, MathSciNet, zbMATH and IEEE Xplore full text were not searched, and no
citation-graph enumeration was run for this dimension. The correct reading is *the instantiation was
not found*, not *the instantiation does not exist*.

## 3. Layer 1 — C02 is prior art, and is re-scoped

The project's exact mid-fringe lag correlation

    r_k = C̄² e^{−s²} sinh(s² a_k)

**is** the pair correlator of Wudarski, Zhang, Korotkov, Petukhov & Dykman, *Phys. Rev. Applied*
**19**, 064066 (2023), arXiv:2207.01740, Eq. (29), evaluated at φ_R = π/2, under f₀ = s²,
f_k = s² a_k and the project's covariance→correlation normalisation (variance ¼). Verified here
numerically over an 18-point grid in (C̄, s, a_k): **maximum relative difference 3.1 × 10⁻¹⁵**.
Their Eq. (34) likewise yields the card's a_k = e^{−kc/τ_c}F(u).

C02 keeps its status. What changes is what it may be presented as: the correlator is not the
project's. The remaining contribution is its **use inside the spectral information-rate comparator
and the sequential crossover**, not the formula.

Independent corroboration at arbitrary readout phase, with an explicit visibility prefactor:
Rojas-Arias et al., arXiv:2509.22073, Eqs. (4)–(5). The two-exponential structure was already in
Fink & Bluhm, *PRL* **110**, 010403 (2013), Eq. (2), which never evaluates at mid-fringe and carries
no contrast prefactor.

Two corrections the audit made to its own sources, both kept:

- **Klauder & Anderson (1962)** must be cited only for the echo-function structure. Their "Gaussian"
  means Gaussian *diffusion* of frequency and is explicitly non-stationary; they are **not** the
  source of the second-cumulant Gaussian-noise result.
- **Degen, Reinhard & Cappellaro**, RMP 89, 035002, Eq. (20) is the **unit-contrast** case. It
  carries no readout contrast, so the finite-contrast extremum divergence is not in the review. What
  the RMP does establish is that both operating points are named and separately analysed
  (Secs. IV.E.1–IV.E.2), which the project must concede.

## 4. A model-consistency item, opened separately

The audit found a real internal gap, unrelated to prior art. The card's lag correlation is

    ρ_k = F(u) e^{−k c/τ_c} = A φ^k,   k ≥ 1,   F(u) = (cosh u − 1)/(u − 1 + e^{−u}).

A scalar AR(1) requires ρ_k = φ^k **including ρ₁ = φ**. Since ρ₁ = F(u)φ, that fails unless
F(u) = 1, which is the point-sampling limit u → 0. Because ρ_k = φ ρ_{k−1} holds only after lag one,
the stationary Gaussian integrated-phase process admits an **ARMA(1,1)** representation, not an
AR(1) one. Verified here: F(1e−6) = 1.0000000000, F(0.5) = 1.198, F(1.0) = 1.476, F(2.0) = 2.433,
with ρ₂/ρ₁ = φ throughout.

Bounded impact, recorded precisely:

- The OU **frequency** process remains Markov / AR(1) when sampled at cycle boundaries.
- Its finite-window **integrated Ramsey phase** is generally ARMA(1,1).
- `analysis/lib/sid_lib.py` simulates the phase itself as AR(1), so the committed HMM is an exact
  reference **only for the point-sampled reduction**.
- **C02, C05 and C23 are not numerically disturbed**: all are computed in that reduction.
- **C04's validation scope** is narrowed in wording to "point-sampled latent-AR(1) binary reference".
- **C08** uses the correct filtered covariance — `analysis/runs/sid_run3.py` folds the filter factor
  as a₁ = φF(u) and fits ρ_k = ρ₁φ^{k−1}, which is the ARMA-consistent geometric form; `sid_run4.py`
  and `sid_core.py` pass F separately and as F² respectively. All three are consistent. What has
  **not** been done is validating the binary comparator against an **exact ARMA(1,1) latent
  likelihood**.

That last point is roadmap item **F**, a narrow model-consistency check, not a prior-art gate. It
should be resolved before the v2.0 manuscript freezes, but it does not block the freeze of the card.

## 5. Status of roadmap A

A1 and A2 are both complete. A is closed as a bounded audit: the operating-point dichotomy, its
amplitude-dependence mechanism, the dephasing and OU machinery, and the exact mid-fringe correlator
are all prior art and are cited; the quantitative detection-theoretic crossover, the τ-optimised
physical map, the identifiability layer, and the Ginzburg-style validity map of the crossover were
not found within the searched boundaries. No claim's status changed as a result of either audit,
which is as it should be: these audits establish attribution, not evidence.
