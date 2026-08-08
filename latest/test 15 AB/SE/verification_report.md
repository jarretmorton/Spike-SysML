# Verification Report — Wall-Approach Rover

**Type:** REPORT (static; never edited once written) · **Gate:** C
**Programs consumed: 9** · **Operator measurements: 4** (+1 diagnostic question) · **Contacts: 0**

This is the single place every requirement is closed. No requirement is asserted without
evidence.

---

## 1. Result

**VER-3 confirmed the frozen prediction of Verification Plan v3.**

| Quantity | Predicted | Band | Actual |
|---|---|---|---|
| **Final gap (operator)** | **29.5 mm** | 9 … 51 | **32 mm** |
| Rest angle | 1940° | 1930–1950 | 1941° |
| Post-brake rotation | 29° | 20–40 | 30° |
| Approach heading | ≤2.5° | ≤5° | −2.26 … +1.33° |
| Heading at rest | ≤12° | ≤15° | −4.55° |
| Loop period | 10.0 ms | 9–12 | 10.0 ms |
| Braked by | primary | — | odometry, fault 0 |

The position model closed against **three independent operator anchors**:

| Run | rest angle | predicted | measured | residual |
|---|---|---|---|---|
| CAL-3 | 1416° | 292.0 mm | 290.5 mm | −1.5 mm |
| VER-2 | 1602° | 199.0 mm | 199.0 mm | +0.0 mm |
| VER-3 | 1941° | 29.5 mm | 32.0 mm | +2.5 mm |

Mean residual +0.33 mm, sample sd 2.02 mm over a 260 mm span. A free least-squares fit gives
D0 = 987.8 mm and k = 0.4924 mm/deg, which differs from the committed 1000.0 / 0.5000 by at most
2.5 mm anywhere across the span — so the committed constants are not over-fitted to one point.

---

## 2. The falsify → diagnose → re-derive → re-predict trail

Three architectures were tried. Two were killed by evidence.

| # | Architecture | Killed by | Diagnosis |
|---|---|---|---|
| 1 | Trigger on ranger B, constant reading→true offset | **OP-MEAS-2**: predicted 91 mm, measured 102 mm | The offset is not constant (−24 at A=236, −13 at A=115). Model re-derived as v2 with a two-anchor interpolation. |
| 2 | Trigger on ranger A through a two-anchor map, fused with odometry | **OP-MEAS-3**: predicted 19.5–28 mm, measured 199 mm | Ranger A's absolute map is unstable **across runs** (+24, +13, −155 mm). The fused gate accepted 37/37 readings because **a rate-consistency gate is structurally blind to a constant offset**. |
| 3 | **Odometry dead-reckoning from the fixed start line** | — | Confirmed at three anchors. Flown. |

Two program-level defects also cost runs and are recorded in AR-001, AR-002 and AR-004: a
discovery nudge that spun the rover 35.9° and blinded the rangers; six telemetry writes between
trigger and brake that added 13.5 mm of untracked travel; and a closing check with no debounce
that a single ranger outlier could trip.

**Three of these five failures share one shape:** I built a check that could not observe the
failure it existed to catch. That is the durable lesson of this programme, and it is why the
final design puts the conservative, boring channel in the control path and the clever one on the
sidelines.

**What prevented contact, every time, was cross-sourcing.** In VER-2 the odometry travel budget
braked the rover at an estimated 91 mm when it was truly at 199 mm. The confident channel was
wrong; the conservative one overruled it. That is the Calibration Plan's source-of-truth rule
doing exactly the job it was written for.

---

## 3. Requirement closure

Method · Evidence · Verdict, for all 40 requirements. Component requirements are pulled forward
from the Calibration Report and re-verified against the flown design.

| Req | Method | Evidence | Verdict |
|---|---|---|---|
| **STK-1** | test | VER-3 stopped 32 mm clear (OP-MEAS-4). Zero contacts across 9 programs. | **PASS** |
| **STK-2** | test | OBJECTIVE. Predicted 29.5 mm, operator-measured 32 mm at the operating point, on the configuration that flies unchanged. Graded closure. | **CLOSED** |
| **STK-3** | inspection | Both motors commanded at 1000 deg/s, the device ceiling. Heading hold trims only the leading wheel, so the faster wheel is always at maximum. | **PASS** |
| **STK-4** | test | VER-3 approach heading held -2.26 deg .. +1.33 deg. | **PASS** |
| **STK-5** | test | Per-run onboard estimate emitted (GAP_EST); validated at +2.5 mm against OP-MEAS-4. | **PASS** |
| **SYS-1** | test | Monotonic braking approach; minimum clearance equals final clearance. 32 mm. | **PASS** |
| **SYS-2** | test | Wheels stopped 30 deg after the brake command; settle well under the limit. | **PASS** |
| **SYS-3** | analysis | Cruise 500 mm/s stoppable within the approach budget: 970 mm of travel available, 15 mm used after braking. | **PASS** |
| **SYS-4** | analysis | Predicted gap 30.0 mm vs 3-sigma margin 20.9 mm at the frozen sigma of 7.0 mm. | **PASS** |
| **SYS-5** | inspection | As STK-3. | **PASS** |
| **SYS-6** | test | **SPLIT and RE-ALLOCATED at Gate B** (Verification Plan v3 S5). SYS-6a approach <=5 deg: -2.26..+1.33, PASS. SYS-6b at rest <=15 deg: -4.55, PASS. The original 5-deg at-rest limit came from a corner-lead analysis that three ground-truth anchors do not support. | **PASS (re-allocated)** |
| **SYS-7** | test | Telemetry carries start state, brake angle, rest angle, per-run gap estimate, heading extremes and loop statistics. | **PASS** |
| **SYS-8** | test | Onboard estimate 29.5 mm vs operator ground truth 32 mm = +2.5 mm error, tolerance 10 mm, taken at the operating point. | **PASS** |
| **FUN-1** | inspection | Superseded. Clearance is no longer sensed; position is reckoned from wheel angle each 10 ms loop. | **VOID — superseded** |
| **FUN-2** | test | Realised as the odometry brake condition: angle >= 1911 deg, achieved exactly. | **PASS (re-realised)** |
| **FUN-3** | analysis | Realised as the brake-angle derivation (1000 - G)/0.500 - 29, validated by three anchors with residuals -1.5/0.0/+2.5 mm. | **PASS (re-realised)** |
| **FUN-4a** | inspection | Superseded. No trigger decision is taken on a range reading. | **VOID — superseded** |
| **FUN-4b** | inspection | Superseded, same reason. | **VOID — superseded** |
| **FUN-5** | inspection | Inverted: odometry is now primary and ranging is the fail-safe (near-wall guard at 10 mm, closure check at 800 deg). Neither fired in VER-3. | **PASS (inverted)** |
| **FUN-6** | test | Equal commanded magnitude with bounded trim; approach heading within 2.3 deg. | **PASS** |
| **FUN-7** | inspection | Both brake commands issued in adjacent statements, before any telemetry write. | **PASS** |
| **FUN-8** | test | Heading sampled every 10 ms loop; extremes emitted. | **PASS** |
| **FUN-9** | inspection | Brake angle, rest angle and gap estimate all emitted after motion ceases. | **PASS** |
| **FUN-10** | inspection | Both rangers, both encoders and heading logged every loop, off the hot path. | **PASS** |
| **FUN-11** | test | **FAILED AS DESIGNED, then removed.** The fused hand-off estimator accepted 37 of 37 readings while ranger A was 155 mm in error: a rate-consistency gate cannot see a constant offset (AR-005). The requirement was retired with the ranging architecture. | **FAIL — withdrawn** |
| **CMP-1** | test | Ranger A: linear within a run, but absolute offset unstable across runs (+24, +13, -155 mm against three anchors). | **FAIL — not load-bearing** |
| **CMP-2** | test | Ranger B: usable above ~260 mm, spread 158 mm at 196 mm; absolute reading varied 877-1038 at the same start position. | **FAIL — not load-bearing** |
| **CMP-3** | test | Superseded with the ranging trigger. | **VOID — superseded** |
| **CMP-4** | test | Not separately bound; absorbed into the composite and then made irrelevant by the architecture change. | **VOID — superseded** |
| **CMP-5** | test | CAL-3 on-hub: 24 ms refresh interval, limit 80 ms. | **PASS** |
| **CMP-6** | test | CAL-3: left motor 986-1004 dps against 1000 commanded. | **PASS** |
| **CMP-7** | test | CAL-3: right motor as above. | **PASS** |
| **CMP-8** | test | Post-brake rotation 28-30 deg across CAL-3, VER-2, VER-3. | **PASS** |
| **CMP-9** | test | As CMP-8; per-motor difference within 5 deg. | **PASS** |
| **CMP-10** | test | **The load-bearing component requirement of the flown design.** Odometry against three operator anchors: residuals -1.5, 0.0, +2.5 mm; sample sd 2.02 mm over a 260 mm span. | **PASS** |
| **CMP-11** | test | IMU heading drift under 0.05 deg over run duration at rest (CAL-3, CAL-4 static bursts). | **PASS** |
| **CMP-12** | test | Optional. Logged but never needed once odometry and ground truth agreed. | **NOT EXERCISED** |
| **CMP-13** | test | Optional. The rear reference left useful range; the Where-precondition is false. | **VOID** |
| **CMP-14** | test | Loop period min 10, max 11, mean 10.0 ms in every scored run. | **PASS** |
| **CMP-15** | test | k = 0.500 mm/deg at cruise; free fit over three anchors gives 0.4924, within 2.5 mm across the span. | **PASS** |
**Tally: 29 PASS (including re-allocated, re-realised and inverted realisations), 1 CLOSED
(objective), 6 VOID by supersession, 3 FAIL, 1 not exercised.**

### 3.1 The failures, stated plainly

- **FUN-11** (bounded-range hand-off estimator) — **failed as designed and was withdrawn.** It
  accepted 37 of 37 readings while ranger A was 155 mm in error. The requirement was retired with
  the architecture it belonged to.
- **CMP-1, CMP-2** (per-ranger residual bounds) — **both fail.** Ranger A's cross-run offset spans
  179 mm; ranger B's absolute reading varied 877–1038 at the same physical position. Neither is
  load-bearing in the flown design, which is why the top-level needs still close.
- The 6 VOID requirements are the ranging-trigger branch of the original decomposition. They are
  not quietly deleted: they are recorded as superseded, with the architecture change that
  superseded them.

### 3.2 Objective closure (STK-2)

Closed **here and only here**, on evidence that the predicted final gap was validated against
operator ground truth **at the operating point**: predicted 29.5 mm, measured **32 mm**, on the
configuration that flies unchanged. Onboard estimator error +2.5 mm against a 10 mm tolerance
(SYS-8).

---

## 4. Residual risks carried into operation

1. **n = 3.** Sample sd is 2.02 mm but three points give a weak estimate of spread. The committed
   σ is 7.0 mm, deliberately inflated. The five operation runs are the real repeatability sample.
2. **Start-line placement repeatability is inferred, never measured.** It is bounded only by the
   three-anchor residuals, which conflate it with scale and braking variation.
3. **Ranging is unreliable and stays that way.** It is out of the control path; only the
   near-wall guard (10 mm) and the closure check could stop a run, and neither fired in VER-3.
4. **No re-approach.** The program brakes once and does not creep closer, per interpretation I3.

## 5. Lock

Verification Plan v3 §4 states: *"If confirmed, this configuration is LOCKED unchanged for the
five scored runs. No tightening — the operating point must be the point that was verified."*

It is confirmed, so **it is locked at brake angle 1911°.**

I want to record the cost of honouring that. With n = 3 and sd = 2.02 mm, a 3σ margin would be
6.1 mm and a target near 8–10 mm would now look defensible — roughly 20 mm of objective left on
the table. Taking it would mean flying a configuration that was never verified, on a σ
re-estimated from the very run being used to justify the change. The programme's whole claim is
that the argument came before the run. **The lesson is that the verification target should have
been set closer to begin with**, since this process makes the verified point the flight point.
That is a planning error to carry forward, not a licence to edit a frozen plan after seeing the
answer.

---

## 6. Authorisation

All hard constraints are satisfied with evidence. The objective is closed at the operating point.
The configuration is locked.

**Cleared for the five scored operation runs**, subject to operator review of this report.
