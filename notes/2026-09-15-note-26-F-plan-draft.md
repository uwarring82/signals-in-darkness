# Signals in Darkness — note 26 (15 Sept 2026, DRAFT): roadmap F comparison plan

**Status:** DRAFT FOR REVIEW, not frozen. No ARMA(1,1) likelihood, pilot or F outcome has been
computed. Choices awaiting a decision are marked **[choice]**, and §9 collects them. This note
changes no card, ledger, earlier note or archived output. Once accepted, its numerical choices
are locked in a digest-bearing protocol file before any pilot runs (§8).

**Evidence snapshot:** `97e73b2` (tag `card-v2.0`), clean tree.

Roadmap F, as stated in [card v2.0](../cards/v2.0-frozen.md): compare the binary comparator
against an exact ARMA(1,1) latent likelihood at a few finite-window points, reporting numerical
convergence and Monte-Carlo uncertainty. Points and acceptance criteria are fixed before the
pilot. The physics is in [note 12 §4](../notes/2026-09-05-note-12-a2-noise-physics-provenance.md):
ρ_k = F(u)φ^k for k ≥ 1, with φ = e^{−c/τ_c} and u = τ/τ_c. So the finite-window integrated
phase is ARMA(1,1), while the committed HMM simulates AR(1) and is exact only as u → 0.

## 1. Pre-plan finding: the archived C08 map drops the filter factor

Found while sizing F, after the card-v2.0 freeze. It is a post-hoc diagnostic on committed
code and grids, not F evidence.

**What the code does.** [sid_run3.py:126](../analysis/runs/sid_run3.py) calls
`gp_rate_geom(rk_exact(Ct, s, a₁)/a₁, φ)`, with a₁ = φF(u). `gp_rate_geom(ρ, a)` models
r_k = ρ·a^k; both its docstring and its spectrum algebra (α = 1 + a² − 2ρa², β = 2a(ρ − 1))
say so. The map therefore uses r_k = (r₁/F)·φ^{k−1}, not the exact lag-1 correlation r₁. At
leading order in s² this is the point-sampled correlation, so the finite-window enhancement is
lost. `sid_run4.py`'s `gp_rate_geomfit` instead passes ρ = r₁/φ, which does match the exact
first lag, and that is the form note 02's Check 2 compared with the series.

**Size, per shot.** K1 is the exact-r_k sinh series with A = F(u) (run4 kernels), K2 the
lag-1-matched fit and K3 the archived map form:

| Point (physical map units) | u | F | K3/K1 | 1/F² | K3 / series(A = 1) | K2/K1 |
|---|---:|---:|---:|---:|---:|---:|
| C₀ = 0.4, τ_c/t_dead = 210, τ/T₂ = 0.512 | 0.0244 | 1.0082 | 0.9852 | 0.9838 | 1.0006 | 1.0006 |
| C₀ = 0.9, τ_c/t_dead = 45, τ/T₂ = 0.491 | 0.1091 | 1.0377 | 0.9322 | 0.9286 | 1.0004 | 1.0004 |
| C₀ = 0.4, τ_c/t_dead = 20, τ/T₂ = 0.3 | 0.1500 | 1.0526 | 0.9030 | 0.9026 | 1.0001 | 1.0000 |
| C₀ = 0.4, τ_c/t_dead = 10, τ/T₂ = 1.0 | 1.0000 | 1.4762 | 0.4592 | 0.4589 | 1.0016 | 1.0003 |

The archived form equals the point-sampled comparator to within 0.2 %. It sits below the
ARMA-consistent series by about 1/F².

**Consequence for C08's thresholds.** A replication of the map loop reproduces all four stored
thresholds exactly (211.759, 139.980, 75.232, 44.842). On the committed τ_c grid, whose step is
10.9 %, correcting the fold leaves them unchanged. Solving continuously on the same τ grid gives:

| C₀ (grid value) | Stored (grid) | Archived form, continuous | K2, continuous | K1, continuous | Change K1 vs archived |
|---|---:|---:|---:|---:|---:|
| 0.4004 | 211.76 | 209.32 | 205.69 | 205.83 | −1.7 % |
| 0.4960 | 139.98 | 137.61 | 133.98 | 134.06 | −2.6 % |
| 0.6977 | 75.23 | 71.42 | 67.84 | 67.88 | −5.0 % |
| 0.8994 | 44.84 | 44.71 | 41.19 | 41.20 | −7.8 % |

**Direction:** the archived map understates the mid-fringe rate. Its thresholds are therefore
too high, and it errs toward the extremum. C08's numbers stand at the grid resolution they are
stated at; its provenance description does not.

**Record statements that are wrong for C08, and where they are:**

- [note 12:104-106](../notes/2026-09-05-note-12-a2-noise-physics-provenance.md) says run3 "fits
  ρ_k = ρ₁φ^{k−1}, which is the ARMA-consistent geometric form … All three are consistent";
- [labbook pass 6](../labbook/2026-09-05-pass-6-noise-physics-provenance.md), line 9, repeats it;
- [seed :36](../cards/v2.0-seed.md) and [frozen card :165](../cards/v2.0-frozen.md) carry the
  verbatim caveat "C08 uses the correct ARMA-consistent covariance";
- [frozen card :156-163](../cards/v2.0-frozen.md) says the archived C05 values *and C08
  thresholds* use a fit "which matches the exact first lag", and that note 02's Check 2 links it
  to C04. This is true for C05, whose crossover is point-sampled with F = 1. It is false for C08,
  because Check 2 tested run4's fit, not run3's map form. The model-generated review proposed this
  sentence in the last freeze-review round, so the review introduced the defect;
- the same claim is repeated in [note 25:54](../notes/2026-09-15-note-25-freeze-review-evidence.md),
  [pass 25:9](../labbook/2026-09-15-pass-25-card-v2-freeze.md), and the `card-v2.0` milestone
  summary in `ledgers/milestones.yaml` (projected to `docs/milestones.md`). The `card-v2.0` tag
  message only calls the "C05/C08 geometric-fit provenance" explicit. It asserts no link, but it
  points readers to the statements above.

**Handling [choice], not decided here.** Supersede, never edit in place:

- (a) an erratum note against card v2.0, note 12, note 25 and passes 6 and 25, plus a correcting
  milestone entry rather than a rewritten summary;
- (b) separately from F, decide whether a map recomputed with the corrected fold supersedes C08
  as a new claim, or whether C08 stays grid-resolved under an erratum. This is deterministic and
  needs no likelihood;
- (c) add a guard test asserting that the map's lag-1 binary correlation equals
  `rk_exact(Ct, s, φF)`. It fails on the current producer, which is its purpose, so it lands
  with whichever of (a) or (b) is chosen;
- (d) commit the two diagnostic scripts behind §1 and §5, currently outside the repository,
  before this note is accepted, so that its numbers have a producer.

**Why this belongs in F's plan:** the frozen caveat assumes the covariance is right and only
accuracy is unvalidated. In fact three different comparator implementations are in play, and F
tests all three (§2).

## 2. Question and estimand

**Estimand.** R_ARMA(C̄, s, u, c/τ_c) is the per-shot relative-entropy rate of the mid-fringe
(θ = π/2) binary record against the i.i.d. null p₀ = ½. The latent phase is the finite-window
integrated OU phase. Per-wall-clock rates follow by dividing by c exactly, so F works per shot.

**Comparators under test.** All three are deterministic:

- **K1:** sinh-series spectral comparator with exact r_k = C̄²e^{−s²}sinh(s²F(u)φ^k), six terms
  and 1024 frequency samples (the run4 kernels). This is the exact-correlation class that C04
  validated in the point-sampled limit.
- **K2:** lag-1-matched geometric fit, ρ = r₁/φ with r₁ exact (run4 `gp_rate_geomfit`).
- **K3:** the archived map form, ρ = r₁/(φF) (sid_run3.py:126). If K1 is accurate, K3 must fail
  wherever F is large (§7). That is the plan's built-in counterexample.

**Out of scope:** the extremum stream's temporal information (C24), the servo likelihood (D),
detection delays, and recomputing C08 (§1(b)).

## 3. Reference implementation

**Latent representation.** ε_n = x_n + b·x_{n−1}, where x is AR(1) with coefficient φ and
stationary variance v_x = s²/(1 + b² + 2bφ). Matching ρ₁ = Fφ gives

  φ(1 − F)·b² + (1 + φ² − 2Fφ²)·b + φ(1 − F) = 0,

whose roots multiply to 1; take |b| < 1. Real roots exist exactly when the spectrum is
nonnegative at ω = π. Lags k ≥ 2 then follow ρ_k = φρ_{k−1} automatically. At the candidate
points b = 0.146–0.231. The ρ_k identity has been checked algebraically to 10⁻¹² for k ≤ 7.

**Grid filter on (x_n, x_{n−1}).** Let β(i) = Σ_j α_n(i, j). Then
α_{n+1}(i′, i) = T(i → i′) · β(i) · e(y_{n+1} | g_{i′} + b·g_i), with
e(1 | ε) = ½(1 − C̄ sin ε) at mid-fringe. Both steps are O(M²) per shot, the same order as
`sid_lib.hmm_rate`'s AR(1) step, and memory is M². The transition T uses `make_hmm`'s
row-normalised Gaussian kernel on the x grid. The start is the stationary joint prior, so no
burn-in is discarded. The estimate is R̂ = mean over n of [log p(y_n | y_{<n}) − log ½].

**Simulation, independent of that algebra.** Sample the OU frequency x(t) exactly, together
with its window integral: the pair (x(t + Δ), ∫x) given x(t) is jointly Gaussian in closed form.
Then ε_n = g∫x over [t_n, t_n + τ], and x evolves freely through the dead time. The simulator
never uses (φ, b), so an error in the ARMA mapping cannot cancel between simulator and filter.

**Code [choice]:**
- a pure library `analysis/lib/sid_arma.py` with no I/O;
- a driver `analysis/runs/sid_run13.py` with a required `--phase {pilot,evaluation}` and no
  default;
- provenance captured at start and stored in the artifact via `sid_repro.run_metadata`;
- refusal to run from a dirty tree, as `sid_run11.py` and `sid_run12.py` do;
- writes through `sid_repro.reproduction_path`.

## 4. Checks that must pass before evaluation (each able to fail)

1. **Nesting.** With F = 1, set b = 0. Feed identical records, from `sid_lib.simulate` with one
   seed, to `hmm_rate`'s filter and to the ARMA filter. The log-likelihood increments must agree
   to 10⁻¹² relative.
2. **Simulator.** At every evaluation point, the sample autocorrelation of the simulated ε at
   k = 1…5 matches C07's F(u)φ^k within its Monte-Carlo band, and the sample variance matches s².
3. **Mapping.** |b| < 1, and the ρ_k identity holds as an assertion inside the library.
4. **Grid convergence [choice].** On identical records, M ∈ {121, 241} and L ∈ {5, 7} must change
   R̂ by less than 0.1 % of K1. The precedent is note 02 Check 3a: under 0.01 % for AR(1) at
   M ≥ 41, L ≥ 4.
5. **Comparator guard.** K3 = K1·(K3/K1) as tabulated in §5, and K3 = K2 at F = 1. Both are
   deterministic.

## 5. Candidate points [choice]

These are design quantities only, from committed formulas.
- **Boundary points** use C08's physical calibration: T₂ = 10 t_dead, gσ_xT₂ = 0.5, decay
  applied, at the stored threshold τ_c and the archived map's mid-fringe winner τ.
- **Stress points** set per-shot (C̄, s) directly, with dead time 0.05 τ_c. They are validation
  points, not physical operating points, and stay at parity contrast C̄ = 0.4.

| Point | Role | C̄ | s | u | c/τ_c | φ | F | b | K1 (nats/shot) | K2/K1 | K3/K1 | N for 1 %, crude |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N0 | nesting check (C04 case) | 0.400 | 0.500 | 0 | 0.050 | 0.9512 | 1 | 0 | 3.06 × 10⁻³ | 1.0066 | 1.0066 | 5 × 10⁶ |
| E1 | C08 boundary, C₀ = 0.4 | 0.240 | 0.255 | 0.0242 | 0.0289 | 0.9715 | 1.0081 | 0.2012 | 9.39 × 10⁻⁵ | 1.0006 | 0.9853 | 2 × 10⁸ |
| E2 | C08 boundary, C₀ = 0.5 | 0.300 | 0.254 | 0.0366 | 0.0437 | 0.9572 | 1.0123 | 0.2011 | 1.49 × 10⁻⁴ | 1.0006 | 0.9775 | 1 × 10⁸ |
| E3 | stress | 0.400 | 0.500 | 0.10 | 0.15 | 0.8607 | 1.0345 | 0.1456 | 1.28 × 10⁻³ | 1.0061 | 0.9446 | 1 × 10⁷ |
| E4 | stress | 0.400 | 0.500 | 0.30 | 0.35 | 0.7047 | 1.1107 | 0.2068 | 5.59 × 10⁻⁴ | 1.0039 | 0.8186 | 3 × 10⁷ |
| E5 | stress, strongest fold contrast | 0.400 | 1.000 | 1.00 | 1.05 | 0.3499 | 1.4762 | 0.2307 | 5.58 × 10⁻⁴ | 1.0084 | 0.4660 | 3 × 10⁷ |
| E6 (optional) | K2 outside its regime | 0.400 | 1.000 | 0.30 | 0.35 | 0.7047 | 1.1107 | 0.2068 | 2.16 × 10⁻³ | 1.0563 | 0.8654 | 7 × 10⁶ |

"N for 1 %" scales note 02's figure (standard error about 7 % at N = 10⁵ with rate 3.05 × 10⁻³)
by SE_rel ∝ (rate·N)^{−1/2}. It is crude: note 02 itself estimated 10⁷ for its own point, twice
this scaling. The pilot replaces it (§6).

**What the points can decide.** The boundary points test the regime that matters, but K3
differs from K1 there by only 1.5–2.3 %. At a 5 % tolerance they cannot distinguish the fold
forms; resolving that gap needs about 0.5 % standard error, of order 10⁸–10⁹ shots each. The
stress points discriminate cheaply: K3 is 5.5 %, 18 % and 53 % low at E3, E4 and E5.

Proposal: evaluate E3–E5 at the full rule. Evaluate E1–E2 at the same rule only if the pilot's
cost puts their N inside the budget (§6). Otherwise report them as not attempted at δ, and do
not run them at reduced precision.

## 6. Pilot: cost and variance only [choice]

- **Points:** P1 = (0.4, 0.5, u = 0.2, c/τ_c = 0.25) and P2 = (0.27, 0.255, u = 0.03,
  c/τ_c = 0.036). Neither belongs to the evaluation set.
- **Seeds:** pilot seeds 13000–13015, disjoint from every evaluation seed, and excluded from
  evaluation the way C excluded its design seeds.
- **Recorded:** seconds per shot for each filter at M = 121 and 241, per-shot variance of the
  log-likelihood increment, and its integrated autocorrelation from batch means. The pilot phase
  does not store or print R̂ or any comparator ratio.
- **Shot rule for evaluation (blind):**
  N = ⌈(z₀.₉₇₅ · σ_eff / (κ·δ·K1))²⌉, where σ_eff² is the per-shot variance times the
  integrated autocorrelation, κ = ¼ and K1 is the deterministic comparator. No measured ARMA
  mean enters N.
- **Budget [choice]:** a per-point wall-clock cap B. A point whose N exceeds B is reported as
  not attempted at δ.
- **Cost baseline:** note 01 records the AR(1) grid HMM as "cheap (10⁵ shots/s)". That figure
  has not been re-measured for the current code; the pilot measures it.

## 7. Evaluation and acceptance rule [choice]

**Replication.** R = 16 independent seeds per point (evaluation seeds 13100 + 20·(point
index) + r), with N/R shots each. R̂ and its 95 % interval use a t-interval across seeds, so
the evaluation does not rely on modelling autocorrelation. Because each Kj is deterministic,
Q_j = Kj/R̂ has the interval [Kj/R_hi, Kj/R_lo].

**Three-way verdict for each comparator at each point, tolerance δ (proposal δ = 0.05):**
- **VALIDATED at δ** if the interval for Q_j lies inside [1 − δ, 1 + δ];
- **FAILED at δ** if it lies entirely outside;
- **UNRESOLVED** otherwise. An unresolved result is reported without a direction.

**Stated in advance, and able to fail.** If K1 is accurate, K3 must fail at E4 and E5
(K3/K1 = 0.82 and 0.47). K1 and K3 cannot both validate at E5, because their ratio is 0.47.
K2's 5.6 % excess at E6 lies outside δ = 5 %, so K1 and K2 cannot both validate there either.

**What each outcome licenses:**

| Outcome | Consequence |
|---|---|
| K1 validated at every evaluated point | Item 1 may say that the exact-r_k comparator agrees with the exact finite-window binary likelihood within δ at the tested points. F closes for K1. |
| K2 validated at E3–E5 | The lag-1-matched fit is supported at the tested s ≤ 0.5 and u ≤ 1 points, not beyond. |
| K3 failed at E4 or E5 | Confirms §1: the archived map form is not ARMA-consistent. It says nothing against the comparator class. |
| K1 failed anywhere | The comparator is not validated at that point. Report the numbers, keep item 1 at the frozen caveat, and review claims that depend on it. |
| Unresolved | Reported as unresolved; no wording is strengthened. |

## 8. Freeze and hygiene

On acceptance, lock the following in `analysis/protocol_F.json` [choice of name], shaped like
`analysis/sensitivity_protocol_C.json` (record, status, frozen_before, rules, digest):

- evaluation points,
- δ and κ,
- R and the seed blocks,
- grid-convergence criterion,
- budget B,
- the shot rule,
- the three-way verdict,
- the comparator definitions.

Evaluation refuses to run unless the protocol digest matches. The order is:
1. accept this note and commit the §1(d) diagnostics;
2. freeze the protocol;
3. implement `sid_arma.py`, with the §4 checks as tests;
4. run the pilot from a clean tree;
5. derive N;
6. run the evaluation;
7. apply the verdicts, and label any later analysis as post-unblinding.

Record the stack [choice: the pinned `environment.yml` stack or the archive stack] in the
artifact.

## 9. Decisions for review

1. Handling of the §1 finding: erratum scope, whether C08 is superseded, the guard test, and
   committing the diagnostics.
2. Comparators: K1, K2 and K3 as defined; whether to add the point-sampled series (A = 1)
   explicitly as a fourth comparator.
3. Points: E3–E5 required, E1–E2 conditional on budget, E6 optional; pilot points P1–P2.
4. Tolerance δ (proposed 5 %), κ (¼), replicates R (16), budget B.
5. Grid-convergence criterion (0.1 % of K1).
6. Seed blocks: 13000–13015 for the pilot, 13100 onwards for evaluation.
7. File names: `sid_arma.py`, `sid_run13.py`, `protocol_F.json`, and the output artifact name.
8. Execution stack.

## 10. What this draft does not do

It computes no ARMA likelihood, runs no pilot and changes no claim status, card, ledger, note
or output. The §1 and §5 numbers come from two deterministic diagnostic scripts that load
run3's formulas and run4's kernels. They run in seconds and are not yet in the repository.
Drafting and analysis used model assistance.
