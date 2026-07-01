# Verification Plan v2 (FROZEN)

**Supersedes v1** (`06_verification_plan.md`; v1 retained). Frozen before the re-verification run — predictions only; not edited afterward. Motivated by the v1 falsification documented in `07_verification_report.md`: the ultrasonic reads erratically below ~100 mm, so an onboard rest reading cannot serve as a criterion.

Basis: `05_calibration_report.md` + `07_verification_report.md`.

---

## 1. Design — UNCHANGED

Same locked program, `operation_locked.py`, **T_OP = 125 mm**:
- open-loop, both motors at CMD_MAX (maximum speed — SYS-1);
- trigger: brake when `min(dA,dB) ≤ 125 mm`, last-valid dropout fallback;
- `brake()` stop; headline-only telemetry.

No design change. The verification run showed the design is **safe and functions correctly** (`07` §3, §5) — the falsification was a flawed measurement assumption, not a design fault. Only the prediction and pass criteria are re-derived.

---

## 2. What changed vs v1 (prediction only)

| | v1 (falsified) | v2 |
|---|---|---|
| gap criterion | onboard rest reading ≈ 41 mm ∈ [15, 60] | **removed** — ranger invalid < ~100 mm |
| primary criteria | onboard gap | **reliable** signals: trigger reading, stop_reason, observed no-contact |
| gap statement | prediction = pass/fail | model-derived expectation, **operator-measured at the scored runs** |

Reason: at v1's verification the onboard rest reading was 141 mm — larger than the trigger reading (120 mm), which is physically impossible → the ranger is unreliable near the wall (`07` §2).

---

## 3. New frozen predictions

**A. Verifiable at the re-verification run (reliable onboard + observed):**
- `stop_reason = 0` — clean ranger trigger (not failsafe/timeout).
- `s_trig_actual` ∈ **[80, 125] mm** (= T_OP − overshoot; overshoot 0–45 mm).
- **NO CONTACT** — the rover halts clear of the wall (operator observes; onboard: rover stops, heading bounded).
- Heading drift: reported, expected within ±20° (does **not** affect no-contact; frontmost point = the sensor).
- Onboard `s_rest` / `s_closest` near the wall: **not criteria** — expect erratic/high values (ranger unreliable < ~100 mm).

**B. Model-derived, verified at the scored runs (operator-measured):**
- Physical final gap ≈ **26–61 mm** across the overshoot range (mean ~44 mm), δ = 0 (sensor B is the frontmost point). Not reliably measurable onboard.

---

## 4. Robustness of no-contact (carried from `07` §3)
Contact requires overshoot > T_OP − D_closest = 125 − 65 = **60 mm**. Observed overshoot ≤ 36 mm; physically bounded by one ultrasonic update step (~40–48 mm) — **< 60 mm**. The trigger fires **above** the erratic regime (~125 mm). No contact is robust; even a delayed trigger keeps ~38 mm clearance (100 − 62 skid).

---

## 5. Pass / fail (re-verification run)
- **PASS:** `stop_reason = 0` **AND** `s_trig_actual ∈ [80, 125] mm` **AND** no contact (operator confirms the rover stopped clear).
- **FALSIFIED:** contact, **OR** `stop_reason ≠ 0` (ranger trigger failed → a failsafe fired), **OR** `s_trig_actual` outside [80, 125] (near-wall erraticism reached the trigger range, or an unmodeled trigger). → diagnose → re-derive → new plan version → re-run.
- The onboard rest reading is **deliberately excluded** from the criteria.

---

## 6. After the re-verification
- **PASS →** new Verification Report (GATE C, v2) → lock `operation_locked.py` unchanged → **5 scored operation runs** (readiness handshake before each; operator measures each final gap — the authoritative gap value).
- **FALSIFIED →** diagnose, re-derive, re-issue this plan, re-run.
