# Signals in Darkness — operating-point crossover in sequential quantum-clock detection

**Status (3 Sept 2026):** card v1.1 frozen; card v2.0 seed open; repository seed committed and tagged `archive-2026-09-03`. The reproduction acceptance criterion is **not yet met** — see `notes/2026-09-03-note-04-reproduction-defect.md` and claims C17–C20.
This README carries no thesis line until card v2.0 is frozen.

## Results hierarchy (from notes/2026-09-03-note-03a-errata.md)
1. Operating-point crossover and physical regime map — *result* at one parameter set; second parameter set open.
2. Detection-versus-identification boundary under a shape-constrained dephasing baseline — *result* (numerical), general criterion ΔΓ_φ > 2η₀Γ̂ in the fast-noise limit.
3. Extension to the independently randomised servo model via C_eff(κ) — *pilot* (supported, not proved).
4. Policy comparison — *pilot*; explicitly not an adaptive-policy or minimax result.

Claim-level status lives in `ledgers/status.yaml`. Anything on a website or in plain-language material is a projection of that ledger.

## Layout
`cards/` preregistered and frozen task cards · `notes/` dated execution notes (append-only) · `labbook/` curated public entries · `ledgers/` machine-readable status, milestones, roadmap · `analysis/` library, run scripts, stored outputs, seeds · `tests/` · `figures/` · `references/` bibliography and verification ledger · `docs/` site source · `tools/` site generator.

## Reproduce
```
conda env create -f environment.yml && conda activate sid     # or: pip install -r requirements.txt
cd analysis/runs
python sid_core.py        # sections A–F, ~5 min on one core; writes figures to figures/
python sid_run3.py        # spectral comparator, exact-comparator tau-optimised map
python sid_run5.py        # calibrated-ARL delay comparison (~4 min)
python sid_run7.py        # identifiability and servo tables (~2 min)
python sid_run6s.py "cal:oracle-mid(tc=20),oracle-mid(tc=5),oracle-mid(tc=1),extremum-only,learner-mid(bank),learner-interleave-B10(bank),learner-interleave-B1(bank)"   # ~8 min
python sid_run6s.py delays        # ~25 min; uses the thresholds the line above just measured
python sid_run8.py                # explore-then-switch, ~10 min
pytest ../../tests
```
`sid_run6s.py` and `sid_run8.py` **recompute by default** and write to `analysis/reproduction/` (git-ignored), then compare what they measured against the published archive in `analysis/outputs/` under the tolerances declared in `analysis/lib/sid_repro.py` — thresholds exactly, means within 3σ. Each prints `computed: N, cached: M` with its seeds, runtime, revision and environment, and exits nonzero if a row falls outside tolerance. Add `--resume` to reuse a partial run; that is the only way to reuse previous state. No run script writes into `analysis/outputs/`.

Scripts locate `analysis/lib` relative to their own file, so the tree can be moved or cloned anywhere; nothing needs editing after a checkout. Every reported number maps to a script, seed and output file via `analysis/seeds.md` and `ledgers/status.yaml`.

**Two rows of the note 03 §2 calibration table do not reproduce** and are withdrawn, along with four delay entries measured at their thresholds (claims C17–C20). Before that was found, this route consumed its own committed output as cache and recomputed nothing. See `notes/2026-09-03-note-04-reproduction-defect.md`; `tests/test_reproduction_route.py` is the gate that keeps it from recurring.

## Cite
See `CITATION.cff`. Content: CC BY 4.0. Code: Apache-2.0 (default; follows `iontrap-dynamics` if that repository fixes a different licence).

## Feedback
Discussions for interpretation and objections; Issues for reproduction defects, numerical errors, reference or documentation corrections (templates in `.github/`). External suggestions enter the ledger as `open`.
