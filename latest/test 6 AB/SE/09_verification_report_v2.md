# Verification Report v2 (GATE C)

**Static REPORT** on the re-verification run against the frozen Verification Plan v2 (`08_verification_plan_v2.md`). Supersedes the reconcile-and-proceed recommendation in `07`; the v1 report is retained. Characterization count unchanged (verification runs are not scored); outside-input count unchanged (1).

Run: `run-20260701-003834` — `completed`, 4.4 s. Program: `operation_locked.py` (T_OP = 125 mm), unchanged.

---

## 1. Predicted (v2) vs actual

| criterion | frozen v2 prediction | actual | verdict |
|---|---|---|---|
| `stop_reason` | 0 (clean ranger trigger) | **0** | ✅ |
| `s_trig_actual` | ∈ [80, 125] mm | **91 mm** (overshoot 34) | ✅ |
| No contact | yes (operator confirms) | **yes — operator confirmed** | ✅ |
| Heading drift | ±20°, reported | **−0.2°** | ✅ |
| Onboard rest reading | excluded (ranger invalid) | 166 mm (invalid, > trigger) | — confirms the exclusion |

**Verdict: PASS — all three criteria met.**

---

## 2. Two-run bracket (added confidence)

The two verification runs land at opposite ends of the overshoot range and **both stopped with no contact**:

| run | overshoot | trigger reading | physical rest (model, δ=0) | drift | contact |
|---|---|---|---|---|---|
| v1 (`001407`) | 5 mm | 120 mm | ~61 mm | +1° | none |
| v2 (`003834`) | 34 mm | 91 mm | ~32 mm | −0.2° | none (operator-confirmed) |

Low overshoot → far stop; high overshoot → close stop — the two directly exercise the predicted **~26–61 mm** physical range, and no-contact holds across it. Combined with the robustness argument (contact needs >60 mm overshoot; overshoot is capped ~40–48 mm), the hard constraint is well established.

---

## 3. Confirmed limitations (carried into the scored runs)
- **Ranger unreliable < ~100 mm** — both runs returned physically impossible rest readings (141, 166 mm). The onboard close-gap estimate is untrustworthy → **the operator measures each scored final gap** (the authoritative value).
- **Trigger reliable** — both fired cleanly in the reliable range (`stop_reason = 0`, trigger readings 120 / 91 mm).

---

## 4. Verdict and path
- **SYS-2 (no contact): VERIFIED** across the overshoot range (2 bracketing samples + robustness argument).
- **SYS-1 (maximum speed): satisfied** (both motors at max throughout).
- **SYS-4 (heading): −0.2° / +1°** — comfortably bounded (though not a no-contact driver).

`operation_locked.py` is **locked and verified**. Proceed to the **5 scored operation runs**, program unchanged, readiness handshake before each, operator measuring each final gap.
