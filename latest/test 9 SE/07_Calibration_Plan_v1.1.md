# Calibration Plan — v1.1 (revision of v1.0)

**Status:** forward-looking plan. **v1.0 is retained**; this revision supersedes
only the sections named below, driven by the Run 1 anomaly report
(`06_Anomaly_Report_Run1.md`). All v1.0 content not listed here is unchanged.

**Change summary (v1.0 → v1.1)**
1. §0 Sensitivity — **heading re-ranked from low ("monitor only") to high**; it
   drives straightness *and* trigger-sensor validity.
2. **New §T Telemetry budget** — hard BLE throughput ceiling; logging strategy.
3. **New §R Ranger selection** — trigger on ranger **A**; B is cross-check only.
4. **New §C Control** — closed-loop **heading correction** on the hot path.
5. §4 Run design — updated to reflect §T/§R/§C and hard-coded (sanity-gated)
   configuration.

---

## §0 (revised) Sensitivity ranking
Unchanged rows from v1.0 omitted for brevity; the change is the promotion of
heading and the addition of a "why" tied to Run 1 evidence.

| Parameter | Range (prior) | Objective/margin sensitivity | Knowledge tier | Priority |
|---|---|---|---|---|
| `c_offset` (true gap − ranger-A rest) | 0–130 mm | ~1:1 on final gap | none onboard → operator | **P1** |
| **heading / straightness** | **0–15°/approach** | **high: veer curves the path and drags ranger B off-target (Run 1: ~13°/approach, B froze ~330 ms); also skews range** | **onboard (IMU), now actively controlled** | **P1 (was P3)** |
| `d_stop_const` (speed-dependent stop) | 30–90 mm | sets the achievable gap and σ_brake | onboard, direct (trigger−rest) | P1 |
| `v_max` | 300–520 mm/s | 62 mm on threshold; immunized by direct `d_stop` | onboard | P2 |
| `a_decel` | 2000–4000 mm/s² | 47 mm; **redundant given direct `d_stop`** → coarse OK | onboard (IMU + range-diff), coarse | P3 (was P2) |
| `refresh` | 20–40 ms | 22 mm | onboard | P3 |
| `k_gain` (mm/deg) | 0.4–0.7 | encoder failsafe scaling only | onboard | P3 |

Consequence: **`a_decel` is downgraded** — since the whole stop is measured
directly at the operating point, dense deceleration data is no longer needed,
which is what frees the telemetry budget in §T.

## §T (new) Telemetry budget
- **Hard ceiling: ~30 telemetry lines/second** over BLE (`print`), measured on
  Run 1 (1749 lines / 50 s). Plan every run to **≤ ~1000 total lines** with
  margin under the 50 s host timeout.
- **Buffer everything, integer-only, dump per cycle.** No direct prints on the
  hot loop or in reposition. Dumping per cycle (not once at the end) preserves
  earlier cycles' data if a later phase truncates.
- **Downsample** to ~40–50 ms; log the minimal set: `d_f0` (ranger A), `d_f1`
  (ranger B, cross-check), `heading_dx10`, `ml_deg`, `mr_deg` on approach;
  `d_f0`, `d_f1`, and one forward-axis accel in the settle window.
- **Wall-clock guard:** exit to `finally` before 50 s so the flush sentinel
  always emits.
- Environment constraint: this hub's MicroPython lacks `sys` and `array`;
  programs use **core built-ins only** (`print`, `list`).

## §R (new) Ranger selection
- **Primary trigger + range channel: ranger A (port A).** Run 1: A tracks
  smoothly and baselines ≈ true start (1028 vs ~1000); B reads ~130 mm short and
  froze for ~330 ms mid-approach.
- **Ranger B: logged for cross-check only**, not in the trigger path.
- **Safety backstop retained on `min(A, B)`:** a k-independent absolute distance
  floor still forces a stop if *either* sensor sees the wall very close, so a
  single-sensor fault cannot cause contact.
- `c_offset` is defined against **ranger A's rest reading** and bound by the one
  costed operator measurement at the verification run.

## §C (new) Control — closed-loop heading
- Single `reset_heading(0)` at start captures the operator-squared orientation as
  heading 0 (global reference for the whole run).
- **Square-up** to |heading| < ~2° before each calibration approach (brief
  in-place rotation; `(+,+)` decreases heading per Run 1).
- **Hold heading ≈ 0 during the approach** by trimming the faster wheel:
  `left = base − k·h`, `right = base + k·h` (signs applied for polarity
  (−1,+1)), clamped. Direction is empirical: right-faster ⇒ heading-negative ⇒
  reduce right. Both motors stay near max, so **maximum speed is preserved** —
  straight-line max is set by the slower motor, which is the correct physical
  ceiling for a straight run.
- Base command is set **near the motor max (~1000 dps)**, not far above it, so
  the proportional trim is actually effective (commands above the motor ceiling
  saturate and cannot be trimmed).

## §4 (revised) Characterization run design
- **Configuration hard-coded** (motors C/D; forward rangers A/B, A primary; rear
  E; color F; polarity (−1,+1)) to save time and avoid the discovery-nudge
  rotation — **gated by a baseline sanity check**: A and B in [750, 1300] and
  within ~250 mm of each other, E > 1500 (rear open); otherwise abort safely.
- **3 approach cycles** at conservative triggers (**A** ≤ 350/300/250 mm) with
  heading held straight; each yields a (trigger reading, rest reading) pair.
- Binds: `v_max` (cruise slope of A, now un-corrupted by veer), `d_stop_const`
  (trigger−rest on A, per cycle), σ_brake (spread across the 3 stops), σ_meas
  (rest-dwell spread), `k_gain` (encoder-vs-A slope), coarse `a_decel`.
- **Deferred to verification run:** the single operator gap measurement binds
  `c_offset` and validates absolute gap at the operating point (unchanged from
  v1.0 §5).

**Forecast:** Phase 1 = the re-run of Run 1 (calibration) + Run 2 (verification)
+ 1 operator measurement, plus the 3 program runs already consumed
(2 import-crashes + 1 partial). Minimum-runs discipline applies from here.
