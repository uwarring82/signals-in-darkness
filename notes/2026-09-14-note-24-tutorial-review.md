# Signals in Darkness — note 24 (14 Sept 2026): tutorial review and a citation erratum

This note records corrections to the drafts of notebooks 02 and 03 and their public summaries.
It changes no scientific claim, archived numerical output or locked manifest.

## 1. Scope and direction of the tutorial statements

- C30's demonstrated action response belongs to posterior sampling. The greedy policy fails
  the action-response gate; updating its beliefs does not establish control response.
- C05's quoted crossover values are at effective contrast 0.4. The stress-point crossing is
  archived and can be recomputed as a worked example, but is not part of that claim. C08's
  interrogation-time-optimised physical map is a separate comparison, with initial contrast,
  finite-window phase variance and wall-clock rates.
- C31 resolves slower sampling in five of six cells; stress at correlation time five cycles
  remains unresolved. The informed fixed endpoint already knows the correlation time.
- The largest point-estimate gap in C27 does not resolve the ranking among the successful
  hedges. The pilot-side claim in this comparison is C11.
- A feasible class-B candidate supplies an upper bound on its infimum. A missed lower candidate
  could only reduce the estimated retained information. Since B is contained in A, the pointwise
  class-A information is a lower bound on the class-B infimum. The notebook states both directions.
- The finite-window OU exponent is below its fast-noise limit. A fast-noise ratio above one is
  necessary but not sufficient for separation on the finite interrogation-time scan.

The last two directions are checked arithmetically in `tests/test_numerical_invariants.py`.
The class-B qualification explains the existing candidate estimate; the ledger is unchanged.

## 2. Preserve the checks after extracting the numerical code

The roadmap-E independence check now imports the driver in a fresh subprocess and checks its
loaded modules, covering indirect dependencies through the extracted library. The no-dead-time
check covers both driver and library. Optimiser and grid-refinement rationale now lives beside
the constants in `analysis/lib/sid_identifiability.py`.

`sid_run9.REGRESSION_TOL = 6e-8` is an **absolute** budget for the historical res7A comparison.
The res9 recomputation test now deliberately applies that numerical value **relatively**, with no
absolute allowance for positive rates and exact equality for zero rates. This tightens the new
test from relative 1e-5; it does not change the historical driver's absolute regression gate.
Absolute and relative tolerances must not be compared as though they were the same quantity.

The initial under-two-second tutorial timings measured cells in an already-started authoring
process. They excluded interpreter startup and imports preceding the timer. End-to-end execution
timings must instead come from fresh subprocesses, as in the tutorial contract test.
On this review pass, the complete fresh-execution contract-test calls took 1.71 s for notebook 02
and 1.32 s for notebook 03, including interpreter startup, imports and archive checks. These are
local observations under Python 3.13.7 with NumPy 2.4.4, SciPy 1.17.1 and Matplotlib 3.10.8,
not a runtime guarantee or a rerun of the pinned release certification.

## 3. Citation erratum to the locked B/E manifest and note 13

The references to `sid_run3.py:129` in `analysis/manifest_BE.json`, under
`physical_stack.t_dead.warning` and `physical_stack.u.at`, and in note 13 section 1 are stale.
The relevant statement was at line 131 of commit `76c0add`; after extraction it is at line 120:

```python
u = taus/tc; c = taus+td
```

The stable target is the loop beneath the **exact-comparator tau-optimised map** section in
[`analysis/runs/sid_run3.py`](../analysis/runs/sid_run3.py), identified by that statement rather
than a floating line number. It still defines `u = tau/tau_c` and `c = tau + t_dead`; the
physical conventions and calculations are unchanged. `tests/test_manifest_BE.py` checks the
content of the definition. The locked manifest and dated note 13 are preserved; this note is
the citation correction.
