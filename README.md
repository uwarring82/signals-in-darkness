# Signals in Darkness — operating-point crossover in sequential quantum-clock detection

**Status (4 Sept 2026):** card v1.1 frozen; card v2.0 seed open; repository imported and tagged `archive-2026-09-03`. The whole analysis path has been run once in the pinned environment (`notes/2026-09-04-note-07-pinned-certification.md`); claims C09, C11, C12, C19 and C20 remain **open**, and C01, C15, C17, C18 and C22 are withdrawn.
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
# whole path ~35-72 min on one core, observed over three runs of the certified platform.
# Runtimes vary strongly with sustained system load; see the note under this block.
python sid_core.py        # sections A–F, ~6 min
python sid_run2.py        # mid-fringe comparator, ~2.5 min; writes res2_partial.json, which run3 needs
python sid_run3.py        # spectral comparator, exact-comparator tau-optimised map (~20 s)
python sid_run4.py        # geometric-fit vs sinh-series check (~7 min)
python sid_run5.py        # calibrated-ARL delay comparison (~5 min)
python sid_run7.py        # identifiability and servo tables (~10 s)
python sid_run6s.py "cal:oracle-mid(tc=20),oracle-mid(tc=5),oracle-mid(tc=1),extremum-only,learner-mid(bank),learner-interleave-B10(bank),learner-interleave-B1(bank)"   # ~8.5 min
python sid_run6s.py delays        # ~1 min; uses the thresholds the line above just measured
python sid_run8.py                # explore-then-switch, ~4.5-41 min (see note below)
python sid_fig_policy_delays.py   # rebuilds sid_policy_delays.png from stored outputs;
                                  # refuses to run while its inputs are withdrawn (C18)
pytest ../../tests
```
**No run script writes into `analysis/outputs/` or `figures/`.** Those hold the published archive and are opened read-only. Every producer writes into `analysis/reproduction/` (git-ignored), including its figures, so a reproduction can never overwrite the record it is being checked against, and nothing archived can silently become a computational input.

Comparison is then explicit:

- `sid_run6s.py` and `sid_run8.py` **recompute by default**, compare in-process under the tolerances declared in `analysis/lib/sid_repro.py` — thresholds exactly, means within 3σ — print `computed: N, cached: M` with seeds, runtime, revision and environment, and exit nonzero on failure. `--resume` is the only way to reuse previous state.
- `python tools/compare_reproduction.py` compares every other reproduced output against the archive under the per-file tolerances declared in that file, and exits nonzero if any exceeds them.

Nothing is adopted automatically: promoting a reproduced output into the archive is a separate, deliberate commit.

**Runtimes are indicative, not budgets.** Across three runs of the certified platform, `sid_run8.py` took between about 4.5 and 41 minutes and the full path between about 35 and 72 minutes, while returning bit-identical results each time (its delay rows agree at 0.00 sigma). Runtime depends strongly on sustained system load. The cause of the spread has not been isolated, and no telemetry was collected; the per-script figures above are the shorter end of the observed range.

The whole path has been run in the pinned environment on 4 Sept 2026: Apple M1 Pro host, macOS x86_64 **under Rosetta 2**, BLAS 3.9.0. Native arm64 is untested, and identical pins on a different architecture are a different numerical stack. What reproduced, and by how much, is in `notes/2026-09-04-note-07-pinned-certification.md`.

Scripts locate `analysis/lib` relative to their own file, so the tree can be moved or cloned anywhere; nothing needs editing after a checkout. Every reported number maps to a script, seed and output file via `analysis/seeds.md` and `ledgers/status.yaml`.

`sid_run3.py` requires the `res2_partial.json` that `sid_run2.py` writes; it reads the committed archive only under an explicit `--from-archive`. Every figure writer asserts that its file landed and is not truncated.

**Two rows of the note 03 §2 calibration table do not reproduce** and are withdrawn, along with four delay entries measured at their thresholds (claims C17–C20). **The regime map's validity overlays were withdrawn on 4 Sept 2026** and rebuilt (C22, C23): under the correct criterion the leading-order crossover is inside its own validity region only for C̄ ≈ 0.2–0.5. See `notes/2026-09-04-note-06-regime-map-overlays.md`. Before that was found, this route consumed its own committed output as cache and recomputed nothing. See `notes/2026-09-03-note-04-reproduction-defect.md`; `tests/test_reproduction_route.py` is the gate that keeps it from recurring.

## Cite
See `CITATION.cff`. Release `repo-v0.1.0` has no DOI; repository archiving is deferred to
a later release. Two licences apply, by file:

- **Apache-2.0** — `analysis/lib/`, `analysis/runs/`, `tests/`, `tools/` and repository metadata (default; follows `iontrap-dynamics` if that repository fixes a different licence).
- **CC BY 4.0** — cards, notes, labbook, ledgers, figures, references, docs and the recorded outputs in `analysis/outputs/`.

The mapping is machine-readable in `REUSE.toml`, with the licence texts under `LICENSES/`. `CITATION.cff` deliberately carries **no** `license:` field: CFF reads a list of licences as OR over the whole cited work, which would misstate this arrangement. `codemeta.json` describes the software component only and carries Apache-2.0 alone.

## Feedback
Discussions for interpretation and objections; Issues for reproduction defects, numerical errors, reference or documentation corrections (templates in `.github/`). External suggestions enter the ledger as `open`.
