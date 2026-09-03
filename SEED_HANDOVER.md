# Seed handover — how to proceed from local disk

This folder is the pre-first-commit seed described in `cards/repo-seed-v0.2.md`. It was assembled on 3 Sept 2026 from the working outputs of three execution passes.

## What is here
- `cards/v1.0-frozen.md` — the preregistered baseline, reproduced verbatim from the frozen text of 2 Sept 2026.
- `cards/v1.1-frozen.md`, `cards/v2.0-seed.md`, `cards/repo-seed-v0.2.md`, `cards/history/` (repo seed v0.1 and the one-page scope path).
- `notes/` 01, 02, 03, 03a — unchanged from the working folder.
- `labbook/` three retroactive entries written to the contract.
- `ledgers/` status, milestones, roadmap — populated from the notes; every claim carries its status.
- `analysis/` library, eight run scripts, stored outputs, `seeds.md`, output schema.
- `tests/` analytic tests with independent expectations (run in seconds); the long Monte-Carlo checks are marked slow.
- `figures/` the seven figures from the notes plus two superseded ones (kept, labelled).
- `references/` bibliography and verification ledger.
- `docs/` site source stub; the companion introduction is included as NOT-CANONICAL.
- `tools/build_site.py` — generator with postconditions and freshness check.
- Licences from SPDX text (Apache-2.0, CC-BY-4.0).

## What is deliberately missing (owner supplies)
- The dated task-card drafts before v1.0 (six documents, 2 Sept 2026) — you hold the originals; drop them into `cards/history/` with their dates. `cards/history/scope-path.md` lists them.
- The fringe-sketch SVG referenced by the companion draft.
- ORCID, affiliation and contact fields in `CITATION.cff` / `codemeta.json` (marked TODO).
- Decision on code licence if `iontrap-dynamics` is not Apache-2.0.

## First actions (repo seed card work plan, step 1)
1. `git init`, add everything as one commit with message `archive-2026-09-03: pure move of working folder`, tag `archive-2026-09-03`.
2. Fix paths: replace `/home/claude/sid` and `/mnt/user-data/outputs` in the run scripts with repository-relative paths (`analysis/lib`, `figures/`). Do this in a second commit so the first commit stays a pure move.
3. Run `pytest tests` (fast tests) and one run script end to end to confirm the environment.
4. Continue with steps 2–9 of `cards/repo-seed-v0.2.md`.
