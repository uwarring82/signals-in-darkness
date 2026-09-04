# FAIR implementation matrix

Binding acceptance test: every public result must be discoverable by identifier, retrievable in an open format, interpretable without private knowledge, and reusable under a declared licence.

| Principle | Implementation |
|---|---|
| Findable | `CITATION.cff`, `codemeta.json`, versioned GitHub releases, tags per frozen card/note, and claim ids in `ledgers/status.yaml`. Repository archiving and DOI assignment are deferred after `repo-v0.1.0`. |
| Accessible | Public repository; open formats only (md, yaml, json, csv, png/svg, py); release archives |
| Interoperable | Output schemas and units in `analysis/outputs/SCHEMA.md`; stable claim/run identifiers; relative links |
| Reusable | SPDX licences (Apache-2.0 code, CC-BY-4.0 content); `environment.yml` lock; `analysis/seeds.md`; provenance chain claim → run → seed → output; `tests/`; errata links |

References: Wilkinson et al., Sci. Data 3, 160018 (2016); Barker et al., Sci. Data 9, 622 (2022). Both listed in `references/verification.md` (identifier-resolved, not load-bearing).
