#!/usr/bin/env python3
"""Reproduce every figure and every number quoted in the engineering report.

Run:  python3 make_analysis.py [outdir]

Reads telemetry_data.py (raw hub telemetry, nothing synthetic), writes CSVs
and PNG plots. No network access required.
"""
import csv
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import telemetry_data as T

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
PLOTS = os.path.join(OUT, "plots")
DATA = os.path.join(OUT, "data")
for d in (PLOTS, DATA):
    os.makedirs(d, exist_ok=True)

C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
GRID = "#e1e0d9"
INK = "#0b0b0b"
MUTED = "#898781"


def style(ax, xlabel, ylabel, title=None):
    ax.set_xlabel(xlabel, color=MUTED, fontsize=10)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=10)
    if title:
        ax.set_title(title, color=INK, fontsize=12, loc="left", pad=12)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)


def mean(x):
    return sum(x) / len(x)


def sd(x):
    m = mean(x)
    return (sum((v - m) ** 2 for v in x) / (len(x) - 1)) ** 0.5


def pearson(x, y):
    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den


def clean(prof):
    return [(t, v) for t, v in prof if v is not None]


# ======================================================================
# Figure 1 - sensor A calibration against the touch-off reference
# ======================================================================
dtc = [T.THETA_CONTACT - c[0] for c in T.CAL]
r1 = [c[1] for c in T.CAL]
r2 = [c[2] if c[2] < 1900 else None for c in T.CAL]


def fit(x, y):
    n = len(x)
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    s = sxy / sxx
    return s, my - s * mx


slope_all, icpt_all = fit(dtc, r1)
res = [b - (slope_all * a + icpt_all) for a, b in zip(dtc, r1)]
worst = max(range(len(res)), key=lambda i: abs(res[i]))
x2 = [d for i, d in enumerate(dtc) if i != worst]
y2 = [v for i, v in enumerate(r1) if i != worst]
slope_cl, icpt_cl = fit(x2, y2)

fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
ax.plot(dtc, r1, "o", color=C[0], ms=6, label="sensor A")
xs = [d for d, v in zip(dtc, r2) if v is not None]
ys = [v for v in r2 if v is not None]
ax.plot(xs, ys, "s", color=C[1], ms=5, alpha=0.75, label="sensor B")
lx = [0, max(dtc)]
ax.plot(lx, [slope_cl * v + icpt_cl for v in lx], "-", color=C[0], lw=1.6,
        label="fit A (outlier dropped): %.4f x %+.2f" % (slope_cl, icpt_cl))
ax.plot(dtc[worst], r1[worst], "o", mfc="none", mec="#e34948", ms=15, mew=2)
ax.annotate("outlier %+.0f mm" % res[worst], (dtc[worst], r1[worst]),
            textcoords="offset points", xytext=(12, 10), color="#e34948", fontsize=9)
ax.axhline(40, color=MUTED, ls="--", lw=1)
ax.annotate("sensor floor 40 mm (reads 40 at true contact)", (max(dtc) * 0.42, 55),
            color=MUTED, fontsize=9)
ax.axvline(0, color=INK, lw=1.2)
ax.annotate("wall (touch-off)", (18, 940), color=INK, fontsize=9)
style(ax, "encoder degrees to contact", "sensor reading (mm)",
      "Sensor calibration referenced to the rover's own touch-off")
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(PLOTS, "fig1_sensor_calibration.png"))
plt.close(fig)

# ======================================================================
# Figure 2 - validation trigger sweep
# ======================================================================
fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
for i, d in enumerate(T.VALIDATION):
    p = clean(T.VALIDATION_PROFILES[d["dash"]])
    ax.plot([q[0] for q in p], [q[1] for q in p], "-", color=C[i], lw=1.8,
            label="trigger %.1f  ->  stop %.1f mm" % (d["trig"], d["gfin_dr"]))
ax.axhline(40, color=MUTED, ls="--", lw=1)
style(ax, "time from dash start (ms)", "forward distance, sensor A (mm)",
      "Phase 1 validation: three triggers, measuring the trigger-to-stop offset C")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 1090)
fig.tight_layout()
fig.savefig(os.path.join(PLOTS, "fig2_validation_sweep.png"))
plt.close(fig)

# ======================================================================
# Figure 3 - the five operation runs overlaid
# ======================================================================
fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
for i, d in enumerate(T.OPERATION):
    p = clean(T.OPERATION_PROFILES[d["run"]])
    ax.plot([q[0] for q in p], [q[1] for q in p], "-", color=C[i], lw=1.7,
            label="run %d  ->  measured %.0f mm" % (d["run"], d["measured_gap"]))
ax.axhline(40, color=MUTED, ls="--", lw=1)
style(ax, "time from dash start (ms)", "forward distance, sensor A (mm)",
      "Phase 2: five locked operation runs, all stopping without contact")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 1090)
fig.tight_layout()
fig.savefig(os.path.join(PLOTS, "fig3_operation_runs.png"))
plt.close(fig)

# ======================================================================
# Figure 4 - estimate vs ground truth
# ======================================================================
mine = [d["gfin_dr"] for d in T.OPERATION]
meas = [d["measured_gap"] for d in T.OPERATION]
delta = [a - b for a, b in zip(mine, meas)]
r_mt = pearson(mine, meas)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8), dpi=160)
idx = [d["run"] for d in T.OPERATION]
w = 0.38
a1.bar([i - w / 2 for i in idx], mine, w, color=C[0], label="onboard estimate")
a1.bar([i + w / 2 for i in idx], meas, w, color=C[1], label="operator measurement")
for i, (m, v) in enumerate(zip(mine, meas)):
    a1.annotate("%.1f" % m, (idx[i] - w / 2, m), ha="center", va="bottom",
                fontsize=8, color=MUTED)
    a1.annotate("%.0f" % v, (idx[i] + w / 2, v), ha="center", va="bottom",
                fontsize=8, color=MUTED)
a1.set_xticks(idx)
style(a1, "operation run", "final gap (mm)", "Estimate vs ground truth")
a1.legend(frameon=False, fontsize=9)

a2.plot(mine, meas, "o", color=C[2], ms=9)
for i in range(5):
    a2.annotate(" run %d" % idx[i], (mine[i], meas[i]), fontsize=9, color=MUTED)
lo, hi = 0, 21
a2.plot([lo, hi], [lo, hi], "--", color=MUTED, lw=1, label="perfect agreement")
a2.set_xlim(lo, hi)
a2.set_ylim(0, 11)
style(a2, "my estimate (mm)", "measured (mm)",
      "No per-run skill: r = %+.3f" % r_mt)
a2.legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(PLOTS, "fig4_estimate_vs_truth.png"))
plt.close(fig)

# ======================================================================
# Figure 5 - diagnostics: what actually correlated with the gap
# ======================================================================
chans = [("max yaw (deg)", [d["hmax"] for d in T.OPERATION]),
         ("lag bias (mm)", [d["lag"] for d in T.OPERATION]),
         ("braking travel (mm)", [d["brake_enc"] for d in T.OPERATION]),
         ("cruise speed (mm/s)", [d["vmms"] for d in T.OPERATION])]
fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), dpi=160)
for ax, (name, vals) in zip(axes, chans):
    rr = pearson(vals, meas)
    ax.plot(vals, meas, "o", color=C[0] if abs(rr) < 0.6 else C[2], ms=8)
    for i in range(5):
        ax.annotate(str(idx[i]), (vals[i], meas[i]), fontsize=8, color=MUTED,
                    textcoords="offset points", xytext=(6, 4))
    style(ax, name, "measured gap (mm)", "r = %+.3f" % rr)
fig.suptitle("Only yaw tracks the measured gap - and with the right sign",
             color=INK, fontsize=12, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(os.path.join(PLOTS, "fig5_diagnostics.png"))
plt.close(fig)

# ======================================================================
# Figure 6 - the root-cause scale error
# ======================================================================
near = [(T.THETA_CONTACT - c[0], c[1]) for c in T.CAL if (T.THETA_CONTACT - c[0]) <= 300]
fig, ax = plt.subplots(figsize=(9, 5.0), dpi=160)
for K, col, lab in ((T.K_CRUISE, C[1], "cruise scale 0.492 (correct for the dash)"),
                    (T.K_STEPPED, C[0], "stepped scale 0.521 (inflated by step-brake skid)")):
    err = [(d * K, v - d * K) for d, v in near]
    ax.plot([e[0] for e in err], [e[1] for e in err], "o-", color=col, lw=1.6, label=lab)
ax.axhline(3.0, color="#e34948", ls="--", lw=1.4)
ax.annotate("OFA = 3.0 mm, the value I actually used", (55, 3.6),
            color="#e34948", fontsize=9)
style(ax, "true gap (mm)", "sensor A reading minus true gap (mm)",
      "Root cause: the zero-point offset was derived in the wrong length scale")
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(PLOTS, "fig6_root_cause.png"))
plt.close(fig)

# ======================================================================
# CSV exports
# ======================================================================
with open(os.path.join(DATA, "calibration_points.csv"), "w", newline="") as f:
    w_ = csv.writer(f)
    w_.writerow(["theta_deg", "deg_to_contact", "sensor_A_mm", "sensor_B_mm",
                 "true_gap_at_K_cruise_mm"])
    for c in T.CAL:
        d = T.THETA_CONTACT - c[0]
        w_.writerow([c[0], d, c[1], c[2] if c[2] < 1900 else "", round(d * T.K_CRUISE, 2)])

with open(os.path.join(DATA, "operation_summary.csv"), "w", newline="") as f:
    keys = ["run", "start_a", "g0", "wall", "lag", "nfix", "vmms", "brake_enc",
            "lastfix_g", "afin", "gfin_dr", "hmax", "hend", "vbat", "measured_gap"]
    w_ = csv.DictWriter(f, fieldnames=keys + ["delta_est_minus_meas"])
    w_.writeheader()
    for d in T.OPERATION:
        row = {k: d[k] for k in keys}
        row["delta_est_minus_meas"] = round(d["gfin_dr"] - d["measured_gap"], 2)
        w_.writerow(row)

with open(os.path.join(DATA, "validation_summary.csv"), "w", newline="") as f:
    keys = list(T.VALIDATION[0].keys())
    w_ = csv.DictWriter(f, fieldnames=keys + ["C_offset"])
    w_.writeheader()
    for d in T.VALIDATION:
        row = dict(d)
        row["C_offset"] = round(d["gfin_dr"] - d["trig"], 2)
        w_.writerow(row)

with open(os.path.join(DATA, "dash_profiles.csv"), "w", newline="") as f:
    w_ = csv.writer(f)
    w_.writerow(["phase", "run", "t_ms", "sensor_A_mm"])
    for k, p in sorted(T.VALIDATION_PROFILES.items()):
        for t, v in p:
            w_.writerow(["validation", k, t, v])
    for k, p in sorted(T.OPERATION_PROFILES.items()):
        for t, v in p:
            w_.writerow(["operation", k, t, "" if v is None else v])

# ======================================================================
# Console summary - every headline number in the report
# ======================================================================
print("=" * 66)
print("PHASE 2 RESULT")
print("=" * 66)
print("run   estimate   measured     delta")
for i in range(5):
    print("  %d    %6.2f     %5.1f    %+7.2f" % (idx[i], mine[i], meas[i], delta[i]))
print("\nmeasured  mean %.2f  sd %.2f  min %.1f  max %.1f" %
      (mean(meas), sd(meas), min(meas), max(meas)))
print("estimate  mean %.2f  sd %.2f" % (mean(mine), sd(mine)))
print("delta     mean %+.2f  sd %.2f" % (mean(delta), sd(delta)))
rr = pearson(mine, meas)
t = rr * math.sqrt(3) / math.sqrt(1 - rr * rr)
print("estimate vs truth  r = %+.3f  (n=5, t=%.2f, p~0.07: no per-run skill)" % (rr, t))
print("\ncontact events: 0 of 5")

print("\n" + "=" * 66)
print("ROOT CAUSE")
print("=" * 66)
errs = [v - d * T.K_CRUISE for d, v in near[1:]]
print("sensor A reads +%.2f mm above true gap near the wall (cruise scale)" % mean(errs))
print("OFA used = 3.0  ->  every estimate optimistic by %.1f mm" % (mean(errs) - 3.0))
yaw_term = 60 * math.sin(math.radians(mean([d["hmax"] for d in T.OPERATION])))
print("yaw/corner term at %.2f deg mean yaw = %.2f mm" %
      (mean([d["hmax"] for d in T.OPERATION]), yaw_term))
print("predicted bias %.1f mm   vs observed %.1f mm" %
      (mean(errs) - 3.0 + yaw_term, mean(delta)))

print("\n" + "=" * 66)
print("CHANNEL CORRELATIONS WITH MEASURED GAP")
print("=" * 66)
for name, vals in chans:
    print("  %-22s r = %+.3f" % (name, pearson(vals, meas)))

print("\nretrospective: trigger 60.0 gave mean %.1f mm; "
      "for 20 mm use trigger %.1f" % (mean(meas), 60.0 + (20 - mean(meas))))
print("\nwrote plots to %s and CSVs to %s" % (PLOTS, DATA))
