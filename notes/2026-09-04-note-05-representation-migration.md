# Signals in Darkness — execution note 05 (4 Sept 2026): stored outputs migrated to strict JSON

Two stored outputs were not valid JSON. This note records the defect, the migration, and the
checks that hold it in place. No scientific value changed meaning; only the representation of
values that were never numbers in the first place.

## 1. The defect

`analysis/outputs/res1_core.json` contained four literal `NaN` tokens and
`analysis/outputs/res7B_servo.json` one `Infinity`. RFC 8259 admits neither. Python's `json`
module emits and accepts both by default, which is why they survived: every reader used in this
project was Python. A conforming parser refuses the files — `node`'s `JSON.parse` rejects both
outright, while `jq` happens to be lenient, so casual checking passed.

This bears on the FAIR matrix directly. `FAIR.md` promises retrievable, interoperable open
formats with documented schemas; a file that only one language's parser will load does not meet
that, and the promise was published while the files could not be read.

## 2. What the values meant

The two cases are different, and were treated differently.

**`res1_core.json`, section F, columns 8 and 9** (mid-fringe delay mean and standard error, at
τ_c/c = 20 and 1). No mid-fringe run reached the threshold within the cap, so `dm.mean()` was
taken over an empty sample. The delay is *undefined* — not a number, not zero, not missing data
that could be filled in. Stored as `null`.

**`res7B_servo.json`, last row, column 0** (κ). The perfect-oscillator limit κ → ∞ is a
deliberate member of the coherence grid, not an error. It is stored as the explicit sentinel
string `"positive-infinity"`. `sid_run7.py` draws it at 100 on the symlog axis, as before. A
magic large number would have been a sentinel indistinguishable from data.

*Corrected later the same day.* This entry first stored κ → ∞ as `null`, on the reading that no
finite coherence applies to it. That conflated two different things. `null` must mean undefined,
missing, or not applicable — a value that does not exist. An infinite limit is a value the
calculation *deliberately visited* and reported a result at; writing it as `null` erases the
distinction between "we looked and there is nothing" and "we evaluated the limiting case".
`null` is now reserved for the former, and known limiting cases carry a declared sentinel that a
consumer must test for explicitly. The finite values are bitwise unchanged across the correction;
only column 0 of the last row differs.

Everything else that is non-finite is now an error. `_mean_se` in `sid_core.py` raises on any
non-finite statistic computed from a non-empty sample, and every writer serialises with
`allow_nan=False`, so a run that produces an unexpected NaN stops instead of writing an
unreadable archive.

## 3. Migration, and how it was done

Through the producers, not by editing the archive: `sid_core.py` and `sid_run7.py` were changed
and rerun from a clean clone, and their outputs installed. The former invalid artifacts remain
in git history under the import tag.

Verification:

- `res1_core.json` — exactly four `null`s, at the declared positions F[0][8], F[0][9], F[1][8],
  F[1][9]. Every finite value is **bitwise identical** to the previous archive (maximum relative
  deviation 0). That copy was itself generated in this environment when key A2 was added, so the
  rerun reproduces it exactly; only the four undefined entries changed representation. The
  "Mean of empty slice" warnings the old code emitted are gone, and section F now prints
  `mid-fringe delay=undefined+-undefined ... [runs 60,0]`, which states the fact the NaN hid.
- `res7B_servo.json` — no nulls; the last row's κ carries `"positive-infinity"`. Finite values
  agree with the pre-migration archive to a maximum relative deviation of **6.9 × 10⁻¹³**, not
  bitwise: that archive predates the environment available here, so a producer rerun cannot
  reproduce it exactly, and the deviation is reported rather than asserted away. Against the
  intermediate null-valued version, every other value is bitwise identical.

## 4. Record

`analysis/outputs/SCHEMA.md` now opens with the representation rule and documents both null
positions and their meanings. `tests/test_output_schema.py` enforces, over **every**
`analysis/outputs/*.json`:

- no `NaN`, `Infinity` or `-Infinity` token in the raw bytes (read as text, because `json.load`
  would silently accept the tokens under test);
- the file round-trips through `allow_nan=False`;
- no parsed value is non-finite;
- every `null` is one of the positions `SCHEMA.md` declares, with the expectations written out
  rather than derived from the file under test — an expectation computed from the data cannot
  fail (rule 4) — and guarded by a row-count check so a reshaped file cannot quietly satisfy
  stale positions.

The third `null`-bearing file, `res2_partial.json`, was already valid JSON and is unchanged; its
nulls are the three columns never stored after the figure crash, and are now declared rather
than merely described in prose.
