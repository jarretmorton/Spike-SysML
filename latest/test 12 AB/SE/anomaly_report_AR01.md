# ANOMALY REPORT — AR-01: USS-B Initial Reading Discrepancy
**Type:** REPORT (static; issued at Cal-Run-1 close-out)  
**Date:** 2026-07-21  **Run:** Cal-Run-1 (run-20260720-233145)

---

## Anomaly

USS-A (Port A) initial reading at the start line: **1028 mm** (5-sample mean; σ < 3 mm).  
USS-B (Port B) initial reading at the start line: **852 mm** (5-sample mean; σ < 4 mm).  
Discrepancy: **176 mm** (USS-B reads 17% shorter than USS-A).

Both sensors were confirmed forward-facing: during the combined-direction test (both motors
+200 deg/s, rover turned 42° CCW), both USS-A and USS-B jumped to 2000 mm (sensor max —
lost the wall). USS-E did not lose the wall and is confirmed rear-facing.

---

## Classification

**Branch: SURPRISING BUT PHYSICALLY POSSIBLE.**

176 mm is within USS physical range ([10, 2000] mm). No sensor read below the plausibility
floor or above its maximum. Therefore this is NOT an unconditional-escalation case.

**Sensitivity filter (per Section 0 of Calibration Plan):**

USS-B is used only as a cross-source (not the primary trigger). Primary trigger = USS-A.
However, the discrepancy is relevant because:
1. If the 176 mm is a stable *systematic offset* (mounting/bias), USS-B cross-checks remain
   valid once the offset is accounted for.
2. If USS-B is pointing slightly off-axis (angle or mounting), the slope of USS-B vs. time
   during approach will differ from USS-A's slope. In that case, USS-B cannot be used to
   cross-check d_stop_total.

This bears on CMP-4 (USS-F2 agreement, TBD_USS_AGREE) and the cross-source fault-detection
function. The USS-B offset is P2-adjacent in leverage terms: if it causes CMP-4 to fail, we
lose the redundancy channel for anomaly detection during operation.

**Possible physical causes (all POSSIBLE, none eliminated):**
1. Rover not perfectly square to the wall at start: a few degrees of skew places the two
   forward-facing sensors at different perpendicular distances (USS-B appears to be mounted
   further forward or on the left/right side). A ~10° skew at 1000 mm with ~100 mm lateral
   sensor separation would produce ~17 mm difference — not 176 mm. So skew alone is
   insufficient.
2. USS-B is mounted at a lateral offset AND faces slightly inward/outward (not parallel to
   USS-A). A 5–10° angle toward a side wall could produce a meaningful path-length difference.
3. USS-B has a systematic *short-read bias* of ~176 mm (unlikely at this magnitude; SPIKE
   Prime USS typically biases ≤ 30 mm, not 176 mm).
4. USS-B faces a different target: if there is a structure (table leg, chair, etc.) at ~852 mm
   lateral to the rover start position, USS-B could be measuring that instead of the wall.

None of these causes endangers the operation if USS-A is the sole trigger sensor.

---

## Recommendation

**CHASE in Cal-Run-2** (no new run or operator measurement required at this stage).

Within Cal-Run-2, examine the USS-A vs USS-B slope during the approach:
- **If slope(USS-A) ≈ slope(USS-B)**: both sensors are closing on the wall at the same rate.
  The 176 mm is a fixed geometric/bias offset. USS-B is a valid cross-source; set
  TBD_USS_AGREE to ≥ 180 mm (wider than the fixed offset) or anchor USS-B to USS-A via
  offset correction.
- **If slope(USS-B) < slope(USS-A)** (USS-B decreasing slower): USS-B is angled off-axis
  and is not closing on the wall as fast as USS-A. USS-B cross-source function is compromised;
  drop USS-B from CMP-4 and log for anomaly detection only.
- **If USS-B jumps to 2000 mm at close range**: USS-B loses its target before USS-A does,
  confirming off-axis mounting. Same disposition as above.

No operator measurement or additional hardware run is requested at this stage.
The chase is free (within Cal-Run-2 telemetry).

---

*AR-01 closed pending Cal-Run-2 slope analysis.*
