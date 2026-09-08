---
layout: default
title: "Signals in Darkness"
---

# Signals in Darkness

**A quantum sensor is read out one bit at a time. Where you choose to read it determines what you
can hear — and when you must raise an alarm quickly, that choice has a right answer that flips.**

This is an open evidence archive for that question. Every claim carries a status, every withdrawal
carries a reason, and **every active `result` and `pilot` number can be recomputed** from the code in
this repository. That qualification is deliberate: one withdrawn historical table cannot be
reproduced, and its provenance is irrecoverable. It is kept, marked, and depended on by nothing.

---

## Current research state

<div class="status-grid" aria-label="Current claim status">
  <a class="status-card status-result" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="result">19</strong><span>supported results</span>
  </a>
  <a class="status-card status-pilot" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="pilot">1</strong><span>pilot result</span>
  </a>
  <a class="status-card status-open" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="open">1</strong><span>open claim</span>
  </a>
  <a class="status-card status-withdrawn" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="withdrawn">8</strong><span>withdrawn claims</span>
  </a>
</div>

The central result is a quantitative crossover: depending on how long the hidden noise remembers
itself, either contrast loss or temporal correlation can reveal a change sooner. The project has
also established where its simplified boundary ceases to be trustworthy, and when detecting a
change is easier than identifying its cause. The finite-delay policy comparison remains open and
is now moving to a second operating point.

**[Read the plain-language research state →](where-we-are.md)**

---

## Learn through the coin

**New to the subject?** Start with a coin toss. No physics required.

- **[Tutorial 00 — How many coin tosses?](tutorials/00-how-many-coin-tosses.md)** — how much evidence
  one binary observation carries, and why “how many samples?” is an underspecified question.
  [Notebook source](../tutorials/00_how_many_coin_tosses.ipynb).
- **[Tutorial 01 — When the coin has memory](tutorials/01-when-the-coin-has-memory.md)** — two records
  with identical head counts and different ordering, and why a sensor can detect a change in
  *balance* or a change in *memory*. [Notebook source](../tutorials/01_when_the_coin_has_memory.ipynb).
- **[Browse the tutorial sequence](tutorials/index.md)** — readable pages with the committed figures
  and numerical outputs visible, while calculation code stays available on demand.

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

Withdrawn claims are not deleted, and there are eight of them. Reading them is the fastest way to
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
