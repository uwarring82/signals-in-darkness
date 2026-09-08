# Figures

| file | source | status |
|---|---|---|
| sid_regime_map.png | sid_core.py (E) | current — rebuilt 4 Sept 2026 with corrected validity overlays; the version published before that date is **withdrawn** (it drew the withdrawn C03 box and the withdrawn C01 uniform bound). See notes/2026-09-04-note-06-regime-map-overlays.md |
| sid_regime_map_tau_optimised.png | sid_core.py (E) | superseded (leading-order mid-fringe rate); kept for provenance |
| sid_regime_map_tau_optimised_exact.png | sid_run3.py | current — panel (ii), exact extremum + comparator |
| sid_midfringe_rate_check.png | sid_run3.py | current — **rebuilt 7 Sept 2026**. The version published before that date is **withdrawn**: its legend attributed the strict O(s⁴) asymptote ½C̄⁴s⁴Σa_k² to the card, whose leading-order rate retains the slope-loss resummation e^{−2s²}. The rebuilt figure names the strict curve correctly and plots the card form alongside it. See notes/2026-09-07-note-14-helper-split-and-BE-decisions.md |
| sid_midfringe_rate_check_gp_numeric.png | sid_run2.py | **not yet in the archive** — `sid_run2.py` writes it under this name from 4 Sept 2026. Both scripts previously wrote `sid_midfringe_rate_check.png` with different curves, so the archived file depended on which ran last; the archived copy is `sid_run3.py`'s. It will appear the next time `sid_run2.py` is run, which the Reproduce path must do in any case (`sid_run3.py` consumes its output) |
| sid_endpoint_check.png | sid_core.py (C) | current (single seed; see note 02 for the three-seed values) |
| sid_check2_geomfit_vs_series.png | sid_run4.py | current |
| sid_policy_delays.png | sid_fig_policy_delays.py from stored outputs | current — **rebuilt 8 Sept 2026** from `res6_policies_pilot_recal.json` and `res8_switch_pilot_recal.json`, whose calibrations are inside the ±30 % matched-ARL envelope. The version published before that date is **withdrawn**: it plotted the delays withdrawn as C18, whose τ_c/c = 20 benchmark is the withdrawn `oracle-mid(tc=20)` row that every ratio divides by. `switch@300` is excluded from the rebuilt figure and named in its output, having calibrated to +52.4 %; three successive methods failed to bring it inside. `--legacy --acknowledge-withdrawn` reproduces the historical figure deliberately. See notes/2026-09-08-note-21-paired-bootstrap.md |
| sid_servo_effective_contrast.png | sid_run7.py | current (pilot) |

## Rebuilding

Every figure is written by the script named above, and every writer asserts that the file
landed and is not truncated (rule 6). Only `sid_policy_delays.png` is rebuilt purely from
stored outputs; the others recompute. The grids behind `sid_regime_map.png` are stored under
key `E` of `analysis/outputs/res1_core.json`, so its curves can be checked without rerunning
the section.
