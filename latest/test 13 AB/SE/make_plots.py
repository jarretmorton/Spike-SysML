#!/usr/bin/env python3
"""
make_plots.py -- regenerates every figure in the record from the telemetry values
extracted during the runs. Standalone: matplotlib only, no network, no live hub.

Data below is transcribed from the hub telemetry dumps (run ids in each caption).
Heading channels were logged as deci-degrees on the hub and are divided by 10 here.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "/mnt/user-data/outputs/plots"
import os
os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, TEAL, RED, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#898781"


def save(fig, name):
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(f"{OUT}/{name}.{ext}", dpi=150)
    plt.close(fig)
    print("wrote", name)


# ---- 1. GATE A sensitivity ranking -----------------------------------------
labels = ["psi_brake\nbrake travel", "k_eff\nodometry scale",
          "b_offset\nranger to bumper", "a_brake\ndeceleration",
          "d_odo_drift\nslip variation", "sigma_psi\nbrake repeatability",
          "eps_scale\nranger scale err", "sigma_ls\nlatency residual",
          "l_sensor\nranger staleness", "t_chain\ncommand lag",
          "q_range\nquantisation"]
vals = [564.4, 440.9, 91.5, 78.4, 75.7, 47.1, 36.2, 20.9, 19.8, 15.8, 12.5]
cols = [ORANGE if i == 2 else BLUE for i in range(len(vals))]
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(range(len(vals))[::-1], vals, color=cols, height=0.68)
ax.set_yticks(range(len(vals))[::-1]); ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel("clearance / margin swing across the assumed prior range (mm)")
ax.set_title("GATE A sensitivity ranking (orange = no onboard channel: the costed measurement)",
             fontsize=10)
ax.grid(axis="x", alpha=.3); ax.set_axisbelow(True)
save(fig, "1_gateA_sensitivity")

# ---- 2. CAL-1 approach 1: the echo loss ------------------------------------
t1 = [18833, 18878, 18898, 18918, 19023, 19043, 19068, 19088, 19193, 19214,
      19233, 19253, 19358, 19378, 19403, 19423, 19529, 22121]
v1 = [1042, 1039, 1037, 1034, 1013, 1008, 1002, 996, 959, 952,
      943, 935, 899, 890, 882, 879, 1022, 2000]
t0 = t1[0]; x1 = [t - t0 for t in t1]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(x1[:16], v1[:16], "-o", color=BLUE, ms=4, label="tracking the wall (valid)")
ax.plot(x1[15:], v1[15:], "--^", color=RED, ms=9, label="echo lost - readings are artifacts")
ax.set_xlabel("time since approach start (ms)"); ax.set_ylabel("reported forward range (mm)")
ax.set_title("CAL-1 approach 1: the rover arced away and lost the specular echo\n"
             "(run-20260729-195903)", fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=.3); ax.set_axisbelow(True)
save(fig, "2_cal1_echo_loss")

# ---- 3. CAL-1 heading: the arc --------------------------------------------
th = [738, 4749, 8398, 12066, 18757, 18908, 19058, 19208, 19359, 19509,
      21010, 21816, 25021, 26804, 28574, 30353]
hv = [0, 2.76, 2.42, 1.72, 0.89, 0.84, 0.37, -0.63, -3.54, -6.71,
      -15.04, -15.05, -16.39, -17.49, -18.74, -20.54]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot([t / 1000 for t in th], hv, "-o", color=ORANGE, ms=4)
ax.axvspan(18.76, 19.57, color=GREY, alpha=.18)
ax.annotate("max-speed pass\n-7.6 deg over 260 mm", xy=(19.2, -4), xytext=(21, -6),
            fontsize=8, arrowprops=dict(arrowstyle="->", color=GREY))
ax.set_xlabel("time since program start (s)"); ax.set_ylabel("IMU heading (deg)")
ax.set_title("CAL-1: a systematic 1961 mm arc from a 6.2% wheel-speed mismatch\n"
             "(run-20260729-195903)", fontsize=10)
ax.grid(alpha=.3); ax.set_axisbelow(True)
save(fig, "3_cal1_heading_arc")

# ---- 4. CAL-2 approach 2: the fix, and the first ranging-triggered stop ----
t2 = [17921, 18322, 18447, 18487, 18676, 18696, 18741, 18866, 18906, 19031,
      19076, 19201, 19241]
v2 = [1014, 852, 661, 645, 570, 557, 536, 477, 460, 404, 388, 333, 319]
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot([t - t2[0] for t in t2], v2, "-o", color=TEAL, ms=4)
ax.set_xlabel("time since approach start (ms)"); ax.set_ylabel("reported forward range (mm)")
ax.set_title("CAL-2 approach 2: monotone to the stop, no dropouts.\n"
             "First run where the fused ranging trigger fired (run-20260729-203131)",
             fontsize=10)
ax.grid(alpha=.3); ax.set_axisbelow(True)
save(fig, "4_cal2_rehearsal")

# ---- 5. Operation: estimate vs ground truth, and the saturation diagnostic --
runs = [1, 2, 3, 4, 5]
com = [25.97, 27.26, 23.84, 24.34, 24.40]
mea = [24.0, 27.0, 21.0, 21.0, 19.0]
rr = [40.00, 44.00, 40.86, 41.00, 41.00]
delta = [c - m for c, m in zip(com, mea)]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
w = 0.36
a1.bar([r - w / 2 for r in runs], com, w, label="my frozen estimate", color=BLUE)
a1.bar([r + w / 2 for r in runs], mea, w, label="operator measurement", color=ORANGE)
a1.axhline(26.0, color=GREY, ls="--", lw=1, label="commanded target 26.0 mm")
a1.axhline(10.7, color=RED, ls=":", lw=1, label="frozen 3-sigma lower bound")
a1.set_xticks(runs); a1.set_xlabel("scored run"); a1.set_ylabel("clearance (mm)")
a1.set_title("5/5 no contact; all inside the frozen band", fontsize=10)
a1.legend(fontsize=7); a1.grid(axis="y", alpha=.3); a1.set_axisbelow(True)

a2.scatter([r - 40 for r in rr], delta, s=70, color=BLUE, zorder=3)
for i, r in enumerate(runs):
    a2.annotate(f"run {r}", (rr[i] - 40, delta[i]), textcoords="offset points",
                xytext=(7, 4), fontsize=8)
a2.axhline(0, color=GREY, lw=1)
a2.set_xlabel("rest reading above the 40 mm vendor floor (mm)")
a2.set_ylabel("estimate error (estimate - measured, mm)")
a2.set_title("Saturation, not noise: the one run clear of the floor\nwas accurate to 0.26 mm",
             fontsize=10)
a2.grid(alpha=.3); a2.set_axisbelow(True)
save(fig, "5_operation_reconciliation")
print("all figures written to", OUT)
