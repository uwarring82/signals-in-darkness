import os
OUTD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'outputs')
import sys, json, math, time
sys.argv=["x","noop"]
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sid_run6s.py")).read().split("arg=sys.argv[1]")[0]
exec(src)
# explore-then-switch policy defined on segment age (stationary w.r.t. filter restarts)
def run_batch_age(bank, B, true_tcc, h, R, seed, max_steps, null):
    r=np.random.default_rng(seed)
    alpha=[np.tile(bank.prior,(R,1)) for _ in range(bank.K)]
    Lk=np.zeros((R,bank.K)); W=np.zeros(R); stop=np.full(R,max_steps); active=np.ones(R,bool); age=np.zeros(R,int)
    if not null:
        a_true=math.exp(-1/true_tcc); sd=s*math.sqrt(1-a_true*a_true); eps=r.normal(0,s,R)
    e1m,e1x=bank.e1[THM],bank.e1[THX]; p0m,p0x=bank.p0(THM),bank.p0(THX)
    for n in range(max_steps):
        mid=age<B
        thv=np.where(mid,THM,THX); p0v=np.where(mid,p0m,p0x)
        if null: y=r.random(R)<p0v
        else:
            eps=a_true*eps+sd*r.normal(0,1,R); y=r.random(R)<0.5*(1+C*np.cos(thv+eps))
        e1=np.where(mid[:,None],e1m[None,:],e1x[None,:]); ey=np.where(y[:,None],e1,1-e1)
        logz=np.empty((R,bank.K))
        for k in range(bank.K):
            al=alpha[k]@bank.T[k]; al*=ey; z=al.sum(1); al/=z[:,None]; alpha[k]=al; logz[:,k]=np.log(z)
        A=Lk+logz; mA=A.max(1,keepdims=True); num=mA[:,0]+np.log(np.exp(A-mA).sum(1))
        mB=Lk.max(1,keepdims=True); den=mB[:,0]+np.log(np.exp(Lk-mB).sum(1))
        l0=np.where(y,np.log(p0v),np.log(1-p0v)); W+=(num-den)-l0; Lk=A; age+=1
        hit=active&(W>=h); stop[hit]=n+1; active&=~hit
        if not active.any(): break
        rs=W<-1e-9
        if rs.any():
            W[rs]=0.0; Lk[rs]=0.0; age[rs]=0
            for k in range(bank.K): alpha[k][rs]=bank.prior
    return stop
def cal_age(B,R=32,lo=1.0,hi=6.0,iters=5):
    for i in range(iters):
        m_=0.5*(lo+hi); st=run_batch_age(bank_ln,B,None,m_,R,300+i,150_000,True); m=st.mean()
        if m>gamma: hi=m_
        else: lo=m_
    h=0.5*(lo+hi); st=run_batch_age(bank_ln,B,None,h,2*R,399,150_000,True)
    return h,st.mean(),st.std()/math.sqrt(2*R)
out={}
for B in (300,1000):
    h,m,se=cal_age(B); log(f"switch@{B}: h*={h:.3f} ARL={m:.0f}+-{se:.0f}")
    row={}
    for tcc in (20.0,5.0,1.0):
        st=run_batch_age(bank_ln,B,tcc,h,64,500+int(tcc),100_000,False); row[tcc]=(st.mean(),st.std()/8)
        log(f"   tc/c={tcc:4.0f}: delay={st.mean():6.0f} +- {st.std()/8:4.0f}")
    out[B]=(h,m,row)
json.dump({str(k):[v[0],v[1],{str(a):b for a,b in v[2].items()}] for k,v in out.items()},open("res8_switch.json","w"))
log("done8")
