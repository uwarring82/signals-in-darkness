# Signals in Darkness — note 28 (15 Sept 2026, DRAFT r4): roadmap F protocol for review

**Status:** DRAFT FOR REVIEW, revision 4. The revisions so far are `0a3584b`, `4f0b390` and
`a327ab5`. The package is:
- this note;
- [analysis/protocol_F.json](../analysis/protocol_F.json), with `status` DRAFT, `draft_revision` 4 and
  `digest` null;
- [tools/build_protocol_F.py](../tools/build_protocol_F.py), which builds the protocol, checks it and,
  once approved, freezes it;
- [tests/test_protocol_F_draft.py](../tests/test_protocol_F_draft.py);
- the execution stack in [analysis/stack_F/](../analysis/stack_F/conda-osx-arm64.txt), now installed and
  locked (commit `009deb5`);
- [tools/lock_stack_F.py](../tools/lock_stack_F.py) and [tests/test_lock_stack_F.py](../tests/test_lock_stack_F.py).

**The freeze is not yet done.** You approved the Gate-1 freeze once the bounded wording
correction passed its checks. That correction does pass. But checking revision 4 on the newly
installed execution stack exposed a separate defect in the design evidence, and fixing it
changed protocol content you had not reviewed (§0). The freeze tooling is ready and tested on
temporary copies, and the freeze waits for your confirmation.

**What has and has not happened:**
- **Ran:** two approved dry-run solves, and the approved installation with its locking.
- **Not run:** no ARMA likelihood evaluation, no latent-record simulation, no numerical check
  from Gate 3, no pilot and no evaluation.

**Evidence snapshot:** `009deb5`. `python tools/build_protocol_F.py --check` and `--markdown` are
read-only.

## 0. Review history

### Revision 4

| Item | Change |
|---|---|
| Scope correction (your request) | After evaluation, the scope sentence speaks only about the mandatory points. If K1 validated at any of them: "At the mandatory points E3–E5, the exact-r_k comparator (K1) is validated … at {validated tuples}." Otherwise: "No mandatory point E3–E5 validated K1 against the finite-window binary likelihood." Next comes "C04 supplies the earlier point-sampled validation; results at the conditional boundary points E1/E2 are reported separately." The pre-evaluation caveat and the numerical closure rule are unchanged (§8). |
| Your fixture | E1/E2 VALIDATED with E3–E5 FAILED closes FAILED. The caveat then says no mandatory point validated and names neither boundary point. A further test runs all 64 combinations of mandatory verdicts, with and without boundary verdicts, and requires that no text confines validation to C04. |
| **Unrequested: design evidence recorded as bounds** | On the installed execution stack (`sid-f`: Python 3.12.14, NumPy 2.4.4, SciPy 1.17.1, OpenBLAS), `--check` failed and two tests failed. Exactly one value differed: the total variation between π and the Gaussian weights at E1 on M121/L7, which is 9.878 × 10⁻¹³ on the drafting stack and 9.997 × 10⁻¹³ on `sid-f`. That is a 1.2 % relative and 1.2 × 10⁻¹⁴ absolute difference in eigenvector roundoff. The builder had recorded noise as if it were a reproducible value. It now records bounds: total variation below 10⁻⁶ (true everywhere, observed 2.1–4.7 × 10⁻⁷ on the L = 5 grids) and below 10⁻¹⁰ (true on both L = 7 grids, observed 0.99–2.05 × 10⁻¹²). Series-convergence changes, at most 9.9 × 10⁻¹⁴, are also recorded as a flag within 10⁻⁶. A new guard test rejects any nonzero design-evidence float below 10⁻⁹; it would have caught the defect. Every protocol rule, point, comparator value and constant is unchanged. |
| Freeze tooling | `--freeze` accepts only a draft that matches its builder. It sets `status` and `frozen`, and computes the digest with the convention of `tools/freeze_ladder_selections.py`. Tests on temporary copies cover the frozen result verifying its digest, a tampered copy failing, a second freeze and any later draft write being refused, and a modified draft being refused. |
| Your bookkeeping correction | Revision 3 counted 41 protocol tests and 7 lock tests, not the 43 and 5 its §12 stated. Revision 4 has 49 protocol tests (§12). |
| My own fixture error | The first freeze-tooling test used `benchmark_ladder_C.json` as its digest fixture, and it failed: that file's stored digest does not recompute under this convention. The test now uses three artifacts that do. See §12 for what this shows about three roadmap-C artifacts. |

### Earlier revisions

- **r3 (`a327ab5`):**
  - Python pinned to 3.12.14, with the pinned dry-run solve recorded.
  - Separate caveat parts for scope, status and tuples. Revision 4 narrows the scope part.
- **r2 (`4f0b390`):**
  - NC6 compares filters on the same final observations.
  - Every run stops at the earliest of its caps, and Gate 3 has a deadline.
  - The builder refuses to overwrite a frozen protocol.
  - One definition and channel policy for solve and installation, with OpenBLAS and a pip lock.

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

**How much initialisation matters, recorded as bounds since revision 4.** At every point the
total variation between π and the Gaussian weights is below 10⁻⁶ on all four grids, and below
10⁻¹⁰ on both L = 7 grids. On those L = 7 grids it is roundoff, as revision 4 found. The
innovation standard deviation spans at least 2.84 grid spacings, and at least 4.06 on the
evaluation grid.

## 4. Simulator and points

**Simulator.**
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
- **Filter steps on M241/L7:** (2W + 50 000) + (W + 50 000).
- **Filter steps on each check grid:** W + 50 000.

The grid, burn-in, record lengths and seeds change only through a superseding protocol version.

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

**Closure rule, unchanged.**
- **Roadmap F:** decided by K1 alone. It closes VALIDATED iff K1 is VALIDATED at E3, E4 and E5. It
  closes FAILED iff all three receive VALIDATED or FAILED and at least one is FAILED. Otherwise F
  remains OPEN.
- **Licensed statements:** K1 and K2 statements are licensed only at their own validated tuples.
- **C08's boundary:** reported separately. A statement there needs E1 and E2 both evaluated, with
  the comparator VALIDATED at both, whatever F's closure. Boundary verdicts never enter the status.

**Wording, revised in revision 4.**

*Before evaluation*, note 27's caveat is used verbatim. It ends "Binary-likelihood validation
remains confined to C04's tested point-sampled exact-r_k comparator; F remains open."

*After evaluation*, the caveat is built from five parts, in order:

1. Note 27's statement that C08's archived implementation divides the first-lag correlation by
   F(u), and that the archived rate map is not the finite-window comparator.
2. A scope sentence about the mandatory points only:
   - with at least one mandatory validation: "At the mandatory points E3–E5, the exact-r_k
     comparator (K1) is validated against the exact finite-window ARMA(1,1) binary likelihood within
     ±5 % (pointwise 95 % intervals) at {validated tuples}."
   - with none: "No mandatory point E3–E5 validated K1 against the finite-window binary likelihood."
3. "C04 supplies the earlier point-sampled validation; results at the conditional boundary points
   E1/E2 are reported separately."
4. The status sentence: "Roadmap F remains OPEN.", "Roadmap F closed VALIDATED." or "Roadmap F closed
   FAILED."
5. The tuple report for E3–E5: "K1 at the mandatory points: VALIDATED at …; FAILED at …; UNRESOLVED
   or without a verdict at …."

The campaign status never decides the scope sentence, and E1/E2 verdicts never enter this caveat.
Generated text, omitting the C08 opening:

- **E1/E2 VALIDATED, E3–E5 FAILED (your fixture):** "No mandatory point E3–E5 validated K1 against
  the finite-window binary likelihood. C04 supplies the earlier point-sampled validation; results at
  the conditional boundary points E1/E2 are reported separately. Roadmap F closed FAILED. K1 at the
  mandatory points: VALIDATED at none; FAILED at E3 (C, s, u, c/tau_c) = (0.40, 0.50, 0.10, 0.15),
  E4 (C, s, u, c/tau_c) = (0.40, 0.50, 0.30, 0.35) and E5 (C, s, u, c/tau_c) = (0.40, 1.00, 1.00,
  1.05); UNRESOLVED or without a verdict at none."
- **E3 VALIDATED, E4 FAILED, E5 VALIDATED:** "At the mandatory points E3–E5, the exact-r_k comparator
  (K1) is validated against the exact finite-window ARMA(1,1) binary likelihood within +/- 5 %
  (pointwise 95 % intervals) at E3 (C, s, u, c/tau_c) = (0.40, 0.50, 0.10, 0.15) and E5 (C, s, u,
  c/tau_c) = (0.40, 1.00, 1.00, 1.05). C04 supplies the earlier point-sampled validation; results at
  the conditional boundary points E1/E2 are reported separately. Roadmap F closed FAILED. …"

**Tests for the wording.**
- The pre-evaluation text must match note 27 verbatim.
- No post-evaluation text confines validation to C04, for any mandatory outcome with or without
  boundary verdicts.
- Your fixture names neither boundary point.
- Both mixed examples keep their mandatory validations.
- A fully validated outcome lists all three mandatory tuples.
- The status function ignores boundary verdicts, and refuses unknown points, unknown verdicts or a
  missing mandatory verdict.

Any analysis the protocol does not specify is post-unblinding and cannot change a verdict.

## 9. Budget, deadlines and stopping

- **Clock:** one numerical thread. The aggregate budget is **28 800 s**, counted as the sum of the
  wall-clock seconds each `sid_run13` phase records. Each run reads the remaining budget before it
  starts.
- **Gate-3 deadline:** **1800 s**, enforced from the start of Gate 3, never later than the remaining
  aggregate budget. It covers every step, including NC1, NC3 and the first point's measurement.
  A step that reaches it is INCOMPLETE, and an incomplete NC1 blocks every point.
- **Gate-3 order:** NC1 and NC3 first, then E3, E4, E5, E1 and E2. A point is NOT_ATTEMPTED if its
  predicted checks and pilot exceed the time left, and E1 and E2 are admitted together.
- **Evaluation admission:** a mandatory point runs only if its prediction, 1.10 × 16(W + n_e)·t_step,
  is at most 7200 s and at most the remaining aggregate budget. E1 and E2 run only together.
- **Stop rule:** every evaluation run stops at **start + min(1.25 × prediction, 7200 s, remaining
  aggregate seconds)**. A 7200 s prediction stops at 7200 s, and a stopped run is INCOMPLETE with no
  verdict.

## 10. Execution stack: installed and locked

**Definition.**
- **conda part:** [analysis/stack_F/conda-osx-arm64.txt](../analysis/stack_F/conda-osx-arm64.txt)
  contains `python=3.12.14`, `numpy=2.4.4`, `scipy=1.17.1`, `matplotlib=3.10.8`, `pytest=9.0.3`,
  `pyyaml=6.0.3`, `pip` and `libblas=*=*openblas`.
- **pip part:** [analysis/stack_F/pip-requirements.txt](../analysis/stack_F/pip-requirements.txt)
  contains `cffconvert==2.0.0`.

Solve and installation run the same command, differing only in `--dry-run --json` versus `-y`.
The reviewed solve is
[conda-dry-run-osx-arm64-python3.12.14.json](../analysis/stack_F/conda-dry-run-osx-arm64-python3.12.14.json):
77 packages, all from conda-forge.

**Installation, approved after revision 3.** Every stop condition passed (commit `009deb5`):

| Step | Result |
|---|---|
| 1. `conda create -y` with the reviewed command | exit 0 in 225 s ([metadata](../analysis/stack_F/install-osx-arm64.meta.txt)) |
| 2. Installed set against the reviewed solve | identical, 77 of 77 by name, version and build; all conda-forge; 57 osx-arm64 and 20 noarch; Python 3.12.14, NumPy 2.4.4, SciPy 1.17.1, `libblas` 11_h51639a9_openblas, `libopenblas` 0.3.34 (OpenMP build) ([conda-list.json](../analysis/stack_F/conda-list.json)) |
| 3. Architecture | `python3.12` is a native arm64 Mach-O executable |
| 4. pip resolution report | 13 distributions ([pip-report.json](../analysis/stack_F/pip-report.json)); `python-dateutil` was already satisfied by conda |
| 5. Hash-pinned lock | written by `tools/lock_stack_F.py`; no entry is conda-provided, and every entry has a sha256 ([pip-lock.txt](../analysis/stack_F/pip-lock.txt)) |
| 6. pip install | `--no-deps --require-hashes` installed exactly the locked set; `pip check` reports no broken requirements |
| 7. Locks and record | [conda-osx-arm64.lock](../analysis/stack_F/conda-osx-arm64.lock) (77 URLs with md5); [pip-installed.json](../analysis/stack_F/pip-installed.json) (13 pip, 24 conda, 3 without an installer field); [stack-record.json](../analysis/stack_F/stack-record.json), written with all five thread variables at 1, records Python 3.12.14, arm64 and OpenBLAS |

**Disclosure.** `docopt 0.6.2` is the only source distribution. pip built it locally with build
isolation and fetched `setuptools 84.0.0` without a hash pin. The built wheel's hash is
recorded in [pip-docopt-build.txt](../analysis/stack_F/pip-docopt-build.txt). This affects only
the pip tooling for `cffconvert`, not the numerical stack.

**Execution-stack check.** Once installation finished, the builder and the protocol and lock tests
were run on `sid-f` itself. That run exposed the roundoff defect recorded in §0. With the
revision-4 bounds, `--check` matches and all 56 protocol and lock tests pass on `sid-f`.

## 11. Review decisions

| Choice | Decision |
|---|---|
| BLAS | OpenBLAS pinned explicitly (`libblas=*=*openblas`) |
| Python | 3.12.14 pinned (option b), with the pinned solve recorded |
| Installation | approved under §10's locking plan; completed with every stop condition passing |
| Burn-in W | max(1000, ⌈100·τ_c/c⌉), subject to the corrected NC6 |
| Pilot length and stability | 125 000 shots and factor 4, as planning choices; the variance bound is approximate |
| Check sizes and threshold | eight 50 000-observation windows; simulator check at 5 standard errors |
| Prediction and stopping margins | 1.10 and 1.25, subordinate to the enforced hard caps |
| Primary comparator | K1 alone decides F; C08-boundary validation is reported separately |
| Labbook | the freeze pass is sufficient |

**What awaits review.**
- **Your confirmation of the unrequested revision-4 change:** design evidence recorded as bounds.
  After that come the Gate-1 freeze, its digest, labbook pass 27 and the local commit, which you have
  already approved.
- **Later gates:** Gate 2 implementation, Gate 3 numerical checks and pilots, and Gate 4 evaluation
  keep their own approvals.

## 12. Limits and an observation outside F

**Test runs.**
- **Python 3.9.7:** 89 tests pass. That is the protocol draft (49), the stack lock helper (7), and
  C08 fold provenance, crossover provenance, site projection and public prose (33).
- **Python 3.13.7:** the 56 protocol and lock tests pass.
- **`sid-f` (Python 3.12.14, OpenBLAS, one thread):** the same 56 tests pass.
- **Rebuild check:** `--check` matches on all three stacks.
- **Scope:** the tests check documents, rules, recorded solves, installation records and helpers on
  fixtures. They validate no comparator.

**Observation, outside roadmap F.** Of the eleven roadmap-C JSON artifacts that store a digest,
eight recompute under the `freeze_ladder_selections.py` convention. `benchmark_ladder_C.json`,
`eligibility_C.json` and `schedule_class_C.json` do not. `sid_run10.py`'s `_digest_of` returns
each file's stored `digest` field without recomputing it, so nothing in the repository currently
checks those three digests against their content. Whether they were computed with another payload
or the files changed after freezing is not established here. The observation is recorded for a
separate check, and nothing about them was changed.

Drafting, analysis, installation and review responses used model assistance.
