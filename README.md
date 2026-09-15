# Signals in Darkness — operating-point crossover in sequential quantum-clock detection

**Status (15 Sept 2026):** [card v2.0 is frozen](cards/v2.0-frozen.md), identified by the
annotated `card-v2.0` Git tag. Roadmap B (second operating point), C (posterior-driven action
selection) and E (dimensionless identifiability) are complete.
**D and F remain open; C24 is the sole open claim.** The ledger contains 22 results, one pilot
and eight withdrawn claims. Posterior sampling responds to the data but does not deliver a
consistent detection-delay advantage (C30–C32). See [`ledgers/status.yaml`](ledgers/status.yaml)
and [`ledgers/roadmap.yaml`](ledgers/roadmap.yaml) for scope and qualifications.

Release [`repo-v0.1.0`](https://github.com/uwarring82/signals-in-darkness/releases/tag/repo-v0.1.0)
was certified at commit `d845a80` by a clean-checkout run of the whole analysis path in the pinned
environment; C19 and C20 closed on that evidence
(`notes/2026-09-05-note-10-certification-closure.md`). That certification applies to that release,
not automatically to later work. No DOI is claimed for it.

In the calibrated binary-readout/OU model, contrast loss and temporal correlation exchange
their information-rate advantage as noise memory changes. Identifying the physical cause
additionally depends on the admissible baseline and interrogation-time scan.

## Current results
1. Operating-point crossover — *result* at C̄ = 0.4 under the stated comparator (C05), with the τ-optimised physical map (C08) and a separate validity check for the leading-order boundary (C23).
2. Detection-versus-identification boundary — *result* (C26), distinguishing a pointwise uncertainty band from a shape-constrained baseline; ΔΓ_φ > 2η₀Γ̂ is necessary but not sufficient for class-A separation on the finite scan.
3. Extension to the independently randomised servo model via C_eff(κ) — *pilot* (C14, supported, not proved).
4. Finite-delay comparisons at two parameter sets — *results* for the specified precommitted schedules (C11, C27–C28) and posterior-driven policies (C30–C32); no global optimality or oracle result is claimed.

Claim-level status lives in `ledgers/status.yaml`. Anything on a website or in plain-language material is a projection of that ledger.

## Start here

The **[project website](https://uwarring82.github.io/signals-in-darkness/)** presents the current
research state in plain language and renders the tutorial notebooks with their committed figures
and numerical outputs.

New to the problem? [`tutorials/00_how_many_coin_tosses.ipynb`](tutorials/00_how_many_coin_tosses.ipynb)
begins with a coin and an elementary question — how many tosses to detect a change in its bias? —
and arrives at the project's own machinery without changing mathematical language. A single-shot
quantum measurement *is* a Bernoulli observation, so the coin is not an analogy. The notebooks are
committed with their outputs and read on GitHub without installing anything; see
[`tutorials/`](tutorials/README.md).

Executed drafts now continue through
[`02 — From coin to quantum sensor`](tutorials/02_from_coin_to_quantum_sensor.ipynb) and
[`03 — Detection is not identification`](tutorials/03_detection_is_not_identification.ipynb).

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
