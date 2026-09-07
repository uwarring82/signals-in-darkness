"""Explore-then-switch policy: mid-fringe for B shots of segment age, then extremum.

Purpose  : calibrate and measure the explore-then-switch hedge at B in {300, 1000},
           the policy family behind claim C11 in ledgers/status.yaml.
Inputs   : the operating point, passed explicitly as sid_policies.PILOT (roadmap G).
Seeds    : calibration bisection 300..304, confirmation 399; delays 500 + int(tau_c/c).
           Recorded in analysis/seeds.md.
Outputs  : analysis/reproduction/res8_switch.json (fresh run; git-ignored).
           The published reference stays at analysis/outputs/res8_switch.json and is
           only read, for comparison.
Runtime  : 4.5 to 41 min on one core, observed across three runs of the certified
           platform (macOS x86_64 under Rosetta 2). Results were bit-identical in every
           run; the spread depends strongly on sustained system load and its cause has
           not been isolated. No telemetry was collected.

Usage:
    python sid_run8.py [--resume]

Two defects fixed here relative to tag archive-2026-09-03, both recorded in
notes/2026-09-03-note-04-reproduction-defect.md:
  - it exec()'d a text slice of sid_run6s.py ("...".split("arg=sys.argv[1]")[0]),
    which silently bound that script's state file and would break on any edit above
    the split marker. It now imports analysis/lib/sid_policies.py.
  - it wrote "res8_switch.json" to the current working directory, not to the
    outputs directory, so the committed archive copy cannot have come from a run
    performed as the README documents.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import sid_repro
from sid_policies import GAMMA, PILOT, STATS, THM, THX, Bank

OP = PILOT          # explicit and immutable; this driver no longer reads module state
C, s = OP.C_eff, OP.s

STATE_NAME = "res8_switch.json"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


# explore-then-switch policy defined on segment age (stationary w.r.t. filter restarts)
def run_batch_age(bank, B, true_tcc, h, R, seed, max_steps, null):
    STATS["run_batch_calls"] += 1
    r = np.random.default_rng(seed)
    alpha = [np.tile(bank.prior, (R, 1)) for _ in range(bank.K)]
    Lk = np.zeros((R, bank.K)); W = np.zeros(R); stop = np.full(R, max_steps); active = np.ones(R, bool); age = np.zeros(R, int)
    if not null:
        a_true = math.exp(-1/true_tcc); sd = s*math.sqrt(1-a_true*a_true); eps = r.normal(0, s, R)
    e1m, e1x = bank.e1[THM], bank.e1[THX]; p0m, p0x = bank.p0(THM), bank.p0(THX)
    for n in range(max_steps):
        mid = age < B
        thv = np.where(mid, THM, THX); p0v = np.where(mid, p0m, p0x)
        if null:
            y = r.random(R) < p0v
        else:
            eps = a_true*eps + sd*r.normal(0, 1, R); y = r.random(R) < 0.5*(1+C*np.cos(thv+eps))
        e1 = np.where(mid[:, None], e1m[None, :], e1x[None, :]); ey = np.where(y[:, None], e1, 1-e1)
        logz = np.empty((R, bank.K))
        for k in range(bank.K):
            al = alpha[k]@bank.T[k]; al *= ey; z = al.sum(1); al /= z[:, None]; alpha[k] = al; logz[:, k] = np.log(z)
        A = Lk+logz; mA = A.max(1, keepdims=True); num = mA[:, 0]+np.log(np.exp(A-mA).sum(1))
        mB = Lk.max(1, keepdims=True); den = mB[:, 0]+np.log(np.exp(Lk-mB).sum(1))
        l0 = np.where(y, np.log(p0v), np.log(1-p0v)); W += (num-den)-l0; Lk = A; age += 1
        hit = active & (W >= h); stop[hit] = n+1; active &= ~hit
        STATS["simulated_steps"] += 1
        if not active.any(): break
        rs = W < -1e-9
        if rs.any():
            W[rs] = 0.0; Lk[rs] = 0.0; age[rs] = 0
            for k in range(bank.K): alpha[k][rs] = bank.prior
    return stop


def cal_age(bank_ln, B, R=32, lo=1.0, hi=6.0, iters=5):
    for i in range(iters):
        m_ = 0.5*(lo+hi); st = run_batch_age(bank_ln, B, None, m_, R, 300+i, 150_000, True); m = st.mean()
        if m > GAMMA: hi = m_
        else: lo = m_
    h = 0.5*(lo+hi); st = run_batch_age(bank_ln, B, None, h, 2*R, 399, 150_000, True)
    return h, st.mean(), st.std()/math.sqrt(2*R)


def main(argv):
    resume = "--resume" in argv
    sid_repro.print_banner("explore-then-switch", resume,
                           "bisection 300-304, confirmation 399, delays 500 + int(tau_c/c)")
    bank_ln = Bank([1.0, 4.0, 10.0, 25.0], OP)
    state = sid_repro.load_checkpoint(STATE_NAME, resume) or {}
    reference = sid_repro.load_reference(STATE_NAME) or {}
    computed = cached = 0

    for B in (300, 1000):
        if str(B) in state:
            cached += 1; log(f"resumed switch@{B}"); continue
        h, m, se = cal_age(bank_ln, B); log(f"switch@{B}: h*={h:.3f} ARL={m:.0f}+-{se:.0f}")
        row = {}
        for tcc in (20.0, 5.0, 1.0):
            st = run_batch_age(bank_ln, B, tcc, h, 64, 500+int(tcc), 100_000, False)
            row[str(tcc)] = [st.mean(), st.std()/8]
            log(f"   tc/c={tcc:4.0f}: delay={st.mean():6.0f} +- {st.std()/8:4.0f}")
        state[str(B)] = [h, m, row]
        sid_repro.save_checkpoint(STATE_NAME, state)
        computed += 1

    verdicts, n_pass, n_fail = [], 0, 0
    for B, entry in state.items():
        ref = reference.get(B)
        if ref is None:
            verdicts.append(f"  NO-REFERENCE  switch@{B}"); continue
        if entry[0] != ref[0]:
            n_fail += 1
            verdicts.append(f"  FAIL  switch@{B}: threshold h* {entry[0]!r} != archived {ref[0]!r} (exact match required)")
            continue
        v, p, f = sid_repro.compare_rows(entry[2], ref[2], threshold_index=None, mean_index=0,
                                         se_index=1, label=f"switch@{B} delay tc/c=")
        verdicts += v; n_pass += p; n_fail += f

    log("done8")
    return sid_repro.report(computed, cached, verdicts, n_pass, n_fail, time.time()-T0)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
