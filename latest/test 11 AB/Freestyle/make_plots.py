#!/usr/bin/env python3
"""Render all run plots for the rover wall-stop session from data/telemetry.json.

Eight runs plot exact downsampled telemetry as retrieved during the session.
Four runs (char7, op3, op4, op5) had their raw traces expire from the trace
store before archiving; their figures are synthesized from the summary anchors
(start medians, trigger point, speeds, stop medians) and are clearly marked.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "data", "telemetry.json")))
OUT = os.path.join(HERE, "plots")
os.makedirs(OUT, exist_ok=True)

C_A = "#2a78d6"   # us_A
C_B = "#eb6834"   # us_B
C_E = "#d4537e"   # us_E
C_X = "#888780"   # odometry
C_V = "#1baf7a"   # speed
C_H = "#7f77dd"   # heading

ORDER = ["char1", "char2", "char3", "char4", "char5", "char6", "char7",
         "op1", "op2", "op3", "op4", "op5"]
FIG_NAMES = {
    "char1": "fig_01_char1_discovery.png",
    "char2": "fig_02_char2_calibration.png",
    "char3": "fig_03_char3_brake_test.png",
    "char4": "fig_04_char4_offset_pin.png",
    "char5": "fig_05_char5_lock_candidate_v1.png",
    "char6": "fig_06_char6_lock_candidate_v2.png",
    "char7": "fig_07_char7_locked_validation.png",
    "op1": "fig_08_op1.png",
    "op2": "fig_09_op2.png",
    "op3": "fig_10_op3.png",
    "op4": "fig_11_op4.png",
    "op5": "fig_12_op5.png",
}


def sec(ts):
    return [t / 1000.0 for t in ts]


def plot_measured(name, run):
    series = run["series"]
    for ch, s in series.items():
        assert len(s["t"]) == len(s["v"]), f"{name}.{ch} length mismatch"
    has_head = "head" in series
    if has_head:
        fig, (ax, axh) = plt.subplots(
            2, 1, figsize=(11, 6.2), sharex=True,
            gridspec_kw={"height_ratios": [3, 1]})
    else:
        fig, ax = plt.subplots(figsize=(11, 4.8))
        axh = None

    if "us_A" in series:
        ax.plot(sec(series["us_A"]["t"]), series["us_A"]["v"],
                color=C_A, lw=1.6, label="us_A (mm)")
    if "us_B" in series:
        ax.plot(sec(series["us_B"]["t"]), series["us_B"]["v"],
                color=C_B, lw=1.4, ls=(0, (2, 2)), label="us_B (mm)")
    if "us_E" in series:
        ax.plot(sec(series["us_E"]["t"]), series["us_E"]["v"],
                color=C_E, lw=1.0, ls=":", marker=".", ms=4, label="us_E (mm)")
    if "x" in series:
        ax.plot(sec(series["x"]["t"]), series["x"]["v"],
                color=C_X, lw=1.6, ls=(0, (6, 3)), label="odometry x (mm)")
    if "v" in series:
        ax.plot(sec(series["v"]["t"]), series["v"]["v"],
                color=C_V, lw=1.4, ls=(0, (1, 2)), label="speed v (mm/s)")
    if "spd" in series:
        ax.plot(sec(series["spd"]["t"]), series["spd"]["v"],
                color=C_V, lw=1.2, ls=(0, (1, 2)),
                label="wheel speed (deg/s)")
    if axh is not None:
        axh.plot(sec(series["head"]["t"]), series["head"]["v"],
                 color=C_H, lw=1.4)
        axh.axhline(0, color="#bbbbb5", lw=0.6)
        axh.set_ylabel("heading (deg)")
        axh.set_xlabel("time (s)")
        axh.grid(alpha=0.25)
    else:
        ax.set_xlabel("time (s)")

    ax.set_ylabel("mm  |  mm/s")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.set_title(f"{run['label']}\n{run['run_id']} - downsampled telemetry",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, FIG_NAMES[name]), dpi=130)
    plt.close(fig)


def plot_reconstructed(name, run):
    a = run["anchors"]
    launch = a["launch_ms"] / 1000.0
    trig = a["trig_ms"] / 1000.0
    tb = a["t_brake_ms"] / 1000.0
    stop = trig + tb
    end = 5.5

    fig, ax = plt.subplots(figsize=(11, 4.8))

    # us_A: standstill median, ramp-phase descent, linear fall to trigger,
    # then post-stop medians.
    a_trig_read = 66.0 if a["hardbrake"] == 0 else 95.0
    tA = [0.0, 0.72, launch + 0.37, trig]
    vA = [a["medA_0"], a["medA_0"], a["medA_0"] - 60.0, a_trig_read]
    ax.plot(tA, vA, color=C_A, lw=1.6, label="us_A (mm)")
    ax.plot([stop + 0.45, stop + 1.2], [a["medA_s"]] * 2, color=C_A, lw=1.6)
    s2 = a.get("medA_s2", a["medA_s"])
    ax.plot([stop + 1.75, end], [s2] * 2, color=C_A, lw=1.6)

    # us_B where anchored (obstruction runs) or clean-run start value.
    if "medB_s" in a:
        ax.plot([0.0, 0.72], [a["medB_0"]] * 2, color=C_B, lw=1.4,
                ls=(0, (2, 2)), label="us_B (mm)")
        ax.plot([stop + 0.45, end], [a["medB_s"]] * 2, color=C_B, lw=1.4,
                ls=(0, (2, 2)))
    else:
        ax.plot([0.0, 0.72], [a["medB_0"]] * 2, color=C_B, lw=1.4,
                ls=(0, (2, 2)), label="us_B (mm)")

    # Odometry: linear flight to trigger, skid-back to x_stop, flat after.
    ax.plot([launch + 0.38, trig, stop + 0.3, end],
            [90.0, a["x_trig"], a["x_stop"], a["x_stop"]],
            color=C_X, lw=1.6, ls=(0, (6, 3)), label="odometry x (mm)")

    # Speed: ramp, plateau at ~vmax, brake collapse.
    ax.plot([launch, launch + 0.38, (launch + trig) / 2.0, trig, stop],
            [0.0, 390.0, a["vmax"], a["v_trig"], 0.0],
            color=C_V, lw=1.4, ls=(0, (1, 2)), label="speed v (mm/s)")

    trig_label = ("primary trigger" if a["hardbrake"] == 0
                  else "60 mm tripwire")
    ax.axvline(trig, color="#a32d2d", lw=0.8, ls=":")
    ax.annotate(f"{trig_label}\nx={a['x_trig']:.0f}", (trig, a["x_trig"]),
                textcoords="offset points", xytext=(6, -28), fontsize=8,
                color="#a32d2d")

    ax.set_xlabel("time (s)")
    ax.set_ylabel("mm  |  mm/s")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.set_title(f"{run['label']}\n{run['run_id']} - RECONSTRUCTED from "
                 "summary anchors (raw trace expired before archiving)",
                 fontsize=10, color="#79402a")
    fig.text(0.5, 0.5, "RECONSTRUCTED", fontsize=44, color="#d85a30",
             alpha=0.10, ha="center", va="center", rotation=18)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, FIG_NAMES[name]), dpi=130)
    plt.close(fig)


def plot_overview():
    res = DATA["operation_results"]
    est = res["onboard_estimate_mm"]
    meas = res["operator_measured_mm"]
    labels = ["Run 1\n(clean)", "Run 2\n(obstr.)", "Run 3\n(obstr.)",
              "Run 4\n(obstr.)", "Run 5\n(obstr.)"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.6))

    idx = range(len(est))
    w = 0.38
    ax1.bar([i - w / 2 for i in idx], est, w, color=C_A,
            label="onboard estimate")
    ax1.bar([i + w / 2 for i in idx], meas, w, color=C_X,
            label="operator measured")
    for i in idx:
        d = est[i] - meas[i]
        ax1.text(i, max(est[i], meas[i]) + 4, f"\u0394 +{d:.1f}",
                 ha="center", fontsize=8, color="#79402a")
    ax1.set_xticks(list(idx))
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("final gap (mm)")
    ax1.set_title("Operation: onboard estimate vs ground truth\n"
                  "5/5 full stops, zero contact", fontsize=10)
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.25)

    # Stop-gap convergence across all full-speed braking runs (A-based
    # onboard gaps for characterization; operator truth for operation).
    runs = ["char3", "char4", "char5", "char6", "char7",
            "op1", "op2", "op3", "op4", "op5"]
    gaps = [279.5, 101.5, 65.5, 151.5, 44.5, 28, 133, 131, 140, 136]
    kinds = ["clean", "clean", "wire", "obstr", "clean",
             "clean", "obstr", "obstr", "obstr", "obstr"]
    colors = {"clean": C_V, "wire": "#eda100", "obstr": C_B}
    ax2.plot(range(len(runs)), gaps, color="#bbbbb5", lw=0.8, zorder=1)
    for i, (g, k) in enumerate(zip(gaps, kinds)):
        ax2.scatter(i, g, color=colors[k], s=48, zorder=2)
        ax2.text(i, g + 8, f"{g:.0f}", ha="center", fontsize=8)
    ax2.set_xticks(range(len(runs)))
    ax2.set_xticklabels(runs, fontsize=8, rotation=30)
    ax2.set_ylabel("stop gap (mm)")
    ax2.set_ylim(0, 320)
    ax2.set_title("Stop gap per full-speed run\n"
                  "green = clean lane, orange = obstructed lane, "
                  "amber = tripwire tuning", fontsize=10)
    ax2.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_00_overview.png"), dpi=130)
    plt.close(fig)


def main():
    for name in ORDER:
        run = DATA["runs"][name]
        if run.get("reconstructed"):
            plot_reconstructed(name, run)
        else:
            plot_measured(name, run)
        print("wrote", FIG_NAMES[name])
    plot_overview()
    print("wrote fig_00_overview.png")


if __name__ == "__main__":
    main()
