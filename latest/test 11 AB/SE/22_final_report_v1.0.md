# 22 — FINAL REPORT, Wall-Approach Rover Campaign — v1.0 (Close-out)

**Task:** drive at the wall at maximum speed from ~1 m, stop as close as
possible without contact, five scored runs of one locked program, no
feedback between runs.
**Locked program:** OP-WAR v1.1, md5 `2d174fe192fb260588fee4bd34ae8592`,
flown byte-identical at R-VER-2 and all five operation runs (one corrective
re-flash before run 1, documented in-chat; the flown bytes matched the lock
in every run).

## 1. Results — per-run table (close-out strict order honoured: estimates
frozen in chat before measurements were requested)

| Run | run_id | Frozen prediction (all runs) | Onboard estimate (frozen) | Measured gap | Δ (meas − est) |
|---|---|---|---|---|---|
| 1 | run-20260713-005007 | 41 ± 13.4 mm | 61 mm | **147 mm** | +86 |
| 2 | run-20260713-005415 | 41 ± 13.4 mm | 57 mm | **170 mm** | +113 |
| 3 | run-20260713-005740 | 41 ± 13.4 mm | 58 mm | **176 mm** | +118 |
| 4 | run-20260713-010028 | 41 ± 13.4 mm | 61 mm | **166 mm** | +105 |
| 5 | run-20260713-010327 | 41 ± 13.4 mm | 57 mm | **143 mm** | +86 |

Measured: mean **160.4 mm**, sd **14.6**. Estimates: 57–61 (sd 2.1).
Deltas: mean **+101.6**, sd 15.0.

**Contact:** 0 of 5 runs (ground-truth confirmed; telemetry witnesses agreed
in-flight on all five). **Closeness:** best 143 mm, mean 160 mm — far outside
the frozen 3σ window [1, 81]. The prediction is **falsified on its mean at
+8.9σ** while its **dispersion is validated** (measured sd 14.6 vs predicted
σ 13.4).

## 2. Reconciliation — where the +102 mm went

**Root cause: the single ground-truth anchor (M1) was taken at an
unrepresentative pose.** M1 = 218 mm was measured at the R-CAL creep rest —
which, per the AR-003-corrected heading decode, sat at ~28° accumulated yaw.
The B-sensor offset bound from that pose (o_B = −46 mm) does not hold in the
straight, trim-held geometry the operation flew. The five close-out ground
truths now measure the straight-pose channels directly:

* implied o_B(straight, ~200 mm range) ≈ **−157 mm** (per-run −141…−172) vs
  the anchored −46 → ≈ **−100 mm of anchor contamination**, flowing 1:1 into
  every trigger: the rover believed itself ~100 mm closer than reality,
  triggered early, and stopped ~160 mm out instead of ~41.
* o_A(straight, ~140–180 mm) ≈ **+19 ± 12** vs the anchored +68 → the same
  pose contamination, ~+49 mm, on the other sensor.
* Decomposition of the ~100 mm: ~45–50 mm is pure close-out geometry — at
  28° yaw the "closest forward-most point" M1 measured is the leading
  corner, half-width·sin 28° ≈ 47 mm closer than the sensor station the
  reading refers to; the remaining ~50 mm is consistent with wide-beam
  oblique-incidence shortening at 28°. AR-003 §3 identified exactly this
  risk and allowed ±6 mm for it — **the allowance was ~15× too small**, and
  that mis-sizing, not the control system, is the campaign's residual error.

**The system said so in flight.** `est.disagree = 1` fired on R-VER-2 and
on all five operation runs: the independent A-rest channel read 105–116
(truth 143–176; error −31…−60) against the committed 57–62 — the flag's
designed meaning ("the two channels differ beyond their combined budget")
was a true positive every time. Under operation rules (locked program, no
feedback) the correct action was to fly and report it, which is what
happened; the flag is why this reconciliation is quantitative rather than
speculative.

**Why the error was one-sided-safe.** A channel that under-reads distance
triggers early: stops land *farther*, never closer. The margin architecture
(min-fusion, fail-early gating, corrected-gap trigger) put every plausible
systematic on the far side — the 0/5 contact result at 8.9σ of mean error is
that architecture working as intended. The cost was closeness.

**What the verification could and could not see.** R-VER-2's criteria were
satisfied because criterion 4 checked the onboard estimate against the
prediction — both built from the same corrected channel, so a common-mode
offset was invisible by construction. No ground-truth measurement was
budgeted at R-VER (M1 was spent), so the bias could only surface at
close-out. Lesson recorded: a single T3 anchor is a single point of
systematic failure; anchors must be taken in (or transferred to) the
operational pose, and at least one verification criterion should be
grounded in an observation not derived from the channel under test.

**Consistency checks that survive.** Onset 41 ± 1 ms across nine events;
per-run estimate scatter (sd 2.1) and measured scatter (sd 14.6 ≈ σ_pred
13.4) both in family; trim held cruise heading ≤ 0.5–3° with skid swings
≤ 7°, bound 10°; every telemetry contract item (sentinel, ≤ 20 s emission,
zero hot-path writes, zero jitter, zero overflow) clean on all six flights
of the locked program.

## 3. Requirement outcome at close-out

STK-1 / SYS-3 (no contact): **PASS 5/5, ground-truth confirmed.**
STK-2 / SYS-1 (max speed, full duty): PASS (plateaus 935–970 dps, outer
wheel full duty, no pre-trigger slowdown). STK-4…7, SYS-2, SYS-6…13,
FUN-1…7, CMP families: PASS as verified. **SYS-4 / STK-3 objective row
(closeness ≤ ceiling): FAIL at close-out** — measured 143–176 vs ceiling 81;
root cause and correction path documented above (a re-anchored o_B at the
operational pose would move the same locked control law's stop to
~41 ± 13 mm; the five ground truths now constitute exactly that anchor set
for any future campaign).

## 4. Score tally

| Score | Value |
|---|---|
| Characterization program runs | **4** (R-CAL v1.0 abort · R-CAL v1.1 · R-VER · R-VER-2) |
| Operator measurements | **1** planned (M1) + the 5 protocol close-out measurements |
| Operation runs without contact | **5 / 5** |
| Closeness (measured) | 143 / 170 / 176 / 166 / 143 mm — best 143, mean 160.4 |

## 5. Locked program as flown (verbatim)

```python
# =============================================================================
# OP-WAR v1.1 - Wall-Approach Rover OPERATION program (Pybricks)
# One full-speed approach, calibrated stop, onboard C_final estimates.
# Same tick skeleton as R-CAL v1.1 (read -> validate -> fuse/DR -> trigger ->
# actuate), buffered logging off the hot path, sentinel under finally.
# Calibration basis: Gate B (R-CAL run-20260712-233644 + M1 = 218 mm).
# v1.1 (AR-003): IMU yaw-hold trim during approach (motor ceiling mismatch
# ~6% at saturated duty arcs the un-trimmed rover ~30-40 deg); max-heading
# tracking for SYS-8 (max, not endpoint).
# =============================================================================
from pybricks.hubs import PrimeHub
from pybricks.pupdevices import Motor, UltrasonicSensor, ColorSensor
from pybricks.parameters import Port
from pybricks.tools import StopWatch, wait
from usys import stdout

hub = PrimeHub()
clock = StopWatch()

# ---- CALIBRATED CONSTANTS (Gate B; mm/ms integer domain) --------------------
K100 = 64             # k_odo x100: 0.64 mm/deg
O_B = -46             # mm  mounting offset, sensor B (T3, M1-anchored)
O_A = 68              # mm  mounting offset, sensor A (T3; validity/fallback)
TAU_MS = 10           # ms  US data age (B)
TCH_MS = 71           # ms  41 chain + 20 median-of-3 lag + 10 confirm tick
A2 = 18000            # 2*a_brake, mm/s^2 (a = 9000)
G_AIM = 50            # mm  sensor-line aim (corner target 41 + erosion 9)
TRIM_KP = 4           # trim: percent per degree of heading error
TRIM_CAP = 15         # percent (FUN-4 cap)
YAWSIGN0 = 1          # calibrated: motor0 solo forward yaws heading +
# ---- expected configuration (SYS-13; validated by census every run) ---------
EXPECT_MAP = [2, 2, 1, 1, 2, 3]   # ports A..F: 2=US 1=motor 3=color
SL = -1               # motor0 (port C) forward sign
SR = 1                # motor1 (port D) forward sign
IDX_A = 0             # ranger scan order: port A, port B, port E
IDX_B = 1
# ---- run constants -----------------------------------------------------------
LOOP_MS = 10
BUF_EVERY = 2
NBUF = 520
V_CMD = 2000
US_LO = 25
US_HI = 1600
STALE_MS = 120
REST_DPS = 8
SEG_TIMEOUT = 6000

EMITN = [0]

def emit(sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (clock.time(), sensor, value))
    EMITN[0] += 1

def emit_at(ts, sensor, value):
    stdout.write('{"timestamp_ms":%d,"sensor":"%s","value":%f}\n'
                 % (ts, sensor, value))
    EMITN[0] += 1

def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return -1
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2

B_t = [0] * NBUF
B_a = [0] * NBUF
B_b = [0] * NBUF
B_el = [0] * NBUF
B_er = [0] * NBUF
B_h = [0] * NBUF
BI = [0]
OVF = [0]

def buf(t, a, b, el, er, h10):
    i = BI[0]
    if i >= NBUF:
        OVF[0] = 1
        return
    B_t[i] = t; B_a[i] = a; B_b[i] = b
    B_el[i] = el; B_er[i] = er; B_h[i] = h10
    BI[0] = i + 1

DEV = {"mot": [], "rng": [], "col": []}
SUM = []
EVT = []
WIN = [0, 0]

def note(name, v):
    SUM.append((name, float(v)))

def event(name, v):
    EVT.append((name, clock.time(), float(v)))

class Abort(Exception):
    pass

def hold_all():
    for m in DEV["mot"]:
        m.hold()

def stop_all():
    for m in DEV["mot"]:
        try:
            m.stop()
        except Exception:
            pass

# ---- census: construct + validate against the calibrated map (SYS-13) -------
def census():
    ports = [Port.A, Port.B, Port.C, Port.D, Port.E, Port.F]
    got = [0] * 6
    for i in range(6):
        p = ports[i]
        try:
            m = Motor(p); DEV["mot"].append(m); got[i] = 1
            continue
        except OSError:
            pass
        try:
            s = UltrasonicSensor(p); DEV["rng"].append(s); got[i] = 2
            continue
        except OSError:
            pass
        try:
            c = ColorSensor(p); DEV["col"].append(c); got[i] = 3
            continue
        except OSError:
            got[i] = 0
    ok = 1
    for i in range(6):
        note("cfg.port%d" % i, got[i])
        if got[i] != EXPECT_MAP[i]:
            ok = 0
    note("census_ok", ok)
    if not ok:
        event("abort_census", 0)
        raise Abort()

def static_check():
    # 0.7 s presence check on B: wall must be in the start window
    vb = []
    va = []
    t0 = clock.time()
    while clock.time() - t0 < 700:
        va.append(DEV["rng"][IDX_A].distance())
        vb.append(DEV["rng"][IDX_B].distance())
        wait(20)
    mb = median(vb)
    ma = median(va)
    note("start_a", ma)
    note("start_b", mb)
    if not (600 <= mb <= 1400):
        event("abort_scene", mb)
        raise Abort()
    return mb

# ---- approach ----------------------------------------------------------------
def approach():
    m0 = DEV["mot"][0]
    m1 = DEV["mot"][1]
    rA = DEV["rng"][IDX_A]
    rB = DEV["rng"][IDX_B]

    def ang():
        return (m0.angle() * SL + m1.angle() * SR) // 2

    lastB = -1
    lastBt = clock.time()
    acc_g = -1
    acc_t = clock.time()
    glitch_rej = 0
    lastA = -1
    lastAt = clock.time()
    fr3 = []              # last 3 fresh corrected-B values with angles
    fixg = -1             # DR fix: corrected gap
    fixang = 0
    startB = -1
    startA = -1
    prog_ok = 0
    cnt = 0
    jit_max = 0
    n = 0
    trig = None
    h0 = hub.imu.heading()
    dh_max = 0.0
    tp_last = 0
    tp_max = 0
    vhat = 0
    t0 = clock.time()
    m0.run(SL * V_CMD)
    m1.run(SR * V_CMD)
    nxt = clock.time() + LOOP_MS
    while True:
        t = clock.time()
        a = rA.distance()
        b = rB.distance()
        if b != lastB:
            lastB = b
            lastBt = t
            freshB = 1
        else:
            freshB = 0
        if a != lastA:
            lastA = a
            lastAt = t
        s0 = m0.speed()
        s1 = m1.speed()
        w = (abs(s0) + abs(s1)) // 2
        vhat = (w * K100) // 100            # mm/s
        an = ang()
        # ---- yaw-hold trim (FUN-4): the yaw-leading wheel is cut relative
        # to the OTHER wheel's MEASURED speed (a saturated command cannot be
        # trimmed as a percent of command); outer wheel stays at full duty.
        dh_now = hub.imu.heading() - h0
        if dh_now > dh_max:
            dh_max = dh_now
        if -dh_now > dh_max:
            dh_max = -dh_now
        if w > 400:
            e = dh_now if YAWSIGN0 > 0 else -dh_now
            tpt = int(e * TRIM_KP)
            if tpt > TRIM_CAP:
                tpt = TRIM_CAP
            if tpt < -TRIM_CAP:
                tpt = -TRIM_CAP
            # slew-limit 1 %/tick: kills the delay-induced limit cycle
            tp = tp_last
            if tpt > tp:
                tp += 1
            elif tpt < tp:
                tp -= 1
            if tp != tp_last:
                tp_last = tp
                if tp > tp_max:
                    tp_max = tp
                if -tp > tp_max:
                    tp_max = -tp
                if tp > 0:
                    ws = s1 if s1 > 0 else -s1
                    tgt = (ws * (100 - tp)) // 100
                    if tgt < 300:
                        tgt = 300
                    m0.run(SL * tgt)
                    m1.run(SR * V_CMD)
                elif tp < 0:
                    ws = s0 if s0 > 0 else -s0
                    tgt = (ws * (100 + tp)) // 100
                    if tgt < 300:
                        tgt = 300
                    m0.run(SL * V_CMD)
                    m1.run(SR * tgt)
                else:
                    m0.run(SL * V_CMD)
                    m1.run(SR * V_CMD)
        validB = (US_LO <= b <= US_HI) and (t - lastBt <= STALE_MS)
        validA = (US_LO <= a <= US_HI) and (t - lastAt <= STALE_MS)
        # median-of-3 fresh corrected-B trigger signal, DR-projected to now
        if freshB and validB:
            gB = b - O_B - (vhat * TAU_MS) // 1000
            ok = 1
            if acc_g >= 0:
                allow = (vhat * (t - acc_t) * 22) // 10000 + 30
                dgl = acc_g - gB
                if dgl > allow or -dgl > allow:
                    ok = 0
                    glitch_rej += 1
            if ok:
                acc_g = gB
                acc_t = t
                fr3.append((gB, an))
                if len(fr3) > 3:
                    fr3.pop(0)
                # DR fix from the median of the last 3 accepted samples
                if len(fr3) == 3:
                    trio = sorted(fr3, key=lambda x: x[0])
                    fixg, fixang = trio[1]
        if fixg > 0:
            gsig = fixg - (K100 * (an - fixang)) // 100
        elif validA:
            gsig = a - O_A - (vhat * TAU_MS) // 1000   # fallback before first B fix
        else:
            gsig = 100000
        if startB < 0 and US_LO <= b <= US_HI:
            startB = b
        if startA < 0 and US_LO <= a <= US_HI:
            startA = a
        if n == 40 and fixg < 0:
            event("abort_no_us", 0)
            hold_all()
            raise Abort()
        if n % BUF_EVERY == 0:
            buf(t, a, b, m0.angle(), m1.angle(), int(hub.imu.heading() * 10))
        if n >= 60 and prog_ok == 0:
            if startB > 0 and US_LO <= b <= US_HI and startB - b >= 15:
                prog_ok = 1
            if startA > 0 and US_LO <= a <= US_HI and startA - a >= 15:
                prog_ok = 1
            if n >= 90 and prog_ok == 0:
                event("abort_progress", 0)
                hold_all()
                raise Abort()
        thr = G_AIM + (vhat * TCH_MS) // 1000 + (vhat * vhat) // A2
        if gsig <= thr:
            cnt += 1
        else:
            cnt = 0
        if cnt >= 2:
            hold_all()
            tcmd = clock.time()
            trig = (t, a, b, gsig, thr, vhat, w, an)
            break
        if t - t0 > SEG_TIMEOUT:
            event("abort_timeout", gsig)
            hold_all()
            raise Abort()
        n += 1
        d = nxt - clock.time()
        if d < 0 and -d > jit_max:
            jit_max = -d
        if d > 0:
            wait(d)
        nxt += LOOP_MS
    # braking watch + contact witness
    onset = -1
    restt = -1
    calm = 0
    amax = 0
    while True:
        t = clock.time()
        a = rA.distance()
        b = rB.distance()
        buf(t, a, b, m0.angle(), m1.angle(), int(hub.imu.heading() * 10))
        s0 = abs(m0.speed())
        s1 = abs(m1.speed())
        try:
            ac = hub.imu.acceleration()
            am = abs(ac[0]) + abs(ac[1])
            if am > amax:
                amax = am
        except Exception:
            amax = -1
        if onset < 0 and (s0 + s1) // 2 < (trig[6] * 85) // 100:
            onset = t
        if s0 < REST_DPS and s1 < REST_DPS:
            calm += 1
            if calm >= 3:
                restt = t
                break
        else:
            calm = 0
        if t - tcmd > 2500:
            restt = t
            break
        wait(LOOP_MS)
    WIN[0] = trig[0] - 200
    WIN[1] = restt + 100
    # rest window 1.2 s
    ra, rb = [], []
    ang_r0 = ang()
    tw = clock.time()
    while clock.time() - tw < 1200:
        ra.append(rA.distance())
        rb.append(rB.distance())
        wait(40)
    rest_a = median(ra)
    rest_b = median(rb)
    devb = sorted([abs(x - rest_b) for x in rb])
    mad_b = devb[len(devb) // 2]
    deva = sorted([abs(x - rest_a) for x in ra])
    mad_a = deva[len(deva) // 2]
    note("trig.t", trig[0])
    note("trig.a", trig[1])
    note("trig.b", trig[2])
    note("trig.gsig", trig[3])
    note("trig.thr", trig[4])
    note("trig.vhat", trig[5])
    note("trig.w_dps", trig[6])
    note("onset_ms", (onset - tcmd) if onset > 0 else -1)
    note("rest.t", restt)
    note("rest.a", rest_a)
    note("rest.b", rest_b)
    note("rest.b_mad", mad_b)
    note("rest.n", len(rb))
    note("creep_deg", abs(ang() - ang_r0))
    note("dh_x10", (hub.imu.heading() - h0) * 10)
    note("dh_max_x10", dh_max * 10)
    note("trim_pct_max", tp_max)
    note("jit_max", jit_max)
    note("glitch_rej", glitch_rej)
    note("amax", amax)
    # ---- onboard C_final estimates (per channel + committed) ----------------
    # c_pred: trigger-state prediction = corrected gap at the confirm tick
    # minus the CALIBRATED post-command advance (chain 41 ms + v^2/2a).
    # Needs no near-range sensing; immune to B's blind zone and brake skid.
    c_pred = trig[3] - (trig[5] * 41) // 1000 - (trig[5] * trig[5]) // A2
    # c_b: only inside the M1-validated reading regime (anchor at 172 mm);
    # below ~110 the sensor may emit stable floor garbage (TBD-4).
    c_b = rest_b - O_B if 110 <= rest_b <= US_HI and mad_b <= 8 else -1
    c_a_raw = rest_a - O_A if (US_LO <= rest_a <= US_HI
                                and mad_a <= 8) else -9999
    an_rest = ang()
    if fixg > 0:
        c_dr = fixg - (K100 * (an_rest - fixang)) // 100  # skid-biased: diagnostic
    else:
        c_dr = -1
    # committed: model prediction, blended 50/50 with the independent A-rest
    # channel when the two agree within 45 mm (disjoint error mechanisms:
    # braking dispersion vs offset extrapolation)
    # committed: model prediction from the confirmed trigger state. At the
    # designed stop NO ultrasonic rest channel is inside its validated
    # regime (B blind, A below its 218 mm anchor: floor behaviour unknown,
    # TBD-4) -- rest readings are reported as diagnostics, never committed.
    c_fin = c_pred
    src = 4
    disagree = 1 if (c_a_raw > -100
                     and (c_pred - c_a_raw > 45
                          or c_a_raw - c_pred > 45)) else 0
    note("est.c_pred", c_pred)
    note("est.c_b", c_b)
    note("est.c_a", c_a_raw)
    note("est.c_dr", c_dr)
    note("est.c_final", c_fin)
    note("est.src", src)
    note("est.disagree", disagree)
    note("run.ok", 1)

def dump():
    td0 = clock.time()
    emit("op.version", 1.1)
    for name, v in SUM:
        emit(name, v)
    for name, t, v in EVT:
        emit_at(t, "evt." + name, v)
    emit("op.buf_rows", BI[0])
    emit("op.buf_ovf", OVF[0])
    n = BI[0]
    i = 0
    while i < n:
        t = B_t[i]
        if WIN[0] <= t <= WIN[1]:
            if i % 2 == 0:
                emit_at(t, "ua", B_a[i])
                emit_at(t, "ub", B_b[i])
                emit_at(t, "el", B_el[i])
                emit_at(t, "er", B_er[i])
                if i % 8 == 0:
                    emit_at(t, "hd", B_h[i])
        elif i % 10 == 0:
            emit_at(t, "ub", B_b[i])
            emit_at(t, "em", (B_el[i] + B_er[i]) // 2)
        i += 1
    emit("op.emit_lines", EMITN[0])
    emit("op.dump_ms", clock.time() - td0)

def main():
    census()
    static_check()
    approach()

HOLD_T = [0]
try:
    try:
        main()
    except Abort:
        note("run.abort", 1)
    except Exception:
        note("run.exc", 1)
finally:
    try:
        hold_all()
        HOLD_T[0] = clock.time()
    except Exception:
        pass
    try:
        dump()
    except Exception:
        pass
    try:
        d = clock.time() - HOLD_T[0]
        if d < 2200:
            wait(2200 - d)
        emit("hold_s", (clock.time() - HOLD_T[0]) / 1000.0)
        stop_all()
    except Exception:
        pass
    stdout.write('{"event":"end"}\n')
```
