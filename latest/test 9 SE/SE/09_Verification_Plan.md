# Verification Plan — Wall‑Stop Rover
**Gate:** B (frozen before the verification run; tests the calibrated model at the true operating point)
**Version:** 1.0 (a falsified prediction forces re‑derivation and v1.1 before any re‑run)
**Depends on:** Calibration Report `08`. Parameters: `v_max=494`, `k_gain=0.516`, `A_floor≈288`, `A_linear~1000–400`, `d_stop` held 25–50 mm, `c_offset` OPEN.

---

## 1. Purpose
Verify, at the operating point, that the committed control scheme (Calibration Report §5) **stops without contact** and lands where the model predicts, while simultaneously closing the two open parameters:
- **`d_stop`** → Tier 1, from settle‑window encoders.
- **`c_offset`** → from the single costed operator gap measurement.

This is the one verification run the process requires; it is instrumented to do all three jobs at once (no extra characterization run).

---

## 2. Article under test — operation‑candidate program
Same frozen hardware config and heading hold as `05`. Control law per cycle (test‑like‑you‑fly = the flight profile, repeated 3× for repeatability):

1. `reset_heading(0)`, baseline sanity gate (A/B forward geometry only; rear not gated), `square_up`.
2. Drive straight at `BASE_CMD` (heading hold).
3. **A‑fix:** at the first sample with `A ≤ 450` (A linear here), latch `enc_fix = ½(|ml|+|mr|)` and `A_fix`. Frame origin = this point.
4. **Dead‑reckon:** `dist_to_go = A_fix − k_gain·(enc − enc_fix)`; **brake** when `dist_to_go ≤ D_BRAKE`.
5. **Coast** (passive brake) to rest; log the settle window **including encoders**.
6. **Backstops (independent):** brake immediately if filtered `B ≤ B_STOP` (median of last 3, reject lone high spikes), or `enc` travel cap, or time cap.
7. Reposition (free) between cycles; leave the rover at rest after the final cycle for the operator measurement.

**Frozen constants for this run (conservative):**
`D_BRAKE = 100 mm` · `B_STOP = 55 mm` · `A_FIX_TRIP = 450 mm` · 3 cycles · settle logs `d_f0,d_f1,ml_deg,mr_deg,acc_x` at `REST_DT_MS`.

Rationale for `D_BRAKE=100`: with `d_stop` unknown up to 50 mm, braking at 100 mm leaves a predicted rest of 50–75 mm (A/encoder frame) — safely non‑contact — while B_STOP=55 catches any dead‑reckon/slip surprise before contact.

---

## 3. FROZEN PREDICTION (before running)

**In the A/encoder frame** (what the rover computes):
- Brake issued at `dist_to_go ≈ 100 mm`.
- Rest distance `= 100 − d_stop`, i.e. **50–75 mm**, central estimate **≈62 mm**.
- **No contact:** rest ≥ 40 mm with margin; B backstop independent.
- Cycle‑to‑cycle rest spread (repeatability) **≤ ±12 mm** (≈ σ_brake ⊕ σ_slip).
- Heading within **±6°** throughout.

**In the bumper/wall frame** (what the operator measures):
- Bumper gap `= rest_A_frame − c_offset`. With `c_offset` unknown, the point prediction using the prior `c_offset≈30 mm` is **≈32 mm**; the honest pre‑measurement interval is **~30–90 mm**, all strictly `> 0` (no contact).
- **This measurement is what collapses that interval** and fixes `c_offset`.

**Derived expectations to be checked:**
- `d_stop = k_gain·(enc_rest − enc_brake)` should fall in **15–60 mm** (model bracket).
- A‑fix distance vs final dead‑reckon should be self‑consistent (no gross slip): implied slip **< 10%**.

---

## 4. The single operator measurement (costed outside‑input action #1)
After the run completes and the rover is at rest from the **final** cycle, **before** any reposition/power‑cycle:
- Operator measures the **bumper‑to‑wall gap once**, in mm, at the rover centerline.
- Record verbatim. This is the only outside‑input action spent in characterization/verification.
- Purpose: bind `c_offset = rest_A_frame(final cycle) − measured_gap`, and give an absolute‑gap ground truth at the operating point (feeds Gate C objective closure).

No other operator observations are requested during this run.

---

## 5. Pass / fail

**PASS (proceed to Gate C):** all of —
1. No contact on any cycle (visual + rest > 0).
2. Rest (A/encoder frame) in **[40, 85] mm** each cycle (⇒ `d_stop` in bracket).
3. Cycle‑to‑cycle rest spread ≤ ±12 mm.
4. Heading within ±6°; clean sentinel; settle encoders present.
5. Operator gap recorded and `c_offset` computed.

**FALSIFICATION (→ re‑derive model, issue Verification Plan v1.1, then re‑run):** any of —
- Contact on any cycle.
- Rest outside [40, 85] mm (⇒ `d_stop` or slip inconsistent with model).
- Implied slip ≥ 10% (dead‑reckon vs A‑fix inconsistent).
- Heading > 6°, or run truncated / no settle encoders.

A pass that lands off‑center (e.g. gap larger than desired but safe) does **not** fail verification — it calibrates the trigger for the 5 operation runs, where `D_BRAKE` is tightened using the now‑measured `d_stop` and `c_offset` to approach `g_target`.

---

## 6. After verification
- **Gate C** (Verification Report): close every requirement; close SYS‑3/objective on the operating‑point ground truth.
- Set the **final** `D_BRAKE` from measured `d_stop`, `c_offset`, and the updated σ‑budget (`g_target`), **lock** the operation program, then execute the **5 operation runs** + close‑out (freeze onboard per‑run gap estimates before requesting the operator's per‑run ground truth).

---

## 7. Run economy
- Verification run: **1** program run (counts). Spends the **1** outside‑input measurement.
- Delivers: model validation + `d_stop` (Tier 1) + `σ_brake`/`σ_slip` + `c_offset` — everything Gate C needs — in that single run.
