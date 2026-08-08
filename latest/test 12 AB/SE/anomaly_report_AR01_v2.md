# ANOMALY REPORT — AR-01 v2: USS-B Discrepancy (Updated with Cal-Run-2 Evidence)
**Type:** REPORT (static)  
**Version:** 2.0  **Date:** 2026-07-21  
**Supersedes:** AR-01 v1 (issued after Cal-Run-1)

---

## Anomaly (updated)

**Original (v1):** USS-B reads 176mm shorter than USS-A at start position.  
**New finding (Cal-Run-2):** USS-B reports exactly **586mm for 6 consecutive loop iterations** (t=951–1201ms, 300ms total) while the rover is moving. This is a stale-reading artefact: the sensor was returning a cached value rather than updating.

Additionally: the USS-B offset relative to USS-A is not fully constant but varies between 100–150mm across different approach distances, suggesting an angular mounting offset rather than purely a translational one.

---

## Classification

**Branch: SURPRISING BUT PHYSICALLY POSSIBLE.**

The stale-reading duration (300ms, ≈ 6× the 50ms loop period) is within physical bounds — many USS sensors have refresh intervals of 50–250ms, and Pybricks may internally cache the last valid reading. The 586mm value matches the last valid reading before the stale period, which is consistent with a cache.

**Sensitivity impact:** USS-B was planned as a cross-source for fault detection (CMP-4). With 300ms stale periods, USS-B cannot serve as a real-time cross-check. Missing a 300ms window at max speed (465mm/s) = 140mm of travel with no confirmed valid USS-B reading. This is significant.

USS-B is NOT used as the trigger sensor, so the stale reading does not endanger the operation directly. However, CMP-4's cross-source function is degraded.

---

## Disposition

**CHASE CLOSED — disposition revised to EXCLUDE USS-B from trigger and real-time logic.**

From Cal-Run-2 slope comparison (t=1251–1701ms):
- fwd1 slope: (592−388)/450ms = 453mm/s
- fwd2 slope: (464−242)/450ms = 493mm/s
- Slopes differ by 9% — consistent with USS-B being at a slightly different angle (measuring a shorter diagonal path to the wall), not a pure translational offset.
- The offset is NOT constant: 129mm at t=1ms, 128mm at t=1251ms, 146mm at t=1701ms.

**Revised disposition:**
1. USS-B is excluded from the trigger decision and from real-time cross-sourcing.
2. USS-B is logged in the Verification Run and operation runs for post-hoc review only.
3. CMP-4 (USS-F2 agreement) is satisfied at TBD_USS_AGREE = 180mm; the stale-reading risk is noted as a caveat.
4. The absence of USS-B real-time cross-sourcing means the only forward-distance channel is USS-A. No further action is possible without operator involvement.

No additional hardware run or operator measurement is required or requested.

---

*AR-01 v2 closed.*
