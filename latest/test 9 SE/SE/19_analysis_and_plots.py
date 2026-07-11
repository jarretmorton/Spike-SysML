#!/usr/bin/env python3
"""
Wall-Stop Rover — analysis & plots.
Self-contained: all series below were extracted from hub telemetry
(get_telemetry) during the session. Regenerates 17_plots.png.
    python3 19_analysis_and_plots.py
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# DATA (from telemetry)
# ----------------------------------------------------------------------
# Calibration run-20260709-214225, cycle 0: ranger-A distance vs |left encoder|
enc  = np.array([654,688,721,755,790,829,862,895,995,1034,1067,1100,1135,
                 1171,1203,1237,1276,1309,1342,1377], float)
distA= np.array([731,717,690,671,658,634,612,592,548,539,516,493,473,
                 464,440,422,412,393,370,351], float)

# Same run, three cycles: trigger threshold vs the two rangers' REST readings
cyc      = np.array([0,1,2])
trig     = np.array([350,300,250])     # cmd threshold on ranger A
A_rest   = np.array([298,288,294])     # ranger A pins near its ~288 mm floor
B_rest   = np.array([162,120,114])     # ranger B keeps resolving downward

# Operation: 5 scored runs
run      = np.array([1,2,3,4,5])
onboard  = np.array([24,27,27,29,26])  # rest_A - c_offset(21)
operator = np.array([19,22,14,30,15])  # ground truth
restA_op = np.array([45,48,48,50,47])
coff_op  = restA_op - operator         # effective c_offset per run
COFF_VERIF = 21.0

# ----------------------------------------------------------------------
# STATS
# ----------------------------------------------------------------------
k, b = np.polyfit(enc, distA, 1)          # slope = -k_gain
kfit = -k
resid = distA - (k*enc + b)
r2 = 1 - np.sum(resid**2)/np.sum((distA-distA.mean())**2)
print("k_gain = %.3f mm/deg   R^2 = %.4f" % (kfit, r2))
print("operator gap: mean=%.1f min=%d max=%d sd=%.1f  -> %.1f sigma to contact"
      % (operator.mean(), operator.min(), operator.max(), operator.std(),
         operator.mean()/operator.std()))
print("onboard bias (op-est) mean = %.1f mm" % (operator-onboard).mean())
print("effective c_offset: %s  mean=%.1f (verif was %.0f)"
      % (coff_op.tolist(), coff_op.mean(), COFF_VERIF))

# ----------------------------------------------------------------------
# PLOTS
# ----------------------------------------------------------------------
plt.rcParams.update({"font.size":10,"axes.grid":True,"grid.alpha":0.3,
                     "figure.dpi":130})
fig, ax = plt.subplots(2,2, figsize=(12.5,9))
fig.suptitle("Wall-Stop Rover — calibration & operation results", fontsize=14, fontweight="bold")

# (1) k_gain fit
a=ax[0,0]
xs=np.linspace(enc.min(),enc.max(),50)
a.scatter(enc,distA,s=28,color="#1f77b4",label="cycle-0 samples",zorder=3)
a.plot(xs, k*xs+b, color="#d62728", lw=2,
       label="fit: k = %.3f mm/deg (R²=%.3f)"%(kfit,r2))
a.set_xlabel("left wheel encoder (deg)"); a.set_ylabel("ranger-A distance (mm)")
a.set_title("(1) Encoder → distance calibration (k_gain)"); a.legend(loc="upper right")

# (2) sensor floor
a=ax[0,1]
w=0.35
a.bar(cyc-w/2, A_rest, w, color="#1f77b4", label="ranger A rest")
a.bar(cyc+w/2, B_rest, w, color="#2ca02c", label="ranger B rest")
a.plot(cyc, trig, "o--", color="#7f7f7f", label="cmd trigger threshold")
a.axhspan(285,300, color="#1f77b4", alpha=0.12)
a.text(1.0, 305, "ranger-A floor ≈ 288–298 mm (pinned)", ha="center",
       fontsize=9, color="#1f77b4")
a.set_xticks(cyc); a.set_xlabel("calibration cycle")
a.set_ylabel("distance (mm)"); a.set_ylim(0,380)
a.set_title("(2) Ranger-A floors; ranger-B resolves closer"); a.legend(loc="lower left")

# (3) operation results
a=ax[1,0]
a.bar(run-w/2, onboard, w, color="#9ecae1", label="onboard estimate")
a.bar(run+w/2, operator, w, color="#08519c", label="operator (ground truth)")
a.axhline(0, color="#d62728", lw=2)
a.text(5.15, 1.5, "contact", color="#d62728", fontsize=9, ha="right")
a.axhline(operator.mean(), color="#000", ls=":", lw=1.5,
          label="operator mean = %.0f mm"%operator.mean())
for r,g in zip(run,operator):
    a.text(r+w/2, g+0.6, str(g), ha="center", fontsize=8)
a.set_xticks(run); a.set_xlabel("operation run")
a.set_ylabel("final gap (mm)"); a.set_ylim(0,34)
a.set_title("(3) Operation: 5/5 no contact, mean 20 mm (best 14)"); a.legend(loc="upper left", fontsize=8)

# (4) reconciliation — effective c_offset
a=ax[1,1]
a.bar(run, coff_op, 0.5, color="#fdae6b", label="effective c_offset / run")
a.axhline(COFF_VERIF, color="#d62728", ls="--", lw=2,
          label="verification value = 21")
a.axhline(coff_op.mean(), color="#000", ls=":", lw=1.5,
          label="operation mean = %.1f"%coff_op.mean())
for r,c in zip(run,coff_op):
    a.text(r, c+0.4, str(c), ha="center", fontsize=8)
a.set_xticks(run); a.set_xlabel("operation run")
a.set_ylabel("c_offset (mm)"); a.set_ylim(0,40)
a.set_title("(4) Why estimates ran ~7 mm high:\nc_offset varied 20–34, verif sat low")
a.legend(loc="upper left", fontsize=8)

fig.tight_layout(rect=[0,0,1,0.97])
out="/mnt/user-data/outputs/17_plots.png"
fig.savefig(out, bbox_inches="tight")
print("wrote", out)
