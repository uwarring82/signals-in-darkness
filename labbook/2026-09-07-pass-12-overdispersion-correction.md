# 2026-09-07 — Pass 12: a fixed mean is not a fixed distribution

**Question:** Notebook 01 claimed a count-based test at mid-fringe has *no* power against a correlated process, because the marginal probability of heads is exactly one half. Is that true?
**Finding:** No, and the error is elementary once named. Fixing the **mean** of the head count does not fix its **distribution**. Positive lag correlations make heads arrive in clusters, and clustering inflates the variance of the total: Var(K) = (N/4)[1 + 2Σ(1−k/N)r_k]. At the notebook's parameters the inflation factor is **2.2130**, so the standard deviation of the count rises from 31.62 to 47.04. An exact two-sided count-only test calibrated on the fair-coin null has a false-alarm rate of 4.81 % and rejects the correlated process about **18.9 %** of the time at N = 4000. That is limited power, emphatically not none — and the difference is not rhetorical: a statistic with low power gets there eventually, while a statistic with none never does.
**Why it matters:** This is the second time in two days that the same shape of error reached a committed artefact — pass 8 recorded "zero information" versus "very little information" as an error of kind rather than degree, and pass 11 then reintroduced exactly that confusion in a tutorial written to explain it. The lesson did not transfer because nothing enforced it. The contracts that passed — imports rather than restates, deterministic, writes nothing, claim labels matching the ledger — check provenance and status alignment, and are structurally incapable of seeing a false statistical claim. `tests/test_statistical_framing.py` now pins the specific confusions actually made here, including the variance-inflation factor itself, so a regression fails rather than reads plausibly.
**Status:** No claim changed; the errors were in explanatory prose, not in the record. Notebook 01 reframed, not replaced — its figures and structure were sound throughout.
**Next test:** G — the immutable operating-point configuration.

Technical record: no note; this pass corrected communication material. The notebook now states four separate things where it previously ran them together: two *realised* records with the same count are indistinguishable to every count-only statistic; the correlated *process* still shifts the distribution of that count through overdispersion; conditional on the count the remaining evidence lies entirely in the ordering; and the full ordered record carries information the count discards. Three further corrections followed the same audit. The extremum is no longer called deaf to ordering — its pair correlations begin at higher order and are small in the principal regime but are not zero, which is C24, and the flat curve is now labelled "single-shot contrast loss, correlation bonus omitted" with C24 cited at its real status of `open`. "Memory takes longer than balance" is scoped to the weak-correlation regime, since the notebook's own crossover shows the memory channel overtaking. The 1/√N band is relabelled an approximate iid reference scale rather than a standard error, which it understates for a correlated record. In the public prose: the reproducibility claim is scoped to active `result` and `pilot` numbers, because one withdrawn table's provenance is irrecoverable; C23 is stated as a limit on the closed-form leading-order curve with C05's exact map explicitly unaffected; C26 now distinguishes the broad pointwise class, which does give exact-zero rows, from the shape-constrained Markov class, which does not; and C24 is no longer said to bound anything.

---

## Correction, appended 7 September 2026 (same day, after review)

The **Finding** paragraph above ends: *"a statistic with low power gets there eventually, while a
statistic with none never does."* **That sentence is false for this test**, and it is the same class
of error the pass was written to correct — a plausible-sounding general statement asserted without
checking it against the case at hand.

Here the alternative differs from the null in **width, not in centre**. Both the fair coin and the
correlated process put the count at N/2, and both widths scale as √N, so the standardised count has
an N(0,1) null and an N(0, V∞) alternative *whatever N is*, with

    V∞ = 1 + 2 Σ_{k≥1} r_k = 2.2192.

The nominal 5 % test therefore approaches **2Φ(−1.96/√V∞) = 18.83 %**, not 100 %. The 18.9 % measured
at N = 4000 is already essentially its asymptotic value. Confirmed by simulation at three record
lengths: 17.2 % at N = 1000, 18.1 % at N = 4000, 20.3 % at N = 16000, each ±0.9 pp — a plateau, not a
climb.

The correct wording, now used in notebook 01:

> Nonzero power means the statistic responds to the alternative; it does not imply that one total
> count becomes decisive as the record grows.

The Monte-Carlo power figure also now carries its standard error, ±1.4 pp at 800 runs, which the
original statement omitted.

One thing the check produced that is worth keeping: **V∞ = 1 + δ(0)**, where δ(0) = 2Σr_k is the same
spectral perturbation the project uses as a validity criterion elsewhere. The overdispersion of the
coin's head count and the quantity deciding where a closed-form approximation stops being
trustworthy are the same number. That is now in the notebook.

The entry above is left unaltered, as the record of what was written at the time.
