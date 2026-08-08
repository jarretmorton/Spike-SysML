#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
29_make_plots.py -- regenerate every plot shown during the campaign as files.

All figures were originally rendered inline and so existed only in the transcript.
This script rebuilds them from the telemetry values recorded in the reports, so the
plot set is reproducible rather than a screenshot.

Outputs, into plots/:
    fig1 .. fig8   as .png (150 dpi) and .svg
    wall_rover_plots.pdf   all eight, one per page
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

OUT = "plots"
os.makedirs(OUT, exist_ok=True)

BLUE, ORANGE, GREEN, RED, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#898781"
plt.rcParams.update({
    "figure.figsize": (9, 5), "figure.dpi": 110,
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
    "legend.frameon": False,
})
K = 0.49066
figs = []


def finish(fig, ax, title, sub=None):
    ax.set_title(title, loc="left", fontweight="medium", pad=22)
    if sub:
        ax.text(0, 1.015, sub, transform=ax.transAxes, fontsize=9, color=GREY)
    fig.tight_layout()
    figs.append(fig)


# --- fig 1 : RUN-1, the full-speed spin -------------------------------------
t = [3646, 3667, 3687, 3707, 3727, 3748, 3768, 3788, 3809, 3829, 3851, 3871,
     3892, 3912, 3932, 3952, 3972, 3992, 3998, 4008, 4018, 4028, 4038, 4048,
     4058, 4068, 4078]
d = [901, 905, 903, 902, 903, 902, 908, 908, 1003, 1003, 1008, 1014, 1014, 2000,
     2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000, 2000]
ht, hv = [3646, 3768, 3892, 3998, 4058], [0, 5.28, 31.5, 66.93, 84.32]
ot = [3646, 3687, 3727, 3768, 3809, 3851, 3892, 3932, 3972, 3998, 4018, 4038, 4058, 4078]
ov = [0, 0, 5, 15, 31, 54, 81, 110, 141, 161, 170, 157, 151, 135]
fig, ax = plt.subplots()
ax.plot(t, d, "-o", color=BLUE, ms=3, lw=1.8, label="forward distance, fused (mm)")
ax.set_xlabel("hub clock (ms)"); ax.set_ylabel("distance (mm)"); ax.set_ylim(800, 2100)
ax2 = ax.twinx(); ax2.grid(False); ax2.set_ylim(0, 200); ax2.set_ylabel("deg")
ax2.plot(ht, hv, "--s", color=ORANGE, ms=4, lw=1.8, label="heading (deg)")
ax2.plot(ot, ov, ":^", color=GREY, ms=4, lw=1.8, label="odometry (deg)")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="center right")
finish(fig, ax, "RUN-1  the rover rotated instead of approaching",
       "wrong-way guard fired at 348 ms; heading reached 95 deg; no contact")

# --- fig 2 : RUN-2, ranger A vs ranger B ------------------------------------
ta = [5177, 5219, 5259, 5299, 5339, 5379, 5419, 5459, 5499, 5539, 5579, 5620,
      5660, 5700, 5740, 5780, 5820, 5860, 5901, 5943, 5984, 6024, 6064, 6104,
      6144, 6186, 6226, 6266, 6308, 6348, 6388, 6428]
va = [1027, 1027, 1031, 1021, 1014, 1006, 993, 982, 962, 965, 954, 1046, 1015,
      1008, 1012, 970, 980, 2000, 929, 2000, 888, 2000, 2000, 2000, 2000, 719,
      702, 675, 659, 635, 619, 604]
tb = ta[:16]
vb = [906, 908, 906, 903, 888, 881, 874, 859, 847, 830, 819, 802, 788, 768, 756, 736]
fig, ax = plt.subplots()
ax.plot(ta, va, "-^", color=RED, ms=4, lw=1.8, label="ranger A  erratic, 6 of 41 dropouts")
ax.plot(tb, vb, "--o", color=BLUE, ms=4, lw=1.8, label="ranger B  clean (trace truncated)")
ax.set_xlabel("hub clock (ms)"); ax.set_ylabel("reported range (mm)")
ax.set_ylim(400, 2100); ax.legend(loc="center left")
finish(fig, ax, "RUN-2  one good forward channel and one bad one",
       "A rises 92 mm while closing on a wall; the 107 mm split was never a mounting constant")

# --- fig 3 : RUN-3, reported vs odometry-derived truth ----------------------
t3 = [3520, 3886, 4250, 4614, 4890, 5055, 5221]
rep = [886, 818, 816, 721, 443, 426, 425]
odo3 = [0, 172, 455, 726, 908, 908, 908]
tru = [887.08 - o * 0.4986 for o in odo3]
fig, ax = plt.subplots()
ax.plot(t3, rep, "-o", color=BLUE, ms=5, lw=1.8, label="reported by ranger B")
ax.plot(t3, tru, "--s", color=GREEN, ms=5, lw=1.8, label="derived from odometry")
ax.axhline(600, color=ORANGE, ls=":", lw=1.5, label="trigger threshold 600 mm")
for x, a, b in zip(t3, rep, tru):
    if a - b > 40:
        ax.annotate("", xy=(x, a), xytext=(x, b),
                    arrowprops=dict(arrowstyle="<->", color=GREY, lw=1))
        ax.text(x + 25, (a + b) / 2, f"{a-b:.0f} mm", fontsize=8, color=GREY, va="center")
ax.set_xlabel("hub clock (ms)"); ax.set_ylabel("distance (mm)"); ax.set_ylim(380, 950)
ax.legend(loc="lower left")
finish(fig, ax, "RUN-3  the ranger cannot track a closing wall",
       "reported value falls up to 196 mm behind truth, then snaps back once stopped; 600 mm is never reported")

# --- fig 4 : verification v1 ------------------------------------------------
t5 = [1854, 2188, 2519, 2852, 3184, 3516, 3847, 4518, 5018]
o5 = [4, 151, 403, 658, 907, 1157, 1407, 1908.5, 1930]
fig, ax = plt.subplots()
ax.plot(t5, [1000 - o * 0.4992 for o in o5], "-o", color=BLUE, ms=4, lw=1.8,
        label="distance to go, odometric")
ax.axhline(48, color=ORANGE, ls="--", lw=1.5, label="trigger 48 mm")
ax.axhline(35.3, color=GREEN, ls=":", lw=1.5, label="frozen prediction 35.3 mm")
ax.set_xlabel("hub clock (ms)"); ax.set_ylabel("distance to go (mm)")
ax.set_ylim(0, 1050); ax.legend()
finish(fig, ax, "Verification v1  odometric trigger, first flight",
       "measured 52 mm: gap clause held, estimate clause failed by 15.5 mm")

# --- fig 5 : verification v2 ------------------------------------------------
t6 = [1854, 2187, 2518, 2850, 3181, 3512, 3842, 4546, 5047]
o6 = [3, 152, 406, 657, 906, 1156, 1399, 1931, 1952.5]
fig, ax = plt.subplots()
ax.plot(t6, [990 - o * 0.491192 for o in o6], "-o", color=BLUE, ms=4, lw=1.8,
        label="distance to go, odometric")
ax.axhline(44, color=ORANGE, ls="--", lw=1.5, label="trigger 44 mm")
ax.axhline(32.1, color=GREEN, ls=":", lw=1.5, label="frozen prediction 32.1 mm")
ax.set_xlabel("hub clock (ms)"); ax.set_ylabel("distance to go (mm)")
ax.set_ylim(0, 1040); ax.legend()
finish(fig, ax, "Verification v2  anchor moved to 990 mm",
       "measured 43 mm: falsified again by 12.05 mm; the 990 was my own profile-mixing artifact")

# --- fig 6 : frozen prediction history --------------------------------------
fig, ax = plt.subplots()
x = range(3); w = 0.26
ax.bar([i - w for i in x], [35.3, 32.1, 19.8], w, color=GREEN, label="frozen prediction")
ax.bar(list(x), [36.54, 30.95, 18.19], w, color=BLUE, label="onboard estimate")
ax.bar([i + w for i in x], [52.0, 43.0, 18.0], w, color=ORANGE, label="operator measured")
for i, (e, m) in enumerate([(36.54, 52.0), (30.95, 43.0), (18.19, 18.0)]):
    ax.text(i + w, m + 1.2, f"{abs(m-e):.2f} mm", ha="center", fontsize=8.5, color=GREY)
ax.set_xticks(list(x)); ax.set_xticklabels(["v1", "v2", "v3"])
ax.set_ylabel("final gap (mm)"); ax.set_ylim(0, 60); ax.legend()
finish(fig, ax, "Frozen predictions  the estimate clause is what caught the systematic",
       "labelled value is the estimate error: 15.46, 12.05, then 0.19 mm")

# --- fig 7 : five operation runs, estimates ---------------------------------
est = [19.42, 20.64, 19.42, 20.40, 21.13]
fig, ax = plt.subplots()
ax.bar(range(1, 6), est, 0.55, color=BLUE, label="onboard estimate (frozen)")
ax.axhline(19.8, color=GREEN, ls="--", lw=1.5, label="frozen prediction 19.8 mm")
for i, v in enumerate(est, 1):
    ax.text(i, v + 0.5, f"{v:.2f}", ha="center", fontsize=9)
ax.set_xlabel("operation run"); ax.set_ylabel("final gap (mm)"); ax.set_ylim(0, 26)
ax.legend(loc="lower right")
finish(fig, ax, "Operation  the five onboard estimates, committed before ground truth",
       "mean 20.20 mm, sd 0.76 mm, range 1.72 mm")

# --- fig 8 : close-out reconciliation ---------------------------------------
meas = [22.0, 34.0, 22.0, 18.0, 37.0]
fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.5, 5), gridspec_kw={"width_ratios": [1.35, 1]})
r = range(1, 6)
axa.bar([i - 0.19 for i in r], est, 0.36, color=BLUE, label="onboard estimate")
axa.bar([i + 0.19 for i in r], meas, 0.36, color=ORANGE, label="operator measured")
axa.axhline(19.8, color=GREEN, ls="--", lw=1.5, label="frozen prediction")
for i, (e, m) in enumerate(zip(est, meas), 1):
    axa.text(i + 0.19, max(m, 19.8) + 1.4, f"{m-e:+.1f}", ha="center", fontsize=8.5,
             color=GREY, clip_on=False)
axa.set_xticks(list(r)); axa.set_xlabel("operation run"); axa.set_ylabel("final gap (mm)")
axa.set_ylim(0, 52); axa.legend(loc="upper left", ncol=3, fontsize=8.5)
axa.set_title("predicted / estimated / measured", loc="left", fontsize=11, pad=10)

starts = [m + o * K for m, o in zip(meas, [1998.5, 1996.0, 1998.5, 1996.5, 1995.0])]
axb.scatter(list(r), starts, s=70, color=RED, zorder=3, label="operation, implied start")
axb.scatter([-1.4, -1.0, -0.6], [1000.0, 1001.0, 999.8], s=70, marker="s",
            color=GREEN, zorder=3, label="verification, implied start")
axb.axhline(1000.0, color=GREY, ls="--", lw=1.5, label="hard-coded anchor 1000 mm")
axb.axvline(0.0, color="#d3d1c7", lw=1)
axb.set_xlim(-1.9, 5.8); axb.set_xticks([-1.0] + list(r))
axb.set_xticklabels(["verif.", "1", "2", "3", "4", "5"])
axb.set_xlabel("run"); axb.set_ylabel("implied start position (mm)")
axb.set_ylim(994, 1022)
axb.set_title("the scatter is placement, not the rover", loc="left", fontsize=11, pad=10)
axb.legend(loc="upper left", fontsize=8.5)
fig.suptitle("Close-out  the whole operation error is start-line placement",
             x=0.005, ha="left", fontsize=12, fontweight="medium")
fig.text(0.005, 0.925, "odometry at rest varied 1.72 mm across all five runs; "
                       "the result varied 19 mm", fontsize=9, color=GREY)
fig.tight_layout(rect=[0, 0, 1, 0.90])
figs.append(fig)

# --- write ------------------------------------------------------------------
names = ["fig1_run1_spin", "fig2_run2_ranger_a_vs_b", "fig3_run3_ranger_lag",
         "fig4_verification_v1", "fig5_verification_v2", "fig6_prediction_history",
         "fig7_operation_estimates", "fig8_closeout_reconciliation"]
for f, nm in zip(figs, names):
    f.savefig(f"{OUT}/{nm}.png", dpi=150, bbox_inches="tight", facecolor="white")
    f.savefig(f"{OUT}/{nm}.svg", bbox_inches="tight", facecolor="white")

with PdfPages(f"{OUT}/wall_rover_plots.pdf") as pdf:
    for f in figs:
        pdf.savefig(f, bbox_inches="tight", facecolor="white")
    info = pdf.infodict()
    info["Title"] = "Wall-Approach Rover -- campaign plots"
    info["Subject"] = "7 characterization runs, 3 verification plan versions, 5 scored runs"

print(f"wrote {len(figs)} figures as png + svg, plus wall_rover_plots.pdf")
