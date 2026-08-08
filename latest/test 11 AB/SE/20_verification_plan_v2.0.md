# 20 — VERIFICATION PLAN, Wall-Approach Rover — v2.0 (Gate C resubmission) — **FROZEN**

Supersedes Verification Plan v1.0, falsified on criterion 8 (heading) per
AR-003. Predictions frozen at issue; falsification ⇒ v3.0, never edits.

## 0. Configuration under verification

| Item | Fingerprint |
|---|---|
| **OP-WAR v1.1** (18_op_program_v1.1.py) | md5 `2d174fe192fb260588fee4bd34ae8592` |
| Diff vs v1.0 | yaw-hold trim block (KP 4 %/°, cap 15 %, slew 1 %/tick, outer wheel full duty), dh_max + trim_pct_max notes, G_AIM 42→50, version 1.1 — nothing else |
| Bindings driver v1.1 (17) | ψ corrected per AR-003; σ_stop 13.4 mm; heading_bound 10° |
| Qualification (19) | 210/210 hard-PASS (1 declared-tail soft breach, no contact); 400-seed soak: 0 contacts, worst min-gap 13.4 mm, yaw-at-brake p95 0.9°, whole-run heading max p95 2.9° |
| Mock-vs-flight validation | un-trimmed v1.0 in corrected plant reproduces the R-VER arc class |

R-VER-2 = one run of byte-identical OP-WAR v1.1 from the start line
(operator re-squares; hub-ready before flash). 45 s host timeout.
**Characterization run 4.**

## 1. Frozen predictions

| Quantity | Prediction |
|---|---|
| Corner-referenced C_final | **41 ± 13.4 mm**, 3σ window **[1, 81] mm** |
| Sensor-line rest | ≈ 50 ± 13 mm |
| Trigger: corrected gsig | ≈ 113 mm at v̂ ≈ 604 |
| Trigger: raw B reading | ≈ 73 mm |
| Plateau | ≈ slower ceiling ~944 dps, outer wheel 100 % duty, trim ≤ 15 % |
| Heading | dh_max ≤ 10° hard bound; expected ≤ ~5° (trim ~1–2° + skid swing) |
| Onset | 41 ± 10 ms |
| est.c_final (= c_pred) | ±25 mm nominal of true rest (tails ±45 at 2σ corners) |
| P(contact)/run | 0.11 % (≈ 0.57 % over 5) |
| Emission | ≤ 20 s, sentinel present |
| Sim cross-check | median gap 52, p5–p95 [27, 72] — sits right of the analytic center by safe-side allowance stacking, same 3σ window; the frozen prediction is the analytic row above |

## 2. R-VER-2 pass criteria (falsifiable)

1. **No contact** — amax within the no-contact brake family, no strike
   spike; encoder + calibrated-skid reconstruction consistent with a
   positive corner clearance *computed at the measured dh_max geometry*.
2. **Clean run** — census_ok, run.ok, no abort/exc.
3. **Stop quality** — rest achieved; hold ≥ 2 s; creep ≤ 4 mm eq.
4. **Prediction window** — est.c_final ∈ [1, 81]; |est.c_final − 41| ≤ 40.3.
5. **Trigger integrity** — gsig ≤ thr proper crossing (within 25);
   glitch_rej and est.disagree reported.
6. **Speed** — full-duty outer wheel; plateau ≥ 0.95 × slower ceiling;
   no slowdown before trigger; trim_pct_max ≤ 15.
7. **Telemetry contract** — sentinel; emission ≤ 20 s; no overflow; jitter
   ≤ 5 ms.
8. **Heading (SYS-8, on the MAX)** — **dh_max ≤ 10°**, with trim
   functioning: dh_max expected ≤ ~5°; dh_max > 10° falsifies; dh_max in
   (5°, 10°] passes with mandatory analysis note.

## 3. After R-VER-2

Verification Report v2.0 (Gate C resubmission) closing all 52 with the
corrected SYS-8 evidence → operator review → lock v1.1 → 5 operation runs →
strict close-out order. Score at resubmitted Gate C: 4 characterization
runs, 1 operator measurement.
