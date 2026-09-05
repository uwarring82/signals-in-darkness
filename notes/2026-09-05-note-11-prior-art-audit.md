# Signals in Darkness — execution note 11 (5 Sept 2026): prior-art boundary for the operating-point crossover

Roadmap A asked whether the operating-point crossover, the correlation channel or the
detection–identification framing had already appeared in the literature. The answer changes the
framing of C05 but does not invalidate its numbers: the two Ramsey response mechanisms are prior
art, while their quantitative sequential-information crossover was not found by the targeted
search. C05 remains a `result`, re-scoped to that boundary.

This is a priority audit, not a proof of absence. Approximately 22 citing papers were enumerated;
only five or six were read in full, with the remainder checked at abstract or search-result level.
Accordingly, every negative conclusion below is phrased as **not found by targeted search**.

## 1. Scope and reading levels

The audit covered five dimensions: Sakuldee and Cywiński 2020 in full text; Sakuldee and
Cywiński 2019 in full text; their and the directly relevant papers' citers; Fisher-information
analyses of Ramsey operating points; and sequential detection in quantum sensing. Sources that
were only visible as an abstract or search result were not treated as read papers.

| source or group | reading level used here | role in the boundary |
|---|---|---|
| Sakuldee & Cywiński 2020, arXiv:1907.01784 | full text | projective-measurement correlations as noise filters; slow-noise and non-Gaussian spectroscopy |
| Sakuldee & Cywiński 2019, arXiv:1903.06463 | full text | inference and postselection for a quasi-static environment |
| Wudarski et al. 2023, arXiv:2207.01740 / Phys. Rev. Applied 19, 064066 | full text, including the exact Gaussian correlators | decisive operating-point mechanism |
| Wudarski, Zhang & Dykman 2023, arXiv:2304.05241 / Phys. Rev. Lett. 131, 230201 | full arXiv manuscript; separate journal supplement not verified | bibliographic context only; disputed supplement attribution not used |
| approximately 22 enumerated citers | five or six full text; remainder abstract or search-result level | bounded check for an existing crossover, latent-AR(1) detector or detection-delay treatment |

The exact identifiers and reading levels are recorded in `references/verification.md`; the
citations themselves are in `references/bibliography.bib`.

## 2. The mechanism already present in Wudarski et al.

Wudarski et al. study periodically repeated binary Ramsey measurements under evolving
low-frequency noise, including exponentially correlated Gaussian noise. Their Eq. (29) gives the
exact Gaussian one-shot probability and centered pair correlator,

    r₁ = ½[1 + exp(−t_R/T₂) exp(−f₀/2) cos φ_R]

    r̃₂(k) = ⅛ exp(−2t_R/T₂) exp(−f₀)
              × [exp(f_k) − 1 − cos(2φ_R)(1 − exp(−f_k))].

The following expansion is an algebraic consequence of that published exact expression, not a
separate literature claim. Removing the common factor `exp(−2t_R/T₂) exp(−f₀)` gives

| Ramsey phase | centered pair correlator |
|---|---|
| mid-fringe, φ_R = π/2 | f_k/4 + O(f_k³) |
| extremum, φ_R = 0 | f_k²/8 + O(f_k⁴) |

Thus the pair-correlation response is first order in the inter-shot covariance at mid-fringe and
second order at the extremum. Independently, `r₁` shows that one-shot contrast loss is maximal at
the extremum and responds at first order in the zero-lag variance `f₀`. Calling the entire
extremum channel "second order" would therefore be wrong: only its centered pair correlation has
that expansion.

The paper also explicitly recommends comparing correlators measured at different Ramsey phases.
The qualitative division between an extremum contrast-loss response and a mid-fringe correlation
response, together with the exact nonlinear amplitude dependence of the relevant Ramsey moments,
is therefore prior art. Applying those ingredients to a sequential-information objective and
locating the resulting boundary is the remaining project contribution.

## 3. The Sakuldee "optimal working point" is not a readout phase

Sakuldee and Cywiński 2020 establishes the measurement-stream formalism: correlations of repeated
projective outcomes can be written as noise-filtering signals, with particular value for slow and
non-Gaussian noise. Its phrase "optimal working point" does not mean an optimal Ramsey fringe
phase. The full text defines it as the sweet spot or clock transition where the first derivative
of the qubit splitting with respect to a noisy parameter vanishes and quadratic coupling becomes
leading.

Sakuldee and Cywiński 2019 treats a quasi-static environment as a latent quantity progressively
learned through repeated measurements, with postselection and environment narrowing. Both papers
remain required context for measurement-stream inference and the slow-noise limit. Neither was
found to compare the sequential detection information or delay of fringe extrema and mid-fringe
readout.

## 4. Attribution not used

An intermediate audit report attributed a formula containing both `sin² φ_R` and `cos² φ_R`, and
a quotation about weak Gaussian noise at `φ_R = 0`, to supplementary Eq. 6 of the 2023 Physical
Review Letters paper associated with arXiv:2304.05241. The full arXiv manuscript does not contain
that equation or quotation; the nearest passage concerns two-level-system noise at small `φ_R`.
The separate journal supplement was not verified. That attribution is therefore **unverified and
not relied upon**. The operating-point conclusion above stands on the full-text-verified Physical
Review Applied paper and the displayed algebra.

## 5. Decision for C05

C05 is re-scoped, not demoted. Its status, numerical output and uncertainty record are unchanged.
The ledger statement is now:

> For the stated binary-link/OU model and exact correlation-rate comparator, the
> sequential-information crossover between the established contrast-loss and pair-correlation
> responses occurs at τ_c/c = 4.65 as s → 0, 5.46 at s = 0.3 and 7.24 at s = 0.5 for C̄ = 0.4;
> at C̄ = 0.99 no crossover exists for s ≥ 0.5. The operating-point dependence of the Ramsey
> moments is prior art; the claimed result is the detection-theoretic boundary and its
> quantitative motion with amplitude.

The quantities claimed as this project's are the crossover locus, its finite-amplitude motion,
its disappearance in the stated high-contrast cases, and its use as a sequential detector design
boundary. The qualitative existence of the two response mechanisms is not claimed.

The targeted survey did not find the C05 numerical locus, C08's interrogation-time-optimised
physical map, C13's latent-process detection and calibrated-nuisance identifiability layer, or
C23's project-specific numerical validity boundary. These are scoped search findings, not claims
that the wider literature contains no such result.

## 6. Remaining exposure: C23

The audit did not cover C23's closest noise-physics prior art: the exact Gaussian dephasing
functional, cumulant and filter-function validity conditions, and possible earlier error maps for
binary Ramsey information. C23 remains a `result` because its numerical validity boundary and
error contours are reproduced and have not been contradicted. The project does not claim the
Gaussian dephasing functional or filter-function machinery as new.

Roadmap A is therefore split. **A1 is complete:** the operating-point and sequential-detection
audit passes with C05 re-scoped. **A2 is open and gates an unqualified v2.0 freeze:** a bounded
check will determine whether the contribution attached to C23 is only the project-specific
binary-information validity map, as currently expected.

No frozen card or earlier note was edited. `cards/v2.0-seed.md`, which is explicitly a mutable
restructure seed, records the new boundary and the A1/A2 split.

## 7. Claim-by-claim comparison matrix

Verdicts, per the review convention:
**(1)** directly anticipates the claim · **(2)** establishes adjacent machinery but not the claim ·
**(3)** does not anticipate it within the searched scope.

Distinctions, abbreviated in the column heads: **obs** same observation model (repeated Ramsey,
one binary outcome per shot) · **hid** same hidden process (OU/AR(1) latent phase) · **act**
operating point treated as a *choosable action* rather than a fixed convention · **τ/t**
interrogation time optimised against wall-clock cost · **seq** sequential delay under matched
false-alarm control · **nui** contrast or dephasing carried as a calibrated nuisance · **bnd** an
explicit crossover or identifiability boundary derived.

Reading levels are those of §1. Entries marked ~ are partial; see the note beneath each table.

### C05 — the detection-theoretic crossover and its motion with amplitude

| source | obs | hid | act | τ/t | seq | nui | bnd | verdict |
|---|---|---|---|---|---|---|---|---|
| Wudarski et al., PR Applied 19, 064066 (full text) | ✓ | ✓ | ✓ | ✗ | ✗ | ~ | ✗ | **2** |
| Wudarski, Zhang & Dykman, PRL 131, 230201 (arXiv text; supplement unverified) | ✓ | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | **2** |
| Jin, Ye & Ma, arXiv:2604.25705 (full text) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **2** |
| Meriles et al., J. Chem. Phys. 133, 124105 (full text) | ✓ | ~ | ✓ | ✗ | ✗ | ~ | ✗ | **2** |
| Degen, Reinhard & Cappellaro, RMP 89, 035002 (full text) | ✓ | ✗ | ✓ | ~ | ✗ | ✓ | ✗ | **2** |
| Sakuldee & Cywiński 2020 (full text) | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | **3** |
| Sakuldee & Cywiński 2019 (full text) | ~ | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | **3** |

The **act** column is where the prior art is strongest and the card must concede: Wudarski et al.
propose comparing correlators across φ_R, and Degen et al. publish a bias-point comparison. What no
row carries is **bnd** — a crossover locus — jointly with **seq**. Degen's `~` under τ/t is a
comparison against *integration time*, not interrogation time. Wudarski's `~` under nui is the
contrast prefactor appearing in the correlators without being treated as a calibrated nuisance.

### C08 — the τ-optimised physical map in T₂ and dead-time units

| source | obs | hid | act | τ/t | seq | nui | bnd | verdict |
|---|---|---|---|---|---|---|---|---|
| Arshad et al., PR Applied 21, 024026 (full text) | ✓ | ✗ | ✗ | ~ | ✗ | ✓ | ✗ | **2** |
| Sakuldee & Cywiński 2019 (full text) | ~ | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | **3** |
| Degen, Reinhard & Cappellaro (full text) | ✓ | ✗ | ✓ | ~ | ✗ | ✓ | ✗ | **3** |
| Wudarski et al., PR Applied (full text) | ✓ | ✓ | ✓ | ✗ | ✗ | ~ | ✗ | **3** |
| citer set, ~22 works (5–6 full text, rest abstract) | — | — | — | ✗ | ✗ | — | ✗ | **3** |

Arshad's `~` is a single-parameter optimum τ_opt ≈ ξ T̂_χ, ξ = 0.79–0.92, not a trade against dead
time. No row produces thresholds in τ_c/t_dead against contrast.

### C13 — identifiability under a constrained baseline class

| source | obs | hid | act | τ/t | seq | nui | bnd | verdict |
|---|---|---|---|---|---|---|---|---|
| Arshad et al. / Granade et al., NJP 14, 103013 (full text) | ✓ | ✗ | ✗ | ~ | ✗ | ✓ | ~ | **2** |
| Sakuldee & Cywiński 2019 (full text) | ~ | ✗ | ✗ | ✗ | ✗ | ~ | ~ | **2** |
| Sakuldee & Cywiński 2020 (full text) | ✓ | ~ | ✗ | ✗ | ✗ | ✗ | ~ | **2** |
| classical sequential-detection theory (Lorden, Lai, Fuh; full text) | ✗ | ~ | ✗ | ✗ | ✓ | ✗ | ✗ | **2** |
| citer set as above | — | — | — | — | ✗ | — | ✗ | **3** |

The three `~` in **bnd** are genuine but structural, not quantitative: a singular Fisher information
matrix cured by two settings (Granade); the 2π/τ aliasing degeneracy and multi-peaked posterior
(Sakuldee 2019 §II.3, Eq. 59); and the one-sided non-Gaussianity witness (Sakuldee 2020 §V). None
states a retained-information fraction, a τ_c ≲ T₂/5 collapse, or a criterion of the
ΔΓ_φ > 2η₀Γ̂ form.

## 8. Search boundaries

"Not found" is interpretable only against these. Anything outside them is unaudited, not absent.

- **Citer enumeration.** OpenAlex (14 citers of arXiv:1907.01784, 8 of arXiv:1903.06463) and
  Semantic Scholar (12 and 6); union ≈ 22 distinct works. Of these, 5–6 judged on-territory were
  read at full text; the remainder at abstract level only.
- **Citer cut-off.** 5 September 2026, the date of the audit. Anything indexed later is out of
  scope, as is anything neither database indexes.
- **Query families.** {optimal Ramsey phase, bias point, working point} × {correlation time,
  quasistatic versus white noise, crossover} × {Fisher information, quickest detection, CUSUM}.
- **Statistics-side queries**, for C13's latent object: "latent AR(1) binary", "clipped
  Ornstein-Uhlenbeck change detection", "probit AR(1) change point", "Bernoulli CUSUM
  autocorrelated", "Markov-modulated Bernoulli quickest change detection".
- **Languages and venues.** English-language, arXiv- and journal-indexed sources only. No theses,
  patents, conference-only proceedings, or non-indexed preprint servers were searched.
- **One source could not be reached.** Stoltenberg, Hjort et al., *Scand. J. Statist.* 48 (2021),
  which builds a clipped-OU latent object for estimation rather than detection: Wiley returned 403.
  Recorded as unverified, and its relation to C13 is therefore **unknown**, not absent.
- **Not audited at all.** C23's noise-physics prior art — the Gaussian dephasing functional,
  cumulant and filter-function validity. That is roadmap A2, and is why A2 gates the freeze.

The negative results above are therefore of the form *"not found within this boundary"*. They are
not, and must not be reported as, evidence that no such work exists.
