# Task Card — Signals in Darkness: project repository (seed v0.2)

**Status:** Seed v0.2, 3 Sept 2026 — supersedes seed v0.1 (retained in `cards/history/`)  
**Purpose:** Turn the working folder (two frozen cards, three execution notes plus errata, nine scripts, seven figures, one companion draft) into a versioned, reproducible, citable, FAIR project archive with a public labbook and a small site — *before* the paper is written and *before* card v2.0 restates the thesis.  
**Owner:** U. Warring. Location: `github.com/uwarring82/signals-in-darkness`.  
**Relation to other repositories:** the batched latent-AR(1) binary filter bank and the sinh-series spectral comparator are migration candidates for `iontrap-dynamics` (v0.7.0). They stay local through the v2.0 release candidate; migration only with independent tests, a tagged library version pinned here, and a clean reproduction confirmed identical before local copies are removed.

## Objective

A reader with the repository and a Python environment can, without contacting the author: read what was preregistered (v1.0), what changed and why (v1.1, v2.0), reproduce every number and figure cited in the notes from the recorded seeds, and see which statements are results, pilots, open items, or withdrawn.

**FAIR acceptance test (binding):** every public result must be discoverable by identifier, retrievable in an open format, interpretable without private knowledge, and reusable under a declared licence.

## One source of truth

The repository's structured records are the only evidence record. The website and the plain-language material are projections of that record, generated or linked, never parallel sources. A generated summary is never an evidentiary source. Public feedback never edits history or silently changes a result; it enters as a recorded issue or discussion and a later decision.

## Non-goals

- No general-purpose simulator; no thesis statement in the README before card v2.0 is frozen.
- No editing of frozen cards or dated notes; corrections are errata files with supersession links.
- No raw conversation transcripts in the labbook; model assistance is acknowledged, not treated as evidence.
- No web framework; no second manuscript on the site; no unfiltered activity log.

## Structure

```
signals-in-darkness/
  README.md                  status line, results hierarchy (note 03a), reproduce, cite
  CITATION.cff               formal metadata; DOI placeholder until first release
  codemeta.json              software metadata (FAIR4RS)
  FAIR.md                    implementation matrix (below)
  LICENSE                    code: same as iontrap-dynamics; default Apache-2.0 (SPDX: Apache-2.0)
  LICENSE-content            prose, cards, notes, figures, tables: CC BY 4.0 (SPDX: CC-BY-4.0)
  CHANGELOG.md               one line per tag
  environment.yml            pinned: python 3.12, numpy 2.4.4, scipy 1.17.1, matplotlib 3.10.8
  cards/
    v1.0-frozen.md  v1.1-frozen.md  v2.0-seed.md  history/ (dated drafts + one-page scope path)
  notes/
    2026-09-02-note-01.md … note-03.md, note-03a-errata.md      dated, append-only
  labbook/
    YYYY-MM-DD-<slug>.md     curated public entries (contract below), append-only
  ledgers/
    status.yaml              every claim: id, statement, status, note, run, seed, output, supersedes
    milestones.yaml          dated summaries at meaningful tags
    roadmap.yaml             the five v2.0 gating runs and their state
  analysis/
    lib/                     sid_lib.py, filter bank, spectral comparator (migration candidates flagged)
    runs/                    sid_core.py, sid_run2–8, each with header: purpose, inputs, seeds, outputs, runtime
    outputs/                 res*.json / csv with documented schemas and units
    seeds.md                 every seed behind any reported number
  tests/                     independent expectations; boundary cases; postconditions on generators
  figures/                   png (+svg), one file per figure, named as in the notes
  references/
    bibliography.bib         every citation
    verification.md          identifier, resolved-on date, checked (abstract / full text), status
  docs/                      GitHub Pages source (site pages below)
  .github/
    ISSUE_TEMPLATE/          reproduction-defect.md, numerical-error.md, reference-correction.md, documentation-defect.md
    DISCUSSION_TEMPLATE/     scientific-feedback.md (claim or run id; reasoning or evidence; reproduced anything?)
  tools/
    build_site.py            single generator: ledgers → status, milestones, roadmap pages; asserts freshness and its own postconditions
```

## FAIR.md — implementation matrix

| Principle | Repository implementation |
|---|---|
| Findable | `CITATION.cff`, `codemeta.json`, versioned releases and tags, descriptive metadata, Zenodo concept DOI plus per-release DOI from the first public release |
| Accessible | Public repository, open formats (md, yaml, json, csv, png/svg, py), persistent release archives |
| Interoperable | CSV/JSON tables with documented schemas and units, stable claim and run identifiers, relative links only |
| Reusable | SPDX licences, environment lock, recorded seeds, provenance chain claim → run → seed → output, tests, errata links |

References: Wilkinson et al. 2016 (FAIR); Barker et al. 2022 (FAIR4RS). Both enter `verification.md`.

## Labbook contract

Each public entry opens with five fields, intelligible to a physicist outside the subfield:

- **Question** — what were we trying to settle?
- **Finding** — what happened, in ordinary language?
- **Why it matters** — did it change the paper or validate machinery?
- **Status** — `result` / `pilot` / `open` / `withdrawn`.
- **Next test** — what would confirm, reject, or supersede it?

Then the technical record: scripts, commits, parameters, seeds, outputs, environment, failures, decisions. Rules: entries are chronological and append-only; current conclusions live in `ledgers/status.yaml`, not in entries; corrections are new entries with explicit supersession links; deleted artifacts receive tombstones, never silently broken links.

## Site (GitHub Pages from `docs/`)

Eight pages, no framework: Introduction (the rewritten companion essay, one canonical source, SVG shipped alongside with a relative link); Current status (generated from `status.yaml`); Milestones (from `milestones.yaml`); Results and figures (each number linked to script, seed, stored output); Labbook (entries linked to technical notes); Reproduce (one tested path from clean checkout to the reported tables); Roadmap (from `roadmap.yaml`); Feedback (the two channels, clearly separated). Generated pages carry a build date and fail the build if older than the ledger they project.

## Feedback channels

- **Discussions:** interpretation, alternative models, applications, theoretical objections.
- **Issues:** failed reproduction, suspected numerical error, reference correction, documentation defect (templates require claim or run id, reasoning or evidence, and whether anything was reproduced).
- **Pull requests:** code, tests, documentation, independently reproduced outputs.

External suggestions enter as `open`; they become `result` only after independent check and promotion through the ledger.

## Rules carried forward

1. Freeze acceptance criteria and the stopping rule before beginning iterative audits.
2. Frozen means frozen; correct through errata and superseding versions.
3. One machine-readable source of truth; human-facing views are generated from it.
4. Tests execute the relevant calculation against independent expectations; they never reread an output's description of itself.
5. Exercise thresholds at the boundary and immediately beyond it.
6. Every automated transformation asserts its own postcondition.
7. Keep the trusted machinery small: one ledger format, one generator script, no framework.
8. Separate irreversible publication failures (wrong tag, wrong DOI, leaked secret) from reversible documentation backlog.
9. Certify the object that will actually be published: clean clone, complete history, filenames, refs, tags, metadata, ignored files, secrets scan.
10. The first commit is a pure move of existing files; governance, FAIR metadata, tests, and the site follow in separate commits.
11. Machine-readable identifiers use formal values: SPDX identifiers, complete checksums, stable versions.
12. No reference without a verification line; load-bearing references require full text.

## Work plan (commits in this order)

1. Pure move of existing files; tag `archive-2026-09-03`.
2. `seeds.md`, per-script headers, `status.yaml` populated from notes 01–03a with `[unreproduced]` where a seed or output is missing.
3. `verification.md` for every existing reference; the two Sakuldee–Cywiński entries flagged load-bearing and unread.
4. Rebuild all seven figures from `analysis/outputs/` without recomputation; fix or flag.
5. Governance and metadata: README (no thesis line), `CITATION.cff`, `codemeta.json`, `FAIR.md`, licences, `CHANGELOG.md`, environment file.
6. Tests: crossover table, calibration table within stated uncertainty, identifiability table exactly; boundary cases at and beyond the validity conditions.
7. Labbook: retroactive entries for the three passes, written to the contract from the notes.
8. Site generator and eight pages; freshness test; templates for issues and discussions.
9. Tags `card-v1.0`, `card-v1.1`, `note-03a`; certification pass (rule 9).
10. Hand over to the v2.0 seed card.

## Acceptance criteria

- Clean environment reproduces the crossover table (note 01 §3), the calibration table (note 03 §2, within stated uncertainty), and the identifiability table (note 03 §4, exactly) from recorded seeds, via the documented Reproduce path.
- Every reference has a verification line; every load-bearing one is full-text or flagged.
- No frozen file differs from its tagged state; every withdrawn claim has an errata pointer.
- `status.yaml` covers every number in the notes; the site's status page is generated from it and passes the freshness test.
- The FAIR acceptance test passes for every public result.
- Certification pass complete before any tag is pushed.

## Decisions taken (owner may override)

- Licences: content CC BY 4.0; code follows `iontrap-dynamics`, default Apache-2.0.
- The current companion introduction is not the public landing page; it is rewritten once against v2.0 and note 03a; earlier drafts remain as dated history, never canonical.
- Module migration deferred to after the v2.0 release candidate, under the conditions above.
- Zenodo DOI at the first public release (concept DOI across versions), not before.

## Stopping rule for this card

The card is complete at commit 9. Anything beyond — additional site pages, automation, badges, dashboards — is out of scope and requires its own card. This adds infrastructure, not scientific scope.
