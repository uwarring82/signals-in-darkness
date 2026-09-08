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
    python sid_run8.py [--resume] [--operating-point=stress]

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
from sid_policies import (ARL_ENVELOPE, CAL_BRACKET, GAMMA, SEED_OFFSET, STATS, THM, THX,
                          Bank, operating_point_from_argv, state_name_for)

# There are deliberately NO module-level C and s aliases here. An earlier version of this
# fix removed the `from sid_policies import C, s` and then immediately rebuilt the same
# coupling as `C, s = OP.C_eff, OP.s`, which reintroduced the exact defect roadmap G exists
# to remove: run_batch_age drew its post-change process from those module names while its
# filter and null came from bank.op, so a bank built at a second operating point would have
# been simulated against the pilot's process. Freezing OP does not freeze a derived binding.
# Everything below reads bank.op.

CAL_R = 32
CAL_SEEDS = "bisection 300-304, confirmation 399, delays 500 + int(tau_c/c)"
B_VALUES = (300, 1000)
BANK_TCCS = [1.0, 4.0, 10.0, 25.0]
DELAY_TCCS = (20.0, 5.0, 1.0)
NULL_CAP, DELAY_CAP = 150_000, 100_000
KNOWN_FLAGS = ("--resume", "--operating-point=", "--no-reference")


def run_config(op, op_name):
    """The configuration these thresholds depend on. A change here invalidates them.

    R and iters are now the values actually used, not decorative: before 7 Sept 2026 this
    declared iters=5 while cal_age hard-coded its own, and omitted the bank correlation-time
    list and both step caps -- so editing the bank would have changed every threshold while
    leaving the digest byte-identical and --resume willing to consume the stale checkpoint.
    """
    lo, hi, iters = CAL_BRACKET[op_name]
    return {"operating_point": op.as_dict(), "operating_point_name": op_name,
            "gamma": GAMMA, "R": CAL_R, "iters": iters, "bracket": [lo, hi],
            "seed_offset": SEED_OFFSET[op_name], "bank_tccs": BANK_TCCS,
            "delay_tccs": list(DELAY_TCCS), "null_cap": NULL_CAP, "delay_cap": DELAY_CAP,
            "seeds": CAL_SEEDS, "B_values": list(B_VALUES),
            "method": "secant-refined" if op_name.endswith("_recal") else "bisection",
            "confirm_R": CONFIRM_R, "max_secant": MAX_SECANT, "arl_envelope": ARL_ENVELOPE,
            "secant_seed_schedule": "anchors seed0+50,+51; secant steps seed0+60..; confirm seed0+99"}
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)


# explore-then-switch policy defined on segment age (stationary w.r.t. filter restarts)
def run_batch_age(bank, B, true_tcc, h, R, seed, max_steps, null):
    STATS["run_batch_calls"] += 1
    r = np.random.default_rng(seed)
    C, s = bank.op.C_eff, bank.op.s        # from the bank, never from module state
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


CONFIRM_R, MAX_SECANT = 64, 4


def cal_age(bank_ln, B, lo, hi, iters, seed0, R=CAL_R, refine=False):
    """As sid_policies.calibrate, for the age-based schedule. Returns the bracket endpoint too.

    The bracket is passed in rather than hard-coded: it duplicated calibrate's pilot-era
    [1.0, 6.0] verbatim, so roadmap B's second operating point would have inherited the same
    un-bracketed bisection that pins a threshold to an untested bracket end.
    """
    lo0, hi0 = lo, hi
    for i in range(iters):
        m_ = 0.5*(lo+hi)
        st = run_batch_age(bank_ln, B, None, m_, R, seed0+i, NULL_CAP, True); m = st.mean()
        if m > GAMMA: hi = m_
        else: lo = m_
    h = 0.5*(lo+hi)
    if refine:
        # Same secant root-find as sid_policies.calibrate_refined. Until 8 Sept 2026 this
        # driver had neither the refinement NOR an envelope gate, so a *_recal run silently
        # produced plain-bisection thresholds identical to the un-recalibrated ones.
        pts = []
        for k, hk in enumerate((lo, hi)):
            mk = run_batch_age(bank_ln, B, None, hk, CONFIRM_R, seed0+50+k, NULL_CAP, True).mean()
            if mk > 0:
                pts.append((hk, math.log(mk)))
        target = math.log(GAMMA)
        for step in range(MAX_SECANT):
            if len(pts) < 2:
                break
            (h1, y1), (h2, y2) = pts[-2], pts[-1]
            if y2 == y1:
                break
            h = min(max(h1 + (target-y1)*(h2-h1)/(y2-y1), lo0), hi0)
            mk = run_batch_age(bank_ln, B, None, h, CONFIRM_R, seed0+60+step, NULL_CAP, True).mean()
            if mk <= 0:
                break
            pts.append((h, math.log(mk)))
        # As sid_policies.calibrate_refined: no early stop on a single noisy probe.
        if pts:
            h = min(pts, key=lambda pt: abs(pt[1]-target))[0]
    st = run_batch_age(bank_ln, B, None, h, 2*R, seed0+99, NULL_CAP, True)
    endpoint = "floor" if lo == lo0 else ("ceiling" if hi == hi0 else None)
    m = st.mean()
    return (h, m, st.std()/math.sqrt(2*R), int((st >= NULL_CAP).sum()), endpoint,
            abs(m-GAMMA)/GAMMA <= ARL_ENVELOPE)


def main(argv):
    op_name, op = operating_point_from_argv(argv)
    state_name = state_name_for("res8_switch.json", op_name)
    resume = "--resume" in argv
    allow_no_reference = "--no-reference" in argv
    unknown = [a for a in argv[1:]
               if a.startswith("--") and not any(a == f or a.startswith(f) for f in KNOWN_FLAGS)]
    if unknown:
        print(f"unrecognised option(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"  known: {', '.join(KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    sid_repro.print_banner("explore-then-switch", resume,
                           "bisection 300-304, confirmation 399, delays 500 + int(tau_c/c)")
    log(f"operating point: {op_name} ({op.label()}) -> {state_name}")
    bank_ln = Bank(BANK_TCCS, op)
    want = sid_repro.run_metadata(run_config(op, op_name))
    bracket_failures = []
    envelope_failures = []

    raw = sid_repro.load_checkpoint(state_name, resume) or {}
    # Checkpoints written before roadmap G were a flat {B: row} map with no identity. They
    # are refused rather than silently resumed: an unidentified checkpoint is exactly what
    # cost C17 and C18.
    state = raw.get("switch", {}) if "switch" in raw else {}
    if resume and raw:
        why = sid_repro.incompatibilities(raw.get("meta"), want)
        if why:
            print("refusing to resume a checkpoint from a different run:", file=sys.stderr)
            for reason in why:
                print(f"  - {reason}", file=sys.stderr)
            print(f"  drop analysis/reproduction/{state_name} and recompute.", file=sys.stderr)
            return 2
    elif raw and not resume:
        state = {}          # fresh by default; the checkpoint is overwritten, not consumed

    published = sid_repro.load_reference(state_name)
    if published is None and not allow_no_reference:
        print(f"no archived reference for operating point {op_name!r} ({state_name} is not in "
              f"analysis/outputs).", file=sys.stderr)
        print("  This run would ESTABLISH those numbers, not verify them. Pass --no-reference "
              "to say so deliberately.", file=sys.stderr)
        return 2
    reference = published or {}
    computed = cached = 0

    for B in B_VALUES:
        if str(B) in state:
            cached += 1; log(f"resumed switch@{B}"); continue
        lo, hi, iters = CAL_BRACKET[op_name]
        h, m, se, ncap, endpoint, inside = cal_age(bank_ln, B, lo, hi, iters,
                                                   300 + SEED_OFFSET[op_name],
                                                   refine=op_name.endswith("_recal"))
        if not inside:
            envelope_failures.append((f"switch@{B}", h, m, 100*(m-GAMMA)/GAMMA))
        log(f"switch@{B}: h*={h:.3f} ARL={m:.0f}+-{se:.0f} (capped {ncap}/{2*CAL_R})")
        if endpoint:
            bracket_failures.append((f"switch@{B}", endpoint, h, m))
            log(f"  ** bracket {endpoint} never moved: h*={h:.6f} is set by the bracket "
                f"[{lo}, {hi}], not by the data; ARL {m:.0f} is "
                f"{100*(m-GAMMA)/GAMMA:+.0f} % off target **")
        row = {}
        for tcc in DELAY_TCCS:
            st = run_batch_age(bank_ln, B, tcc, h, 64, 500+int(tcc)+SEED_OFFSET[op_name],
                               DELAY_CAP, False)
            nc = int((st >= DELAY_CAP).sum())
            row[str(tcc)] = [st.mean(), st.std()/8, nc, st.tolist()]
            log(f"   tc/c={tcc:4.0f}: delay={st.mean():6.0f} +- {st.std()/8:4.0f} (capped {nc}/64)")
        state[str(B)] = [h, m, row]
        sid_repro.save_checkpoint(state_name, {"switch": state, "meta": want})
        computed += 1

    verdicts, n_pass, n_fail = [], 0, 0
    # The published archive predates roadmap G and is a flat {B: row} map; it is read in
    # that shape deliberately, and its lack of identity is a fact about it, not a bug here.
    ref_rows = reference.get("switch", reference)
    for B, entry in state.items():
        ref = ref_rows.get(B)
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
    status = sid_repro.report(computed, cached, verdicts, n_pass, n_fail, time.time()-T0)
    if published is None:
        print(f"\nNOT A COMPARISON: no archived reference for operating point {op_name!r}.")
    if envelope_failures:
        print(f"\nARL ENVELOPE BREACHES ({len(envelope_failures)}): a policy outside "
              f"+-{100*ARL_ENVELOPE:.0f} % is not held to the same false-alarm rate as the "
              f"others, so ratios built on it are incomparable.", file=sys.stderr)
        for nm, h, m, pct in envelope_failures:
            print(f"  {nm}: h*={h:.6f}, ARL={m:.0f} ({pct:+.1f} %)", file=sys.stderr)
        status = status or 4
    if bracket_failures:
        print(f"\nCALIBRATION BRACKET FAILURES ({len(bracket_failures)}):", file=sys.stderr)
        for name, end, h, m in bracket_failures:
            print(f"  {name}: {end} pinned, h*={h:.6f}, ARL={m:.0f}", file=sys.stderr)
        status = status or 3
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
