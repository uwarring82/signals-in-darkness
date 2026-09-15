# Signals in Darkness — note 28 (15 Sept 2026, DRAFT r2): roadmap F protocol for review

**Status:** DRAFT FOR REVIEW, revision 2, Gate 0 of the approved sequence. Revision 1 is
commit `0a3584b`. The package is:
- this note;
- [analysis/protocol_F.json](../analysis/protocol_F.json), with `status` DRAFT, `draft_revision` 2 and
  `digest` null;
- [tools/build_protocol_F.py](../tools/build_protocol_F.py) and
  [tests/test_protocol_F_draft.py](../tests/test_protocol_F_draft.py);
- the execution-stack definition in [analysis/stack_F/](../analysis/stack_F/conda-osx-arm64.txt), with
  the reviewed dry-run solve;
- [tools/lock_stack_F.py](../tools/lock_stack_F.py) and [tests/test_lock_stack_F.py](../tests/test_lock_stack_F.py).

The note replaces [note 26](2026-09-15-note-26-F-plan-draft.md) as the proposed plan. It adopts
[note 27 §3](2026-09-15-note-27-C08-fold-erratum-and-F-review.md#3-preferred-decisions-for-the-revised-plan),
and revision 2 carries out the Gate-0 review of revision 1.

**What has and has not happened:**
- **Ran:** the approved conda dry-run solve. It downloaded channel metadata into conda's cache and
  installed nothing.
- **Not run:** no ARMA likelihood evaluation, no latent-record simulation, no pilot and no
  package installation.
- **Still gated:** freezing, implementation, the numerical checks with pilots, installation and
  evaluation each keep their own approval. A driver must refuse to run anything from the
  protocol while its status starts with DRAFT.

**Evidence snapshot:** `0a3584b`. Every protocol number comes from the builder.
`python tools/build_protocol_F.py --check` and `--markdown` are both read-only.

## 0. Revision 2: the Gate-0 review

| Review item | Change |
|---|---|
| NC6 compared different observations | NC5 and NC6 now use named filter passes over records of 2W + 50 000 observations. Every pass is estimated on the **same final 50 000 observations**. NC6 compares the evaluation-grid pass given W preceding observations with the pass given 2W, so only the history length differs. The extra pass is costed (§5, §9). A test evaluates the pass offsets for W = 1000, 2287 and 3460, and shows that revision 1's windows differ in 2W observations. |
| The runtime stop could exceed the hard caps | Every evaluation run stops at start + min(1.25 × prediction, 7200 s, the aggregate seconds remaining at its start). Gate 3 has an enforced 1800 s deadline that also covers NC1, NC3 and the first point's measurement. A test checks that a 7200 s prediction now stops at 7200 s, where revision 1 allowed 9000 s (§9). |
| The builder could overwrite a frozen protocol | Writing refuses any destination that is frozen (status not DRAFT, *or* a non-null digest) or unreadable, and new drafts after a freeze need `--out`. `--check` and `--markdown` are read-only. Tests on temporary fixtures confirm that a frozen or unreadable file is left byte-identical, and that only drafts are replaced. |
| Solve and installation used different channel policies | One F-specific definition serves both steps, [conda-osx-arm64.txt](../analysis/stack_F/conda-osx-arm64.txt): `environment.yml`'s pins plus `libblas=*=*openblas`. Both commands use `conda create --override-channels -c conda-forge --no-default-packages --file` on it and differ only in `--dry-run --json` versus `-y`, which a test enforces. pip packages have their own definition and a hash-pinned lock (§10). |
| Wording after a FAILED closure | Three caveats now exist: while open, after FAILED and after VALIDATED. Only the open wording ends "F remains open", and a test checks this (§8). |

The §11 decisions are recorded in [§11](#11-review-decisions-and-the-one-remaining-choice) and in the
protocol's `adopted_choices`.

## 1. How note 27's findings are resolved

| Note 27 finding | Resolution |
|---|---|
| 1. E6 does not force a failure | E6 is deferred. A pair of comparators is *forced incompatible* only when their ratio lies outside [0.904762, 1.105263]. The builder marks those pairs and a test checks the marking (§4). |
| 2. The shot rule is not executable | Each selected point gets its own variance pilot on disjoint seeds, with fixed length and batching, an approximate conservative variance bound, a stability rule, the t(15) quantile, whole replicates of equal length, and no top-ups (§6). |
| 3. Boundary points were approximations | E1/E2 are the exact archived grid values, frozen with their indices. E2's K1 moves −3.0 % from the rounded draft (§4). |
| 4. The closure rule was too loose | K1 alone decides F, and only once E3–E5 are all resolved. C08's boundary is reported separately (§8). |
| 5. Reference and convergence contracts were missing | Stationary initialisation and burn-in, shared with the AR(1) nesting reference, plus a tie to `hmm_rate`. NC1–NC6 fix grid convergence, finite history, series truncation and nesting tolerances (§§3, 5). |
| 6. Interval and scope edge cases | R_lo ≤ 0 gives UNRESOLVED. A failed check blocks every verdict at that point. Intervals are pointwise. The tautological guard is dropped (§7). |

## 2. Estimand and comparators

The target is the per-shot relative-entropy rate R of the θ = π/2 binary record against the
i.i.d. null p₀ = ½. The latent phase is the finite-window integrated stationary OU phase.
All four comparators are deterministic:

- **K1 (primary):** the six-term sinh-series spectral rate with exact
  r_k = C̄²e^{−s²}sinh(s²F(u)φ^k), on 1024 midpoint frequencies.
- **K2:** the lag-1-matched geometric fit.
- **K3:** the archived C08 map form, a diagnostic control.
- **K4:** the point-sampled series, also a diagnostic control.

The Gate-2 library must reproduce the design values to relative 10⁻¹².

## 3. Reference filter contract

**Latent model.** ε_n = x_n + b·x_{n−1}, where x is AR(1) with coefficient φ = e^{−c/τ_c}. The MA
coefficient b is the root with |b| < 1 of

  φ(1 − F)·b² + (1 + φ² − 2Fφ²)·b + φ(1 − F) = 0.

The stationary variance of x is v_x = s²/(1 + b² + 2bφ), and the innovation variance is
q = v_x(1 − φ²).

**Discretisation.**
- **Grid:** x takes M equally spaced values on ±L√v_x.
- **Transition:** the Gaussian kernel on that grid, with each row normalised.
- **Emission:** E_y[i′, i] = (1 + (2y − 1)·C̄·cos(θ + g_{i′} + b·g_i))/2.

**Initialisation and recursion.** Each filter pass starts at its first observation m from π,
the exact stationary distribution of the *discretised* transition, with
α̃_m(i, j) = π(j)·T[j, i]·E_{y_m}(i, j). The residual Σ|πT − π| must be at most 10⁻¹², and π at
least −10⁻¹⁵. After that, β(i) = Σ_j α_{n−1}(i, j) and α̃_n(i′, i) = T[i, i′]·β(i)·E_{y_n}(i′, i),
with log increment ℓ_n = log Z_n − log ½. Both steps are O(M²) per shot.

**Burn-in and estimator.** W = max(1000, ⌈100·τ_c/c⌉). Pilot and evaluation passes start at
observation 1, and R_seed is the mean of ℓ_n over n = W+1 … W+n.

**AR(1) nesting reference.** It uses the same grid (with b = 0), T, π, emission, W and
estimator. Separately, started from `make_hmm`'s Gaussian weights with W = 0, it must reproduce
`sid_lib.hmm_rate` to relative 10⁻¹².

**How much initialisation matters on these grids.** The total variation between π and the
Gaussian weights is 2–4 × 10⁻⁷ at M = 121, L = 5, and at most 2 × 10⁻¹² on the evaluation grid.
The innovation standard deviation spans at least 2.84 grid spacings, and at least 4.06 on the
evaluation grid.

## 4. Simulator and points

**Simulator, unchanged from revision 1.**
- **Method:** exact OU in units of τ_c, starting from z₀ ~ N(0, 1).
- **Window and dead time:** the pair (z, ∫z) over the window is drawn from its closed-form
  Gaussian law, and the dead time is evolved exactly.
- **Generator:** `default_rng(seed)`, drawing in blocks of 2²⁰ shots.
- **Independence:** it never uses φ or b.

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
τ index 118.

| Point | K2/K1 | K3/K1 | K4/K1 | K3/K4 | Forced-incompatible pairs at δ = 0.05 |
|---|---:|---:|---:|---:|---|
| E1 | 1.000605 | 0.985336 | 0.984729 | 1.000617 | none |
| E2 | 1.000578 | 0.977518 | 0.976937 | 1.000595 | none |
| E3 | 1.006110 | 0.944588 | 0.938260 | 1.006745 | none |
| E4 | 1.003919 | 0.818572 | 0.814048 | 1.005559 | K3/K1, K3/K2, K4/K1, K4/K2 |
| E5 | 1.008369 | 0.465969 | 0.442697 | 1.052569 | K3/K1, K3/K2, K4/K1, K4/K2 |
| N0 | 1.006591 | 1.006591 | 1.000000 | 1.006591 | none |

## 5. Numerical checks: Gate 3, before any pilot at a point

**The records behind NC5 and NC6.** Check seeds r = 0…7 give eight records of 2W + 50 000
observations each. Every pass starts from π at its first observation, burns in until
observation 2W, and is estimated on the **same final observations 2W+1 … 2W+50 000**.

| Pass | Grid | First observation | Preceding history |
|---|---|---:|---:|
| M241_L7_2W_history | M241/L7 | 1 | 2W |
| M241_L7_W_history | M241/L7 | W+1 | W |
| M241_L5_W_history | M241/L5 | W+1 | W |
| M121_L7_W_history | M121/L7 | W+1 | W |
| M121_L5_W_history | M121/L5 | W+1 | W |

| Check | Records and seeds | Pass condition | Failure |
|---|---|---|---|
| NC1 nesting | N0; seed 15900; `sid_lib.simulate`, 200 000 shots; M121/L5 and M241/L7 | per increment \|Δℓ\| ≤ 10⁻¹² + 10⁻⁹\|ℓ\|; \|ΣΔℓ\| ≤ 10⁻⁹ Σ\|ℓ\|; `hmm_rate` tie to relative 10⁻¹² | blocks every point |
| NC2 simulator | check seeds r = 8…15; 250 000 shots each | variance of ε and lag-1…5 autocorrelation within 5 across-seed standard errors | point blocked |
| NC3 series | deterministic | K1 and K4 change by at most 10⁻⁶ from (6, 1024) to (12, 4096) | point blocked |
| NC4 stationarity | every grid used | residual ≤ 10⁻¹², min π ≥ −10⁻¹⁵ | point blocked |
| NC5 grid | the three check-grid W-history passes, each against M241_L7_W_history | \|paired mean\| + t(0.975, 7)·SE ≤ 0.001·K1 | point blocked |
| NC6 finite history | M241_L7_W_history against M241_L7_2W_history | \|paired mean\| + t(0.975, 7)·SE ≤ 0.001·K1 | point blocked |

**Cost per check seed.**
- **Simulation:** 2W + 50 000 observations.
- **Filter steps on M241/L7:** (2W + 50 000) + (W + 50 000). The second term is the NC6 pass
  revision 1 lacked.
- **Filter steps on each check grid:** W + 50 000.

The grid, burn-in, record lengths and seeds change only through a superseding protocol
version.

## 6. Pilot and shot rule

**Pilot per point.**
- **Seeds and length:** seeds 13000 + 20p + r (r = 0…15), each W + 125 000 shots on the evaluation grid.
- **Stored:** per-seed wall time, the across-seed variance S² of per-seed means, and pooled
  batch-means variances v̄₁₀ and v̄₂₀.
- **Cost:** t_step, in seconds per shot including burn-in.
- **Not stored:** per-seed means, their average, and any ratio.

**Variance bound: approximate, for planning only, not an exact confidence limit.**
- U = max(U_seed, U_bm10, U_bm20).
- U_seed = 15·S²/χ²(0.05, 15).
- U_bmB = v̄_B·df_B/χ²(0.05, df_B), with df = 144 and 304.
- **Approximations:** the χ² factors treat per-seed and batch means as approximately normal, and
  batches as approximately independent.
- **Stability:** if the largest of S², v̄₁₀ and v̄₂₀ exceeds four times the smallest, the point is
  PILOT_UNSTABLE.

**Shot rule.** n_e = max(n_p, 1000·⌈t(0.975, 15)²·U·n_p / (16·(κ·δ·K1)²) / 1000⌉), with
t(0.975, 15) = 2.131450, κ = ¼ and δ = 0.05.
- **Total:** 16·n_e shots plus 16·W burn-in shots.
- **Blindness:** only the deterministic K1 and U enter n_e.
- **No top-ups:** no extension, replacement seed or early stop based on measured means.
- **Constants:** every quantile is read from the protocol and never recomputed. SciPy 1.10 and 1.17
  differ by 2.5 × 10⁻¹⁰ in t(0.975, 7).
- **What decides:** the realised interval decides the verdict, not the planned N.

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

No simultaneous coverage is claimed.

## 8. Closure and wording

- **Roadmap F:** decided by K1 alone. It closes VALIDATED iff K1 is VALIDATED at E3, E4 and E5. It
  closes FAILED iff all three receive VALIDATED or FAILED and at least one is FAILED. Otherwise F
  remains OPEN.
- **Licensed statements:** K1 and K2 statements are licensed only at their own validated tuples.
- **C08's boundary:** reported separately. A statement there needs E1 and E2 both evaluated, with
  the comparator VALIDATED at both, whatever F's closure.

The protocol fixes three caveats. All three open with note 27's statement that C08's archived
implementation divides the first-lag correlation by F(u) and is not the finite-window
comparator.

| F's state | Closing wording |
|---|---|
| OPEN | "Binary-likelihood validation remains confined to C04's tested point-sampled exact-r_k comparator; F remains open." (note 27, verbatim) |
| closed FAILED | "Roadmap F closed FAILED: the exact-r_k comparator (K1) was not validated against the exact finite-window ARMA(1,1) binary likelihood at {failed_tuples}. Binary-likelihood validation of the comparator remains confined to C04's tested point-sampled cases." |
| closed VALIDATED | "Roadmap F closed VALIDATED: the exact-r_k comparator (K1) agrees with the exact finite-window ARMA(1,1) binary likelihood within ±5 % (pointwise 95 % intervals) at {validated_tuples}, and only at those inputs." |

Any analysis the protocol does not specify is post-unblinding and cannot change a verdict.

## 9. Budget, deadlines and stopping

- **Clock:** one numerical thread. The aggregate budget is **28 800 s**, counted as the sum of the
  wall-clock seconds each `sid_run13` phase records in its `res13` artifact. Each run reads the
  remaining budget from those records before it starts.
- **Gate-3 deadline:** **1800 s**, enforced from the start of the Gate-3 run and never later than the
  remaining aggregate budget. It applies to every step, including NC1, NC3 and the first point's
  measurement. A step that reaches it is stopped and recorded INCOMPLETE, and an incomplete NC1
  blocks every point.
- **Gate-3 order:** NC1 and NC3 first, then E3, E4, E5, E1 and E2. A point is NOT_ATTEMPTED if its
  predicted checks and pilot exceed the time left before the deadline, and E1 and E2 are admitted
  together.
- **Evaluation admission:** a mandatory point runs only if its prediction,
  1.10 × 16(W + n_e)·t_step, is at most 7200 s and at most the remaining aggregate budget. E1 and
  E2 run only together.
- **Stop rule:** every evaluation run stops at **start + min(1.25 × prediction, 7200 s, remaining
  aggregate seconds)**. A 7200 s prediction therefore stops at 7200 s, not 9000 s, and a stopped
  run is INCOMPLETE with no verdict.
- **Shot counts,** with no time estimate until t_step is measured:
  - **Pilot:** 16(W + 125 000) ≈ 2.0–2.06 × 10⁶ evaluation-grid steps per point.
  - **NC5/NC6, per check seed:** (2W + 50 000) + (W + 50 000) steps on M241/L7, W + 50 000 on
    M241/L5, and W + 50 000 on each M121 grid.

## 10. Execution stack: definition, reviewed solve and locking plan

**Machine.** Apple M1 Pro, arm64. The available conda is 22.9.0 as an **osx-64** build, whose
configured channel is `defaults`.

**One definition for both steps.**
- **conda part:** [analysis/stack_F/conda-osx-arm64.txt](../analysis/stack_F/conda-osx-arm64.txt)
  contains `python=3.12`, `numpy=2.4.4`, `scipy=1.17.1`, `matplotlib=3.10.8`, `pytest=9.0.3`,
  `pyyaml=6.0.3`, `pip` and `libblas=*=*openblas`.
- **pip part:** [analysis/stack_F/pip-requirements.txt](../analysis/stack_F/pip-requirements.txt)
  contains `cffconvert==2.0.0`.

Solve and installation run the same command. The installation replaces `--dry-run --json`
with `-y`:

```sh
CONDA_SUBDIR=osx-arm64 conda create --dry-run --json -n sid-f \
    --override-channels -c conda-forge --no-default-packages --file analysis/stack_F/conda-osx-arm64.txt
```

`--override-channels` keeps configured channels such as `defaults` out of both steps.

**The reviewed dry-run solve,** run 2026-09-15T14:41:15Z in 172 s with exit 0. The raw output
and its metadata are in
[conda-dry-run-osx-arm64.json](../analysis/stack_F/conda-dry-run-osx-arm64.json).
- **Scope:** 80 packages, all from conda-forge; 60 osx-arm64 and 20 noarch.
- **Stop conditions:** none triggered.

| Package | Version | Build |
|---|---|---|
| python | **3.12.0** | h47c9636_0_cpython |
| numpy | 2.4.4 | py312ha003a3f_0 |
| scipy | 1.17.1 | py312h4519d97_1 |
| matplotlib | 3.10.8 | py312h1f38498_0 |
| pytest | 9.0.3 | pyhc364b38_1 |
| pyyaml | 6.0.3 | py312h04c11ed_1 |
| pip | 26.2.1 | pyh8b19718_0 |
| libblas / libcblas / liblapack | 3.11.0 | 11_…_openblas |
| libopenblas | 0.3.34 | openmp_h5e6e99c_1 |
| llvm-openmp | 23.1.1 | hdb3d66b_0 |

**Two findings from the solve.**
1. **Python resolved to 3.12.0 (October 2023), although the same conda-forge osx-arm64 metadata
   has 3.12.13 and 3.12.14 builds.**
   - *Ruled out:* a missing `__osx` virtual package. Under `CONDA_SUBDIR=osx-arm64`, conda reports
     `__osx` 26.6.2 with archspec arm64, and 49 of the 60 chosen osx-arm64 builds already require
     `__osx >=11.0`, including NumPy, SciPy and OpenBLAS.
   - *Visible difference:* the newer Python builds also depend on `libpython`, `liblzma` and newer
     `libffi`, `openssl` and `libexpat`.
   - *Not established:* why the classic solver of conda 22.9.0 preferred 3.12.0.
2. **OpenBLAS is the OpenMP build,** so both `OMP_NUM_THREADS` and `OPENBLAS_NUM_THREADS` must be 1.
   The protocol already requires all five thread variables to be 1.

**Locking plan, after installation is approved.** Each step stops on its stop condition.
1. **Install** with the command above, using `-y` in place of `--dry-run --json`.
2. **Compare** `conda list -n sid-f --json`, saved as `conda-list.json`, with the reviewed solve by
   name, version and build. Stop if they differ, because channel metadata can change between
   the two steps.
3. **Verify the architecture:** `file $ENV/bin/python3.12` must report arm64.
4. **pip resolution without installing:**
   `$ENV/bin/python -m pip install --dry-run --no-cache-dir --report analysis/stack_F/pip-report.json -r analysis/stack_F/pip-requirements.txt`.
5. **pip lock:** `tools/lock_stack_F.py pip-lock` writes `pip-lock.txt` as `name==version --hash=sha256:…`.
   It refuses if pip would install anything conda provides, or if any entry lacks a sha256;
   fixture tests cover both refusals.
6. **pip install:** `pip install --no-deps --require-hashes --no-cache-dir -r analysis/stack_F/pip-lock.txt`.
7. **Record and lock:**
   - `conda list --explicit --md5 > conda-osx-arm64.lock` (conda packages);
   - `pip list --format=json --verbose > pip-installed.json`, which records the installer of each
     distribution;
   - `tools/lock_stack_F.py record`, run with the five thread variables set, writes
     `stack-record.json` with the Python patch version, machine, platform, NumPy/SciPy, NumPy's
     build configuration, the BLAS package builds and the thread variables.
   - All of these are committed before Gate 3.

**Installation stop conditions, from the protocol.**
- The installed set differs from the reviewed solve.
- Any channel other than conda-forge.
- A subdir other than osx-arm64 or noarch.
- A `libblas` build without `openblas`.
- A Python other than 3.12.x, or NumPy/SciPy other than the pins.
- A Python binary that is not arm64.
- pip replacing a conda distribution, or an entry without a sha256.

## 11. Review decisions and the one remaining choice

| Choice | Decision (Gate-0 review) |
|---|---|
| BLAS | OpenBLAS pinned explicitly (`libblas=*=*openblas`) |
| Burn-in W | max(1000, ⌈100·τ_c/c⌉), subject to the corrected NC6 |
| Pilot length and stability | 125 000 shots and factor 4, as planning choices; the variance bound is described as approximate |
| Check sizes and threshold | eight 50 000-observation windows; simulator check at 5 standard errors |
| Prediction and stopping margins | 1.10 and 1.25, subordinate to the enforced hard caps |
| Primary comparator | K1 alone decides F; C08-boundary validation is reported separately |
| Labbook | the freeze pass is sufficient |

**Open: the Python patch version.** `python=3.12` currently resolves to 3.12.0. The options:
- **(a)** Accept 3.12.0 and record it.
- **(b) — my recommendation.** Pin `python=3.12.14` in the spec and run a second dry-run solve.
  This changes the reviewed definition, so it needs your approval.
- **(c)** If conda 22.9.0 cannot solve (b), use a native Miniforge conda instead. That is a separate
  installation needing its own approval.

## 12. Limits

- **Where the design evidence comes from:** the drafting stack (Python 3.9.7, SciPy 1.10.0).
  `--check` also matches under Python 3.13.7 / SciPy 1.17.1.
- **Test runs:**
  - on 3.9.7, 66 tests pass across the protocol draft, the stack lock helper, C08 fold
    provenance, crossover provenance, site projection and public prose;
  - on 3.13.7, the protocol and lock tests pass (33).
- **Scope of the tests:** they check documents, rules and helpers on fixtures. They validate no
  comparator and install nothing.
- **Model assistance:** drafting and analysis used it.
