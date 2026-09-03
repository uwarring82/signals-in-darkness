import os
import sys, math, json, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
import numpy as np
from sid_lib import I_ext_exact, DB, rk_exact
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "figures")
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

C, s = 0.4, 0.5
THM, THX = math.pi/2, math.pi          # mid-fringe, dark extremum
M, L = 61, 5.0

# ---------------- batched latent-AR(1) bank simulator ----------------
class Bank:
    def __init__(self, tccs):
        self.g = np.linspace(-L*s, L*s, M)
        self.prior = np.exp(-self.g**2/(2*s*s)); self.prior /= self.prior.sum()
        self.T = []
        for tcc in tccs:
            a = math.exp(-1/tcc); sd = s*math.sqrt(1-a*a)
            T = np.exp(-(self.g[None, :]-a*self.g[:, None])**2/(2*sd*sd)); T /= T.sum(1, keepdims=True)
            self.T.append(T)
        self.K = len(tccs)
        self.e1 = {th: 0.5*(1+C*np.cos(th+self.g)) for th in (THM, THX)}
    def p0(self, th): return 0.5*(1+C*math.cos(th))

def run_batch(bank, sched, true_tcc, h, R, seed, max_steps, null):
    """sched(n) -> theta. Returns stopping step per run (max_steps if not stopped). Mixture-LR CUSUM with reset."""
    r = np.random.default_rng(seed)
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

    for i in range(iters):
        mid = 0.5*(lo+hi); m, se, nc = arl_of(bank, sched, mid, R, seed+i)
        if m > gamma: hi = mid
        else: lo = mid
    h = 0.5*(lo+hi); m, se, nc = arl_of(bank, sched, h, 2*R, seed+99)
    return h, m, se, nc

def delay_of(bank, sched, true_tcc, h, R, seed, cap=100_000):
    st = run_batch(bank, sched, true_tcc, h, R, seed, cap, False)
    return st.mean(), st.std()/math.sqrt(R), (st >= cap).sum()


import os
STATE=os.path.join(OUTD, "res6_policies.json")
state=json.load(open(STATE)) if os.path.exists(STATE) else {"cal":{}, "delays":{}}
gamma=3.0e4
bank_or={tcc: Bank([tcc]) for tcc in (20.0,5.0,1.0)}
bank_ln=Bank([1.0,4.0,10.0,25.0])
sched_mid=lambda n: THM
sched_ext=lambda n: THX
def make_interleave(B): return lambda n: THM if (n//B)%2==0 else THX
policies={
 "oracle-mid(tc=20)":(bank_or[20.0],sched_mid),
 "oracle-mid(tc=5)":(bank_or[5.0],sched_mid),
 "oracle-mid(tc=1)":(bank_or[1.0],sched_mid),
 "extremum-only":(bank_or[20.0],sched_ext),
 "learner-mid(bank)":(bank_ln,sched_mid),
 "learner-interleave-B10(bank)":(bank_ln,make_interleave(10)),
 "learner-interleave-B1(bank)":(bank_ln,make_interleave(1)),
}
arg=sys.argv[1]
if arg.startswith("cal:"):
    for name in arg[4:].split(","):
        if name in state["cal"]: log("cached",name,state["cal"][name]); continue
        bk,sc=policies[name]
        h,m,se,nc=calibrate(bk,sc,gamma,R=32,iters=5)
        state["cal"][name]=[h,m,se,int(nc)]; json.dump(state,open(STATE,"w"))
        log(f"{name:32s} h*={h:.3f}  ARL={m:.0f} +- {se:.0f}  (capped runs: {nc}/64)")
elif arg=="delays":
    for true_tcc in (20.0,5.0,1.0):
        row=state["delays"].setdefault(str(true_tcc),{})
        for name,(bk,sc) in policies.items():
            if name.startswith("oracle-mid") and f"(tc={int(true_tcc)})" not in name: continue
            if name in row: continue
            m,se,nc=delay_of(bk,sc,true_tcc,state["cal"][name][0],64,200+int(true_tcc))
            row[name]=[m,se,int(nc)]; json.dump(state,open(STATE,"w"))
            log(f"tc/c={true_tcc:4.0f}  {name:32s} delay={m:7.0f} +- {se:5.0f}  (capped {nc})")
    for true_tcc,row in state["delays"].items():
        orc=min(row[f"oracle-mid(tc={int(float(true_tcc))})"][0],row["extremum-only"][0])
        line=f"tc/c={float(true_tcc):4.0f} oracle={orc:6.0f} |"
        for name in ("extremum-only","learner-mid(bank)","learner-interleave-B10(bank)","learner-interleave-B1(bank)"):
            line+=f" {name}: +{row[name][0]-orc:6.0f} ({row[name][0]/orc:4.2f}x)"
        log(line)
log("stage done")
