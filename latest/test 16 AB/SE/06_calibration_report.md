# CALIBRATION REPORT — WallStop

**Document** CR-WALLSTOP-001 · **Type: REPORT (static — not edited once written)** · **Gate: B** · Evidence run: `run-20260807-111521` (C1), 1 program run, 0 outside-input actions

Companion documents: AR-001 (anomalies), Calibration Plan v1.1, Verification Plan v1.0, RS-WALLSTOP-001 rev B.

---

## 1. What C1 produced

One flash-and-run, 59.3 s, 1025 telemetry events. Every planned phase executed: port scan, static classification, polarity discovery, two full-speed stops, reverse, and a creep sweep terminating in stall-detected wall contact. No aborts, no failsafe trips — both stops fired on `reason = 1` (the modelled trigger).

**Port map and configuration (TBD-13, TBD-14).**

| Port | Device | Role |
|---|---|---|
| A | UltrasonicSensor | **forward ranger A — sole trigger channel** |
| B | UltrasonicSensor | forward ranger B — monitor only (disqualified, AR-001 A-2) |
| C | Motor | drive left, forward = `−1` |
| D | Motor | drive right, forward = `+1` |
| E | UltrasonicSensor | rear ranger — **dropped by traceability** |
| F | ColorSensor | **dropped by traceability** (no requirement traces to it) |

Rated max speed 1000 deg/s; acceleration limit set explicitly to 4000 deg/s² for run-to-run repeatability; torque limit 199.

Polarity was resolved exactly as designed: the `(+,+)` probe produced a 49.5° heading change with no translation → mirrored drivetrain; the `(+,−)` probe translated *backwards* (+39 mm) → forward is `(−,+)`. A single-motor probe gave +23.0° of yaw, fixing the steering-trim sign at `+1`.

---

## 2. TBD register — closed

Tiers: **T0** none · **T1** physics-bounded · **T2** datasheet · **T3** onboard multi-point · **T4** external ground truth.

| TBD | Quantity | **Bound value** | Producing test | Evidence basis | Tier |
|---|---|---|---|---|---|
| TBD-01 | Ranger A offset `c_A` | **10.0 mm** (σ 4.6) | C1 creep sweep | 26-point regression referenced to the contact point; slope-choice spread ±2.5 mm; +3.5 mm allowance for contact-detection lag | T3 |
| TBD-02 | Ranger B offset | **VOID** | C1 creep + 7 static epochs | Implies a face 100 mm ahead of the foremost point — impossible. Channel disqualified (AR-001 A-2) | — |
| TBD-03 | Travel per motor degree `k` | **0.482 mm/deg** | C1 rolling segments | ranger/odometry ratio 1.0288 and 1.0230 over 186–202 mm | T3 |
| TBD-04 | Achievable ground speed | **480.9 mm/s** | C1 steady segments | two segments, 1012 and 983 deg/s at the wheel | T3 |
| TBD-05 | Brake deceleration `a` | **UNBOUND** | — | **not identifiable** at one operating point (AR-001 A-3). Left uncalibrated, not zeroed | — |
| TBD-06 | Lumped response `t_eff` | **0.09661 s** (σ 0.00834) | C1 ×2 stops | Δu = 50.0 and 43.0 mm at 487.8 and 474.0 mm/s. n=2, **1 df — weakly determined** | T3 |
| TBD-07 | Ranger A noise σ | **1.47 mm** | C1 rest window | 11 samples, spread 4 mm, at 602 mm | T3 |
| TBD-08 | Loop period | **0.0105 s** | C1 both cores | min 10 / max 11 ms over 175 cycles | T3 |
| TBD-09 | Ranger A clamp | **40 mm hard clamp** | C1 creep near field | 7 consecutive identical readings while odometry advanced 23.7 mm | T3 |
| TBD-10 | Ranger refresh | **≤ 10 ms** | C1 rest window | values change sample-to-sample at 10 ms | T3 |
| TBD-11 | Heading deviation | **4.91°** worst | C1 both cores | peak excursion ≈5.0° mid-approach; **−1.40°/−0.48° at trigger**, −4.91°/−1.51° at rest | T3 |
| TBD-12 | Target gap `G` | **37.0 mm** | analysis | set by SYS-6 (clamp), not SYS-1 — see §4 | A |
| TBD-13 | Port map | §1 | C1 port scan | all six ports probed | T3 |
| TBD-14 | Polarity, yaw sign | `(−1,+1)`, `+1` | C1 probes | 3 probes, each undone | T3 |
| TBD-15 | Rear ranger validity | in range (548 mm) but **role void** | C1 static | never exercised dynamically; role filled by odometry | — |
| TBD-16 | Run-to-run σ | **4.01 mm** | C1 ×2 stops | from the Δu spread; n=2 | T3 |
| TBD-17 | **Gap at the operating point** | **OPEN** | **C2 + operator** | the single costed measurement | **T4 pending** |
| TBD-18 | Ranger scale α | **not separated — by design** | — | model carried in ranger-A units, so α cancels exactly in the trigger comparison | n/a |
| TBD-19 | Half-width | 65 mm | inspection | enters only the yaw-corner term | T1 |

**Source-of-truth discipline applied.** TBD-01 is a T3 multi-point value. The single close-range sample that read `40 mm at contact` was **not** allowed to overwrite it — that sample is the clamp artifact of AR-001 A-1, and a lower-tier reading never re-fits a higher-tier constant. Had it been accepted, `c_A` would have been 40 mm and every stop would have landed 30 mm closer than predicted.

---

## 3. CMP unit verification (tenet C1 — components before integration)

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| **CMP-1** Ranger A offset known to σ_c | T | 26-point creep regression; σ_c = 4.6 mm ≤ 6 mm allocation | **PASS** |
| **CMP-2** (rev B) Stop shall not depend on ranger B | I | locked source: `d2` appears in zero of the 5 trigger conditions (verified programmatically) | **PASS** |
| **CMP-3** Ranger refresh bounded | T | ≤10 ms, below the 25 ms limit | **PASS** |
| **CMP-4** Clamp region rejected | T + I | clamp measured at 40 mm; gate specified `42 < u < 1900` in the locked source | **PASS** |
| **CMP-5** Rotation-to-travel scale bound | T | k = 0.482 mm/deg from two rolling segments | **PASS** |
| **CMP-6** Max speed achieved | T | 480.9 mm/s at a commanded 1000 deg/s (the rated ceiling) | **PASS** |
| **CMP-7** Stopping lump bound at the operating point | T | Δu = 50.0 / 43.0 mm, two stops; `a_brake` deliberately unbound | **PASS** |
| **CMP-8** Effective latency bounded | T | t_eff = 0.0966 s ≤ 0.15 s | **PASS** |
| **CMP-9** Heading drift ≤ limit | T | 4.91° worst ≤ 5.0° — **marginal, 0.09° of margin** | **PASS (marginal)** |
| **CMP-10** Loop period ≤ limit | T | 10–11 ms ≤ 25 ms | **PASS** |
| **CMP-11** Port/polarity self-check | T + I | C1 scan resolved all six ports; gate implemented in the locked source | **PASS** |
| **CMP-12** Trim reduce-only | I | `cl = VCMD − max(0,red)`, `cr = VCMD − max(0,−red)`; never exceeds VCMD | **PASS** |
| **CMP-13** Rear ranger conditional | — | **DELETED** — effector dropped by traceability (spec rev B) | **N/A** |
| **CMP-14** IMU at-rest indicator | T | 3-axis accel captured at static / rest / contact; rest speeds 4 and 0 mm/s | **PASS** |

**CMP-9 is flagged.** 4.91° against a 5.0° limit is not margin, it is luck. The excursion is not a drift — the trace shows the trim actively pulling heading back (0 → −5.0° → −1.4° by the trigger). The yaw *grows during braking*, after the trim has stopped acting, because one wheel locks before the other. It is carried in the budget as `sigma_yaw = 2.5 mm` and it is the third-largest term.

---

## 4. The finding that sets the achievable performance

The GATE A plan assumed the ranger's bounded range would be covered by an odometry hand-off. **That hand-off does not exist.** Odometry captures only 37–39 % of the braking travel because the wheels skid, and the clamp region is entered precisely during that skid. So:

- **SYS-1** (no contact) permits a target gap of **21.0 mm** (3σ).
- **SYS-6** (a valid onboard estimate) requires the rest reading to clear the clamp: `u_rest ≥ 44` ⇒ `G ≥ 34 mm`, and with 2σ of ranger noise, **G ≥ 37 mm**.

**SYS-6 binds, by 16 mm.** The rover is not limited by its ability to stop — it is limited by its inability to *see* how close it stopped. `G = 37.0 mm` is adopted.

The alternative — flying below the clamp and reporting a model-predicted gap — was rejected: the close-out requires a frozen onboard estimate that is then checked against ground truth, and a knowingly-saturated estimate would make that check meaningless.

---

## 5. Margin budget (tenet A6)

| Contributor | 1σ (mm) | Resolved by |
|---|---|---|
| Ranger A offset `c_A` | 4.60 | C1 creep (T3) — **anchored to T4 at C2** |
| Run-to-run lump Δu | 4.01 | C1 ×2 stops (n=2, weak) |
| Yaw corner advance | 2.50 | C1 heading traces |
| Ranger A noise | 1.47 | C1 rest window |
| Trigger phase `v·dt/√12` | 1.46 | C1 loop timing |
| Slip / model residual | 1.00 | C1 ratio analysis |
| **RSS σ_gap** | **6.98** | |
| **Contact margin = 3σ** | **20.9** | SYS-1 floor |

The two largest terms are both weakly determined — `c_A` at T3 and `Δu` on 1 degree of freedom. Both are exactly what the C2 ground-truth anchor addresses.

---

## 6. Requirements affected — specification revised to rev B

C1 falsified two rev-A requirements. Per REQUIREMENTS METHOD the specification governs, so it is **revised**, not quietly worked around:

| Req | rev A | rev B | Why |
|---|---|---|---|
| CMP-2 | "Ranger B's longitudinal offset shall be known to within σ_c" | *Unwanted:* "The stop decision shall not depend on ranger B" | Its offset implies an impossible geometry; it cannot be known because it is not measuring what was assumed |
| CMP-13 | "Where the rear ranger is in range, it shall serve as an independent travelled-distance channel" | **DELETED** | Never exercised dynamically; the role is filled better by odometry. Effector dropped by traceability — closed on evidence, not assumed |
| SYS-8 | fallback = second ranger or odometry | fallback = **odometry only** | Only one trusted ranger remains |

SYS-8's fallback was **observed working in flight**: at the core-1 trigger instant ranger B returned 2000, the validity gate rejected it, and the decision proceeded on ranger A alone. That is in-run evidence, not an inspection claim.

---

## 7. Budget consumed

| | Planned at GATE A | Actual |
|---|---|---|
| Characterisation runs | 1 (C1) | **1** |
| Outside-input actions | 0 | **0** |

Every one of the five anomalies was dispositioned from data C1 had already captured. No re-run was required.
