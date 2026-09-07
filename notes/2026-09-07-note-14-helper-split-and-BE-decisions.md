# Signals in Darkness — execution note 14 (7 Sept 2026): the strict/slope split, and the resolved B/E decisions

Note 13 escalated three decisions and reported one defect. The decisions are resolved here, and the
"defect" is restated more precisely, because the framing in note 13 was wrong in a way that would
have licensed the wrong repair.

## 1. Erratum to note 13 §2 — it is not an omission

Note 13 said the helper "omits the factor e^{−2s²} that C02's statement says the leading-order rate
carries", which reads as a missing term to be restored. It is not. There are two legitimate
quantities:

    I_strict = ½ C̄⁴ s⁴ Σ a_k²                  the strict O(s⁴) asymptote
    I_slope  = I_strict · e^{−2s²}              the card's slope-loss resummation

They **agree through strict O(s⁴)** and differ above it — by 19.7 % at s = 0.3 and 64.9 % at
s = 0.5. Neither is wrong; the former helper `I_mid_lo` computed `I_strict` while its name, and one
figure legend, promised `I_slope`. So the repair is not to overwrite the helper. It is to split,
audit the call sites, and correct only what claimed to be the card formula.

## 2. What was split, and what was audited

`I_mid_lo` → `I_mid_strict` / `I_mid_slope`, and `I_lo_theta` → `I_lo_theta_strict` /
`I_lo_theta_slope`, in both copies (`analysis/lib/sid_lib.py`, `analysis/runs/sid_core.py`). No
ambiguous name survives; `tests/test_manifest_BE.py` asserts both are gone.

Call sites, all four audited:

| site | resolution |
|---|---|
| `sid_run2.py:32`, `:178` | → `I_mid_strict`. Legend reads `½C̄⁴s⁴Σa_k²` with no card attribution: **honest, unchanged.** |
| `sid_core.py:169` | → `I_mid_strict`. Column label `I_lo` → `I_mid_strict`. **Value unchanged.** |
| `sid_core.py:187` | → `I_lo_theta_strict`. Column `lo` → `lo_strict`. **Value unchanged.** |
| `sid_run3.py:104` | → `I_mid_strict`, **and its legend said `(card)`** — the one false attribution in the repository. Corrected, and the `I_mid_slope` curve added alongside, since the figure's subject is exactly the comparison of mid-fringe approximations. |

**No stored value changed anywhere.** The archived columns always held the strict asymptote; only
names that promised otherwise were corrected. `SCHEMA.md` carries the relabelling and its reason.

The split was verified to be a pure refactor by regenerating `res1_core.json` with and without it:
`tools/compare_reproduction.py` produced **byte-identical output both ways**, including the same
pre-existing discrepancy described in §5.

### 2a. The two forms are not equally good approximations

Plotting both made a further point visible, which is worth recording because it strengthens §3.
Against the exact ½Σr_k² at C̄ = 0.4, s = 0.5, over τ_c/c ∈ [1, 100]:

| | ratio to ½Σr_k² |
|---|---|
| `I_mid_slope` (card) | **0.9897 – 0.9975** |
| `I_mid_strict` | 1.6318 – 1.6446 |

The slope-loss resummation is within **1 %** of the exact half-sum across the entire grid, while the
strict asymptote is uniformly **63–64 % high**. So `e^{−2s²}` is not a cosmetic refinement: at this
amplitude it captures almost all of the correction that using exact r_k provides. The two curves
therefore overlap in the rebuilt figure, which is the honest depiction.

This also settles which form a claim should quote when it says "leading order": the card's, because
the strict asymptote is not a usable approximation at s = 0.5 in the first place.

## 3. C25 carries 1496

C25 attributes its comparison to the card formula, so it must quote that formula's value.

    h/I_strict = 907.1     the strict asymptote, evaluated well outside its useful range
    h/I_slope  = 1495.6    the card leading order

C25 now reads 1496, corrected from a published 910. **The conclusion is unchanged**: against a
measured 2010 ± 170, the card leading order is 26 % low while the exact rate is 11 % high, so the
leading-order rate remains an unusable delay predictor and the exact rate remains a usable one. C25
keeps status `result` with an erratum. C02 keeps status `result`; its statement was always the
correct one.

## 4. C06 is robust to the choice

The endpoint lemma's B term carried the same ambiguity, so the conclusion was checked directly. The
interior-minimum-versus-endpoint verdict is **identical** under both forms at all three archived
cases — (0.9, 0.3, 5) interior, (0.4, 0.5, 20) interior, (0.4, 0.5, 1) endpoint. Only the minimum's
location moves, e.g. 0.3416 → 0.3954 rad at C̄ = 0.9, s = 0.3, τ_c/c = 5. C06 is unaffected.

## 5. A pre-existing discrepancy, recorded and not attributed

`res1_core.json["F"][1][8:10]` is `null` in the archive but **87159.325 ± 6294.0** here. The archive
records that no mid-fringe run reached the threshold at τ_c/c = 1; on python 3.9 / numpy 1.x, 40 of
60 runs did. This is **not caused by the split** — it reproduces identically with the split stashed —
and this is not the certified environment. What it shows is that the archived `null` is stack-
dependent at that point rather than a property of the physics. Off B's and E's path; recorded for
follow-up.

## 6. The three decisions

**D1 — the convention is split.** B uses effective per-shot contrast **C̄_eff**, including all loss at
its implicit fixed interrogation. E uses zero-dephasing contrast **C̄₀**, with e^{−χ(τ)} applied
separately. They are not one physical operating point and no longer share a field: the manifest
contains no key named `C_bar`, and a test enforces that.

**D2 — B's second point is C̄_eff = 0.5, s = 0.3**, at the parity ceiling, **labelled an upper-bound
stress test and not a realistic contrast.** This keeps the freeze-gating run inside the
oscillator-cancelled parity regime that carries the principal claims, so **roadmap D is not promoted
to a freeze gate**. C̄_eff ≈ 0.8 survives only as an optional servo-appendix run after D, which may
not gate the principal parity result.

The choice also improves validity. δ(0) at (0.5, 0.3) is **0.0239 / 0.1858 / 0.8025** at
τ_c/c = 1 / 5 / 20 against C23's level 0.3 — **one** of three points outside, against two of three
under the withdrawn 0.8 proposal. Interpretation at τ_c/c = 5 and 20 uses the exact comparator.

**D3 — all three calibration uncertainties are kept**, η₀ ∈ {0.02, 0.05, 0.10}. An already archived,
useful dimension is not discarded; the card is updated to match the archive rather than the reverse.

**E gains C̄₀ = 0.5** as its second principal-regime slice. The existing C̄₀ = 0.9 rows are retained as
servo/coherent context and **may not be used to support the parity-regime headline**. E reports
**per-shot** identifiability over τ_c/T₂ and **does not price dead time** — `sid_run7.py:20` assigns
`td = 1.0` and never uses it — and this must be stated explicitly in any result. E's reproducibility
is recorded as **seed-free and reproducible within 6 × 10⁻⁸, but optimiser- and stack-dependent**,
with optimiser termination status and all three starts to be stored alongside the infimum.

## 7. Order

E remains first among the new scientific runs. The helper split (this note) and the operating-point
provenance repair land before B starts. The five pre-B steps are recorded in
`analysis/manifest_BE.json` under `pre_B_sequence`: an immutable operating-point configuration
replacing the mutable globals; that configuration carried in checkpoint identity and output
metadata; proof that the refactor preserves all five reproducible pilot calibration rows before any
second point is added; fresh calibration of every B policy, with no archived C17/C18 threshold
entering; and the exact comparator for interpretation at τ_c/c = 5 and 20.
