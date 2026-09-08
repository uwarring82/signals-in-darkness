# Signals in Darkness — execution note 19 (8 Sept 2026): B's pilot control fails the matched-ARL premise

Note 18 reported roadmap B as complete and promoted three claims. **The stress-point half stands.
The pilot control does not**, and the promotions were wrong. This note records why, what changed,
and one thing the investigation turned up about C17 that the record currently gets backwards.

## 1. The defect

Every delay ratio in this project divides by a benchmark, and the whole construction assumes the
policies being compared are held to the *same* false-alarm rate — matched E₀[T] ≈ 3×10⁴, within a
declared ±30 % envelope. In the fresh pilot chain two rows breach it:

| policy | h* | ARL | miss | capped null runs |
|---|---|---|---|---|
| oracle-mid(tc=20) | 4.671875 | 44 699 | **+49 %** | 4 / 64 |
| learner-interleave-B10 | 3.734375 | 47 313 | **+58 %** | 0 / 64 |

`oracle-mid(tc=20)` **is** the benchmark at τ_c/c = 20, and every worst-case ratio in the pilot
column is set at τ_c/c = 20. So the pilot control — the thing that made B's inversion a comparison
rather than a single measurement — rests on a premise that is false for the policy it divides by.

This was already documented. Note 04 §51 recorded the envelope breach; nothing enforced it. The
±30 % condition lived as a **warning inside `sid_fig_policy_delays.py`, printed after the figure had
already been drawn from the offending rows.** I also printed these two numbers myself while
assembling note 18, observed that they were "exactly the two C17-withdrawn rows", and then used the
delays built on them anyway. Fresh computation repaired provenance; it did not repair calibration,
and I treated the first as if it were the second.

## 2. Why the bisection lands high

Two errors push the same way.

The bisection probes with R = 32, whose ARL estimate carries ~15 % standard error. And null runs that
hit the 150 000-step cap contribute the cap instead of their true larger stopping time — a downward
bias that grows with h. **A probe that understates the ARL moves `lo` up.** Noise and censoring
therefore both push the bracket above the true crossing, and neither is corrected by more iterations.

Measured directly (R = 64 per point):

    oracle-mid(tc=20):        ARL(4.000) = 26 875    ARL(4.200) = 32 653
                              ARL(4.400) = 36 235    ARL(4.600) = 45 784
    learner-interleave-B10:   ARL(3.200) = 28 107    ARL(3.400) = 32 377
                              ARL(3.550) = 38 484    ARL(3.700) = 43 389

The crossings are near **h ≈ 4.15** and **h ≈ 3.3**. The bisection returned 4.672 and 3.734.

`calibrate_refined` bisects, then measures both ends of the final interval at higher replication and
interpolates ln(ARL) linearly in h — a good local model because ARL grows close to exponentially in
the threshold — then confirms. It runs under a separate `pilot_recal` profile so the archive-
reproducing path is untouched and the new numbers land in their own artifact.

## 3. What this says about C17, which the record currently has backwards

The archived thresholds withdrawn as C17 are **4.359** and **3.55**. Against the measurements above,
those give roughly **+17 %** and **+28 %** — *inside* the envelope. The documented bisection's
4.672 and 3.734 give +49 % and +58 %, outside it.

**The withdrawn values are better calibrated than the procedure that replaced them.** Separately,
the reachable outputs of the documented bisection are 1 + 5k/64 for odd k; 4.359 fits as 4.359375
truncated, but 3.55 lies strictly between the lattice points 3.421875 and 3.578125 and is not
reachable at all.

Taken together these say the withdrawn thresholds came from a **finer procedure whose record was
lost**, not from a corrupted one. That does not un-withdraw them: their provenance is still
unrecoverable, which is what C17 is about, and an unreproducible number cannot be relied upon however
good it looks. But the record should not imply the values were *wrong*, because the evidence points
the other way. C17's wording is left for the owner to decide.

## 4. Claims

- **C09** and **C11** return to `open`. Their reason is now stated as the calibration breach, not
  provenance. Closing them needs the two rows recalibrated inside the envelope and every dependent
  delay rerun.
- **C12** is `withdrawn` and superseded by **C29**. Its unqualified "no resolved penalty" is false at
  τ_c/c = 1, where both ARLs sit comfortably inside the envelope (28 854 and 27 698) and the measured
  penalty is 1.60×. C29 states that, states the 1.04× at τ_c/c = 5, and makes **no** statement at
  τ_c/c = 20 where the benchmark is +49 % off.
- **C27** is narrowed to the stress point alone. Its core is the clean anchor: switch@1000 versus
  fixed-extremum, both +13 % off target and therefore held to the same accuracy, 1.91× apart.
- **C28** is added at `open` to hold the full operating-point inversion, so it cannot be quoted from
  C27, which no longer contains it.

## 5. Two corrections to note 18's own text

"Zero capped runs anywhere" was false. Zero capped **detection-delay** runs; the calibration rows
carry 9 capped null runs at the pilot and 3 at the stress point, and their bias runs downward, so an
ARL already above target understates its miss.

And the ±30 % envelope is now a **gate** in the driver, exiting 4 and naming every breaching row,
rather than a warning printed after the fact.
