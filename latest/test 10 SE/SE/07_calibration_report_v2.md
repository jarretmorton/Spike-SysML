# Calibration Report — Addendum v2
**Document type:** REPORT (backward-looking, static) · **Version:** v2 (addendum to v1; v1
unchanged) · **Basis:** runs VER-1 (`run-20260711-001826`), VER-2 (`run-20260711-003046`),
VER-3 (`run-20260711-003610`), and the **operator ground-truth measurement = 166 mm**.

v1 covered CHAR-1/CHAR-1b (config + gross dynamics). This addendum records what the three
verification-attempt runs and the single operator measurement established. These runs were, in
effect, further characterization — they are counted against the run budget (§4).

---

## 1. The operator anchor resolves the sensor picture (decisive)

With the rover stopped **square** (heading −2.8°) at the end of VER-3, the operator measured the
true front-face-to-wall distance = **166 mm**. At that instant the channels read:

| Channel | Reading at rest | vs true 166 mm | Verdict |
|---------|-----------------|----------------|---------|
| **us0 (port A)** | **182 mm** | +16 mm | **ACCURATE** — `true_gap = us0 − 16 mm` (small fixed offset) |
| us1 (port B) | 50 mm | −116 mm | **UNRELIABLE near the wall** — does not read the front-face perpendicular distance; dropped for control and for safety limits |
| **Odometry** (k_rot=0.50, us0-anchored) | predicts 167 mm | +1 mm | **ACCURATE and lag-free** — matches the operator to 1 mm over the full 771 mm approach |

**Consequence:** every "close" stop in VER-1/2/3 was measured on **us1**, which reads ~116 mm
short — so those stops that *looked* like 50–80 mm were actually **~166–200 mm true**. The rover
had **not** been getting close to the wall. Control must move to **us0 + odometry**.

## 2. Sensor lag vs skid — resolved

Over the whole VER-3 approach, odometry (771 mm) and the ultrasonic delta (770 mm) agree, and the
odometry-anchored final (167 mm) matches the operator (166 mm). So at the VER-3 speed there is
**no net brake skid** — odometry is trustworthy end-to-end. The dynamic-phase disagreements seen
earlier are **ultrasonic lag**: at cruise the readings trail true position by ~60 mm and settle
correctly only at rest. (The larger apparent discrepancy in CHAR-1b was full-speed brake skid,
which does not occur at the reduced cruise command adopted below.) **Control therefore uses the
lag-free channels — a standstill us0 anchor plus odometry — never the in-motion ultrasonic.**

## 3. Straightness solved (SYS-5)

- **VER-1** (full-speed, open-loop): heading drift **20°**, rest skew −17° → SYS-5 FAIL; stop was
  oblique.
- **VER-2** (first steering attempt, base command 1500): **no effect** (still 20°). Root cause:
  at 1500 the motors are saturated at their physical max (~880°/s), so trimming the command down
  changed nothing — a wheel cannot be sped up past saturation to steer.
- **VER-3** (steering with cruise command **below saturation, base 850 ≈ 97% of max**, IMU
  proportional gain Kp=25 slowing the outside wheel, clamp ±250, ramped launch): heading held to
  **|max| 3.1°, rest −2.8°** → SYS-5 effectively met; stop is square. Confirmed calibration values
  (k_rot, straight-line odometry accuracy) all come from this clean run.

## 4. Ledger (updated)

| Run | Outcome | Counts |
|-----|---------|--------|
| CHAR-1 | wrong direction + truncated dump | 1 |
| CHAR-1b | config + gross dynamics | 2 |
| VER-1 | discovered 20° veer; oblique stop | 3 |
| VER-2 | steering no-op (saturation); diagnosed | 4 |
| VER-3 | straight + square; enabled operator anchor | 5 |

**Characterization/verification runs executed: 5. Operator measurements: 1 (the 166 mm anchor).**
(One flash failed to deploy — a BLE timeout — and did not run; not counted.)

## 5. Calibrated basis carried forward to Verification Plan v2

`k_rot = 0.50 mm/deg` (confirmed to 1 mm); **true_gap = us0 − 16 mm**; **odometry is the control
truth** (anchor with a standstill us0 average, propagate with k_rot); **us1 dropped**; cruise
command **850** (straight, no skid); steering **Kp=25, clamp ±250, ramped launch**; brake roll
after the stop command ≈ **13 mm** (VER-3). Ultrasonic in-motion lag ≈ 60 mm (reason the anchor is
taken at standstill).
