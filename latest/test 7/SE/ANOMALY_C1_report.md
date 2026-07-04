# ANOMALY REPORT — C1 run (run-20260702-094256)

**Type:** ANOMALY REPORT (free deliverable; ends with a recommendation).
**Run:** C1, first characterization run. `completed: false` (host timeout at 15.2 s).
**Classification:** **IMPOSSIBLE / DANGEROUS — escalate unconditionally.** A hard constraint (SYS-1 No-Contact) was violated: the rover drove into the wall at maximum speed and remained against it with wheels slipping for ~6 s. **Disposition: HALT. Do not retry as-is. Operator inspection required before any re-flash.**

---

## 1. Timeline (reconstructed from telemetry, hub clock)

| t (ms) | Event | Evidence |
|---|---|---|
| 34–92 | Device probe OK: 2 motors, 3 ultrasonic, 1 color | `det_n_motors=2`, `det_n_ultras=3`, `det_n_colors=1` |
| 78–92 | Baselines: A=1022, B=866, E=549 mm | `det_base_u0/1/2` |
| 2295–2401 | Direction nudges: (+,+) spun (−19.9°), (+,−) translated (+1.2°) | `det_dheadA=−19.88`, `det_dheadB=+1.18` |
| ~2460 | **Detection fell back to "smallest baseline = forward"** → picked E (549, primary), B (866, secondary); A→rear | `det_forward_sign=−1`, `det_primary_port=4 (E)`, `det_secondary_port=1 (B)` |
| 2762 → 4621 | Approach: **B (wall-facing) descends 866 → 40 mm**; **E (primary) rises 549 → 757 → 2000** | `distance2` ↓, `distance` ↑ then 2000 |
| ~4621 | **Rover reaches wall (B at 40 mm floor)** | `distance2` min 40 @ 4621 |
| 4621 → 10682 | **B pinned at 40 mm; motors still at max; heading skews to ~13.5°; encoder accrues to 7621°** | `distance2`≡40, `heading`≈13.5, `angle_rest_deg=7621.5` |
| ~10762 | Loop hits `MAX_RUN_MS=8000` and breaks (no trigger ever fired) | `triggered=0`, `trigger_report=0` |
| 11742+ | `hold()`, settle, latched scalars emitted | scalars present |
| 11744 → 15219 | Buffer dump too slow over BLE; host timeout mid-dump | only 20 `hf_*` samples; `completed:false` |

## 2. Primary evidence

- **`distance2` (port B, wall-facing):** 866, 651, 423, 251, 133, 63, **40** (t=4621), then 40 held for ~5.7 s. A sensor at its ~40 mm near-range floor, held while driving at max speed → the rover is against the wall.
- **`distance` (port E, selected as trigger sensor):** 549 → 757 → **2000 (held)**. E is not wall-facing; the trigger (`primary ≤ 180`) could never fire.
- **`triggered = 0`, `trigger_report = 0`, `angle_trigger_deg = 0`:** the loop exited on the 8 s safety timeout, not on a stop trigger. `D_stop_deg = 7621.5` is therefore meaningless (whole-run rotation, not a stopping distance).
- **`heading`:** 0 → ~13.5° and held — chassis skew from pushing against the wall.
- **`omega_cruise_deg_s = 1044`** (18.2 rad/s) — full commanded speed was reached; the rover hit the wall at cruise, not slowed.

## 3. Root cause (two independent defects, both in my program design)

1. **Primary/forward-sensor mis-identification.** The paired-nudge direction detection produced a distance signal below the `MOVE_THRESH_MM = 8 mm` gate (short 150 deg/s × 250 ms nudges, cancelled by their undo, against ultrasonic quantization and 2000-mm "no-echo" artifacts). It therefore fell to the **"two smallest baselines = forward" fallback, which is wrong**: the wall-facing sensor reads the ~1000 mm standoff (the *largest* of the forward group, here A≈1022 and B≈866), not the smallest. Port E (549 mm, actually rear/angled) was chosen as the trigger sensor. The trigger watched a sensor that never saw the wall.
2. **Inadequate safety backstop.** `MAX_RUN_MS = 8000 ms` at ~500 mm/s permits ~4 m of travel — no protection when the wall is 1 m away. And the trigger depended on a *single* (mis-identified) sensor with **no independent "any forward sensor sees close → stop" cutoff**. A detection error thus led directly to a crash instead of a safe abort.

A third, non-safety defect: **telemetry volume.** The post-stop full-rate buffer dump was too slow over BLE; the run did not complete within 15 s (only 20 of ~400 buffered samples emitted). This must also be fixed so runs finish and the sentinel is reached cleanly.

## 4. Salvageable findings (trusted-reference-first; what C1 *did* establish)

- **Port map (high confidence):** motors on **C (idx 2)** and **D (idx 3)**; ultrasonic on **A (0)**, **B (1)**, **E (4)**; color on **F (5)**. The type-probe (UltrasonicSensor→Motor→ColorSensor, keep first success) worked with no EBUSY.
- **Wall-facing (forward) sensor identified empirically:** **port B** tracked the wall monotonically 866 → 40 mm. **Port A** (baseline 1022 ≈ the true ~1000 mm standoff) is the other forward candidate. **Port E** is rear/angled (reading rose then went to the 2000 no-echo value). This replaces the failed nudge inference with direct evidence.
- **`k_speed` first estimate ≈ 27–30 mm/rad** (early window: B Δ≈−287 mm over ≈9.5–10.8 rad of wheel rotation) — consistent with a ~56 mm wheel; to be refined on a clean forward segment.
- **Motor max speed ≈ 1044 deg/s (18.2 rad/s).**
- **Ultrasonic behavior:** near-range floor ≈ **40 mm**; "no-echo" sentinel = **2000 mm**; brief echo instability right at the floor (a lone 139 then 2000 then back to 40). Confirms the operating-point rest reading will be below the reliable floor — vindicating the encoder-primary `D_stop` decision.

## 5. Disposition and recommendation

**Recommendation: HALT and fix; do NOT retry C1 as written.**

1. **Operator action (blocking):** please inspect the rover, back it off the wall, check for any damage, and re-square it at the start line (~1000 mm). Confirm before any re-flash.
2. **Program revision (I will make before re-flashing; free):**
   - **Robust forward-sensor selection** using this run's evidence: watch the sensor(s) whose reading *decreases* under confirmed forward motion — i.e., use the port map (B, and validate A) as the wall-facing channel — rather than the smallest-baseline heuristic. Retain a clean, longer forward calibration segment early in the run to confirm the wall-facing sensor before committing to the fast approach.
   - **Independent hard safety cutoff:** stop if *any* forward-candidate ultrasonic reads below a safe floor (e.g. ≤ 250 mm), regardless of which sensor is "primary." This guarantees a safe abort even if selection is imperfect.
   - **Tighten `MAX_RUN_MS`** to a physically-sane bound (cover ~1200 mm at cruise ≈ 2.5–3 s), so the backstop actually prevents a wall crash.
   - **Cut telemetry volume** so the run completes: stream a light downsampled set live and either drop the full-rate buffer or downsample it hard; keep the latched scalars and sentinel.
3. **Plan revision:** re-issue the Calibration Plan as **v2** (prior version retained), replacing the nudge-based forward/rear method (§2.3) with the empirically-anchored port map + the hard safety cutoff, and noting the telemetry-budget change. This is a documented revision trigger from Plan v1 §5 ("detection flaky → hard-code map").

No re-flash until (a) the operator confirms the rover is inspected, undamaged, and re-squared, and (b) the revised program is reviewed and explicitly authorized.
