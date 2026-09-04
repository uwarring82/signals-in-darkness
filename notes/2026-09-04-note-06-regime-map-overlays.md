# Signals in Darkness — execution note 06 (4 Sept 2026): the regime map published two withdrawn validity criteria

`figures/sid_regime_map.png` is the principal figure of the crossover result. Both of its
validity overlays were drawn from criteria the record had already withdrawn, and both errors
ran the same way: they made the leading-order expansion look valid over far more of the map
than it is. The figure as published before this date is **withdrawn**; the rebuilt version
carries corrected overlays and stores the grids it is drawn from.

Nothing about the exact calculations changes. What changes is where the map says the
*leading-order* curve may be believed.

## 1. Mid-fringe overlay — a criterion withdrawn eleven days earlier

`sid_core.py` section E contoured `pert_mid = C̄⁴ s⁴ Σa_k²` at 0.3, and legended it as the
mid-fringe expansion's validity boundary. That is the v1.0 box which `ledgers/status.yaml`
records as **withdrawn** under C03, and which note 01 §2b calls "the wrong parameter". Card
v1.1 replaced it with the spectral perturbation δ(0) = 2 Σ r_k, using the exact
r_k = C̄² e^{−s²} sinh(s² a^k).

At the reference point C̄ = 0.4, s = 0.5 the two disagree by a factor of about 70:

| criterion | mid-fringe validity boundary |
|---|---|
| drawn on the figure (withdrawn C03 box) | τ_c/c = **376** |
| card v1.1, δ(0) = 0.3 | τ_c/c = **5.29** |
| the crossover the same figure draws | τ_c/c = 4.65 |

The consequence is not cosmetic. Under the correct criterion the crossover curve lies inside
the region where its own expansion is valid only in a narrow band of contrast:

| C̄ | δ(0) = 0.3 at τ_c/c | crossover at τ_c/c | crossover within validity? |
|---|---|---|---|
| 0.05 | outside the plotted range | 201.5 | — (both off-scale) |
| 0.20 | 19.69 | 14.00 | yes |
| 0.40 | 5.29 | 4.65 | yes |
| 0.50 | 3.55 | 3.57 | on the boundary |
| 0.70 | 2.03 | 2.89 | **no** |
| 0.90 | 1.39 | 4.17 | **no** |
| 0.995 | 1.21 | 51.62 | **no** |

So for C̄ ≳ 0.5 the drawn crossover is a leading-order curve evaluated outside leading-order
validity. The withdrawn overlay concealed exactly that, by placing the boundary two decades
too high. This does not refute the crossover — the exact-comparator map
(`sid_regime_map_tau_optimised_exact.png`, `sid_run3.py`) is the one that carries C08 — but the
leading-order panel must not be read as validated above C̄ ≈ 0.5.

## 2. Extremum overlay — the bound withdrawn as C01

The figure contoured `s² C̄/(1−C̄²) = 0.3`, i.e. q = 0.3 in the notation of note 01a. That is
the uniform accuracy bound withdrawn as C01 yesterday: q does not fix the relative error
without also fixing a contrast range.

Contouring the *exact* error I_LO/I_exact − 1 at s = 0.5 instead gives a blunter picture:

- the minimum over the whole contrast axis is **13.2 %**, at C̄ = 0.05;
- **6 % accuracy is not attained anywhere on this map**;
- 20 % is reached at C̄ = 0.6705, and 50 % at C̄ = 0.9110, rising to 462 % at C̄ = 0.995.

The old overlay implied a comfortable valid region to its left. There is none: at s = 0.5 the
extremum leading-order expansion is nowhere better than about 13 % on this figure. The rebuilt
version draws the declared exact-error levels and states the floor in the legend.

## 3. What changed in the producer

- `delta0()` computes δ(0) in closed form. Σ_k sinh(x a^k) = Σ_m x^{2m+1}/(2m+1)! ·
  a^{2m+1}/(1 − a^{2m+1}), so the lag sum closes in eight terms rather than being truncated;
  verified against direct summation to 2.6 × 10⁻¹⁶ relative over C̄ ∈ [0.2, 0.99],
  τ_c/c ∈ [0.2, 200].
- The extremum overlay contours the exact error at declared levels; a level not attained on the
  axis is reported as such rather than drawn.
- The title states that the crossover is drawn beyond mid-fringe validity wherever it lies above
  the dashed curve.

## 4. Grids stored (work-plan step 4)

`analysis/outputs/res1_core.json` gains key `E`: the C̄ and τ_c/c axes, the crossover curve, the
δ(0) = 0.3 boundary as (C̄, τ_c/c) pairs, the exact extremum error along the contrast axis, the
declared error crossings, and the error floor. The boundary is stored only where it falls inside
the plotted range — 394 of 400 contrasts — and the 6 omitted are counted in
`delta0_boundary_omitted` rather than dropped silently.

## 5. Two adjacent defects fixed in the same pass

**A figure written by two scripts.** `sid_run2.py` and `sid_run3.py` both wrote
`figures/sid_midfringe_rate_check.png`, with different curves — the numeric Gaussian-process
comparator and the closed-form geometric fit. The archived file was whichever script ran last.
`sid_run2.py` now writes `sid_midfringe_rate_check_gp_numeric.png`.

**A script silently consuming the archive.** `sid_run3.py` loaded `res2_partial.json`, which only
`sid_run2.py` produces, and the README's Reproduce block never ran `sid_run2.py`. The documented
path therefore worked only because the archived output answered — the same failure as the
`sid_run6s.py` cache, by a different mechanism, and it compounded the collision above, since
running `sid_run2.py` to satisfy the dependency overwrote the shared figure before `sid_run3.py`
overwrote it back. `sid_run3.py` now requires a fresh `analysis/reproduction/res2_partial.json`
and reads the committed copy only under an explicit `--from-archive`.

**Rebuilders assert their postconditions.** Every figure writer checks that the file landed and
is not truncated. `sid_fig_policy_delays.py`, which printed "rebuilt" unconditionally, now
refuses to run at all: its inputs include the delay entries withdrawn as C18, one of which is the
τ_c/c = 20 benchmark that every ratio on that figure divides by. `--acknowledge-withdrawn`
rebuilds the historical figure deliberately, and the run reports any calibrated ARL outside the
±30 % envelope note 03 §2 states.
