# Signals in Darkness — execution note 07 (4 Sept 2026): pinned-environment reproduction

The first reproduction of the whole analysis path in the environment `environment.yml` pins.
It closed one archival gap, produced three previously unstored outputs, and independently
confirmed the two withdrawals recorded in note 04. It also found two defects that only running
the pinned path could expose, both fixed before the certified run.

This note records evidence. The release certification itself is a separate run from a clean
clone of the tagged commit; see §6.

## 1. Platform certified

One platform, named precisely, with no claim beyond it:

| | |
|---|---|
| host | Apple M1 Pro (`uname -m` → `arm64`) |
| execution | macOS 26.6.2, **x86_64 under Rosetta 2** — the anaconda3 installation is Intel |
| interpreter | Python 3.12.14 (`Mach-O 64-bit executable x86_64`) |
| libraries | numpy 2.4.4, scipy 1.17.1, matplotlib 3.10.8, pytest 9.0.3 — every pin confirmed against `environment.yml` in the log |
| BLAS | `blas 3.9.0` |
| native arm64 | **untested** |

Identical pins on a different architecture, or without translation, are a different numerical
stack. Nothing here certifies native arm64; that remains a later portability check. Platform,
machine, processor and BLAS are now part of every run's provenance banner and of the identity a
calibration checkpoint carries, so a checkpoint from one stack cannot be consumed by another.

## 2. Two defects the pinned run exposed

**`sid_run2.py` had never completed.** Its figure labels used `\tfrac`, which matplotlib's
mathtext does not define — checked against 3.10.8, 3.10.1 and 3.7.1, all raising
`Unknown symbol: \tfrac`. This is *not* version sensitivity: the committed path cannot complete
under any tested supported matplotlib. The crash mattered because `json.dump` sat after the
figure, so every run died before writing `res2_partial.json`. That is the "figure crash" the old
schema note referred to without naming, and it explains both standing puzzles: why the archived
B2 rows had 7 columns where the producer builds 10, and why key `F2` was absent although the
producer writes it. Fixed by using `\frac`, and by writing the numerical output before any
plotting, so a figure failure can no longer destroy a run's data.

**`sid_run6s.py delays` could not see its own input.** It read thresholds only from its own
state, which "fresh by default" leaves empty, so the documented two-command sequence failed every
time. Thresholds are a required output of the *current* reproduction, held in the reproduction
checkpoint and never in the archive; reading them is not reuse of prior state. `--resume`
continues to govern only whether delay rows already measured are reused.

## 3. What reproduced

Under the pinned stack, against the archive and the declared tolerances:

| output | result |
|---|---|
| `res1_core.json` | max relative deviation **1.7e-12** (tolerance 1e-9) |
| `res7B_servo.json` | **1.4e-16** |
| `res7A_identifiability.json` | **6.0e-8** (tolerance 1e-6; class-B rows come from an L-BFGS-B infimum whose convergence point moves with the scipy version) |
| `res6_policies.json` calibration | `computed: 7, cached: 0` — five rows at **0.00 σ**, two failing on exact `h*` |
| `res6_policies.json` delays | `computed: 15, cached: 0` — **11 of 15 rows at 0.00 σ** |

The 1.7e-12 on `res1_core.json` is the measured size of the difference between python 3.9 /
numpy 1.23 and python 3.12 / numpy 2.4.4 on this stack. No version sensitivity was detected
across the tested Python and NumPy versions on the x86_64/Rosetta execution path, at the
tolerances declared in `tools/compare_reproduction.py`.

## 4. The withdrawals of note 04, independently confirmed

The two calibration rows withdrawn as C17 failed again, on the same field and with the same
values (`h* 4.671875` against archived `4.359`; `3.734375` against `3.55`), under a different
interpreter and a different numpy major version. Their provenance loss is therefore a fact about
those rows, not an artefact of the environment used to find it.

The delay stage sharpened C18. Eleven of fifteen rows reproduced bitwise; the four that moved are
exactly the four measured at the two withdrawn thresholds:

| row | archived | reproduced | deviation |
|---|---|---|---|
| `oracle-mid(tc=20)` at τ_c/c = 20 | 1332.2 | 1448.6 | 0.70 σ |
| `learner-interleave-B10(bank)` at 20 | 2044.0 | 2196.8 | 0.60 σ |
| `learner-interleave-B10(bank)` at 5 | 2680.2 | 2823.6 | 0.40 σ |
| `learner-interleave-B10(bank)` at 1 | 4580.8 | 4707.6 | 0.26 σ |

All four sit inside a 3 σ band on the mean, so a means-only comparison would have passed every
one of them. The exact-threshold test is what catches them — the same lesson as note 04 §2,
now demonstrated on the delays as well as the calibration.

There is a consequence for C11. At τ_c/c = 20 the benchmark
`min(oracle-mid(tc=20), extremum-only)` becomes 1449 rather than the archived 1332, so
fixed-extremum operation sits at **1.44×** rather than the 1.56 note 03 §3 reports. C11 is
already `open`; this quantifies by how much its headline number moves once the thresholds are
derived rather than transcribed. It is not a replacement result: it comes from a single
reproduction and has not been through the calibration protocol as a whole.

## 5. `res2_partial.json` adopted

The reproduced file replaces the hand reconstruction. The legacy 7 fields map index-for-index
onto the first 7 of the new 10, and every overlapping value equals the reproduced value rounded
to the 4 significant figures it was stored at — an exact test, not a tolerance, because the
permitted rounding error depends on the leading mantissa digit and a flat bound would be wrong.
Newly archived, and therefore not reproductions of anything: B2 columns 3–5 (previously null),
columns 7–9 (previously absent), and the keys `crossover`, `C2` and `F2`.

`F2` reproduces all eleven values quoted in note 01 §7 at their stated precision, with 40 of 40
runs detected on every row, so C25's `[unreproduced-from-file]` qualifier is removed. Its
scientific status is unchanged: archival reproduction closes a records gap, it does not promote a
claim.

One statement is looser than its own data, and reproduction does not fix it: note 01 §7 says
delays run "0.8–0.9 of h/I", but its own published numbers span 0.799–0.916 and the reproduction
spans 0.799–0.917. Recorded rather than quietly adopted.

Adopting one file makes the archive mixed-provenance, which should be stated rather than left
implicit: `res2_partial.json` now comes from the pinned python 3.12 stack, while
`res1_core.json`, `res7A_identifiability.json` and `res7B_servo.json` were produced on python
3.11 / numpy 2.2 and `res6_policies.json` predates all of it. Each still reproduces within its
declared tolerance under the pinned environment — the 1.7e-12 on `res1_core.json` is exactly
that difference — so this is a provenance fact, not a defect. Making the whole archive
single-stack would mean regenerating files whose values would move only in the twelfth
significant figure, and is a decision for the owner rather than a side effect of this adoption.

`crossover` is `sid_run2.py`'s own HMM-grid crossover estimate (6.29 at C̄ = 0.4, s = 0.5). It is
**not** the comparator crossover of C05 (7.24, from `sid_run3.py`), which remains unstored. `C2`
holds the 7-angle endpoint profile behind note 01 §4 and bears on C06, whose cited output does
not match its note; assessing that is separate work and no claim was changed on the strength of
this file appearing.

## 6. Status

This note records evidence, not certification. The release gate is a run from a clean clone of
the commit that is actually tagged, with no tracked change afterwards, so that the object
certified and the object tagged are the same. That run's record is kept as a release artefact
rather than committed, since committing it would change the object that was certified.
