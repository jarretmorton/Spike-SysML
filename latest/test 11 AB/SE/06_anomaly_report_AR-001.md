# Anomaly Report AR-001 — R-CAL run 1 (run-20260712-231537)
**Status:** Dispositioned — corrective actions specified, carried into CP-WAR v1.1 and R-CAL v1.1. | **Contact:** none (min approach ≈ start distance; rover never exceeded pulse motion). | **Safety systems:** performed as designed (classification refusal → safe hold → full dump → sentinel).

## A. Events

**AR-001a — run failed to start (ground segment).** First `run_program` returned `TimeoutError` with no run id, zero events, no motion: the host→hub BLE session never opened. Immediate retry succeeded. Root cause: transient BLE session-open failure (hub advertising latency after the flash disconnect is the usual mechanism). Corrective action: none to flight software; retry-once is the standing procedure. Consequence: none (no motion, no data, no score impact beyond the single run consumed by the successful retry).

**AR-001b — sign ladder failed to resolve (flight).** Run executed 9.11 s: census PASS (2 motors {C,D}, 3 rangers {A,B,E}, 1 color {F}), static PASS, then four S1 pulses, no classification, `abort_signs`, safe hold, dump (1.26 s), sentinel. **Characterization run 1 consumed.**

## B. Evidence (telemetry, run-20260712-231537)

| Pulse | Command | Δus A | Δus B | Δus E (rear) | Δψ |
|---|---|---|---|---|---|
| 1 (300 ms) | (+,+) | +979 (→ no echo) | +111 | −1458 (echo gained) | **−31.2°** |
| 2 (300 ms) | (+,−) | 0 | +12 | −126 | +1.7° |
| 3 (450 ms) | (+,+) | 0 (already no echo) | +941 (→ no echo) | +1584 (→ no echo) | **−58.5°** |
| 4 (450 ms) | (+,−) | 0 | 0 | 0 (all blind) | −1.8° |

Statics: A = 1022 mm (MAD 2, update 24 ms), B = 904 mm (MAD 2, update 20 ms), E = 2000 pegged (no echo), IMU drift 0.01°/2 s, battery 7594 mV, u_est 22 ms, dump 1263 ms ≈ **2.2 kB/s BLE**.

## C. Root-cause chain (three compounding causes)

1. **Mirror-mounted motors:** same-sign command (+,+) is the ROTATION parity on this rover (Δψ −31°, −59° — twice confirmed). Anticipated by the ladder design; not itself the failure.
2. **Translation authority below the classification threshold:** the (+,−) translation pulses moved ~0–12 mm against a ±12 mm threshold. Two contributors: the wheel constant is small (translation ≈ 12 mm over a 300 ms 250 dps pulse implies k ≈ 0.2–0.35 mm/deg, at/below the prior floor of 0.30), and Pybricks `run()` acceleration-limits the ramp so a 300 ms pulse spends most of its time below commanded speed. The sim's ramp model was tied to the speed ceiling and did not reproduce a slow ramp on a low-k rover.
3. **Un-recovered rotation destroyed scene visibility:** the ladder retried the known-rotation hypothesis first (adding −59° to −31°); at ~90° total yaw, all three rangers lost the wall (2000 pegged), so even a good translation pulse (pulse 4) produced zero deltas. The sim did not model echo loss versus yaw angle, which is why 465 scenarios missed this.

Additional finding (not a failure): rest readings A−B differ by **118 mm**, exceeding the prior's possible per-pair offset spread (max 60 mm). At least one mounting offset lies outside [−10, +50] mm. Min-fusion makes a *negative* offset conservative (earlier stops); the residual contact-relevant case is *both* offsets large-positive, addressed below.

## D. Corrective actions (→ R-CAL v1.1, CP-WAR v1.1)

1. **Parity elimination:** first (+,+) probe classifying as rotation fixes the rotation parity; all subsequent pulses use only the translation parity {(+,−), (−,+)} — a known-rotation hypothesis is never re-fired.
2. **Rotation undo:** after any |Δψ| > 6° pulse, closed-loop pivot back to the ladder's reference heading (the observed rotation authority, ~100–130°/s at 250 dps differential, makes this fast); the rover therefore faces the wall for every classification attempt. A final pivot re-squares before S2.
3. **Translation authority:** translation-parity pulses at 360 dps × 500 ms (retry 480 dps × 600 ms) ≈ 29–45 mm travel even at k = 0.2 — 2.4–3.7× threshold. Worst-case forward travel bounded ≤ 180 mm/pulse (K_HI), leaving ≥ 500 mm runway.
4. **Blind-scene detection:** all |Δ| < 12 with encoder travel ≥ 40° ⇒ sensors lost the scene or authority too low → pivot to reference and retry stronger, rather than burning the attempt.
5. **Prior extensions (mock + plan):** k ∈ [0.18, 1.0] mm/deg; per-sensor offset o ∈ [−60, +90] mm; run-ramp acceleration 700–2600 dps/s independent of ceiling; front-ranger echo loss beyond 18–40° yaw; BLE 2.0 kB/s.
6. **Both-offsets-high contact guard:** creep trigger raised 90 → 110 mm and O_MAX 50 → 90 in onboard worst-case constants (worst-case creep rest ≥ ~25 mm even at o = +90 on both sensors).
7. **Emission re-budget at 2.0 kB/s:** tighter windows/decimation (~≤ 45 kB), run timeout 75 → 90 s.
8. **Re-qualification:** full suite + soak with the new fault axes, plus a directed "as-built" scenario replicating this rover (mirrored parity, k ≈ 0.25, slow ramp, echo loss ~25°, offsets +70/−48).

## E. Disposition

Retry R-CAL as v1.1 after mock re-qualification and operator go-ahead. Budget impact: total program runs 2 → 3 (R-CAL₁ consumed, R-CAL₂, R-VER). M1 unspent and reserved for the near-wall rest. No requirement changes; no model-structure changes (all corrections are within the S1 procedure, onboard worst-case constants, and sim fidelity).
