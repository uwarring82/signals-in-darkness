# Signals in Darkness — execution note 04 (3 Sept 2026): reproduction-route defect at `archive-2026-09-03`

Written while certifying the repository seed immediately after the first commit (`5c1f909`, tag `archive-2026-09-03`). Four defects are recorded, in decreasing order of consequence. Items 1–3 concern the policy-comparison chain (`sid_run6s.py`); item 4 is unrelated and concerns `sid_run8.py`. Nothing in notes 01–03a is edited; the consequences for the claim ledger are recorded in `ledgers/status.yaml` and pointed back here.

Checks were run from a clean `git clone` of the tagged commit into a scratch directory, so no archived file was modified during the investigation. Environment: python 3.11.11, numpy 2.2.4, scipy 1.15.2 — **not** the pinned `environment.yml` (python 3.12, numpy 2.4.4, scipy 1.17.1), which no available environment satisfies. That mismatch turned out to be informative rather than disqualifying: see §2. The checks were performed with machine assistance; the evidence below is the record, the assistance is not.

## 1. Interface defect — the documented command consumed committed cache state

`analysis/runs/sid_run6s.py` at the tagged commit sets `STATE = os.path.join(OUTD, "res6_policies.json")` (line 81) and loads it if it exists (line 82). The two stage loops then skip any entry already present: `if name in state["cal"]: log("cached", …); continue` (line 101) and `if name in row: continue` (line 111). Because `analysis/outputs/res6_policies.json` is a committed file holding all seven calibration rows and all fifteen delay rows, the commands the README documents —

```
python sid_run6s.py "cal:oracle-mid(tc=20),…"; python sid_run6s.py delays
```

— recompute **nothing** on a clean clone. Measured: the calibration stage returned all seven rows in 0 s, printing the archived values. The same file is both the script's published output and its mutable checkpoint, so the archive silently answers the question the reader believes they are asking.

This alone fails the binding acceptance criterion of `cards/repo-seed-v0.2.md` ("a clean environment reproduces … the calibration table (note 03 §2, within stated uncertainty) … from recorded seeds"), independently of whether the archived numbers are correct. It also breaks rule 4 one level up: the route rereads an output's description of itself.

Real cost of the calibration stage when it does compute: **7.7 minutes** (7 policies, one core), against 0 s cached.

## 2. Provenance defect — two archived rows cannot be produced by the committed code

With `res6_policies.json` removed from the clone, the calibration stage was rerun cold. Five of seven rows regenerate **bit-identically**, including the full float tails:

| policy | archived = regenerated |
|---|---|
| `oracle-mid(tc=5)` | `3.421875 / 38283.15625 / 4605.476487918581 / 3` |
| `oracle-mid(tc=1)` | `1.546875 / 28853.828125 / 3431.937345741478 / 1` |
| `extremum-only` | `3.734375 / 32314.0 / 3567.985930479219 / 1` |
| `learner-mid(bank)` | `3.421875 / 27697.625 / 2715.414548492737 / 0` |
| `learner-interleave-B1(bank)` | `3.421875 / 31881.265625 / 3635.2225879962857 / 0` |

`calibrate()` fixes `seed=100` and a deterministic bisection, so this is expected — and it establishes the control this note depends on: the RNG stream and the simulator are stable across the environment change recorded in the preamble, and the harness used below is faithful.

Two rows do not regenerate, and fail a second, stronger test — they are not reproduced even when the simulator is driven at their own archived threshold, using the same confirmation call the calibrator ends with (`arl_of(·, R=64, seed=199)`):

| policy | archived | cold bisection | re-run at the archived h\* |
|---|---|---|---|
| `oracle-mid(tc=20)` | `4.359 / 33852 / 3394 / 0` | `4.671875 / 44698.640625 / 5208.357712 / 4` | `31881.265625 / 3212.951595 / 0` |
| `learner-interleave-B10(bank)` | `3.55 / 34014.96875 / 3017.082197716481 / 0` | `3.734375 / 47313 / 4186 / 0` | `37841.375 / 3540.903337 / 0` |

Two independent signatures corroborate the conclusion that these were entered by hand rather than written by the script:

- `oracle-mid(tc=20)` is rounded to exactly the log line's print precision in all three fields (`h*={h:.3f}`, `ARL={m:.0f} +- {se:.0f}`), while every regenerating row carries full float precision.
- `learner-interleave-B10` carries a full-precision ARL and standard error but `h* = 3.55`, which is off the k/64 lattice the bisection can produce (3.55 × 64 = 227.2; the neighbouring lattice values are 3.546875 and 3.5625). Its threshold was overwritten after the run that produced its ARL.

**Their provenance is lost.** They are therefore withdrawn, not merely open: no code in this repository generates them, and the code that did is not recorded. The cold-bisection values in the table above are diagnostic evidence of the defect and are **not** replacement results — they were obtained under an unpinned environment and have not been through the calibration protocol as a whole.

Note the tolerance lesson. Both bad rows sit **inside** a 3σ agreement band on the mean (1.74σ and 2.58σ). A comparison that tests only means would have passed them. Exact equality of the deterministic threshold is what catches them, and is why the tolerance declared in `analysis/lib/sid_repro.py` gates on `h*` exactly and on means at 3σ.

## 3. Downstream impact — the affected comparisons are no longer at matched null run length

Delay entries are measured at each policy's own calibrated threshold (`delay_of(…, state["cal"][name][0], …)`). Four entries in `res6_policies.json` were therefore measured at a threshold of unknown provenance and are withdrawn with it:

- `oracle-mid(tc=20)` at τ_c/c = 20 — `1332.1875 ± 114.43`
- `learner-interleave-B10(bank)` at τ_c/c = 20, 5, 1 — `2044.015625 ± 178.89`, `2680.203125 ± 256.65`, `4580.78125 ± 339.08`

The consequence is larger than four numbers. At τ_c/c = 20 the benchmark is `min(oracle-mid(tc=20), extremum-only) = 1332.19`, i.e. the withdrawn entry, so **every ratio reported at τ_c/c = 20 divides by a withdrawn quantity** — including the worst-case delay ratio 1.56 of note 03 §3 / errata E3, and the 0.98× of errata E2 (`1299.03 / 1332.19`). The measured null run lengths behind those comparisons are 44 699 and 47 313 rather than the ~33 900 and ~34 000 recorded, i.e. +49 % and +58 % from the 3 × 10⁴ target, outside the ±30 % band note 03 §2 states. The matched-Ê₀[T] premise does not hold for those policies.

Claims C09, C11 and C12 are demoted to `open` until the calibration-and-delay chain is rerun end to end. C10 is unaffected: it comes from `sid_run5.py`, which has no cache and reproduces. `figures/sid_policy_delays.png` is built from `res6_policies.json` and `res8_switch.json` and therefore currently plots withdrawn entries.

## 4. Unrelated defect — `sid_run8.py` writes to the working directory

`analysis/runs/sid_run8.py` defines `OUTD` (line 2) and never uses it; line 50 is `json.dump(…, open("res8_switch.json", "w"))`, a path relative to the current working directory. Following the README (`cd analysis/runs`) leaves the file in `analysis/runs/`, while `sid_fig_policy_delays.py` keeps reading `analysis/outputs/res8_switch.json`. The committed `analysis/outputs/res8_switch.json` cannot have been written in place by a run performed as documented, so **its numerical output is unresolved** until it is independently regenerated and compared; it is recorded as `open`, not withdrawn, because nothing yet contradicts its values.

The same file also obtained its machinery by `exec()`-ing a text slice of `sid_run6s.py` (`.split("arg=sys.argv[1]")[0]`), which bound that script's state file as a side effect and would break silently on any edit above the split marker. That is an unsafe coupling; it did **not** replay cached rows, because the slice stops before the cache branches and `state` is never referenced in `sid_run8.py`.

## 5. Closure conditions

The reproduction criterion may not be marked satisfied until all of the following hold:

1. The documented command computes afresh by default; reuse of previous state is available only through an explicit `--resume`.
2. Published reference outputs and mutable checkpoints live in separate directories, and checkpoints are ignored by git.
3. Fresh results are written to the reproduction directory and compared against the archive under declared tolerances, never written over it.
4. Every run reports `computed: N, cached: M` together with seeds, runtime, code revision and environment.
5. A regression test runs with the committed reference archive present and fails if the route reports work that no simulation performed.
6. `sid_run8.py` writes to its declared destination and imports shared machinery instead of executing another script as text.
7. A clean-checkout rerun of the whole affected chain — calibration, delays, and the explore-then-switch table — under a pinned environment, with the results compared to the archive under those tolerances.

Items 1–6 are addressed in the commit that carries this note (`analysis/lib/sid_policies.py`, `analysis/lib/sid_repro.py`, rewritten `sid_run6s.py` and `sid_run8.py`, `tests/test_reproduction_route.py`). Item 7 remains open and is the release gate.

---

*Footnote, investigated and dismissed.* At seed 199 the null stopping-time arrays for `oracle-mid(tc=20)` at h = 4.359375 and for `learner-interleave-B1` at h = 3.421875 differ element-wise yet share the identical integer sum 2 040 401, hence an identical mean. At seeds 200 and 201 the sums differ normally (2 074 795 vs 2 230 217; 1 812 866 vs 2 086 603). A coincidence, not structure; recorded so it is not rediscovered as evidence of aliasing.
