# Changelog

One line per tag, as the repository seed card requires. Tags that do not yet exist are
listed under Planned and are not claimed as history.

## Tags

- **`repo-v0.1.0`** — first certified repository release, at `d845a80`. Full analysis path
  re-run from a clean clone of that commit in the pinned environment, tree unchanged before
  and after: every stage computed afresh, 164 tests passed with none skipped, site projection
  current, strict JSON throughout, and six comparable outputs within their declared
  tolerances. The calibration gate exits nonzero by design, refusing the two rows whose
  provenance is lost (C17, C18). Certifies one platform — macOS x86_64 under Rosetta 2 on an
  Apple M1 Pro, BLAS 3.9.0; native arm64 untested. Tags the repository, not a scientific
  document.
- **`archive-2026-09-03`** — verbatim import of the handed-over working folder. Byte-identical
  to the folder as received; not a pure move, because the portability rewrite predates the
  import (`SEED_HANDOVER.md`, `cards/history/2026-09-04-repo-seed-v0.2-errata.md`).

## Unreleased (after `repo-v0.1.0`)

- C19 and C20 closed from `open` to `result`. Both carried closure conditions written before the
  pinned certification existed, and the certified run satisfied them: `res8_switch.json` was
  regenerated from computation rather than cache and agreed at 0.00 sigma, and the repaired route
  completed from a clean checkout while correctly rejecting the two unreproducible calibration
  rows (`notes/2026-09-05-note-10-certification-closure.md`). The original defect note is
  unaltered.

- Publication metadata updated for the GitHub-only release: repository archiving and DOI
  assignment are deferred, and the citation records now identify version 0.1.0. The certified
  tag remains at `d845a80`.
- Documentation only: runtimes recorded as observed ranges rather than single figures.
  `sid_run8.py` took between about 4.5 and 41 minutes across three runs of the certified
  platform, and the full path between about 35 and 72 minutes, with bit-identical results
  every time. Runtime depends strongly on sustained system load; the cause of the spread has
  not been isolated and no telemetry was collected. The tag was not moved or recreated for
  this correction.

## Before `repo-v0.1.0`

Work since the import, none of it tagged. No tag may be pushed until the certification
blockers in the notes below are cleared under a clean-checkout verification.

- Reproduction route repaired: the documented command consumed its own committed output as
  cache state and recomputed nothing. Fresh by default, explicit `--resume`, archive separated
  from checkpoints, comparison under declared tolerances, and a regression gate
  (`notes/2026-09-03-note-04-reproduction-defect.md`).
- Two archived calibration rows withdrawn as unreproducible, with four delay entries measured
  at their thresholds; C09, C11 and C12 demoted to open (C17–C20).
- C01 withdrawn: the extremum expansion's accuracy ranges were stated as contrast-independent
  and are not (`notes/2026-09-03-note-01a-errata.md`). Replaced by C21.
- Licensing declared file-scoped in `REUSE.toml`; `CITATION.cff` now validates.
- Site projection made verifiable (`build_site.py --check`); the previous freshness assertion
  could not fail.
- Stored outputs migrated to strict JSON
  (`notes/2026-09-04-note-05-representation-migration.md`).
- The principal regime map's validity overlays withdrawn and rebuilt: both drew criteria the
  ledger had already withdrawn (`notes/2026-09-04-note-06-regime-map-overlays.md`).
- Producers separated from the archive: every run script writes to `analysis/reproduction/`,
  and calibration thresholds are bound to the numerical stack that produced them.
- First reproduction of the whole analysis path in the pinned environment. Two defects only
  that path could expose, `res2_partial.json` adopted from a real run for the first time, and
  C17/C18 confirmed independently
  (`notes/2026-09-04-note-07-pinned-certification.md`).
- Comparator crossover and tau-optimised thresholds persisted (C05, C08); the two crossover
  estimators reconciled rather than ranked
  (`notes/2026-09-04-note-08-comparator-vs-hmm-crossover.md`). C06's output pointer corrected.
- Ledger invariant added and enforced: `result` and `pilot` claims require an existing
  machine-readable output; `open` and `withdrawn` may carry a documented provenance exception.
  It failed on C10 and C24. C10's table is now stored; C24 is demoted to open because no script
  in this repository produces it
  (`notes/2026-09-04-note-09-extremum-bonus-provenance.md`).
- Test dependencies pinned. Eight checks — CFF validity and the whole CITATION.cff/codemeta
  agreement guard — skipped silently in the certified environment because PyYAML and
  cffconvert were never pinned. A check that skips is not a gate.

## Planned

`card-v1.0`, `card-v1.1`, `note-03a` — retrospective tags for the frozen cards and the errata,
to be applied during the certification pass, not before.
