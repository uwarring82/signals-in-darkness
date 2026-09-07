# Signals in Darkness

**A quantum sensor is read out one bit at a time. Where you choose to read it determines what you
can hear — and when you must raise an alarm quickly, that choice has a right answer that flips.**

This is an open evidence archive for that question. Every claim carries a status, every withdrawal
carries a reason, and every number can be recomputed from the code in this repository.

---

## Start here

**New to the subject?** Start with a coin toss. No physics required.

- **[Where we are](where-we-are.md)** — plain-language status: the question, what is established,
  what was withdrawn and why, what is still open, and what this work does not cover.
- **[Tutorial 00 — How many coin tosses?](../tutorials/00_how_many_coin_tosses.ipynb)** — how much
  evidence one binary observation carries, and why "how many samples?" is an underspecified question.
- **[Tutorial 01 — When the coin has memory](../tutorials/01_when_the_coin_has_memory.ipynb)** — two
  records with identical head counts and different ordering, and why a sensor can detect a change in
  *balance* or a change in *memory*.

The tutorials are pedagogical views. They import the project's tested functions rather than
restating them, and every conclusion in them is labelled either `worked example` — a teaching
calculation, not a claim of this project — or with a ledger claim and its status.

---

## The record

| page | what it holds |
|---|---|
| **[Status](status.md)** | every claim, its standing, its notes and its errata pointers |
| **[Roadmap](roadmap.md)** | planned work, and which items gate the next freeze |
| **[Milestones](milestones.md)** | what has been completed and when |
| **[Reproduce](reproduce.md)** | how to recompute the results from a clean copy |
| **[Feedback](feedback.md)** | how to report an error |

Labbook passes are in [`../labbook/`](../labbook/) and the technical notes in [`../notes/`](../notes/).
Each labbook entry states a question, a finding, why it matters, the resulting status, and the next
test — including the entries recording mistakes.

---

## How to read the claim statuses

- **`result`** — supported by evidence in this repository, reproducible from the committed code.
- **`pilot`** — a preliminary finding under a simplified model; not yet load-bearing.
- **`open`** — stated but not settled, or resting on something that was withdrawn.
- **`withdrawn`** — believed at some point, now known to be wrong. The original statement is kept,
  marked, and pointed at whatever replaced it.

Withdrawn claims are not deleted, and there are seven of them. Reading them is the fastest way to
understand what this project actually knows.

---

## Provenance and honesty conventions

- The pages above are **generated** from `ledgers/` by `tools/build_site.py`. Do not edit them by
  hand; a test verifies they match the ledgers.
- Prose pages such as *Where we are* are views over the ledger. Their claim identifiers and statuses
  are checked against the record by `tests/test_public_prose.py`.
- Numbers have exactly one source. A page that quotes a result points at the claim or output that
  owns it rather than restating a computation.
- Frozen cards and dated notes are never rewritten. Corrections are appended as errata, and
  superseded claims keep their original wording.

The introduction page will be the rewritten companion essay after card v2.0. The present draft in
this folder is marked NOT CANONICAL, describes several results as proposed that have since been
settled or withdrawn, predates the prior-art attribution boundary, and must not be linked from here.
