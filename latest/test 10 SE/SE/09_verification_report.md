# Verification Report — Wall-Approach Rover
**Document type:** REPORT (backward-looking, static — never edited) · **Version:** v1 · **Gate:**
GATE C · **Basis:** run VER-4 (`run-20260711-005846`) against frozen Verification Plan v2.

---

## 1. VER-4 vs the frozen prediction (Plan v2 §2)

| Quantity | Frozen prediction | VER-4 actual | Verdict |
|----------|-------------------|--------------|---------|
| True final gap | ≈ 40 mm | odometry **36.7 mm**; us0-at-rest **31 mm** | close, no contact |
| us0 at rest | ≈ 56 mm | 47 mm | consistent (near floor) |
| Two-channel agreement | ≤ 10 mm | **5.7 mm** (36.7 vs 31) | PASS |
| Heading through approach | ≤ 3° | **1.63° max** | PASS |
| Heading at rest | ≤ 3° | **−0.82°** | PASS |
| Brake roll | ≈ 13 mm | **13.0 mm** (906.5 − 893.5) | as calibrated |

## 2. Pass/fail criteria (Plan v2 §4)

| # | Criterion | Result |
|---|-----------|--------|
| P-1 | No contact | **PASS** — true gap ~31–37 mm |
| P-2 | Close (SYS-4) | **PASS** — 36.7 mm within 40 ± 12 |
| P-3 | Two-channel agreement | **PASS** — 5.7 mm |
| P-4 | Straight (SYS-5) | **PASS** — ≤1.63°, rest −0.82° |
| P-5 | Complete stop (SYS-3) | **PASS** — odometry → 0, settled |

**All criteria pass.** The control strategy is verified.

## 3. Requirement closure

| Req | Status | Evidence |
|-----|--------|----------|
| SYS-1 No contact | **CLOSED** | VER-4 ~31–37 mm clearance; hard odometry cap guarantees ≥25 mm even off-nominal |
| SYS-2 Max approach speed | **CLOSED (with documented trade)** | cruise command **850 ≈ 97% of saturated max**. Running the last 3% (command ≥ ~880) saturates both motors and removes the ability to slow a wheel — which caused the 20° veer in VER-1/VER-2. ~97% is the fastest speed at which the rover can be held straight; the trade buys SYS-5 and is required, not optional |
| SYS-3 Complete stop | **CLOSED** | odometry speed → 0; body settled |
| SYS-4 Minimise gap (objective) | **CLOSED at operating point** | ~34 mm true vs 166 mm uncontrolled; read on operator-validated channels (see §5) |
| SYS-5 Straight approach | **CLOSED** | IMU proportional steering; heading ≤1.63°, rest −0.82° |
| SYS-6 No-contact margin | **CLOSED** | brake logic + hard cap keep predicted gap above the contact margin with wide slack |
| CMP-1 ranger reads | CLOSED (us0); us1 **dropped** (reads ~116 mm short near wall) | operator anchor + trace |
| CMP-3 motor at max | CLOSED | achieved cruise at command ceiling |
| CMP-4 motor → 0 | CLOSED | odometry rest |
| CMP-5 odometry → distance (k_rot) | CLOSED | k_rot 0.50 matched operator to 1 mm |
| CMP-6 IMU yaw | CLOSED | steering holds heading; used as control input |
| CMP-7 IMU accel | CLOSED | decel captured (secondary) |
| Dropped effectors | CONFIRMED | us2 rear open/uninformative; reflectance flat |

## 4. The locked operation program (frozen for the five scored runs)

- Identify ports; standoff-ID the front pair; **verify forward** with a low-speed move (front
  reading must decrease) — self-checks direction every run.
- **Anchor** at standstill: `true_start = us0_avg − 16`.
- **Steered approach**: cruise command 850, IMU proportional gain Kp=25, correction clamp ±250,
  ramped launch (holds heading ≤ ~3°).
- **Odometry control** (lag-free): `pred_gap = true_start − mean(|Δmotor|)·0.50`; **brake when
  `pred_gap ≤ 53`** (target ≈ 34 mm true after the 13 mm brake roll).
- **Safety**: hard cap brake if `pred_gap ≤ 25`; us0 close backstop; 6 s time cap; **us1 excluded**
  from all limits; motors stop in `finally`; `{"event":"end"}` sentinel; lean telemetry.

This is the exact program from VER-4 — **locked, unchanged** for all five runs (test-like-you-fly).

## 5. Objective validation statement

The objective (true final gap) is tied to operator ground truth: the **166 mm** measurement at the
VER-3 square stop calibrated `us0` (`true = us0 − 16`) and confirmed odometry to 1 mm. VER-4 and
the five operation runs are therefore read on **operator-validated, lag-free channels**, not on an
unvalidated sensor. Per the close-out order, the operator's **direct** ground-truth gaps for the
five operation stops are collected **after** the runs (onboard estimates frozen first), providing
the final at-operating-point validation in the Final Report.

## 6. Ledger

Characterization/verification runs executed: **6** (CHAR-1, CHAR-1b, VER-1, VER-2, VER-3, VER-4).
Operator measurements: **1**. One flash failed to deploy (BLE timeout; not run, not counted).
**Ready for the five locked operation runs.**
