# Task Card — Signals in Darkness: tutorial sequence (v0.1)

**Status:** Open, 5 Sept 2026. Workstream for `repo-v0.2.0`.
**Purpose:** Give a reader with no background in sequential detection or quantum metrology a path
into the project's actual question, beginning from an elementary one and never changing
mathematical language along the way.
**Owner:** U. Warring.
**Relation to `cards/repo-seed-v0.2.md`:** that card's stopping rule places anything beyond its
commit 9 out of scope and requires a card of its own. This is that card. It adds explanatory
surface, not scientific scope.

## Why the coin toss is the front door

A single-shot quantum measurement **is** a Bernoulli observation. The coin is therefore not an
analogy that must later be discarded; it is the same object under a different name. A reader who
understands the likelihood ratio of a coin toss already possesses the machinery of the extremum
channel, and the transition to physics changes only what the probability *means*.

This is what makes the sequence honest: nothing is simplified and then corrected. The
mathematical language of notebook 00 is the language of note 01.

## Sequence

| notebook | question | introduces |
|---|---|---|
| `00_how_many_coin_tosses.ipynb` | How many tosses to detect a change in bias? | p0/p1, alpha, power, known vs unknown change time; likelihood ratio; Bernoulli divergence; exact fixed-sample binomial test; calibrated CUSUM; observations vs wall-clock; the fixed-Δp / fixed-log-odds trap |
| `01_when_the_coin_has_memory.ipynb` | What changes when the bias is an AR(1)? | the discrete counterpart of an Ornstein–Uhlenbeck process; two streams with equal head counts and different correlation; evidence carried by **balance** versus evidence carried by **memory** |
| `02_from_coin_to_quantum_sensor.ipynb` | What is the coin, physically? | the quantum binary link; contrast; the two operating points; the extremum reads contrast loss, mid-fringe reads temporal structure; the crossover appears |
| `03_detection_is_not_identification.ipynb` | When do the data justify a physical interpretation? | contrast loss is ambiguous between stochastic frequency noise and a change in T2; varying τ does the identifiability work |

Deferred, explicitly: replacing the Gaussian hidden process with jump or Lévy dynamics. It belongs
after the OU case is understood, not inside the first sequence.

## Contract — notebooks are views, never sources

A tutorial that restates a research formula becomes a second implementation that can silently
disagree with the tested one. A tutorial that presents a number without its status invites a
reader to cite an illustration as a finding. Both are forbidden.

1. **Import, never restate.** Research formulas come from `analysis/lib`. Retyping `DB`,
   `I_ext_exact`, `rk_exact` or `hmm_rate` is a test failure.
2. **Deterministic.** Every random result has a named seed defined in the notebook.
3. **Fast.** Each notebook executes top to bottom in well under a minute.
4. **Read-only against the archive.** Nothing writes into `analysis/outputs/` or `figures/`.
5. **Every conclusion labelled, in two distinct namespaces.** Each quoted conclusion opens with
   either `**worked example**` or `**C·· — status**`.
   - `worked example` — computed here for teaching using standard methods. **Not** a claim of
     this project. The label is not `textbook`: numbers like "213 tosses" or "delay 174" are not
     textbook facts, they are tutorial-local calculations, and calling them `result` would place
     them in the project's claim vocabulary — the conflation `ledgers/status.yaml` exists to
     prevent.
   - `C·· — status` — a ledger claim and its current status, both checked against
     `ledgers/status.yaml` by the tests. A tutorial number that merely *resembles* a claim does
     not inherit its standing; the two are stated as separate conclusions.
6. **Plain Python cells, executed in the tests.** No line or cell magics and no shell escapes:
   `tests/test_tutorials.py` runs the code cells directly, without a Jupyter kernel, in a
   temporary directory. It hashes `analysis/outputs/` and `figures/` before and after to prove
   nothing was written, asserts nothing is left behind, and compares the freshly produced numbers
   with those committed in the notebook — to four significant figures, so a different interpreter
   does not fail on a last digit while a stale committed output does. Lines prefixed `[env]` are
   provenance and are excluded from that comparison.
7. **Dependencies separate.** Authoring tools live in `tutorials/requirements.txt` and may not
   enter `environment.yml`. The contract tests deliberately need none of them, so the gate runs
   in the certified environment.
8. **Outputs committed.** Notebooks are stored executed, so a GitHub visitor reads them without
   installing anything.

## Work plan

1. Notebook 00, its contract tests, and this card. **← `repo-v0.2.0` scope. Done.**
2. Notebook 01 (AR(1) memory), with the equal-head-count demonstration. **Done 7 Sept 2026.**
3. Notebook 02 (the binary link and the crossover). **Deferred until roadmap B completes**, so it
   teaches the final operating-point comparison rather than an interim one.
4. Notebook 03 (detection versus identification). Follows notebook 02, and can now rest on the
   settled C26 rather than the withdrawn C13.
5. Site page linking the sequence. **Done 7 Sept 2026**: `docs/index.md` is a readable front page
   and `docs/where-we-are.md` is the plain-language status, both checked against the ledger by
   `tests/test_public_prose.py`.

Only step 1 was in scope for `repo-v0.2.0`. The version is set **before** certification, so the
tagged commit declares its own version — the one avoidable defect of `repo-v0.1.0`, whose
`CITATION.cff` still reads `0.0.0-seed`.

## Acceptance criteria

- Each notebook satisfies all eight contract items, enforced by tests in the certified
  environment.
- Notebook 00 ends on the question that opens notebook 01: *what changes when the coin's
  probability has a memory of previous tosses?*
- No claim in `ledgers/status.yaml` changes status because of a tutorial. If a notebook appears
  to establish something new, that is a defect in the notebook or a missing claim in the ledger,
  and is resolved in the ledger first.

## Stopping rule

The card is complete when the four notebooks exist, pass their contract tests, and are linked
from the site. Interactive widgets, a hosted execution service, video, or a second explanatory
track are out of scope and would need their own card.
