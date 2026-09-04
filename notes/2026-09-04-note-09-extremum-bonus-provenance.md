# Signals in Darkness — execution note 09 (4 Sept 2026): the extremum-bonus table has no producer

Enforcing a new ledger invariant — *`result` and `pilot` claims require an existing
machine-readable output reference* — left two claims failing. C10's table had a producer and
simply was not being stored; that is now fixed. C24's does not.

**No script in this repository computes the table in note 03 §1.** The claim is demoted to
`open`.

## 1. What is missing

Note 03 §1 reports a dark-fringe excess of the exact extremum rate over the marginal Bernoulli
divergence at three operating points, from 3.84 × 10⁶ shots each (64 × 60 000). C24 cited
`analysis/runs/sid_run6s.py (section 1)` for it.

That file exists, which is why the pointer looked sound, but it contains no such section — and
neither does any other script, at the import tag or now. The decisive check is the Ramsey phase:
the table requires an extremum-channel rate, θ = π, and **every `hmm_rate` call in the
repository uses θ = π/2 or a θ-scan**. Nothing computes a dark-fringe rate. Nor does any script
use the stated 64 × 60 000 design.

The seeds were never recorded either, so the published rows cannot be regenerated even with the
method in hand.

## 2. An independent check, which is not a reproduction

`sid_run2.py` now performs the note's design with seeds 0–63 recorded, stored as
`extremum_bonus` in `res2_partial.json`. It is labelled an independent check, because with the
original seeds unknown it cannot be anything else:

| C̄, s, τ_c/c | note 03 §1 | independent check (seeds 0–63) | separation |
|---|---|---|---|
| 0.9, 0.3, 5 | 3.662(40)e-3, −0.9 ± 1.1 % | 3.716(47)e-3, **+0.59 ± 1.27 %** | 0.87 σ |
| 0.9, 0.3, 20 | 3.920(48)e-3, +6.1 ± 1.3 % | 3.964(48)e-3, **+7.31 ± 1.29 %** | 0.65 σ |
| 0.4, 0.5, 20 | 1.299(26)e-3, +0.2 ± 2.0 % | 1.318(23)e-3, **+1.70 ± 1.79 %** | 0.55 σ |

The marginal divergences agree exactly (3.694e-3 and 1.296e-3), confirming the parameters and
the method are the ones the note used. The three rates agree within Monte-Carlo error. So the
*method* is sound and the *phenomenon* is real: there is a positive excess at high contrast and
long correlation time.

## 3. Why the claim is nonetheless demoted

C24 asserted "at most 6 % across the tested points". That is a **bound**, and it rests on a
single unseeded realisation. An independent realisation of the same design gives 7.31 ± 1.29 %
at the point that drives it — above the asserted bound, and 0.65 σ from the note's own
6.1 ± 1.3 %. Both are consistent with a true excess somewhere around 6–7 %, which is precisely
why "at most 6 %" cannot be asserted from one draw of an estimator with a ±1.3 % standard error.

Errata E6 already narrowed this from a global bound to "at most 6 % across the tested points".
The narrowing was in the right direction but not far enough: at this sample size the tested
points do not establish a 6 % ceiling either.

C24 becomes `open`, with the provenance exception documented, which the ledger invariant permits
for `open` and `withdrawn` claims. What would settle it is a longer run — the standard error
scales as 1/√N, so distinguishing 6 % from 7.3 % at 2 σ needs roughly an order of magnitude more
shots — with seeds recorded, which the new producer does.

C15 keeps its `[unreproduced-from-file]` marker. It is `withdrawn`, the invariant permits the
exception there, and the gap is irrecoverable for the same reason: the producer never existed.

## 4. Record

- `sid_run5.py` stores the calibration and slack table as `res5_calibration.json` (C10),
  written **before** the delay measurements so a later failure cannot destroy it — the lesson of
  `sid_run2.py`'s figure crash, recorded in note 07 §2.
- `sid_run2.py` stores the independent extremum-bonus check with its seeds and design.
- `tests/test_ledger_invariants.py` enforces the invariant, plus: every named output file
  exists, every named producer script exists, and every withdrawn claim carries an errata
  pointer. It would have caught C05, C10 and C24.

One limitation is worth stating: the producer test checks that a named *script* exists, not that
a named *section* within it does. C24's pointer named a real file and a section that was never
there, and only reading the code found it. A section-level check would need the scripts to
declare their sections in a machine-readable way, which they do not.
