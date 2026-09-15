# Signals in Darkness — note 28 (15 Sept 2026, DRAFT): roadmap F protocol for review

**Status:** DRAFT FOR REVIEW, Gate 0 of the approved sequence. The package is:
- this note;
- [analysis/protocol_F.json](../analysis/protocol_F.json), with `status` DRAFT and `digest` null;
- its builder, [tools/build_protocol_F.py](../tools/build_protocol_F.py);
- [tests/test_protocol_F_draft.py](../tests/test_protocol_F_draft.py).

The note replaces [note 26](2026-09-15-note-26-F-plan-draft.md) as the proposed plan. Note 26
stays in the record as the rejected draft. The note adopts every decision in
[note 27 §3](2026-09-15-note-27-C08-fold-erratum-and-F-review.md#3-preferred-decisions-for-the-revised-plan)
and resolves each finding in §2 of that note.

**What has not happened:** no ARMA likelihood was evaluated, no latent record simulated, no
pilot run and no package installed. Freezing, implementation, the numerical checks with
pilots, and evaluation each keep their own approval gate. A driver must refuse to run
anything from this file while its status starts with DRAFT.

**Evidence snapshot:** `590c6af`, clean tree. Every number in the protocol comes from the
builder, not from transcription: `python tools/build_protocol_F.py --check` confirms the
committed draft, and `--markdown` prints the tables below.

## 1. How note 27's findings are resolved

| Note 27 finding | Resolution in this draft |
|---|---|
| 1. E6 does not force a failure | E6 is deferred. A pair of comparators is *forced incompatible* only when their ratio lies outside [(1−δ)/(1+δ), (1+δ)/(1−δ)] = [0.904762, 1.105263]. The builder marks those pairs at each point (§4), and a test checks the marking. E3 forces nothing; E4 and E5 force K3 and K4 against K1 and K2. |
| 2. The shot rule is not executable | Each selected point gets its own variance pilot on disjoint seeds, with fixed length and batching, a conservative variance bound, a stability rule, the t(15) quantile, whole replicates of equal length, and no top-ups (§6). |
| 3. Boundary points were approximations | E1/E2 are the exact archived grid values, frozen with their indices (§4). The rounded inputs were not harmless: E2's K1 moves from 1.492 × 10⁻⁴ to 1.447 × 10⁻⁴ (−3.0 %). |
| 4. The closure rule was too loose | K1 is the primary comparator. F closes only when E3, E4 and E5 are all attempted and resolved. Statements are licensed only at validated tuples, and E1/E2 carry C08's boundary statement (§8). |
| 5. Reference and convergence contracts were missing | The filter starts from the exact stationary distribution of the discretised chain and discards a burn-in, and the AR(1) nesting reference uses the same two conventions. A tie to the committed `hmm_rate` is required. Grid convergence, finite history, series truncation, and absolute-plus-relative nesting tolerances are all fixed (§§3, 5). |
| 6. Interval and scope edge cases | R_lo ≤ 0 gives UNRESOLVED with no division. A failed check blocks every verdict at that point. Intervals are pointwise. The tautological K3 guard is dropped; the lag-one contract tests from note 27 remain (§7). |

## 2. Estimand and comparators

The target is the per-shot relative-entropy rate R of the θ = π/2 binary record against the
i.i.d. null p₀ = ½. The latent phase is the finite-window integrated stationary OU phase.
All four comparators are deterministic:

- **K1 (primary):** the six-term sinh-series spectral rate with exact
  r_k = C̄²e^{−s²}sinh(s²F(u)φ^k), on 1024 midpoint frequencies (run4's kernel).
- **K2:** the lag-1-matched geometric fit.
- **K3:** the archived C08 map form, a diagnostic control.
- **K4:** the point-sampled series with A = 1, also a diagnostic control and not a
  finite-window truth model.

Definitions and sources are in the protocol. The Gate-2 library must reproduce the design
values to relative 10⁻¹² on the execution stack.

## 3. Reference filter contract

**Latent model.** ε_n = x_n + b·x_{n−1}, where x is AR(1) with coefficient φ = e^{−c/τ_c}.
The MA coefficient b is the root with |b| < 1 of

  φ(1 − F)·b² + (1 + φ² − 2Fφ²)·b + φ(1 − F) = 0.

The stationary variance of x is v_x = s²/(1 + b² + 2bφ), and the innovation variance is
q = v_x(1 − φ²).

**Discretisation.**
- **Grid:** x takes M equally spaced values on ±L√v_x.
- **Transition:** the Gaussian kernel on that grid, with each row normalised.
- **Emission:** E_y[i′, i] = (1 + (2y − 1)·C̄·cos(θ + g_{i′} + b·g_i))/2.

**Initialisation.** π is the exact stationary distribution of the *discretised* transition:
the eigenvector of Tᵀ for the eigenvalue nearest 1. The residual Σ|πT − π| must be at most
10⁻¹², and π at least −10⁻¹⁵. The first step is α̃₁(i, j) = π(j)·T[j, i]·E_{y₁}(i, j). After
that, β(i) = Σ_j α_{n−1}(i, j) and α̃_n(i′, i) = T[i, i′]·β(i)·E_{y_n}(i′, i). The log increment
is ℓ_n = log Z_n − log ½, where Z_n is the normalising sum. Both steps are O(M²) per shot.

**Burn-in and estimator.** W = max(1000, ⌈100·τ_c/c⌉) shots. The filter runs through them,
every estimator excludes them, and R_seed is the mean of ℓ_n over the n shots that follow.

**AR(1) nesting reference, as you specified.** It uses the same grid (with b = 0), T, π,
emission, W and estimator: α̃₁(i) = π(i)·E_{y₁}(i). The committed code is tied in separately.
That same AR(1) recursion, started instead from `make_hmm`'s Gaussian weights with one
propagation before the first emission and W = 0, must reproduce `sid_lib.hmm_rate` to
relative 10⁻¹² on hmm_rate's own record.

**How much initialisation matters on these grids.** Deterministic design values: the total
variation between π and the Gaussian weights is 2–4 × 10⁻⁷ at M = 121, L = 5, and at most
2 × 10⁻¹² on the evaluation grid (M = 241, L = 7). The convention is fixed regardless. The
innovation standard deviation spans at least 2.84 grid spacings (E1 at M = 121, L = 5) and at
least 4.06 on the evaluation grid.

## 4. Simulator and points

**Simulator.** The frozen convention works in units of τ_c:
- **Frequency:** standardised, starting from z₀ ~ N(0, 1).
- **Window:** over u, draw the pair (z, ∫z) exactly from its Gaussian law, using Var ξ₁ = 1 − e^{−2u},
  Var ξ₂ = 2[u − 2(1 − e^{−u}) + (1 − e^{−2u})/2] and Cov = (1 − e^{−u})². Then
  ε = s·I/√(2(u − 1 + e^{−u})).
- **Dead time:** over d = c/τ_c − u, z ← e^{−d}·z + √(1 − e^{−2d})·ξ₃.
- **Outcome:** y = 1 if U < (1 + C̄ cos(θ + ε))/2.
- **Generator:** `default_rng(seed)`. Draws come in blocks of 2²⁰ shots, three normals per shot and
  then the uniforms.

The simulator never uses φ or b, so an error in the ARMA mapping cannot cancel between simulator
and filter.

**Points.** E3–E5 are mandatory, E1/E2 form a conditional pair, and E6 is deferred.

| Point | Status | C | s | u | c/τ_c | φ | F(u) | b | W | K1 (nats/shot) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E1 | conditional | 0.239907 | 0.255070 | 0.024188 | 0.028910 | 0.971504 | 1.008128 | 0.201185 | 3460 | 9.429134e-05 |
| E2 | conditional | 0.297166 | 0.254546 | 0.036591 | 0.043734 | 0.957208 | 1.012347 | 0.201169 | 2287 | 1.446672e-04 |
| E3 | mandatory | 0.400000 | 0.500000 | 0.100000 | 0.150000 | 0.860708 | 1.034471 | 0.145589 | 1000 | 1.277055e-03 |
| E4 | mandatory | 0.400000 | 0.500000 | 0.300000 | 0.350000 | 0.704688 | 1.110742 | 0.206841 | 1000 | 5.589440e-04 |
| E5 | mandatory | 0.400000 | 1.000000 | 1.000000 | 1.050000 | 0.349938 | 1.476246 | 0.230679 | 1000 | 5.574999e-04 |
| N0 | nesting | 0.400000 | 0.500000 | 0.000000 | 0.050000 | 0.951229 | 1.000000 | 0.000000 | 2000 | 3.054880e-03 |

E1 is C₀ column 33, τ_c row 74 and τ index 118 of the archived map. E2 is column 42, row 70 and
τ index 118. Full-precision values are in the protocol. Physical calibration: T₂/t_dead = 10,
gσ_xT₂ = 0.5, with τ the archived map form's winner at the stored threshold.

| Point | K2/K1 | K3/K1 | K4/K1 | K3/K4 | Forced-incompatible pairs at δ = 0.05 |
|---|---:|---:|---:|---:|---|
| E1 | 1.000605 | 0.985336 | 0.984729 | 1.000617 | none |
| E2 | 1.000578 | 0.977518 | 0.976937 | 1.000595 | none |
| E3 | 1.006110 | 0.944588 | 0.938260 | 1.006745 | none |
| E4 | 1.003919 | 0.818572 | 0.814048 | 1.005559 | K3/K1, K3/K2, K4/K1, K4/K2 |
| E5 | 1.008369 | 0.465969 | 0.442697 | 1.052569 | K3/K1, K3/K2, K4/K1, K4/K2 |
| N0 | 1.006591 | 1.006591 | 1.000000 | 1.006591 | none |

**What the controls can and cannot do.** If K1 validates at E4 or E5, K3 and K4 cannot also
validate there. E3, E1 and E2 force nothing: they test the comparator, not the fold. K3
failing is a rate comparison consistent with note 27. The covariance defect was established
algebraically and does not depend on it.

## 5. Numerical checks: Gate 3, before any pilot at a point

| Check | Records and seeds | Pass condition | Failure |
|---|---|---|---|
| NC1 nesting | N0; seed 15900; `sid_lib.simulate`, 200 000 shots; grids M121/L5 and M241/L7 | per increment \|Δℓ\| ≤ 10⁻¹² + 10⁻⁹\|ℓ\|; \|ΣΔℓ\| ≤ 10⁻⁹ Σ\|ℓ\|; `hmm_rate` tie to relative 10⁻¹² | blocks every point |
| NC2 simulator | check seeds r = 8…15; 250 000 shots each | variance of ε against s², and lag-k autocorrelation against F(u)φ^k for k = 1…5, within 5 across-seed standard errors | point blocked |
| NC3 series | deterministic | K1 and K4 change by at most 10⁻⁶ from (6 terms, 1024) to (12, 4096); design values ≤ 10⁻¹³ | point blocked |
| NC4 stationarity | every grid used | residual ≤ 10⁻¹², min π ≥ −10⁻¹⁵ | point blocked |
| NC5 grid | check seeds r = 0…7; records of 2W + 50 000 shots; window n = W+1…W+50 000 | for M121/L5, M121/L7 and M241/L5 against M241/L7: \|paired mean\| + t(0.975, 7)·SE ≤ 0.001·K1 | point blocked |
| NC6 finite history | NC5 records on M241/L7 | window W+1… minus window 2W+1…: \|paired mean\| + t(0.975, 7)·SE ≤ 0.001·K1 | point blocked |

The grid, burn-in, record lengths and seeds change only through a superseding protocol
version. Nothing escalates automatically.

## 6. Pilot and shot rule

**Pilot per point.**
- **Seeds and length:** seeds 13000 + 20p + r (r = 0…15), each W + 125 000 shots on the evaluation grid.
- **Stored:** per-seed wall time, the across-seed variance S² of the per-seed means, and pooled
  batch-means variances v̄₁₀ and v̄₂₀ (B = 10 and 20 equal batches).
- **Cost:** t_step, in seconds per shot including burn-in.
- **Not stored:** the per-seed means themselves, their average, and any comparator ratio.

**Variance bound.**
- U = max(U_seed, U_bm10, U_bm20).
- U_seed = 15·S²/χ²(0.05, 15), with χ²(0.05, 15) = 7.260944.
- U_bmB = v̄_B·df_B/χ²(0.05, df_B), with df = 144 and 304 (quantiles 117.2683 and 264.6102).
- **Stability:** if the largest of S², v̄₁₀ and v̄₂₀ exceeds four times the smallest, the point is
  PILOT_UNSTABLE and is not evaluated.

**Shot rule.** n_e = max(n_p, 1000·⌈t(0.975, 15)²·U·n_p / (16·(κ·δ·K1)²) / 1000⌉), with
t(0.975, 15) = 2.131450, κ = ¼ and δ = 0.05.
- **Total:** 16·n_e shots plus 16·W burn-in shots.
- **Blindness:** only the deterministic K1 and the pilot's variance bound enter n_e.
- **No top-ups:** no extension, replacement seed or early stop based on measured means.
- **What decides:** the realised interval decides the verdict, not the planned N.
- **Constants:** every t, z and χ² quantile is read from the protocol and never recomputed on the
  execution stack. SciPy 1.10 and 1.17 already differ by 2.5 × 10⁻¹⁰ relative in t(0.975, 7),
  which surfaced when the draft's tests ran on both stacks.

## 7. Evaluation and verdicts

**Evaluation.** Seeds 14000 + 20p + r (r = 0…15). The interval is R̄ ± t(0.975, 15)·s_R/4,
pointwise at 95 %.

**Verdicts,** for each comparator K at each point:

| Condition, checked in order | Verdict |
|---|---|
| The point failed a check, was PILOT_UNSTABLE, not attempted or INCOMPLETE | NO_VERDICT |
| R_lo ≤ 0 | UNRESOLVED (no division) |
| Q = [K/R_hi, K/R_lo] lies inside [1 − δ, 1 + δ] | VALIDATED |
| Q is disjoint from that band | FAILED |
| Otherwise | UNRESOLVED, without a direction |

No simultaneous coverage is claimed across the up to 20 verdicts.

## 8. Closure and what outcomes license

- **Roadmap F:** closes VALIDATED iff K1 is VALIDATED at E3, E4 and E5. It closes FAILED iff all
  three receive VALIDATED or FAILED for K1 and at least one is FAILED. Otherwise F remains OPEN.
- **K1 statements:** only at the validated tuples (C̄, s, u, c/τ_c), within ±δ, pointwise. If E3–E5
  all validate, the statement covers (0.4, 0.5, 0.10, 0.15), (0.4, 0.5, 0.30, 0.35) and
  (0.4, 1.0, 1.00, 1.05) and nothing beyond them.
- **K2:** a statement about the lag-1-matched fit, only at the tuples where K2 is VALIDATED.
- **C08's boundary:** a finite-window binary-likelihood statement there needs E1 and E2 both
  evaluated, with the comparator VALIDATED at both. Otherwise that validation remains open.
- **Wording while F is open or failed:** note 27's replacement caveat, quoted verbatim in the
  protocol, never the frozen caveat.
- **Other analyses:** anything this protocol does not specify is labelled post-unblinding and
  cannot change a verdict.

## 9. Budget and scheduling

- **Limits:** one numerical thread and 8 aggregate hours.
- **Gate 3:** at most 30 minutes, run in the order NC1/NC3, then E3, E4, E5, then E1 and E2 together.
  Before each point's checks and pilot, its cost is predicted from the t_step measured so far,
  after running the first point to measure it. If the prediction exceeds the remaining Gate-3
  budget, the point is NOT_ATTEMPTED.
- **Evaluation:** in the order E3, E4, E5, then E1 + E2.
  - The predicted cost is 1.10 × 16(W + n_e)·t_step.
  - A mandatory point runs only if its prediction is at most 2 h and fits the remaining aggregate budget.
  - E1 and E2 run only together, and only if each is predicted at 2 h or less and their sum fits.
  - A run exceeding 1.25 × its prediction is stopped and recorded INCOMPLETE, with no partial verdict.
- **Shot counts, no time estimate yet:** each pilot is 16(W + 125 000) ≈ 2.0–2.06 × 10⁶
  evaluation-grid shots. NC5/NC6 add 8 records of 2W + 50 000 shots on the evaluation grid,
  plus W + 50 000 on each of three check grids. Seconds per shot are unknown until the pilot.

## 10. Execution stack: definition and installation commands for review

- **Machine:** Apple M1 Pro, arm64.
- **Existing conda:** 22.9.0, but an **osx-64** build. Its base Python 3.9.7 runs under Rosetta and
  it uses the defaults channel, so a plain `conda env create` would produce an x86_64 stack. That
  is not the approved stack, and the protocol forbids it.
- **Other tools:** no mamba or micromamba; Homebrew has only Python 3.13.
- **Definition:** the committed `environment.yml`, with conda-forge, Python 3.12, NumPy 2.4.4,
  SciPy 1.17.1, Matplotlib 3.10.8, pytest 9.0.3, PyYAML 6.0.3 and pip `cffconvert==2.0.0`.
- **Name:** the environment would be `sid-f`, so it cannot collide with README users' `sid`.

Proposed commands, **not run**:

```sh
CONDA=/Users/uwarring/opt/anaconda3/bin/conda
ENV=/Users/uwarring/opt/anaconda3/envs/sid-f

# 0. Solve only; installs nothing (downloads conda-forge osx-arm64 repodata)
CONDA_SUBDIR=osx-arm64 $CONDA create --dry-run -n sid-f --override-channels -c conda-forge \
    python=3.12 numpy=2.4.4 scipy=1.17.1 matplotlib=3.10.8 pytest=9.0.3 pyyaml=6.0.3 pip

# 1. Create from the committed definition, native arm64 (pip installs cffconvert from PyPI)
CONDA_SUBDIR=osx-arm64 $CONDA env create -f environment.yml -n sid-f

# 2. Keep later installs into this environment on osx-arm64
printf 'subdir: osx-arm64\n' > "$ENV/.condarc"

# 3. Verify the architecture and record the resolved stack
file "$ENV/bin/python3.12"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 "$ENV/bin/python" -c "import sys, platform, numpy, scipy; \
    print(sys.version); print(platform.machine()); print(numpy.__version__, scipy.__version__); \
    numpy.show_config()"
$CONDA list -n sid-f '^(python|libblas|libcblas|liblapack|libopenblas)$'

# 4. Lock the exact packages, committed before Gate 3
$CONDA list -n sid-f --explicit --md5 > analysis/stack_F_osx-arm64.lock
```

**What gets recorded.** `sid_repro` records numpy's *build* BLAS name, which does not identify
the runtime implementation. The lock's `libblas` build string does, so the F driver will also
record that, together with the resolved Python patch version, `platform.machine()` and the
thread variables.

**Risks before running.** conda 22.9.0 is old, and its classic solver may be slow or fail on
current conda-forge metadata. That is why step 0 is a dry run. The fallback would be a native
Miniforge3 installation, which is a separate install needing its own approval.

## 11. Choices still open for review

1. **BLAS variant:** conda-forge's default `libblas`, or `libblas=*=*openblas` pinned so that runs
   cannot drift to another implementation.
2. **Burn-in:** W = max(1000, ⌈100·τ_c/c⌉).
3. **Pilot:** n_p = 125 000 per seed; stability factor 4.
4. **Checks:** NC5/NC6 use 8 seeds × 50 000-shot windows; the NC2 threshold is 5 standard errors.
5. **Hard stop:** 1.25 × the prediction. Prediction margin: 1.10.
6. **Closure:** K1 as the sole comparator deciding F. K2 is licensed separately and K3/K4 are diagnostics.
7. **Labbook:** whether a labbook pass should accompany this draft, or wait for the freeze at
   Gate 1. My proposal is the freeze.

## 12. Limits

The design evidence was computed on the drafting stack (Python 3.9.7, SciPy 1.10.0), and
`--check` also matches under Python 3.13.7 / SciPy 1.17.1. None of it validates a comparator.
The test module checks only the protocol document: reproducibility from the builder, that a
draft cannot authorise a run, seed disjointness, exact archive-grid inputs, the MA mapping,
band arithmetic, the constants, and the explicit mandatory, closure and edge-case rules.
Drafting and analysis used model assistance.
