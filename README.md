# Signals in Darkness — operating-point crossover in sequential quantum-clock detection

**Status (3 Sept 2026):** card v1.1 frozen; card v2.0 seed open; repository seed (pre-first-commit).
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
python sid_core.py        # sections A–F, ~5 min on one core; writes figures to OUT (edit OUT at top of sid_lib.py)
python sid_run3.py        # spectral comparator, exact-comparator tau-optimised map
python sid_run5.py        # calibrated-ARL delay comparison (~4 min)
python sid_run7.py        # identifiability and servo tables (~2 min)
python sid_run6s.py "cal:oracle-mid(tc=20),oracle-mid(tc=5),oracle-mid(tc=1),extremum-only,learner-mid(bank),learner-interleave-B10(bank),learner-interleave-B1(bank)"; python sid_run6s.py delays
python sid_run8.py
pytest ../../tests
```
Scripts expect `analysis/lib` on `sys.path` (each run script inserts `/home/claude/sid`; change `SID_HOME` in `analysis/lib/sid_lib.py` and the run headers after moving). Every reported number maps to a script, seed and output file via `analysis/seeds.md` and `ledgers/status.yaml`.

## Cite
See `CITATION.cff`. Content: CC BY 4.0. Code: Apache-2.0 (default; follows `iontrap-dynamics` if that repository fixes a different licence).

## Feedback
Discussions for interpretation and objections; Issues for reproduction defects, numerical errors, reference or documentation corrections (templates in `.github/`). External suggestions enter the ledger as `open`.
