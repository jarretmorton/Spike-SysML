#!/usr/bin/env python3
"""
Regenerate every telemetry CSV and every plot for the wall-stop task.

Telemetry was retrieved from the hub via get_telemetry and is embedded below so
this script is self-contained and the figures are reproducible without the rover.

    python3 make_plots.py

Writes ../data/*.csv and ./*.png + ./*.svg
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
os.makedirs(DATA, exist_ok=True)

BLUE, ORANGE, TEAL, AMBER, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948"
GRID, INK = "#e1e0d9", "#52514e"

# ----------------------------------------------------------------------------
# Telemetry
# ----------------------------------------------------------------------------

# char1, run-20260806-094342: three max-speed approach cycles, usA and usB
# sampled every ~150 ms. Times are relative to each cycle's start.
CHAR1 = {
    1: dict(
        t=[0, 152, 305, 458, 610, 762],
        A=[1089, 1070, 999, 932, 871, 798],
        B=[959, 933, 873, 810, 745, 671],
    ),
    2: dict(
        t=[0, 151, 301, 461, 611, 764, 914, 1068, 1220, 1372, 1522, 1675, 1827],
        A=[1088, 1065, 1004, 921, 854, 777, 713, 644, 596, 490, 413, 339, 290],
        B=[968, 944, 872, 799, 729, 647, 591, 591, 591, 355, 291, 207, 156],
    ),
    3: dict(
        t=[0, 150, 302, 455, 607, 760, 911, 1063, 1215, 1367, 1520, 1670, 1823],
        A=[1081, 1054, 1002, 935, 858, 791, 723, 657, 589, 518, 434, 356, 286],
        B=[965, 938, 880, 805, 725, 654, 589, 589, 589, 376, 295, 222, 146],
    ),
}

# char2, run-20260806-095340: cycle k3 stop window, usA and encoder at 20 ms.
# The invariant usA + enc_mm is constant to +/-1.5 mm through cruise, then usA
# freezes at 287 while the encoder keeps advancing.
CHAR2 = [
    (58399, 423, 651.84), (58420, 413, 661.86), (58440, 403, 671.40),
    (58460, 392, 681.42), (58481, 379, 692.42), (58501, 368, 702.69),
    (58521, 358, 712.72), (58541, 348, 723.23), (58561, 338, 733.50),
    (58582, 328, 743.52), (58602, 318, 753.30), (58622, 307, 763.08),
    (58642, 298, 773.35), (58664, 287, 784.36), (58685, 287, 795.60),
    (58689, 287, 798.29), (58719, 287, 810.03), (58749, 287, 812.96),
    (58779, 287, 812.96), (58809, 287, 811.98), (58839, 287, 811.25),
    (58869, 287, 812.23), (58899, 287, 812.23), (58929, 287, 812.23),
    (58959, 287, 811.98), (58989, 287, 811.98), (59019, 287, 811.98),
    (59049, 287, 811.98), (59079, 287, 811.98), (59109, 287, 811.98),
    (59139, 287, 811.98), (59169, 287, 811.98), (59199, 287, 811.74),
    (59229, 287, 811.74), (59259, 287, 811.98), (59289, 287, 811.74),
]

# char3, run-20260806-095951: approach k1, raw usB. Trigger at t=1831, B_est
# 153.9; settled 102. Stall plateaus at indices 24-27 (591) and 55-61 (279).
CHAR3_T = [0, 61, 121, 183, 245, 306, 368, 430, 490, 552, 613, 675, 713, 734,
           754, 774, 795, 816, 837, 858, 878, 898, 919, 942, 962, 982, 1002,
           1022, 1042, 1062, 1082, 1102, 1125, 1146, 1167, 1188, 1209, 1231,
           1253, 1274, 1294, 1314, 1335, 1355, 1375, 1395, 1415, 1437, 1458,
           1478, 1498, 1518, 1539, 1560, 1581, 1602, 1623, 1644, 1665, 1686,
           1706, 1727, 1747, 1768, 1789, 1810, 1831, 1848, 1888, 1928, 1968,
           2008, 2048, 2088, 2128, 2168, 2208, 2248, 2288, 2328, 2369, 2409,
           2450, 2490, 2530]
CHAR3_V = [976, 976, 967, 945, 930, 900, 868, 836, 807, 779, 750, 720, 706,
           697, 686, 677, 667, 658, 647, 637, 632, 622, 608, 601, 591, 591,
           591, 591, 563, 552, 542, 537, 522, 513, 502, 488, 474, 464, 451,
           440, 430, 415, 405, 396, 381, 371, 361, 346, 341, 327, 318, 307,
           298, 291, 291, 279, 279, 279, 279, 279, 279, 279, 198, 189, 180,
           170, 161, 151, 146, 126, 111, 100, 100, 100, 102, 102, 102, 102,
           102, 102, 102, 102, 102, 102, 102]
CHAR3_STALL = list(range(24, 28)) + list(range(55, 62))

# operation run 1, run-20260806-101238: sensor B reading ~14% low from the
# first stationary sample; odometry backstop stopped it; settled unstable.
OP1_T = [0, 61, 122, 185, 248, 308, 368, 428, 490, 511, 532, 553, 574, 595,
         616, 637, 658, 679, 700, 721, 743, 764, 784, 805, 825, 845, 865, 885,
         905, 925, 945, 965, 985, 1005, 1026, 1047, 1068, 1088, 1110, 1132,
         1153, 1173, 1193, 1213, 1234, 1255, 1276, 1297, 1317, 1338, 1358,
         1379, 1399, 1419, 1440, 1461, 1483, 1503, 1525, 1548, 1568, 1588,
         1608, 1628, 1648, 1668, 1688, 1708, 1729, 1750, 1755, 1795, 1835,
         1875, 1915, 1955, 1995, 2035, 2075, 2115, 2155, 2195, 2235, 2275,
         2315, 2355, 2395, 2435, 2475, 2515, 2555, 2595, 2635]
OP1_V = [863, 865, 851, 832, 810, 789, 765, 737, 719, 707, 699, 688, 675, 670,
         663, 653, 639, 618, 606, 598, 593, 593, 593, 593, 593, 593, 593, 593,
         593, 593, 593, 593, 593, 485, 468, 458, 440, 432, 415, 403, 394, 385,
         368, 360, 347, 337, 323, 315, 304, 288, 288, 270, 261, 251, 235, 226,
         221, 213, 199, 193, 185, 174, 170, 170, 170, 170, 170, 227, 110, 100,
         100, 81, 67, 57, 49, 157, 157, 157, 158, 163, 163, 147, 147, 155, 155,
         155, 155, 155, 156, 152, 152, 147, 147]

# operation run 5, run-20260806-102554: healthy. Trigger on a fresh reading at
# 93 mm, settled rock-solid at 40 mm.
OP5_T = [0, 61, 123, 184, 246, 308, 370, 431, 492, 553, 616, 677, 738, 759,
         781, 802, 823, 844, 865, 886, 907, 927, 948, 969, 989, 1009, 1029,
         1050, 1071, 1092, 1113, 1134, 1155, 1176, 1197, 1219, 1239, 1259,
         1280, 1301, 1322, 1343, 1365, 1386, 1408, 1429, 1450, 1471, 1491,
         1511, 1532, 1553, 1574, 1596, 1616, 1637, 1657, 1677, 1697, 1717,
         1737, 1757, 1777, 1797, 1819, 1839, 1859, 1879, 1899, 1920, 1940,
         1960, 1972, 2013, 2053, 2093, 2133, 2173, 2213, 2253, 2293, 2333,
         2373, 2413, 2453, 2493, 2533, 2573, 2613, 2654, 2694, 2734, 2774,
         2814, 2854]
OP5_V = [993, 997, 992, 962, 947, 917, 883, 852, 823, 793, 765, 731, 701, 692,
         682, 667, 657, 647, 633, 624, 613, 603, 593, 593, 593, 593, 557, 543,
         531, 519, 508, 499, 488, 478, 463, 454, 445, 445, 431, 411, 411, 391,
         381, 371, 361, 350, 342, 331, 321, 321, 307, 302, 291, 291, 291, 291,
         291, 291, 291, 291, 213, 200, 191, 182, 172, 167, 167, 167, 131, 125,
         112, 102, 93, 80, 63, 52, 44, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40,
         40, 40, 40, 40, 40, 40, 40, 40]

# Scored results. Estimates were committed before ground truth was disclosed.
RESULTS = [
    (1, 863, "backstop", 97.6, "147 (rejected)", "", 852.3, -2.2, 130, 145),
    (2, 868, "backstop", 106.9, "151 (rejected)", "", 855.0, -5.0, 132, 148),
    (3, 992, "trigger", 94.4, "40", 54.4, 956.5, -8.2, 29, 29),
    (4, 990, "trigger", 94.1, "40", 54.1, 953.8, -9.4, 29, 24),
    (5, 993, "trigger", 93.0, "40", 53.0, 953.6, -8.1, 29, 27),
]


# ----------------------------------------------------------------------------
# CSV export
# ----------------------------------------------------------------------------

def write_csvs():
    with open(os.path.join(DATA, "char1_three_approaches.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cycle", "t_ms_rel", "usA_mm", "usB_mm"])
        for cyc in (1, 2, 3):
            d = CHAR1[cyc]
            for t, a, b in zip(d["t"], d["A"], d["B"]):
                w.writerow([cyc, t, a, b])

    with open(os.path.join(DATA, "char2_sensorA_freeze.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_ms", "usA_mm", "enc_mm", "invariant_mm"])
        for t, a, e in CHAR2:
            w.writerow([t, a, round(e, 2), round(a + e, 2)])

    with open(os.path.join(DATA, "char3_k1_approach.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_ms_rel", "usB_mm", "stalled"])
        for i, (t, v) in enumerate(zip(CHAR3_T, CHAR3_V)):
            w.writerow([t, v, int(i in CHAR3_STALL)])

    with open(os.path.join(DATA, "operation_run1_run5.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "t_ms_rel", "usB_mm"])
        for t, v in zip(OP1_T, OP1_V):
            w.writerow([1, t, v])
        for t, v in zip(OP5_T, OP5_V):
            w.writerow([5, t, v])

    with open(os.path.join(DATA, "operation_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "B_startline_mm", "stop_source", "est_at_trigger_mm",
                    "settled_B_mm", "S_mm", "encoder_total_mm", "heading_at_stop_deg",
                    "my_estimate_mm", "measured_gap_mm", "delta_mm", "contact"])
        for r in RESULTS:
            w.writerow(list(r) + [r[8] - r[9], "no"])


def style(ax, xlabel, ylabel):
    ax.set_xlabel(xlabel, fontsize=10, color=INK)
    ax.set_ylabel(ylabel, fontsize=10, color=INK)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK, labelsize=9)


def save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(HERE, "%s.%s" % (name, ext)),
                    dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name + ".png/.svg")


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------

def plot1():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    cols = {1: BLUE, 2: ORANGE, 3: TEAL}
    for cyc in (1, 2, 3):
        d = CHAR1[cyc]
        ax.plot(d["t"], d["A"], color=cols[cyc], lw=2, marker="o", ms=3,
                label="sensor A - cycle %d" % cyc)
    for cyc in (2, 3):
        d = CHAR1[cyc]
        ax.plot(d["t"], d["B"], color=cols[cyc], lw=2, ls="--", marker="s", ms=3,
                label="sensor B - cycle %d" % cyc)
    ax.annotate("sensor B stalls at 591/589 mm\nwhile A keeps falling",
                xy=(1068, 591), xytext=(1150, 760), fontsize=9, color=INK,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1))
    ax.set_ylim(0, 1150)
    style(ax, "time since approach start (ms)", "forward distance (mm)")
    ax.set_title("char1 - three max-speed approaches, both forward sensors",
                 fontsize=11, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=2)
    save(fig, "plot1_char1_three_approaches")


def plot2():
    t = [r[0] - CHAR2[0][0] for r in CHAR2]
    a = [r[1] for r in CHAR2]
    inv = [r[1] + r[2] for r in CHAR2]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True,
                                   gridspec_kw=dict(height_ratios=[2, 1]))
    ax1.plot(t, a, color=BLUE, lw=2, marker="o", ms=3)
    ax1.axvline(58664 - CHAR2[0][0], color=RED, lw=1.2, ls=":")
    ax1.annotate("sensor A freezes at 287 mm\nand never recovers",
                 xy=(58664 - CHAR2[0][0], 287), xytext=(400, 380),
                 fontsize=9, color=INK,
                 arrowprops=dict(arrowstyle="->", color=INK, lw=1))
    ax1.set_ylim(250, 450)
    style(ax1, "", "sensor A (mm)")
    ax1.set_title("char2 - sensor A freeze, exposed by the odometry invariant",
                  fontsize=11, color=INK, loc="left")

    ax2.plot(t, inv, color=ORANGE, lw=2, marker="o", ms=3)
    ax2.axhline(1071.4, color=TEAL, lw=1.5, ls="--")
    ax2.set_ylim(1060, 1110)
    style(ax2, "time since window start (ms)", "usA + encoder (mm)")
    ax2.annotate("constant to +/-1.5 mm while both healthy;\ndiverges once A freezes",
                 xy=(430, 1066), fontsize=9, color=INK)
    save(fig, "plot2_char2_sensorA_freeze")


def plot3():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(CHAR3_T, CHAR3_V, color=BLUE, lw=2, label="raw sensor B")
    ax.scatter([CHAR3_T[i] for i in CHAR3_STALL], [CHAR3_V[i] for i in CHAR3_STALL],
               color=AMBER, s=26, marker="s", zorder=5, label="sensor stalled")
    ax.scatter([1831], [153.9], color=RED, s=70, zorder=6, label="brake triggered, 154 mm")
    ax.axhline(102, color=TEAL, lw=2, ls="--", label="settled, 102 mm")
    ax.set_ylim(0, 1050)
    style(ax, "time since approach start (ms)", "distance to wall (mm)")
    ax.set_title("char3 - one approach, stall-immune estimator (k1)",
                 fontsize=11, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False)
    save(fig, "plot3_char3_k1_stalls")


def plot4():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(OP1_T, OP1_V, color=ORANGE, lw=2, label="op run 1 - starts 863, backstop stop")
    ax.plot(OP5_T, OP5_V, color=BLUE, lw=2, label="op run 5 - starts 993, clean trigger")
    ax.axhline(40, color=TEAL, lw=2, ls="--", label="settled 40 mm (runs 3-5)")
    ax.annotate("~130 mm low from the first\nstationary sample", xy=(0, 863),
                xytext=(230, 700), fontsize=9, color=INK,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1))
    ax.annotate("multi-path echoes below\nthe sensor's floor", xy=(2100, 152),
                xytext=(1750, 330), fontsize=9, color=INK,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1))
    ax.set_ylim(0, 1060)
    style(ax, "time since approach start (ms)", "distance to wall, sensor B (mm)")
    ax.set_title("operation - faulted run 1 vs healthy run 5",
                 fontsize=11, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False)
    save(fig, "plot4_operation_run1_vs_run5")


if __name__ == "__main__":
    write_csvs()
    print("wrote CSVs to", DATA)
    plot1()
    plot2()
    plot3()
    plot4()
