"""Rebuild figures/sid_policy_delays.png from stored outputs (no recomputation).

Refuses to rebuild from withdrawn inputs. Four delay entries in res6_policies.json were
withdrawn as C18 (notes/2026-09-03-note-04-reproduction-defect.md): they were measured at
two calibration thresholds whose provenance is lost, and at tau_c/c = 20 one of them is the
benchmark every ratio on this figure divides by. Pass --acknowledge-withdrawn to rebuild
anyway, e.g. to reproduce the historical figure deliberately.
"""
import os, sys, json, math
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
# Reads the published archive by design -- it rebuilds from stored outputs -- but writes the
# rebuilt figure into analysis/reproduction/figures/, never over the archived one.
OUTD = os.path.join(HERE, "..", "outputs")
FIG = os.path.join(HERE, "..", "reproduction", "figures"); os.makedirs(FIG, exist_ok=True)
PARCH, SEA, SIG, INK, STONE = "#f5f0e8", "#2c5f7c", "#c0392b", "#1a1a1a", "#6b6b6b"
# Rebuilt from the RECALIBRATED chain since 8 Sept 2026. The previous figure plotted the
# withdrawn C18 delays, whose tau_c/c=20 benchmark is the withdrawn oracle-mid(tc=20) row that
# every ratio divides by. res6_policies_pilot_recal.json has all seven policies inside the
# +-30 % matched-ARL envelope. --legacy reproduces the historical figure deliberately.
_recal = "--legacy" not in sys.argv
_r6 = "res6_policies_pilot_recal.json" if _recal else "res6_policies.json"
_r8 = "res8_switch_pilot_recal.json" if _recal else "res8_switch.json"
st = json.load(open(os.path.join(OUTD, _r6))); r8 = json.load(open(os.path.join(OUTD, _r8)))
r8 = r8.get("switch", r8)
tccs = [20.0, 5.0, 1.0]

# Withdrawn inputs (C17/C18). The benchmark at tau_c/c = 20 is one of them, so every ratio
# drawn at that tau_c divides by a withdrawn quantity.
WITHDRAWN = {"oracle-mid(tc=20)", "learner-interleave-B10(bank)"}
if not _recal:
    if not any(a == "--acknowledge-withdrawn" for a in sys.argv):
        sys.exit("sid_fig_policy_delays.py --legacy: res6_policies.json carries the entries "
                 "withdrawn as C17/C18 for\n  " + ", ".join(sorted(WITHDRAWN)) +
                 "\n  Rebuilding would republish a figure whose benchmark has no provenance.\n"
                 "  See notes/2026-09-03-note-04-reproduction-defect.md. Pass "
                 "--acknowledge-withdrawn\n  to rebuild the historical figure deliberately.")
    print("  --legacy --acknowledge-withdrawn: rebuilding from inputs withdrawn as C17/C18")
else:
    # The default path reads the recalibrated chain, so the guard has nothing to guard. It is
    # replaced by a live check: every policy drawn must be inside the matched-ARL envelope,
    # because every ratio on this figure divides by a benchmark.
    _bad = {k: v[1] for k, v in st["cal"].items() if abs(v[1] - 3.0e4) / 3.0e4 > 0.30}
    _sw = {f"switch@{B}": r[1] for B, r in r8.items() if abs(r[1] - 3.0e4) / 3.0e4 > 0.30}
    _bad.update(_sw)
    if _bad:
        print("  EXCLUDED from the figure, calibrated outside the +-30 % envelope: "
              + ", ".join(f"{k} ({100*(v-3.0e4)/3.0e4:+.1f} %)" for k, v in sorted(_bad.items())))

pol = {"extremum-only": ("extremum-only", INK, "-"), "mid-fringe (bank)": ("learner-mid(bank)", SEA, "-"),
       "interleave B=1 (bank)": ("learner-interleave-B1(bank)", STONE, "--"), "interleave B=10 (bank)": ("learner-interleave-B10(bank)", STONE, ":")}
fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150, facecolor=PARCH); ax.set_facecolor(PARCH)
bench = [min(st["delays"][str(t)][f"oracle-mid(tc={int(t)})"][0], st["delays"][str(t)]["extremum-only"][0]) for t in tccs]
ax.plot(tccs, bench, "k*", ms=11, label="best fixed-endpoint benchmark (knows $\\tau_c$)", zorder=5)
for lab, (key, col, ls) in pol.items():
    ax.errorbar(tccs, [st["delays"][str(t)][key][0] for t in tccs], [st["delays"][str(t)][key][1] for t in tccs], color=col, ls=ls, marker="o", ms=4, label=lab, capsize=2)
for B, col in ((300, SIG), (1000, "#e08070")):
    if _recal and f"switch@{B}" in _bad:
        continue          # not held to the same false-alarm rate; its ratio is incomparable
    d = r8[str(B)][2]; ax.errorbar(tccs, [d[str(float(t))][0] for t in tccs], [d[str(float(t))][1] for t in tccs], color=col, marker="s", ms=4, ls="-.", label=f"explore mid-fringe {B} shots, then extremum", capsize=2)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("$\\tau_c/c$ (true)"); ax.set_ylabel("detection delay (shots)")
# The operating point is READ from the stored runs' metadata, not hardcoded here. A figure
# that names its parameters in a string literal keeps claiming them after the run beneath it
# has moved (roadmap G).
#
# This figure combines TWO outputs -- res6_policies (the seven policies) and res8_switch (the
# explore-then-switch curves) -- so it must not label both from one file's metadata. If the
# two were produced at different operating points the figure would be meaningless, and it
# refuses rather than drawing it.
def _opof(doc):
    m = doc.get("meta") or {}
    return (m.get("config") or {}).get("operating_point") or m.get("operating_point")

_op6, _op8 = _opof(st), _opof(r8)
if _op6 and _op8 and _op6 != _op8:
    sys.exit(f"refusing to combine outputs from different operating points: "
             f"res6_policies {_op6} vs res8_switch {_op8}")
_op = _op6 or _op8
if _op and _op6 and _op8:
    _optxt = f"$\\bar C_{{\\rm eff}}={_op['C_eff']:g}$, $s={_op['s']:g}$"
elif _op:
    _which = "res6_policies" if _op6 else "res8_switch"
    _optxt = (f"$\\bar C_{{\\rm eff}}={_op['C_eff']:g}$, $s={_op['s']:g}$ "
              f"(recorded in {_which} only)")
else:
    _optxt = "operating point not recorded in either output"
ax.set_title(f"Policies at matched $\\hat{{E}}_0[T]\\approx3\\times10^4$, {_optxt}", fontsize=10)
ax.legend(fontsize=6.5)
_drawn_switch = len([b for b in r8 if f"switch@{b}" not in _bad])
fig.tight_layout()
out = os.path.join(FIG, "sid_policy_delays.png" if _recal else "sid_policy_delays_legacy.png")
fig.savefig(out)

# Postconditions (rule 6). "rebuilt" used to be printed unconditionally.
assert os.path.exists(out), "postcondition: figure not written"
_size = os.path.getsize(out)
assert _size > 10_000, f"postcondition: figure is {_size} bytes"
_target, _tol = 3.0e4, 0.30
_off = {name: abs(row[1] - _target)/_target for name, row in st["cal"].items()}
_bad = {n: v for n, v in _off.items() if v > _tol}
if _bad:
    print("  WARNING: calibrated ARLs outside the +-30 % envelope note 03 s2 states: "
          + ", ".join(f"{n} {100*v:.0f} %" for n, v in sorted(_bad.items())))
print(f"rebuilt {os.path.basename(out)} ({_size//1024} kB) from "
      f"{len(st['cal'])} calibration rows and {_drawn_switch} switch rows drawn")
