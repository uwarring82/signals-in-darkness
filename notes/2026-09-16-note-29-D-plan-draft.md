# Signals in Darkness — note 29 (16 Sept 2026): roadmap D plan — DRAFT for review

**Status: DRAFT.** No four-outcome calculation with a correlated residual has been run, and this
note changes no claim. D is non-gating (`ledgers/roadmap.yaml`: `gates_freeze: false`) and bears on
one claim, **C14**, which is a `pilot` in the servo appendix. The note states what D is, what
already exists, one structural problem with the obvious implementation, and the decisions I need
from you before writing any code.

## 1. What D is

From the seed card §D, restated in the frozen card:

> One calculation of the four-outcome likelihood with a correlated oscillator residual (AR(1)
> phase, one correlation time) to size the effect on the mid-fringe channel; if it moves C_eff by
> more than the 2 % tolerance at the operating κ, the exclusion in item 3 is stated with that
> number.

So D is bounded: one calculation, one correlation time, and its only product is either a
confirmation of the existing exclusion or a number to put in it.

## 2. What exists

**The only four-outcome code in the repository** is inline in
[`analysis/runs/sid_run7.py`](../analysis/runs/sid_run7.py) §B, lines 59–121:

- `C1 = C2 = 0.9`; the oscillator phase is a von Mises variable on a 4000-point grid (`vm`, :64).
- `four_outcome(eps, kappa, ph1, ph2)` (:67) marginalises that phase **per shot**, independently.
- The slope channel is a Fisher information by central difference, `d = 1e-4` (`fisher`, :77).
- The variance channel is the KL of a **white** Gaussian phase modulation, `ssq = 0.3²`, on a
  41-point grid (`var_channel`, :81).
- `C_eff` is inferred by inverting the binary-link divergence: `brentq` on
  `I_ext_exact(c, 0.3) = KL` (`ceff_from_kl`, :94).
- A 13×13 phase-offset grid, κ ∈ {0, 0.5, 1, 2, 5, 10, 30, ∞}, written to `res7B_servo.json`.

**C14** (`ledgers/status.yaml`, `pilot`): both channels reduce to the binary-link form with matching
effective contrast within 2 %, and C_eff > 0.8 needs κ ≳ 5 at C̄₁ = C̄₂ = 0.9. Erratum E5 of note
03a already records that this used independent phases, small modulation and a coarse phase grid.

**What does not exist:** no four-outcome code in `analysis/lib/`, no test over any of it, no D
plan, protocol, artifact or claim id, and no correlated oscillator phase anywhere in a servo model.
The repository has a mature correlated-latent-phase machinery (`sid_lib.make_hmm`, `sid_arma`) and a
mature four-outcome calculation, and they have never been joined. That join is D.

## 3. The structural problem with the obvious implementation

With an independent phase per shot the record is i.i.d., and a single-shot KL or Fisher information
is the whole answer. **With an AR(1) oscillator phase it is not.** The phase becomes a latent
correlated state, so the four-outcome record is a hidden-Markov process and the quantity that
answers D is a per-shot information **rate**, not a single-shot divergence. Marginalising a
correlated phase shot by shot, as `four_outcome` does, would keep exactly the independence
assumption D exists to test, and would report a number that looks like an answer.

That makes D structurally the same problem as F, one channel over: a latent correlated phase, an
exact emission law, and a rate that needs either a grid filter over the latent state with Monte
Carlo over records, or a deterministic small-signal (Fisher-rate) treatment.

**A second confound.** The current variance channel treats the *signal* as white while D makes the
*oscillator* correlated. Note 03 already warns that a correlated common-mode residual "mimics the
signal's correlation channel". If both are correlated with comparable times, the two are not
separately identifiable from the rate alone, and D must either separate them by design (distinct
correlation times) or state the confound as a limit on what the number means.

**Third, the finite-window caveat.** `rho_1 = F(u)·exp(−c/τ_c)`, so an AR(1) reduction of a
windowed phase is exact only as τ/τ_c → 0. D's spec says "AR(1) phase". Either D assumes a
point-sampled oscillator residual explicitly, or it inherits F's finite-window caveat.

## 4. Decisions I need before writing code

| # | Decision | Options and my recommendation |
|---|---|---|
| 1 | **The operating κ** | Nothing in any card, ledger or manifest designates one; the 2 % tolerance has no κ attached. Recommend κ = 5, the value C14's own statement uses, with κ = 10 as a sensitivity point. |
| 2 | **Correlation time** | One value, per the spec. Recommend a shot-to-shot AR(1) coefficient ρ chosen to be clearly distinguishable from the signal channel (decision 3), reported as both ρ and τ_osc in shots. |
| 3 | **Signal model** | Keep the variance channel's white signal (clean separation, matches C14's construction), or make the signal correlated too (realistic, confounded). Recommend keeping it white for D's bounded question, and stating the confound explicitly. |
| 4 | **What C_eff means under correlation** | Keep run7's convention — invert the binary-link divergence at s = 0.3 — applied to the *rate* rather than the single-shot KL, so the number stays comparable with C14. |
| 5 | **Method** | (a) Fisher-information rate for small ε, deterministic, cheap; (b) grid filter over the latent phase with Monte Carlo over records, exact but needing F's precision apparatus. Recommend (a) as the answer, with (b) at one point as a check, if its cost is acceptable. |
| 6 | **Gates** | Mirror F at lower weight: D0 this plan, D1 implementation with tests, D2 the calculation and C14's disposition. A frozen protocol file is probably overkill if the method is deterministic. |
| 7 | **Library extraction** | The four-outcome code is untested and inline in a run script. Recommend extracting it to `analysis/lib/` with tests as part of D1, leaving `sid_run7.py` and `res7B_servo.json` untouched. |
| 8 | **Tolerance** | "2 %" is not defined as absolute or relative, nor against which channel. Recommend relative, on the smaller of the two channels' C_eff, stated explicitly. |

## 5. What D will and will not settle

D sizes one effect at one correlation time and one κ. It cannot establish the servo reduction in
general, and a null result does not promote C14 beyond `pilot`. If the effect exceeds the
tolerance, the appendix's exclusion gains a number; if it does not, the exclusion stays as it is
with the calculation cited. Either way the claim ledger records the correlated case as tested at one
point only.

## 6. Cost

Not measured. Decision 5(a) is a deterministic calculation over a phase grid and should be seconds
to minutes; 5(b) inherits F's sampling problem and needs a cost estimate before it is approved.
No compute has been spent on D.
