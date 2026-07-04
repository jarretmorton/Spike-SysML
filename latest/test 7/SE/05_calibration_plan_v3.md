# Calibration Plan — Wall-Approach Rover — **v3**

**Document type:** PLAN (living; v1, v2 retained as prior record).
**Supersedes:** `05_calibration_plan_v2.md`.
**Revision trigger:** C1-v2 (clean run, no contact) + operator measurement #1 (true closest gap = **196 mm**). This resolved an instrument fault and corrected several interpretations. Plan v2 §R.5 listed "an emergency-floor stop / sensor disagreement" as a trigger; a ~130 mm sensor disagreement is that trigger.

**Scope:** the analytical core (v1 §0.2 sensitivity ranking, §0.3 measure-directly strategy, §2.1/2.2 cross-sourcing & source-of-truth, §3 the two costed measurements, §4 verification structure) is unchanged and still valid. This revision records the **sensor-B fault disposition**, the **corrected parameter picture**, the **trigger-sensor + backstop change**, and the **updated run plan**.

---

## R3.0 Disposition: sensor B is faulty (instrument imperfection, tenet D)

C1-v2 stopped cleanly at a true closest gap of **196 mm** (operator), which matches **sensor A** (203 mm, offset ≈ +7 mm). **Sensor B read ~130 mm low throughout** (crawl 888 vs A 1025; rest 80 vs A 203; trigger 156), and the operator confirmed the rover front is **flush with nothing protruding** — so B is not seeing a real closer surface; it is **faulty / mis-aimed** (likely a floor or chassis reflection).

**Disposition:** **B is excluded** from triggering and gap estimation, and is **logged only for monitoring** (a persistent ~130 mm under-read is itself a watch item; if it changes, escalate). **Sensor A is the trusted forward channel.** This is an epistemic-hygiene action (characterize and quarantine the imperfect instrument), not a tuning change.

Because the previous trigger was `min(A, B)`, **B's low reading fired the stop early**, which is why C1-v2 halted safely-but-loose at 196 mm rather than tight. Triggering on A alone removes that.

## R3.1 Corrected / confirmed parameters

My v2-era worry that the encoder under-counted `D_stop` (brake slip) was an **artifact of trusting B** and is **withdrawn**. With A anchored to the 196 mm truth, everything reconciles:

| Quantity | Value | Basis / confidence |
|---|---|---|
| **`D_stop`** | **≈ 6 mm** (sharp `hold()` stop) | encoder Δ (12.5°) × k; trigger→rest segment matches the A-anchored travel; **trustworthy**. A sharp stop *helps* closeness. |
| slip (rolling) | ~5% over the approach | whole fast approach: encoder 695 mm vs A-anchored travel 733 mm; concentrated in rolling, negligible in the stop |
| **`k_speed`** | **≈ 27.6 mm/rad** | crawl (27.8) and stop-segment (27.5) agree; matches ~56 mm wheel; **trusted** |
| **`omega_cruise`** | **≈ 1042 deg/s** (~18.2 rad/s) | steady cruise, both runs; `v_max` ≈ 505 mm/s |
| **sensor A offset `b_A`** | **≈ +7 mm** (reports true + 7) | operator #1 (196) vs A rest (203); tier-4 anchored |
| sensor B | **faulty, ~−130 mm**, excluded | see R3.0 |
| `r_min` (A) | reliable at ≥ ~200 mm; near-range TBD | A accurate at 196–200; near-floor behaviour not yet needed (encoder-primary) |

**Objective model, corrected.** With A trusted and the stop sharp: `final_true_gap ≈ R_trigger − b_A − o − D_stop`, where `o` is the sampling+latency overshoot (rover is slightly closer than the reported trigger implies). `b_A ≈ 7`, `D_stop ≈ 6`; `o` and all spreads are what remain to characterize. The lumped `(b_A + o + D_stop)` is measured directly at the operating point by V1 + operator measurement #2 — the strategy is unchanged, just now anchored on A.

## R3.2 Program change (prog_v3.py)

Still the locked superset; only R_TRIGGER changes for V1/operation. Changes from v2:

- **Trigger on sensor A only** (faulty B excluded, logged). A is read on the hot path alone → **loop ~25–30 ms (was ~63 ms)** → less trigger-sampling jitter (a direct reduction of `σ_o`).
- **Independent encoder crash backstop:** stop if forward wheel-travel exceeds **`TRAVEL_CAP_MM` = 850 mm** — derived from the ~1000 mm start, **does not rely on any ultrasonic**, so a sensor fault cannot cause contact. Layered with an **A emergency floor** (A ≤ 80 mm reported) and the tightened **`MAX_RUN_MS` = 2500 ms**.
- Crawl now **verifies sensor A specifically** (A must decrease ≥ 40 mm from a plausible standoff) and safe-aborts otherwise; B/E logged for monitoring.

Crash prevention now has two independent legs (trusted sensor A **and** the encoder travel cap), so no single instrument fault reaches the wall.

## R3.3 Run schedule and budget (updated)

Spent so far: **2 program runs** (failed C1, C1-v2) + **1 operator measurement** (#1 = 196 mm, which anchored `b_A`, exposed the B fault, and confirmed `D_stop`/`k_speed`).

| # | Run | Trigger (on A) | Binds / verifies | Operator input |
|:--:|---|---|---|---|
| ~~0,1~~ | ~~C1, C1-v2~~ | — | done: map, signs, k, omega, `b_A`, `D_stop`, B-fault | #1 spent (196 mm) |
| 2 | **C2 (prog_v3)** | conservative 200 (reported) | `D_stop` sample under final config + spread; confirm A-only trigger is safe & tight; approach consistency | none |
| (2b) | **C3** *(only if C2's spread is unclear)* | conservative 200 | second `D_stop` sample for `σ_stop` | none |
| — | *compute operating `R_trigger`; freeze Verification Plan (**GATE B**)* | | | |
| 3 | **V1** | **operating** (computed) | tests frozen prediction; lumped `(b_A+o+D_stop)` at operating point | **Measurement #2** (objective validation) |
| — | *operation ×5, locked prog* | operating | scored | close-out only |

**Next program run is C2** (prog_v3, conservative 200 on A). Decision after C2: proceed to GATE B if `D_stop` and its spread are clean (C1-v2 + C2 give two dynamics samples), else add C3. The failed C1 remains a sunk program-run cost.

**Margin unchanged:** `safetyMargin = k_margin · RSS(σ_o, σ_stop, σ_b, σ_pred)`, `k_margin = 3`. The sharp 6 mm stop and the faster loop both *shrink* the terms, so a tight operating gap looks achievable while keeping the hard no-contact guarantee.

*Revision triggers for v3:* sensor B's offset changes or A begins to disagree with the encoder (re-examine which channel is faulty) · the encoder travel cap fires in C2 (A trigger mis-set) · `D_stop` spread larger than the ~6 mm stop suggests · V1's true gap departs from the frozen prediction beyond margin (re-derive, new Verification Plan version, re-run V1).
