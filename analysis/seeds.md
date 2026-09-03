# Seeds behind reported numbers
All generators are `numpy.random.default_rng(seed)`. Grid M and half-width L as stated in each script.

## core (sid_core.py)
- module rng: 1 (unused by reported numbers)
- B: hmm_rate seed 1, N=1e5, M=121
- C: hmm_rate seed 2, N=6e4, M=121 (all theta)
- F: cusum_ext seed 11 (60 runs), cusum_mid seed 12 (40 runs) — mid-fringe result invalid (reset bug), superseded by run2
## run2 (sid_run2.py)
- B2: hmm_rate seed 3, N=1.5e5, M=121
- crossover grid: seed 4, N=1.2e5
- C2: seeds 21, 22, 23, N=2.5e5, M=101
- F2: cusum_ext seed 31 (80 runs), cusum_mid seed 32 (40 runs), h=ln(1e3)
- rate-check figure: seed 7, N=1e5, M=101
## run3 (sid_run3.py)
- rate-check figure: seed 7, N=1e5, M=101; everything else deterministic
## run4 (sid_run4.py)
- 3a convergence: seed 5, N=8e4 (common random numbers across M, L)
- 3b (discarded calibration): seeds 77, 78, 91, 92
## run5 (sid_run5.py)
- calibration bisection: seeds 100+i (i=0..6), confirmation 999; delays: ext seed 7 (150 runs), mid seed 8 (40 runs)
## run6 (sid_run6s.py, batched)
- section 1 bonus: seed 11, R=64, N=6e4, M=61, L=5
- calibration: seeds 100+i (i=0..4), confirmation 199 (via seed+99), R=32/64; B10 refinement seed 777
- delays: seed 200+int(tau_c), R=64
## run7 (sid_run7.py)
- deterministic (quadrature and optimisation)
## run8 (sid_run8.py)
- calibration seeds 300+i, confirmation 399; delays seed 500+int(tau_c), R=64
