# CALIBRATION PLAN — Wall-Approach Rover — **Revision v1.1**

**Document type:** PLAN (revised and re-issued on new characterization information; prior versions retained).
**Version:** 1.1 · supersedes **v1.0** (`03_calibration_plan.md`, retained unchanged).
**Phase:** Calibration & unit verification (Phase 4), after Run **C1**.
**Realises:** Requirements Specification v1.0 + `02_wall_run_model.sysml`.

> **Scope of this revision.** v1.1 changes only the *run construction* (how a characterization run discovers the plant and logs data) and adds the **C1 findings** that motivated the change. **All other sections of v1.0 remain in force unchanged** — the strategy (§0), the single-speed overshoot insight, the calibration input list (§1), the source-of-truth hierarchy (§2), the channel catalog and cross-sourcing (§3), the outside-input budget (§5, still one operator gap at verification), the verification-support roll-up (§6), and the analysis sequencing (§7, `k → v_max → O → a`). Nothing about the *quantities* being calibrated or the gate structure changes.

---

## R0. Revision history

| Ver | Trigger | Change |
|---|---|---|
| 1.0 | Initial (GATE A) | Baseline plan. |
| 1.1 | **Run C1** revealed the drive base is **mirror-mounted** and that distance-based motor-sign discovery is corrupted by body rotation. | Replace sign-discovery method; add derived gyro heading-trim for straight max-speed driving; move per-sample telemetry off the hot path (RAM buffer, dumped after stop). |

---

## R1. What Run C1 established (findings)

C1 ran to completion with **zero contact** and is the source of these facts:

- **Device map (confirmed, will be reused / hardcoded for the locked operation program):**
  - Drive motors: ports **C** and **D**.
  - Forward ultrasonics: ports **A** and **B** (both read the wall ~0.9 m at squared start; agreed).
  - Rear ultrasonic: port **E** (read max range / open space — correctly excluded by the forward-ID test).
  - Color/reflectance: port **F** (unallocated, logged opportunistically — read ~32 reflectance, consistent with floor).
- **The base is mirror-mounted.** A same-direction command to both motors **rotates** the rover in place. Driving forward therefore requires **opposite-sign** motor commands.
- **Failure mode of v1.0 sign discovery:** v1.0 inferred motor forward-direction from the **change in forward distance** during a nudge. On a mirror base a wheel nudge predominantly *rotates* the body, sweeping the forward ultrasonics off the wall; the distance reading then jumps to max range and **swamps the small translation signal**. v1.0 concluded `(−1, −1)` — a spin command — and the rover executed ~3.25 rotations in place (heading 9°→1171°) instead of approaching.
- **Toolchain proven:** flash → run → telemetry-retrieval all functioned; the wire contract and end-sentinel behaved as specified.
- **Sampling-rate observation:** emitting ~9 telemetry lines *inside* the control loop throttled it to ~14 samples across the whole maneuver — too sparse to resolve a brake curve.

None of the v1.0 calibration *targets* were obtained (no valid forward run occurred), so C1 is **re-run as C1′** under the corrected construction below. C1′ remains a characterization run and is acknowledged to count toward the program-run score; correctness here is the precondition for every downstream gate, so the re-run is the right expenditure.

---

## R2. Corrected run construction (replaces v1.0 §4 "test-like-you-fly run construction")

The shared run skeleton is unchanged in intent (a characterization run is a strict **superset** of the operation program; the extra logging lives **off** the hot path). Three concrete changes:

### R2.1 Rotation-proof port/sign discovery

Order of operations (the rover is squared at the start line by the operator; discovery does **not** require any operator input):

1. **Device discovery** — try-construct ladder per port; each device constructed exactly once (Pybricks port-claim rule). *(unchanged; verified working in C1.)*
2. **Forward-ultrasonic identification** — read all rangers while squared; the two that agree in plausible forward range are forward, the odd one is rear. *(unchanged; verified working in C1.)*
3. **Mirror-vs-aligned detection — by heading, not distance.** Apply a brief **same-sign** pulse to both motors and read the **IMU heading change**:
   - large |Δheading| (> 20°) ⇒ **mirror base** ⇒ the *translating* configuration is **opposite-sign**;
   - small |Δheading| with clear translation ⇒ **aligned base** ⇒ translating configuration is same-sign.
   The sign of that same-sign Δheading also fixes `SPIN_DIR` (the rotation polarity), used to re-square.
4. **Forward-direction — from a translating pulse, with re-squaring.** Re-square to the wall (closed-loop: rotate via the known rotating-configuration until heading ≈ 0) so the forward sensors face the wall, then apply a brief pulse in the *translating* configuration. Now the rover actually translates, so the **distance sign is meaningful**: distance decreased ⇒ that polarity is forward; increased ⇒ use the opposite polarity. Re-square again afterwards.

Heading (a rotation-domain measurement) is used to resolve a rotation-domain ambiguity; distance (a translation-domain measurement) is only trusted while the rover is actually translating and squared. This is the specific error v1.0 made — mixing the domains — now corrected.

### R2.2 Derived gyro heading-trim (instantiates CMP-3.2, derived not tuned)

At full motor saturation ("max speed") the two regulators lose authority to equalize, so a mirror base will tend to veer. Straightness (SYS-5 / CMP-3.1) is held by a **proportional heading-trim that slows the leading wheel** (it never speeds a wheel past max, so commanded speed stays at maximum — this is *not* "slowing for margin," it is the straight-approach correction the spec already permits):

- A short **yaw-response probe** (command one wheel faster than the other, read Δheading) measures `YAW_DIR` = the sign mapping *wheel-speed differential → yaw*. This makes the correction sign **measured**, and the proportional gain **derived from the observed veer**, satisfying the requirement that CMP-3.2 be derived rather than hand-tuned. The probe value is logged (`yaw_dir`).
- Trim law: `D = −Kp · heading · YAW_DIR`; the wheel that should be slower is reduced by `min(|D|, TRIM_MAX)`. Authority is bounded (`TRIM_MAX` ≪ max speed) so the correction cannot itself become a hazard.

If C1′ shows the natural veer is already within the SYS-5 budget without trim, the trim term is retained at the gain that holds it (a measured, possibly small, gain) — its instantiation is now justified by data, per the spec's "Optional/Derived" condition on CMP-3.2.

### R2.3 Off-hot-path logging (RAM buffer, dumped after stop)

The control loop **buffers** each sample `(t, fwd_a, fwd_b, ang_0, ang_1, heading, accel_x, accel_y)` in RAM and performs **no I/O** while moving; after the rover is stopped and held, the whole buffer is streamed out as telemetry, followed by the static final readings and the end-sentinel. This restores a dense sample rate (target ≫ 14 across the maneuver, sufficient to resolve the deceleration tail and hence `O` and `a`). This is the buffering the v1.0 skeleton already called for and which the C1 program failed to implement.

---

## R3. C1′ run design (safe characterization, unchanged safety envelope)

Identical safety posture to the v1.0 C1: brake trigger at a conservative **400 mm**, plus guards (hard floor, approach-time cap, wrong-direction abort). Expected final gap ~200–300 mm ⇒ **no contact risk**. C1′ now actually drives forward at **maximum speed** (the operation speed), so a single C1′ binds the operating-point quantities directly — `k` (Δrange ÷ Δodometry), `v_max` (cruise dR/dt), `O` (overshoot at max, bias-tangled), refresh cadence, residual creep, deceleration `a`, and the natural heading veer — with **no extrapolation**, exactly as §0 intends. The operator ground-truth gap (the single Phase-1 outside input) is still taken later, at the verification run, to anchor sensor bias `b` and yield the bias-free `O`.

**Planned program ledger (updated):** C1 (spin, diagnostic — complete) → **C1′** (corrected characterization) → **Verification run** (integrated, frozen prediction + operator gap). Re-runs only if a gate falsifies.

*End of Calibration Plan v1.1 (supersedes v1.0; v1.0 retained).*
