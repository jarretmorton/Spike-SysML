# C1 Program — Review Note (pre-flash)

**Status:** the C1 characterization program (`c1_program.py`) is **written and syntax-checked but NOT flashed.** It is staged now so the exact code can be reviewed alongside Calibration Plan v1, and so we can flash immediately once (a) GATE A is approved, (b) you give an explicit go-ahead to flash, and (c) the rover is power-cycled and squared up at the start line. Staging code changes nothing about the gate.

This is a head-start on the post-GATE-A characterization phase, not part of GATE A itself.

---

## What this program is

The **locked superset program** (Calibration Plan §2.3): the identical detection → accelerate-to-max → paced loop → `hold()`-both stop → `try/finally` structure that V1 and all five operation runs will use. Only two things ever change downstream: the **trigger threshold value** and the **trimming of extra logging**. Everything else is frozen here so that hot-path timing — hence `t_response` and `D_stop` — is identical in characterization and operation.

## Program section → plan mapping

| Program section | Calibration Plan reference | What it produces |
|---|---|---|
| §1 Port/device detection (probe U→M→C, keep first success) | §2.3 detection; avoids EBUSY double-claim | port map (telemetry `det_*_port`) |
| §2 Direction detection (paired nudges, spin-vs-translate via IMU) | §2.3 forward/rear + motor-sign discovery | `det_sign0/1`, `det_primary_port`, forward pair |
| §3 Accelerate to max + paced loop | §2.3 test-like-you-fly; §2.1 `omega_max`, `v_max`, `k_speed`, `alpha`, `r_min`, `heading_drift` | live `distance/distance2/heading`; full-rate `hf_*` |
| §4 Stop (`hold()` both) + settle + latch | §2.4 D_stop channel; SYS-4 rest speed | `angle_trigger/rest_deg`, `rest_speed_deg_s` |
| §5 Latched scalars | §2.4; onboard gap estimate inputs | `trigger_report`, `rest_report`, `D_stop_deg`, headings |
| §6 Full-rate buffer dump (post-stop, off hot path) | §2.3 extra logging never on hot path | `hf_distance/…/hf_angle_deg` |
| `try/finally` | task rule: motors always stop, sentinel always sent | `{"event":"end"}` |

## Design choices baked in (all traceable to prior analysis)

- **`hold()` on both motors** for the stop — committed a priori as the sharpest, lowest-variance stop; `D_stop` is then characterized empirically.
- **`D_stop` primary channel = motor encoder** (`angle_rest − angle_trigger`, signed so forward is positive), range-independent. `k_speed` (encoder→mm) is derived offline from the approach as `−Δreport/Δangle` (offset `b` cancels), so the program reports the raw encoder delta + the sensor reports and lets the host compute mm with provenance. Ultrasonic report-drop and IMU double-integral are logged as cross-checks.
- **Detection nudges are paired** ((+,+) then (−,−); (+,−) then (−,+)) so net runway creep ≈ 0 and the sequence is deterministic (identical every run). Spin vs. translation is told apart by IMU heading change; forward vs. rear by which readings decrease, cross-checked against baseline magnitude (forward pair ≈ the two smallest baselines at the start).
- **Max speed via regulated `run()` with raised limits** (both wheels speed-matched → straight and maximal), best-effort with a plain-`run()` fallback.

## Please confirm before I flash

1. **Trigger value:** C1 uses a conservative **180 mm reported** trigger (well clear of the wall; rest lands ~130 mm true, above the ultrasonic near-floor, so the C1 rest reading is valid for the `b` anchor / operator measurement #1). OK, or prefer more/less conservative?
2. **Run timeout:** I plan to give `run_program` ~**15 s** (detection nudges ~2 s + approach ~2–3 s + settle + buffer dump). OK?
3. **Detection nudges acceptable?** They move the rover a little during detection but paired nudges cancel net displacement. If you'd rather not nudge, the fallback is a magnitude-only forward/rear classification (less robust on the motor-sign question).
4. **Open item for the *operation* program (not C1):** the trigger fires on a single reading ≤ threshold. A 2-consecutive-reading debounce would reject ultrasonic glitches but adds one loop of latency (slightly larger `D_stop`). For C1 (conservative) a glitch only widens the gap — safe. Worth deciding for the operation program at GATE B; flagging now.

Nothing is flashed until you approve GATE A, give the flash go-ahead, and confirm the rover is staged.
