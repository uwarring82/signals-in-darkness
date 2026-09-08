# Signals in Darkness — execution note 21 (8 Sept 2026): the right estimator, and four things it exposed

Note 20 reported roadmap B's comparison using marginal error propagation. Review identified four
problems: an ungated calibration breach, an incomplete calibration identity, three wrong provenance
pointers, and a significance calculation that ignored both the pairing between policies and the
selection bias of a maximum. All four were real. This note records the corrected result and the
defects found on the way, two of which I introduced myself while fixing the others.

## 1. res8 was never gated

`switch@300` at the pilot calibrates to ARL 40 708, **+35.7 %**, outside the declared ±30 %
matched-ARL envelope. It went unnoticed because **nothing checked it**: `sid_run8.py` had no
envelope gate at all, and the ledger invariant added on 8 September matched only
`res6_policies*.json`. Every switch row in the archive has been ungated since the file existed.
Meanwhile C11 quoted that policy's ratio and asserted "all rows inside the envelope".

Both are fixed — `sid_run8` gates and exits 4, the invariant walks `res6` **and** `res8` — and
extending it immediately caught **C19**, which rests on `res8_switch.json` and had never disclosed
the breach either.

**`switch@300` is excluded, not repaired.** Three successive methods failed to bring it inside:
bisection +35.7 %, secant +38 %, secant without early stop **+52.4 %**. The third made it worse.
Its two secant anchors sit close together and both above target, so the slope estimate is dominated
by noise and extrapolates the wrong way. From measurements of my own — ARL 40 708 at h = 3.734 and
45 719 at h = 3.8125 — the crossing is near h ≈ 3.53, so the target is reachable and the *search* is
what fails. Tuning a root-find against one policy's noise realisation would produce a procedure that
works on the case I tested and nothing else, so it is disclosed and excluded instead.

A genuine bug was fixed on the way: the secant **stopped as soon as one `confirm_R` probe landed
inside the envelope**. At `confirm_R` the ARL estimate carries ~11 % standard error, so a lucky
probe ended the search while the `2*confirm_R` confirmation fell outside. Both calibrators now run
every step and take the h whose measurement is nearest the target in log space.

## 2. The estimator

The headline statistic is, per policy, the **maximum** over τ_c ∈ {20, 5, 1} of (its mean delay) /
(the best fixed-endpoint benchmark at that τ_c). Marginal propagation gets two things wrong, in
opposite directions.

**Pairing.** Policies measured at one τ_c in `res6` share a seed (`200 + int(τ_c) + offset`), so
replicate *i* of every policy sees the same noise realisation. Their delays are positively
correlated and a difference between them is measured far better than marginal errors imply —
marginal propagation **overstates** the uncertainty of a difference. The switch policies in `res8`
use `500 + int(τ_c) + offset`, so they are **not** paired with the benchmark they divide by, and a
bootstrap that resampled everything jointly would credit them with pairing they do not have.

**Selection.** A maximum of three noisy ratios is biased upward, and the bias does not cancel
between two policies whose worst case falls at different τ_c.

`tools/paired_bootstrap.py` resamples replicate indices with replacement, jointly within each source
and independently between them, and recomputes the benchmark, the ratios and the maximum inside
every draw. It requires per-replicate stopping times, which `delay_of` now returns and both drivers
store.

## 3. The corrected result

**Pilot (recalibrated), 20 000 draws.** Fixed-extremum 1.63 [1.33, 2.01].

| policy | worst case | difference | verdict |
|---|---|---|---|
| interleave-B1 | 1.60 | +0.03 [−0.36, +0.39], P = 0.550 | not resolved |
| interleave-B10 | 2.02 | −0.39 [−0.92, +0.11], P = 0.066 | not resolved |
| switch@1000 | 2.55 | −0.92 [−1.58, −0.29], P = 0.002 | **resolved worse** |
| learner-mid | 6.98 | −5.35 [−7.77, −3.46] | resolved worse |

**C11 stands.** No hedge is resolvedly better at the pilot.

**Stress point.** Fixed-extremum 2.88 [2.20, 3.83].

| policy | worst case | difference | verdict |
|---|---|---|---|
| switch@1000 | 1.51 | +1.37 [+0.55, +2.18], P = 1.000 | **resolved better** |
| interleave-B1 | 1.87 | +1.01 [+0.20, +1.62], P = 0.994 | **resolved better** |
| interleave-B10 | 2.01 | +0.87 [+0.22, +1.55], P = 0.996 | **resolved better** |
| switch@300 | 2.19 | +0.69 [−0.02, +1.49], P = 0.971 | not resolved |
| learner-mid | 4.95 | −2.07 [−3.69, −0.57] | resolved worse |

**C27 is corrected upward: three of five, not two.** `interleave-B10` was 1.9 σ under marginal
propagation and resolves under the bootstrap — the pairing effect outweighing the selection penalty.
This is the third count for that claim: "four of five" counted point estimates, "two of five" used
marginal propagation, and three is what the paired estimator gives.

**C28 survives with the better estimator.** `switch@1000` reverses with both directions resolved:
P(better) = 0.002 at the pilot, P(better) = 1.000 at the stress point.

## 4. Two regressions I introduced while fixing the others

**I destroyed the published stress calibration.** `--thresholds=archive` writes a state whose `cal`
block is empty, and I copied that over `res6_policies_stress.json` — seven calibration rows and the
run identity replaced by delays alone. Restored from git, and the per-replicate runs then *merged*
after verifying every mean, standard error and capped count matched to 1e-9, so the original
revision `5ea5806` and run `ecc6ffad55ad` survive. Overwriting an archive with a partial re-run is
exactly what the read-only discipline exists to prevent.

**And `res8_switch_stress` recorded `+dirty`**, run with an uncommitted tool in the tree. Fourth
occurrence in three days. Re-run from clean `06624d7` and merged the same verified way.

## 5. Also in this pass

C17 clarified in place, status and subject unchanged, in the owner's words: later refined
calibration produced thresholds within about 2 % of the archived values, and C17 remains withdrawn
because their producing procedure cannot be recovered, not because subsequent computation
contradicts the values. The policy figure is rebuilt from the recalibrated chain with `switch@300`
dropped and named in its output; the previous version is marked withdrawn. Calibration identity now
carries `method`, `confirm_R`, `max_secant`, `arl_envelope` and the secant seed schedule. Provenance
pointers repaired on C11, C28 and C29.
