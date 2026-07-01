# Verification Plan (GATE B) — FROZEN

**Forward-looking PLAN, predictions only.** Frozen before the verification run. If the verification run falsifies a prediction, this plan is **not** edited — a new version is issued and the run repeated (INCOSE/NASA discipline). The verification run is **never** one of the 5 scored operation runs.

Basis: `05_calibration_report.md`.

---

## 1. Locked operation program design

| element | choice | why |
|---|---|---|
| Ports / polarity | hard-coded: forward US = A, B; motors C(−1), D(+1) | discovered, Runs 1–3 |
| Control | **open-loop, both motors at CMD_MAX (max)** | honors SYS-1 (maximum speed) **strictly** |
| Heading | **none** (no closed-loop hold) | hold would trim a wheel below max (SYS-1 tension); yaw is not a no-contact driver (report §5) |
| Trigger estimate | **raw** `min(dA,dB)` with last-valid dropout fallback | see §6 — a fused estimate cannot be made fail-safe |
| Trigger threshold | **T_OP = 125 mm** | derivation §3 |
| Stop | `brake()` both | characterized (skid) |
| Failsafes | TIME_CAP; raw-min **is** the trigger (no separate floor needed) | |
| Telemetry | headline one-shots only, **no per-sample buffer** | instant flush; avoids the BLE-overrun seen in Runs 1 & 3 |

The Phase-2 hot loop (read dA,dB → min w/ fallback → threshold check → wait) is identical to the calibration hot loop (test-like-you-fly). Only the pre-approach setup (hard-coded vs discovered) and the threshold value differ.

---

## 2. Design law
```
s_trig = D_closest + overshoot + δ + margin        (δ = 0)
frontmost nadir gap = T_OP − overshoot − D_closest   > 0   (no contact)
rest gap (scored)   = T_OP − overshoot − D_rest
```

## 3. Threshold derivation
```
σ_total = 11 mm                          (report §8, RSS of measured σ)
margin  = k · σ_total = 3 × 11 = 33 mm   (k = 3, for the HARD no-contact constraint)
T_OP    = D_closest + overshoot_mean + δ + margin + lip
        = 65 + 25 + 0 + 33 + 2 ≈ 125 mm
```

## 4. FROZEN PREDICTIONS (what the verification run must show)

- The rover accelerates to max, triggers when `min(dA,dB) ≈ 125 mm`, brakes, and **skids ~62 mm**.
- **Predicted REST gap** (sensor B = frontmost point, δ = 0): **≈ 41 mm** (band ~25–50 mm across the overshoot range).
- **Predicted NADIR** (closest transient): **≈ 35 mm**.
- **Predicted worst-case frontmost clearance:** **≈ 12 mm**.
- **NO CONTACT.**
- Heading drift: unpredictable within ±15° — does not affect the above.

## 5. Pass / fail criteria
- **PASS:** no contact **AND** onboard rest reading within ~**[15, 60] mm**.
  - Caveat: below ~50 mm the ultrasonic is near its minimum range, so the onboard rest reading may be noisy or clamped. That affects only the onboard *estimate*; the operator's final measurement is authoritative for the true gap, and physical no-contact does not depend on the reading's precision at rest.
- **FALSIFIED:** contact, **or** a stop well outside the band (e.g. skid distance materially different at this closer trigger point, or a mis-trigger). → diagnose → re-derive → **new Verification Plan version** → re-run. No scored run is used for this.

## 6. Rationale for the conservative design (explicit trade-off)
A tighter result (~23 mm gaps) was reachable two ways, both **declined**:
- **Encoder–ranger fusion** to shrink the dominant overshoot term (and it is SYS-1-safe). Declined because it **cannot be robustly backstopped**: any raw-reading failsafe either pre-empts the fusion benefit (fires first, at a larger distance) or fires too late to prevent contact — so a fusion mis-trigger would put the **hard no-contact constraint** at risk. For a hard constraint, the directly-triggered raw threshold with a k=3 margin is the defensible choice.
- **Closed-loop heading hold** to reduce yaw. Declined because it trims a wheel below max (SYS-1 tension), and yaw is already not a no-contact driver (frontmost point = the sensor).

The result strictly satisfies both hard constraints (SYS-1 max speed, SYS-2 no contact) and trades some closeness (graded SYS-3) for that guarantee — the correct priority ordering. Fusion is recorded as the primary lever if a future revision chooses to pursue tighter gaps.

## 7. After verification
- **PASS →** GATE C (Verification Report: predicted vs actual), then lock the program unchanged and execute the **5 scored operation runs** (readiness handshake before each; no input between them except the final gap measurements).
- **FALSIFIED →** diagnose, re-derive, re-issue this plan, re-run verification.
