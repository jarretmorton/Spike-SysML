# CALIBRATION PLAN — Wall-Approach Rover — **v3**
**Document:** `14_calibration_plan_v3.md` · **Type: PLAN** (revised and re-issued)
**Supersedes:** v2 (`11_calibration_plan_v2.md`, retained unedited) · **Trigger:** AR-02

---

## 0. SENSITIVITY ANALYSIS (re-run under the REV C architecture)

Bindings applied: `t_loop` = 10.09 ms, `k` = 0.482 mm/deg, `σ_n` = 3.4 mm, `R0` = 910.25 mm,
`ω` = 750 deg/s (now a *design* value — see §2), heading spread 0.3° (heading hold).

| parameter | assumed range | d objective (mm) | d nominal margin (mm) | d degraded (mm) | tier | priority |
|---|---|---:|---:|---:|---|---|
| `b_offset_mm` | −40 .. 80 mm | +0.0 | **−120.0** | −120.0 | T0 | **P1** |
| `k_mm_per_deg` | 0.35 .. 0.8 mm/deg | +11.6 | **−58.0** | −45.3 | T2 prov. | **P1** |
| `a_decel_mm_s2` | 1000 .. 6000 mm/s² | −11.5 | **+54.5** | +54.5 | T0 | **P1** |
| `delta_bs_mm` | 5 .. 40 mm | +0.0 | +0.0 | −35.0 | T0 | **P1** |
| `omega_max_deg_s` | 700 .. 1100 deg/s | +6.6 | −33.3 | −26.0 | design | P1 |
| `tau_sensor_s` | 0.005 .. 0.06 s | +3.2 | −19.9 | +0.0 | T0 | P2 |
| `e_odo_mm` | 2 .. 20 mm | +0.0 | +0.0 | −18.0 | T0 | P2 |
| `t_chain_s` | 0.002 .. 0.02 s | +1.0 | −6.5 | −6.5 | T0 | P2 |
| `t_loop_s` | bound | +1.2 | −3.6 | +0.0 | **T2** | closed |

**Working point:** `v` = 362 mm/s · `S` = 34 mm · `R_trig` = 80 mm ·
σ_run 4.73 ⊕ σ_sys 6.17 → **σ_g 7.78 mm** · predicted gap **23.8 mm** · rest reading 43.8 mm.

### 0.1 What changed, and one thing you should scrutinise

`b_offset` returns to the top and its lead widens: everything else is shrinking as
calibration proceeds, and `b` cannot shrink without M1. Every other P1 is bindable from
RUN-3's own channels.

**The disclosure.** Under REV C the model predicts σ_g falling from 10.36 mm to 7.78 mm and
the achievable gap from 31.3 mm to **23.8 mm**. Some of that is better knowledge, but part
of it is simply that `S ∝ v²` and `σ_S ∝ S`, so **a slower rover scores a better gap**.

That is a perverse gradient and I am flagging it rather than banking it. The task says *do
not slow down for safety margin*, and a plan that quietly discovers "slower is better" has
found a way to game the constraint, not a way to satisfy it. **The justification for the
speed change in §2 is heading authority and nothing else.** The gap improvement is a
disclosed side effect. If you judge that the speed reduction violates the task's intent,
say so and I will hold full command and re-derive the margin with a large yaw term instead
— that is a worse gap and a worse contact margin, but it is your call to make, not mine to
make silently.

---

## 1. CALIBRATION INPUT LIST

**TBD closure: 6 of 29.** Closed or provisionally bound: TBD-01 (design), TBD-02 `k` = 0.482
(provisional), TBD-07 `σ_n` = 3.4 mm, TBD-10 retired with the ranger pair, TBD-11 closed,
TBD-29 = 910.25 mm.

RUN-3 is designed to close TBD-02 (firm), 03, 04, 05, 06, 09, 12, 17, 18, 26, 27.
**M1 closes TBD-08, 16, 28** — still unspent after two runs.

---

## 2. ARCHITECTURE CHANGE — and the requirement deltas it forces

### 2.1 Single forward channel

Ranger A failed by test (AR-02 §1): non-monotonic while closing, 15% dropouts. **It is not
constructed in REV C**, which also stops the runtime polling it and so tests the crosstalk
hypothesis at no cost — if B's dropouts vanish, crosstalk is confirmed.

| requirement | disposition |
|---|---|
| **CMP-6** (ranger A refresh) | **RETIRED** — effector dropped on evidence, not assumption (Rule 7) |
| **FUN-13** (forward-pair agreement) | **RETIRED** — no pair remains |
| **SYS-1 redundancy** | FUN-13's fault-detection role transfers to the **odometric channel**: `S_ranger` vs `S_odo·k` must agree to within the lag term `v·τ`. A *negative* odometric stop distance is the slip signature; a difference far from `v·τ` is the fault flag |

This is a genuine loss of redundancy and I am not going to dress it up: the forward channel
is now single-string, and SYS-7's degraded path (odometric backstop + staleness guard)
carries the whole no-contact case if B fails. That is acceptable only because the backstop
is independent and, with `k` bound after RUN-3, correctly sizeable for the first time.

### 2.2 Regulated speed with heading hold

RUN-2 ran both motors torque-saturated at ≈820 deg/s with a ≈5% mismatch, producing 12.6°
of yaw. **Above saturation a heading correction has no authority** — subtracting from an
already-clamped command changes nothing. Heading control therefore *requires* commanding
below the weaker motor's sustained speed. REV C uses `SPEED_CMD` = 750 deg/s (≈362 mm/s
against ≈395 mm/s saturated, a 8.5% reduction).

**Gain derivation (not a guess).** `dθ/dt = −(2·g·k·57.3/W_t)·θ`, so `τ = W_t/(2·g·k·57.3)`.
Choosing `τ` = 0.3 s gives `g` ≈ 7 deg/s per degree. Track width is the only assumed
quantity, and the choice is robust to it:

| `W_t` | 90 mm | 120 mm | 160 mm | 200 mm |
|---|---:|---:|---:|---:|
| `τ` at `g` = 7 | 0.23 s | 0.31 s | 0.41 s | 0.52 s |

All well inside the ~1.2 s approach and all ≥20× the 10 ms loop, so neither sluggish nor
discretisation-unstable.

**New requirement, derived from AR-02:**

> **FUN-15** **[D]** · *Ubiquitous* · The rover **shall** determine the sign of its
> heading-correction term by measurement before applying it. — *Rationale: which motor is
> on which physical side is not known a priori, and an assumed sign makes the correction
> positive feedback. Derived from the AR-02 analysis, verified by negative test.*

**SYS-4 re-derivation (for your approval).** From *"command each drive motor at its maximum
achievable speed"* to *"command each drive motor at the maximum speed at which it remains in
closed-loop regulation."* Rationale: above that point the commanded speed is fiction — the
motors run at their individual load limits, the rover curves, and no control authority
exists. See §0.1 for the disclosure that this also flatters the objective.

### 2.3 Passive braking

Plugging produced 59 mm of odometry/ranger disagreement — gross slip (AR-02 §4).
REV C uses `brake()`. Expected healthy signature in RUN-3: `S_ranger − S_odo·k ≈ +v·τ`
(≈ +15 mm), *positive and small*. A negative `S_odo` again means slip and re-opens the item.

### 2.4 Telemetry budget

Each `stdout` write blocks ≈240 ms. **Lines are the binding constraint.** REV C emits **43
lines** (verified by dry run) against RUN-2's 168. Raw units are emitted wherever the host
would otherwise need `k`, so no prior is baked into the data `k` is calibrated from.
Run timeout: **45 s** (dry run: 9.7 s of motion + ~10 s of emission).

---

## 3. OUTSIDE-INPUT REQUESTS — unchanged, still two, still unspent

**M1** after RUN-3, conditional on it reaching a close pose **at ≈0° yaw**; **M2** after the
verification run. M1 has now been deliberately withheld twice, both times because the pose
would not have transferred to the operating point. Two runs consumed, zero measurements.

---

## 4. VERIFICATION SUPPORT

Closed and pulled forward: **CMP-11 PASS** (10.09 ms, twice). **CMP-12, CMP-13 DROP** by
traceability, confirmed twice. **FUN-3 PASS**, **FUN-12 PASS** (RUN-1 abort path).
**CMP-6, FUN-13 RETIRED** with the effector. **SYS-6, CMP-3** re-tested in RUN-3 under
heading hold; the simulated peak is 0.23°, against a 5° limit and 12.58° measured open-loop.

RUN-3 additionally unit-verifies CMP-1/CMP-2 directly for the first time: `cruise_wL` and
`cruise_wR` are emitted as cruise-window means, so regulation is checked per motor rather
than inferred.

---

## 5. RUN BUDGET

| | v2 plan | v3 plan | consumed |
|---|---:|---:|---:|
| characterization runs | 3 | **4** | 2 |
| operator measurements | 2 | **2** | **0** |

Remaining: RUN-3 → M1 → GATE B → verification run → M2 → GATE C → operation.

---

## 6. VALIDATION OF REV C BEFORE FLASHING

| check | result |
|---|---|
| nominal dry run | `trigger_reason` 1 · `d_trigger` **597.9** vs 600 (the 119 mm undershoot is gone) · heading peak **0.23°** · `cruise_wL/wR` 748/751 — both regulating · no contact · 43 lines · 9.7 s |
| **negative test — correction sign injected wrong** | found a **new defect**: positive feedback grows only to 4.06° over the short approach, so the 15° guard never trips; the divergence then **ran away during the much longer creep and hit the wall** |
| fix | yaw guard **and** ranger-staleness guard added to the creep loop; re-tested: creep aborts at 26.7°, **no contact** |

That defect was found by free analysis, in a phase I had not thought to guard, because the
failure needed a *long* phase to develop. It is the second time a negative test has been
worth more than a passing one.

---

## 7. WHAT I AM ASKING YOU TO REVIEW

1. **The SYS-4 re-derivation and the §0.1 disclosure.** This is the one place the plan
   touches an explicit task constraint, and the change happens to improve my score. It
   should be your decision, not mine.
2. **Dropping ranger A**, and accepting a single-string forward channel with the odometric
   backstop as the only independent path.
3. **Passive braking** instead of plugging.
4. **`R_TRIG` held at 600 mm** — `S` is still unbound.
5. **The 45 s timeout**, above the suggested 10–15 s, forced by the 240 ms-per-line emission
   cost.

**I will not flash RUN-3 until you review this, and I will ask again immediately before the
flash.**
