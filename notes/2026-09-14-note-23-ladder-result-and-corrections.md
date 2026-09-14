# Signals in Darkness — execution note 23 (14 Sept 2026): the ladder, a negative result, and three corrections to my own report

Roadmap C asked whether posterior-driven action selection beats precommitted scheduling. The
campaign is complete: 22 calibrations, 75 selection-stream delay cells, 75 evaluation-stream
cells, no censoring anywhere. **The answer is largely negative, and the corrections review forced
on the first write-up matter as much as the result.**

## 1. Selection, frozen before anything was evaluated

Each rung named its member from the `700 + int(tau_c)` stream alone:

| | L1 (tau_c 20/5/1) | L2 robust | L3 (tau_c 20/5/1) |
|---|---|---|---|
| pilot | mid / ext / ext | interleave-B10 | mid / ext / ext |
| stress | mid / mid / ext | switch@300 | mid / **sampling** / ext |

Two cells need care and are named in the artifact rather than left to be noticed. L3 selected
**sampling** at stress tau_c=5, which is legal — both learners are in L3's class by design, the
repair made when L3's class had held only precommitted schedules — but that cell is then not an
independent benchmark: it is the learner re-measured on held-out data. And several margins are a
fraction of a standard error: pilot tau_c=20 separates `mid` from `switch@3000` by **0.02 se**,
stress tau_c=5 separates `sampling` from `switch@1000` by **0.25 se**. Where the margin is that
small a different selection draw would routinely name a different member.

## 2. The learners' evaluation cells reproduce per replicate

All twelve learner cells reproduce `sid_run10`'s **per-replicate stopping times** exactly, at both
operating points. That was the standing condition for reusing any existing output, so the
condition is met — and since everything was re-measured uniformly anyway, it serves as
verification of the common driver rather than a saving.

## 3. The result

Against **L1**, the tau_c-knowing best fixed endpoint, posterior sampling is resolvedly slower in
five of six cells, by 19 % to 114 %. Against **L2**, the best eligible robust precommitted
schedule, the evidence is mixed: faster at two cells, slower at one, unresolved at three.

The physics shows through. L1 picks `mid` at tau_c=20 and `ext` at tau_c=1 — the crossover this
whole project is about — and a policy that must *infer* tau_c pays for the inference within the
detection horizon.

This does not contradict the action gate. Sampling converts posterior movement into changed action
probabilities and greedy does not; that was measured and stands. The preregistration had recorded
in advance that neither balance nor responsiveness implies a shorter delay. That warning is now
the finding.

## 4. Three corrections to my own reporting

Review caught three defects in the first write-up. None changed a number; all changed what the
numbers were said to support.

**The falsifier prose was reversed.** Lower delay is better, so the diagnostic envelope — a
minimum over a set that *contains* each learner — always beats or ties every learner. The
inequality is `D_envelope <= D_learner`. The artifact and the assertion had this right throughout;
the test docstring said the envelope "cannot beat a learner" and my summary repeated it, which
states the reverse. Corrected to "no learner beats the envelope".

**"The class offers nothing beyond the endpoints" was too strong.** What is established is
narrower: the independently selected L3 procedure found no robust schedule advantage, choosing
endpoints in five cells and sampling in one, with several margins inside the noise. The class is
not exhausted by what one noisy selection picked — the evaluation envelope is minimised by
`switch@3000` at stress/tau_c=20 and `switch@1000` at stress/tau_c=5. That envelope is
optimistically biased and is not a benchmark, but it is exactly what forbids the stronger claim: a
schedule *did* attain the sample minimum twice.

**Cross-policy threshold ratios do not quantify the ARL confound.** This was the substantive one.
I had argued that the calibration mismatch could explain at most ~5 % because `h_sampling /
h_benchmark` spans 0.908 to 1.052. That reasoning is invalid: different policies have different
null increment distributions, so `h` is not a common currency between them and its ratio bounds
nothing.

## 5. Closing the confound properly

The ±30 % envelope is a band, not a match. A policy with a longer null ARL is harder to trip and
detects later, so where sampling holds the longer ARL the mismatch could manufacture the negative
result. Classifying every cell by **measured** ARL splits them cleanly:

- **stress** tau_c=20/L1, tau_c=1/L1, tau_c=1/L2 — sampling holds the *shorter* null ARL, is
  easier to trip, and is still slower. The mismatch runs *against* the negative conclusion, so
  these understate the contrast.
- **pilot** tau_c=20/5/1 against L1 — sampling holds the *longer* ARL. These required measurement.

`sid_run12` measured a delay-versus-null-ARL curve for sampling at four thresholds per operating
point, with each point's own calibrated threshold included as a self-check — and that point
reproduces the frozen null ARL and all three evaluation delays exactly.

The curve is nearly **flat**: at the pilot, a 45 % change in null ARL (23 775 to 34 444) moves the
tau_c=20 delay by 3 % (1886 to 1943). Read at each benchmark's own ARL the ratios barely move:

| pilot cell | at sampling's own ARL | matched |
|---|---|---|
| tau_c=20 vs mid | 1.544 | 1.504 |
| tau_c=5 vs ext | 1.425 | 1.384 |
| tau_c=1 vs ext | 1.557 | 1.504 |

The band accounts for about 4 points of a 38-56 % gap. It has no room to manufacture a 1.5x
effect. The matched intervals also carry calibration uncertainty, which the frozen ladder
intervals did not: every ARL entering the interpolation is perturbed by its own standard error
inside each bootstrap draw.

## 6. What stands

Posterior sampling demonstrates action-level responsiveness, yet at these calibrations it is
resolvedly slower than the independently selected fixed-endpoint benchmark in five cells, and
offers mixed evidence against L2. The cost of learning tau_c is visible; responsiveness alone does
not repay it within the detection horizon.

No oracle, optimal or regret language is licensed anywhere: L4 was not attempted. L1 knows tau_c
and the learner does not, so L1 is an informed benchmark and not a fair rival — the fair minimum
bar is L2, where the evidence is genuinely mixed.
