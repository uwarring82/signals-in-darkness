# 2026-09-02 — Pass 1b: three checks before issuing card v1.1

**Question:** Is the geometric-fit shortcut adequate, is the reference detector grid-converged, and do the delay comparisons hold at a common false-alarm run length?
**Finding:** Shortcut within 0.4 % at the map's optimal interrogation time and fails only at s = 1; reference detector converged to < 0.01 % (Monte-Carlo error ≈ 7 % is the limit); at matched null run length the delay crossover agrees with the rate crossover, but the delay advantage is 1.5–3× smaller than the rate ratio.
**Why it matters:** Fixed the working formula and the comparison protocol for v1.1; the compression is a pilot observation until null statistics are tightened.
**Status:** result (checks 2, 3a); pilot (3b).
**Next test:** tightened null calibration; policy comparison.

Technical record: notes/2026-09-02-note-02.md; sid_run4.py, sid_run5.py; figure sid_check2_geomfit_vs_series.png. A first calibration attempt extrapolated outside the measured range and was discarded (documented in the note).
