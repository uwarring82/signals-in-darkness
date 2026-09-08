"""Shared policy-simulation machinery for the sequential-detection comparisons.

Purpose   : batched latent-AR(1) filter-bank CUSUM simulator, null calibration
            (ARL -> threshold) and detection-delay measurement.
Inputs    : an OperatingPoint, passed explicitly by every caller. There is no module-level
            C or s: see the note under OperatingPoint for why that mattered.
Seeds     : callers pass every seed explicitly; recorded in analysis/seeds.md.
Outputs   : none. Callers own their output files.
Runtime   : n/a (library).

Provenance: moved verbatim from the prefix of analysis/runs/sid_run6s.py as it
            stood at tag archive-2026-09-03, so that sid_run8.py can import this
            machinery instead of exec()ing that file as text, and so that the two
            drivers cannot drift apart. The only additions are the STATS counter
            and this docstring; no numerical behaviour is changed. The move is
            verified bit-for-bit against the five reproducible archive rows in
            notes/2026-09-03-note-04-reproduction-defect.md.
"""
import math
from dataclasses import dataclass

import numpy as np

THM, THX = math.pi/2, math.pi          # mid-fringe, dark extremum
M, L = 61, 5.0                         # bank grid resolution and half-width in units of s
GAMMA = 3.0e4                          # target null run length E_0[T]


@dataclass(frozen=True)
class OperatingPoint:
    """The (contrast, amplitude) pair a simulation is run at. Immutable, and passed explicitly.

    Until 7 September 2026 this module held `C, s = 0.4, 0.5` as mutable module globals with
    three readers that could disagree. That is not a style question. A stored result did not
    carry the parameters it was computed at, so a checkpoint could not refuse to be reused
    under the wrong ones, and a threshold measured at one operating point could be consumed by
    a delay run at another with nothing to detect it. Claims C17 and C18 were withdrawn over
    calibration whose provenance could not be established; this is the structural fix for that
    class of failure, and it is a precondition for adding a second operating point (roadmap B).

    `C_eff` is the EFFECTIVE per-shot contrast, including all loss at the implicit fixed
    interrogation time. It is not the zero-dephasing contrast C_0 that the physical maps and
    the identifiability run use -- those are different quantities and do not share a field.
    """
    C_eff: float
    s: float

    def as_dict(self):
        """Canonical serialisation, for checkpoint identity and output metadata."""
        return {"C_eff": self.C_eff, "s": self.s}

    def label(self):
        return f"C_eff={self.C_eff:g}, s={self.s:g}"


#: The pilot operating point. A named constant, not a default: callers pass it explicitly.
PILOT = OperatingPoint(C_eff=0.4, s=0.5)

#: Roadmap B's second operating point. C_eff = 0.5 is EXACTLY the parity ceiling
#: C_par = (1/2) C_1 C_2 <= 1/2 (cards/v1.1-frozen.md:117), so it stays inside the
#: oscillator-cancelled parity regime that carries the principal claims and does not depend on
#: roadmap D. It is an UPPER-BOUND STRESS TEST, not a realistic contrast, and must be labelled
#: as such wherever it is reported. Decided 7 Sept 2026 as manifest decision D2, replacing an
#: earlier C = 0.8 proposal that would have placed a freeze gate in the servo regime.
STRESS = OperatingPoint(C_eff=0.5, s=0.3)

#: Calibration bisection bracket and iteration count, PER OPERATING POINT.
#:
#: The pilot's (1.0, 6.0, 5) is frozen: those exact values produced the archived thresholds,
#: and roadmap G's preservation evidence compares them by exact equality. It must not change.
#:
#: The stress point needs its own. Measured 7 Sept 2026: under the pilot's bracket,
#: oracle-mid(tc=1) at (C_eff=0.5, s=0.3) never moves the floor, converges to h* = 1.078125 --
#: the midpoint of an *untested* [1.0, 1.156] -- and confirms at ARL 23669, a 21 % miss against
#: the 3e4 target. Five iterations over a span of 5.0 resolve only to 0.156, which is coarse
#: where h* ~ 1.1. A narrower bracket with more iterations resolves to 0.027 and brackets every
#: stress policy: h* runs from about 1.1 (oracle-mid(tc=1)) to about 2.3 (extremum-only).
CAL_BRACKET = {"pilot": (1.0, 6.0, 5), "stress": (0.5, 4.0, 7), "pilot_recal": (1.0, 6.0, 5)}

#: Seed offset per operating point. With a shared seed the latent phase paths of two operating
#: points are perfectly correlated -- simulate() scales the same standard normals by s, so the
#: stress path is exactly 0.6x the pilot's, shot for shot. That is fine as a variance-reduction
#: device but it is not an independent second measurement, and the second operating point is
#: meant to be one. The pilot's offset is 0 so its archived seeds are untouched.
SEED_OFFSET = {"pilot": 0, "stress": 7000, "pilot_recal": 0}

#: The declared matched-E0[T] envelope. A calibration outside it breaks the premise every
#: delay ratio rests on -- the policies are then NOT held to the same false-alarm rate, so the
#: ratios are not comparable. Until 8 Sept 2026 this lived only as a WARNING inside
#: sid_fig_policy_delays.py, printed after the figure had already been drawn from the offending
#: rows; note 04 documented the breach and nothing enforced it. It is now a gate.
ARL_ENVELOPE = 0.30
NULL_CAP_DEFAULT = 150_000

#: Selectable by name from the command line. Adding an entry here is the only supported way to
#: introduce an operating point; nothing reads one from module state.
#: `pilot_recal` is the SAME physical operating point as `pilot`, calibrated with
#: calibrate_refined instead of plain bisection. It is a separate name so it writes a
#: separate artifact and cannot overwrite the historical archive.
OPERATING_POINTS = {"pilot": PILOT, "stress": STRESS, "pilot_recal": PILOT}


def operating_point_from_argv(argv, default="pilot"):
    """Read --operating-point=<name> from argv. Unknown names are refused, not defaulted."""
    name = default
    for arg in argv:
        if arg.startswith("--operating-point="):
            name = arg.split("=", 1)[1]
    if name not in OPERATING_POINTS:
        raise SystemExit(f"unknown operating point {name!r}; "
                         f"choose one of {sorted(OPERATING_POINTS)}")
    return name, OPERATING_POINTS[name]


def state_name_for(base, op_name):
    """Checkpoint/output filename for an operating point.

    The pilot keeps the historical name so its reproduction path is unchanged; every other
    operating point gets its own file. Two operating points sharing one checkpoint would
    reintroduce, at the filesystem level, exactly the confusion roadmap G removed in memory.
    """
    if op_name == "pilot":
        return base
    stem, dot, ext = base.partition(".")
    return f"{stem}_{op_name}{dot}{ext}"

# ---------------- work counter (read by the reproduction regression test) ------
# Incremented once per simulator entry. A reproduction route that reports work
# done but leaves this at zero has replayed stored numbers instead of computing.
STATS = {"run_batch_calls": 0, "simulated_steps": 0}


def reset_stats():
    STATS["run_batch_calls"] = 0
    STATS["simulated_steps"] = 0


# ---------------- batched latent-AR(1) bank simulator ----------------
class Bank:
    """Filter bank for one or more candidate correlation times, at one operating point.

    The operating point is carried on the object, so every downstream function reads it from
    the bank rather than from module state. Two banks built at different operating points
    cannot be confused for one another.
    """

    def __init__(self, tccs, op):
        if not isinstance(op, OperatingPoint):
            raise TypeError("Bank requires an explicit OperatingPoint; module-level C and s "
                            "were removed on 7 September 2026 (roadmap G)")
        self.op = op
        s = op.s
        self.g = np.linspace(-L*s, L*s, M)
        self.prior = np.exp(-self.g**2/(2*s*s)); self.prior /= self.prior.sum()
        self.T = []
        for tcc in tccs:
            a = math.exp(-1/tcc); sd = s*math.sqrt(1-a*a)
            T = np.exp(-(self.g[None, :]-a*self.g[:, None])**2/(2*sd*sd)); T /= T.sum(1, keepdims=True)
            self.T.append(T)
        self.K = len(tccs)
        self.e1 = {th: 0.5*(1+op.C_eff*np.cos(th+self.g)) for th in (THM, THX)}

    def p0(self, th): return 0.5*(1+self.op.C_eff*math.cos(th))


def run_batch(bank, sched, true_tcc, h, R, seed, max_steps, null):
    """sched(n) -> theta. Returns stopping step per run (max_steps if not stopped). Mixture-LR CUSUM with reset."""
    STATS["run_batch_calls"] += 1
    r = np.random.default_rng(seed)
    C, s = bank.op.C_eff, bank.op.s        # read from the bank, never from module state
    alpha = [np.tile(bank.prior, (R, 1)) for _ in range(bank.K)]
    Lk = np.zeros((R, bank.K)); W = np.zeros(R); stop = np.full(R, max_steps); active = np.ones(R, bool)
    if not null:
        a_true = math.exp(-1/true_tcc); sd = s*math.sqrt(1-a_true*a_true); eps = r.normal(0, s, R)
    logK = math.log(bank.K)
    for n in range(max_steps):
        th = sched(n); e1 = bank.e1[th]
        if null:
            y = r.random(R) < bank.p0(th)
        else:
            eps = a_true*eps + sd*r.normal(0, 1, R)
            y = r.random(R) < 0.5*(1+C*np.cos(th+eps))
        ey = np.where(y[:, None], e1[None, :], 1-e1[None, :])           # R x M
        logz = np.empty((R, bank.K))
        for k in range(bank.K):
            al = alpha[k] @ bank.T[k]; al *= ey; z = al.sum(1); al /= z[:, None]
            alpha[k] = al; logz[:, k] = np.log(z)
        # mixture predictive: log sum_k pi_k exp(L_k + logz_k) - log sum_k pi_k exp(L_k)
        A = Lk + logz; mA = A.max(1, keepdims=True); num = mA[:, 0] + np.log(np.exp(A-mA).sum(1))
        mB = Lk.max(1, keepdims=True); den = mB[:, 0] + np.log(np.exp(Lk-mB).sum(1))
        p0 = bank.p0(th); l0 = np.where(y, math.log(p0), math.log(1-p0))
        W += (num-den) - l0; Lk = A
        hit = active & (W >= h); stop[hit] = n+1; active &= ~hit
        STATS["simulated_steps"] += 1
        if not active.any(): break
        rs = W < -1e-9
        if rs.any():
            W[rs] = 0.0; Lk[rs] = 0.0
            for k in range(bank.K): alpha[k][rs] = bank.prior
    return stop


def arl_of(bank, sched, h, R, seed, cap=150_000):
    st = run_batch(bank, sched, None, h, R, seed, cap, True)
    return st.mean(), st.std()/math.sqrt(R), (st >= cap).sum()


def calibrate(bank, sched, gamma, R=48, lo=1.0, hi=6.0, iters=5, seed=100):
    """Fixed-iteration bisection on the CUSUM threshold. Returns (h, ARL, se, capped, endpoint).

    `endpoint` is None when the bracket was two-sided -- both ends moved at least once -- and
    otherwise names the end that was never moved. That case is not a convergence failure in the
    usual sense: the bisection still returns the midpoint of its final interval, but one side of
    that interval was never tested, so the answer is set by the bracket rather than by the data.
    It is reported rather than swallowed, because at the stress point it silently cost 21 % of
    the target run length before anyone looked.
    """
    lo0, hi0 = lo, hi
    for i in range(iters):
        mid = 0.5*(lo+hi); m, se, nc = arl_of(bank, sched, mid, R, seed+i)
        if m > gamma: hi = mid
        else: lo = mid
    h = 0.5*(lo+hi); m, se, nc = arl_of(bank, sched, h, 2*R, seed+99)
    endpoint = "floor" if lo == lo0 else ("ceiling" if hi == hi0 else None)
    return h, m, se, nc, endpoint


def calibrate_refined(bank, sched, gamma, R=32, lo=1.0, hi=6.0, iters=5, seed=100,
                      confirm_R=64, cap=NULL_CAP_DEFAULT, max_secant=4):
    """Bisection, then a secant root-find on ln(ARL), then confirmation.

    Plain bisection is not good enough at the pilot. Its probes use R=32, whose ARL estimate
    carries ~15 % standard error, and null runs that hit the cap contribute the cap instead of
    their true larger stopping time -- a downward bias growing with h. A probe that understates
    the ARL moves `lo` UP, so noise and censoring push the same way and the bracket can end up
    entirely ABOVE the true crossing.

    Interpolating inside that bracket cannot then help: measured 8 Sept 2026, oracle-mid(tc=20)
    and learner-interleave-B10 both had their whole final interval above target, the
    interpolation fraction fell outside [0,1], and the routine fell back to the midpoint -- so
    the refined answer was bit-identical to the bisection's and still +37 % and +48 % off.

    A secant step on ln(ARL) versus h is not confined to the bracket, so it can walk back down
    to the crossing. ln(ARL) is close to linear in h, which is what makes it converge quickly.
    Returns (h, ARL, se, capped, endpoint, within_envelope).
    """
    lo0, hi0 = lo, hi
    for i in range(iters):
        mid = 0.5 * (lo + hi)
        m, _, _ = arl_of(bank, sched, mid, R, seed + i, cap=cap)
        if m > gamma:
            hi = mid
        else:
            lo = mid
    endpoint = "floor" if lo == lo0 else ("ceiling" if hi == hi0 else None)

    # Two anchors for the secant, measured at higher replication than the bisection used.
    pts = []
    for k, h_k in enumerate((lo, hi)):
        m_k, _, _ = arl_of(bank, sched, h_k, confirm_R, seed + 50 + k, cap=cap)
        if m_k > 0:
            pts.append((h_k, math.log(m_k)))
    target = math.log(gamma)

    h = 0.5 * (lo + hi)
    for step in range(max_secant):
        if len(pts) < 2:
            break
        (h1, y1), (h2, y2) = pts[-2], pts[-1]
        if y2 == y1:
            break
        h = h1 + (target - y1) * (h2 - h1) / (y2 - y1)
        h = min(max(h, lo0), hi0)                      # never leave the declared bracket
        m, _, _ = arl_of(bank, sched, h, confirm_R, seed + 60 + step, cap=cap)
        if m <= 0:
            break
        pts.append((h, math.log(m)))
        if abs(m - gamma) / gamma <= ARL_ENVELOPE:
            break

    m, se, nc = arl_of(bank, sched, h, 2 * confirm_R, seed + 99, cap=cap)
    return h, m, se, nc, endpoint, abs(m - gamma) / gamma <= ARL_ENVELOPE


def delay_of(bank, sched, true_tcc, h, R, seed, cap=100_000):
    st = run_batch(bank, sched, true_tcc, h, R, seed, cap, False)
    return st.mean(), st.std()/math.sqrt(R), (st >= cap).sum()


# ---------------- the seven pilot policies ----------------
def make_interleave(B): return lambda n: THM if (n//B) % 2 == 0 else THX


def sched_mid(n): return THM


def sched_ext(n): return THX


def build_policies(op):
    """Return (policies, bank_or, bank_ln) at the given operating point.

    Every Bank depends on the operating point -- the grid, the prior and the per-shot
    likelihood all derive from s, and e1 from both -- so `op` is required, not defaulted.
    """
    if not isinstance(op, OperatingPoint):
        raise TypeError("build_policies requires an explicit OperatingPoint (roadmap G)")
    bank_or = {tcc: Bank([tcc], op) for tcc in (20.0, 5.0, 1.0)}
    bank_ln = Bank([1.0, 4.0, 10.0, 25.0], op)
    policies = {
        "oracle-mid(tc=20)": (bank_or[20.0], sched_mid),
        "oracle-mid(tc=5)": (bank_or[5.0], sched_mid),
        "oracle-mid(tc=1)": (bank_or[1.0], sched_mid),
        "extremum-only": (bank_or[20.0], sched_ext),
        "learner-mid(bank)": (bank_ln, sched_mid),
        "learner-interleave-B10(bank)": (bank_ln, make_interleave(10)),
        "learner-interleave-B1(bank)": (bank_ln, make_interleave(1)),
    }
    return policies, bank_or, bank_ln
