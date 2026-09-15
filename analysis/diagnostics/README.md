# Deterministic diagnostics for note 26 and its review

These scripts calculate comparator quantities only. They implement no ARMA likelihood,
simulate no latent trajectory and produce no F validation result. Run from the repository
root; output goes to stdout. Nothing writes to the numerical archive.

```sh
python analysis/diagnostics/fold_check.py
python analysis/diagnostics/f_design.py
python analysis/diagnostics/review_F_plan.py
```

`fold_check.py` and `f_design.py` are byte-identical copies of the model-generated review's
scratch producers located during review of note 26. They preserve the original diagnostics,
including the rounded boundary inputs in `f_design.py`; they are not a frozen F protocol.
Their SHA-256 values at adoption are:

| File | SHA-256 |
|---|---|
| fold_check.py | 13009ab35cc94958cac170e2ed255c969d7c2f5742c550272bf189ba79e6532d |
| f_design.py | 3e362061f8271fd15043bdebda77d765b91673fbc11e8534c7e081cc6bbe35b5 |

`review_F_plan.py` adds the deterministic checks behind
[note 27](../../notes/2026-09-15-note-27-C08-fold-erratum-and-F-review.md): it reads the actual
run3 map call through the AST, checks comparator distinctions, demonstrates the E6 verdict
counterexample and derives boundary points from the archived columns and run3 tau grid.
Driver bodies are not imported or executed. The original diagnostics copy run3's map loop;
the additional review checks inspect its live expression so the historical normalization
cannot be silently replaced by the corrected one during reproduction.

The focused guard is in [test_c08_fold_provenance.py](../../tests/test_c08_fold_provenance.py).
It requires the lag-one contract to reject the archived map form and accept run4's fit.
A future producer correction must explicitly retire that negative control and identify
its replacement artifact; passing these tests does not make the archived map correct.
