# 16 — ANOMALY REPORT AR-003 — v1.0 (Gate C rejection: yaw requirement)

**Trigger:** Operator rejected Gate C — "You have not met the yaw
requirement." The rejection is **correct**. This report owns the error,
quantifies its propagation, and records the corrective chain.

## 1. The error

The telemetry channel `dh_x10` encodes heading **degrees × 10**. During
run-2 analysis I decoded R-CAL segment values as if ×100:

| Value | I reported | Actual |
|---|---|---|
| seg2 dh_x10 = −107.8 | −1.1° | **−10.8°** |
| seg3 dh_x10 = −52.1 | −0.5° | **−5.2°** |
| seg4 dh_x10 = −112.3 | −1.1° | **−11.2°** |
| R-VER dh_x10 = −392.4 | −3.92° | **−39.2°** |

Compounding it, the R-VER §1 table evaluated the *endpoint* deviation where
SYS-8's operand is the *maximum* deviation. Both errors were mine; the S1
event decode in the same analysis (÷10) was correct, so this was an
inconsistent-units slip, not a systematic convention.

## 2. Independent confirmation

Two witnesses agree with the corrected decode: (a) the R-VER `hd` buffer
channel (int(heading×10)) reads −30.8° → −39.1° across the brake window;
(b) the encoder split in the same window — L 944 vs R 1006 dps, a **6.3 %
motor-ceiling mismatch at saturated duty** — integrates to ~32–39° over the
2.4 s approach with the effective half-track (~70 mm) this pins.

## 3. Propagation of the corrupted value

ψ_run was bound 10× low (0.056 rad vs reality ~0.5+ rad un-trimmed) → the
trim decision (kp = 0) was made on false evidence → heading_bound (TBD-3)
set at 4° was unachievable by the flown design → the corner-erosion fold
(6 mm) understated reality (38–63 mm at 39° yaw) → **R-VER criterion 1's
no-contact certification was overstated** (revised status: no positive
contact evidence — amax normal, clean rest, no encoder rebound — but corner
clearance at 39° yaw is not certifiable; R-VER standoff ≈ 52 mm sensor-line
against 38–63 mm possible erosion). Doc 15 (Verification Report v1.0) is
**withdrawn/superseded**; Verification Plan v1.0 is falsified on criterion 8
and superseded by v2.0 per the gated process.

Partially mitigating (why the stop still landed sanely): the M1 anchor was
taken at ~−28° accumulated yaw and R-VER approached at a similar arc, so the
anchored offset absorbed similar geometry; and the M1 residual (172 = 218 −
46, exact) supports a perpendicular-echo model for the wide-beam sensor
against a flat wall, under which most range calibration transfers to the
trimmed (near-perpendicular) geometry with an added ±6 mm de-confounding
term now carried in σ.

## 4. Root cause of the yaw itself

At saturated duty the two motors run open at their physical ceilings, which
differ ~6 %; nothing corrected the differential (trim off). Yaw rate
≈ 13–16°/s at full speed. The brake skid adds a further ~−6° uncontrolled
swing (wheels held, chassis slides).

## 5. Corrective actions

1. **OP-WAR v1.1** (md5 `2d174fe192fb260588fee4bd34ae8592`): IMU yaw-hold
   trim — outer wheel at full duty (SYS-1 preserved), yaw-leading wheel cut
   relative to the other wheel's *measured* speed (a saturated command
   cannot be trimmed as % of command), KP 4 %/°, cap 15 % (FUN-4),
   slew-limited 1 %/tick (kills the delay-induced limit cycle found in
   qualification), engaged above 400 dps; plus `dh_max` tracking so SYS-8 is
   verified on the maximum, and `trim_pct_max` emission.
2. **Rebind** (driver v1.1): ψ_run corrected; o_B σ 3→6 mm (yaw
   de-confounding); heading_bound TBD-3 re-set to **10° whole-run max**
   (justified by corner math: with trim, at-wall heading ≤ ~8° worst incl.
   skid ⇒ erosion ≤ 14 mm, folded 9 mm mean + 4 mm var into the margin);
   σ_stop 13.4 mm → G_target 41 mm, G_AIM 50 mm.
3. **Mock corrected to as-built yaw physics** (per-motor ceilings, as-built
   yaw sign, effective half-track 60–100 mm, brake-skid yaw injection) and
   *validated against flight*: un-trimmed v1.0 in the new plant reproduces
   the R-VER-class arc. v1.1 requalified: 210/210 hard-PASS, 400-seed soak
   0 contacts, yaw-at-brake p95 0.9°, whole-run max p95 2.9°.
4. **Verification Plan v2.0** issued (doc 20); R-VER-2 required
   (characterization run 4).

**Status:** OPEN until R-VER-2 disposition at the resubmitted Gate C.
