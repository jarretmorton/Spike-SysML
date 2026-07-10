# Verification Plan v1.1 — Wall‑Stop Rover
**Supersedes v1.0** (falsified: the ranger‑B backstop pre‑empted the dead‑reckon; rover rested at 138/155/153 mm A‑frame vs predicted 50–75). Re‑derivation below uses the parameters that run closed.

**Now Tier‑1 from run‑20260709‑221742:**
- `d_stop = 15 mm` (encoder‑measured, identical all 3 cycles, σ≈0)
- `c_offset = 31 mm` (= frozen rest_A 153 − operator gap 122)
- Relationship: **`true_gap = dist_est_rest − 46`**
- Dead‑reckon slip bounded **σ ≤ 8 mm** (from the ±8 mm B‑fire spread)

## 1. What changed
1. **Dead‑reckon is the trigger** at `D_BRAKE = 81 mm` (⇒ predicted rest_A 66 → true gap 35). Prior 100 mm target was never reached because B fired first.
2. **Ranger‑B net demoted and gated:** armed only below `dist_est = 65` (< D_BRAKE), trips on median‑B ≤ 40. It therefore *cannot* pre‑empt the 81 mm stop; it only catches a gross dead‑reckon overshoot into the danger zone. (B has no trustworthy close‑range calibration, so it can't be a primary close trigger — this run logs B all the way in to fix that for the future.)
3. **`read_D0` rejects A no‑echo (2000) spikes** (cycle‑1 of the prior run read D0=2000). Enc‑cap failsafe is now reliable.
4. **Time cap tightened** to 2600 ms.

## 2. FROZEN PREDICTION (before running)
A/encoder frame:
- Brake (dead‑reckon, reason 1) at `dist_est ≈ 81 mm`; **rest_A ≈ 66 mm**; cycle spread **≤ ±8 mm**.
Bumper/wall frame:
- **true gap ≈ 35 mm**, **no contact** (35 mm ≈ 3.7σ above 0).
- Heading within **±6°** during approaches.
- Derived checks: `d_stop` recomputed from settle encoders should stay ~15 mm; A‑fix ≈ 448 mm; re‑measured `c_offset` within ±10 of 31.

## 3. The operating‑point operator measurement (characterization measurement #2)
After the run, with the rover at the **final** cycle's rest (unmoved): operator measures the **bumper‑to‑wall gap once**, in mm.
Purpose — closes three things at the true operating point: (a) confirms **no contact**, (b) confirms `c_offset` transfers (predict ~35 mm; expect the measurement near that), (c) supplies the operating‑point ground truth **Gate C** requires. Justification for a 2nd measurement: the first (122 mm) was at a non‑operating distance; the objective must be closed where the rover will actually operate.

## 4. Pass / fail
**PASS (→ Gate C, then lock + 5 runs):**
1. No contact on any cycle.
2. Measured final true gap in **[20, 55] mm** (near predicted 35, allowing c_offset/slip).
3. Rest_A cycle spread ≤ ±10 mm; recomputed `d_stop` 10–20 mm.
4. Heading ≤ ±6°; clean sentinel; settle encoders present.

**FALSIFICATION (→ re‑derive, v1.2, re‑run):** contact; or true gap outside [20,55]; or spread > ±10 mm; or `d_stop`/`c_offset` shifted beyond tolerance.

## 5. After
Gate C closes the objective on the measured operating‑point gap. Then **lock this exact program** (no post‑verification tuning) and run it **5×** at max speed, power‑cycling and re‑squaring between runs; freeze onboard per‑run gap estimates before requesting the operator's per‑run ground truth at close‑out.

## 6. Economy
Re‑verify: **1** program run, **1** operator measurement (the 2nd, and last, characterization measurement). No further characterization planned unless falsified.
