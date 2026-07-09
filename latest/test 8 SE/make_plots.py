"""Generate all WallRun figures from the captured run telemetry."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "/home/claude/wallrun_plots"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.axisbelow": True})

def mask(v, hi=1200):
    a = np.array(v, dtype=float)
    a[a >= hi] = np.nan
    return a

def L(t, v):
    n = min(len(t), len(v))
    return list(t[:n]), list(v[:n])

# ---------------------------------------------------------------- data
# C1 heading (discovery creep spun the hub ~18deg, approach crooked)
c1_t = [0,80,160,240,320,400,480,560,641,721,802,882,962,1042,1122,1202,1282,1362,1442,1522,1602,1682,1762,1842]
c1_h = [-18.42,-18.0,-18.5,-19.58,-20.55,-21.70,-22.78,-23.85,-24.91,-25.85,-27.05,-27.83,-28.68,-29.54,-30.19,-31.32,-31.90,-32.86,-32.76,-32.75,-32.75,-32.75,-32.75,-32.75]
# C1b heading (open loop: veers to -14 deg)
c1b_t = [0,81,161,241,321,401,481,561,641,722,802,882,962,1042,1122,1202,1282]
c1b_h = [0.0,0.41,1.2,0.22,-0.92,-2.06,-3.09,-3.99,-4.99,-6.0,-7.06,-7.76,-8.72,-9.93,-11.33,-13.34,-14.22]
# C1c heading (first control attempt: holds ~-6 then coasts to -12.5)
c1c_t = [160,181,202,223,244,265,286,307,328,349,370,391,412,433,454,475,496,517,538,559,580,601,622,643,664,685,706,727,748,769,790,811,832,853,874,895,916,937,958,979,1000,1021,1042,1063,1084,1105,1126,1147,1168,1189,1210,1231,1252,1273,1294,1400,1600,1900,2216]
c1c_h = [0.78,1.01,1.0,0.87,0.67,0.41,0.31,0.5,0.62,0.48,0.17,-0.09,-0.39,-0.62,-0.93,-1.19,-1.45,-1.67,-1.91,-2.18,-2.4,-2.6,-2.77,-2.96,-3.23,-3.62,-3.97,-4.25,-4.61,-4.9,-5.12,-5.28,-5.51,-5.71,-5.91,-6.11,-6.22,-6.28,-6.29,-6.26,-6.35,-6.39,-6.48,-6.61,-6.84,-7.55,-8.52,-9.32,-10.22,-11.19,-12.04,-12.53,-12.71,-12.62,-12.5,-12.5,-12.5,-12.5,-12.5]

# C1d dist_A (clean straight approach; trigger 993, rest 557)
c1d_t = [11,33,55,77,99,121,143,165,187,209,231,253,275,297,319,341,363,385,407,429,451,473,495,517,539,561,583,605,627,649,671,693,715,737,759,781,803,825,847,869,891,913,935,957,979,1001,1023,1045,1067,1089,1111,1133,1155,1250,1400,1600,1800,2189]
c1d_A = [1025,1025,1023,1021,1017,1020,1009,997,988,982,882,952,948,936,927,918,912,898,889,889,873.5,857,851,837,828,823,813,799,794,783,766,756,741,732,718,708,699,689,680,680,670,651.5,636,627,618,604,595,595,595,595,569,563,558,557,557,557,557,557,557]

# Verification dist_A (full approach from start line; trigger 2081, rest 51)
ver_t = [14,43,72,101,130,159,188,217,246,275,304,333,362,391,420,449,478,507,536,565,594,623,652,681,710,739,768,797,826,855,884,913,942,971,1000,1029,1058,1087,1116,1145,1174,1203,1232,1261,1290,1319,1348,1377,1406,1435,1464,1493,1522,1551,1580,1609,1638,1667,1696,1725,1754,1783,1812,1841,1870,1899,1928,1957,1986,2015,2044,2073,2102,2131,2160,2189,2218,2247,2400,2600,2874]
ver_A = [1029,1027,1031.5,1054,1020,1012,995,993,993,971,987,947,929,921,901,953,868,868,854,954,1475,2000,1501.5,931,821,751,737,724.5,706,690,674,656.5,641,636.5,618,612,593,588,572,553,539,521,511,493,477,460.5,444,429,415,398,382,372,367,353,339,325,309.5,299,288,288,288,288,235,213.5,198,182,172,171.5,150,141,124,114,93,78,66.5,58,55,53.5,51,51,51,51]

# Operation (5 scored runs)
runs = [1,2,3,4,5]
onboard = np.array([29,49,55,41,49], float)
measured = np.array([31,47,50,41,48], float)
head_rest = np.array([1.83,-1.98,-3.82,-1.35,-1.30])
PRED, SIGMA = 45.0, 12.0
C_A = 15.0

c1_t, c1_h = L(c1_t, c1_h)
c1b_t, c1b_h = L(c1b_t, c1b_h)
c1c_t, c1c_h = L(c1c_t, c1c_h)
c1d_t, c1d_A = L(c1d_t, c1d_A)
ver_t, ver_A = L(ver_t, ver_A)

BLUE, RED, GRN, ORG, GRY = "#2166ac", "#b2182b", "#1a9850", "#e08214", "#555555"

# ---------------------------------------------------------------- Fig 1
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.plot(c1_t, c1_h, "-", color=GRY, lw=1.6, label="C1  discovery creep (crooked, −33°)")
ax.plot(c1b_t, c1b_h, "-", color=RED, lw=1.8, label="C1b open loop (veers to −14°)")
ax.plot(c1c_t, c1c_h, "-", color=ORG, lw=1.8, label="C1c  P-only control (−6° hold, coasts to −12.5°)")
ax.axhspan(-0.5, 2.61, color=GRN, alpha=0.18, label="C1d  FF+P+D control band [−0.5°, +2.6°]")
ax.scatter(np.full(5, 2000), head_rest, color=BLUE, zorder=5, s=28,
           label="operation runs, heading at rest")
ax.axhline(0, color="k", lw=0.8)
ax.set_xlabel("time (ms)"); ax.set_ylabel("heading (deg)")
ax.set_title("Taming the drivetrain veer: heading vs time across the control iterations")
ax.legend(fontsize=8, loc="lower left"); ax.set_xlim(-30, 2120)
fig.tight_layout(); fig.savefig(f"{OUT}/fig1_heading_control_progression.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 2
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.plot(c1d_t, mask(c1d_A), "-o", color=BLUE, ms=2.5, lw=1.2, label="sensor A distance")
ax.axvline(993, color=RED, ls="--", lw=1.3, label="trigger (t=993 ms)")
ax.axhline(557, color=GRN, ls=":", lw=1.3, label="rest S_A = 557 mm")
# v_max slope annotation
ax.annotate("cruise ≈ 490 mm/s", xy=(700, 730), xytext=(300, 500),
            arrowprops=dict(arrowstyle="->", color=GRY), color=GRY, fontsize=9)
ax.annotate("D_stop ≈ 53 mm\n(610→557 at trigger)", xy=(1050, 575), xytext=(1200, 720),
            arrowprops=dict(arrowstyle="->", color=RED), color=RED, fontsize=8.5)
ax.set_xlabel("time (ms)"); ax.set_ylabel("sensor-A distance (mm)")
ax.set_title("C1d — clean straight-line dynamics (source of v_max, D_stop)")
ax.legend(fontsize=8.5); ax.set_xlim(-30, 1900); ax.set_ylim(500, 1080)
fig.tight_layout(); fig.savefig(f"{OUT}/fig2_C1d_dynamics.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 3
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.plot(ver_t, mask(ver_A), "-o", color=BLUE, ms=2.3, lw=1.1, label="sensor A distance")
ax.axhline(113, color=ORG, ls="--", lw=1.2, label="trigger threshold S_A = 113 mm")
ax.axvline(2081, color=RED, ls="--", lw=1.2, label="trigger fired (t=2081 ms)")
ax.axhline(51, color=GRN, ls=":", lw=1.3, label="rest S_A = 51 mm  →  gap 36 mm")
ax.axhline(15, color="k", ls="-", lw=1.0, alpha=0.6, label="wall (S_A = c_A = 15 mm)")
ax.set_xlabel("time (ms)"); ax.set_ylabel("sensor-A distance (mm)")
ax.set_title("Verification run — full max-speed approach and close stop (frozen prediction confirmed)")
ax.legend(fontsize=8, loc="upper right"); ax.set_xlim(-30, 2900); ax.set_ylim(0, 1090)
fig.tight_layout(); fig.savefig(f"{OUT}/fig3_verification_profile.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 4
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.axhspan(PRED-2*SIGMA, PRED+2*SIGMA, color=BLUE, alpha=0.10, label="frozen prediction ±2σ")
ax.axhspan(PRED-SIGMA, PRED+SIGMA, color=BLUE, alpha=0.16, label="frozen prediction ±1σ")
ax.axhline(PRED, color=BLUE, ls="--", lw=1.3, label=f"frozen prediction {PRED:.0f} mm")
w = 0.16
ax.bar(np.array(runs)-w, onboard, width=2*w, color=ORG, alpha=0.85, label="onboard estimate")
ax.bar(np.array(runs)+w, measured, width=2*w, color=GRN, alpha=0.9, label="operator measured")
ax.axhline(0, color="k", lw=1.2)
ax.text(5.35, 1.5, "wall (contact)", color="k", fontsize=8, ha="right")
for i, r in enumerate(runs):
    ax.text(r-w, onboard[i]+1, f"{onboard[i]:.0f}", ha="center", va="bottom", fontsize=8, color=ORG)
    ax.text(r+w, measured[i]+1, f"{measured[i]:.0f}", ha="center", va="bottom", fontsize=8, color=GRN)
ax.set_xlabel("operation run"); ax.set_ylabel("gap: frontmost point to wall (mm)")
ax.set_title("Operation reconciliation — predicted vs onboard vs measured (5/5 no contact)")
ax.set_xticks(runs); ax.legend(fontsize=8, ncol=2, loc="upper left"); ax.set_ylim(0, 78)
fig.tight_layout(); fig.savefig(f"{OUT}/fig4_operation_reconciliation.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 5
fig, ax = plt.subplots(figsize=(5.6, 5.4))
lim = [20, 60]
ax.plot(lim, lim, "-", color=GRY, lw=1.2, label="perfect agreement (y = x)")
ax.fill_between(lim, [l-3 for l in lim], [l+3 for l in lim], color=GRY, alpha=0.12, label="±3 mm")
ax.scatter(measured, onboard, color=BLUE, s=55, zorder=5)
for i, r in enumerate(runs):
    ax.annotate(f"run {r}", (measured[i], onboard[i]), textcoords="offset points",
                xytext=(6, 4), fontsize=8)
ax.set_xlabel("operator measured gap (mm)"); ax.set_ylabel("onboard estimated gap (mm)")
ax.set_title("Onboard estimator vs ground truth\n(RMS 2.6 mm — validates c_A and sensor A)")
ax.legend(fontsize=8); ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal")
fig.tight_layout(); fig.savefig(f"{OUT}/fig5_onboard_vs_measured.png"); plt.close(fig)

# ---------------------------------------------------------------- Fig 6
fig, ax = plt.subplots(figsize=(8.2, 4.4))
ax.axhspan(PRED-2*SIGMA, PRED+2*SIGMA, color=BLUE, alpha=0.10, label="prediction ±2σ (21–69 mm)")
ax.axhspan(PRED-SIGMA, PRED+SIGMA, color=BLUE, alpha=0.16, label="prediction ±1σ")
ax.axhline(PRED, color=BLUE, ls="--", lw=1.3, label="frozen prediction 45 mm")
ax.axhline(0, color="k", lw=1.3, label="wall (contact)")
ax.scatter(runs, measured, color=GRN, s=70, zorder=6, label="measured gap")
ax.plot(runs, measured, color=GRN, lw=1.0, alpha=0.5)
mmean = measured.mean()
ax.axhline(mmean, color=RED, ls="-.", lw=1.1, label=f"measured mean {mmean:.1f} mm")
for i, r in enumerate(runs):
    ax.text(r, measured[i]+1.5, f"{measured[i]:.0f}", ha="center", fontsize=8.5, color=GRN)
ax.set_xlabel("operation run"); ax.set_ylabel("measured gap (mm)")
ax.set_title("Measured gaps vs frozen prediction band — all clear, all within ~1.2σ")
ax.set_xticks(runs); ax.legend(fontsize=8, loc="upper right"); ax.set_ylim(-4, 74)
fig.tight_layout(); fig.savefig(f"{OUT}/fig6_gaps_vs_prediction.png"); plt.close(fig)

print("wrote:")
for f in sorted(os.listdir(OUT)):
    print("  ", f)
