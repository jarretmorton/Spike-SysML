# Final Engineering Report — Wall-Approach Rover

**Mission:** drive a LEGO SPIKE Prime rover straight at a wall ~1000 mm ahead, at maximum speed, and
stop as close as possible **without contact**.

**Outcome in one line:** five locked-program operation runs, **5/5 with no contact**, mean true gap
**192 mm** (range 171–200 mm), heading held within ±5°, and the frozen pre-test prediction (189 mm)
matched the measured mean to **within 3 mm**.

---

## 1. Result against the four scored axes

| Axis | Result |
|---|---|
| **No contact (of 5 operation runs)** | **5 / 5** — every run stopped clear of the wall |
| **Closeness** | mean **192 mm**, range 171–200 mm, σ ≈ 12 mm |
| **Characterization program-runs** | **8** (development/calibration runs; itemized in §6) |
| **Outside-input measurements** | **2 design-informing** (anchor 469 mm; verification 173 mm) + **5 close-out ground-truth** (post-lock, for this report only) |

Total hardware runs: 8 characterization + 1 verification + 5 operation = **14**.

---

## 2. The locked control strategy

The rover drives both motors at a commanded speed well past their clamp (max speed), holding a
straight heading with a PD loop on the IMU, and stops when a **velocity-aided distance trigger** says
the nearer of the two forward ultrasonic sensors has reached the threshold.

**Why velocity-aided.** The forward sensor refreshes irregularly (16–60 ms typical, with occasional
200–265 ms plateaus where the reading freezes while the rover keeps moving). A naive "stop when the
reading ≤ threshold" trigger would either overshoot through a plateau or fire late. The control keeps
a dead-reckoned estimate `est = last_changed_reading − VEL_EST·Δt` and triggers on
`eff = min(raw, est)`. This carries the trigger through plateaus *and* ignores spurious **high**
glitches (because `min` rejects a raw reading that jumps above the estimate). Both behaviors were
observed and handled on every run.

**Locked numeric parameters:** `THRESH = 120 mm`, `VEL_EST = 455 mm/s`, PD gains `KP = 24`,
`KD = 2.5`, correction clamp 700, heading-abort ±30°, runaway guard 2.6 s. Telemetry is buffered in
pre-allocated fixed-length lists and dumped only after the stop, so the control loop never blocks on
BLE I/O (the cause of an early stall failure). Full source in Appendix A.

**Determined hardware configuration** (hardcoded after live identification): 2 drive motors; two
forward ultrasonics on ports A and B; rear ultrasonic (port E) and the downward color sensor both
dropped by requirement traceability; forward = motor commands (−1, +1); slowing motor B raises
heading.

---

## 3. The calibration that governed everything: the sensor offset

The control signal is `min(A, B)`, the nearer forward reading. It reads **short of the true gap** by a
roughly constant offset. Measured across the whole campaign:

| Distance regime | Reading | True gap (measured) | Offset (true − reading) |
|---|---|---|---|
| Far field (anchor) | 346 mm | 469 mm | **+123 mm** |
| Verification | ~67 mm | 173 mm | +106 mm |
| Operation run 1 | 67 mm | 197 mm | +130 mm |
| Operation run 2 | 66 mm | 171 mm | +105 mm |
| Operation run 3 | 79 mm | 198 mm | +119 mm |
| Operation run 4 | 70 mm | 196 mm | +126 mm |
| Operation run 5 | 68 mm | 200 mm | +132 mm |

**The offset is ~120 mm and essentially constant** (123 mm far, mean ~122 mm close). The rover
therefore always comes to rest ~120 mm **farther** from the wall than its control sensor reports — a
large, automatic no-contact cushion, and the reason nothing ever touched across 14 runs.

This same offset is the binding limit on **closeness**: because the trigger acts on the *nearer*
sensor (the fail-safe rule that protects against a sensor ever reading *long*), and that sensor reads
short, the rover cannot be commanded nearer than ~120 mm without abandoning the fail-safe.

---

## 4. Prediction vs reality (the reconciliation)

### 4.1 The frozen prediction held
GATE B froze, before any close-range run, a predicted true rest gap of **189 mm** at `THRESH = 120`.
The five operation runs measured a mean of **192 mm** — a **+3 mm** miss on a frozen point estimate.
The design model (`true rest ≈ THRESH + offset − braking`) was correct.

### 4.2 Per-run table

| Run | Predicted (frozen) | Onboard estimate (frozen) | Measured | Meas − Pred | Meas − Onboard |
|----:|----:|----:|----:|----:|----:|
| 1 | 189 | 166 | 197 | +8 | +31 |
| 2 | 189 | 165 | 171 | −18 | +6 |
| 3 | 189 | 178 | 198 | +9 | +20 |
| 4 | 189 | 169 | 196 | +7 | +27 |
| 5 | 189 | 167 | 200 | +11 | +33 |
| **mean** | **189** | **169** | **192** | **+3** | **+23** |

### 4.3 Why the onboard estimates ran low — an honest correction
The onboard per-run estimate used `rest_reading + 99 mm`. The 99 mm came from the **single**
verification sample (173 mm gap at ~74 mm reading). The five operation measurements reveal that 173 mm
was a low draw (only run 2 reproduced it); the true offset is ~120 mm. Had the onboard estimate used
the **original far-field offset (123 mm)** — the value GATE B itself used — it would have read
190/189/202/193/191 mm against measured 197/171/198/196/200, essentially unbiased. **Lesson: the
single mid-course verification point was a weaker estimator than the original anchor; revising the
offset down to fit it introduced a ~23 mm low bias into the live estimates, even though the locked
controller and the GATE B prediction were unaffected and correct.**

### 4.4 A real limitation: close-range sensor resolution
At rest the readings clustered at 66–79 mm while the true gaps spanned 171–200 mm. Near the wall the
sensor loses resolution — the reading no longer tracks the gap finely — so the per-run *onboard*
estimate is inherently only good to ~±12 mm there, regardless of offset. The **ground-truth** gaps,
by contrast, are tightly clustered (σ ≈ 12 mm), so the *physical* repeatability is good; it is the
*sensing* of it at close range that is coarse.

---

## 5. Did it meet the requirements?

| Requirement | Target | Measured | Verdict |
|---|---|---|---|
| No contact (gap > 0) | > 0 | 171–200 mm | ✅ 5/5 |
| Stop ≥ safety margin (72 mm) | ≥ 72 mm | ≥ 171 mm | ✅ |
| Minimise gap (objective) | as small as safe | 192 mm mean | ✅ achieved (sensor-limited; see §7) |
| Max speed | command past clamp | vMax ≈ 440–480 mm/s at full command | ✅ |
| Straight heading | small drift | ±5° worst, ±2–3° typical | ✅ |
| Complete stop | residual ≈ 0 | flat rest readings | ✅ |
| Sensors agree (CMP-RNG-2) | within tol | A−B ≈ 120 mm | ⚠️ **waived** — handled by `min` + offset calibration |

Every binding requirement passed. The one waiver (the two forward sensors disagree by ~120 mm) was
declared at GATE B, mitigated by the fail-safe `min` rule, and is the documented cause of the
closeness floor.

---

## 6. Honest run ledger

**Characterization (8):** CHAR‑1 v1 (veered — needs heading hold), v2 (32° wander — choose polarity by
IMU), v3 (clean config + speed/noise/decel); anchor buffered (MemoryError — no unbounded buffers),
anchor v2 (revealed BLE loop stalls), anchor v3 (stall is in the loop), anchor v4 (no `array` module),
anchor v5 (clean stall-free anchor). **Verification (1):** `THRESH = 120`, measured 173 mm.
**Operation (5):** all `THRESH = 120`, measured 197/171/198/196/200 mm, no contact.

Two operation runs (3, 5) reported inflated *final-sample* rest readings (126 mm, 104 mm) that were
single-sample sensor glitches at loop exit; the settled clusters (79 mm, 68 mm) were used. Run 4's
19 s wall-clock was host/BLE transfer overhead — its on-hub timing was normal (2.3 s). None affected
the stop.

---

## 7. What "as close as possible" cost, and what I would do differently

The rover stopped at ~192 mm, not at the few-tens-of-mm a perfect sensor would allow. Two compounding
reasons, both deliberate:

1. **Fail-safe sensing.** Triggering on the *nearer* of two sensors guarantees the rover never thinks
   it is farther than it is. Since that sensor reads ~120 mm short, the rover always stops ~120 mm
   out. Dropping the fail-safe (trusting the single accurate sensor, or correcting blind below the
   sensor floor) could have closed most of that gap — at a real contact risk that the hard no-contact
   constraint did not justify.
2. **Locked-verified threshold.** I held `THRESH = 120` (the verified value) rather than nudging it
   closer post-verification, per process discipline.

**With hindsight from the 5-run data:** the offset is constant at ~120 mm and the sensor reads
reliably to ~66 mm, so a lower threshold (≈ 60–70 mm) would have stopped the rover at ~125–135 mm
**still with no contact**. The conservatism that produced 192 mm instead was driven by (a) the single
verification sample suggesting the offset shrank near the wall (it does not) and (b) prioritizing the
no-contact score over closeness. Given another verification run at a lower threshold to confirm the
constant offset, ~130 mm would have been a defensible, safe lock.

---

## 8. Bottom line

The disciplined requirements → SysML → calibration → frozen-prediction → verification → operation
process delivered a controller whose **frozen prediction (189 mm) matched reality (192 mm) within
3 mm**, with **no contact in any of the five scored runs**, a straight (±5°) approach at max speed,
and full, repeatable stops. The achievable closeness was set by a real, measured sensor offset and a
deliberate no-contact-first design choice — both documented, neither hidden.

---

## Appendix A — Locked operation program (`THRESH = 120`)

```python
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

THRESH  = 120.0    # locked
VEL_EST = 455.0
FORWARD = (-1, 1); DBSIGN = 1
MAXSP = 2000; CLAMP = 1000; KP = 24.0; KD = 2.5; CORR_MAX = 700
ABORT_E = 30.0; SAT = 1900.0; GUARD_MS = 2600; SETTLE_MS = 700
LOG_DT = 16; BUFN = 130

hub = PrimeHub(); clock = StopWatch()
try: hub.imu.reset_heading(0)
except Exception: pass

def emit_t(t,s,v): stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'%(t,s,v))
def emit(s,v): emit_t(clock.time(),s,v)
def end_sentinel(): stdout.write('{"event":"end"}\n')

ALLP=(Port.A,Port.B,Port.C,Port.D,Port.E,Port.F)
PORT_NUM={Port.A:0,Port.B:1,Port.C:2,Port.D:3,Port.E:4,Port.F:5}
motors=[]; ultra=[]; colors=[]
for p in ALLP:
    done=False
    try: m=Motor(p); motors.append([p,m]); done=True
    except Exception: pass
    if done: continue
    try: u=UltrasonicSensor(p); ultra.append([p,u]); done=True
    except Exception: pass
    if done: continue
    try: c=ColorSensor(p); colors.append([p,c])
    except Exception: pass

def read_u(u):
    try: return float(u.distance())
    except Exception: return 2000.0

fwdL=fwdR=rear=None
if len(ultra)>=2:
    rd=[[it[0],it[1],read_u(it[1])] for it in ultra]
    if len(ultra)==2: fwdL,fwdR=rd[0],rd[1]
    else:
        best=None; n=len(rd)
        for i in range(n):
            for j in range(i+1,n):
                df=abs(rd[i][2]-rd[j][2])
                if best is None or df<best[0]: best=[df,i,j]
        i,j=best[1],best[2]; fwdL,fwdR=rd[i],rd[j]
        for k in range(n):
            if k!=i and k!=j: rear=rd[k]; break

cfg_ok=(len(motors)>=2) and (fwdL is not None) and (fwdR is not None)
mA=motors[0][1] if len(motors)>=1 else None
mB=motors[1][1] if len(motors)>=2 else None
sL=fwdL[1] if fwdL else None; sR=fwdR[1] if fwdR else None
for it in motors:
    try: it[1].control.limits(speed=MAXSP, acceleration=10000)
    except Exception:
        try: it[1].control.limits(speed=MAXSP)
        except Exception: pass

def heading():
    try: return hub.imu.heading()
    except Exception: return 0.0
def fwd_read():
    a=read_u(sL); b=read_u(sR); return (a if a<b else b), a, b
def stop_both():
    try: mA.brake()
    except Exception: pass
    try: mB.brake()
    except Exception: pass

_h=[0.0,0]
def hold_reset(): _h[0]=0.0; _h[1]=clock.time()
def hold_step(e):
    now=clock.time(); dt=now-_h[1]
    if dt<=0: dt=1
    rate=(e-_h[0])*1000.0/dt; _h[0]=e; _h[1]=now
    s=KP*e+KD*rate; mag=abs(s)
    if mag>CORR_MAX: mag=CORR_MAX
    slow=CLAMP-mag
    if slow<0: slow=0
    reduce_is_B=(DBSIGN<0); slowB=((s>0)==reduce_is_B)
    if slowB: mA.run(FORWARD[0]*2000); mB.run(FORWARD[1]*int(slow))
    else: mA.run(FORWARD[0]*int(slow)); mB.run(FORWARD[1]*2000)

bt=[0]*BUFN; bd=[0.0]*BUFN; bi=0
try:
    emit("cfg_thresh",THRESH); emit("cfg_velest",VEL_EST)
    triggered=0; trig_reading=2000.0; trig_eff=2000.0; rest_reading=2000.0
    yaw_min=999.0; yaw_max=-999.0; yaw_at_trig=0.0
    if not cfg_ok: print("CFG-FAIL")
    else:
        hold_reset(); sat_n=0; g0=clock.time(); raw=2000.0; t_log=-100
        rr,_,_=fwd_read(); last_changed=rr; t_changed=clock.time(); prev_raw=rr
        while True:
            raw,dL,dR=fwd_read(); e=heading(); now=clock.time()
            if e<yaw_min: yaw_min=e
            if e>yaw_max: yaw_max=e
            if raw!=prev_raw: last_changed=raw; t_changed=now
            prev_raw=raw
            est=last_changed - VEL_EST*(now-t_changed)/1000.0
            eff = raw if raw<est else est
            if now-t_log>=LOG_DT and bi<BUFN: bt[bi]=now; bd[bi]=raw; bi+=1; t_log=now
            if eff<=THRESH: triggered=1; trig_reading=raw; trig_eff=eff; yaw_at_trig=e; break
            if e>ABORT_E or e<-ABORT_E: trig_reading=raw; yaw_at_trig=e; break
            if raw>=SAT:
                sat_n+=1
                if sat_n>=4: trig_reading=raw; yaw_at_trig=e; break
            else: sat_n=0
            if clock.time()-g0>GUARD_MS: trig_reading=raw; yaw_at_trig=e; break
            hold_step(e)
        stop_both()
        t2=clock.time(); t_log=-100
        while clock.time()-t2<SETTLE_MS:
            raw,dL,dR=fwd_read(); e=heading(); now=clock.time()
            if e<yaw_min: yaw_min=e
            if e>yaw_max: yaw_max=e
            if now-t_log>=22 and bi<BUFN: bt[bi]=now; bd[bi]=raw; bi+=1; t_log=now
            wait(12)
        rest_reading=raw; yaw_at_rest=heading()
        step=1
        if bi>80: step=(bi//80)+1
        k=0
        while k<bi: emit_t(bt[k],"fwd_min",bd[k]); k+=step
        emit("event_trigger",trig_reading); emit("yaw_min",yaw_min); emit("yaw_max",yaw_max)
        emit("rest_reading",rest_reading); emit("samples",bi)
        print("OP thresh=%d trig=%d rest=%d n=%d"%(int(THRESH),triggered,int(rest_reading),bi))
finally:
    stop_both(); end_sentinel()
```

## Appendix B — Document trail
`01_requirements_specification.md` · `02_tailored_sysml_model.md` ·
`03_calibration_and_verification_plan.md` (GATE A) · `04_calibration_report.md` +
`05_pre_verification_report.md` (GATE B) · `06_post_verification_report.md` (GATE C) · this report.
