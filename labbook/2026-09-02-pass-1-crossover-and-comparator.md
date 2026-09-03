# 2026-09-02 — Pass 1: does the crossover theorem survive exact calculation?

**Question:** Does the leading-order operating-point crossover in card v1.0 hold against exact information rates, and can the regime map be drawn honestly?
**Finding:** The extremum formula holds. The mid-fringe leading-order rate overstates the exact rate by 2–4× where mid-fringe is supposed to win, because the channel turns into tracking of a quasi-static offset at long correlation time; the correct validity condition is spectral, first order in s². A Gaussian spectral comparator built from the exact lag correlations reproduces the exact latent-process rate within Monte-Carlo error.
**Why it matters:** Changed the paper: the theorem is exact only as a small-amplitude limit; the working formula for the map changed; the crossover is amplitude-dependent.
**Status:** result (one parameter set).
**Next test:** second parameter set; matched-run-length delay comparison.

Technical record: notes/2026-09-02-note-01.md; scripts sid_core.py, sid_run2.py, sid_run3.py; seeds in analysis/seeds.md; outputs res1_core.json, res2_partial.json; figures sid_regime_map.png, sid_regime_map_tau_optimised_exact.png, sid_midfringe_rate_check.png, sid_endpoint_check.png. Model assistance: analysis and drafting were produced with an AI model; every number was recomputed by the scripts listed.
