---
layout: default
title: "Current research state"
---

# Where we are

*Plain-language status, 7 September 2026. Written for a reader with no background in sequential
detection or quantum sensing. Every claim identifier below is checked against
[`ledgers/status.yaml`](status.md) by `tests/test_public_prose.py`, so this page cannot drift from
the record without a test failing.*

*This page is a **view**, not a source. Every number lives in the ledger or an output file; nothing
is computed here. For the technical record see the [status table](status.md), the
[roadmap](roadmap.md), and the notes and labbook in the repository.*

<div class="status-grid compact" aria-label="Current claim status">
  <a class="status-card status-result" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="result">16</strong><span>supported results</span>
  </a>
  <a class="status-card status-pilot" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="pilot">1</strong><span>pilot result</span>
  </a>
  <a class="status-card status-open" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="open">4</strong><span>open claims</span>
  </a>
  <a class="status-card status-withdrawn" href="{{ '/status.html' | relative_url }}">
    <strong data-status-count="withdrawn">8</strong><span>withdrawn claims</span>
  </a>
</div>

---

## The question, in one paragraph

A quantum sensor is read out one bit at a time. Between measurements its phase drifts, and that
drift carries information about the environment you are trying to sense. You get to choose *where on
the interference fringe you read it out*, and the choice determines what you can hear: at a **dark
extremum** each bit reports how much contrast has been lost, while at **mid-fringe** each bit is a
coin flip whose *ordering* carries most of the signal — in the symmetric, zero-mean model studied
here its long-run average is fixed at one half no matter what the sensor is doing, though the
*spread* of the count still leaks a little. The question
this project asks is not which readout gives a better single measurement. It is: **when you must
raise an alarm as fast as possible, and you are held to the same false-alarm rate either way, which
readout detects the change sooner — and where exactly does the answer flip?**

That flip is real, it is quantitative, and it moves with how long the noise remembers itself.

---

## What is established

Three results carry the project. All are `result` in the ledger.

**C05 — the crossover exists and is quantitative.** For the stated binary-link model, neither
operating point is universally better. Which one detects a change faster depends on the noise
correlation time and the drift amplitude, and the boundary between them can be computed. The
*mechanism* behind this — that the two readouts respond differently — is **not** ours; it is
established in the Ramsey-noise-spectroscopy literature, and the project cites it. What is ours is
the sequential-detection boundary: the crossover locus, and how it moves.

**C23 — and the *simplified* version of that boundary knows where it stops being trustworthy.**
There are two crossover curves in play, and keeping them apart matters. C05's boundary is computed
with the **exact** comparator. There is also a **leading-order** curve — a closed-form approximation
valid only for small drift, useful because you can write it down. C23 asks the awkward follow-up
about that approximation alone: is the leading-order crossover curve itself inside the region where
the expansion producing it holds? Sometimes yes, sometimes no — valid over part of the parameter
range and not the rest. **This is a limit on the closed form, not on C05's exact map, which is
unaffected.** The kind of self-consistency test involved is not a new idea; it is the move
Ginzburg-style validity criteria make in phase-transition theory, and the project cites that
precedent rather than claiming it.

**C27 — and the best policy depends on where you stand.** Given a false-alarm budget, which
detection strategy raises the alarm soonest in its *worst* case is not a fixed answer. At the first
operating point the simple fixed choice — always read at the dark extremum — wins, and no hedging
schedule beats it. At a second point it loses badly, and four of five hedges beat it, the best by
nearly a factor of two. That second point is the part that is established; whether the *first*
point really behaves the other way is still open, because one strategy there is mis-tuned. What makes this more than a numerical curiosity is the cleanest pair in it:
two strategies calibrated to the *same* accuracy, 1.9× apart. A caution the record insists on: every
schedule tested was **fixed in advance**. None of them watches the data and decides what to do next.
So this says that committing to a robust schedule pays where a single fixed choice does not — it
does not say that learning-on-the-fly works, which remains untested.

**C26 — detecting a change is not the same as explaining it.** Suppose contrast is falling. That
could be new frequency noise, or it could be that the qubit's coherence time has simply got worse.
Telling those apart is a strictly harder problem than noticing the change. C26 states when the data
can and cannot separate them, in a form that carries no units: it depends on the ratio of the extra
dephasing rate to the calibration uncertainty.

How hard it gets depends on what you are willing to assume about the unknown baseline. Against a
**broad class** — a baseline free to wander anywhere inside an uncertainty band at each interrogation
time — the answer really is **exactly zero** over part of the range: those data cannot separate the
two explanations at all, and no amount of averaging helps. Against a **shape-constrained class** —
a baseline restricted to a simple parametric form — a small amount of information survives, so the
question becomes answerable but slow. The distinction is not a technicality: one says impossible, the
other says expensive.

Supporting these are the model's closed forms (C02, C03, C04, C07, C08, C21), the endpoint result
that says only the two extreme readout angles are worth considering (C06), and the reproducibility
results (C19, C20). C10 and C25 concern how well the theory predicts actual detection delay.

---

## What was corrected or withdrawn

Eight claims are `withdrawn`. The project treats this as ordinary, and none of them was withdrawn
because someone else pointed it out.

- **C01** claimed an accuracy bound that held regardless of contrast. It does not — the error
  depends strongly on contrast. Replaced by **C21**, which states the dependence.
- **C13** said a certain method retains *exactly zero* information throughout a whole regime. It is
  genuinely zero over most of that regime, but not at its boundary under the tightest calibration
  assumption, where a small nonzero amount survives. Exact zero would mean the question is
  unanswerable there; a small number means it is answerable but slow. Those are different scientific
  statements, and stating the second as the first is an error of kind rather than of magnitude, so
  C13 was withdrawn rather than edited and replaced by **C26**.
- **C15** reported a correlation effect that turned out to be Monte-Carlo noise. **C24** is the
  open attempt to bound whatever real, much smaller effect remains; it has not yet succeeded.
- **C17 and C18** are calibration thresholds and the delay measurements built on them, withdrawn
  because they could not be reproduced. Everything that depended on them is marked.
- **C22** withdrew two figure overlays that overstated where the theory was valid.
- **C16** withdrew a scaling argument from an early draft.
- **C12** said a mixed-model detector paid no measurable price against one that already knew the
  answer. At the shortest correlation time it pays **1.60×**, and that measurement is made where
  both detectors *are* properly matched, so it is not a quibble about tuning. Replaced by **C29**,
  which says where the claim holds and, just as importantly, where it declines to say anything.

Two further corrections did not need a withdrawal. A published comparison quoted the wrong one of
two similar formulas, and now quotes the right one (C25). And the correlator at the heart of the
mid-fringe channel was found to be already published; C02 now says so and confines the project's
contribution to what it does with it.

---

## What remains open

**Roadmap items.** **G** replaces a mutable global variable holding the operating point with an
explicit, serialised configuration. This is **provenance-critical**, not housekeeping: while the
operating point lives in a mutable global, a stored result does not carry the parameters it was
computed at, and a checkpoint cannot refuse to be reused under the wrong ones. Two claims have
already been withdrawn over calibration whose provenance could not be established, and G is what
stops that recurring. **B** then adds a second operating point — a deliberate upper-bound stress
test at the parity ceiling, not a realistic setting. **F** checks the comparator against an exact
treatment of a subtlety in the noise model: the phase accumulated over a finite measurement window
is not quite the simple process the simulator assumes. F is not expected to move any published
number, but it has not been run, so that expectation is not a guarantee; what it certainly gates is
how strongly the manuscript may word one claim.

**Open claims.** **C09**, **C11** and **C28** turn on comparisons made at one particular noise
correlation time, and at that setting one of the strategies being compared is not actually being
held to the agreed false-alarm rate — it raises far fewer false alarms than intended, which makes it
look slower than it is. Until that is recalibrated, those comparisons are not like-for-like and the
claims stay open. **C24** concerns a small extra correlation effect whose proposed ceiling is not yet established. Re-running the whole pilot chain did
remove a *different* problem — every ratio used to divide by a number that had been withdrawn — but
repairing where a number came from is not the same as repairing how well it was tuned, and only the
first was fixed. **C24** concerns a small extra correlation effect in the extremum stream. Its proposed ceiling of
6 %, in the high-contrast long-correlation corner only, is **not yet established** — the claim is
open, so the effect is at present unbounded rather than bounded. **C14** remains `pilot`: it holds in a
simplified servo model only.

---

## What this work does not cover

- **Jump and Lévy-type noise.** Everything here assumes the hidden drift is Gaussian and
  exponentially correlated. Noise that arrives in discrete jumps — a common situation in real
  devices — is deliberately out of scope, and the conclusions should not be transferred to it.
- **Platform-specific claims.** No result here says anything about a particular ion, atom,
  superconducting qubit or NV centre. The model is a binary readout with a hidden drifting phase.
  Mapping it onto a real apparatus requires calibration work this project has not done.
- **Experimental demonstration.** Nothing here has been run on hardware.
- **Generality across operating points.** The policy and delay comparisons rest on a single
  operating point. B narrows this specifically: it adds one further point inside the same
  parity regime, for the finite-γ policy and delay comparison. That is a second data point, not a
  demonstration of generality, and it does not touch the identifiability result or the physical map,
  which are established on their own terms.

---

## Lessons from the work

These were earned by getting things wrong here, not imported from a methodology text.

**A skipped check is not a gate.** A test that silently skips because an optional dependency is
missing reports success. Eight metadata checks were inert in a green pre-certification test run, and
one of them would have failed. A suite's skip count is part of its result.

**Reproducing a value does not recover its provenance.** One archived file was independently
regenerated and matched to the last digit. That established the number was right. It did *not*
establish how the original file came to exist, and that remains unknown. The two questions are
separate and were kept separate in the record.

**Test the documented route, not a convenient one.** The reproduction instructions were correct and
the code passed its tests, yet following the instructions from a clean copy recomputed nothing — the
route silently consumed its own committed output as a cache. No test failed, because no test ran the
route as written.

**Matching optimiser starts do not establish correctness.** Three numerical searches agreeing to
within 0.1% sounds like convergence. On five rows here, all three agreed closely and all three were
wrong, one by 9.7%, and a deterministic grid search found the better answer. Agreement between
methods that share a blind spot is not evidence.

**"Zero information" and "very little information" are different statements.** One says a question
cannot be answered; the other says it can be answered slowly. A claim was withdrawn rather than
edited over exactly this distinction, because tightening a number in place would have hidden a change
of kind behind what looked like a change of degree.

---

## Where to go next

- **[The tutorial sequence](../tutorials/)** — starts with a coin toss and no physics.
  [Notebook 00](../tutorials/00_how_many_coin_tosses.ipynb) asks how many tosses it takes to notice a
  change; [notebook 01](../tutorials/01_when_the_coin_has_memory.ipynb) asks what changes when the
  coin remembers.
- **[The status table](status.md)** — every claim, its standing, and its errata.
- **[The roadmap](roadmap.md)** — what is planned and what gates what.
- **[Reproduce](reproduce.md)** — how to recompute the results yourself.
- **[Feedback](feedback.md)** — corrections are welcome, and the record shows they get acted on.
