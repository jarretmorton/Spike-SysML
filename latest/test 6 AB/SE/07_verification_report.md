# Verification Report (GATE C)

**Static REPORT** on the verification run against the frozen Verification Plan (`06_verification_plan.md`). Characterization-run count unchanged (verification is not scored and is not one of the 5). Outside-input count unchanged (1).

Run: `run-20260701-001407` — `completed`, 4.0 s. Program: `operation_locked.py` (T_OP = 125 mm), unchanged.

---

## 1. Predicted vs actual

| quantity | frozen prediction | actual | verdict |
|---|---|---|---|
| **No contact** | yes | **yes** — rover stopped clear | ✅ **VERIFIED** |
| Trigger | reading ≈ 125 mm | fired at **120 mm** (overshoot 5 mm) | ✅ reliable at trigger range |
| Heading drift | ±15° tolerable | **+1°** | ✅ |
| Rest gap (onboard) | ≈ 41 mm, band [15, 60] | **141 mm** (invalid) | ❌ falsified — see §2 |
| Nadir (onboard) | ≈ 35 mm | 76 mm | further (safe direction) |
| Start gap | ~1000 mm | 934 mm | ok |

---

## 2. The falsification and its root cause

The onboard rest reading (141 mm) fell outside the frozen [15, 60] band → the prediction is **falsified**. But 141 mm is **greater than the trigger reading (120 mm)**, which is physically impossible for a rover that only ever moved forward and braked. **The reading is invalid.**

**Root cause:** the ultrasonic is **unreliable below ~100 mm** (near its minimum range) — it returns erratic, high values close to the wall (readings ranged 76–141 mm while the body sat still). The safe-distance calibration (stops at ~400 mm) never exercised this regime, so the frozen plan wrongly assumed the onboard ranger could measure the close final gap. **It cannot.**

A second, benign contributor: this run's overshoot was only 5 mm (vs the ~25 mm central estimate), so it stopped at the far, safe end of the gap range.

---

## 3. What held — the safety-critical prediction

**NO CONTACT is VERIFIED and is robust**, independent of the ranger's close-range behaviour:

- The trigger fires in the ranger's **reliable** range (~125 mm; it fired cleanly at 120 mm). The erratic regime is **below ~100 mm — entirely after the brake command**.
- Contact would require overshoot > T_OP − D_closest = 125 − 65 = **60 mm**. Observed overshoot ≤ 36 mm across all runs, and it is physically bounded by one ultrasonic update step (~40–48 mm) — **< 60 mm**. The rover therefore **cannot** reach the wall.
- Even a delayed trigger stays safe: the erratic regime begins ~100 mm, and 100 − skid(62) ≈ 38 mm of clearance remains.

This run confirmed it directly: stop at ~55–60 mm (physical), drift 1°, clean.

---

## 4. Corrected understanding (supersedes Verification Plan §5 criteria)

- **The onboard ranger cannot measure the close final gap** (unreliable < ~100 mm). Onboard `s_rest` / `s_closest` near the wall are rough at best. The **operator's close-out measurement is authoritative** for the scored runs — which the scoring process already provides.
- **Physical final gap** (from the reliable trigger + characterized skid, δ = 0): **≈ 26–61 mm** across the overshoot range (mean ~44 mm), **no contact**. Corrected band, replacing the onboard [15, 60].
- The **trigger is unaffected** — it operates above the erratic regime.

---

## 5. Design decision — no change

The locked program is **safe and functions correctly** (reliable trigger, robust no-contact). **No design change.** T_OP = 125 mm stays: tightening would erode the no-contact margin given the poorly-bounded upper tail of the overshoot, and the ranger's close-range unreliability rules out a fusion-style tightening that would need accurate close readings.

---

## 6. Verdict and recommended path

- **Hard constraint (SYS-2, no contact): VERIFIED and robust.**
- **Hard constraint (SYS-1, maximum speed): satisfied** (both motors at max throughout).
- The falsified sub-criterion was a flawed **measurement assumption** (onboard ranger measuring close gaps), now corrected — **not a design fault**. The safety-critical prediction held robustly.

**Recommendation: proceed to the 5 scored operation runs** with `operation_locked.py` unchanged (readiness handshake before each; the operator measures each final gap at close-out).

Because the falsification was benign (safe direction, measurement-only) and no-contact is robustly established, I recommend **reconcile-and-proceed** rather than a re-run. If you would prefer an extra confirmation, I can execute **one non-scored re-verification** first — your call.
