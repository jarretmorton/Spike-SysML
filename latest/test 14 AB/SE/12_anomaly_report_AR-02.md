# ANOMALY REPORT AR-02 — RUN-2: four findings, three re-plan triggers
**Document:** `12_anomaly_report_AR-02.md` · **Type: REPORT** (static)
**Raised:** after RUN-2 (`run-20260805-210020`) · **Run status:** completed the mission, truncated in the dump

---

## 0. Summary

RUN-2's corrections worked: the map assertion passed, the heading-gated direction probe
read **−0.93°** (a clean translation, against RUN-1's −23°), and the **ranger trigger fired
(`reason 1`)**. AR-01 is closed.

The run then exposed four further problems. Three of them are the re-plan triggers written
down in Calibration Plan v1 §2.4 — they fired as specified, which is the plan working, not
the plan failing. The fourth is new.

| # | finding | branch | status |
|---|---|---|---|
| **A** | Forward ranger A is **faulty**: erratic, non-monotonic, 15% dropouts | physically impossible | effector fails |
| **B** | Trigger fired at **481 mm against a 600 mm threshold** — a 119 mm undershoot | model-contradicting | explained by A |
| **C** | Heading **−12.58°** at trigger — SYS-6 limit is ±5° | re-plan trigger | fails |
| **D** | Stop-distance channels disagree **three ways**: +38.3 / +8 / −20.4 mm | re-plan trigger | S unbound |
| **E** | Telemetry truncated; **each `stdout` write blocks ~240 ms** | new | budget defect |

**No contact with the wall.** The rover finished at a close pose, ranger B reading 85.9 mm.

---

## 1. Finding A — forward ranger A is faulty

Ranger A's approach trace, closing on a flat wall:

```
1027 1027 1031 1021 1014 1006  993  982  962  965  954 1046 1015 1008 1012  970  980
2000  929 2000  888 2000 2000 2000 2000  719  702  675  659  635  619  604
```

- **Non-monotonic while closing**: 954 → **1046** is a +92 mm *increase* over 41 ms while the
  rover is demonstrably approaching. Physically impossible.
- **Dropouts**: 2000 mm (no target) on **6 of 41 samples — 15%** — against a flat wall at
  under 1 m.
- **Discontinuity**: 2000 → 719 in one sample.

Ranger B over the same window, by contrast:

```
906 908 906 903 888 881 874 859 847 830 819 802 788 768 756 736
```

Smooth, monotonic, and consistent with a constant cruise of **395 mm/s**.

**FUN-13 is now dispositioned, exactly as Calibration Plan v2 §2.5 planned and at no extra
cost: B tracks the wall, A does not.** The 107–117 mm pair split was never a mounting
constant to be absorbed into `b`; it is one good channel and one bad one.

### Probable mechanism — ultrasonic crosstalk

Two ultrasonic rangers face the same direction and are polled continuously by the Pybricks
runtime whether or not the program reads them. Mutual interference produces exactly this
signature: sporadic no-target returns and occasional long readings when one sensor hears
the other's ping. Crosstalk was catalogued as a risk in the channel catalog; it now has
evidence.

This is a **hypothesis, not a conclusion.** The alternative — A is simply defective or
mis-aimed — predicts the same trace. Both are dispositioned the same way (§5), so the plan
does not depend on which is true, and RUN-3 distinguishes them for free: if A is not
constructed and B's dropouts vanish, it was crosstalk.

---

## 2. Finding B — the 119 mm trigger undershoot, explained by A

`d_trigger` = 481.0 against `R_TRIG` = 600. The trigger is supposed to fire on the *first*
loop where the estimate crosses, so the expected undershoot is one loop of travel — about
**4 mm** at 395 mm/s and a 10.1 ms loop. 119 mm is 30× that.

The fusion rule is `min(A, B)` over *plausible* readings, and A ≈ B + 117 mm. So:

1. B goes momentarily invalid → the only plausible reading is A → `last_raw` jumps up to
   A's value, ~117 mm above B's.
2. While B is out, the estimate tracks A, which is still above 600 — **no trigger**.
3. B returns → `min` drops ~119 mm in a single loop, straight through the threshold →
   trigger fires at 481.

The arithmetic matches: at the trigger A read 604, and 604 − 117 ≈ 487 ≈ the observed 481.

**This is not a second defect — it is Finding A propagating through a fusion rule that
assumed both inputs were valid observers of the same target.** `min()` fusion fails safe
against a channel reading *too short*; it does not protect against a good channel dropping
out and a bad one taking over. Removing A removes this failure mode entirely.

---

## 3. Finding C — SYS-6 fails; the rover does not drive straight

| point | heading |
|---|---:|
| at trigger | **−12.58°** |
| at rest after the stop | **−16.80°** |
| after the creep | −14.62° |

Against a **±5° limit**. The in-loop gross-yaw guard (15°) did not trip — correctly, it is
sized for gross failure — but SYS-6 fails on the merits.

### Mechanism, and why it is a *speed-command* problem

Both motors were commanded at `SPEED_CMD` = 2000 deg/s. The controller ceiling is 1000
deg/s, and the observed cruise is ≈ 820 deg/s (395 mm/s ÷ 0.482 mm/deg). **The motors are
torque-saturated well below the commanded speed**, so the speed controller has no headroom
and each motor simply runs at whatever its own load allows.

Yaw rate ≈ 10°/s. For a differential drive, `ψ̇ = (v_R − v_L)/W_t`; at `W_t` ≈ 120 mm this is
a wheel-speed mismatch of ≈ 21 mm/s, i.e. **≈5% between the two motors** — right at CMP-3's
limit. The rover curves because both motors are saturated and one is slightly stronger.

**The consequence is a saturation trap: while both motors are commanded above their
ceiling, no heading correction has any authority.** Subtracting from a command of 2000 still
clamps to the ceiling. Heading control is impossible until the command sits *below* the
weaker motor's sustained speed.

### Cost to clearance

At 12.6° yaw the leading corner is roughly `c_yaw · θ` ≈ 16 mm closer to the wall than the
along-axis reading implies — and it varies run to run, so it enters `σ_g` rather than `b`.
A geometric cross-check supports this: the A−B split moves from −117.3 mm at θ ≈ 0 to
−153.3 mm at θ = −16.8°, implying a lateral ranger separation of ≈124 mm
(`Δoffset = L·sin θ`). Predicted split at θ = −14.6° is −148.6 mm against −137.5 mm
observed. Order-of-magnitude agreement only, and it leans on A, so it is recorded as
supporting inference, not evidence.

---

## 4. Finding D — three channels, three different stop distances

| channel | stop distance | note |
|---|---:|---|
| ranger B (`d_T − r_rest_b`) | **+38.3 mm** | `d_T` is the suspect extrapolated value from §2 |
| ranger A (`604 → 596` across the stop) | **+8 mm** | A is the faulty channel, though stable in this window |
| odometry (`925 → 889.5 deg`) | **−20.4 mm** | wheels rotated *backwards* 35.5 deg |

A three-way disagreement spanning 59 mm. The source-of-truth rule is explicit that this is
**a discrepancy to diagnose, not to arbitrate**, and I am not going to pick a favourite.

What can be said: odometry going backwards while both rangers report forward motion is the
signature of **gross wheel slip under plugging** — full reverse duty locks or reverses the
wheels while the chassis slides forward. That is the re-plan trigger from Calibration Plan
v1 §2.4 (threshold 15 mm; observed 59 mm). Note also that A's +8 mm implies deceleration of
~10,500 mm/s² from 395 mm/s, which is above any plausible tyre-floor traction limit —
another impossible value.

**Verdict: `S` remains UNBOUND.** It cannot be bound from this run, because the primary
channel's trigger value is contaminated (§2), the secondary channel is faulty (§1), and the
tertiary channel is corrupted by slip. This is the correct outcome — binding `S` from any
one of these would ship a systematic error straight into the scored quantity.

---

## 5. Finding E — telemetry budget defect

Timestamps between consecutive `emit()` calls while the rover is stationary:

```
R0_a 3317 → R0_a_spread 3616 → R0_b_spread 3736 → R0_pair_offset 3976 → travel_limit 4696
```

**Each `stdout` write blocks for roughly 240 ms.** The whole-run throughput is ≈5 lines/s.
I had budgeted ~168 lines on an assumption of ~1 KB/s; the true cost is about **20× worse**,
and the run hit its 30 s timeout mid-dump, losing the `odo_deg`, `heading` and `accel_fwd`
traces and most of `d_b`.

Those losses are the reason Findings B and D cannot be closed from this run rather than
merely diagnosed. **Telemetry volume is a first-class design constraint, not an
afterthought**, and the RUN-2 design violated it by roughly 4×.

The truncation-tolerant emission order did its job: every scalar arrived, and only the
least-critical traces were lost. That design decision is what makes this run recoverable.

---

## 6. What RUN-2 nonetheless bound

| parameter | value | evidence | tier |
|---|---:|---|---|
| `t_loop_s` | 10.09 ms | 124 hot-path samples over 1251 ms (confirms RUN-1's 10.18 ms) | T2 |
| `k_mm_per_deg` | ≈ 0.482 | creep phase: 356.8 mm of range change over 740.5 motor deg, at low speed where slip is negligible | T2 provisional |
| cruise speed | ≈ 395 mm/s | ranger B, 847→736 mm over 281 ms | T2 |
| saturated ω | ≈ 820 deg/s | 395 ÷ 0.482 — **below** the 1000 deg/s controller limit | T2 |
| `sigma_n_mm` (ranger B) | ≈ 3.4 mm | 12-sample static dwell, spread 11–12 mm | T2 |
| motor asymmetry | ≈ 5% | inferred from yaw rate and track width | T1 |

**Requirement verdicts:** CMP-11 **PASS** (10.09 ms) · CMP-12, CMP-13 **DROP** confirmed
again (rear ranger 2000 throughout; reflectance 31/30/28) · FUN-13 **FAIL** and now
dispositioned · SYS-6 **FAIL** · CMP-6 (ranger A) **FAIL**.

**M1 was again NOT spent.** The rover is at a close pose (B = 85.9 mm) but yawed −14.6°.
Since the recommended fix changes the operating yaw to ≈0°, an offset measured at −14.6°
would not transfer to the operating point, and `b` is precisely the parameter that must not
carry a systematic bias. **Two runs consumed, zero measurements consumed.**

---

## 7. RECOMMENDATION

**RETEST** with a re-architected RUN-3. Four changes, each tied to a finding:

| # | change | closes |
|---|---|---|
| **1** | **Drop ranger A entirely — do not construct it.** B alone is the primary channel. Not constructing it also stops the Pybricks runtime polling it, which tests the crosstalk hypothesis for free: if B's dropouts vanish, it was crosstalk | A, B |
| **2** | **Command below saturation and add heading hold.** `SPEED_CMD` ≈ 750 deg/s so both motors regulate, with proportional heading correction `cmd = V ∓ g·θ`, `g` = 7 deg/s per degree — *derived*, not guessed, from a target closed-loop heading time constant of 0.3 s: `τ = 1/(2·g·k·57.3/W_t)` | C |
| **3** | **Replace plugging with passive `brake()`.** Slip of 59 mm makes `S` unrepeatable and destroys the odometric cross-check and backstop | D |
| **4** | **Cut telemetry to ≤40 lines** and raise the run timeout to 45 s | E |

### The one decision I am escalating rather than making

Change 2 lowers the commanded speed from saturated (~820 deg/s, ~395 mm/s) to regulated
(~750 deg/s, ~360 mm/s) — about **9%**. The task says *run at maximum speed, do not slow
down for safety margin*, so this deserves your explicit call rather than my quiet
reinterpretation.

**My recommendation is to accept it**, for three reasons:

1. It is not a safety margin. It is the speed at which the rover can drive *straight*.
   Above it, the extra 9% buys a 12.6° curve that costs ~16 mm of corner clearance and adds
   run-to-run variance to the scored gap.
2. Heading control is impossible above it — the saturation trap in §3 is structural, not a
   tuning problem.
3. The scored objective is the **gap**, not the speed. Speed enters only as constraint
   SYS-4, and I propose re-deriving SYS-4 as *the maximum speed at which both drive motors
   remain in closed-loop regulation* — which is genuinely the rover's maximum
   straight-line-capable speed.

**If you would rather hold full command and accept the yaw**, that is a legitimate call and
I will re-derive the margin with a much larger `σ` for the yaw term instead; say so and I
will re-plan that way. What I will not do is quietly change the meaning of a task
constraint.

### Proposed plan (costed only if approved)

1. **RUN-3** — re-architected calibration run, as Calibration Plan v3.
2. **M1** immediately after, *if* it reaches a close pose at ≈0° yaw.
3. No further measurement requested. Crosstalk, `S`, `k` and symmetry are all settled from
   RUN-3's own channels.

### Residual risk

`R_TRIG` stays at 600 mm. `S` is still unbound and the plausible envelope has if anything
widened, so tightening the trigger now would spend margin against an unknown.
