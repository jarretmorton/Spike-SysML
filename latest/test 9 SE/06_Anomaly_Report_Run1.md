# Anomaly Report — Run 1 (Calibration), `run-20260709-210725`

**Status:** free analysis (no rover contact). **Outcome: physically safe.** All
three cycles stopped on the normal ranger trigger (`stop_reason = 1`); the
closest rest reading was 220 mm (ranger B), i.e. ~140–190 mm true clearance.
The rover never contacted the wall. However, the run is **not usable as
calibration evidence** for the reasons below, and is superseded by a re-run
under Calibration Plan v1.1.

Confirmed reusable facts (carried forward, will be hard-coded with a baseline
sanity gate rather than re-discovered):
- **Port map:** motors on **C, D**; forward rangers on **A, B**; rear ranger on
  **E**; color on **F** (`n_motors=2, n_rangers=3, n_colors=1`).
- **Drive polarity:** forward = (left, right) sign **(−1, +1)**. Commanding both
  motors the same sign spins the rover (mirror-mounted motors), confirmed by the
  `(+,+)` discovery nudge producing a −25.7° heading change with no net
  translation.

---

## A1 — BLE print throughput bottleneck → run truncated, settle data starved
**Severity: high (blocks characterization).** **Class: surprising-but-possible.**

`run_program` returned `completed:false` at the 50 s timeout with **no
`run_done`/sentinel** — the program was still emitting when the host stopped it.
Total telemetry = **1749 lines over ~50 s ≈ 35 lines/s**. This is a hard
BLE/`print` throughput ceiling (~28 ms per line), independent of the control
loop.

Consequences:
- The buffered per-cycle **dumps** (~500 lines each) each took ~15 s to flush,
  consuming the time budget and leaving the final cycle's dump truncated.
- The **settle/rest sampling uses direct `print`** and was therefore
  throttled to ~5–6 samples/cycle instead of the intended ~47. The deceleration
  transient and the rest reading — the inputs to `d_stop_const`, the #1
  calibration target — are effectively missing.
- The approach data itself is intact (it is buffered, not printed, on the hot
  path): ~72 samples/cycle at ~28 ms spacing.

**Disposition:** chase (high leverage — it gates all calibration).
**Recommendations (→ Plan v1.1 §Telemetry):**
1. Treat **~30 lines/s** as a hard budget; cap a run at **≤ ~1000 total lines**
   with margin under 50 s.
2. **Buffer everything** (approach *and* settle), integer-only, and dump per
   cycle so partial data survives truncation; **remove all hot-loop/repos direct
   prints** (e.g., `repos_d`, which alone cost ~100 lines).
3. **Downsample** logged samples (~40–50 ms) and log the minimal channel set.
4. Exploit the model structure: because `d_stop_const` is measured **directly**
   as (trigger reading − rest reading), dense deceleration data is **not
   required** — this removes the most throughput-hungry sampling.
5. Add a wall-clock **guard** that exits to the `finally` block before 50 s so
   the sentinel always emits.

## A2 — Rover veers ~13°/approach (curved path, not straight)
**Severity: high.** **Class: surprising-but-possible (unmodeled motor mismatch).**

Single-approach heading (cycle 0) rose to +4.6° then curved monotonically to
−8.1° at trigger — a **~13° swing in ~1.35 s**; cumulatively the run reached
−26°. Encoder travel over the run was **right 1091° vs left 1048°** (~4% faster
right), consistent with the observed direction of drift.

This violates the straight-line intent (SYS-5) and, more damagingly, drags
ranger B off the wall (see A3), corrupting the trigger channel.

**Disposition:** chase (root cause of A3; and required by the task).
**Recommendation (→ Plan v1.1 §Control, re-ranks heading from low to high):**
add **closed-loop heading correction** to the hot path — hold heading ≈ 0
(the operator-squared orientation, captured by a single `reset_heading(0)` at
start) by trimming the faster wheel; both motors remain near max, so "maximum
speed" is preserved (straight-line max is set by the slower motor). Add a brief
**square-up** to heading ≈ 0 before each calibration approach. Correction sign is
determined empirically (right-faster ⇒ heading-negative ⇒ reduce right).

## A3 — Forward rangers disagree (~165 mm) and B freezes mid-approach
**Severity: high.** **Class: surprising-but-possible.**

- **Offset:** A and B sit ~156–176 mm apart throughout the approach. A baselines
  at 1028 mm (≈ the true ~1000 mm start); **B reads ~130 mm short** — B is
  angled/offset and does not report true perpendicular range.
- **Freeze:** B held **exactly 593 mm for ~330 ms** (2771–3097 ms) while A
  decreased smoothly (757 → 608), then abruptly reacquired. B loses echo as the
  rover rotates and repeats its last value.
- Triggering on `min(A, B)` therefore triggers on the **less accurate, freezing**
  sensor.

**Disposition:** chase.
**Recommendation (→ Plan v1.1 §Ranger selection):** use **ranger A (port A) as
the primary trigger and range channel** (smooth, ≈ true range); keep B logged
for cross-check only. Retain a k-independent absolute failsafe on `min(A, B)` so
either sensor seeing the wall very close still forces a stop. Expectation: with
heading held straight (A2 fix), B's echo loss should largely disappear, but its
~130 mm bias remains, so A stays primary. The A-vs-truth offset is exactly what
the single costed operator measurement at the verification run will bind
(`c_offset`).

---

## Net effect on the process
- Run 1 is re-issued under **Calibration Plan v1.1** (v1.0 retained). The program
  is rewritten accordingly and re-validated on the CPython Pybricks stub before
  re-flash.
- **Program-run ledger:** 2 crashed-at-import loads (no motion, no data) + this
  partial run = 3 characterization program runs consumed. The import failures
  were environment-specific (this hub's MicroPython lacks the `sys` and `array`
  modules) and not catchable on the CPython stub; the program is now restricted
  to core built-ins to prevent recurrence.
- No hard requirement has been falsified; the predictive argument is not yet
  committed (that happens at GATE B), so no re-derivation of a frozen prediction
  is triggered — only a plan/program revision.
