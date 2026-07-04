import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "figure.dpi": 140, "font.size": 11, "axes.grid": True,
    "grid.alpha": 0.3, "axes.axisbelow": True,
})
BLUE, ORANGE, GREEN, RED, GREY = "#0072B2", "#E69F00", "#009E73", "#D55E00", "#555555"

# ---------------- data ----------------
runs      = [1, 2, 3, 4, 5]
onboard   = [43, 39, 37, 43, 44]      # frozen sensor-A near-range fit
trig_geo  = [52, 54, 53, 54, 53]      # trigger-geometry cross-check
truth     = [46, 45, 32, 51, 46]      # operator ground truth

# full-process journey (true gap; * = onboard estimate, not operator-measured)
j_labels  = ["C1", "C1-v2", "C2", "C3", "V1", "V1'", "Op1", "Op2", "Op3", "Op4", "Op5"]
j_gap     = [np.nan, 196, 125, 150, 28, 46, 46, 45, 32, 51, 46]
j_src     = ["contact", "op", "onb", "onb", "op", "op", "op", "op", "op", "op", "op"]

# representative approach (characterization run C2)
t = np.array([1622,1702,1762,1824,1883,1944,2003,2064,2124,2184,2244,2304,2364,
              2424,2484,2604,2663,2723,2786,2844,2904,2965,3025,3085,3204])
a = np.array([938,934,917,881,852,832,804,2000,2000,718,684,650,617,593,593,499,
              464,431,402,380,349,319,294,294,198], dtype=float)
fwd = np.array([0,13.2,39.0,68.2,96.6,126.0,155.6,184.7,215.3,244.9,274.3,304.0,
                333.8,362.5,392.8,451.1,477.6,507.0,538.1,567.0,596.1,624.8,653.9,
                682.6,740.4])
t0 = (t - t[0]) / 1000.0
a_clean = np.where(a >= 1900, np.nan, a)   # 2000 = no-echo -> gap in the line

# ============ FIG 1: operation results ============
fig, ax = plt.subplots(figsize=(8.5, 5.2))
ax.axhspan(-30, 0, color=RED, alpha=0.10)
ax.axhline(0, color=RED, lw=2, ls="--", label="wall (contact)")
for i, r in enumerate(runs):
    ax.plot([r, r], [onboard[i], truth[i]], color=GREY, lw=1, zorder=1)
ax.scatter(runs, truth,    s=110, color=GREEN, zorder=3, label="operator truth")
ax.scatter(runs, onboard,  s=90,  color=BLUE, marker="o", facecolors="none",
           linewidths=2, zorder=3, label="onboard estimate (frozen)")
ax.scatter(runs, trig_geo, s=55,  color=ORANGE, marker="^", zorder=3,
           label="trigger-geometry x-check")
for i, r in enumerate(runs):
    ax.annotate(f"{truth[i]}", (r, truth[i]), textcoords="offset points",
                xytext=(9, -3), color=GREEN, fontsize=9)
ax.set_xticks(runs); ax.set_xlabel("operation run")
ax.set_ylabel("gap to wall (mm)")
ax.set_ylim(-30, 70)
ax.set_title("Operation: 5/5 runs, no contact  (gaps 32–51 mm, mean 44 mm)")
ax.legend(loc="upper right", framealpha=0.95, fontsize=9)
fig.tight_layout(); fig.savefig("plot_operation_results.png"); plt.close(fig)

# ============ FIG 2: full-process journey ============
fig, ax = plt.subplots(figsize=(9.5, 5.2))
x = np.arange(len(j_labels))
ax.axhline(0, color=RED, lw=2, ls="--", label="wall (contact)")
ax.axhspan(-40, 0, color=RED, alpha=0.08)
# phase separators / labels
ax.axvspan(-0.5, 3.5, color=BLUE,   alpha=0.05)
ax.axvspan(3.5, 5.5,  color=ORANGE, alpha=0.06)
ax.axvspan(5.5, 10.5, color=GREEN,  alpha=0.06)
ax.text(1.5, 205, "calibration", ha="center", color=BLUE, fontsize=9)
ax.text(4.5, 205, "verification", ha="center", color=ORANGE, fontsize=9)
ax.text(8.0, 205, "operation (scored)", ha="center", color=GREEN, fontsize=9)
for i, (g, s) in enumerate(zip(j_gap, j_src)):
    if s == "contact":
        ax.scatter(i, 0, marker="X", s=160, color=RED, zorder=4)
        ax.annotate("CONTACT", (i, 0), textcoords="offset points", xytext=(0, 10),
                    ha="center", color=RED, fontsize=9, fontweight="bold")
    elif s == "op":
        ax.scatter(i, g, s=90, color=GREEN, zorder=4)
    else:
        ax.scatter(i, g, s=90, facecolors="none", edgecolors=BLUE, linewidths=2, zorder=4)
    if not np.isnan(g) and s != "contact":
        ax.annotate(f"{int(g)}", (i, g), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8, color=GREY)
ax.plot([], [], "o", color=GREEN, label="operator-measured gap")
ax.plot([], [], "o", mfc="none", mec=BLUE, mew=2, label="onboard estimate only")
ax.set_xticks(x); ax.set_xticklabels(j_labels)
ax.set_ylabel("final gap to wall (mm)"); ax.set_xlabel("run (chronological)")
ax.set_ylim(-40, 220)
ax.set_title("Gap journey: from a wall strike to a repeatable ~44 mm stop")
ax.legend(loc="center right", framealpha=0.95, fontsize=9)
fig.tight_layout(); fig.savefig("plot_gap_journey.png"); plt.close(fig)

# ============ FIG 3: estimator accuracy ============
fig, ax = plt.subplots(figsize=(6.4, 6.2))
lim = [25, 60]
ax.plot(lim, lim, color=GREY, ls="--", lw=1, label="perfect (y = x)")
ax.scatter(truth, onboard,  s=110, color=BLUE,   zorder=3,
           label="onboard A-fit  (RMS 5.3 mm)")
ax.scatter(truth, trig_geo, s=80,  color=ORANGE, marker="^", zorder=3,
           label="trigger-geometry  (+9 mm bias)")
for i in range(len(runs)):
    ax.annotate(f"R{runs[i]}", (truth[i], onboard[i]), textcoords="offset points",
                xytext=(6, 2), fontsize=8, color=BLUE)
ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal")
ax.set_xlabel("operator true gap (mm)"); ax.set_ylabel("onboard estimate (mm)")
ax.set_title("Onboard estimate vs. ground truth")
ax.legend(loc="upper left", framealpha=0.95, fontsize=9)
fig.tight_layout(); fig.savefig("plot_estimator_accuracy.png"); plt.close(fig)

# ============ FIG 4: approach profile ============
fig, ax = plt.subplots(figsize=(8.5, 5.0))
ax.plot(t0, a_clean, "-o", color=BLUE, ms=4, label="sensor-A distance (mm)")
miss = np.isnan(a_clean)
ax.scatter(t0[miss], np.full(miss.sum(), 60), marker="v", color=RED, s=45,
           label="ultrasonic no-echo (dropout)")
ax.axhline(0, color=RED, lw=2, ls="--")
ax.text(t0[-1], 8, "wall", color=RED, ha="right", fontsize=9)
ax.set_xlabel("time into fast approach (s)"); ax.set_ylabel("sensor-A distance (mm)", color=BLUE)
ax.tick_params(axis="y", labelcolor=BLUE)
ax2 = ax.twinx(); ax2.grid(False)
ax2.plot(t0, fwd, "-s", color=GREEN, ms=3, label="encoder travel (mm)")
ax2.set_ylabel("encoder travel (mm)", color=GREEN); ax2.tick_params(axis="y", labelcolor=GREEN)
ax.set_title("Representative approach (C2): rover closes on the wall at full speed")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper right", framealpha=0.95, fontsize=9)
fig.tight_layout(); fig.savefig("plot_approach_profile.png"); plt.close(fig)

print("wrote: plot_operation_results.png, plot_gap_journey.png, "
      "plot_estimator_accuracy.png, plot_approach_profile.png")
