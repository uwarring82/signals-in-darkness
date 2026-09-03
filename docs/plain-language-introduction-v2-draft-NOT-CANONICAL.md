# Signals in Darkness

## When a quantum sensor detects a change—and when it knows what changed

**Status:** Revised draft companion to the *Operating-Point Crossover in Sequential Quantum-Clock Detection* research card  
**Audience:** Physicists and technically interested readers who are not specialists in quantum clocks or sequential statistics

### A trail of bright and dark outcomes

In many atomic-clock and qubit experiments, each measurement ends in one of two outcomes. Depending on the apparatus, these may literally appear as a bright or dark signal. One result says almost nothing. A long trail of results can reveal that the balance between bright and dark has shifted, or that nearby results have started to resemble one another more than chance would allow.

The project *Signals in Darkness* asks what physical claim such a trail can support. Detecting that something changed is not the same as identifying what changed. A weak fluctuating field may alter the measurement record, but so can ordinary drift in the sensor. The central question is therefore:

> If a weak stochastic modulation may begin at an unknown time, which clock setting extracts evidence of that change fastest, and how much time is lost when the signal's correlation scale is not known in advance?

Behind this is a second, equally important question: when does the evidence justify attributing the change to the sought signal rather than to a mundane loss of sensor coherence?

This is the quantum version of watching a coin that may change without warning. One could look for a change in the fraction of heads. But a hidden influence might leave that fraction at one half while making runs of similar outcomes more common. The first clue is a change in **balance**; the second is a change in **memory**. A quantum sensor can be deliberately placed in a setting that favours one clue or the other.

### One clock, two ways to notice noise

The measurement studied here is a Ramsey interrogation: the quantum system is placed in a superposition, allowed to accumulate phase for a chosen time, and then converted back into a bright-or-dark probability. Changing the final control phase traces a wave-shaped response called a Ramsey fringe.

At the steep side of this fringe—**mid-fringe**—a small phase shift has a large effect on the immediate outcome. If the hidden signal fluctuates equally in both directions, however, those shifts cancel in the average. Its trace instead appears as memory: a slowly changing signal makes nearby outcomes correlated.

At the top or bottom of the fringe—a **fringe extremum**—the outcome is initially almost certain. Random phase excursions blur that certainty and reduce the fringe's contrast. Its trace therefore appears as a change in balance. Unfortunately, ordinary sensor degradation can produce exactly the same effect.

![Sketch of a Ramsey fringe marking mid-fringe and a dark extremum. Mid-fringe reveals temporal memory; the extremum reveals contrast loss.](signals-in-darkness-fringe-sketch.svg)
<!-- TODO(owner): the SVG itself is still to be supplied (SEED_HANDOVER.md, "deliberately missing").
     The link was an absolute path into a local working directory until 2026-09-03; it is now
     relative, per cards/repo-seed-v0.2.md ("relative links only"). The target does not yet exist. -->

Neither setting is always best. Fast fluctuations leave little memory between measurements, making contrast loss the more useful clue. Slow fluctuations persist across many measurements, making their temporal pattern valuable.

For scale, imagine a clock-like sensor that preserves useful phase information for about one second and needs another 100 milliseconds for readout and preparation. A fluctuation with a half-second correlation time—the time over which it substantially remembers its previous value—has largely changed during a long interrogation. A ten-second fluctuation survives across many cycles and produces a visible pattern in the sequence. If detection needs a thousand one-second interrogations, it takes roughly eighteen minutes rather than an abstract “thousand samples.” This is why interrogation time, dead time, and calibration time must be counted together.

### What prior work established—and what remains

The project sits where three established research traditions meet.

**Correlation spectroscopy** compares two clocks interrogated by the same laser. By asking whether their two outcomes agree or disagree—a quantity known as parity—it can reject phase noise shared through the laser and expose their relative evolution. [Chou and colleagues](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.106.160801) demonstrated coherence between two ions beyond the coherence of the probe laser. [Hume and Leibrandt](https://journals.aps.org/pra/abstract/10.1103/PhysRevA.93.032138) developed clock-comparison protocols that operate beyond that laser limit, and [Clements and colleagues](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.125.243602) demonstrated lifetime-limited interrogation of two independent aluminium-ion clocks. This work establishes how shared technical noise can be removed, but it does not ask which point on the fringe gives the fastest warning of a new stochastic signal.

**Quantum sensing and noise spectroscopy** use a controlled qubit or atom to learn about its environment. Ramsey measurements and more elaborate pulse sequences can translate different fluctuation timescales into measurable phase or loss of coherence; accessible introductions include [Degen, Reinhard and Cappellaro](https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.89.035002) and [Szańkowski and colleagues](https://arxiv.org/abs/1705.02262). [Shulman and colleagues](https://www.nature.com/articles/ncomms6156) went further by using repeated single-shot qubit measurements and Bayesian inference to track a fluctuating effective field in real time. These methods show that a binary quantum record contains information about hidden dynamics, but their main goal is usually estimation, reconstruction, or feedback—not the quickest trustworthy alarm after an unknown change time.

**Sequential statistics** asks when accumulated evidence is strong enough to stop observing and announce a change. [Page's cumulative-sum method](https://doi.org/10.1093/biomet/41.1-2.100) and [Lorden's quickest-detection formulation](https://authors.library.caltech.edu/records/n9ryc-0sr08) laid classical foundations for balancing delay against false alarms. [Chernoff](https://doi.org/10.1214/aoms/1177706205) considered the additional problem of choosing each next experiment, an idea developed in modern active hypothesis testing by researchers including [Naghshvar and Javidi](https://doi.org/10.1214/13-AOS1144). This theory explains how evidence and measurement choices can be coupled, but it does not by itself include the clock's fringe geometry, its finite coherence, shared-laser rejection, or the ambiguity between a signal and ordinary dephasing.

Our gap is the intersection: quickest change detection when the available quantum measurements reveal different statistical features of the same hidden process, and when the most sensitive feature may not be specific to the cause of interest.

### The proposed study

The first study uses Ornstein–Uhlenbeck noise, a standard model of a smoothly fluctuating quantity that gradually forgets its past. It has a strength and a single correlation time, so it can represent both nearly independent changes from shot to shot and a slowly drifting offset. This is intentionally simpler than a process with abrupt jumps. Its value is that the measurement logic can be derived and checked without hiding it inside a needlessly complicated signal model.

The calculation begins with the actual two-outcome records of two synchronously interrogated clocks. Their phase-memory time, often called \(T_2\), their readout quality, interrogation duration, and dead time are included. When the shared laser phase is completely unknown, the analysis keeps only whether the two clock outcomes agree or disagree. When a feedback loop keeps that laser phase approximately known, the complete pair of outcomes can carry more information, although the feedback measurements also consume time.

Two strategies are then compared on equal terms:

- The **extremum strategy** watches the bright-dark balance for contrast loss.
- The **mid-fringe strategy** watches the sequence for correlations across one or more measurement cycles.

The analysis asks how much evidence each strategy gains per unit of wall-clock time. A manageable frequency-domain calculation is checked against a fuller numerical model that explicitly follows the hidden fluctuation behind the binary outcomes. False-alarm rates are measured separately for each complete strategy so that one detector is not given an easier stopping rule than the other.

The expected result is a regime map rather than a single best setting. Rapid fluctuations should usually favour the extremum; persistent fluctuations should favour mid-fringe. The boundary depends not only on correlation time but also on signal strength, contrast, sensor coherence, and the chosen interrogation time. In the persistent limit, the mid-fringe sensor effectively tracks a slowly moving offset rather than merely measuring extra noise.

Identification requires an additional layer. Contrast loss at the extremum may mean that the sought fluctuation appeared, but it may simply mean that \(T_2\) became shorter. The experiment must therefore repeat the measurement at several interrogation times and compare the resulting contrast curve with a calibrated family of ordinary dephasing behaviours. If both explanations fit, the honest conclusion is “additional dephasing detected,” not “stochastic field identified.” Mid-fringe correlations can sometimes provide their own evidence of temporal structure and avoid that ambiguity.

Finally, the study compares an **oracle**, which already knows the hidden correlation time, with a **learner**, which must estimate it while looking for the change. The learner may explore by measuring correlations at mid-fringe or by varying the interrogation time. The cost of that exploration is the extra detection delay relative to the oracle, with both held to the same measured false-alarm rate.

### Possible uses and wider relevance

For optical-clock comparisons and clock networks, the regime map could indicate when to monitor ordinary contrast and when to preserve and analyse correlations between repeated outcomes. For trapped ions, neutral atoms, solid-state spins, and superconducting qubits, the same framework could help separate a new external fluctuation from a change in device coherence. It could also support early warning of calibration drift, real-time monitoring of qubit environments, and sensing of weak stochastic magnetic, electric, inertial, or frequency disturbances.

The first model is continuous and Gaussian—its fluctuations follow the familiar bell-curve statistics. A later extension could treat intermittent signals and Lévy processes, a broad class that allows both gradual motion and sudden jumps. That would bring rare transients and competing kinds of hidden dynamics into scope, but only after the simpler case has made the distinction between detection and physical identification explicit.

The wider contribution is therefore not another claim that a quantum sensor can detect something small. It is a framework for deciding what a finite stream of bright and dark outcomes actually establishes: which measurement should be made next, how long a defensible alarm takes, and whether the observed change identifies a physical cause or merely reveals that the sensor no longer behaves as before.
